# Reliability and Resilience

*How to design a system that keeps serving when its parts fail — the vocabulary of availability, the patterns that contain failure, and the Go primitives that make retries, limits, and fallbacks safe rather than dangerous.*

---

The previous two posts settled an uncomfortable fact: in any system of meaningful size, **failure is normal, not exceptional**. A disk fills, a network link drops packets, a dependency slows to a crawl, a deploy ships a bug. Post 5 made the case that partial failure is inevitable once work spans more than one machine; post 6 showed that the honest delivery guarantee across a network is *at-least-once*, which is why message processing has to be **idempotent** — safe to run twice.

Reliability engineering is what you do with that fact. It is not the pursuit of a system that never fails — that system does not exist — but the discipline of building one that **degrades predictably and recovers on its own** when pieces of it fail. This post covers the vocabulary you need to reason about it, the patterns that stop one failure from becoming all of them, and concrete Go sketches for the primitives you will reach for most.

---

## Speaking precisely about reliability

You cannot improve what you cannot name. Site Reliability Engineering gives us a small, precise vocabulary; using it correctly is half the battle in a design review.

**Availability** is the fraction of time a system is usable, and it is almost always quoted in "nines":

| Availability | "Nines" | Downtime per year | Downtime per month |
|---|---|---|---|
| 99% | two nines | ~3.65 days | ~7.2 hours |
| 99.9% | three nines | ~8.76 hours | ~43.8 minutes |
| 99.99% | four nines | ~52.6 minutes | ~4.4 minutes |
| 99.999% | five nines | ~5.26 minutes | ~26 seconds |

Each nine costs roughly ten times as much to reach as the one before it, because it forces you to eliminate ever-rarer failure modes. Most business systems live happily at three nines; five nines is telecom-grade and rarely worth it.

Two mechanical numbers underpin availability. **MTBF** (mean time between failures) is how long the system runs before breaking; **MTTR** (mean time to recovery) is how long it takes to come back. Availability is roughly `MTBF / (MTBF + MTTR)`. That ratio holds a strategic insight: **you usually get more availability by shrinking MTTR than by stretching MTBF.** Fast, automatic recovery beats heroic attempts to never fail — which is exactly why the patterns later in this post are about *recovering quickly*, not about being perfect.

The service-level trio is the language you use with the rest of the organization:

- An **SLI** (indicator) is a *measured* signal — e.g. the fraction of requests served under 300 ms, or the ratio of non-5xx responses.
- An **SLO** (objective) is the *target* you hold that indicator to — e.g. "99.9% of requests succeed over a rolling 28 days." This is an internal engineering commitment.
- An **SLA** (agreement) is a *contract* with a customer that carries penalties if breached. Your SLO should always be stricter than your SLA, so you notice trouble before a customer can invoice you for it.

The most useful thing an SLO buys you is an **error budget**: if your objective is 99.9%, then 0.1% of requests are *allowed* to fail, and that slack is a currency. Spend it on shipping fast and running risky experiments; when it runs low, the budget forces a freeze and a focus on stability. It turns "how reliable is reliable enough?" from an argument into arithmetic — and it means a team that is comfortably inside budget should be *taking more risk*, not less.

**The gotcha:** an SLO with no error budget policy is decoration. The point of the budget is that crossing it *changes behaviour* — halt feature launches, redirect the on-call rotation, page a decision-maker. If breaching the objective triggers nothing, you have a dashboard, not a reliability practice.

---

## Eliminate single points of failure

A **single point of failure (SPOF)** is any component whose loss takes the whole system down. Finding them is a simple exercise with a hard question: walk the request path and, at each hop, ask "what happens if this one thing dies right now?" The load balancer, the primary database, the single availability zone, the one machine holding a shared lock, the DNS provider — each is a candidate.

The cure is **redundancy**: have more than one of everything on the critical path. The baseline is **N+1** — provision one more instance than peak load requires, so any single loss is absorbed without degradation. For higher tiers you provision N+2 (survive a failure *during* maintenance) or spread across independent failure domains such as availability zones so that a whole-zone outage is survivable.

Redundancy only pays off with **failover** — the automatic promotion of a healthy replacement — and failover only works if you can tell healthy from unhealthy. That is the job of **health checks**: a lightweight endpoint a load balancer or orchestrator polls, pulling an instance out of rotation the moment it stops answering correctly. Make the check *deep enough to be meaningful* (can it reach its database?) but *shallow enough to be fast and stable* — a health check that itself calls three flaky downstreams will flap and evict healthy nodes.

There are two shapes of redundancy:

