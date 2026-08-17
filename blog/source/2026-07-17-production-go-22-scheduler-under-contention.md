# The Go Scheduler Under Contention

*How an unbounded goroutine-per-request design quietly collapsed a high-TPS payment authorization service — and how understanding the G-M-P model, then capping concurrency with worker pools, semaphores, and backpressure, brought p99 latency back under control.*

---

The pager went off at 02:14 on a Saturday. Our card-authorization service — the thing in the hot path of every tap, swipe, and online checkout — was timing out. Not down, not erroring, just *slow*. p99 authorization latency had climbed from its usual single-digit milliseconds to **`TODO: real number`ms**, and the upstream payment gateway was starting to cut us off for breaching its response SLA. Traffic wasn't even at an all-time peak — a busy Saturday night, but nothing we hadn't served before.

The root cause was a design decision that had sat in the code for two years looking completely idiomatic: `go handleAuth(conn)`. One goroutine per request, unbounded. It's the first thing everyone learns about Go concurrency, and for two years it was fine. This post is about the night it stopped being fine, what the Go scheduler was actually doing under that load, and the three-part fix that made the service predictable again.

---

## "Goroutines are cheap" is true until it isn't

The reason the goroutine-per-request pattern feels safe is that the sales pitch is accurate. A goroutine starts with a tiny stack (a couple of KB) that grows and shrinks on demand, and the runtime multiplexes thousands of them onto a small number of OS threads. Spawning one is cheap. Blocking one is cheap. You can have hundreds of thousands of them.

Here's the handler that had been in production, lightly cleaned up:

```go
func (s *AuthServer) Serve(l net.Listener) {
	for {
		conn, err := l.Accept()
		if err != nil {
			s.log.Error("accept", "err", err)
			continue
		}
		// One goroutine per connection. Unbounded.
		go s.handleAuth(conn)
	}
}

func (s *AuthServer) handleAuth(conn net.Conn) {
	defer conn.Close()

	req, err := decodeAuthRequest(conn)
	if err != nil {
		return
	}

	// Each of these can block: fraud model, ledger balance check,
	// network round-trip to the card network.
	score := s.fraud.Score(req)             // ~a few ms, CPU + a cache call
	bal := s.ledger.Reserve(req.Account)    // DB round-trip, holds a row lock
	resp := s.network.Authorize(req, score) // external network call, slowest

	_ = encodeAuthResponse(conn, combine(bal, resp))
}
```

Nothing here is *wrong* in isolation. The problem is that "cheap" hides a cost that doesn't surface until you cross a threshold. Each goroutine's stack is small but not free — at **`TODO: real number`** in-flight requests, stacks alone consumed **`TODO: real number`GB** of RSS. Worse, every one of those goroutines wanted to *run*, and the thing that decides who runs is where the real story is.

---

## The G-M-P model at a working level

To understand what went wrong you need a working mental model of the Go scheduler. It has three moving parts, and Go people call them G, M, and P.

- **G — goroutine.** A unit of work: your function plus its stack and its state. Cheap to create, and there can be an enormous number of them.
- **M — machine.** An OS thread. This is the thing the operating system actually schedules onto a CPU core. Ms are expensive; the runtime tries to keep the count modest.
- **P — processor.** A *logical* processor, a scheduling context that holds a run queue of runnable Gs. The number of Ps is fixed at `GOMAXPROCS`, which defaults to the number of CPU cores. **A G can only run when an M is holding a P.** P is the permission slip.

So the shape is: many Gs, a small fixed number of Ps (say 8 on an 8-core box), and roughly one M per P doing useful work at any instant. Each P has a **local run queue** of ready goroutines, with a **global run queue** for overflow. When a P's local queue empties, its M goes **work-stealing** — grabbing half the runnable Gs from another P's queue. That's why Go scales across cores for free: the runtime keeps the Ps fed.

