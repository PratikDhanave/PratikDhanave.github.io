<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/production-go-36-gomaxprocs-kubernetes.html -->

# CPU Limits and GOMAXPROCS in Kubernetes

*Why a Go service can be provisioned with plenty of CPU and still run like it's starved — the CFS quota model, a measured reproduction of the throttling mismatch, and the fixes.*

---

There's a production failure signature every Go-on-Kubernetes team eventually meets: p99 latency falls apart while the CPU dashboard shows modest, healthy utilization. The service isn't out of CPU — it's being *frozen* in bursts by the kernel, because the Go runtime's idea of how wide it may run doesn't match the CPU quota the container actually has.

This post explains the mechanism — and then, instead of asking you to trust a war story, **reproduces it in a real cgroup-limited container and measures it**. The experiment runs a static Go binary inside Docker's Linux VM with `--cpus=1`; numbers are from those runs. One of the results genuinely surprised me, which is the kind of thing that only happens when you run the experiment instead of writing the fable.

---

## How the Go runtime picks GOMAXPROCS

`GOMAXPROCS` is the number of OS threads allowed to execute Go code *simultaneously* — the width of the runtime scheduler, the number of P's in the [G-M-P model](/blog/posts/production-go-22-scheduler-under-contention.html). For most of Go's history the startup default was simply the machine's logical CPU count, the same number `runtime.NumCPU()` returns:

```go
package main

import (
	"fmt"
	"runtime"
)

func main() {
	// Pre-1.25, on a 64-core node these both print 64 —
	// regardless of what the container is actually allowed to use.
	fmt.Println("NumCPU:    ", runtime.NumCPU())
	fmt.Println("GOMAXPROCS:", runtime.GOMAXPROCS(0)) // 0 = query, don't set
}
```

**The gotcha:** `runtime.NumCPU()` reads the *node's* CPU count, not your container's CPU limit, and in Kubernetes those two numbers are almost never the same. A pod with a 2-core limit scheduled onto a 64-core node got a scheduler built to run 64-wide on hardware it was never allowed to touch.

Go 1.25 made the runtime cgroup-aware, and the default now accounts for the CFS limit on Linux — with a wrinkle the experiment below measures. If you're pinned to an older toolchain, you own this problem yourself, and everything below applies in full.

---

## The Linux CFS quota/period model

Kubernetes doesn't give a container N dedicated cores. A CPU *limit* becomes CFS bandwidth control, which has two knobs:

- **`cpu.cfs_period_us`** — an accounting window, 100ms by default.
- **`cpu.cfs_quota_us`** — how much CPU *time* the cgroup may consume per window.

A limit of `1` means 100ms of CPU time per 100ms window; a limit of `2` means 200ms; and so on. The critical word is **time, not cores**. 200ms of quota can be spent by two threads running flat-out all window — or by twenty threads that collectively burn it in the first 10ms and then get frozen, *all of them*, for the remaining 90.

| CPU limit | CFS quota / 100ms period | Core-equivalent |
|---|---|---|
| `500m` | 50,000 µs | 0.5 |
| `1` | 100,000 µs | 1 |
| `2` | 200,000 µs | 2 |
| `4` | 400,000 µs | 4 |

The quota is a budget, and `GOMAXPROCS` determines how fast you spend it. A runtime running 64-wide against a 2-core quota drains the whole window's budget in ~3ms of wall-clock, then the kernel deschedules the entire cgroup until the next window. Your service sprints, freezes, sprints, freezes — a sawtooth. Averaged over a minute the CPU graph looks calm; any request in flight when the freeze lands eats the stall in its latency.

---

## Measured: the mismatch in a real cgroup

The demo binary runs 4 CPU-bound workers (each repeatedly burning a 5ms slice and timing how long the slice *actually* took), reads the cgroup's own `cpu.stat` throttling counters before and after, and runs inside `docker run --cpus=1` — a genuine CFS quota of 100ms/100ms on a 4-CPU Linux VM. Three configurations, real output:

