# Failure and Resilience

*In a distributed system, failure is not an exception to handle — it's the steady state. Nodes are always crashing, recovering, slowing down, and being partitioned somewhere in your cluster. Resilience is not preventing failure; it's designing so that the failures happening right now don't become the outage your users see.*

The first post argued that partial failure is the root difficulty of distributed systems. This final post closes the loop with the practical craft of *living with it*: how to detect failure when you can't tell "slow" from "dead," how to retry without causing harm, and how to keep one component's failure from cascading into a system-wide outage. These patterns are where the theory of the whole series meets the pager at 3 a.m.

## Detecting failure: the impossible question

Everything starts with a question the second post showed is unanswerable: *is that node down, or just slow?* Because you can't know, failure detection is **heuristic**, and the primary tools are **timeouts** and **heartbeats**:

- **Heartbeats** — nodes periodically signal "I'm alive"; a peer that misses several is *suspected* failed.
- **Timeouts** — if a request gets no response within a bound, treat it as failed.

The timeout value is a genuine trade-off with no perfect setting. **Too short**, and you declare healthy-but-slow nodes dead — triggering needless failovers, retries, and instability, sometimes making a load problem worse. **Too long**, and you keep sending work to a truly dead node, raising latency and hiding the failure. Because a fixed timeout is always wrong for *some* condition, mature systems use **adaptive timeouts** (based on observed response-time distributions) and **phi-accrual detectors** that output a *suspicion level* rather than a hard alive/dead bit — letting callers react proportionally. Accept up front that failure detection is inherently imperfect; design to tolerate both false positives (declaring a live node dead) and false negatives.

## Retrying safely: idempotency

When a request fails, the obvious response is to retry — but retries are dangerous for the exact reason from post one: a request that timed out might have *succeeded*, with only the response lost. Blindly retrying can execute the operation **twice** — charge a card twice, ship an order twice.

The discipline that makes retries safe is **idempotency**: an operation that has the same effect whether applied once or many times. Some operations are naturally idempotent (setting a value, deleting by ID); others must be *made* idempotent, usually with an **idempotency key** — the client generates a unique ID per logical operation, and the server records which keys it has processed, so a retry with a seen key returns the original result instead of re-executing:

```text
Client → Server: POST /charge  (Idempotency-Key: abc-123, amount: $50)
Server: key abc-123 not seen → charge $50, record abc-123 → return result
--- response lost, client retries ---
Client → Server: POST /charge  (Idempotency-Key: abc-123, amount: $50)
Server: key abc-123 already processed → return SAME result, do NOT charge again
```

And retries must be *polite*: use **exponential backoff** (wait longer after each failure) with **jitter** (randomized delay) so that when a service recovers, thousands of clients don't retry in lockstep and immediately knock it over again — the "thundering herd." Retry only what's safe, retry with backoff and jitter, and make the operation idempotent so that "retry" never means "duplicate."

## Stopping cascades: isolating failure

The failure mode that turns a small problem into an outage is the **cascade**: one slow or failed dependency causes its callers to pile up waiting, exhaust their own resources (threads, connections, memory), and fail in turn — propagating failure *upstream* until the whole system is down. Several patterns exist to contain it:

- **Circuit breakers** — wrap calls to a dependency and *trip* after a failure threshold, then **fail fast** (reject immediately) instead of waiting on a known-bad service. After a cooldown the breaker lets a trial request through to test recovery. This stops callers from wasting resources on a dependency that's already down.
- **Bulkheads** — isolate resources per dependency (separate connection/thread pools) so that one saturated dependency can't consume the resources the rest of the system needs — like watertight compartments keeping one flooded section from sinking the ship.
- **Timeouts everywhere** — a call with no timeout can block forever; every remote call needs a bound so a slow dependency can't hold your resources hostage indefinitely.
- **Load shedding & backpressure** — when overloaded, *deliberately* reject or slow incoming work rather than accept everything and collapse. Backpressure signals upstream to slow down; shedding drops excess load to keep the core serving. Serving *some* requests beats failing *all* of them.

The theme is **isolation**: assume every dependency will fail, and build boundaries so its failure stays contained instead of spreading.

## Designing for graceful degradation

Beyond containing failure, resilient systems **degrade gracefully** — lose functionality in proportion to the failure rather than falling over entirely. When a non-critical dependency is down, serve a sensible **fallback**: a slightly stale cached value, a default recommendation, the page without the personalized sidebar. The principle is to identify what's *essential* (can a user still check out?) versus *enhancing* (personalized recommendations), and ensure a failure in the enhancing parts never takes down the essential path. A checkout that works without recommendations is vastly better than a checkout that's down because the recommendation service is.

This connects back to the [CAP](/blog/posts/distsys-03-cap-and-pacelc.html) decisions: deciding *in advance* what each component does when its dependencies fail — serve stale, use a default, or reject — is graceful degradation designed rather than discovered.

## Verifying resilience: test the failures

Resilience you haven't tested is a hypothesis, not a property. Because failures are the steady state, mature teams **inject** them deliberately — **chaos engineering** — killing nodes, adding latency, and dropping packets in controlled conditions to verify the system behaves as designed *before* the same failures happen unplanned. The value isn't the chaos; it's turning "we think we handle a node dying" into "we've watched it happen and recover." Combined with good observability (metrics, tracing, alerting on the leading indicators from earlier posts — replication lag, consumer lag, error rates), it's how you know your timeouts, retries, and circuit breakers actually work.

## The series, closed

Distributed systems are hard because of partial failure, and every post was a response to it: consistency models define correctness without a shared clock; CAP/PACELC name the forced trade-offs; logical clocks order events by causality; replication and partitioning distribute data for availability and scale; consensus lets nodes agree despite failures; and resilience patterns keep the failures that are *always happening* from becoming outages. The unifying discipline is to stop treating failure as exceptional and start designing for it as normal — detect it heuristically, retry it safely, isolate it aggressively, degrade gracefully, and test it deliberately. Do that, and a system built from unreliable parts becomes reliable as a whole.

## Key takeaways

- Failure is the steady state, and detection is inherently heuristic (timeouts + heartbeats) because you can't distinguish slow from dead — use adaptive/phi-accrual detection and tolerate both false positives and false negatives.
- Make retries safe with idempotency (naturally, or via idempotency keys) so a retried-but-already-succeeded request doesn't double-execute, and use exponential backoff with jitter to avoid thundering-herd retry storms.
- Stop cascades by isolating failure: circuit breakers (fail fast on a known-bad dependency), bulkheads (per-dependency resource pools), timeouts on every remote call, and load shedding/backpressure when overloaded.
- Degrade gracefully — separate essential from enhancing functionality and serve fallbacks (stale cache, defaults) so a non-critical dependency's failure never takes down the core path; decide partition/failure behavior in advance.
- Verify resilience by injecting failures (chaos engineering) plus observability on leading indicators — untested resilience is only a hypothesis.

## Further reading

- [Consensus and Raft (previous post)](/blog/posts/distsys-07-consensus-and-raft.html)
- [Why Distributed Systems Are Hard — start of the series](/blog/posts/distsys-01-why-distributed-is-hard.html)
- [Site Reliability Engineering (Google, free online)](https://sre.google/books/)
