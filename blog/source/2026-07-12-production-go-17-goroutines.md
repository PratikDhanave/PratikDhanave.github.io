# Goroutines

*What a goroutine actually is, why it is cheaper than a thread, and the one rule that separates working concurrent code from a program that quietly leaks itself to death: every goroutine you start must have a way to stop.*

---

Concurrency is the feature people reach for Go to get, and the goroutine is the primitive underneath all of it. Channels, `sync.WaitGroup`, worker pools, the `net/http` server that hands each request its own goroutine — all of it is built on one idea: you start a function running independently by putting the word `go` in front of the call. That is easy to write and surprisingly easy to get wrong. The syntax hides two questions that matter enormously in production: *when does this goroutine finish*, and *what happens if it never does*. This post answers both.

We will build up from what a goroutine is at runtime, through the semantics of `go f()`, to the two bugs that account for most concurrency incidents I have seen: forgetting to synchronize, and leaking goroutines that block forever.

---

## What a goroutine is

A goroutine is a function that runs concurrently with the rest of your program, scheduled by the Go runtime rather than the operating system. That last part is the whole trick. When you start a goroutine, you are not asking the OS for a thread — you are handing a function to Go's scheduler, which multiplexes many goroutines onto a small pool of OS threads.

The practical consequence is cost. An OS thread reserves a large fixed stack (commonly a megabyte or more) and every context switch goes through the kernel. A goroutine starts with a tiny stack — a couple of kilobytes — that **grows and shrinks on demand** as the call stack deepens. The runtime allocates a bigger stack and copies the goroutine's frames over when it needs more room, and reclaims the space when it doesn't. Because switching between goroutines happens in user space, it is far cheaper than a kernel thread switch.

This is why "just start a goroutine" is idiomatic in Go in situations where "just start a thread" would be reckless in other languages. Tens of thousands of live goroutines is normal; the same count of OS threads would exhaust memory.

```go
func main() {
    go greet("world") // runs concurrently; main does not wait
    fmt.Println("main keeps going")
}

func greet(name string) {
    fmt.Println("hello", name)
}
```

If you run that, you will often see `main keeps going` and *not* `hello world`. That is not a bug in the runtime — it is the single most important fact about goroutines, and the next section is entirely about it.

---

## `go f()` semantics: start and forget

`go f(args)` does exactly one thing: it evaluates `f` and its arguments *now*, on the current goroutine, then schedules the call to run on a new goroutine and immediately returns. It does not wait for `f` to run, let alone finish. There is no handle, no future, no join — the statement has no return value.

Two details trip people up:

- **Arguments are evaluated at the call site, immediately.** `go f(compute())` runs `compute()` on the calling goroutine before the new goroutine starts. Only the call to `f` is deferred.
- **A return value from `f` is discarded.** A goroutine's function can return a value, but there is nowhere for it to go. If you want a result out of a goroutine, you must send it somewhere — a channel is the usual answer.

Because `go` returns instantly, the calling code races ahead. In the `greet` example, `main` reaches the end of its body and the program exits before the scheduler ever runs `greet`. Which brings us to the lifecycle.

---

## The lifecycle, and why main exiting kills everything

A goroutine lives from the `go` statement that starts it until its function returns (or the whole program stops). There is no "goroutine finished" event you can subscribe to, and no built-in way to name or enumerate them.

The rule that surprises newcomers: **when `main` returns, the program exits immediately and every other goroutine is killed mid-flight.** No deferred functions in those goroutines run, no cleanup happens — the process is simply gone. `main` is not "the last goroutine to finish"; it is the goroutine whose exit ends the world.

So the `greet` program does not print `hello world` because `main` returned before the scheduler got around to `greet`. The fix is *not* to make `main` wait a little longer and hope. You have to synchronize.

**The gotcha:** the reflex fix is `time.Sleep`. Do not do this.

```go
func main() {
    go greet("world")
    time.Sleep(100 * time.Millisecond) // WRONG: a guess, not a guarantee
}
```

