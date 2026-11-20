<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/production-go-37-escape-analysis-allocations.html -->

# Escape Analysis and Allocation Discipline

*How a ledger-posting path that looks innocent quietly mints garbage on every transaction — reading the compiler's escape-analysis output, and a measured 4× win from allocating only what you keep.*

---

A latency profile that scales with volume — double the transactions per second, double the tail — is a tell. It's rarely a slow dependency; it's almost always something the code does *per request*. And when the CPU flame graph of such a service is dominated by `runtime.mallocgc` and `runtime.scanobject`, the work isn't slow — the *garbage the work produces* is.

This post is about allocation discipline: how Go decides whether a value lives on the stack or the heap, how to read `-gcflags="-m"`, and how to treat allocations on a hot path as a budget. The claims are measured, not asserted — a ledger-posting function is taken through three versions below, with real benchmark output for each (Apple M1 Max, Go 1.27; `-benchmem`, 256-posting batches). The runtime concept underneath it all is **escape analysis** — the compiler pass that decides who cleans up after each value you create.

---

## Stack is free; heap has a bill

A value on the stack costs nothing to reclaim. When the function returns, the stack pointer moves and the memory is gone — no bookkeeping, no collector, no scan. A value on the heap is the opposite: the garbage collector has to track it, mark it as reachable on every cycle, and eventually sweep it. On a path that runs a few thousand times a second, the difference between "this struct lives on the stack" and "this struct escapes to the heap" is the difference between a rounding error and a GC-pressure incident.

The critical thing to internalize: **you do not choose stack or heap in Go.** There is no `alloca`, no placement control. The compiler chooses, and its rule is a safety rule, not a performance one. If the compiler can prove a value does not outlive the function that created it, the value stays on the stack. If it *cannot* prove that, the value "escapes" to the heap, where it's safe. Escape analysis is that proof engine. Every heap allocation on your hot path is the compiler telling you "I couldn't prove this was safe on the stack." The job isn't to fight the compiler — it's to write code whose lifetimes the compiler can actually reason about.

---

## The offending path

Here's the version every codebase starts with. It takes a batch of postings, formats a per-entry key, and appends normalized rows to an audit buffer. Read it with allocation in mind.

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

Real output for the code above (trimmed to the instructive lines):

```
./post.go:35:32: e.Account escapes to heap
./post.go:35:43: e.Currency escapes to heap
./post.go:36:48: e.Account escapes to heap
./post.go:36:59: e.Amount escapes to heap
./post.go:36:69: e.Currency escapes to heap
./post.go:36:81: e.Ref escapes to heap
./post.go:38:16: append escapes to heap
```

Lines 35–36 are the two `fmt.Sprintf` calls: every operand — including `e.Amount`, a plain `int64` — is reported escaping, because each is boxed into an `interface{}` to ride through `fmt`'s variadic parameter. Line 38 is the growing slice.

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

Not in the snippet above, but a classic on hot paths: a closure that captures a variable by reference forces that variable to the heap if the closure itself escapes (stored in a struct, passed to a goroutine, returned). The canonical offender is a retry helper that captures a whole request struct in a closure handed to a worker pool — every request boxes its payload onto the heap purely to satisfy the closure's lifetime. Passing the needed fields as explicit arguments, instead of capturing them, lets them stay on the stack.

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

The per-row debug log moves behind a sampled, level-checked logger outside the loop. Both the `+` concatenation for the key and the `strings.Builder` earn their place the same way: they avoid `fmt`'s variadic `interface{}` boxing. Measured against the naive version (256-posting batches, median of 10 runs):

```text
BenchmarkPostBatchNaive-10          60116 ns/op   63156 B/op   2056 allocs/op
BenchmarkPostBatchDisciplined-10    31366 ns/op   47736 B/op   1536 allocs/op
```

Twice as fast — but look harder at `allocs/op`, because it teaches the honest lesson: 2,056 only fell to 1,536, which is still six allocations per posting. Why? Because `strings.Builder` does **not** buy buffer reuse here. Each `b.String()` is retained inside a returned row, so the loop must `b.Reset()` (which drops the builder's backing array) before the next iteration — every row's line still allocates, and the builder *re-grows from nil* every row, several allocations at a time. The speedup came almost entirely from killing `fmt`'s boxing, not from killing allocations.

The real discipline is sharper: **allocate only what you keep.** Each row legitimately keeps exactly two strings — the key and the line. So build the line in one reusable byte scratch and pay for just the final `string(scratch)` copy:

```go
func PostBatchTight(entries []Posting) []AuditRow {
	rows := make([]AuditRow, 0, len(entries))
	scratch := make([]byte, 0, 64) // reused across every row
	for _, e := range entries {
		key := e.Account + ":" + e.Currency
		scratch = scratch[:0]
		scratch = append(scratch, "post "...)
		scratch = append(scratch, e.Account...)
		scratch = append(scratch, ' ')
		scratch = strconv.AppendInt(scratch, e.Amount, 10)
		scratch = append(scratch, ' ')
		scratch = append(scratch, e.Currency...)
		scratch = append(scratch, " ref="...)
		scratch = append(scratch, e.Ref...)
		rows = append(rows, AuditRow{Key: key, Line: string(scratch), Delta: e.Amount})
	}
	return rows
}
```

```text
BenchmarkPostBatchTight-10          15542 ns/op   27264 B/op    513 allocs/op
```

**513 allocations for 256 postings** — 256 keys + 256 lines + 1 pre-sized slice. The allocation count now *equals* the number of values the function's contract requires to survive it, which is the end state this whole discipline aims at: every remaining allocation is one you can point to and justify. Net result versus the naive version: **3.9× faster, 4× fewer allocations, 57% less allocated memory** — and, on a GC-bound service, correspondingly less future scan work per batch.

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

`-benchmem` adds two columns you should learn to read before `ns/op`: **`B/op`** (bytes allocated per operation) and **`allocs/op`** (number of distinct allocations per operation). On a GC-bound service, `allocs/op` is often the number that predicts your tail latency, because each allocation is potential future scan work. The three versions from this post, measured on the same machine with the commands above:

| Metric (256-posting batch) | Naive | Disciplined | Tight |
|---|---|---|---|
| `allocs/op` | 2,056 | 1,536 | **513** |
| `B/op` | 63,156 | 47,736 | **27,264** |
| `ns/op` | 60,116 | 31,366 | **15,542** |
| allocs per posting | 8.0 | 6.0 | **2.0** |

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

Allocation discipline isn't premature optimization when the allocations are per-transaction. It's knowing what the machine does with the code you wrote — and both the compiler (`-m`) and the benchmark (`-benchmem`) will tell you exactly, if you ask.

---

## Further reading

- Ardan Labs, "Garbage Collection In Go" (Parts I–III) — a clear model of how the Go collector, the allocator, and pacing interact, and why reducing allocations reduces the collector's work. https://www.ardanlabs.com/blog

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-08-01
Canonical: https://pratikdhanave.com/blog/posts/production-go-37-escape-analysis-allocations.html
Attribution: please link the canonical URL when citing or quoting this post.
