# Profiling and PGO in Production

*How I actually find performance wins in a high-TPS payment ledger — the four pprof profiles and when each one matters, capturing them safely against live traffic, reading them with `go tool pprof`, chasing latency with execution traces, and locking the gains in with Profile-Guided Optimization.*

---

Every performance investigation I've run in payments started the same way: someone points at a Grafana panel and says "the p99 on authorization is creeping up." The instinct is to open the code and start guessing. That instinct is almost always wrong. On a ledger doing tens of thousands of transactions per second, the hot path is rarely where you think it is — it's a `time.Format` inside a log line, a `regexp.MustCompile` that escaped into a per-request function, or a map you allocate fresh on every settlement.

Profiling replaces guessing with evidence. This post is the workflow I use: which profile answers which question, how to capture profiles from a live service without taking it down, how to read them, when to reach for an execution trace instead, and how to feed a representative CPU profile back into the compiler with PGO so the wins stick across deploys.

This is a method post. It deliberately does **not** re-teach GC pacing traces (that's the `GODEBUG=gctrace` post) or escape analysis (that's the allocation post) — both are complementary lenses, and I'll point at where they slot in.

---

## 1. The four profiles, and the question each one answers

`runtime/pprof` exposes several profile types. In four years of chasing ledger latency I've only ever needed four of them, and the discipline is matching the profile to the *symptom* before you capture anything.

| Profile | Question it answers | Reach for it when |
|---|---|---|
| **CPU** | Where is on-CPU time being spent? | Service is CPU-bound; throughput caps below expectation |
| **Heap** | What is allocating, and what's still live? | RSS climbs, GC frequency rises, OOM kills |
| **Block** | What goroutines wait on sync primitives? | Latency is high but CPU is idle |
| **Mutex** | Which locks are contended? | Throughput plateaus as you add cores |

The trap is defaulting to CPU for everything. If your p99 is bad but the box is 30% CPU, a CPU profile will show you a mostly-idle scheduler and teach you nothing. That symptom — latency without CPU — is a *waiting* problem, and block/mutex profiles (or a trace) are the right tools.

Block and mutex profiles are **off by default** because they carry sampling overhead. You arm them explicitly, and I keep the sampling rates conservative in production:

```go
import "runtime"

func init() {
    // Sample 1 blocking event per N nanoseconds of blocked time.
    // Higher = less overhead, coarser data.
    runtime.SetBlockProfileRate(10_000) // 10µs
    // Sample 1 in N mutex contention events.
    runtime.SetMutexProfileFraction(100)
}
```

**The gotcha:** these rates are global and cost you continuously, not just while you're looking. `SetMutexProfileFraction(1)` captures every contention event and is fine on a laptop; on a hot ledger path it adds measurable overhead to every `Unlock`. I leave block/mutex profiling armed at low rates in staging and only crank the fraction up briefly, under a flag, when I'm actively hunting contention in prod.

---

## 2. Exposing profiles safely on a live service

The easy way to collect profiles is `net/http/pprof`, which registers handlers under `/debug/pprof/`. The mistake I see constantly is importing it for its side effect on the *main* service mux:

```go
import _ "net/http/pprof" // registers on http.DefaultServeMux — dangerous in prod
```

That silently exposes CPU profiles, heap dumps, and full goroutine stacks on whatever mux serves your business traffic. On a payment API those endpoints are both a DoS lever (a CPU profile pins a core for 30s) and an information leak. Never put pprof on the public listener.

What I run instead: a separate listener, bound to localhost or an internal-only interface, on its own mux, reachable only from inside the cluster.

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

Then I pull profiles across a port-forward, so nothing is ever exposed beyond the pod:

```bash
kubectl port-forward pod/ledger-authz-7d9c 6060:6060 &

# 30-second CPU profile under live load
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Heap: in-use bytes right now (add ?gc=1 to force GC first for live-set accuracy)
go tool pprof http://localhost:6060/debug/pprof/heap

# Contention and waiting
go tool pprof http://localhost:6060/debug/pprof/block
go tool pprof http://localhost:6060/debug/pprof/mutex
```

**The gotcha:** a CPU profile does real work — it sends `SIGPROF` ~100 times/sec and unwinds the stack each time. That overhead is small but non-zero, and 30 seconds of it lands on one instance. In a fleet, profile *one* canary pod, not the whole deployment, and never profile every replica at once during an incident — you'll amplify the very latency you're diagnosing. If you can't reach a shell, `runtime/pprof.StartCPUProfile` gated behind an admin RPC writing to a temp file works too, but the internal HTTP listener is simpler to operate.

