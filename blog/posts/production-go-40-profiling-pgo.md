<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/production-go-40-profiling-pgo.html -->

# Profiling and PGO in Production

*Finding performance wins with evidence instead of guesses — the four pprof profiles and when each matters, capturing them safely, reading them with `top`/`list`/flame graphs, execution traces for tail latency, and a measured 6.2× + 8.6% from the full workflow.*

---

Every performance investigation starts the same way: someone points at a dashboard and says "the p99 is creeping up." The instinct is to open the code and start guessing, and that instinct is almost always wrong — the hot path is rarely where you think it is. It's a `time.Format` inside a log line, a `regexp.MustCompile` that wandered into a per-request function, a payload parsed twice.

Profiling replaces guessing with evidence. This post is the workflow: which profile answers which question, capturing from a live service safely, reading what you captured, when to reach for an execution trace instead, and feeding a representative profile back to the compiler with PGO. And because this series doesn't do hypothetical numbers, the whole workflow is **run for real** on a demo authorization path with two deliberately planted (and extremely common) bugs — every profile excerpt and speedup below is actual output (Apple M1 Max, Go 1.27).

This is a method post. It deliberately does not re-teach GC traces ([that post](/blog/posts/production-go-38-reading-gc-traces.html)) or escape analysis ([that one](/blog/posts/production-go-37-escape-analysis-allocations.html)) — complementary lenses, pointed at along the way.

---

## 1. The four profiles, and the question each answers

`runtime/pprof` exposes several profile types; four carry nearly all investigations, and the discipline is matching profile to *symptom* before capturing anything:

| Profile | Question it answers | Reach for it when |
|---|---|---|
| **CPU** | Where is on-CPU time spent? | CPU-bound; throughput caps below expectation |
| **Heap** | What allocates; what's still live? | RSS climbs, GC frequency rises, OOM kills |
| **Block** | What waits on sync primitives? | Latency high but CPU idle |
| **Mutex** | Which locks are contended? | Throughput plateaus as cores are added |

The trap is defaulting to CPU for everything. If p99 is bad but the box is at 30% CPU, a CPU profile shows you a mostly-idle scheduler and teaches you nothing — that symptom is a *waiting* problem, and block/mutex profiles (or a trace) are the right tools.

Block and mutex profiles are **off by default** because they cost something to collect. Arm them explicitly, conservatively:

```go
import "runtime"

func init() {
	// Sample 1 blocking event per N ns of blocked time. Higher = cheaper, coarser.
	runtime.SetBlockProfileRate(10_000) // 10µs
	// Sample 1 in N mutex contention events.
	runtime.SetMutexProfileFraction(100)
}
```

**The gotcha:** these rates are global and cost you continuously, not just while you're looking. `SetMutexProfileFraction(1)` captures everything and is fine on a laptop; on a hot path it adds measurable overhead to every `Unlock`. Keep low rates armed in staging; crank them briefly, behind a flag, when actively hunting in production.

---

## 2. Exposing profiles safely on a live service

The famous one-liner is also the famous mistake:

```go
import _ "net/http/pprof" // registers on http.DefaultServeMux — dangerous in prod
```

That silently exposes CPU profiles, heap dumps, and full goroutine stacks on whatever mux serves business traffic — both a DoS lever (a CPU profile does real work for 30s) and an information leak. Never put pprof on the public listener. Run it on a separate, internal-only listener instead:

```go
package obs

import (
	"net/http"
	"net/http/pprof"
)

// StartDebugServer runs pprof on an internal-only address.
// Reach it via kubectl port-forward or a mesh-internal route — never the LB.
func StartDebugServer(addr string) *http.Server {
	mux := http.NewServeMux()
	mux.HandleFunc("/debug/pprof/", pprof.Index)
	mux.HandleFunc("/debug/pprof/cmdline", pprof.Cmdline)
	mux.HandleFunc("/debug/pprof/profile", pprof.Profile) // CPU
	mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
	mux.HandleFunc("/debug/pprof/trace", pprof.Trace) // execution trace
	srv := &http.Server{Addr: addr, Handler: mux}
	go func() { _ = srv.ListenAndServe() }()
	return srv
}
```

```bash
kubectl port-forward pod/ledger-authz-7d9c 6060:6060 &

go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30   # CPU
go tool pprof http://localhost:6060/debug/pprof/heap                 # memory
go tool pprof http://localhost:6060/debug/pprof/block                # waiting
go tool pprof http://localhost:6060/debug/pprof/mutex                # contention
```

