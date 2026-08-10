# Channels and select

*A working guide to Go's channels — unbuffered rendezvous vs buffered capacity, send/receive/close semantics, directional types in APIs, and how `select` multiplexes, times out, and disables cases with a nil channel.*

---

Goroutines are cheap to start. The hard part is getting them to talk without corrupting shared state or deadlocking. Channels are Go's answer: a **typed conduit** that carries values from one goroutine to another and, just as importantly, synchronizes the two at the moment of handoff. The Go proverb is "don't communicate by sharing memory; share memory by communicating" — and channels make that slogan practical.

This guide walks through what a channel actually guarantees, unbuffered vs buffered channels, the rules around closing (which trip up nearly everyone at first), and `select` — the control structure that turns one channel into a real concurrency toolkit.

---

## A channel is a typed conduit with a synchronization guarantee

You create a channel with `make`, and its type includes the element type it carries. A `chan int` moves `int` values; nothing else will compile.

```go
ch := make(chan int)   // unbuffered
ch <- 42               // send: blocks until a receiver is ready
v := <-ch              // receive: blocks until a sender is ready
```

The arrow always points *in the direction the value flows*: into the channel on a send, out of it on a receive. Beyond moving data, a channel establishes a **happens-before** relationship — everything the sending goroutine did before the send is visible to the receiving goroutine after the receive. That memory guarantee is why you can pass a pointer or a slice through a channel and read it safely on the other side without a mutex.

---

## Unbuffered channels: a synchronous rendezvous

An unbuffered channel (`make(chan T)`, capacity zero) has no room to hold a value. A send blocks until some other goroutine is ready to receive, and a receive blocks until some goroutine is ready to send. The two operations complete together, at the same instant — a **rendezvous**.

```go
func main() {
	done := make(chan struct{})

	go func() {
		fmt.Println("worker: doing work")
		done <- struct{}{} // won't complete until main receives
	}()

	<-done // blocks here until the worker sends
	fmt.Println("main: worker finished")
}
```

Because the send and receive are simultaneous, an unbuffered channel is a **signal** as much as a transport. The `chan struct{}` idiom above carries no data — a zero-size `struct{}` value costs nothing — it exists purely to mark "this happened." Use unbuffered channels when you want a guarantee that the receiver has actually taken the value, not merely that you managed to hand it off.

---

## Buffered channels: capacity and asynchrony up to the cap

Give `make` a second argument and the channel gains an internal buffer. A send succeeds immediately as long as the buffer has room; only when the buffer is full does a send block. Symmetrically, a receive succeeds while the buffer holds values and blocks only when it's empty.

```go
ch := make(chan int, 2) // capacity 2
ch <- 1                 // fits, returns immediately
ch <- 2                 // fits, returns immediately
// ch <- 3              // would block: buffer full, no receiver yet

fmt.Println(<-ch, <-ch) // 1 2 — FIFO order
```

`len(ch)` reports how many values are currently queued; `cap(ch)` reports the capacity. Buffering decouples sender and receiver *up to the cap* — useful when producers and consumers run at uneven rates. It is **not** an unbounded queue and not a substitute for correct synchronization: pick a capacity for a concrete reason (a known batch size, a bounded worklist), not as a guess to "make blocking go away." A too-large buffer just hides backpressure until it's a bigger problem.

**The gotcha:** a buffered channel does not guarantee the receiver ever ran. `ch <- x` on a channel with spare capacity returns whether or not anyone is listening, so a "done" signal sent over a buffered channel can be lost if the program exits first. When you need proof of delivery, use an unbuffered channel.

---

## Receiving, closing, and the two-value receive

A sender can `close` a channel to announce that no more values are coming. Closing is a broadcast: every current and future receiver sees it.

Receiving from a closed channel never blocks. It drains any buffered values first, then returns the element type's **zero value** forever after. The two-value form of receive tells you which case you're in:

```go
v, ok := <-ch
// ok == true : v is a real value sent on the channel
// ok == false: the channel is closed AND drained; v is the zero value
```

That `ok` flag is the only reliable way to distinguish "a real zero was sent" from "the channel is closed." Ranging over a channel wraps this up for you: `for v := range ch` receives values until the channel is closed and drained, then exits the loop cleanly.