```text
# pre-1.25 default on a 4-core node: width = NumCPU = 4
go=go1.27.3 NumCPU=4 GOMAXPROCS=4 cgroup_cpu="100000 100000"
ops=1644 (274/s)  op p50=5ms  p99=75.072ms  max=84ms
throttled_periods=60/60  throttled_time=15585ms

# width matched to the quota
go=go1.27.3 NumCPU=4 GOMAXPROCS=1 cgroup_cpu="100000 100000"
ops=1465 (244/s)  op p50=5ms  p99=65.853ms  max=69ms
throttled_periods=18/60  throttled_time=3ms

# Go 1.27's cgroup-aware default, no override
go=go1.27.3 NumCPU=4 GOMAXPROCS=2 cgroup_cpu="100000 100000"
ops=1488 (248/s)  op p50=5ms  p99=82.06ms  max=95ms
throttled_periods=60/60  throttled_time=5926ms
```

Three findings, in increasing order of interest:

1. **The headline number isn't throughput — it's frozen time.** At width 4, the cgroup was throttled in **60 of 60 periods**, accumulating **15.6 seconds** of frozen thread-time in a 6-second run (4 threads, each frozen ~65% of the time). Matched at width 1: **3 milliseconds**. Same quota, same work, three-and-a-half orders of magnitude difference in how long the kernel held the process frozen. Every one of those freezes lands mid-request in a real service — and it lands on *everything* in the cgroup at once, including goroutines holding locks. One freeze behind a held lock becomes a convoy.
2. **Throughput barely moves.** 274/s vs 244/s vs 248/s — the quota caps total CPU either way. This is exactly why the dashboard lies: utilization-against-limit looks the same in all three configurations. You cannot see this failure in average CPU; you can only see it in `cpu.stat` and in your tail latency.
3. **The surprise: Go 1.27's cgroup-aware default picked `GOMAXPROCS=2` on a 1-CPU quota — and still throttled every period.** The new default enforces a floor of 2, a deliberate liveness trade-off. It cut frozen time by ~62% versus the old default (5.9s vs 15.6s), which is a big improvement — but it is not zero, and on quota-of-1 containers an explicit `GOMAXPROCS=1` measurably out-behaves the modern default. "Upgrade and forget" is *mostly* true; for 1-CPU pods it's worth checking.