`time.Sleep` is a bet that the goroutine finishes within some arbitrary window. On a loaded CI box or under the race detector it will lose that bet, and you get a flaky test or a dropped write that only reproduces in production. Sleeping to wait for a goroutine is never correct — it either wastes time (you slept too long) or corrupts results (you slept too short). Use a real synchronization primitive.

---

## Synchronizing: WaitGroup and channels

There are two everyday tools for waiting on goroutines correctly.

A `sync.WaitGroup` is a counter. You `Add` before starting work, each goroutine calls `Done` when it finishes, and `Wait` blocks until the counter hits zero. It is the right choice when you just need to know *everyone is done*.

```go
func main() {
    var wg sync.WaitGroup
    for _, name := range []string{"world", "gophers", "reader"} {
        wg.Add(1)
        go func() {
            defer wg.Done() // runs even if greet panics-and-recovers
            greet(name)
        }()
    }
    wg.Wait() // blocks until all three Done calls land
}
```

Two habits make `WaitGroup` reliable: call `Add` *before* the `go` statement (not inside the goroutine, where it may run after `Wait` already returned), and `defer wg.Done()` as the goroutine's first line so it fires on every exit path.

When you need the *results* back, use a channel. A channel both transfers the value and synchronizes: the receive blocks until a send happens, so no separate wait is needed.

```go
func main() {
    results := make(chan int, 3) // buffered so senders never block
    for i := 1; i <= 3; i++ {
        go func() {
            results <- i * i
        }()
    }
    for i := 0; i < 3; i++ {
        fmt.Println(<-results) // each receive waits for one send
    }
}
```

Channels are worth their own post; the point here is that they are the idiomatic way to get a value *out* of a goroutine, and the receive doubles as your synchronization point.

---

## Goroutine leaks: the number one concurrency bug

Here is the failure mode I check for first in any concurrency review. A **goroutine leak** is a goroutine that blocks forever because nothing will ever unblock it. It never returns, so its stack is never reclaimed, and it sits there holding memory and whatever resources it captured — for the life of the process.

Leaks are insidious because the program keeps working. Nothing crashes. You just watch goroutine count and memory climb over hours or days until the service falls over. The most common shape is a goroutine that sends on a channel no one will ever receive from:

```go
// LEAK: if the caller returns early, the goroutine blocks on the send forever.
func firstResult(ctx context.Context, urls []string) (string, error) {
    ch := make(chan string) // unbuffered
    for _, u := range urls {
        go func() {
            ch <- fetch(u) // blocks until someone receives
        }()
    }
    select {
    case r := <-ch: // we take exactly ONE result
        return r, nil
    case <-ctx.Done():
        return "", ctx.Err()
    }
    // Every goroutine except the one we read is now blocked on `ch <- ...`
    // forever. One call, len(urls)-1 leaked goroutines.
}
```

The receiver takes one value and returns. Every other goroutine is stuck on `ch <- fetch(u)` with no receiver left — permanently. Call this in a loop and you leak a goroutine per URL per call, forever.

The rule that prevents this: **every goroutine you start must have a guaranteed way to exit.** If a goroutine can block, there must be something that eventually unblocks it on *every* path, including the paths where the caller gives up early.

Two fixes apply here. The simplest is to give the send somewhere to go by buffering the channel so a send never blocks even if no one reads:

```go
func firstResult(ctx context.Context, urls []string) (string, error) {
    ch := make(chan string, len(urls)) // buffer for ALL senders
    for _, u := range urls {
        go func() {
            ch <- fetch(u) // never blocks: buffer has room for everyone
        }()
    }
    select {
    case r := <-ch:
        return r, nil
    case <-ctx.Done():
        return "", ctx.Err()
    }
}
```

Now the goroutines whose results we ignore still complete their send into the buffer and return normally. The buffer holds values nobody reads, but the goroutines are gone and the channel is garbage-collected once unreferenced.

The more general fix is a **cancellation signal** — usually `context.Context` — so a goroutine can abandon a blocking operation instead of hanging on it:

```go
func worker(ctx context.Context, jobs <-chan Job) {
    for {
        select {
        case job, ok := <-jobs:
            if !ok {
                return // channel closed: no more work, exit cleanly
            }
            process(job)
        case <-ctx.Done():
            return // cancelled: stop waiting and exit
        }
    }
}
```