The critical rule for our incident: **runnable goroutines are not running goroutines.** You can have 50,000 Gs all ready to execute, but only `GOMAXPROCS` of them touch a CPU at any moment. The other 49,992 sit in run queues waiting their turn.

```
        G G G G G G G G ...  (tens of thousands, all "runnable")
         \  |  /
   ┌──────┴──┴──────┐
   │  P0   P1  ...  P7   │   GOMAXPROCS = 8 logical processors
   │  each holds a local │   local run queues; overflow → global queue
   │  run queue of Gs    │   idle P steals half of a busy P's queue
   └──┬───┬─────────┬────┘
      M   M   ...   M         OS threads, ~one per P doing work
      │   │         │
     CPU CPU  ...  CPU         actual cores
```

When a goroutine makes a **blocking syscall**, the runtime hands its P off to another M so the rest of that P's goroutines keep running — the handoff that makes blocking I/O feel free. But a subtler kind of blocking — waiting on a channel, a mutex, a `sync.WaitGroup` — parks the goroutine in the scheduler's own structures. That's where contention lives.

---

## What actually happens under contention

Here's the sequence that took us down, in scheduler terms.

Saturday-night traffic pushed inbound connections up, and every connection spawned a goroutine. Each ran a fraud score (CPU-bound — it *wants* a P), then hit `ledger.Reserve`, which takes a **row lock** in the database and, on our side, sits behind a `sync.Mutex` guarding a connection-pool structure. So we had tens of thousands of goroutines all needing to:

1. Get scheduled onto a P to do CPU work (fraud scoring), and
2. Contend for a mutex (the ledger pool) and a downstream DB lock.

Two things compounded. First, **scheduler churn**: with tens of thousands of runnable Gs and 8 Ps, the runtime is constantly moving goroutines on and off Ps, and every mutex contention event parks one goroutine and wakes another — more scheduling work. The CPU was busy, but a growing fraction of that "busy" was the runtime managing the stampede rather than scoring transactions. Second, **latency inversion**: because the run queues were enormous, a brand-new request's goroutine landed at the back of a very long line. A request whose fraud score would take a fraction of a millisecond now waited **`TODO: real number`ms** just to get *onto* a CPU. The slow external card-network call held its goroutine alive the entire time, keeping the in-flight count high, which kept the queues long. A feedback loop.

**The gotcha:** unbounded goroutines don't fail by crashing. They fail by turning your CPU-bound fast path into a queueing-theory problem. The system stays "up" and "busy" while every individual request gets slower, because you admitted more work than you have Ps to run, and the Go scheduler faithfully queued all of it instead of telling anyone *no*. Goroutines being cheap to *create* is exactly the trap: nothing pushed back at creation time.

---

## Fix part 1: a bounded worker pool

The first move is to stop coupling "a request arrived" to "spawn a goroutine." Spawn a fixed number of workers once and feed them requests over a channel. Now the number of goroutines doing expensive work is a constant *you* chose, not one the internet chose for you.

```go
type AuthPool struct {
	jobs    chan net.Conn
	handler func(net.Conn)
	wg      sync.WaitGroup
}

// workers = how many auths run concurrently. Size it to the bottleneck,
// not to GOMAXPROCS — see the sizing note below.
func NewAuthPool(workers, queue int, handler func(net.Conn)) *AuthPool {
	p := &AuthPool{
		jobs:    make(chan net.Conn, queue),
		handler: handler,
	}
	p.wg.Add(workers)
	for i := 0; i < workers; i++ {
		go p.worker()
	}
	return p
}

func (p *AuthPool) worker() {
	defer p.wg.Done()
	for conn := range p.jobs { // blocks when idle; no busy-wait
		p.handler(conn)
	}
}

// Submit reports whether the job was accepted. A full queue means
// we're saturated — the caller decides what to do (see load-shedding).
func (p *AuthPool) Submit(conn net.Conn) bool {
	select {
	case p.jobs <- conn:
		return true
	default:
		return false // queue full — do NOT block the accept loop
	}
}

func (p *AuthPool) Shutdown() {
	close(p.jobs) // workers drain remaining jobs, then exit
	p.wg.Wait()
}
```