- **Active-passive:** one instance serves traffic while a standby waits. On failure, the standby is promoted. Simpler and a natural fit for stateful systems like a primary database with a hot replica, but the standby is idle capacity and failover takes seconds to minutes.
- **Active-active:** all instances serve traffic simultaneously behind a load balancer. Losing one just sheds a fraction of capacity with no promotion step — which is why it delivers better availability — but it demands that instances be stateless (or share state carefully) and that you provision enough headroom to absorb the lost node.

**The gotcha:** redundancy that shares a hidden dependency is not redundant. Three app servers that all talk to one database, or two availability zones fed by one NAT gateway, collapse to a single point of failure at the shared resource. Trace redundancy all the way down — the SPOF is almost always the thing everyone forgot they had only one of.

---

## Timeouts, retries, backoff, and jitter

When a dependency is slow or flaky, three tools handle it: give up in time, try again, and try again *politely*.

A **timeout** is the most important and most often omitted. A call with no timeout can hang forever, and a hung call holds a goroutine, a connection, and a slot in every caller upstream — so one slow dependency silently consumes the whole system's capacity. Every network call needs a deadline. In Go the idiom is `context.WithTimeout`, and the deadline should propagate down the call chain so the total budget is bounded end to end.

A **retry** turns a transient failure into a success — a dropped packet, a momentary blip, a replica that was mid-failover. But retries are dangerous precisely when you need them most. If a dependency is struggling and every client retries immediately, you have just *multiplied* the load on a system that is already falling over. That is a **retry storm**, and it is a leading cause of **metastable failure** — an outage that persists even after the original trigger is gone, because the retry load alone is now enough to keep the system down.

The two disciplines that make retries safe are **exponential backoff** (wait longer after each attempt: 100 ms, 200 ms, 400 ms…) and **jitter** (randomise each wait). Backoff drains load off a struggling dependency; jitter *desynchronises* the callers so they do not all wake up and retry in lockstep.

```go
// retry runs fn up to maxAttempts, backing off exponentially with full jitter.
// It only retries when fn returns a retryable error, and it respects ctx.
func retry(ctx context.Context, maxAttempts int, base, cap time.Duration, fn func() error) error {
	var err error
	for attempt := 0; attempt < maxAttempts; attempt++ {
		if err = fn(); err == nil {
			return nil
		}
		if !isRetryable(err) {
			return err // don't retry a 400; it will just fail again
		}
		// Exponential backoff: base * 2^attempt, clamped to cap.
		backoff := float64(base) * math.Pow(2, float64(attempt))
		if backoff > float64(cap) {
			backoff = float64(cap)
		}
		// Full jitter: sleep a random duration in [0, backoff).
		sleep := time.Duration(rand.Int63n(int64(backoff) + 1))
		select {
		case <-time.After(sleep):
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	return fmt.Errorf("gave up after %d attempts: %w", maxAttempts, err)
}
```

Two design decisions live in that code. First, retry only *retryable* errors — a timeout or a 503 is worth another shot; a 400 or a validation error is not, and retrying it just wastes budget. Second, the "full jitter" strategy (sleep a uniform random time between zero and the backoff ceiling) is what the AWS Builders' Library found spreads retry load most evenly; the naive alternative — everyone sleeping exactly the backoff interval — recreates the thundering herd you were trying to avoid.

**The gotcha:** retries *without* jitter synchronise clients into a thundering herd. Picture a thousand clients that all failed at the same instant during a brief outage; with fixed backoff they all retry at exactly T+1s, hammer the recovering service, and knock it down again. Jitter is not a nice-to-have — it is the difference between a retry policy that heals and one that perpetuates the outage.

---

## Idempotency: what makes a retry safe at all

Backoff and jitter make retries *polite*. They do nothing to make them *correct*. A retry means the same operation may execute more than once — and if that operation has a side effect, running it twice can charge a customer twice, ship two orders, or send two emails. This is the exact problem post 6 raised about at-least-once delivery: the network cannot promise you *exactly* once, so your handler has to be safe under duplication.

The fix is the same for retries as it was for message consumers: **idempotency keys.** The client generates a unique key per logical operation and sends it with the request. The server records which keys it has already processed; a repeat of a key returns the *stored result of the first execution* instead of doing the work again.

```go
// Process executes the charge exactly once per idempotency key.
// A retry with the same key returns the original result without re-charging.
func (s *Server) Process(ctx context.Context, key string, req ChargeRequest) (ChargeResult, error) {
	// Atomically claim the key. INSERT ... ON CONFLICT DO NOTHING returns
	// rows-affected 0 if another attempt already claimed it.
	claimed, prior, err := s.store.ClaimOrLoad(ctx, key)
	if err != nil {
		return ChargeResult{}, err
	}
	if !claimed {
		return prior, nil // duplicate: replay the first result, do NOT re-charge
	}

	result, err := s.charge(ctx, req) // the side-effecting work, runs once
	if err != nil {
		s.store.Release(ctx, key) // let a genuine retry try again
		return ChargeResult{}, err
	}
	s.store.Save(ctx, key, result) // persist so future duplicates replay it
	return result, nil
}
```

