# Tail Latency and SLOs

*The capstone of this series: why payments live or die on p99 and p999, how the Go runtime shows up in the tail, and the levers — deadlines, hedging, load-shedding — that keep an SLO honest.*

---

Every post in this series has been a story about a single service getting slower than it had any right to be, and a single runtime knob that explained it. `GOMAXPROCS` fighting CFS throttling. GC pacing that stalled allocators mid-request. A scheduler parking goroutines behind a saturated P. Escape analysis quietly moving a hot struct onto the heap. Each was diagnosed the same way — not by watching the average, but by watching the *tail*.

That's not a coincidence. In a payments system the average latency is a vanity metric. Nobody feels the average. What a merchant feels is the one authorization in a thousand that takes **`TODO: real number`** ms and trips their terminal timeout, or the settlement batch that misses its window because a handful of requests tailed out and the whole job blocked on them. The tail is where money and trust are actually lost.

So this final post ties the series together around the thing all of it was really about: **tail latency, and the service-level objectives you build on top of it.** The earlier posts were the mechanics — GOMAXPROCS, GC, the scheduler, profiling. This one is the discipline that makes those mechanics matter.

---

## Averages lie; percentiles don't

Start with why the average is worse than useless — it's actively misleading. Imagine 1,000 authorization requests. 990 of them clear in 5 ms. Ten of them, caught behind a GC assist or a scheduler stall, take 400 ms. The average is about 9 ms. Your dashboard is green. The mean says everything is fine.

But 1% of your merchants just had a request that was **80×** slower than typical. At a fintech doing millions of transactions a day, "1% of requests" is not a rounding error — it's tens of thousands of degraded payments, some of which time out, retry, and double the load exactly when you can least afford it.

Percentiles describe the experience the average hides:

- **p50 (median):** the typical request. Useful for capacity, useless for reliability.
- **p99:** one request in a hundred is at least this slow. This is usually the number your SLO is written against.
- **p999 (99.9th):** one in a thousand. In a fan-out architecture, this is the number that actually determines your *page* latency, because a page that calls 100 backends waits on the slowest of 100 — and the slowest of 100 draws from the p99 tail of each.

That last point is the one that surprises people. If a single service has a 1-in-100 chance of a slow response, and your request touches 100 such services, the probability that *at least one* is slow is `1 - 0.99^100 ≈ 63%`. Your p50 backend latency becomes your p50 *user* latency almost never. **The tail is the common case once you fan out.** This is why a payments platform obsesses over p999 on its leaf services: it's the only way the aggregate stays bounded.

---

## Where the tail comes from in a Go service

Everything in the earlier posts converges here. The sources of tail latency in a Go service are, roughly in order of how often they've bitten me:

**GC pauses and assists.** The stop-the-world portions of Go's collector are short now — sub-millisecond in most services — but they land on *some* request, and that request wears the whole pause in its tail. Worse is the *assist*: when allocation outruns the background collector, the allocating goroutine is drafted into doing GC work itself. That's not a pause you see in `GODEBUG=gctrace`; it's latency charged directly to whichever request happened to allocate at the wrong moment. The GC post covered pacing; the tail is where you feel getting it wrong.

**Scheduler queueing.** With `GOMAXPROCS` P's and more runnable goroutines than P's, someone waits in a run queue. Under load that wait is invisible to CPU dashboards (the CPU is busy, not idle) but very visible in the tail. This is the same phenomenon the GOMAXPROCS and scheduler posts described, now expressed as a percentile.

**Lock contention.** A `sync.Mutex` around a hot ledger cache or a shared rate-limiter is fine at p50 and catastrophic at p99, because contention is bursty — it's exactly when traffic spikes that the lock serializes everyone. `go test -bench` with `-blockprofile`, or the runtime's mutex profile, is how you find these; the tail is how you notice you should look.

**Allocation stalls.** Heavy allocation doesn't just create GC pressure — it can stall directly on the memory allocator's own locks and on page faults when the heap grows. The escape-analysis post was about keeping objects on the stack precisely so they never enter this path.