**The gotcha:** a CPU profile sends `SIGPROF` ~100×/sec and unwinds stacks each time — small but non-zero overhead that lands on one instance for 30 seconds. Profile *one* canary pod, never the whole fleet at once during an incident, or you amplify the latency you're diagnosing. For memory emergencies, wiring `runtime/pprof.WriteHeapProfile` to a `SIGUSR1` handler lets on-call snapshot the heap before the OOM kill destroys the evidence.

---

## 3. Reading a profile: top, list, and the flame graph

Time for the real workload. The demo is an authorization function with two planted bugs that pass review constantly: the request JSON is parsed twice (a "probe" parse, then the typed parse), and a currency regexp is compiled per call. Driven flat out, it manages **324,268 authorizations/second** — remember that number.

**`top` — and its first lesson.** Opening the raw capture:

```text
Duration: 5.13s, Total samples = 5480ms
      flat  flat%        cum  cum%
    1880ms 34.31%     1880ms 34.31%  runtime.kevent
     620ms 11.31%      620ms 11.31%  runtime.pthread_cond_wait
     580ms 10.58%      580ms 10.58%  runtime.usleep
     ...
```

The top of the profile is *runtime idle machinery* — because the demo loop is single-threaded on a 10-core machine, and idle P's get sampled too. This is real output and a real trap: before reading any profile, ask whether its top reflects your workload or your idle capacity. Filter to the path you care about (`-show_from`, or click into the flame graph) rather than optimizing `runtime.kevent`.

**`list` — the command people skip.** Focused on the handler, per-line costs name both bugs precisely:

```text
(pprof) list authorize
ROUTINE ======================== main.authorize
         0      1.38s (flat, cum) 25.18% of Total
         .       10ms   var probe map[string]any // first parse: "is it JSON at all"
         .      550ms   if json.Unmarshal(raw, &probe) != nil {
         .          .   }
         .      200ms   if json.Unmarshal(raw, &req) != nil {
         .          .   }
         .      590ms   re := regexp.MustCompile(`^[A-Z]{3}$`) // compiled on every call
         .       30ms   if !re.MatchString(req.Currency) {
```

This is the whole argument for `list` in one screen: "JSON is hot" (what `top` tells you) becomes "**line 40 is the single hottest line, and it's the regexp compile, not the match**" — 590ms compiling versus 30ms matching. The probe parse (550ms) costs 2.7× the typed parse of the *same bytes*, because parsing into `map[string]any` allocates generically.

**The fix and the proof.** Hoist the regexp to a package `var`, delete the probe parse (the typed `Unmarshal` already reports malformed JSON). Two trivial diffs:

```text
before:   324,268 authorizations/s
after:  2,006,715 authorizations/s     (6.2x)
```

