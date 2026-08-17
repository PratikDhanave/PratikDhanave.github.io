# Concurrency Patterns That Survive Production

*The concurrency shapes that actually hold up under payment load — pipelines, fan-out/fan-in, context propagation, errgroup with bounded parallelism, singleflight, and the idempotency realities of moving money under partial failure.*

---

Concurrency is easy to demo and hard to keep. Every Go tutorial spins up a goroutine, closes a channel, and calls it a day. Then you point real traffic at it — a payment gateway doing settlement, a ledger absorbing a burst of authorizations — and the patterns that looked clever on a slide start leaking goroutines, swallowing errors, or double-charging a customer because a retry raced a slow write.

This is not a post about the scheduler. If you want the G-M-P internals and how worker pools are sized, that's [the scheduler-under-contention post](/blog/posts/production-go-22-scheduler-under-contention.html) in this series. This one is about *composition*: how you wire concurrent stages together so the system stays correct when something upstream times out, a downstream dependency flaps, or a client retries a request you were already processing. The through-line is a single question I ask of every concurrent path in a money system: **what happens when exactly one thing fails?** Not zero, not everything — the awkward partial failure in the middle. The patterns below are the ones that answered that question well enough to survive.

---

## Pipelines: stages joined by channels, cancellation on a leash

The first pattern that scales past a single goroutine is the pipeline: a chain of stages, each reading from an inbound channel and writing to an outbound one. In a payment enrichment path we run something close to `decode → validate → enrich → score`. Each stage is independent, each can run at its own concurrency, and the channels between them are the only shared state.

The part tutorials skip is *shutdown*. A pipeline that only knows how to drain cleanly is a pipeline that leaks the moment a consumer walks away. Every stage must select on `ctx.Done()` alongside its channel sends, or a slow downstream stage will wedge every upstream goroutine forever.

```go
func enrichStage(ctx context.Context, in <-chan Txn) <-chan Enriched {
    out := make(chan Enriched)
    go func() {
        defer close(out)
        for txn := range in {
            e, err := enrich(ctx, txn)
            if err != nil {
                // log, tag, and drop — a bad enrichment must not stall the stage
                continue
            }
            select {
            case out <- e:
            case <-ctx.Done():
                return // consumer gone; stop producing, let defer close(out)
            }
        }
    }()
    return out
}
```

The invariant: **the stage that creates a channel is the stage that closes it**, and it closes with `defer` so an early `ctx.Done()` return still terminates the range on the consumer side. Get this wrong in one stage and you get the two classic failures — a send on a closed channel (panic) or a goroutine parked on a send nobody will ever receive (leak). We caught leaks like this only because goroutine count sat on a dashboard; a wedged stage had quietly accumulated **`TODO: real number`** stuck goroutines before anyone noticed.

**The gotcha:** ranging over an inbound channel handles the *normal* end-of-stream, but it does **not** handle early cancellation on the *send* side. You need both — `for txn := range in` to know when upstream is done, and `select { case out <- e: case <-ctx.Done(): }` to know when downstream has abandoned you. A stage with only the first will hang on a full outbound channel the instant the consumer stops reading.

---

## Fan-out / fan-in: parallelism without losing the stream

When one stage is the bottleneck — say enrichment makes a network call per transaction — you fan that stage out across N goroutines reading the same inbound channel, then fan the results back into one outbound channel. The channel itself does the load balancing; whichever worker is free grabs the next item.

```go
func fanOut(ctx context.Context, in <-chan Txn, n int) <-chan Enriched {
    out := make(chan Enriched)
    var wg sync.WaitGroup
    wg.Add(n)
    for i := 0; i < n; i++ {
        go func() {
            defer wg.Done()
            for txn := range in {
                e, err := enrich(ctx, txn)
                if err != nil {
                    continue
                }
                select {
                case out <- e:
                case <-ctx.Done():
                    return
                }
            }
        }()
    }
    // one closer, after all workers exit — never N closers
    go func() {
        wg.Wait()
        close(out)
    }()
    return out
}
```

The fan-*in* is the subtle half. N workers write to one `out`, but only **one** goroutine may close it, and only *after all* writers have finished. That's the `sync.WaitGroup` plus a single closing goroutine. The tempting bug is letting each worker `close(out)` when its input drains — the second close panics. The WaitGroup exists precisely to answer "have all writers stopped?" before the close happens.

**The gotcha:** fan-out silently reorders the stream — results come back in completion order, not input order. For enrichment that's fine; for anything where order encodes meaning (a sequence of ledger entries that must apply in order), fan-out is the wrong tool, or you must carry a sequence number and re-sort downstream. Decide this deliberately; the reordering is invisible in tests with fast, uniform work and glaring in production with variable latency.

---

## Context propagation: a deadline is a contract, not a suggestion

Every request that touches money in our stack carries a `context.Context` from the edge all the way down. It is the single mechanism that ties cancellation, deadlines, and request-scoped values together, and the rule is absolute: **a function that does I/O takes a `ctx` as its first argument and honors it.** No background goroutine outlives the request that spawned it without an explicit, deliberate reason.

