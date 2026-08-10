# Atomics and the Go Memory Model

*What a data race actually is, why it is undefined behavior rather than "just a wrong number," the happens-before rules that make concurrent code correct, and when `sync/atomic` is the right tool — and when it quietly is not.*

---

Most Go developers learn concurrency as a set of recipes: put `go` in front of a call, guard shared state with a `sync.Mutex`, pass values over channels. The recipes work, but they leave a gap. Sooner or later you write `counter++` from two goroutines, notice it produces the wrong total, reach for `sync/atomic`, and it fixes the number. What you have not learned is *why* the plain `counter++` was broken, why it was broken even though `int` is a single machine word, and why "it printed the right answer on my laptop" is not evidence of anything.

That gap is the Go memory model. It is the contract that says which writes in one goroutine are guaranteed to be visible to reads in another. This post works through it at the level you actually need in production: what a data race is, the happens-before relation that defines correctness, what `sync/atomic` gives you, and the sharp edge that catches experienced people — atomics do not compose.

---

## What a data race is

A data race has a precise definition, and it is worth memorizing because every rule downstream follows from it. A data race occurs when:

1. two or more goroutines access the same memory location,
2. at least one of those accesses is a write, and
3. the accesses are not ordered by a synchronization event.

All three conditions must hold. Two goroutines reading the same variable is fine — no write, no race. A goroutine reading and another writing, but with a mutex serializing them, is fine — the accesses are ordered. Remove the ordering while one side writes, and you have a race.

```go
// DATA RACE: two goroutines, both writing, no synchronization.
func main() {
    var counter int
    var wg sync.WaitGroup
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter++ // read counter, add 1, write counter — three steps, no lock
        }()
    }
    wg.Wait()
    fmt.Println(counter) // almost never 1000
}
```

The reason this loses increments is that `counter++` is not one operation. It is a load, an add, and a store. Two goroutines can both load `41`, both add one, and both store `42` — two increments, one net change. The `WaitGroup` correctly waits for every goroutine to finish, but it does nothing to order the accesses *to `counter`* against each other. That is the missing third condition.

---

## A race is undefined behavior, not a wrong number

Here is the part that trips up people who think of a race as "sometimes I lose an update." Under the Go memory model, a program with a data race has **no defined behavior at all** for the racing accesses. It is not "you get one of the two values." The specification makes no promise about what you get.

In practice this means more than a lost increment. A racing read of a multi-word value — an interface, a slice header, a string, a `map` — can observe a **torn** value: the pointer half from one write and the length half from another, a combination that was never actually stored. Dereference that and you get a crash, not a wrong answer. The runtime explicitly detects concurrent map writes and aborts the process with `fatal error: concurrent map writes` precisely because the alternative is silent corruption.

**The gotcha:** "it works on my machine" tells you nothing about a racy program. Compilers are permitted to assume race-free code, so the optimizer may hoist a load out of a loop, cache a value in a register, or reorder stores — all legal transformations that change racy behavior between `-race` and release builds, between architectures (x86 has stronger memory ordering than ARM), and between Go versions. A race that "passes" today is not fixed; it is unobserved. Treat every race as a correctness bug, never a performance quirk.

---

## The memory model, at a working level

The Go memory model is built on one relation: **happens-before**. If event A happens-before event B, then A's effects are guaranteed visible to B. If neither happens-before the other, they are *concurrent*, and concurrent access where one side writes is exactly a data race.

Within a single goroutine, happens-before matches program order — line 1 happens-before line 2, as you would expect. The interesting question is *across* goroutines, and the answer is that you only get a happens-before edge through an explicit synchronization operation. The everyday ones:

- **Channel operations.** A send on a channel happens-before the corresponding receive completes. And the close of a channel happens-before a receive that returns because the channel is closed. This is why passing a value over a channel is safe: the send publishes everything the sending goroutine did beforehand.
- **Mutex.** For a `sync.Mutex`, the *n*-th `Unlock` happens-before the *(n+1)*-th `Lock` returns. Unlocking publishes your writes to whoever locks next.
- **`sync.Once`.** The single call to `once.Do(f)` completes (returns from `f`) happens-before any other `once.Do(f)` returns. That is what makes lazy initialization safe.
- **`sync.WaitGroup`.** The `Done` calls (which decrement the counter) happen-before the `Wait` that they release. So work done before `Done` is visible after `Wait` returns.
- **`sync/atomic`.** An atomic write happens-before a subsequent atomic read of the same location that observes the written value (Go's atomics are sequentially consistent).

Notice what is *not* on this list: `time.Sleep`, print statements, plain variable assignments, and "the goroutine obviously ran first." None of those establish happens-before. If the only thing connecting a write in one goroutine to a read in another is that you are *pretty sure* of the timing, you have a race.

```go
// The channel makes this correct.
func main() {
    done := make(chan struct{})
    var result int
    go func() {
        result = expensiveComputation() // write
        close(done)                     // publishes the write
    }()
    <-done                              // receive happens-after the close
    fmt.Println(result)                 // guaranteed to see the write
}
```

The write to `result` happens-before `close(done)` (same goroutine, program order), and `close(done)` happens-before the `<-done` receive completes (channel rule). Happens-before is transitive, so the write happens-before the read. No race, no atomics needed — the channel already did the synchronization.

---

## `sync/atomic`: the typed atomics

When you genuinely need shared mutable state and a full mutex is heavier than the job warrants — a counter, a flag, a hot-swapped pointer — `sync/atomic` gives you operations that are indivisible and that establish happens-before.

Since Go 1.19 the idiomatic form is the **typed atomic**: `atomic.Int64`, `atomic.Int32`, `atomic.Uint64`, `atomic.Bool`, and the generic `atomic.Pointer[T]`. Prefer these over the older free functions (`atomic.AddInt64(&x, 1)` and friends). The typed wrappers make the atomic contract part of the variable's type, so there is no way to accidentally touch the value non-atomically, and they carry no alignment footguns.

```go
type Metrics struct {
    requests atomic.Int64
    healthy  atomic.Bool
}

func (m *Metrics) OnRequest() {
    m.requests.Add(1) // atomic read-modify-write; no lost increments
}

func (m *Metrics) Count() int64 {
    return m.requests.Load() // atomic read
}
```

`m.requests.Add(1)` fixes the earlier broken counter: the load-add-store now happens as one indivisible step, and each `Add` establishes happens-before the next. The core methods are worth knowing by name:

- **`Load`** / **`Store`** — atomic read and write of the whole value.
- **`Add`** — atomic read-modify-write, returning the new value.
- **`Swap`** — store a new value, return the old one, atomically.
- **`CompareAndSwap`** (CAS) — if the current value equals `old`, set it to `new` and report success; otherwise do nothing. This is the primitive for lock-free algorithms.

**The gotcha:** never mix atomic and non-atomic access to the same variable. If one goroutine does `x.Store(5)` and another reads the underlying value directly (or you memcpy a struct containing an `atomic.Int64`), you are back to a data race — the atomic guarantee only holds when *every* access goes through the atomic methods. For the same reason, do not copy an atomic value after first use; the `sync` types (and `go vet`'s `copylocks` check) exist to catch this. Pass a pointer to the struct that contains them.

---

## Why one word is still a race

A frequent misconception: "`int` is a single machine word, so `x = 5` is atomic anyway — I don't need synchronization for a single word." This is wrong for two independent reasons, and both matter.

First, **atomicity is not visibility.** Even if the store lands in one instruction, nothing forces another goroutine's read to *observe* it. Without a happens-before edge, the compiler may keep the value in a register and the CPU may reorder the store relative to other stores. A goroutine spinning on a plain `for !done {}` can loop forever even after another goroutine sets `done = true`, because the compiler is entitled to hoist the load out of the loop — it never re-reads memory.

Second, **the compiler assumes no races.** Once you have a race, the optimizer's transformations are no longer required to preserve the behavior you imagined, so reasoning about "well, the write is one instruction" is moot. The specification has already declared the behavior undefined.

The fix is to make the shared flag an atomic:

```go
var done atomic.Bool

func worker() {
    for !done.Load() { // re-reads memory every iteration; sees the Store
        doWork()
    }
}

func stop() {
    done.Store(true) // establishes happens-before with the Load that sees it
}
```

`atomic.Bool` is not needed because a `bool` is "too big" to write in one step — it is needed because `Load`/`Store` are the only way to get the *happens-before edge* that makes the write visible and forbids the compiler from caching the read.

---

## A correct CAS loop

`CompareAndSwap` is how you build a lock-free update when the new value depends on the old one and a plain `Add` will not express it — for example, clamping a maximum:

```go
// RecordMax atomically raises the stored high-water mark to v if v is larger.
func RecordMax(max *atomic.Int64, v int64) {
    for {
        old := max.Load()
        if v <= old {
            return // already at or above v; nothing to do
        }
        if max.CompareAndSwap(old, v) {
            return // we won the race: old was still current, swap succeeded
        }
        // Another goroutine changed max between our Load and CAS.
        // Loop and retry with the fresh value.
    }
}
```

The shape is the canonical CAS loop and worth internalizing: read the current value, compute the new value from it, then attempt to swap *only if nothing changed in between*. If the `CompareAndSwap` fails, some other goroutine moved the value, so your computed update is stale — you loop, re-read, and try again. The loop is not busy-waiting on a lock; each iteration either succeeds or means real contention that another goroutine resolved. This is exactly how `Add` is implemented under the hood, and it generalizes to any single-word update you can express as "compute from old, install if unchanged."

---

## Atomics do not compose

This is the failure I see most from developers who have learned atomics well enough to trust them too far. Each atomic operation is individually safe. **A sequence of atomic operations is not.**

```go
type Account struct {
    balance  atomic.Int64
    lastTxID atomic.Int64
}

// BROKEN: two atomics, but the pair is not atomic together.
func (a *Account) Deposit(amount, txID int64) {
    a.balance.Add(amount)     // step 1: atomic
    a.lastTxID.Store(txID)    // step 2: atomic
    // Between step 1 and step 2 another goroutine can observe the new
    // balance with the OLD lastTxID — an invariant violation.
}
```

Each line is atomic in isolation, but there is no atomicity *across* the two. Another goroutine can read `balance` after step 1 and `lastTxID` before step 2 and see a state that is internally inconsistent. Atomics protect a single memory location; they cannot protect an *invariant that spans multiple fields*.

**The gotcha:** the moment your correctness condition involves more than one variable — "balance and lastTxID must agree," "the length and the backing array must match," "read the config and the version together" — atomics are the wrong tool. Use a `sync.Mutex` (or `sync.RWMutex`) to make the whole update a single critical section:

```go
type Account struct {
    mu       sync.Mutex
    balance  int64
    lastTxID int64
}

func (a *Account) Deposit(amount, txID int64) {
    a.mu.Lock()
    defer a.mu.Unlock()
    a.balance += amount   // both fields updated inside one critical section:
    a.lastTxID = txID     // no other goroutine can observe a half-done state
}
```

The rule of thumb: reach for `sync/atomic` when the shared state is a *single* value — a counter, a flag, a pointer you hot-swap wholesale. The instant you need two things to change together, or a read to see a consistent snapshot of several fields, use a mutex. Atomics buy you speed at the cost of composability, and paying that cost where you need multi-field invariants is how you ship a subtle corruption bug.

---

## The race detector

You do not have to reason about all of this by inspection. Go ships a **race detector** that instruments memory accesses at runtime and reports any that are unsynchronized. Turn it on with the `-race` flag:

```bash
go test -race ./...
go run -race ./cmd/server
go build -race -o server ./cmd/server
```

When it finds a race it prints both stacks — the read and the conflicting write — with the goroutines that made them, which usually points straight at the bug. Two things to understand about it. First, it has **no false positives**: if `-race` reports a race, there is a race, full stop. Second, it only detects races on code paths that *actually execute during the run*, so its coverage is exactly your test coverage — a race in a branch your tests never hit stays invisible.

**The gotcha:** the detector adds significant overhead (memory use and CPU both climb several-fold), so it is a testing and CI tool, not something you run in production. The discipline that works: run your whole test suite under `-race` in CI, and make sure the concurrent paths are actually exercised by tests. A race the detector never runs is a race it never finds — so the value you get out is only as good as the concurrency your tests drive.

---

## Key takeaways

- **A data race is a precise thing:** concurrent access to one location, at least one write, no synchronization ordering them. All three conditions must hold.
- **A race is undefined behavior, not a wrong number.** It can tear multi-word values and crash, and the compiler is free to optimize racy code in ways that differ across builds and architectures. "Works on my machine" proves nothing.
- **The memory model is happens-before.** Only explicit synchronization — channel ops, mutex Lock/Unlock, `sync.Once`, `WaitGroup`, and atomics — creates the visibility edge. `time.Sleep` and timing intuition do not.
- **Prefer the typed atomics** (`atomic.Int64`, `atomic.Bool`, `atomic.Pointer[T]`, Go 1.19+) over the old free functions, and never mix atomic and non-atomic access to the same variable.
- **A plain shared `var x int` is a race even though it is one word** — atomicity is not visibility, and the optimizer assumes no races. Use `Load`/`Store` for the happens-before edge.
- **Atomics do not compose.** They protect a single location; the moment an invariant spans multiple fields, use a mutex to make the whole update one critical section.
- **Run `go test -race` in CI.** It has no false positives, but it only catches races on code your tests actually execute.

---

## Further reading

- [The Go Memory Model](https://go.dev/ref/mem) — the authoritative specification of happens-before and exactly which operations establish it. Short, precise, and worth reading in full.
- [`sync/atomic` package documentation](https://pkg.go.dev/sync/atomic) — the typed atomics, their methods, and the alignment and copying caveats.
