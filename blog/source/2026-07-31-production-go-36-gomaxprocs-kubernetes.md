# CPU Limits and GOMAXPROCS in Kubernetes

*A high-TPS payment service that was provisioned for plenty of CPU but ran like it was starved — and the one-line runtime mismatch behind it.*

---

The pager went off during a routine settlement window. Our authorization service — the Go process that sits in the hot path of every card transaction, decrementing balances against the ledger and emitting settlement events — was blowing its p99 latency SLO. Not by a little. Requests that normally cleared in **`TODO: real number`** ms were tailing out past **`TODO: real number`** ms, and the queue depth in front of the service was climbing. Throughput had cratered even though the fleet was, on paper, barely warm: CPU utilization on the dashboard sat around **`TODO: real number`%**, nowhere near the limit.

That last detail is the whole story. A service showing modest CPU usage while its latency falls apart is the classic signature of CFS throttling colliding with Go's default `GOMAXPROCS`. We had pods requesting **`TODO: real number`** cores, a `GOMAXPROCS` that thought it owned the whole node, and a kernel scheduler quietly parking our goroutines for milliseconds at a time. This post is how we found it and how we fixed it.

---

## How the Go runtime picks GOMAXPROCS

`GOMAXPROCS` is the number of OS threads the Go runtime will allow to execute Go code *simultaneously*. It's the width of the runtime's scheduler — how many P's (processors, in the runtime's terminology) exist to run goroutines in parallel. Set it to 8 and up to 8 goroutines run Go code at the same instant; the rest wait their turn.

For most of Go's history, when your program started, the runtime called `GOMAXPROCS` to whatever the operating system reported as the machine's logical CPU count — the same number `runtime.NumCPU()` returns. On a bare-metal box or a VM that's exactly right: the OS's view of CPUs matches the hardware you actually get to use.

```go
package main

import (
	"fmt"
	"runtime"
)

func main() {
	// On a 64-core node, both of these print 64 —
	// regardless of what the container is actually allowed to use.
	fmt.Println("NumCPU:    ", runtime.NumCPU())
	fmt.Println("GOMAXPROCS:", runtime.GOMAXPROCS(0)) // 0 = query, don't set
}
```

**The gotcha:** `runtime.NumCPU()` reads the *node's* logical CPU count, not your container's CPU limit. In Kubernetes those two numbers are almost never the same. Our authorization pods landed on nodes with **`TODO: real number`** logical cores, so the runtime spun up that many P's — while the pod's CPU limit entitled it to a small fraction of that. The scheduler was built to run wide on hardware the container was never allowed to touch.