The through-line: **none of these show up in average latency, and all of them show up at p99+.** That's why the whole series measured tails.

---

## Deadline budgets: context is your latency contract

If the tail is what you're defending, the first line of defense is refusing to wait forever. In Go that means `context` deadlines — but the discipline that matters is treating the deadline as a *budget* that gets spent down as a request moves through your call graph, not a fixed timeout re-applied at every hop.

The mistake I see constantly: every downstream call gets `context.WithTimeout(ctx, 500*time.Millisecond)`, independently. Three sequential calls can now legally take 1.5 seconds even though your SLO is 500 ms, because each hop reset the clock. A budget is derived from the *inbound* deadline and shared:

```go
// ErrBudgetExhausted signals we ran out of time before even attempting a call —
// distinct from a call that ran and timed out, because it's not worth retrying.
var ErrBudgetExhausted = errors.New("deadline budget exhausted")

// withBudget carves a sub-deadline out of the remaining budget on the parent
// context, reserving `reserve` for work that must happen after this call
// (writing the response, emitting the settlement event, cleanup).
func withBudget(ctx context.Context, reserve time.Duration) (context.Context, context.CancelFunc, error) {
	deadline, ok := ctx.Deadline()
	if !ok {
		// No inbound deadline is a bug in a payments hot path: every request
		// should arrive with one. Fail loudly rather than inheriting "forever".
		return nil, nil, errors.New("no deadline on inbound context")
	}
	remaining := time.Until(deadline)
	if remaining <= reserve {
		return nil, nil, ErrBudgetExhausted
	}
	// Spend everything except the reserve on this call.
	child, cancel := context.WithTimeout(ctx, remaining-reserve)
	return child, cancel, nil
}

func authorize(ctx context.Context, txn Transaction) (Decision, error) {
	// Reserve time to persist the decision even if the risk check runs long.
	riskCtx, cancel, err := withBudget(ctx, 20*time.Millisecond)
	if err != nil {
		return Decision{}, err // shed early — don't start work we can't finish
	}
	defer cancel()

	score, err := riskEngine.Score(riskCtx, txn)
	if err != nil {
		return Decision{}, err
	}
	// The reserved 20ms is still on the parent ctx for the write below.
	return persistDecision(ctx, txn, score)
}
```

**The gotcha:** deriving `context.WithTimeout` from a parent that already has a nearer deadline does *not* extend anything — `context` always honors the earliest deadline in the chain. The value of `withBudget` isn't enforcement (context handles that); it's the *reserve*, and failing fast with `ErrBudgetExhausted` before you start work you provably can't finish. Starting a 200 ms risk check with 30 ms left on the clock burns CPU to produce a result nobody will wait for — that's tail latency you're *manufacturing* under load.

---

## Hedging and retries — only with idempotency

Once you can measure the tail, the tempting move is to *race* it away. **Hedging** sends a second request after a short delay — typically around your p95 — and takes whichever response comes back first. If the first request drew an unlucky GC pause or a slow node, the hedge, landing on a different pod, usually clears fast. Done right, hedging can pull p999 down toward p99 for a small increase in total load.

```go
// hedgedAuthorize fires a backup request if the first hasn't answered within
// `after` (tune to ~p95, so you only hedge the genuinely slow tail).
func hedgedAuthorize(ctx context.Context, txn Transaction) (Decision, error) {
	results := make(chan result, 2)
	attempt := func() {
		// The buffered results channel (cap 2) is what prevents the goroutine
		// leak: the loser can always send its result and exit even after the
		// winner has already returned. Note the winner does NOT cancel the
		// loser — each attempt's cancel fires only on its own return, so the
		// loser runs to completion unless the parent ctx is cancelled.
		aCtx, cancel := context.WithCancel(ctx)
		defer cancel()
		d, err := authorize(aCtx, txn)
		results <- result{d, err}
	}

	go attempt()
	timer := time.NewTimer(hedgeDelay) // e.g. ~p95 latency
	defer timer.Stop()

	select {
	case r := <-results:
		return r.decision, r.err
	case <-timer.C:
		go attempt() // hedge: a second try, likely on a different pod
	case <-ctx.Done():
		return Decision{}, ctx.Err()
	}

	select {
	case r := <-results:
		return r.decision, r.err
	case <-ctx.Done():
		return Decision{}, ctx.Err()
	}
}
```