The deadline is where this earns its keep. A settlement call that can take 200ms on a good day must not take 30 seconds on a bad one — that's how you turn one slow dependency into a thread-pool-exhaustion incident that takes down unrelated traffic.

```go
func authorize(ctx context.Context, req AuthRequest) (AuthResult, error) {
    // Bound this call independently of the caller's remaining budget,
    // but never *extend* past it — WithTimeout takes the min implicitly.
    ctx, cancel := context.WithTimeout(ctx, 250*time.Millisecond)
    defer cancel() // ALWAYS. even on the happy path — or you leak the timer.

    res, err := gateway.Send(ctx, req)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            // We do NOT know if the gateway processed it. Treat as indeterminate,
            // never as a clean failure — see idempotency below.
            return AuthResult{}, ErrIndeterminate
        }
        return AuthResult{}, err
    }
    return res, nil
}
```

**The gotcha:** `defer cancel()` is not optional and not just for the error path. `context.WithTimeout` allocates a timer that lives until the deadline *or* until you call `cancel()`; skip it on the success path and you leak a timer per call until each one fires. `go vet` will flag the obvious cases, but the one that bit us was a `cancel` captured in a closure that returned early — vet stayed quiet, and the timers piled up. The deeper trap is semantic: a `DeadlineExceeded` on a write is **indeterminate**, not a failure. You timed out waiting for the answer; the write may still have landed. Money code must never treat "I stopped waiting" as "it didn't happen."

---

## errgroup: bounded parallel work with first-error semantics

Raw `sync.WaitGroup` gives you "wait for all," but it has no opinion about errors and no opinion about how many goroutines run at once. For fan-out where each unit can fail — enriching a batch of transactions, calling three risk providers in parallel — `golang.org/x/sync/errgroup` is the right primitive. It cancels the shared context on the first error and returns that error from `Wait()`, and since Go's addition of `SetLimit`, it also caps concurrency without a hand-rolled semaphore.

```go
func scoreBatch(ctx context.Context, txns []Txn) ([]Score, error) {
    g, ctx := errgroup.WithContext(ctx)
    g.SetLimit(16) // cap in-flight calls — protect the downstream risk service

    scores := make([]Score, len(txns))
    for i, txn := range txns {
        i, txn := i, txn // pin loop vars (pre-1.22 habit worth keeping explicit)
        g.Go(func() error {
            s, err := riskService.Score(ctx, txn) // ctx is cancelled on first error
            if err != nil {
                return fmt.Errorf("scoring txn %s: %w", txn.ID, err)
            }
            scores[i] = s // distinct index per goroutine — no lock needed
            return nil
        })
    }
    if err := g.Wait(); err != nil {
        return nil, err // first error wins; the rest were cancelled
    }
    return scores, nil
}
```

Two details make this safe. Each goroutine writes to a **distinct index** of a pre-sized slice, so there's no shared write and no mutex. And `g.SetLimit(16)` means a 10,000-item batch never opens 10,000 sockets to the risk service — it holds at 16, which is the difference between backpressure and a self-inflicted DDoS on your own dependency. We landed on **`TODO: real number`** as the limit after watching the risk service's p99 climb under unbounded fan-out.

**The gotcha:** `errgroup` gives you *first-error* semantics, not *all-errors*. `Wait()` returns exactly one error; the others are discarded once the context cancels. That's usually what you want — fail fast, cancel the rest. But when you genuinely need every failure (validating a batch where each line's error must be reported back to the client), errgroup is the wrong shape — collect errors into a slice under a mutex, or use `errors.Join`, and don't cancel siblings on the first fault. Also mind `SetLimit`'s mechanics: `g.Go` *blocks* once the active-goroutine limit is reached (it does not panic), while `SetLimit` itself *panics* if you change the limit while goroutines are still active in the group — set the limit once, up front.

---

## singleflight: collapse duplicate in-flight work

Here's a pattern that saved a dependency from itself. FX rate and reference-rate lookups are read-heavy and cache-fronted, but on a cache miss under load you get the *thundering herd*: 500 concurrent requests all miss the same key at the same millisecond and all stampede the upstream rate service. `golang.org/x/sync/singleflight` collapses those into **one** actual call — the rest wait and share the result.

```go
var group singleflight.Group

func (c *RateCache) Get(ctx context.Context, pair string) (Rate, error) {
    if r, ok := c.lookup(pair); ok {
        return r, nil
    }
    // Only ONE goroutine per key actually calls upstream; the herd shares its result.
    v, err, shared := group.Do(pair, func() (interface{}, error) {
        r, err := c.upstream.Fetch(ctx, pair) // the single real call
        if err != nil {
            return nil, err
        }
        c.store(pair, r)
        return r, nil
    })
    if err != nil {
        return Rate{}, err
    }
    _ = shared // true when this caller piggybacked on another's call — useful metric
    return v.(Rate), nil
}
```

