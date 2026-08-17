# Reading GC Traces Under Load

*How I diagnosed garbage-collection pressure on a live payment-authorization service using `GODEBUG=gctrace=1` — reading a trace line field by field, telling healthy from pathological, and turning the numbers into fewer allocations and the right GOGC.*

---

The page came in at the tail of a weekday settlement window: p99 authorization latency on our card-present service had roughly doubled, and the graph was sawtoothed rather than flat. CPU wasn't pegged, throughput was holding, the database was bored. Everything that usually causes latency was innocent — the signature of a problem inside the runtime rather than in front of it.

On a high-TPS payment service, the runtime *is* production. Every authorization allocates — request structs, decoded ISO 8583 fields, the ledger entries we stage before commit — and all of that pressure lands on Go's garbage collector. When the GC starts running more often, or stealing more CPU from your own goroutines to keep up, latency moves in exactly the sawtooth shape I was staring at. The fastest way to confirm that hunch without attaching a profiler to a live payment box ships with every Go binary and costs almost nothing: the GC trace.

This post is about *reading* that trace. Not escape analysis (that decides whether an allocation happens at all — a separate post), and not `GOMEMLIMIT` pacing (I have a separate write-up on the soft memory limit). Just: you turn on `gctrace`, a line prints every GC cycle, and you learn to read it like an EKG.

---

## Turning it on without redeploying the world

`gctrace` is a `GODEBUG` setting. You don't recompile, you don't import anything — you set an environment variable and every garbage collection writes one line to standard error:

```bash
GODEBUG=gctrace=1 ./authsvc
```

In a containerized fintech deployment you rarely restart the whole fleet on a whim, so the practical options are:

- Bake `GODEBUG=gctrace=1` into a **canary** pod's env and route a slice of traffic to it — production-representative traces without touching the fleet.
- Set it on a **load-test** instance replaying captured authorization traffic, which is where I did most of this.

**The gotcha:** `gctrace` writes to **stderr**, one line per GC cycle, unbuffered and unstructured. Under load that's a lot of lines. Make sure stderr is captured by your log pipeline (not dropped), and be ready to `grep '^gc '` because the runtime interleaves other `GODEBUG` output on the same stream. It also can't be toggled at runtime — it's read once at startup — so treat it as a deploy-time decision, not a knob you flip during an incident.

---

## Anatomy of one trace line

Here is the field *layout* of a single `gctrace` line. I've marked every value that would be a real measurement as a TODO — the shape is what matters, and I won't invent numbers for a system I'm describing from memory:

```text
gc 1 @0.000s 0%: 0.000+0.000+0.000 ms clock, 0+0.000/0.000/0.000+0.000 ms cpu, 0->0->0 MB, 0 MB goal, 0 MB stacks, 0 MB globals, 0 P
```

Read against that template, the fields of a real line decode as follows:

```text
gc <N> @<T>s <P>%: <a>+<b>+<c> ms clock, <w>+<x>/<y>/<z>+<v> ms cpu, <H0>-><H1>-><H2> MB, <G> MB goal, <S> MB stacks, <GL> MB globals, <procs> P
```

- **`gc N`** — the cycle number since process start. On its own it's just a counter; its *rate of increase* is the first thing I look at.
- **`@Ts`** — wall-clock seconds since the program started. Diff two consecutive lines' timestamps and you have the interval between collections — the single most diagnostic number in the whole trace.
- **`P%`** — the percentage of total CPU spent in the GC since startup. This is cumulative, so it drifts slowly; a sudden climb over a window is the alarm.
- **`a+b+c ms clock`** — the three phases as wall-clock durations: **sweep-termination + mark/scan + mark-termination**. The outer two are stop-the-world; the middle is the big concurrent mark phase. On the modern collector STW is tiny — if the outer numbers grow, that hits your tail latency directly.
- **`w+x/y/z+v ms cpu`** — the same work as CPU-time across all Ps: how much the collector is *stealing* from your request-serving goroutines. The `x/y/z` triple is mark-assist / background-mark / idle-mark.
- **`H0->H1->H2 MB`** — heap size **before** the GC started, **after** marking finished, and the **live** heap at cycle end. `H0` is where the heap grew to before this cycle triggered; `H2` is what actually survived.
- **`G MB goal`** — the heap-size target the pacer wants to hit before the *next* GC fires. This is derived from live heap and `GOGC`, and watching `goal` move over time tells you whether your working set is stable or creeping.
- **`S MB stacks`** — the memory scanned for goroutine stacks this cycle. Modern Go emits it right after `goal`; on a service with a stable goroutine count it barely moves, and a climbing value points at goroutine growth.
- **`GL MB globals`** — the memory scanned for package-level globals, also emitted between `goal` and `P`. It's essentially constant for a given binary, so it's mostly a fixed floor rather than something you tune.
- **`procs P`** — the number of processors (`GOMAXPROCS`) the collector had to work with.