(Go 1.25 made the runtime cgroup-aware and this default now accounts for the CFS limit on Linux. If you're pinned to an older toolchain — which plenty of production fintech services are — you own this problem yourself, and everything below still applies.)

---

## The Linux CFS quota/period model

To see why that's a problem, you have to look at how Kubernetes actually enforces a CPU *limit*. It does not hand your container N dedicated cores. It uses the Completely Fair Scheduler's bandwidth control, which works on two knobs:

- **`cpu.cfs_period_us`** — the length of an accounting window, 100,000 µs (100 ms) by default.
- **`cpu.cfs_quota_us`** — how much CPU *time* your container may consume within each period.

A CPU limit of `1` means quota = 100,000 µs per 100,000 µs period — 100 ms of CPU time every 100 ms, i.e. one core-equivalent. A limit of `2` means quota = 200,000 µs, and so on. The critical word is *time*, not *cores*. That 200 ms of quota can be spent by two threads running flat-out for the full period — or by twenty threads that collectively burn it in the first 10 ms and then get frozen for the remaining 90.

That second scenario is exactly what a mis-set `GOMAXPROCS` produces.

| CPU limit | CFS quota / 100ms period | Core-equivalent |
|---|---|---|
| `500m` | 50,000 µs | 0.5 |
| `1` | 100,000 µs | 1 |
| `2` | 200,000 µs | 2 |
| `4` | 400,000 µs | 4 |

The quota is a budget, and Go's scheduler width determines how fast you spend it.

---

## Why the mismatch throttles you

Put the two halves together. The runtime believes it has, say, 64 P's, so during a burst of traffic it will happily schedule 64 goroutines onto 64 OS threads and run them in parallel. The kernel lets all 64 threads run — until the container's quota for this 100 ms period is exhausted. With a limit of 2 cores, 64 threads running in parallel drain 200 ms of quota in roughly 3 ms of wall-clock time. Then the CFS scheduler throttles the *entire cgroup*: every thread is descheduled and nothing in your process runs until the next period begins.

The result is a sawtooth. Your service sprints for a few milliseconds, then stalls for the rest of the window. Averaged over a minute, CPU usage looks low and healthy — you spent 200 ms of a possible 200 ms, so utilization against the limit is "fine" — but any request unlucky enough to be mid-flight when the freeze hits eats the full throttle stall in its latency. That's your p99 blowing up while your average CPU graph stays calm.

There's a second, subtler cost. More P's than you have real CPU time means more context switching, more scheduler contention, and worse cache locality. The Go scheduler is doing bookkeeping for parallelism it can never actually realize. For a latency-sensitive payment path, that overhead is pure waste.

**The gotcha:** the throttle applies to the whole cgroup, not to one thread. A single GC assist or a burst of goroutines waking at once can spend the period's entire budget and freeze your request-handling goroutines along with it — including the ones holding locks on the ledger's in-memory balance cache. One throttle stall behind a held lock turns into a convoy of stalled requests.

---

## Diagnosing it in production

The tell is the gap between three numbers: your CPU limit, `runtime.NumCPU()`, and the CFS throttling counter. Line them up and the diagnosis is unambiguous.

**1. Confirm the runtime is running too wide.** We added a startup log line to every service — cheap, and it settles the argument immediately:

```go
slog.Info("runtime sizing",
	"num_cpu", runtime.NumCPU(),
	"gomaxprocs", runtime.GOMAXPROCS(0),
	"cpu_limit_cores", cpuLimitFromCgroup(), // helper shown below
)
```

Seeing `num_cpu=64 gomaxprocs=64 cpu_limit_cores=2` in a pod's logs is the smoking gun.

**2. Look at the CFS throttling metric.** cAdvisor exposes this and it is the single most important number here:

```promql
# Fraction of periods in which the container was throttled, per pod
rate(container_cpu_cfs_throttled_periods_total{pod=~"authz-.*"}[5m])
  /
rate(container_cpu_cfs_periods_total{pod=~"authz-.*"}[5m])
```

If that ratio is materially above zero on a latency-sensitive service, you are being throttled. Ours was sitting at **`TODO: real number`** during settlement windows. The companion metric `container_cpu_cfs_throttled_seconds_total` tells you *how much* wall-clock time was spent frozen — correlate its spikes against your p99 latency graph and they line up tooth-for-tooth.

**3. Rule out the innocent explanations.** Throttling with genuinely saturated CPU means you're under-provisioned — raise the limit. Throttling with *low* average CPU and a too-high `GOMAXPROCS` is the runtime mismatch, and that's a config fix, not a capacity fix. The startup log line is what distinguishes the two in seconds.

---

## The fix

The goal is simple: make `GOMAXPROCS` match the CPU the container is actually allowed to use, so the runtime's scheduler width matches the CFS budget. When the two agree, the runtime naturally paces itself inside the quota and the sawtooth flattens out.

### Option A: uber-go/automaxprocs (what we shipped)

The pragmatic answer for pre-1.25 services. Import it for its side effect and it reads the cgroup CPU quota at startup and sets `GOMAXPROCS` to match, rounding down:

```go
package main

import (
	_ "go.uber.org/automaxprocs" // sets GOMAXPROCS from the cgroup CFS quota at init

	"log/slog"
	"runtime"
)

func main() {
	slog.Info("runtime sizing", "gomaxprocs", runtime.GOMAXPROCS(0))
	// ... start the authorization server ...
}
```

That blank import is the entire change. On a pod limited to 2 cores it logs something like `maxprocs: Updating GOMAXPROCS=2` and the runtime stops trying to run 64-wide. One line, committed behind a canary, and our throttling ratio dropped to near zero.

**The gotcha:** `automaxprocs` rounds the quota *down* to a whole number and enforces a floor of 1. A limit of `1500m` (1.5 cores) becomes `GOMAXPROCS=1`, quietly leaving half a core on the table; a limit of `900m` also becomes 1. If you use fractional limits, either round up to whole cores in your pod spec or set the value explicitly. And it reads the quota *once at startup* — an in-place vertical resize won't be picked up until the process restarts.

### Option B: set GOMAXPROCS from the limit yourself

If you'd rather not add a dependency, you can compute it. The cleanest, most auditable version is to let the CPU limit flow in as an environment variable via the downward API, then set the runtime value at startup:

```yaml
# pod spec — expose the CPU limit to the process
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

If you want to read the cgroup directly instead of relying on the downward API, the quota lives in the filesystem — cgroup v2 exposes both numbers on one line in `cpu.max`:

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

**The gotcha:** don't hand-code cgroup v1 paths (`/sys/fs/cgroup/cpu/cpu.cfs_quota_us` and `cpu.cfs_period_us`) unless you know your nodes are v1 — the layout differs between v1 and v2, and getting it wrong silently returns the wrong number. This is precisely the drudgery `automaxprocs` handles for you, which is why we reached for the library rather than maintaining our own cgroup parser. The manual approach is worth it only when you need custom rounding (round *up* for fractional limits) or want zero third-party dependencies in the payment path.

### A note on requests vs. limits

The cleanest way to avoid throttling entirely is to reconsider whether latency-critical services need a CPU *limit* at all. A CPU *request* guarantees you a scheduling floor; a CPU *limit* imposes the CFS ceiling that causes throttling. Many teams running latency-sensitive Go services set requests and drop limits (relying on requests plus node capacity to bound noisy neighbors), which removes the quota mechanism from the picture. That's an org-wide policy call with real trade-offs around bin-packing and isolation — but if you keep limits, `GOMAXPROCS` must match them.

---

## Key takeaways

- **`GOMAXPROCS` defaults to the node's core count on pre-1.25 Go, not your container's limit.** `runtime.NumCPU()` reports the machine, and the scheduler will run that wide even when CFS won't let it.
- **Kubernetes CPU limits are a *time budget*, not dedicated cores.** Too many P's spend the CFS quota in a few milliseconds, then the whole cgroup freezes for the rest of the period — the sawtooth that wrecks p99 while average CPU looks fine.
- **Diagnose with three numbers:** the CPU limit, `runtime.GOMAXPROCS(0)`, and `container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total`. A startup log line comparing `NumCPU` to the cgroup limit ends the debate in seconds.
- **Fix by matching scheduler width to the quota.** `go.uber.org/automaxprocs` as a blank import is the low-risk default; set `GOMAXPROCS` from the downward API or `cpu.max` when you need custom rounding or zero dependencies.
- **Mind fractional limits.** `automaxprocs` rounds down with a floor of 1, so `1500m` becomes 1 — prefer whole-core limits for latency-critical services, or drop the limit and rely on requests.
- **Upgrading to Go 1.25+ makes the runtime cgroup-aware** and largely removes the default mismatch — but until you're there, this is your responsibility, and it's a one-line dependency to get right.

---

## Further reading

- Ardan Labs — ["Kubernetes CPU Limits and Go"](https://www.ardanlabs.com/blog) — a deeper walk through the CFS quota mechanics and the GOMAXPROCS interaction. The treatment above is my own, drawn from a production payment-path incident, but the Ardan Labs write-up is the canonical explanation of the underlying runtime behavior.
