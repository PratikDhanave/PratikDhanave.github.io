<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/production-go-22-scheduler-under-contention.html -->

# The Go Scheduler Under Contention

*How an unbounded goroutine-per-request design turns overload into a latency collapse — the G-M-P model at a working level, a measured reproduction of the failure, and the fix: worker pools, semaphores, and load-shedding.*

---

"Goroutine per request" is the first pattern everyone learns in Go, and for most services it's fine for years. Then one day offered load exceeds what some bottleneck can serve, and the service doesn't crash — it just gets slower and slower while staying "up" and "busy." This post explains why, at the level of the Go scheduler, and then **reproduces the collapse with a measured demo you can run yourself** rather than asking you to take the story on faith. All numbers in this post come from running the demo harness on an Apple M1 Max (10 cores, Go 1.27, `GOMAXPROCS=10`); your numbers will differ, but the shape won't.

---

## "Goroutines are cheap" is true until it isn't

The sales pitch is accurate: a goroutine starts with a tiny stack that grows on demand, and the runtime multiplexes enormous numbers of them onto a few OS threads. Measured, not asserted — parking 100,000 goroutines on a channel receive:

```text
demo1: 100000 parked goroutines: runtime memory 5 MB -> 270 MB
       (+265 MB, ~2.7 KB/goroutine)
```

2.7 KB each. Genuinely cheap — which is exactly the trap, because *nothing pushes back at creation time*. Here's the idiomatic-looking server shape this post is about:

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

	// Each of these can block: a scoring model, a database row,
	// a slow external dependency.
	score := s.fraud.Score(req)             // CPU work
	bal := s.ledger.Reserve(req.Account)    // DB round-trip, pool-limited
	resp := s.network.Authorize(req, score) // external call, slowest, capacity-limited
}
```

Nothing here is *wrong* in isolation. The problem surfaces only when arrivals outpace the slowest dependency — and to see it clearly you need a working model of the thing deciding who runs.

---

## The G-M-P model at a working level

The Go scheduler has three moving parts:

- **G — goroutine.** A unit of work: your function plus its stack and state. Cheap; there can be an enormous number.
- **M — machine.** An OS thread — the thing the OS schedules onto a core. The runtime keeps the count modest.
- **P — processor.** A *logical* processor holding a run queue of runnable Gs. There are exactly `GOMAXPROCS` of them (default: core count). **A G runs only while an M holds a P.** P is the permission slip.

```text
        G G G G G G G G ...   (thousands, all "runnable")
         \  |  /
   ┌──────┴──┴──────────┐
   │  P0   P1  ...  P9  │   GOMAXPROCS logical processors
   │  each: local run   │   overflow -> global queue
   │  queue of Gs       │   idle P steals half of a busy P's queue
   └──┬───┬─────────┬───┘
      M   M   ...   M        OS threads, ~one per P doing work
      │   │         │
     CPU CPU  ...  CPU
```

Each P has a **local run queue**, with a **global queue** for overflow; an idle P **work-steals** half of a busy P's queue, which is why Go scales across cores for free. When a goroutine blocks in a syscall, its P is handed to another M so the rest keep running. When it blocks on a channel, mutex, or `WaitGroup`, it's parked in the scheduler's own structures.

The critical rule: **runnable is not running.** 50,000 Gs can be ready while only `GOMAXPROCS` of them touch a CPU at any instant — everyone else waits in a queue.

One honest nuance my own measurements forced me to state carefully: raw scheduling *dispatch* stays fast even under absurd load. With 50,000 CPU-spinning goroutines running, the time for a *newly created* goroutine to first execute only doubled (856ns → 1.6µs in my run) — the scheduler places fresh goroutines in a preferential "run next" slot. The latency damage under contention doesn't come from the scheduler being slow. It comes from *your work* queueing behind other work for the actual bottleneck — which is the next section.

---

## The collapse, reproduced and measured

The demo harness models the handler above honestly: each request burns 200µs of CPU (the scoring step), then calls a downstream that takes 2ms and allows **32 concurrent calls** (a semaphore inside the "database/card network"). That caps downstream capacity at 32 slots ÷ 2ms = **~16,000 requests/second** — on purpose, because real systems are capacity-limited by their slowest dependency, not by Go.

Offer it **24,000 requests/second — 1.5× capacity — for 1.5 seconds**, first with goroutine-per-request, then with a bounded pool (48 workers, queue of 64) that sheds when full. Real output, same machine, same load:

```text
paced unbounded:    36000 accepted,     0 shed, peak goroutines 12710,
                    p50 409.948ms, p99 894.48ms
