<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/production-go-38-reading-gc-traces.html -->

# Reading GC Traces Under Load

*Diagnosing garbage-collection pressure with `GODEBUG=gctrace=1` — a trace line decoded field by field, real healthy and pathological traces side by side, and what `GOGC` measurably buys.*

---

There's a latency signature that points inside the runtime rather than in front of it: p99 doubles, the graph goes sawtoothed, and everything that usually causes latency is innocent — CPU isn't pegged, throughput holds, the database is bored. On an allocation-heavy service (every request builds structs, decodes fields, stages entries), that pressure lands on Go's garbage collector, and when the GC runs more often or steals more CPU from your goroutines, latency moves in exactly that sawtooth shape.

The fastest way to confirm the hunch ships with every Go binary and costs almost nothing: the GC trace. This post is about *reading* it — and every trace line in it is real output from a workload you can run yourself: a request-shaped allocator (per "request": a grown `[]byte` plus a 24-entry field map) run in three modes on an Apple M1 Max, Go 1.27, 10 P's. Not escape analysis (that's [the previous post](/blog/posts/production-go-37-escape-analysis-allocations.html) — it decides whether an allocation happens at all), and not `GOMEMLIMIT` pacing. Just: turn on `gctrace`, one line prints per GC cycle, learn to read it like an EKG.

---

## Turning it on without redeploying the world

`gctrace` is a `GODEBUG` setting — no recompile, no imports:

```bash
GODEBUG=gctrace=1 ./authsvc
```

In a containerized deployment you rarely restart the fleet on a whim, so the practical options are a **canary** pod with the env var baked in and a slice of traffic routed to it, or a **load-test** instance replaying captured traffic.

**The gotcha:** `gctrace` writes to **stderr**, one line per GC cycle, unbuffered and unstructured. Under load that's a lot of lines (the churn workload below produced ~690 per *second*). Make sure stderr is captured by your log pipeline, and be ready to `grep '^gc '` because other `GODEBUG` output interleaves on the same stream. It also can't be toggled at runtime — it's read once at startup — so treat it as a deploy-time decision, not an incident knob.

---

## Anatomy of one trace line

A real line from the steady-churn workload:

```text
gc 25 @0.036s 6%: 0.18+0.62+0.059 ms clock, 1.8+0.076/0.069/0.001+0.59 ms cpu,
      3->4->0 MB, 4 MB goal, 0 MB stacks, 0 MB globals, 10 P
```

Field by field:

- **`gc 25`** — cycle number since process start. On its own, just a counter; its *rate of increase* is the first thing to look at.
- **`@0.036s`** — wall-clock seconds since start. Diff two consecutive lines and you have the interval between collections — the single most diagnostic number in the trace. (25 cycles in 36ms: this workload collects every ~1.4ms.)
- **`6%`** — cumulative share of CPU spent in GC since startup. It drifts slowly; a climb over a window is the alarm.
- **`0.18+0.62+0.059 ms clock`** — the three phases as wall-clock: **sweep-termination + mark/scan + mark-termination**. The outer two are stop-the-world; the middle is the big concurrent mark. STW here: 0.18ms and 0.059ms — tiny, as the modern collector promises. If the outer numbers grow, that's direct tail latency.
- **`1.8+0.076/0.069/0.001+0.59 ms cpu`** — the same work as CPU time across all P's: what the collector *stole* from your goroutines. The middle triple is **mark-assist / background-mark / idle-mark** — assist is the one to watch (more below).
- **`3->4->0 MB`** — heap at GC start, heap when marking finished, **live** heap at cycle end. `3->4->0` says: the heap grew to 3–4 MB of almost pure garbage, and *nothing* survived. That zero is the signature of healthy short-lived allocation.
- **`4 MB goal`** — the pacer's heap-size target for triggering the *next* cycle, derived from live heap and `GOGC`. Watching `goal` move tells you whether the working set is stable or creeping.
- **`0 MB stacks, 0 MB globals`** — scan work for goroutine stacks and package globals; stable unless goroutine count grows.
- **`10 P`** — `GOMAXPROCS` the collector had to work with.

