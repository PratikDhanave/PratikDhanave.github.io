# Escape Analysis and Allocation Discipline

*How a ledger-posting path that looked innocent was quietly minting garbage on every transaction — and how reading the compiler's escape-analysis output turned a GC-bound service back into a CPU-bound one.*

---

The pager went off during a Friday settlement window. Nothing was down. Latency was up — p99 on our ledger-posting endpoint had crept from single-digit milliseconds into the tens, and it correlated almost perfectly with volume. Double the transactions per second, double the tail. That shape is a tell: it's rarely a slow dependency and almost always something we're doing *per request* that scales with load. In our case the CPU flame graph was dominated by `runtime.mallocgc` and `runtime.scanobject`. We weren't slow because of the work. We were slow because of the *garbage* the work produced.

This post is about the discipline that came out of that week: how Go decides whether a value lives on the stack or the heap, how to read `-gcflags="-m"`, and how to treat allocations on a hot path as a budget rather than an afterthought. The runtime concept underneath all of it is **escape analysis** — the compiler pass that decides who cleans up after each value you create.

---

## Stack is free; heap has a bill

A value on the stack costs nothing to reclaim. When the function returns, the stack pointer moves and the memory is gone — no bookkeeping, no collector, no scan. A value on the heap is the opposite: the garbage collector has to track it, mark it as reachable on every cycle, and eventually sweep it. On a path that runs a few thousand times a second, the difference between "this struct lives on the stack" and "this struct escapes to the heap" is the difference between a rounding error and a GC-pressure incident.

The critical thing to internalize: **you do not choose stack or heap in Go.** There is no `alloca`, no placement control. The compiler chooses, and its rule is a safety rule, not a performance one. If the compiler can prove a value does not outlive the function that created it, the value stays on the stack. If it *cannot* prove that, the value "escapes" to the heap, where it's safe. Escape analysis is that proof engine. Every heap allocation on your hot path is the compiler telling you "I couldn't prove this was safe on the stack." Our job isn't to fight the compiler — it's to write code whose lifetimes the compiler can actually reason about.

---

## The offending path

Here's a lightly disguised version of the ledger-posting code that was minting garbage. It takes a batch of postings, formats a per-entry key, and appends normalized rows to an audit buffer. Read it with allocation in mind.

```go
type Posting struct {
	Account  string
	Amount   int64 // minor units
	Currency string
	Ref      string
}

type AuditRow struct {
	Key   string
	Line  string
	Delta int64
}

// Logger is satisfied by our structured logger.
type Logger interface {
	Debug(msg string)
}

func PostBatch(entries []Posting, log Logger) []AuditRow {
	var rows []AuditRow // grows via append, no capacity hint
	for _, e := range entries {
		key := fmt.Sprintf("%s:%s", e.Account, e.Currency)
		line := fmt.Sprintf("post %s %d %s ref=%s", e.Account, e.Amount, e.Currency, e.Ref)
		log.Debug(line) // interface call in the hot loop
		rows = append(rows, AuditRow{Key: key, Line: line, Delta: e.Amount})
	}
	return rows
}
```

It's clean, readable, and it allocates on nearly every line. `fmt.Sprintf` allocates. The `append` onto a nil slice reallocates repeatedly as it grows. `log.Debug(line)` passes a `string` through an `interface`. And the whole `rows` slice is returned, so it has to escape. Four independent allocation sources, all inside a loop that runs once per posting.

---

## Reading `-gcflags="-m"`

You don't have to guess which lines escape. The compiler will tell you. Build (or vet, or test) with `-gcflags="-m"` and it prints escape-analysis decisions. Add a second `-m` for more detail; it gets noisy, so start with one.

```
go build -gcflags="-m" ./ledger 2>&1 | grep -E 'escapes|moved to heap|does not escape'
```

The relevant lines for the code above look roughly like this (annotations trimmed):

```
./post.go:  ...: fmt.Sprintf(...) escapes to heap
./post.go:  ...: line escapes to heap
./post.go:  ...: ... argument does not escape
./post.go:  make([]AuditRow, ...) escapes to heap
./post.go:  moved to heap: <various>
```

Three phrases carry all the meaning:

- **`escapes to heap`** — this value could not be proven stack-safe. It's a heap allocation.
- **`moved to heap`** — a specific named variable was promoted from stack to heap for the same reason. Same cost, different phrasing.
- **`does not escape`** — the good outcome. The value stayed on the stack. This is what you want to see for transient locals.

**The gotcha:** `-m` output is per *compilation*, and it reflects what the compiler could prove *given how the value is used*, not some fixed property of the type. The same struct can escape in one function and stay on the stack in another. Don't read escape analysis as "this type is heap-y" — read it as "the compiler couldn't prove *this use* was safe." Change the use, change the verdict.

The two escapes worth studying here are the interface call and the returned slice, because they're the ones people misread.

---

## Escape trigger 1: interface boxing