**`web` / `-http`** renders the flame graph for seeing shape (wide frame you didn't expect = your lead), and before/after diffing is where profiling pays for itself:

```bash
go tool pprof -http=:8080 -diff_base=before.pprof after.pprof
```

**The gotcha:** confirm the profile captured representative load before trusting it — the idle-noise lesson above, plus: a profile from a traffic trough or right after a GC misleads in quieter ways. `pprof` prints duration and sample counts on open; if they look thin, re-capture.

---

## 4. When a profile isn't enough: execution traces

Profiles are statistical summaries — *what* consumed time in aggregate, not *when* or *why this request stalled*. For tail-latency mysteries ("p99.9 is 40× the median but the box is idle"), the execution trace records scheduler, GC, syscall, and goroutine events with timestamps:

```bash
curl -s "http://localhost:6060/debug/pprof/trace?seconds=5" -o trace.out
go tool trace trace.out
```

The trace answers questions no profile can:

- Is a slow request *running* (CPU-bound → back to the CPU profile) or *not scheduled* (runnable but no P — oversubscription, or the [GOMAXPROCS-in-containers mismatch](/blog/posts/production-go-36-gomaxprocs-kubernetes.html), whose measured freezes are exactly what a trace makes visible per-goroutine)?
- Did a GC pause land on *this* goroutine? (The trace shows it landed; [`gctrace`](/blog/posts/production-go-38-reading-gc-traces.html) explains why GC ran then.)
- Are goroutines piling up on a channel or mutex handoff?

**The gotcha:** traces are big and short — a few seconds of a busy service is tens of megabytes, and the UI drags past ~10–20s of capture. Take short, targeted traces during the symptom. And a trace records everything; keep `/debug/pprof/trace` as internal as the profiler, for the same reasons.

---

## 5. Profile-Guided Optimization: handing the compiler your evidence

Everything above finds wins by hand. PGO hands your profile to the compiler so it optimizes for *actual* behavior — aggressively inlining the proven-hot functions, devirtualizing interface calls that overwhelmingly resolve to one type, laying out code for real branch patterns.

The mechanism is deliberately boring. Drop a CPU profile named `default.pgo` in the main package's directory, and `go build` uses it automatically:

```bash
# 1. Capture a representative profile from production (canary, peak-ish load)
go tool pprof -proto \
  "http://localhost:6060/debug/pprof/profile?seconds=60" > cpu.pprof

# 2. It becomes a build input
cp cpu.pprof ./cmd/ledger-authz/default.pgo

# 3. Build. No flags needed.
go build ./cmd/ledger-authz
```

Run against the *fixed* demo binary — profile captured from it, rebuilt with that profile, three runs each:

```text
fixed, no PGO:    2,002,094 – 2,015,103 authorizations/s
fixed, with PGO:  2,178,292 – 2,180,460 authorizations/s    (+8.6%)
```

A consistent, free **8.6%** on top of the hand optimization. Two honest footnotes on that number. First, it's *above* the 2–7% the Go team reports for large real binaries — a tiny demo whose entire hot path fits in a few functions (including a one-implementation interface call, prime devirtualization bait) is close to PGO's best case; expect the low single digits fleet-wide. Second, the attribution is the measured delta itself — same source, same flags, the profile the only difference between the two builds.

**The gotcha:** the profile must be *representative*, and it goes stale. A profile from a quiet Sunday or an old release teaches the compiler yesterday's hot path. Treat `default.pgo` as a build artifact with a lifecycle: capture from a canary on the current release under real load, commit it (or fetch in CI), refresh when the hot path shifts. Iterating on top of a PGO build is stable by design — profiles from PGO-optimized binaries still produce sensible builds. And PGO is not a substitute for sections 1–4: it would have optimized the *double JSON parse* faithfully. Fix the algorithm first; let PGO polish what remains. The ordering in this post's own numbers makes the case: hand fixes 6.2×, PGO 1.086×.

---

## 6. The workflow, start to finish

1. **Start from a symptom, not a hunch.** Latency, memory, or a throughput ceiling — the symptom picks the profile.
2. **Capture safely from one canary** over an internal listener, under representative load.
3. **Read `top` → `list` → flame graph**, filtering out idle noise, and diff against a baseline to prove any fix.
4. **If it's a waiting problem, trace it** instead of profiling it.
5. **Fix, re-profile, confirm the diff moved.**
6. **Then turn on PGO** to lock in compiler-level wins across deploys.

Every step produces evidence before code changes, and evidence that the change worked. "I profiled it — here's the before/after" is the only justification a hot path should accept.

---

## Key takeaways

- **Match the profile to the symptom.** CPU for on-CPU cost, heap for memory, block/mutex for waiting — don't point a CPU profile at an idle box.
- **Never expose pprof on the business mux.** Internal listener, one canary, port-forward.
- **`list` turns "this function is hot" into "this line is hot."** Measured: it attributed 590ms to a regexp *compile* that review had read as a cheap match — and the resulting two-line fix was worth 6.2×.
- **Mind idle-sample noise.** A real capture's top-10 was two-thirds runtime idle machinery; filter before reading.
- **Traces answer "when" and "why stalled."** Reach for `go tool trace` when latency is high and CPU is not.
- **PGO is free and compounding — after the hand work.** Measured +8.6% on a best-case demo (expect low single digits at fleet scale), from a `default.pgo` that must be kept representative and fresh.

---

## Further reading

- William Kennedy, profiling series — Ardan Labs blog: https://www.ardanlabs.com/blog
- Go team, *Profile-guided optimization*: https://go.dev/doc/pgo
- Go team, *Diagnostics* (pprof, trace, runtime profiling reference): https://go.dev/doc/diagnostics

---

*All profile excerpts and throughput numbers: a single demo workload on an Apple M1 Max, Go 1.27, 5-second runs; the planted bugs (double parse, per-call regexp compile) are the two most common real-world findings this workflow produces.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-08-04
Canonical: https://pratikdhanave.com/blog/posts/production-go-40-profiling-pgo.html
Attribution: please link the canonical URL when citing or quoting this post.