paced bounded+shed: 22737 accepted, 13263 shed, peak goroutines    49,
                    p50   3.157ms, p99   4.023ms
```

Read that slowly, because it's the whole post:

- **Unbounded accepted everything** — and made everyone pay. In-flight goroutines climbed to 12,710 and p99 hit ~895ms *and was still rising when the run ended*, because at 1.5× capacity the queue grows without bound. A request whose work takes ~2.2ms spent hundreds of milliseconds waiting for a downstream slot.
- **Bounded accepted 22,737 — and check that number**: 22,737 ÷ 1.5s ≈ 15,200/s, which is the downstream's ~16k/s capacity with scheduling overhead. The pool found the service's true capacity *by construction*. Everything it accepted completed at p99 4ms — the latency the work actually costs — and the other 13,263 requests got an instant, cheap rejection instead of a 900ms timeout.

**The gotcha:** unbounded goroutines don't fail by crashing. They fail by turning your fast path into a queueing-theory problem. The system stays up while every individual request slows down, because you admitted more work than the bottleneck can serve and the scheduler faithfully queued all of it instead of telling anyone *no*.

---

## Fix part 1: a bounded worker pool

Stop coupling "a request arrived" to "spawn a goroutine." Spawn a fixed number of workers once and feed them over a channel — now the concurrency doing expensive work is a constant *you* chose, not one the internet chose for you.

```go
type AuthPool struct {
	jobs    chan net.Conn
	handler func(net.Conn)
	wg      sync.WaitGroup
}

// workers = how many requests run concurrently. Size it to the bottleneck,
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

In the measured run this is what held peak goroutines at 49 (48 workers + the submitter) versus 12,710. A goroutine parked on a channel receive costs the scheduler nothing until there's work.

**The gotcha:** a bounded pool only bounds what runs *inside* the pool. If `handler` spawns `go somethingElse()`, you've reopened the hole one level down. The bound has to sit at the concurrency limit you actually care about — usually the downstream dependency, not the pool.

---

## Fix part 2: a semaphore for the real bottleneck

The pool caps total in-flight work, but the resource that falls over first — the external dependency — usually tolerates far less concurrency than your CPU. Different bottlenecks want different limits, which is what a second limit is for. `golang.org/x/sync/semaphore` is weighted and, crucially, context-aware:

```go
import "golang.org/x/sync/semaphore"

type NetworkClient struct {
	sem *semaphore.Weighted // caps concurrent calls to the dependency
}

func NewNetworkClient(maxConcurrent int64) *NetworkClient {
	return &NetworkClient{sem: semaphore.NewWeighted(maxConcurrent)}
}

func (c *NetworkClient) Authorize(ctx context.Context, req AuthRequest, score float64) (Resp, error) {
	// Acquire respects the deadline: if we can't get a slot before the
	// request's context expires, fail fast instead of piling on.
	if err := c.sem.Acquire(ctx, 1); err != nil {
		return Resp{}, fmt.Errorf("network slot: %w", err)
	}
	defer c.sem.Release(1)

	return c.call(ctx, req, score)
}
```

Without the dependency, a buffered channel is a serviceable semaphore — one token per slot — though you handle the deadline yourself:

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

The context integration is the point for anything with a hard deadline: `Acquire(ctx, 1)` doing double duty as concurrency gate *and* deadline check means a doomed request stops consuming a slot the moment its context is done.

**The gotcha:** put `Release` on `defer` immediately after a *successful* `Acquire`, never before it. If `Acquire` errored you took no token; releasing one you never held corrupts the count — `x/sync/semaphore` panics on a stray release, and the channel version silently admits one extra caller forever.

---

## Fix part 3: backpressure and load-shedding