The accept loop becomes: accept, `Submit`, and if `Submit` returns false, shed (we'll get to that). The number of goroutines running `handler` is now bounded by `workers`, full stop. The scheduler only juggles that many active work-Gs plus idle workers parked on the channel receive — and a goroutine parked on a receive costs the scheduler nothing until there's work.

**The gotcha:** a bounded pool only bounds what runs *inside* the pool. If your `handler` itself spawns `go somethingElse()`, you've reopened the hole one level down. The bound has to sit at whatever concurrency limit you actually care about — which, for us, was the downstream dependency, not the pool.

---

## Fix part 2: a semaphore for the real bottleneck

The pool caps how many auths we process at once. But the resource that falls over first is the **card network connection**, which tolerates far fewer concurrent calls than our CPU can handle scoring. Different bottlenecks want different limits — which is exactly what a second limit, a semaphore, is for.

I used `golang.org/x/sync/semaphore`: it's weighted and, crucially, context-aware, so a request already past its deadline stops waiting for a slot.

```go
import "golang.org/x/sync/semaphore"

type NetworkClient struct {
	sem *semaphore.Weighted // caps concurrent calls to the card network
	// ... underlying transport
}

func NewNetworkClient(maxConcurrent int64) *NetworkClient {
	return &NetworkClient{sem: semaphore.NewWeighted(maxConcurrent)}
}

func (c *NetworkClient) Authorize(ctx context.Context, req AuthRequest, score float64) (Resp, error) {
	// Acquire respects the deadline: if we can't get a slot before the
	// request's context expires, fail fast instead of piling on.
	if err := c.sem.Acquire(ctx, 1); err != nil {
		return Resp{}, fmt.Errorf("network slot: %w", err) // ctx deadline/cancel
	}
	defer c.sem.Release(1)

	return c.call(ctx, req, score)
}
```

If you don't want the extra dependency, a buffered channel is a serviceable semaphore — one token per buffer slot — though you have to handle the deadline yourself:

```go
type chanSem chan struct{}

func (s chanSem) acquire(ctx context.Context) error {
	select {
	case s <- struct{}{}:
		return nil
	case <-ctx.Done():
		return ctx.Err() // don't wait past the deadline
	}
}

func (s chanSem) release() { <-s }
```

The context integration is what matters in a payment path. Every auth carries a hard deadline — a late "approved" is worse than a timely "try again." So `Acquire(ctx, 1)` doing double duty as the concurrency gate *and* the deadline check means a doomed request stops consuming a slot the moment its context is done, instead of waiting for a network slot it will never use.

**The gotcha:** put the `Release` on `defer` immediately after a *successful* `Acquire`, never before it. If `Acquire` returns an error you did not take a token, and releasing one you never held corrupts the count — with `x/sync/semaphore` a stray `Release` panics, and with the channel version it lets in one extra caller forever. One acquire, one guaranteed release, and only on the success path.

---

## Fix part 3: backpressure and load-shedding

Bounding concurrency creates a new, better problem: what do you do with work you can't accept yet? The wrong answer is an unbounded queue in front of the pool — it just moves the pileup and reintroduces latency inversion. The right answer is **backpressure**: a bounded queue, and when it's full, **shed load** — reject fast with a retryable signal rather than accept work you can't finish in time.

```go
func (s *AuthServer) Serve(l net.Listener) {
	for {
		conn, err := l.Accept()
		if err != nil {
			s.log.Error("accept", "err", err)
			continue
		}
		if !s.pool.Submit(conn) {
			// Saturated. Answer immediately with a retryable status
			// so the gateway backs off instead of hanging on us.
			s.shed(conn)
			s.metrics.Shed.Inc() // watch this: it's your saturation signal
			continue
		}
	}
}

func (s *AuthServer) shed(conn net.Conn) {
	defer conn.Close()
	_ = encodeAuthResponse(conn, Resp{
		Decision: "TRY_AGAIN",  // maps to a 503-style retryable at the gateway
		Reason:   "at_capacity",
	})
}
```

This inverts the failure mode. Before, at saturation *every* request got slow and many timed out anyway — the worst of both worlds, because we paid for the fraud-scoring and ledger work and then failed. After, we serve a fast, cheap "try again" for the marginal requests and keep serving the accepted ones at full speed, spending our fixed capacity on requests we can finish inside the deadline. A load-shed request costs almost nothing; a timed-out request costs a full fraud score, a held row lock, and a doomed network call.

**The gotcha:** load-shedding is only correct if the caller treats the shed response as *retryable*, not as a decline. Getting that contract right with the gateway was as important as the code — a shed request that a partner interprets as "declined" is a failed payment, which is far worse than a slow one. Shedding must be visibly, semantically distinct from a real authorization decision.

---

## Sizing the limits (don't copy my numbers)

The point of bounding is choosing the bound deliberately, so here's the reasoning rather than magic constants.

| Limit | What it protects | How to size it |
|---|---|---|
| `GOMAXPROCS` | CPU oversubscription | Leave at core count; in containers, pin it to your CPU *quota* so the scheduler doesn't assume more cores than cgroups allow |
| Worker count | Overall in-flight work | Little's Law: `workers ≈ target_throughput × avg_service_time`; then load-test around it |
| Queue depth | Burst absorption vs. latency | Small — just enough to ride out sub-second bursts; a deep queue is latency inversion waiting to happen |
| Network semaphore | The external dependency | The downstream's documented/observed safe concurrency, minus headroom |

The container note bit us specifically: on an 8-core node with a 2-core cgroup quota, `GOMAXPROCS` defaulted to 8, so the runtime created more Ps than we had CPU to run and the throttling made scheduling latency *worse*. (Modern Go is cgroup-aware; if you're not on a version that sets this automatically, `automaxprocs` or an explicit `runtime.GOMAXPROCS` from the quota is the fix.) Our pool size, semaphore width, and queue depth were all found by load-testing to the point where p99 stayed flat — the real values were **`TODO: real number`** workers and a network semaphore of **`TODO: real number`**, but yours will differ because they're properties of *your* bottleneck, not of Go.

After the change, p99 under the same Saturday load dropped from **`TODO: real number`ms** to **`TODO: real number`ms**, in-flight goroutines went from **`TODO: real number`** to a bounded **`TODO: real number`**, and RSS stopped tracking traffic. The scheduler was never the bug. Asking it to queue unbounded work was.

---

## Key takeaways

- **Runnable is not running.** Only `GOMAXPROCS` goroutines execute at once; the rest sit in P run queues, and new requests join the back of a very long line.
- **"Goroutines are cheap" is about creation, not admission.** Nothing pushes back when you spawn one, so unbounded goroutine-per-request turns a load spike into a queueing collapse — slow, not crashed.
- **Bound at the real bottleneck.** A worker pool caps total in-flight work; a separate semaphore caps the scarce downstream. Different resources need different limits, and a pool doesn't bound goroutines its handler spawns.
- **Make the semaphore context-aware.** `Acquire(ctx, 1)` gating on the request deadline lets doomed requests stop consuming capacity. One acquire, one deferred release, only on success.
- **Prefer shedding to queueing.** A bounded queue plus a fast, retryable "try again" beats an unbounded queue that just relocates the pileup — and the caller must treat a shed as retryable, never as a decline.
- **Pin `GOMAXPROCS` to your CPU quota** in containers, or the scheduler assumes cores the cgroup won't give it.

---

## Further reading

- **"Scheduling In Go"** series by William Kennedy — the definitive working-level explanation of the G-M-P model, run queues, and work-stealing that underpins everything above: [Ardan Labs blog](https://www.ardanlabs.com/blog).