The two derived quantities I actually reason about aren't printed — you compute them:

- **GC frequency** = `1 / (Δ@Ts between lines)`. Cycles per second.
- **Allocation rate** ≈ `(H0_next - H2_prev) / (Δ@Ts)`. How fast you filled the heap from the last cycle's live set to the next trigger — your allocation firehose in MB/s, and the root cause behind almost every GC problem.

---

## What healthy looks like

A well-behaved payment service under steady load produces a boring trace, and boring is the goal:

```text
gc <N>   @<T>s   <P>%: ... ms clock, ... ms cpu, <H0>-><H1>-><H2> MB, <G> MB goal, <procs> P
gc <N+1> @<T+k>s <P>%: ... ms clock, ... ms cpu, <H0>-><H1>-><H2> MB, <G> MB goal, <procs> P
```

The tells of health:

- **Stable interval.** `@Ts` deltas are roughly constant — GC fires on a regular cadence, say once every `TODO: real interval` seconds, not in bursts.
- **Flat live heap.** `H2` (the live number) barely moves cycle to cycle. Your working set is steady; you're allocating garbage that dies young, which is exactly what the generational-ish behavior of Go's collector handles cheaply.
- **Low, flat `P%`.** Cumulative GC CPU sits at some small percentage — for our service, healthy was around `TODO: real GC CPU %` — and doesn't climb.
- **Tiny STW.** The outer `clock` phases stay sub-millisecond; `TODO: real STW pause` was normal.
- **Goal comfortably above live.** `goal` sits a predictable multiple above `H2` — with the default `GOGC=100`, goal ≈ 2× live — and stays put.

When those five hold, the GC is not your problem — go look elsewhere.

---

## What pathological looks like

My sawtooth incident was the opposite of every bullet above. Three signals fired together:

**1. GC frequency climbing.** The `@Ts` deltas were shrinking — collections were firing every `TODO: real bad interval` instead of the usual cadence. More GCs per second means more mark work, more assist, more contention.

**2. `P%` walking up and to the right.** Cumulative GC CPU was climbing over the window. The collector was eating a growing slice of the cores I needed to authorize transactions. On a service where each core is serving requests, GC CPU is latency you can't see in a flame graph unless you know to look.

**3. Rising `goal` with rising live heap.** `H2` crept up cycle over cycle and `goal` chased it. A steadily rising live heap under steady traffic means something is accumulating — the classic shape of a slow leak or an unbounded cache.

The mechanism behind the sawtooth: as allocation rate rose, the pacer triggered GC earlier and earlier to avoid overshooting `goal`. Each early trigger conscripted goroutines into **mark assist** — when you allocate faster than the background collector can keep up, the runtime makes *your* allocating goroutine do mark work before it's allowed to allocate. That assist time is charged directly to the unlucky request, which is precisely why the pain showed up at p99 and not in the mean. The `x` field (mark-assist CPU) in the `cpu` group was the smoking gun: non-trivial and growing, where healthy traces keep it near zero.

**The gotcha:** high *GC frequency* and high *GC CPU* are different diseases with different cures, and the trace lets you tell them apart. Frequent GC with low per-cycle cost usually means a high allocation rate against a small heap — you're churning short-lived garbage. High GC CPU with heavy mark-assist means the collector can't keep pace with allocation and is drafting your goroutines to help. Frequent-but-cheap you often fix by allocating less *or* by giving the heap more room (`GOGC`); assist-heavy you fix by cutting the allocation rate, because more heap room alone just makes each mark phase scan more.

---

## Connecting the trace back to allocation rate

Every knob downstream is really a proxy for one number: **how many bytes per second you allocate**. The trace hands you that number if you do the subtraction. In my case the derived allocation rate was `TODO: real MB/s`, and the live heap (`H2`) was slowly rising, which pointed me at *what* was being allocated.

I confirmed it with the allocation profiler, the natural next step once the trace points at allocation:

```bash
go tool pprof -alloc_space http://<canary>:6060/debug/pprof/heap
```

The offender was mundane and typical of payment code: for every authorization we built the response by growing a `[]byte` and a `map[string]string` of ISO 8583 fields from zero, plus a fresh `bytes.Buffer` per log line. It *legitimately* escaped to the heap because it outlived the call. Multiplied across `TODO: real TPS`, that's the firehose.

The fixes were the boring, durable kind:

```go
// A per-worker buffer pool removes the steady-state Buffer churn.
var bufPool = sync.Pool{
	New: func() any { return new(bytes.Buffer) },
}

func encodeAuthResponse(dst *bytes.Buffer, r *AuthResult) {
	dst.Reset()
	// ... write fields into the pooled buffer ...
}

// Presize the field map to its known cardinality so it doesn't rehash-grow.
fields := make(map[string]string, 24)

// Reuse a request-scoped slice instead of appending from nil each time.
buf := r.scratch[:0]
```

`sync.Pool` is exactly right for the buffer case: objects expensive to churn, safe to reuse, lifetime of a single request. Presizing the map kills incremental rehash allocations. Reusing a request-scoped scratch slice removes a whole class of `append`-from-nil growth. Individually small; against a payment firehose, decisive.

---

## Turning the trace into action

The trace is a diagnosis, not a prescription. Once it names the disease, the response falls into three tiers:

**1. Allocate less (almost always the right first move).** Pool reusable buffers, presize slices and maps, avoid per-request temporaries, keep values on the stack when they don't need to escape. This attacks the root — allocation rate — so it helps *both* the frequency and the assist problems, and unlike the other tiers it costs no memory headroom.

**2. Give the collector more room with `GOGC`.** `GOGC` is the pacer's setpoint: at the default `100`, the next GC targets a heap 100% larger than the live set. Raise it and GC runs less often (fewer cycles, less total CPU) at the cost of a bigger heap; lower it and you trade RAM for more frequent collection. You can set it two ways:

```go
import "runtime/debug"

// Programmatic — the honest place to put it, next to a comment explaining why.
debug.SetGCPercent(200) // trade heap for fewer GC cycles on this service
```

```bash
# Or via env, no recompile:
GOGC=200 ./authsvc
```

Raising `GOGC` was the right lever for the *frequent-but-cheap* half of my problem: doubling it roughly halved GC frequency and dropped cumulative GC CPU, buying back tail latency at the cost of `TODO: real extra heap MB` of resident memory — a trade a payment box with headroom is happy to make. It is **not** a fix for a genuine leak; if live heap keeps rising, a bigger `GOGC` just delays the wall.

**3. Bound total memory with `GOMEMLIMIT`.** Go's soft memory limit lets the runtime run GC harder as you approach a ceiling — invaluable in a container with a hard cgroup limit. It's a different mental model from `GOGC` (a limit, not a ratio) and interacts with the pacer in ways worth understanding first. I've written that up separately — see my post on `GOMEMLIMIT` and soft GC pacing — rather than repeat it here.

**The gotcha:** don't tune `GOGC` blind and call it fixed. If you raise `GOGC` without cutting allocation, you've traded latency for memory and pushed yourself closer to the OOM killer — on a payment box that's a worse incident than the one you started with. Always confirm the trace *after* the change: frequency down, `P%` down, mark-assist near zero, live heap flat. If live heap is still rising, you have a leak, and no pacer setting will save you — go back to the allocation profile.

---

## A reading checklist

| Symptom in the trace | Likely cause | First action |
|---|---|---|
| `@Ts` deltas shrinking | High allocation rate vs. heap size | Reduce allocs; consider raising `GOGC` |
| `P%` climbing over a window | Collector stealing CPU (assist) | Cut allocation rate; profile `-alloc_space` |
| Mark-assist (`x`) non-trivial | Allocating faster than background mark | Reduce allocs — more heap won't fix it |
| `H2` (live) rising steadily | Leak or unbounded cache/accumulation | Heap profile; find the retained objects |
| `goal` far above live, GC still frequent | `GOGC` too low for the workload | Raise `GOGC` (if memory allows) |

---

## Key takeaways

- **`gctrace` is free and always available.** One `GODEBUG` env var, one line per cycle to stderr, no recompile. It's the first thing to reach for when latency looks runtime-shaped.
- **Read the derived numbers, not just the printed ones.** GC *frequency* (Δ`@Ts`) and *allocation rate* (heap growth ÷ interval) aren't in the line — you compute them, and they're where the diagnosis lives.
- **Frequency and CPU are different diseases.** Frequent-but-cheap GC often yields to more heap (`GOGC`); assist-heavy GC only yields to fewer allocations.
- **Mark-assist is the tail-latency villain.** When your own goroutines are drafted to mark, the cost lands on individual requests — exactly the p99 shape.
- **Allocate less first, tune second.** `GOGC` and `GOMEMLIMIT` buy time and trade memory; cutting allocation rate fixes the root. Re-read the trace to confirm the change did what you expected — and never invent the numbers, measure them.

---

## Further reading

- **"Garbage Collection In Go: Part II - GC Traces"** — Ardan Labs, https://www.ardanlabs.com/blog