The load-bearing detail is that claiming the key is **atomic** — a single `INSERT ... ON CONFLICT DO NOTHING` (or a conditional write in a key-value store), never a read-then-write, which races two concurrent duplicates straight past the guard.

**The gotcha:** retries without idempotency duplicate side effects. A payment endpoint that a client retries after a timeout — where the *first* call actually succeeded but the response was lost — will charge the card twice unless an idempotency key catches the replay. Never add retries to a mutating operation without making that operation idempotent first. The two patterns are a matched pair, not independent choices.

---

## Circuit breakers and bulkheads: contain the blast radius

Retries help when a dependency is *briefly* unavailable. When it is *thoroughly* down, continued retrying is actively harmful — you pile load on a dead service and tie up your own resources waiting for calls that will time out. A **circuit breaker** solves this by failing fast once a dependency is clearly broken.

It is a small state machine wrapping calls to a dependency:

- **Closed** — normal operation; calls flow through and failures are counted.
- **Open** — once failures cross a threshold, the breaker "trips": for a cooldown period every call fails *immediately* without touching the dependency, giving it room to recover and freeing your resources.
- **Half-open** — after cooldown, a few trial calls are let through. If they succeed, the breaker closes; if they fail, it re-opens and waits again.

The pattern (Michael Nygard named and popularised it in *Release It!*) converts a slow, resource-draining cascade into a fast, cheap failure you can handle deliberately — often by falling back to a degraded response.

Where a breaker stops failure from spreading *over time*, a **bulkhead** stops it from spreading *across resources*. The name comes from a ship's hull, partitioned so a breach floods one compartment instead of sinking the vessel. In software, you isolate resource pools so a problem in one dependency cannot starve the others: give each downstream its own connection pool and its own bounded concurrency, so a hang in the recommendation service cannot consume every worker and take checkout down with it. In Go a buffered channel or a semaphore capping in-flight calls per dependency is a serviceable bulkhead.

**The gotcha:** a circuit breaker that never opens is just hope with extra code. If the failure threshold is set so high it never trips under real conditions, the breaker adds latency and complexity while providing zero protection. Tune the thresholds against realistic failure rates, and — crucially — *test the open path*: force the breaker open and confirm the fallback actually works. An untested fallback is a second bug waiting for the worst possible moment to surface.

---

## Rate limiting and load shedding

Redundancy and breakers handle *failing* dependencies. **Overload** is a different threat: more work arriving than you can serve. Left unmanaged it produces the worst outcome of all — a system that slows to a crawl, times out every request, and serves *nobody* while consuming maximum resources. That is metastable failure again, from the demand side.

**Rate limiting** caps how much work you accept, usually per client or per API key. Two classic algorithms:

- **Token bucket** — a bucket refills with tokens at a steady rate up to a maximum; each request spends a token, and a request with no token available is rejected or delayed. It permits short bursts (up to the bucket size) while bounding the sustained rate. This is the common choice, and Go ships a production-quality implementation.
- **Leaky bucket** — requests queue and drain at a fixed rate, smoothing bursts into a constant output stream. It trades burst tolerance for a perfectly even flow.

The standard library extension `golang.org/x/time/rate` is a token-bucket limiter and worth using directly rather than reinventing:

```go
import "golang.org/x/time/rate"

// Allow 100 requests/second sustained, with bursts up to 20.
limiter := rate.NewLimiter(rate.Limit(100), 20)

func handle(w http.ResponseWriter, r *http.Request) {
	if !limiter.Allow() { // non-blocking: true if a token was available
		http.Error(w, "rate limit exceeded", http.StatusTooManyRequests) // 429
		return
	}
	// ... serve the request
}
```

Rate limiting protects you from *steady* excess. **Load shedding** protects you from a *surge* your capacity genuinely cannot meet: when the system is saturated, deliberately drop the least important work so the rest survives. The move is to return a fast `503 Service Unavailable` for low-priority requests — batch jobs, prefetches, analytics pings — while reserving capacity for the requests that matter, like checkout or login. Shedding is triggered by a real saturation signal (queue depth, CPU, in-flight count), not by a fixed rate.

**The gotcha:** under overload, shedding load beats collapsing under it. A fast 503 costs almost nothing to produce and lets the caller back off; a request accepted into a saturated system consumes memory and a goroutine only to time out anyway — and takes a neighbouring request down with it. When you cannot serve everyone, serving *some* requests well is strictly better than serving *all* of them badly. Degrade on purpose, before the system degrades on its own terms.

---

## Graceful degradation