An honest caveat on scope: this workload is deliberately saturated, which is where the mismatch is most visible. A service running well below its quota with smooth arrivals may never throttle even when mismatched — the pathology needs the budget to actually run out within a window, which bursts, saturation, or a GC cycle (background marking uses *all* the P's at once) will do. That's also why the classic incident report says "it only happens during the busy window."

---

## Diagnosing it in production

The tell is the gap between three numbers: your CPU limit, the runtime's width, and the CFS throttling counters — the same counters the demo reads.

**1. Log the runtime's view at startup.** Cheap, and it settles the argument immediately:

```go
slog.Info("runtime sizing",
	"num_cpu", runtime.NumCPU(),
	"gomaxprocs", runtime.GOMAXPROCS(0),
	"cpu_limit_cores", cpuLimitFromCgroup(), // helper below
)
```

`num_cpu=64 gomaxprocs=64 cpu_limit_cores=2` in a pod's logs is the smoking gun.

**2. Watch the throttling ratio.** cAdvisor exposes the same cgroup counters:

```promql
# Fraction of periods in which the container was throttled, per pod
rate(container_cpu_cfs_throttled_periods_total{pod=~"authz-.*"}[5m])
  /
rate(container_cpu_cfs_periods_total{pod=~"authz-.*"}[5m])
```

Materially above zero on a latency-sensitive service means you're being frozen. The companion `container_cpu_cfs_throttled_seconds_total` is the "15.6 seconds" from the experiment — correlate its spikes with your p99 graph.

**3. Separate the two causes.** Throttling with genuinely saturated CPU means under-provisioned — raise the limit. Throttling with *low average* CPU and an oversized `GOMAXPROCS` is the runtime mismatch — a config fix, not a capacity fix. The startup log line distinguishes them in seconds.

---

## The fix

Make the runtime's width match the CPU the container may actually use.

### Option A: uber-go/automaxprocs

The pragmatic answer for pre-1.25 toolchains — import it for its side effect:

```go
import _ "go.uber.org/automaxprocs" // sets GOMAXPROCS from the CFS quota at init
```

On a 2-core-limit pod it logs `maxprocs: Updating GOMAXPROCS=2` and the runtime stops running node-wide.

**The gotcha:** it rounds the quota *down* with a floor of 1 — `1500m` becomes `GOMAXPROCS=1`, quietly stranding half a core; and it reads the quota once at startup, so an in-place vertical resize isn't picked up until restart. Prefer whole-core limits for latency-critical pods.

### Option B: set it yourself from the limit

Zero dependencies, fully auditable — surface the limit via the downward API:

```yaml
env:
  - name: CPU_LIMIT
    valueFrom:
      resourceFieldRef:
        resource: limits.cpu
        divisor: "1" # whole cores; Kubernetes rounds a millicore limit up
```

```go
func configureGOMAXPROCS() {
	raw := os.Getenv("CPU_LIMIT")
	if raw == "" {
		return // fall back to the runtime default
	}
	limit, err := strconv.Atoi(raw)
	if err != nil || limit < 1 {
		return
	}
	prev := runtime.GOMAXPROCS(limit)
	slog.Info("pinned GOMAXPROCS to CPU limit", "gomaxprocs", limit, "previous", prev)
}
```

Or read the cgroup directly — v2 puts both numbers in one file (this is the helper the demo itself uses):

```go
// cgroup v2: /sys/fs/cgroup/cpu.max holds "<quota> <period>", e.g. "200000 100000".
// A quota of "max" means unlimited — fall back to NumCPU in that case.
func cpuLimitFromCgroup() int {
	b, err := os.ReadFile("/sys/fs/cgroup/cpu.max")
	if err != nil {
		return runtime.NumCPU()
	}
	fields := strings.Fields(string(b))
	if len(fields) != 2 || fields[0] == "max" {
		return runtime.NumCPU()
	}
	quota, err1 := strconv.Atoi(fields[0])
	period, err2 := strconv.Atoi(fields[1])
	if err1 != nil || err2 != nil || period == 0 {
		return runtime.NumCPU()
	}
	cores := quota / period // integer floor
	if cores < 1 {
		cores = 1
	}
	return cores
}
```

**The gotcha:** don't hand-code cgroup v1 paths (`cpu.cfs_quota_us` / `cpu.cfs_period_us`) unless you know your nodes are v1 — the layouts differ, and getting it wrong silently returns the wrong number. That drudgery is what `automaxprocs` exists to handle; roll your own only when you need custom rounding (round *up* for fractional limits) or a dependency-free build.

### A note on requests vs. limits

The cleanest way to avoid throttling is to question whether latency-critical services need a CPU *limit* at all. A *request* guarantees a scheduling floor; a *limit* imposes the CFS ceiling that causes freezing. Many teams set requests and drop limits for latency-sensitive services, removing the quota mechanism entirely — an org-level policy call with real trade-offs around bin-packing and isolation. But if you keep limits, the runtime's width must match them.

---

## Key takeaways

- **Kubernetes CPU limits are a time budget, not cores.** Spend the window's budget early and the kernel freezes the *entire cgroup* — measured: 60/60 windows throttled, 15.6s of frozen thread-time in a 6s run at width 4 on a 1-CPU quota.
- **Throughput hides it; tail latency and `cpu.stat` reveal it.** All three measured configs delivered ~250 ops/s against the same quota; they differed by 5000× in frozen time.
- **Pre-1.25 Go defaults to node width.** `runtime.NumCPU()` reports the machine, not the cgroup — on big nodes with small limits, that's the whole incident.
- **Go 1.25+'s cgroup-aware default has a floor of 2** — measured on a quota of 1, it still throttled every period (though 62% less frozen time than the old default). For 1-CPU pods, set `GOMAXPROCS=1` explicitly and measure.
- **Diagnose with three numbers:** the limit, `runtime.GOMAXPROCS(0)`, and the throttled-periods ratio. Fix with `automaxprocs`, the downward API, or `cpu.max` — or drop limits for latency-critical pods and rely on requests.

---

## Further reading

- Ardan Labs — ["Kubernetes CPU Limits and Go"](https://www.ardanlabs.com/blog) — the canonical deep walk through CFS quota mechanics and the GOMAXPROCS interaction.

---

*Measurements: static Go 1.27 binary in `docker run --cpus=1` (Docker Desktop Linux VM, 4 CPUs, Apple M1 Max host); cgroup v2 counters read from inside the container before/after each 6-second run. Absolute numbers are environment-specific; the ratios — and the 60/60 throttled windows — are the lesson.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-07-31
Canonical: https://pratikdhanave.com/blog/posts/production-go-36-gomaxprocs-kubernetes.html
Attribution: please link the canonical URL when citing or quoting this post.
