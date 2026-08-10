# The sync Package

*When channels are the wrong tool — a working guide to shared memory and locks in Go: Mutex, RWMutex, WaitGroup, Once, Cond, Map, Pool, and the race detector that keeps you honest.*

---

Go's famous advice is "don't communicate by sharing memory; share memory by communicating." It's good advice, and it makes channels the first thing most people reach for. But it is a *default*, not a law. A large fraction of real concurrent Go — caches, counters, connection pools, lazily-initialized singletons — is plainer, faster, and easier to reason about when you protect a piece of shared memory with a lock than when you route every access through a goroutine and a channel.

The `sync` package is that other half of the story. This guide walks the primitives you actually reach for, when each earns its place, and the specific ways each one bites. Everything here is standard library; the only external tool is the race detector, which is built into the `go` command.

---

## When shared memory beats channels

Use a channel when you are **transferring ownership** of data or **coordinating** the flow of work between goroutines — a pipeline stage handing a value downstream, a worker pool draining a job queue, a signal that something happened. The channel *is* the design.

Reach for `sync` when the goroutines all touch **one piece of state that stays put** and you just need to serialize access to it. A hit counter, an in-memory map, a config struct that's read constantly and updated rarely — wrapping every read and write in a channel round-trip adds latency and ceremony for no benefit. A mutex says exactly what you mean: "only one goroutine in here at a time."

The honest test: if you find yourself building a goroutine whose entire job is to own a variable and answer request/reply channels, you've reinvented a mutex the hard way. Just use the mutex.

---

## sync.Mutex: the workhorse

A `Mutex` is a mutual-exclusion lock. `Lock()` blocks until the lock is free and then acquires it; `Unlock()` releases it. The region between the two is a **critical section** that exactly one goroutine occupies at a time.

```go
type Counter struct {
	mu    sync.Mutex
	count int
}

func (c *Counter) Inc() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.count++
}

func (c *Counter) Value() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.count
}
```

Two habits make mutex code reliable. First, **`defer c.mu.Unlock()` right after `Lock()`**. It guarantees the lock is released even if the critical section panics or returns early, and it keeps the pair visually adjacent so a later edit can't accidentally strand a lock. (The one time to skip `defer` is a hot path where you want to release *before* doing more work in the function — then unlock explicitly and be careful.) Second, keep the critical section **short and self-contained**: never call out to unknown code, block on I/O, or acquire a second lock while holding the first unless you have a strict, documented lock ordering. Holding a lock across a network call is how a whole service seizes up.

The zero value of a `Mutex` is a ready-to-use unlocked mutex, so you never initialize one — just embed it or declare it. And critically, note that `Value()` above takes the lock too. Reading an `int` *feels* atomic, but without synchronization the Go memory model gives you no guarantee another goroutine's write is ever visible. A read that races with a write is a data race, full stop.