**The gotcha:** hedging and retries are *duplicate requests by design*. In payments, a duplicate authorization that isn't deduplicated is a double charge — a customer-facing incident, not a latency win. Every hedged or retried operation **must** carry an idempotency key so the downstream treats the second copy as the same logical transaction and returns the original result instead of charging again. And hedge *only the tail*: if you set the delay too low you're duplicating a large fraction of traffic, which raises load, which raises latency, which triggers more hedges — a positive-feedback loop that turns a latency optimization into an outage. Cap total attempts, and never hedge non-idempotent writes without a dedup layer you trust.

---

## Load-shedding: protect the SLO by serving fewer requests

Hedging assumes there's spare capacity to race into. When there isn't — when you're genuinely overloaded — the honest move is the opposite: **serve fewer requests, fast, so the ones you do serve stay inside the SLO.** A service that accepts everything under overload degrades *everyone's* latency past the objective; a service that sheds the excess keeps its promise to the requests it admits.

The cleanest signal for "am I overloaded" isn't CPU or a request count — it's your own latency and queue depth. If requests are already spending too long waiting to be picked up, admitting more only makes the tail worse:

```go
// shedder admits work only while the service is meeting its latency budget.
// It watches in-flight concurrency against a ceiling derived from measured
// service time and the SLO (Little's Law: max in-flight ≈ throughput × latency).
type shedder struct {
	inFlight atomic.Int64
	ceiling  int64 // tune from load tests; the point past which p99 breaks the SLO
}

func (s *shedder) do(ctx context.Context, fn func(context.Context) (Decision, error)) (Decision, error) {
	n := s.inFlight.Add(1)
	defer s.inFlight.Add(-1)
	if n > s.ceiling {
		// Reject immediately with a retryable signal. A fast 503 the caller can
		// route elsewhere is far cheaper than a slow success that blows the SLO.
		return Decision{}, ErrOverloaded
	}
	return fn(ctx)
}
```

**The gotcha:** shed *cheaply and early*, before you've spent the request's budget. A rejection that happens after you've already done the expensive risk scoring is the worst of both worlds — you paid the cost and delivered nothing. And shed *selectively*: not all traffic is equal. A payments platform should drop a low-priority analytics read long before it drops a card authorization. Encode priority in the request and let the shedder protect the transactions that matter. Load-shedding isn't giving up — it's choosing what to sacrifice instead of letting the overload choose for you.

---

## Measuring the tail honestly

None of the above is tunable if you can't see the tail, and averages actively hide it. You need **histograms** — bucketed counts of observed latencies — because only a histogram lets you compute a percentile after the fact. Reporting a pre-averaged number from each instance and averaging *those* across the fleet gives you the average of averages, which can be off from the true p99 by an order of magnitude.

Here's a minimal, allocation-free latency histogram with fixed buckets — the kind of thing you'd expose to Prometheus, but shown standalone so the mechanics are visible:

```go
// latencyHistogram records observations into fixed upper-bound buckets.
// Bucket boundaries are in milliseconds; pick them to straddle your SLO.
type latencyHistogram struct {
	bounds  []float64      // ascending upper bounds, e.g. 1,2,5,10,25,50,100,250,500,1000
	buckets []atomic.Int64 // len == len(bounds)+1; last is the +Inf overflow
}

func newLatencyHistogram(bounds []float64) *latencyHistogram {
	return &latencyHistogram{bounds: bounds, buckets: make([]atomic.Int64, len(bounds)+1)}
}

// Observe records one latency sample. Safe for concurrent use; no allocation.
func (h *latencyHistogram) Observe(ms float64) {
	i := sort.SearchFloat64s(h.bounds, ms) // first bound >= ms; == len(bounds) means overflow
	h.buckets[i].Add(1)
}

// Quantile returns the upper bound of the bucket containing the q-th percentile.
// This is deliberately conservative: you report "p99 <= this bucket's bound",
// which is the honest thing a bucketed histogram can claim.
func (h *latencyHistogram) Quantile(q float64) float64 {
	var total int64
	counts := make([]int64, len(h.buckets))
	for i := range h.buckets {
		counts[i] = h.buckets[i].Load()
		total += counts[i]
	}
	if total == 0 {
		return 0
	}
	target := int64(math.Ceil(q * float64(total)))
	var cum int64
	for i, c := range counts {
		cum += c
		if cum >= target {
			if i == len(h.bounds) {
				return math.Inf(1) // fell into the overflow bucket — widen your bounds
			}
			return h.bounds[i]
		}
	}
	return math.Inf(1)
}
```

Usage in the hot path stays cheap — one `time.Since` and one atomic add:

```go
start := time.Now()
dec, err := authorize(ctx, txn)
hist.Observe(float64(time.Since(start).Microseconds()) / 1000.0)
```

**The gotcha:** histogram fidelity is entirely a function of your bucket boundaries, and the most common mistake is boundaries too coarse around the SLO. If your objective is p99 under 50 ms and your buckets jump 25 → 50 → 100, every violation lands in the same bucket and you can't tell a 51 ms tail from a 99 ms one. Put dense boundaries *right around your SLO threshold* where decisions get made, and always keep an overflow bucket — a `+Inf` count that's climbing is your early warning that the tail escaped your instrumentation entirely. And never, ever compute a fleet percentile by averaging per-instance percentiles; sum the buckets across instances first, then compute the quantile once.

---

## Bringing the series together

| Earlier post's lever | How it shows up in the tail | The SLO move |
|---|---|---|
| `GOMAXPROCS` vs CFS limits | Scheduler queueing under throttling | Right-size P's; shed before queues build |
| GC pacing & assists | Allocation stalls charged to a request | Cut allocation; budget the deadline |
| The scheduler | Goroutines parked behind saturated P's | Bound in-flight concurrency |
| Escape analysis / profiling | Heap growth, allocator stalls | Find hot allocs with pprof, keep them on the stack |

Every mechanic in this series was a way to make the tail shorter or more predictable. This post is the frame that tells you *which* tail to chase and *when you've won*: a service-level objective, measured with honest histograms, defended with deadline budgets, hedging on idempotent paths, and load-shedding when the only honest answer is "not all of you, not right now."

---

## Key takeaways

- **The average is a lie in the hot path.** Feel the tail: p99 for your SLO, p999 once you fan out. The slowest-of-N is the common case at scale.
- **Deadlines are budgets, not per-hop timeouts.** Derive each call's deadline from the inbound one, reserve time for cleanup, and shed early when the budget can't cover the work.
- **Hedge and retry only with idempotency.** Duplicate requests are a latency win only if a dedup key makes them safe — otherwise they're double charges. Hedge the tail, not the median.
- **Load-shedding protects the SLO.** Under overload, a fast rejection beats a slow success. Shed cheaply, early, and by priority.
- **Measure with histograms, not averages.** Dense buckets around the SLO, an overflow bucket as an alarm, and never average percentiles across instances.
- **The runtime is always in the tail.** GC, the scheduler, allocation, and `GOMAXPROCS` — everything the earlier posts covered — is what you're actually measuring when you watch p99.

---

## Further reading

- Ardan Labs — ["Scheduling In Go" and the broader Go performance series](https://www.ardanlabs.com/blog) — for the runtime mechanics beneath every source of tail latency discussed here.