```go
func produce(n int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out) // sender closes when finished
		for i := 0; i < n; i++ {
			out <- i * i
		}
	}()
	return out
}

func main() {
	for v := range produce(5) {
		fmt.Println(v) // 0 1 4 9 16, then the loop ends
	}
}
```

---

## Who closes a channel — and the rules you cannot break

There is one owner of a channel's lifecycle, and it is the **sender**. The receiver must never close a channel, because a receiver has no way to know whether another goroutine is still about to send. Three rules follow, and violating them is a runtime panic, not a compile error:

- **Sending on a closed channel panics.** So does closing an already-closed channel.
- **Closing is optional.** You only need to close when a receiver relies on it — typically to terminate a `range`. A channel that is simply garbage-collected doesn't need closing.
- **The sender closes; the receiver detects.** If several goroutines send on one channel, none of them may close it unilaterally. Coordinate them (for example with a `sync.WaitGroup`) and let a single goroutine close once they've all finished.

```go
func fanIn(sources ...<-chan int) <-chan int {
	out := make(chan int)
	var wg sync.WaitGroup
	wg.Add(len(sources))
	for _, s := range sources {
		go func(c <-chan int) {
			defer wg.Done()
			for v := range c {
				out <- v
			}
		}(s)
	}
	go func() {
		wg.Wait()  // wait for every sender to finish
		close(out) // exactly one close, by one goroutine
	}()
	return out
}
```

**The gotcha:** `close` means "no more sends," not "stop receiving." Receivers can and should keep draining after a close to collect buffered values. If you want to signal receivers to stop *sending* to you, that's a different channel (or a `context.Context`) flowing the other way — closing your output channel doesn't do it.

---

## Directional channel types make APIs honest

A function that only sends should accept a **send-only** channel; one that only receives should accept a **receive-only** channel. The syntax puts the arrow next to `chan`:

```go
func emit(out chan<- int)      { out <- 1 }    // send-only: may send (and close), cannot receive
func drain(in <-chan int) int  { return <-in } // receive-only: may receive, cannot send or close
```

A bidirectional `chan int` converts implicitly to either directional type, but not back — so once a function has a `<-chan int`, the compiler forbids it from sending or closing. This is not decoration: it moves a whole class of "wrong goroutine closed the channel" bugs from runtime panics to compile errors. Notice the `produce` and `fanIn` examples above return `<-chan int` — callers can only receive, which documents ownership and enforces it. Make your channel-returning functions hand back the narrowest direction the caller needs.

---

## select: multiplexing over multiple channels

`select` is to channels what `switch` is to values: it lets a goroutine wait on several channel operations at once and proceeds with whichever is ready first.

```go
select {
case v := <-in1:
	fmt.Println("from in1:", v)
case v := <-in2:
	fmt.Println("from in2:", v)
case out <- compute():
	fmt.Println("sent a result")
}
```