The instinct when a dependency fails is to return an error. Often there is a better answer: **serve something reduced rather than nothing.** Graceful degradation is designing the system so that when a non-essential piece fails, the core function keeps working with diminished quality instead of falling over.

The moves are concrete. When the personalization service is down, **serve a generic, cached homepage** instead of a personalized one. When the live inventory count is unavailable, **show the last known value** with a quieter guarantee ("usually ships in 2 days") rather than blocking the purchase. When the recommendation engine times out, **hide the recommendations panel** and render the rest of the page. Stale cache in particular is a powerful fallback: a value that is a few minutes old is almost always better than an error page, so treating your cache as a fallback source — not just a speed-up — buys real resilience.

The design question to ask of every feature is: *what is the minimum useful response if this dependency is gone?* Answer it in advance, wire the fallback in behind a circuit breaker, and a downstream outage becomes a quiet quality dip your users may not even notice — instead of a page of red.

---

## Testing that it actually works

Every pattern above shares a weakness: the failure path runs rarely, so it rots quietly. The fallback that was correct at launch drifts out of sync; the breaker's open path was never exercised; the retry logic has a bug that only shows under real timeouts. You cannot trust resilience you have not tested under failure.

**Chaos engineering** is the discipline of injecting failure deliberately to verify the system behaves as designed. Netflix's Chaos Monkey — which randomly terminates production instances — is the famous example, but the idea generalizes: kill an instance and confirm failover; add latency to a dependency and confirm timeouts and breakers fire; blackhole a downstream and confirm graceful degradation. The rigorous version starts from a hypothesis ("if the cache disappears, latency rises but error rate stays flat"), injects the fault in a controlled blast radius, and checks whether reality matched the hypothesis. A surprise is a bug you found on your own schedule instead of at 3 a.m.

**Game days** are the human-in-the-loop counterpart: a scheduled exercise where the team injects a realistic failure and practices the *response* — the runbooks, the dashboards, the escalation path, the on-call muscle memory. They test the parts of recovery that automation cannot: whether the alert reaches the right person, whether the runbook is accurate, whether anyone remembers how the failover switch works. Recovery is a skill, and skills decay without practice.

---

## Key takeaways

- **Failure is normal — design for it.** The goal is not a system that never fails but one that degrades predictably and recovers on its own. Optimize MTTR (fast recovery) at least as hard as MTBF (fewer failures).
- **Turn "reliable enough" into arithmetic.** SLIs measure, SLOs target, SLAs contract; the error budget between your SLO and 100% is a currency you spend on velocity — and its policy must actually change behaviour when it runs out.
- **Redundancy only helps if it is real.** Eliminate single points of failure with N+1 across independent failure domains, back it with health checks and failover, and trace it all the way down — the SPOF is the shared thing you forgot you had one of.
- **Retries need three companions.** Timeouts to bound the wait, backoff to drain load, jitter to desynchronize clients — and idempotency keys, because a retry without them duplicates side effects like a double charge.
- **Contain failure in space and time.** Circuit breakers stop cascades over time (and must be tuned and their open path tested); bulkheads isolate resource pools so one sick dependency cannot starve the rest.
- **Under overload, shed deliberately.** Rate-limit steady excess (token bucket), and when saturated return fast 503s for low-priority work — collapsing serves nobody; degrading serves the requests that matter.
- **Untested resilience is theater.** Chaos experiments and game days are how you learn your fallbacks still work *before* an outage teaches you they don't.

---

## Further reading

- [Site Reliability Engineering (Google, free online)](https://sre.google/sre-book/table-of-contents/) — the source text for SLIs/SLOs/SLAs and error budgets; the "Service Level Objectives" and "Embracing Risk" chapters are the primary reference for this post's vocabulary.
- [Timeouts, retries, and backoff with jitter (Amazon Builders' Library)](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) — the practitioner's guide to why naive retries cause storms and why full jitter spreads load best.
- [Avoiding fallback in distributed systems (Amazon Builders' Library)](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems/) — a sharp, real-world take on when fallbacks help and when they quietly become their own outage.
- [Using load shedding to avoid overload (Amazon Builders' Library)](https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/) — how to detect saturation and shed low-priority work rather than collapse.
- [Circuit Breaker (Martin Fowler)](https://martinfowler.com/bliki/CircuitBreaker.html) — a clear write-up of the pattern Michael Nygard introduced in *Release It!*, with the closed/open/half-open state machine.
- [golang.org/x/time/rate](https://pkg.go.dev/golang.org/x/time/rate) — the official Go token-bucket rate limiter, with `Allow`, `Wait`, and `Reserve` documented.
- [Principles of Chaos Engineering](https://principlesofchaos.org/) — the hypothesis-driven definition of chaos experiments, from the practitioners who coined the term.