The `shared` return is worth emitting as a metric: the ratio of shared-to-total tells you exactly how much herd you're collapsing. Under a burst we saw a single upstream call absorb **`TODO: real number`** waiting callers, turning what would have been **`TODO: real number`** upstream requests into one.

**The gotcha:** singleflight shares the *error* too. If the single in-flight call fails, every waiter gets that same failure — a transient blip becomes a synchronized failure across the whole herd. Worse, the failing call blocks all of them for its full duration, so a slow-failing upstream can pin the herd for the timeout window. Two mitigations we run: pass a `ctx` with a tight deadline into the shared function so a hung upstream can't pin waiters indefinitely, and call `group.Forget(key)` after a failure so the next request re-attempts instead of the whole herd sharing one stale error. And never singleflight a *write* — collapsing two identical writes into one is only correct if the operation is idempotent, which brings us to the last and most important pattern.

---

## Idempotency and at-least-once: the pattern money actually requires

Everything above is about making concurrent work fast and cancellable. This is about making it *correct* when the network lies to you. In a payment system the hard truth is that **at-most-once delivery does not exist over an unreliable network** — you get at-least-once, and you make it safe with idempotency. Every one of the patterns above can, under partial failure, cause the same operation to be attempted twice: a retry after an indeterminate timeout, a redelivered queue message, a client resubmitting because our response got lost on the way back.

The only defensive shape that holds is an **idempotency key** attached to every state-changing operation, enforced at the durable layer.

```go
func (l *Ledger) Post(ctx context.Context, key string, e Entry) (PostResult, error) {
    tx, err := l.db.BeginTx(ctx, nil)
    if err != nil {
        return PostResult{}, err
    }
    defer tx.Rollback() // no-op after a successful Commit

    // The unique constraint on idempotency_key is the real enforcement —
    // not the app-level check, which races under concurrency.
    _, err = tx.ExecContext(ctx,
        `INSERT INTO ledger_entries (idempotency_key, account, amount)
         VALUES ($1, $2, $3)`, key, e.Account, e.Amount)
    if isUniqueViolation(err) {
        // Already posted — return the prior result, do NOT post again.
        return l.loadResult(ctx, key)
    }
    if err != nil {
        return PostResult{}, err
    }
    return PostResult{Applied: true}, tx.Commit()
}
```

**The gotcha:** the enforcement has to live in the database's unique constraint, not in an application-level "check then insert." A check-then-insert has a race window — two concurrent retries both read "not present," both insert, and you've double-posted. The unique constraint collapses that race into one winner and one clean violation you can handle. And notice the timeout path from the context section connects here: an `ErrIndeterminate` from a settlement call is *safe to retry* precisely because the retry carries the same idempotency key — the second attempt either completes the work that never landed or harmlessly hits the constraint for the work that did. Idempotency is what makes at-least-once tolerable. Without it, every retry in every pattern above is a potential double-charge.

---

## When each pattern earns its place

| Situation | Pattern | The failure it prevents |
|---|---|---|
| Multi-stage transform of a stream | Pipeline + `ctx.Done()` on sends | Goroutine leak when a consumer leaves |
| One stage is the bottleneck | Fan-out / fan-in with one closer | Panic from multiple `close`; lost cancellation |
| Any I/O call | Context with timeout + `defer cancel()` | One slow dependency exhausting the system |
| Bounded parallel work that can fail | `errgroup` + `SetLimit` | Unbounded fan-out; swallowed first error |
| Cache-miss stampede on hot keys | `singleflight` | Thundering herd onto an upstream |
| Any state change over a network | Idempotency key + unique constraint | Double-charge on retry / redelivery |

---

## Key takeaways

- **Cancellation is a first-class concern, not cleanup.** Every channel send in a pipeline selects on `ctx.Done()`; every timeout has a `defer cancel()`. The leak you don't see in tests is the incident you see in production.
- **One channel, one closer.** Fan-in is only safe when exactly one goroutine closes the shared channel after a WaitGroup confirms all writers are done.
- **Bound your parallelism.** `errgroup.SetLimit` turns a batch into backpressure instead of a self-inflicted outage on your own dependency — and remember it returns only the *first* error.
- **Collapse duplicate reads, never duplicate writes.** `singleflight` is a gift for hot cache keys but shares errors too; pair it with a tight context and `Forget` on failure.
- **A timeout on a write is indeterminate, and the answer is idempotency.** At-least-once is the only delivery you actually get; a unique constraint on an idempotency key is what makes retrying money-moving operations safe.

The pattern isn't any single primitive — it's asking "what happens when exactly one thing fails?" of every concurrent path *before* it ships, and refusing to treat "I stopped waiting" as "it didn't happen."

---

## Further reading

- Ardan Labs, *Scheduling In Go: Part III - Concurrency* — a grounded treatment of how concurrency composes with the Go runtime, and the mental model behind writing concurrent code that stays correct under load. https://www.ardanlabs.com/blog