If exactly one case is ready, that case runs. If **several** are ready simultaneously, `select` picks one **at random** — a deliberate design choice that prevents starvation, so you can never assume the first-listed ready case wins. If **no** case is ready, `select` blocks until one becomes ready (unless there's a `default`, below).

---

## default: making select non-blocking

Add a `default` case and `select` stops blocking: if no channel operation is ready *right now*, it runs `default` immediately. This turns `select` into a try-send or try-receive.

```go
// Non-blocking send: drop the value if nobody's ready to take it.
select {
case ch <- value:
	// delivered
default:
	// buffer full / no receiver — skip rather than block
}

// Non-blocking receive: poll without waiting.
select {
case v := <-ch:
	handle(v)
default:
	// nothing available right now
}
```

This pattern is how you implement dropping under load, or a poll that must never stall. Use it deliberately: a `default` inside a tight `for` loop with nothing else to wait on becomes a **busy-wait** that pins a CPU core. If the goal is "wait, but not forever," reach for a timeout instead.

---

## Timeouts with time.After

Because `time.After` returns a channel that delivers a value after a duration, it drops straight into a `select` as a timeout arm:

```go
select {
case res := <-work:
	fmt.Println("result:", res)
case <-time.After(2 * time.Second):
	fmt.Println("timed out waiting for work")
}
```

Whichever fires first wins. If `work` produces within two seconds you take the result; otherwise the timer's channel becomes ready and you bail out. For a deadline shared across many operations, prefer a `context.Context` with `context.WithTimeout` and select on `ctx.Done()` — but `time.After` is the right tool for a single, local wait.

**The gotcha:** in a long-running loop, `time.After(d)` allocates a fresh timer *every iteration*, and the old timer isn't collected until it fires. For a hot loop, create one `time.NewTimer` (or `time.NewTicker`) outside the loop and reset it, so you're not leaking timers under the covers.

---

## nil channels block forever — the disable-a-case trick

A receive or send on a `nil` channel blocks *forever*. That sounds like a pure hazard, but it's the cleanest way to **disable a case** in a `select`: a `nil` channel case can never be selected, so setting a channel variable to `nil` removes its arm from consideration on the next loop iteration.

```go
func merge(a, b <-chan int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for a != nil || b != nil { // keep going while either is live
			select {
			case v, ok := <-a:
				if !ok {
					a = nil // a is drained; disable this case
					continue
				}
				out <- v
			case v, ok := <-b:
				if !ok {
					b = nil // b is drained; disable this case
					continue
				}
				out <- v
			}
		}
	}()
	return out
}
```

Without the nil trick, a closed channel stays *permanently ready* in a `select` — it fires instantly with `ok == false` on every iteration, spinning the loop. Nilling the drained channel takes its case out of the running so `select` waits properly on whatever's left, and the loop condition `a != nil || b != nil` gives you a clean exit once both are done.

**The gotcha:** the closed-channel-stays-ready behavior is exactly why a naive `select` over channels you never nil out can turn into a hot spin after one of them closes. If a `select` loop suddenly burns CPU, suspect a closed channel whose case you forgot to disable.

---

## Channels or a mutex? Choosing between the two models

Channels are not always the right tool. Go ships `sync.Mutex` precisely because some problems are about protecting state, not moving it. A rough guide:

| Situation | Reach for |
|---|---|
| Transferring ownership of data between goroutines | Channel |
| Pipelines / producer-consumer / fan-in-fan-out | Channel |
| Signaling events, cancellation, completion | Channel (or `context`) |
| Guarding a field or map read/written by many goroutines | Mutex |
| A simple counter or cache with short critical sections | Mutex (or `sync/atomic`) |
| Distributing work across N workers | Channel (a job queue) |

The heuristic: if a value has an **owner** that changes over time, pass it on a channel so ownership moves with it; if a value is **shared state** several goroutines poke at in place, protect it with a mutex. Mixing the two is fine — a worker pool often uses channels to hand out jobs and a mutex to accumulate results into a shared map. Don't force everything through channels for purity's sake; a mutex around three lines is clearer than a goroutine and two channels to serialize the same access.

---

## Key takeaways

- **A channel synchronizes as it transports.** The value handoff also establishes happens-before, which is what makes passing pointers between goroutines safe.
- **Unbuffered = rendezvous, buffered = capacity.** Unbuffered proves the receiver took the value; buffered decouples the two up to `cap`. Size a buffer for a reason, never to paper over blocking.
- **The sender closes, never the receiver.** Sending on or closing a closed channel panics. Use the `v, ok := <-ch` form (or `range`) to detect closure and drain cleanly.
- **Directional types (`chan<-`, `<-chan`) turn ownership bugs into compile errors.** Return the narrowest direction your caller needs.
- **`select` multiplexes; `default` makes it non-blocking; `time.After` times it out.** Ready cases are chosen at random — never assume ordering.
- **A `nil` channel blocks forever — use it to disable a `select` case** once a source is drained, and to avoid the hot spin a closed channel would otherwise cause.
- **Share memory by communicating — but keep the mutex.** Channels move ownership; a mutex guards shared state. Pick the model that matches the problem.

---

## Further reading

- [Effective Go — Channels](https://go.dev/doc/effective_go#channels)
- [The Go Blog — Go Concurrency Patterns: Pipelines and cancellation](https://go.dev/blog/pipelines)