`log.Debug(line)` looks free. It isn't. To pass a concrete `string` (or any value) through an interface parameter, the runtime needs an interface value — a type pointer plus a data pointer. For anything that isn't already a pointer, that data pointer has to point *somewhere stable*, so the compiler frequently moves the boxed value to the heap. That's why you'll see the argument to a variadic `interface{}` — the classic being `fmt.Println(x)` — reported as escaping even when `x` itself was a happy stack local a line earlier.

This is the sneakiest one on a hot path because it hides inside logging and `fmt`. Every `fmt.Sprintf` argument is passed as `...interface{}`, and every one is a candidate to escape. A single debug log inside a per-transaction loop can own a surprising share of your allocation profile.

**The gotcha:** the escape isn't the interface *call* — it's the *boxing of the operands*. Passing an already-pointer type, or not calling into the interface at all on the hot path, avoids it. Guarding the log with a level check that the compiler can see (or dropping it from the hot path entirely) removes both the call and the boxing. "Just leave the debug log, it's cheap" is exactly the intuition escape analysis is there to correct.

---

## Escape trigger 2: returning a pointer, and slices that grow

`return rows` forces `rows` to escape — the caller outlives `PostBatch`, so its backing array can't live on this stack frame. That one is unavoidable *by design*: we genuinely need the data to survive the call. But two things make it worse than it has to be.

First, `rows` starts as `nil` and grows by `append`. Each growth allocates a new, larger backing array and copies the old one. A batch of N postings can trigger several reallocations as the slice doubles its way up. Second, because we never told the compiler how big the result would be, it can't pre-size anything.

The fix for the growth is a capacity hint — we know exactly how many rows we'll produce:

```go
rows := make([]AuditRow, 0, len(entries)) // one allocation, sized once
```

That single change collapses log-N reallocations into one. The slice still escapes (we return it — that's correct), but it escapes *once*, at the right size, instead of repeatedly.

There's a companion trap worth naming: returning a pointer to a local. `func newPosting() *Posting { p := Posting{...}; return &p }` forces `p` onto the heap — `moved to heap: p` in the `-m` output — because the pointer outlives the frame. That's often fine and idiomatic. It becomes a problem only when it's on a hot path and the pointer wasn't actually necessary; returning the value instead of `*Posting` lets small structs ride the stack.

---

## Escape trigger 3: closures that capture

Not in the snippet above, but it bit us elsewhere in the same service. A closure that captures a variable by reference forces that variable to the heap if the closure itself escapes (stored in a struct, passed to a goroutine, returned). Our retry helper captured the whole request struct in a closure handed to a worker pool — every request boxed its payload onto the heap purely to satisfy the closure's lifetime. Passing the needed fields as explicit arguments, instead of capturing them, let them stay on the stack.

**The gotcha:** a closure passed to something that runs it *synchronously and doesn't retain it* (like `sort.Slice`) usually does **not** escape — the compiler can see the closure dies with the call. The same closure handed to `go func()` or stored in a channel *does* escape. It's the closure's lifetime that decides, not the fact that it's a closure. Check `-m`; don't assume.

---

## The disciplined version

Putting the fixes together — pre-sized slice, no per-iteration `fmt`, no interface boxing on the hot path — the loop stops generating garbage per posting:

```go
func PostBatch(entries []Posting) []AuditRow {
	rows := make([]AuditRow, 0, len(entries)) // sized once; the only intended alloc

	// Reuse one builder across iterations instead of fmt.Sprintf per row.
	var b strings.Builder
	for _, e := range entries {
		// key: "account:currency" without fmt's interface boxing.
		key := e.Account + ":" + e.Currency

		b.Reset()
		b.WriteString("post ")
		b.WriteString(e.Account)
		b.WriteByte(' ')
		b.WriteString(strconv.FormatInt(e.Amount, 10))
		b.WriteByte(' ')
		b.WriteString(e.Currency)
		b.WriteString(" ref=")
		b.WriteString(e.Ref)

		rows = append(rows, AuditRow{Key: key, Line: b.String(), Delta: e.Amount})
	}
	return rows
}
```

We dropped the per-row debug log from the hot path (it moved behind a sampled, level-checked logger outside the loop). Both the `+` concatenation for the key and the `strings.Builder` earn their place the same way: they avoid `fmt`'s variadic `interface{}` boxing — the operands no longer get boxed and moved to the heap the way every `fmt.Sprintf` argument was. What `strings.Builder` does *not* buy you here is buffer reuse. Because each `b.String()` is retained inside the row we return, the loop has to `b.Reset()` (which sets the builder's `buf` back to `nil`) before the next iteration, so there is no cross-row reuse of the backing array — every row still allocates its own line string, exactly because that string is returned. Rebuild with `-gcflags="-m"` and the boxing-driven `escapes to heap` lines are gone; what remains is the one intended slice allocation plus the per-row `b.String()` results that legitimately become part of the returned rows.

---

## sync.Pool for transient buffers — and its sharp edges

Sometimes a per-call buffer genuinely can't be avoided — you need a scratch buffer to serialize each posting into a wire format, and it can't live on the stack because it's handed to an `io.Writer`. That's the case `sync.Pool` is built for: amortizing the allocation of transient objects across calls.