This goroutine has *two* exits: the jobs channel being closed, and the context being cancelled. It cannot get wedged waiting on `jobs` forever, because `ctx.Done()` is always another way out. That is the shape you want every long-lived goroutine to have — a closed channel or a cancelled context that guarantees it returns.

**The gotcha:** a leaked goroutine does not show up in normal testing because the program produces the right answer — the leak is invisible until you measure it. Watch `runtime.NumGoroutine()` in tests around a function that spawns goroutines: if the count is higher after than before, you have a leak. The `go.uber.org/goleak` package automates exactly this check in test teardown, and I treat a leak it flags as a failing test, not a warning.

---

## Capturing loop variables

For years the classic Go gotcha was capturing a loop variable in a goroutine:

```go
// Behavior depends on your Go version.
for _, name := range []string{"a", "b", "c"} {
    go func() {
        fmt.Println(name)
    }()
}
```

**Before Go 1.22**, the loop variable `name` was a *single* variable reused across every iteration. All three goroutines closed over the same `name`, and since they run later, they typically all saw the final value — printing `c c c` (in some order) instead of `a b c`. The fix was to shadow the variable per iteration (`name := name`) or pass it as an argument (`go func(n string) {...}(name)`).

**As of Go 1.22**, the language changed: loop variables in `for` statements are now scoped *per iteration*. Each goroutine captures its own `name`, and the loop above prints `a`, `b`, `c` as you'd expect. The old workaround is now redundant but harmless.

**The gotcha:** the version matters. The per-iteration semantics apply only when the module's `go` directive in `go.mod` is `1.22` or higher — the compiler keys the behavior off the language version the module targets. If you maintain code that must build under older toolchains, or a module still declaring `go 1.21`, the old capture bug is live and the explicit `name := name` shadow is still your protection. When reading unfamiliar code, check `go.mod` before you trust a bare capture.

---

## You rarely spawn goroutines unbounded

One last discipline that separates toy code from production code. Every example above starts a fixed, known number of goroutines. Real systems get input they don't control — a queue with a million messages, a slice of user-supplied URLs, a firehose of requests. The naive `for _, x := range hugeSlice { go work(x) }` starts *one goroutine per item*, and while goroutines are cheap, they are not free: a million of them will exhaust memory or bury a downstream service in concurrent calls.

The production pattern is a **bounded worker pool** — a fixed number of goroutines pulling from a shared channel — so concurrency is capped no matter how much work arrives. The details of that pattern, along with how the runtime scheduler actually maps goroutines onto threads (the G-M-P model), deserve their own treatment and I will cover them in a later post on the scheduler and worker pools. For now, hold the rule: unbounded input should never mean unbounded goroutines.

---

## Key takeaways

- **A goroutine is a runtime-scheduled function with a small, growable stack** — cheap enough to start thousands of, because the Go scheduler multiplexes them onto a few OS threads instead of one thread each.
- **`go f()` starts and returns immediately.** Arguments are evaluated at the call site; the return value is discarded. There is no built-in way to wait.
- **When `main` returns, all other goroutines die instantly** with no cleanup. You must synchronize to wait — use `sync.WaitGroup` or a channel, **never `time.Sleep`**.
- **The number one concurrency bug is the goroutine leak:** a goroutine blocked forever because no one reads or cancels. Give every goroutine a guaranteed exit — a buffered channel, a closed channel, or a cancelled `context`.
- **Loop-variable capture is fixed in Go 1.22** (per-iteration scoping), but the old `c c c` bug is live in modules targeting Go 1.21 or earlier — check `go.mod`.
- **Don't spawn goroutines unbounded** over input you don't control; a bounded worker pool caps concurrency.

---

## Further reading

- [Effective Go — Goroutines](https://go.dev/doc/effective_go#goroutines) — the canonical description of the primitive and how `go` statements behave.
- [The Go Blog](https://go.dev/blog/) — deeper pieces on concurrency patterns, channels, and context; start with the concurrency-patterns and pipelines articles.