For capturing a heap profile the moment memory misbehaves, I wire `runtime/pprof.WriteHeapProfile` to a `SIGUSR1` handler so an on-call engineer can grab a snapshot before the pod gets OOM-killed and the evidence disappears.

---

## 3. Reading a profile: top, list, and the flame graph

A captured profile is useless until you can read it. Three `pprof` commands carry almost every investigation.

**`top`** ranks functions by cost. The columns that matter are `flat` (time in the function itself) and `cum` (time in it plus everything it called):

```bash
(pprof) top20
```

```
      flat  flat%   sum%        cum   cum%
   TODO: real number   ...   TODO: real number   encoding/json.(*decodeState).object
   TODO: real number   ...   TODO: real number   github.com/acme/ledger/authz.normalizeAmount
   ...
```

A function with high `flat` is doing the work itself — optimize it directly. High `cum` but low `flat` means the cost is downstream; follow it. In one authz investigation the top of the profile was dominated by JSON decoding of a request field we parsed twice — high `cum` on our handler, high `flat` inside `encoding/json`.

**`list`** annotates the source of a specific function with per-line cost. This is where you go from "JSON is hot" to "*this line* is hot":

```bash
(pprof) list normalizeAmount
```

It prints the function's source with sampled time beside each line, so a stray allocation or a per-call `regexp.Compile` shows up as an obvious spike. This is the single most useful command in pprof and the one people skip.

**`web`** (or `-http`) renders the flame graph — the fastest way to *see* shape. Wide frames are expensive; a wide frame you didn't expect is your lead:

```bash
# Interactive browser UI with flame graph, source, and graph views
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/profile?seconds=30
```

Comparing before/after is where profiling pays for itself. Save a baseline, ship a fix, capture again, and diff:

```bash
go tool pprof -http=:8080 -diff_base=before.pprof after.pprof
```

**The gotcha:** always confirm the profile captured representative load before you trust it. A CPU profile taken during a traffic trough shows idle-loop noise, and a heap profile taken right after a GC shows an artificially small live set. I check the profile's own duration and sample count (`pprof` prints them on open) and re-capture if the numbers look thin. Reading a profile from the wrong moment sends you optimizing code that isn't actually hot — [in one case I "fixed" a hotspot that turned out to be TODO: real number % of real production CPU].

---

## 4. When a profile isn't enough: execution traces

Profiles are statistical summaries — they tell you *what* consumed time in aggregate, not *when* or *why a specific request stalled*. For tail-latency problems, scheduling stalls, and "the p99.9 is 40x the median but the box is idle" mysteries, you need the execution trace, which records scheduler, GC, syscall, and goroutine events with timestamps.

```bash
# Capture a 5-second trace under load
curl -s "http://localhost:6060/debug/pprof/trace?seconds=5" -o trace.out
go tool trace trace.out
```

`go tool trace` opens a browser UI with a timeline, per-goroutine views, and — the part I actually use — the **scheduler latency** and **network/sync blocking** breakdowns. It answers questions a profile can't:

- Is a request slow because it's *running* (CPU-bound work → back to a CPU profile) or because it's *not scheduled* (goroutine ready but no P available → you're oversubscribed or `GOMAXPROCS` is wrong in a container)?
- Did a stop-the-world GC pause land on this request? (This is where the trace and `gctrace` complement each other — the trace shows you the pause landed on *this* goroutine; `gctrace` tells you *why* GC ran then.)
- Are goroutines piling up blocked on a channel or a mutex handoff?

A concrete win from a settlement worker: p99 was fine but p99.99 spiked periodically, and no CPU profile explained it — the CPU was busy elsewhere during the spikes. The trace showed batches of goroutines going `Runnable` and sitting there for milliseconds because we'd capped `GOMAXPROCS` below the container's real CPU allotment. The fix was one line (`automaxprocs`), and the tail dropped by TODO: real number ms at p99.99.

**The gotcha:** traces are big and short. A few seconds of a busy service produces tens of megabytes, and the UI gets sluggish past ~10–20s of capture, so take short, targeted traces during the symptom rather than a long "just in case" one. And a trace records *everything* — never leave `/debug/pprof/trace` reachable from outside the pod for the same reasons as the CPU profiler.

---

## 5. Profile-Guided Optimization: making the compiler use your profile

Everything above is about *finding* wins by hand. PGO is about handing your profiling evidence to the compiler so it optimizes for your *actual* production behavior — inlining the functions that are genuinely hot, devirtualizing interface calls it can prove usually resolve to one type, and laying out code for your real branch patterns.

The mechanism is deliberately boring, which is the point. The toolchain looks for a file named `default.pgo` in the **main package's directory**. If it's there, `go build` uses it automatically — no flags, no build tags:

```bash
# 1. Capture a representative CPU profile from production
go tool pprof -proto \
  "http://localhost:6060/debug/pprof/profile?seconds=60" > cpu.pprof

# 2. Drop it in as the default profile next to main
cp cpu.pprof ./cmd/ledger-authz/default.pgo

# 3. Build. PGO is picked up automatically.
go build ./cmd/ledger-authz
```

You can confirm the compiler actually used it:

```bash
go build -pgo=auto -gcflags=-m ./cmd/ledger-authz 2>&1 | grep "PGO"
# ...inlining call ... (cost N) with PGO
```

Typical reported gains from the Go team are in the low single-digit percent range across a whole binary — modest but *free* and compounding, and on a fleet the size of a payments platform a few percent of CPU is real money. In our authz service PGO moved throughput by TODO: real number % and shaved TODO: real number % off CPU at steady state, the biggest single effect being devirtualization of a hot `Validator` interface call PGO could prove resolved to one concrete type on TODO: real number % of calls.

**The gotcha:** the profile has to be *representative*, and it goes stale. A profile captured during a quiet Sunday, or from an old release, teaches the compiler the wrong hot path — at worst PGO optimizes for code that no longer dominates. I treat `default.pgo` as a build artifact with a lifecycle: capture from a canary running the current release under peak-ish load, commit it (or fetch it in CI), and refresh it when the hot path shifts. Iterating on top of a PGO build is stable — the Go team designed it so that a profile from a PGO-optimized binary still produces sensible results, avoiding an oscillation between builds. And PGO is not a substitute for the hand work in sections 1–4: it optimizes the code you have, it doesn't remove the redundant JSON parse. Fix the algorithm first, then let PGO polish.

---

## 6. The workflow, start to finish

Putting it together, this is the loop I actually run:

1. **Start from a symptom, not a hunch.** Latency, memory, or throughput ceiling? The symptom picks the profile.
2. **Capture safely from one canary** over an internal listener, under representative load.
3. **Read it with `top` → `list` → flame graph**, and diff against a baseline to prove the fix.
4. **If it's a waiting/scheduling problem, trace it** rather than profiling it.
5. **Fix the algorithm or allocation**, re-profile, confirm the diff moved.
6. **Once the code is stable, turn on PGO** to lock in compiler-level wins across deploys.

Every step produces *evidence* before you change code, and *evidence* that the change worked. In a payment system where a regression is measured in declined transactions, "I profiled it, here's the before/after diff" is the only acceptable justification for touching the hot path.

---

## Key takeaways

- **Match the profile to the symptom.** CPU for on-CPU cost, heap for memory, block/mutex for waiting and contention. Don't default to CPU when the box is idle.
- **Never expose pprof on your business mux.** Use a separate internal listener and profile one canary, not the whole fleet.
- **`list` is the command people skip** — it turns "this function is hot" into "this *line* is hot." Always diff against a baseline to prove the win.
- **Traces answer "when" and "why stalled," profiles answer "what."** Reach for `go tool trace` when latency is high but CPU is idle — often a `GOMAXPROCS`/scheduling issue.
- **PGO is free, automatic, and cumulative** via `default.pgo` in the main package — but only with a *representative, fresh* profile, and only after you've done the hand optimization it can't do for you.

Profiling and PGO complement the other lenses in this series: GC traces tell you *why* the collector runs, escape analysis tells you *why* something allocates, and profiles tell you *where the time actually goes*. Use all three, and let the evidence — not the Grafana panel and a hunch — decide what you change.

---

## Further reading

- William Kennedy, *"Profiling a Go program"* / the Go performance and profiling series — Ardan Labs blog: https://www.ardanlabs.com/blog
- Go team, *"Profile-guided optimization"* — official docs: https://go.dev/doc/pgo
- Go team, *Diagnostics* (pprof, trace, and runtime profiling reference): https://go.dev/doc/diagnostics