Two derived quantities aren't printed — you compute them:

- **GC frequency** = `1 / Δ@Ts` between lines.
- **Allocation rate** ≈ heap growth between cycles ÷ interval. For the workload above, `MemStats.TotalAlloc` confirms it directly: **13.9 GB allocated in 8 seconds — ~1.7 GB/s** of short-lived garbage. That number is the root cause behind almost every GC problem.

---

## What healthy-but-churning looks like

The steady workload (8 goroutines allocating request-shaped garbage flat out, retaining nothing) produces a trace that is *regular* — and regularity is most of what "healthy" means:

```text
gc 20 @0.029s 6%: ... 3->3->0 MB, 4 MB goal, ... 10 P
gc 25 @0.036s 6%: ... 3->4->0 MB, 4 MB goal, ... 10 P
    ...8 seconds later...
done: numgc=5514  gc_cpu_frac=0.071
```

The tells, each visible above:

- **Stable interval** — cycles fire on a constant ~1.4ms cadence, not in bursts.
- **Flat live heap** — `H2` pinned at 0 MB cycle after cycle: everything allocated dies young, which Go's collector handles cheaply.
- **Stable goal** — 4 MB forever; the pacer isn't chasing anything.
- **Tiny STW** — sub-0.2ms outer phases throughout.

But one number says this service still has a problem: **5,514 collections in 8 seconds, costing 7.1% of all CPU.** Nothing is leaking — the GC is simply sprinting to keep up with a 1.7 GB/s allocation firehose against a 4 MB heap. That's the *frequent-but-cheap* disease: no single cycle hurts, and the collector quietly taxes every core. Remember the shape; the fix comparison below is measured against it.

---

## What a leak looks like

Same workload, one change: each request also appends its buffer to a global slice — an unbounded "audit log." Real trace, sampled:

```text
gc 10 @0.042s 1%: ...   6->7->3 MB,   7 MB goal, ... 10 P
gc 20 @0.162s 0%: ...  25->25->14 MB,  25 MB goal, ... 10 P
gc 30 @0.582s 0%: ...  90->90->52 MB,  92 MB goal, ... 10 P
gc 40 @2.098s 0%: ... 328->328->189 MB, 332 MB goal, ... 10 P
```

Every healthy tell inverts, and you can read the disease straight off the columns: **live heap (`H2`) climbing** 3 → 14 → 52 → 189 MB under steady traffic — something is accumulating. **`goal` chasing it** upward, 7 → 25 → 92 → 332 MB, because the pacer always targets a multiple of live. **Intervals *stretching*** (0.04s → 0.16s → 0.58s → 2.1s between samples) as the growing goal gives each cycle more runway — which is why "GC is running less often" is *not* reassuring on its own. And the mark CPU numbers growing with the live set, because every surviving megabyte is future scan work for every future cycle.