Bounding concurrency creates a better problem: what about work you can't accept? The wrong answer is an unbounded queue in front of the pool — that just relocates the pileup. The right answer is a **bounded queue plus shedding**: reject fast with a retryable signal.

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
			// so the caller backs off instead of hanging on us.
			s.shed(conn)
			s.metrics.Shed.Inc() // watch this: it's your saturation signal
			continue
		}
	}
}

func (s *AuthServer) shed(conn net.Conn) {
	defer conn.Close()
	_ = encodeAuthResponse(conn, Resp{
		Decision: "TRY_AGAIN", // maps to a 503-style retryable upstream
		Reason:   "at_capacity",
	})
}
```

The measured run shows the inversion exactly: unbounded made *every* request pay ~400–900ms and (in a real system with deadlines) many would time out *after* their CPU and downstream work was already spent. Bounded spent its fixed capacity only on requests it could finish in ~4ms, and the marginal requests cost almost nothing. A shed request is a channel-send that failed; a timed-out request is a full scoring pass, a held database row, and a doomed downstream call.

**The gotcha:** shedding is only correct if the caller treats the response as *retryable*, not as a decision. In anything transactional, a shed that an upstream interprets as "declined" is worse than slowness — the contract with the caller matters as much as the code. Shedding must be visibly, semantically distinct from a real answer.

---

## Sizing the limits (reason, don't copy)

The demo's numbers were *derived*, and that's the transferable part:

| Limit | What it protects | How to size it |
|---|---|---|
| `GOMAXPROCS` | CPU oversubscription | Core count; in containers, your CPU *quota* (see below) |
| Worker count | Total in-flight work | Little's Law: `workers ≈ target_throughput × avg_service_time`, then load-test around it |
| Queue depth | Burst absorption vs. latency | Small — enough for sub-second bursts; a deep queue is latency inversion waiting to happen |
| Downstream semaphore | The external dependency | Its documented/observed safe concurrency, minus headroom |

Worked example from the demo: service time ≈ 2.2ms, downstream capacity 16k/s, so Little's Law says ~35 workers keep the downstream saturated; I used 48 to cover scheduling slack, and the measured throughput landed within 5% of theoretical capacity. When your p99 stays flat as you approach the bound and sheds begin exactly at capacity, the limits are right.

The container note is its own post ([GOMAXPROCS in Kubernetes](/blog/posts/production-go-36-gomaxprocs-kubernetes.html)), but the one-line version: on an 8-core node with a 2-core quota, old defaults gave you 8 Ps and the kernel throttled the excess — modern Go is cgroup-aware, and if yours isn't, pin `GOMAXPROCS` to the quota.

---

## Key takeaways

- **Runnable is not running.** Only `GOMAXPROCS` goroutines execute at once; everyone else queues. Measured: 12,710 in-flight goroutines produced p99 ~895ms for work that costs ~2.2ms.
- **"Goroutines are cheap" is about creation, not admission.** ~2.7 KB each, measured — and that cheapness is why nothing pushes back when load exceeds capacity.
- **The scheduler isn't the bottleneck — your dependencies are.** Dispatch latency barely moved under 50k runnable goroutines; the collapse was queueing for a 32-slot downstream.
- **Bound at the real bottleneck.** A pool caps total in-flight work; a separate context-aware semaphore caps the scarce downstream. One acquire, one deferred release, only on success.
- **Prefer shedding to queueing.** The bounded run served its true capacity (within 5% of the Little's-Law number) at p99 4ms and rejected the rest instantly — and callers must treat sheds as retryable, never as answers.

---

## Further reading

- **"Scheduling In Go"** series by William Kennedy — the definitive working-level explanation of the G-M-P model, run queues, and work-stealing: [Ardan Labs blog](https://www.ardanlabs.com/blog).

---

*All measurements: Apple M1 Max (10 cores), Go 1.27, `GOMAXPROCS=10`, single run of the demo harness described above. Absolute numbers are machine-specific; the ratios are the lesson.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-07-17
Canonical: https://pratikdhanave.com/blog/posts/production-go-22-scheduler-under-contention.html
Attribution: please link the canonical URL when citing or quoting this post.