**The gotcha:** never copy a `Mutex` — or any struct that contains one — after it has been used. A `Mutex` carries internal state (who holds it, who's waiting); copying it produces a second lock that shares none of that state, so the copy and the original no longer exclude each other. This bites most often silently: a method with a value receiver (`func (c Counter)` instead of `func (c *Counter)`) copies the whole struct, mutex included, on every call. Always use pointer receivers for types with a mutex, and pass them by pointer. `go vet` catches this class of bug — it reports "passes lock by value" — so run it in CI and treat the finding as a real error, not a nit.

---

## sync.RWMutex: many readers, one writer

An `RWMutex` distinguishes readers from writers. Any number of goroutines can hold the read lock (`RLock`/`RUnlock`) simultaneously, but the write lock (`Lock`/`Unlock`) is exclusive — it waits for all readers to leave and blocks new readers while held.

```go
type Config struct {
	mu     sync.RWMutex
	values map[string]string
}

func (c *Config) Get(key string) string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.values[key]
}

func (c *Config) Set(key, val string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.values[key] = val
}
```

The shape to look for is **read-mostly** state: configuration, routing tables, caches that are queried far more than they're mutated. There, letting readers proceed in parallel is a genuine win.

But an `RWMutex` is not a free upgrade over a plain `Mutex`. It does more bookkeeping, so each acquisition is more expensive; if the critical section is tiny (a map lookup, a field read), that overhead can outweigh the concurrency you gain, and a plain `Mutex` is actually faster. It also only helps when readers genuinely overlap and the work under the lock is non-trivial — if writes are frequent, readers wait for writers anyway and you've paid for machinery you don't use. Reach for `RWMutex` when you've established the workload is read-heavy, not reflexively.

---

## sync.WaitGroup: wait for a set of goroutines

A `WaitGroup` counts outstanding work. `Add(n)` raises the counter, each goroutine calls `Done()` (which decrements it) as it finishes, and `Wait()` blocks until the counter hits zero.

```go
func fetchAll(urls []string) []Result {
	results := make([]Result, len(urls))
	var wg sync.WaitGroup

	for i, url := range urls {
		wg.Add(1)
		go func() {
			defer wg.Done()
			results[i] = fetch(url)
		}()
	}

	wg.Wait()
	return results
}
```

Note the discipline: `wg.Add(1)` happens **before** the `go` statement, and `defer wg.Done()` is the first line of the goroutine. Writing to a distinct index of `results` per goroutine needs no lock — the goroutines touch disjoint memory, and `Wait()` establishes the happens-before edge that makes every write visible before `fetchAll` reads the slice back.

(A note on the loop variable: as of Go 1.22 each iteration gets a fresh `i` and `url`, so capturing them directly in the closure is safe. On Go 1.21 and earlier you had to shadow them — `i, url := i, url` — or every goroutine would see the final iteration's values.)

**The gotcha:** call `Add` from the goroutine that *spawns* the work, before launching it — never inside the goroutine itself. If `Add(1)` runs inside the new goroutine, `Wait()` can execute before that goroutine is scheduled, see a counter of zero, and return while work is still pending. Two related rules: don't reuse a `WaitGroup` for a new round until `Wait()` has fully returned, and never let the counter go negative (more `Done`s than `Add`s), which panics. A `WaitGroup` must not be copied after first use either — pass it by pointer, and `go vet` flags copies here too.

---

## sync.Once: exactly-once initialization

`Once` guarantees a function runs one time, no matter how many goroutines call it concurrently. Every caller blocks until that first run completes, so they all safely observe the initialized result.

```go
var (
	once     sync.Once
	instance *Client
)

func GetClient() *Client {
	once.Do(func() {
		instance = newExpensiveClient()
	})
	return instance
}
```

This is the clean answer to lazy singletons and one-time setup — a connection pool, a compiled regexp, a parsed config — without the double-checked-locking dance people write by hand and get subtly wrong. The function passed to `Do` runs at most once for the lifetime of that `Once` value; even if it panics, `Once` considers the attempt spent and will not retry.

That "spent even on panic" behavior is the thing to know: if your init can fail and you want retries, `Once` is the wrong tool — capture the error and handle it, or use a different pattern. Go 1.21 added the convenience wrappers `sync.OnceFunc`, `sync.OnceValue`, and `sync.OnceValues`, which return a function that memoizes a call or its result; they're often tidier than managing a bare `Once` plus package-level variables.

---

## sync.Cond: usually reach for a channel instead

A `Cond` is a condition variable — a way for goroutines to wait until some shared condition becomes true, and to be woken (`Signal` for one waiter, `Broadcast` for all) when another goroutine changes it. It's built around a lock you hold while checking the condition in a loop.

```go
c := sync.NewCond(&sync.Mutex{})
// waiter:
c.L.Lock()
for !ready {          // always re-check in a loop, never a bare if
	c.Wait()          // atomically unlocks, sleeps, re-locks on wake
}
c.L.Unlock()
```

`Cond` is correct but easy to misuse — you must always re-test the condition in a `for` loop after `Wait()` returns, because wakeups can be spurious and the condition may have changed again by the time you're scheduled. In practice, most "wait until X happens" problems in Go are cleaner with a channel: close one to broadcast a one-time event, or send on one to hand off. Keep `Cond` for the narrow case of many goroutines waiting on a repeatedly-changing shared predicate where a channel would be awkward — reach for it deliberately, not by default.

---

## sync.Map: a specialist, not a general map

`sync.Map` is a concurrent map you can use without wrapping it in your own mutex. It is tempting to treat it as "the thread-safe map," but that's a trap: for most workloads a plain `map` guarded by a `sync.Mutex` (or `RWMutex`) is simpler *and* faster.

`sync.Map` is optimized for two narrow patterns its own documentation calls out: keys that are written once and then read many times (a stable cache), and workloads where **different goroutines touch disjoint sets of keys**. In those cases its internal design avoids lock contention that a mutex-wrapped map would suffer. Outside those patterns — a map with churn, or many goroutines hammering the same keys — it can be *slower* than the naive approach, and its untyped `interface{}` API (`Load`, `Store`, `LoadOrStore`, `Delete`, `Range`) costs you compile-time type safety and adds allocation.

```go
var cache sync.Map // maps string -> *User

func getUser(id string) (*User, bool) {
	v, ok := cache.Load(id)
	if !ok {
		return nil, false
	}
	return v.(*User), true // type assertion required
}
```

Default to a mutex plus a typed map. Reach for `sync.Map` only after you've confirmed your access pattern matches one of the two it's built for — ideally with a benchmark, not a hunch.

---

## sync.Pool: reusing transient allocations

`sync.Pool` holds a set of temporary objects that can be reused to relieve pressure on the garbage collector. You `Get()` an object (the pool hands you a free one or calls your `New` func to make one), use it, and `Put()` it back for the next caller. It shines for short-lived, frequently-allocated objects like byte buffers in a hot request path.

```go
var bufPool = sync.Pool{
	New: func() any { return new(bytes.Buffer) },
}

func process(data []byte) {
	buf := bufPool.Get().(*bytes.Buffer)
	buf.Reset()          // pooled objects are dirty — reset before use
	defer bufPool.Put(buf)
	// ... use buf ...
}
```

Two things define correct use: objects you `Get` are in whatever state their last user left them, so **reset before use**, and the pool can drop any or all of its contents at any time (it's cleared during GC), so it's a cache for *reducing allocations*, never a place to store anything you must not lose. Whether pooling actually helps is a measurement question, not an assumption — I'll treat the performance profiling of `sync.Pool` (and how to tell if it's earning its keep) as its own topic elsewhere in this series.

---

## The race detector: your ground truth

None of this reasoning matters if you can't verify it, and data races are invisible until they aren't — they surface as impossible values, corrupted maps, and crashes that reproduce once a week. Go ships a race detector built into the toolchain:

```bash
go test -race ./...
go run -race ./cmd/server
go build -race -o server ./cmd/server
```

The `-race` flag instruments memory accesses and reports, with full goroutine stacks, any time two goroutines touch the same memory concurrently without synchronization and at least one is a write. It's a **dynamic** detector: it only flags races on code paths your tests actually exercise, so its value is proportional to your coverage of concurrent paths. It also raises memory use and slows execution, so you run it in CI and locally, not in production.

Make `go test -race` part of your standard CI. A green race build is the difference between "I reasoned about the locking and I think it's right" and "the tooling confirms these paths don't race." Both `go vet` (copied locks, misused `WaitGroup`s) and `-race` (actual data races) belong in every Go pipeline.

---

## Key takeaways

- **Channels coordinate; locks protect.** Use `sync` when goroutines share one piece of stationary state — don't route everything through channels out of dogma.
- **`Mutex` is the default lock.** `Lock` then `defer Unlock`, keep critical sections short, use pointer receivers, and never copy a mutex — `go vet` catches the copy.
- **`RWMutex` is for read-mostly state only.** It's more expensive per call; a plain `Mutex` wins for tiny critical sections or write-heavy loads.
- **`WaitGroup`: `Add` before the goroutine, `Done` in a `defer`, then `Wait`.** Calling `Add` inside the goroutine is a race.
- **`Once` is exactly-once, even on panic.** Perfect for lazy init; wrong if you need retry-on-failure.
- **`Cond` is niche — a channel is usually clearer.** `sync.Map` and `sync.Pool` are specialists; default to a mutex-guarded map and profile before pooling.
- **`go test -race` is non-negotiable.** It's the only thing that turns "I think it's correct" into evidence.

---

## Further reading

- [The `sync` package documentation](https://pkg.go.dev/sync) — the authoritative reference for every primitive above, including the precise contracts for `sync.Map`, `sync.Pool`, and the `Once` variants.
- [The Go Memory Model](https://go.dev/ref/mem) — what "happens-before" actually guarantees, and why an unsynchronized read of shared memory is undefined behavior, not just a stale value.