A steadily rising `H2` under steady load is the classic shape of a leak or an unbounded cache, and no GC tuning fixes it — the next step is the heap profiler (`go tool pprof -alloc_space`, or `-inuse_space` for what's retained), which names the call site doing the accumulating.

**The gotcha:** high GC *frequency* and high GC *CPU* are different diseases, and the two traces above let you tell them apart at a glance. Frequent-but-cheap with a flat live heap = allocation churn — fix by allocating less, or give the heap room with `GOGC`. Climbing live heap = retention — fix the leak; more heap room just delays the wall. And when allocation outruns the background collector entirely, the runtime drafts *your* goroutines into **mark assist** (the `x` in the `x/y/z` CPU triple) — that cost lands on individual unlucky requests, which is precisely why GC pain shows up at p99 before it shows up in the mean.

---

## What `GOGC` measurably buys

`GOGC` is the pacer's setpoint: at the default `100`, the next GC triggers when the heap is 100% larger than the live set. Raise it and GC runs less often at the cost of a bigger heap:

```go
import "runtime/debug"

// Programmatic — the honest place to put it, next to a comment explaining why.
debug.SetGCPercent(400) // trade heap for fewer GC cycles on this service
```

```bash
# Or via env, no recompile:
GOGC=400 ./authsvc
```

Here's the same steady-churn workload at both settings — same machine, same 8 seconds:

| | `GOGC=100` | `GOGC=400` |
|---|---|---|
| GC cycles | 5,499 | 1,793 (−67%) |
| GC share of CPU | 7.1% | 2.4% |
| Heap goal | 4 MB | 16 MB |
| Work done (bytes allocated) | 13.9 GB | **25.3 GB (+82%)** |

The last row is the one worth staring at. Freeing the workers from GC taxation — fewer cycles, less mark assist — meant they got **82% more actual work done** in the same wall-clock time, for the price of 12 MB of heap. When the diagnosis is frequent-but-cheap churn, `GOGC` is a spectacular lever.

**The gotcha:** don't tune `GOGC` blind and call it fixed. You've traded memory for CPU, and pushed closer to the container's memory limit — check the trade is affordable, and confirm the *trace* after the change: frequency down, GC CPU down, assist near zero, live heap still flat. If live heap is rising, you have the other disease, and no pacer setting will save you. (For bounding total memory against a cgroup limit, `GOMEMLIMIT` — a ceiling, not a ratio — is its own topic and its own post.)

The priority order stands regardless: **allocate less first** (pool churny buffers, presize maps and slices, keep `fmt` boxing off hot paths — the [escape-analysis post](/blog/posts/production-go-37-escape-analysis-allocations.html) measures those fixes), *then* tune the pacer with what remains.

---

## A reading checklist

| Symptom in the trace | Likely cause | First action |
|---|---|---|
| `@Ts` deltas tiny and constant, `H2` flat | Allocation churn vs. small heap | Reduce allocs; consider raising `GOGC` |
| Cumulative `%` climbing over a window | Collector stealing CPU | Cut allocation rate; profile `-alloc_space` |
| Mark-assist (`x`) non-trivial | Allocating faster than background mark | Reduce allocs — more heap won't fix it |
| `H2` rising steadily | Leak or unbounded cache | Heap profile; find the retained objects |
| `goal` far above live, GC still frequent | `GOGC` too low for the workload | Raise `GOGC` (if memory allows) |

---

## Key takeaways

- **`gctrace` is free and always available.** One env var, one line per cycle to stderr, no recompile — the first thing to reach for when latency looks runtime-shaped.
- **Read the derived numbers, not just the printed ones.** GC frequency (Δ`@Ts`) and allocation rate aren't in the line; you compute them, and the diagnosis lives there. The demo workload's 1.7 GB/s allocation rate explains every other number it produced.
- **Churn and retention are different diseases with opposite trace shapes.** Flat `H2` + 1.4ms intervals = churn; climbing `H2` + stretching intervals + chasing goal = leak. The same trace distinguishes them in ten lines.
- **Mark-assist is the tail-latency villain.** When your goroutines get drafted to mark, the cost lands on individual requests — the p99 shape with a calm mean.
- **`GOGC` is a real lever with a measurable price.** On the churn workload: −67% cycles, GC CPU 7.1%→2.4%, +82% useful work, for 12 MB of heap. Allocate less first; tune second; re-read the trace to confirm — and never invent the numbers, measure them.

---

## Further reading

- **"Garbage Collection In Go: Part II - GC Traces"** — Ardan Labs, https://www.ardanlabs.com/blog

---

*All trace lines and numbers: a request-shaped allocation workload (8 worker goroutines; per request a grown `[]byte` + 24-entry map) on an Apple M1 Max, Go 1.27, 8-second runs. Machine-specific in absolute terms; the shapes are universal.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-08-02
Canonical: https://pratikdhanave.com/blog/posts/production-go-38-reading-gc-traces.html
Attribution: please link the canonical URL when citing or quoting this post.