```go
var bufPool = sync.Pool{
	New: func() any { return new(bytes.Buffer) },
}

func serialize(p Posting, w io.Writer) error {
	buf := bufPool.Get().(*bytes.Buffer)
	buf.Reset()             // Get can hand back a dirty buffer
	defer bufPool.Put(buf)  // always return it

	// ... write p into buf ...
	_, err := w.Write(buf.Bytes())
	return err
}
```

`sync.Pool` is powerful and easy to misuse. The caveats that matter in production:

- **Always `Reset` on `Get`.** The pool hands back whatever was last `Put`, contents and all. Forgetting `Reset` is a data-leak bug, not just a correctness nit — in a ledger, a stale buffer means one transaction's bytes bleeding into another's.
- **Never retain what you `Put`.** Once returned, the object may be handed to another goroutine immediately. Keeping a reference to `buf.Bytes()` after `Put` is a use-after-free-shaped race.
- **The pool is emptied by GC.** `sync.Pool` is a cache, not a free list with guarantees — objects can be reclaimed on any GC cycle, so it only pays off under sustained churn where `Get` hits a warm pool. For rare or bursty allocations it buys little.
- **Pooling small values is a net loss.** If the object is cheap to allocate and stack-friendly, a pool adds interface boxing (`any`), a type assertion, and synchronization for no benefit. Measure before you pool.

**The gotcha:** `sync.Pool` doesn't reduce your allocation *rate* to zero — it reduces the number that reach the allocator. If your `-benchmem` numbers don't move after pooling, the objects were probably being reclaimed between calls, or they weren't the ones on your hot path. Pool because a benchmark told you to, not because pooling feels fast.

---

## Measuring: benchmarks, `-benchmem`, and benchstat

None of the above is worth doing without numbers, and "numbers" means a benchmark, not a stopwatch on production. Write a benchmark that exercises the real batch shape:

```go
func BenchmarkPostBatch(b *testing.B) {
	entries := makeEntries(256) // representative batch size
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = PostBatch(entries)
	}
}
```

Run it capturing allocations, several times so `benchstat` can reason about variance:

```
go test -run=^$ -bench=BenchmarkPostBatch -benchmem -count=10 ./ledger | tee old.txt
# apply the fixes, then:
go test -run=^$ -bench=BenchmarkPostBatch -benchmem -count=10 ./ledger | tee new.txt
benchstat old.txt new.txt
```

`-benchmem` adds two columns you should learn to read before `ns/op`: **`B/op`** (bytes allocated per operation) and **`allocs/op`** (number of distinct allocations per operation). On a GC-bound service, `allocs/op` is often the number that predicts your tail latency, because each allocation is potential future scan work. Our real before/after looked like this:

| Metric | Before | After |
|---|---|---|
| `allocs/op` | **`TODO: real number`** | **`TODO: real number`** |
| `B/op` | **`TODO: real number`** | **`TODO: real number`** |
| `ns/op` | **`TODO: real number`** | **`TODO: real number`** |
| p99 under load | **`TODO: real number`** | **`TODO: real number`** |

Use `benchstat` rather than eyeballing two runs: it reports the delta *with a confidence interval*, so you don't celebrate a 3% "improvement" that's within noise. If it prints `~` for the delta, the change was statistically indistinguishable — treat that as "no effect" no matter how good the diff looks.

**The gotcha:** always benchmark with `-run=^$` so no unit tests run alongside, and pin `b.ReportAllocs()` (or `-benchmem`) or you're flying blind on the exact metric this entire exercise is about. And benchmark the *batch*, not a single posting — allocation behavior like slice growth only shows up at realistic sizes.

---

## Key takeaways

- **The compiler chooses stack vs heap; escape analysis is the proof.** "Escapes to heap" means the compiler couldn't prove the value dies with its frame — not that the type is inherently heap-y. Change the usage, change the verdict.
- **Read `-gcflags="-m"` on hot paths.** `escapes to heap` / `moved to heap` are allocations; `does not escape` is the win. It's the ground truth, not a guess.
- **Know the common triggers.** Interface boxing (including every `fmt`/`log` argument), returning pointers, growing an unsized slice, and captured closures are the usual suspects on a payment path.
- **Fix with lifetime, not tricks.** Pre-size slices you'll return, keep `fmt` and interface calls out of tight loops, pass fields instead of capturing them, and return values instead of pointers for small structs.
- **`sync.Pool` is a scalpel.** Great for genuinely transient, churny buffers; a liability for small stack-friendly values. Always `Reset` on `Get`, never retain after `Put`, and only reach for it when a benchmark demands it.
- **Prove it with `-benchmem` + `benchstat`.** Optimize `allocs/op` first on a GC-bound service, and trust the confidence interval over the diff.

Allocation discipline isn't premature optimization when the allocations are per-transaction and the service is settling real money. It's just knowing what the machine does with the code you wrote — and the compiler will tell you, if you ask it with `-m`.

---

## Further reading

- Ardan Labs, "Garbage Collection In Go" (Parts I–III) — a clear model of how the Go collector, the allocator, and pacing interact, and why reducing allocations reduces the collector's work. https://www.ardanlabs.com/blog
