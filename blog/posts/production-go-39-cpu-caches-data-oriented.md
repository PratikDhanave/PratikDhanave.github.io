<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/production-go-39-cpu-caches-data-oriented.html -->

# Data-Oriented Design and CPU Caches

*Why a loop that profiles as CPU-bound can really be memory-bound — struct layout, array-of-structs vs struct-of-arrays, and false sharing, all measured on real hardware (including a 128-byte-cache-line surprise).*

---

A profile saying "we spend all our time in this loop" is not the same as "this loop is doing useful arithmetic." A loop can be CPU-bound the way a car stuck in traffic is engine-bound: the engine's running, but that's not the bottleneck. Hot loops over large data routinely stall on memory — waiting for cache lines to arrive from RAM — and the CPU idles through those stalls without anything in a standard profile saying so.

This post works through the three data-layout levers that fix it — field ordering, hot/cold separation, and false-sharing padding — and **measures every claim** on a settlement-matching workload: a linear scan over 2 million position records. Numbers are from an Apple M1 Max (10 cores, Go 1.27), which turns out to be a usefully *awkward* machine for this topic, in ways flagged honestly below.

---

## The memory hierarchy your algorithm forgot about

The mental model most of us carry — memory is a flat array you index in O(1) — hasn't been true since roughly the 1990s. What's actually underneath a Go program is a hierarchy, and each step down is an order of magnitude slower:

| Level | Rough latency | Rough size |
|---|---|---|
| L1 cache | ~1 ns | 32–192 KB per core |
| L2 cache | ~4 ns | 256 KB–12 MB |
| L3 / SLC | ~15 ns | tens of MB, shared |
| Main memory (RAM) | ~100 ns | gigabytes |

A load from L1 versus a load from RAM is the difference between reaching into your pocket and walking to another building, and the CPU can't do useful work while it waits.

The unit of transfer matters as much as the latency. The CPU never fetches one byte — it fetches a **cache line**: 64 bytes on amd64 and most server arm64 (Graviton, Ampere), but **128 bytes on Apple's M-series**. Everything in the line comes along for free; everything outside it is another trip. And the **hardware prefetcher** watches your access pattern — when it detects a predictable stride, it fetches upcoming lines before you ask, hiding the latency entirely. It rewards linear, dense access and gives up when you chase pointers.

So the real performance question for a hot loop isn't "how many operations?" It's "how many cache lines does this loop touch, and can the prefetcher see them coming?"

---

## Array of structs: the layout that looks reasonable

Here's a position record that reads like clean, obvious domain code — which is why layouts like it survive review for years:

```go
type Position struct {
	Notes        string    // 16 bytes — rarely read in the hot loop
	CreatedAt    time.Time // 24 bytes — audit only
	Counterparty string    // 16 bytes — matched on, but rarely
	AccountID    uint64    // 8 bytes
	Amount       int64     // 8 bytes  — the hot field (minor units)
	Currency     uint16    // 2 bytes  — the hot field
	Status       uint8     // 1 byte   — the hot field
	Matched      bool      // 1 byte   — written in the hot loop
}

book := make([]Position, 2_000_000) // array of structs
```

The matcher walks the whole book looking for open positions in a currency that can absorb an incoming leg:

```go
func matchLeg(book []Position, ccy uint16, want int64) int {
	for i := range book {
		p := &book[i]
		if p.Status == statusOpen && p.Currency == ccy && !p.Matched && p.Amount >= want {
			return i
		}
	}
	return -1
}
```

Look at what the CPU does per iteration. The hot path reads `Status`, `Currency`, `Matched`, `Amount` — 12 bytes of the record. But `unsafe.Sizeof(Position{})` is **80 bytes**, measured. The loop uses 15% of every record it hauls out of memory; the cold `Notes`, `CreatedAt`, and `Counterparty` ride along in the same cache lines, evicting useful data and multiplying fetches.

**The gotcha:** an array of structs (AoS) co-locates *all* of a record's fields. Great when you use most fields together; actively harmful in a loop that reads a few. The profiler blames the loop because that's where the stalls surface — but the cost was decided at `struct` definition time.

---

## Field ordering and padding: the free win

Go lays out fields in declaration order, aligning each to its natural boundary with padding. Interleave small and large fields and the padding scatters through the struct. Measured at the extreme:

```go
type BadLayout struct {
	A bool  // offset 0
	B int64 // offset 8  (7 bytes padding after A)
	C bool  // offset 16
	D int64 // offset 24 (7 bytes padding after C)
	E bool  // offset 32
} // unsafe.Sizeof == 40 (measured): 19 real bytes, 21 of padding

type GoodLayout struct {
	B int64 // offset 0
	D int64 // offset 8
	A bool  // offset 16
	C bool  // offset 17
	E bool  // offset 18
} // unsafe.Sizeof == 24 (measured): bools pack into the tail word
```

Same fields, same data — **40 bytes down to 24** for a mechanical reorder. The rule of thumb: **largest fields first.** And you don't have to eyeball it; `go vet`'s `fieldalignment` analyzer finds and even rewrites it:

```
go run golang.org/x/tools/go/analysis/passes/fieldalignment/cmd/fieldalignment@latest -fix ./...
```

More records per cache line, fewer fetches per pass — the cheapest performance work in Go.

**The gotcha:** `fieldalignment` optimizes for *size*, not *access locality*. It will happily produce a smaller struct that still interleaves hot and cold fields. For a hot loop over millions of records you want the hot fields not just packed but *separated* — the next move.

---

## Struct of arrays: separate hot from cold

Stop storing records as records. Split the bloated `[]Position` into parallel arrays — struct of arrays (SoA) — so each field is its own contiguous slice:

```go
type Book struct {
	// hot columns — everything the matcher touches, densely packed
	Amount   []int64
	Currency []uint16
	Status   []uint8
	Matched  []bool

	// cold columns — audit/reporting only, never touched in the hot loop
	AccountID    []uint64
	Counterparty []string
	CreatedAt    []time.Time
	Notes        []string
}

func matchLeg(b *Book, ccy uint16, want int64) int {
	for i := range b.Status {
		if b.Status[i] == statusOpen && b.Currency[i] == ccy && !b.Matched[i] && b.Amount[i] >= want {
			return i
		}
	}
	return -1
}
```

Reading `b.Status[i]` now pulls a line of *consecutive status bytes* — the next 128 records' worth on this machine. The cold columns live in different memory regions and are never fetched. Each hot column is a dense linear stride the prefetcher locks onto immediately.

Measured — full worst-case scan of 2 million positions, median of 6 runs:

```text
BenchmarkMatchAoS-10    3,029,653 ns/op
BenchmarkMatchSoA-10    2,318,272 ns/op     (1.31x faster)
```

Now the honesty section, because this is where lesser posts reach for a fabricated "2×". **The win here is 1.31×, and the reasons it isn't bigger are themselves the lesson.** The M1 Max is close to a best case for the *bad* layout: an 80-byte record is a short, perfectly regular stride that its prefetcher predicts flawlessly, and its caches are enormous (the 2M-record hot columns nearly fit in cache as SoA). The same comparison widens as conditions worsen — bigger structs, more cold payload per record, smaller caches (a modest cloud instance), or random access patterns that defeat the prefetcher. Data-oriented design is insurance whose payout scales with how hostile the memory system is; on friendly hardware the premium looks small. Measure on hardware that resembles production before deciding it's not worth it — and before deciding it is.

**The gotcha:** SoA costs ergonomics. There's no `Position` value to pass around; a "record" is an index into parallel slices you must keep the same length. Reach for it only where it pays — large collections, tight loops, few fields touched. Don't SoA your codebase; SoA the hot loop.

---

## False sharing: when padding is the fix, not the problem

Parallelize the matcher — one worker per core, each accumulating matches into its own slot of a shared slice:

```go
type Counter struct {
	Matched uint64
}

counters := make([]Counter, numWorkers)
// worker w, in its hot loop:
counters[w].Matched++
```

Every worker writes only its own slot; `-race` is clean; the logic is correct. But the slots are 8 bytes apart, so many of them share a cache line — and cache *coherency* operates at line granularity. When worker 0 writes its slot, the protocol invalidates the whole line in every other core's cache; worker 1, writing its own independent slot, must re-fetch the line worker 0 just dirtied. The cores ping-pong the line. Independent data, false dependency — **false sharing**.

The fix is padding each slot to a full line. And here the M1 Max teaches the sharpest lesson in the post. Measured: 8 workers, 100k increments each, three layouts:

```text
BenchmarkCounterPlain-10     500,404 ns/op   // 8-byte slots, heavily shared lines
BenchmarkCounterPad64-10     431,192 ns/op   // padded to 64B: the "standard" fix
BenchmarkCounterPad128-10    387,740 ns/op   // padded to this CPU's actual 128B line
```

Padding to 64 bytes — the number every blog post hard-codes — recovered about half the available win, because **on Apple Silicon two 64-byte-padded counters still share each 128-byte line.** Padding to the real line size took the full ~23% improvement. The portable way to not care is the standard library's `cpu.CacheLinePad`, or in a pinch, pad generously:

```go
type Counter struct {
	Matched uint64
	_       [120]byte // pad to 128 — covers both 64B and 128B line sizes
}
```

**The gotcha:** false sharing is invisible to `-race` and to a normal CPU profile — the time disappears into coherency traffic. Suspect it whenever adding goroutines fails to scale a loop that writes nearby slots. On Linux, `perf c2c` points at the contended line (macOS has no equivalent, which is why the benchmark deltas above are the evidence). And don't pad reflexively — a full line per element across a large array wastes real cache; pad only slots that goroutines actually hammer concurrently.

---

## Benchmark it, because intuition lies

Every number above came from benchmarks shaped like this — note the package-level `sink`, without which the compiler may delete the loop you're measuring:

```go
var sink int

func BenchmarkMatchSoA(b *testing.B) {
	book := makeSoA(2_000_000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		sink = matchLeg(book, usd, 99_000)
	}
}
```

```
go test -bench=Match -benchmem -count=6 | tee bench.txt
benchstat bench.txt

# Linux: confirm the mechanism, not just the symptom —
perf stat -e cache-references,cache-misses,L1-dcache-load-misses \
    go test -bench=Match -benchtime=5x
```

**The gotcha:** benchmark on hardware resembling production. Cache sizes, line size (64 vs 128 — measured above to matter), and prefetcher behavior differ across CPUs; a layout that barely wins on a laptop's giant caches can win big on a small cloud instance, and vice versa.

---

## Key takeaways

- **Memory-bound masquerades as CPU-bound.** A loop pinned at 100% CPU may be stalling on RAM. When throughput is far below what the arithmetic allows, suspect data layout before algorithm.
- **The cache line is the unit of cost — and it isn't always 64 bytes.** Apple M-series uses 128; measured, padding to 64 left half the false-sharing win on the table.
- **Order struct fields largest-to-smallest and run `fieldalignment`.** Measured: 40 → 24 bytes for the same data, mechanically.
- **Split hot from cold with SoA in your hottest loops only.** Measured: 1.31× on cache-rich hardware with a prefetch-friendly stride — and the gap widens as structs grow, caches shrink, or access randomizes. It costs ergonomics; spend it where the loop earns it.
- **Pad concurrently-hammered slots to a full line.** Measured: −23% on an 8-worker counter array; `-race` and the profiler will never name this bug for you.
- **Measure, don't reason.** Cache behavior is the most hardware-specific thing in this series — which is exactly why this post reports its machine, and why your numbers will differ in the details while the ordering of the lessons holds.

---

## Further reading

- ["Getting Friendly With CPU Caches"](https://www.ardanlabs.com/blog) — Ardan Labs. The canonical Go-centric walk through cache lines, prefetching, and why data layout beats clever algorithms for memory-bound work.

---

*All measurements: Apple M1 Max (10 cores, 128-byte cache lines), Go 1.27, 2M-record scans and 8-worker counter benchmarks as described. The absolute numbers are machine-specific; the mechanisms and their ordering are not.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-08-03
Canonical: https://pratikdhanave.com/blog/posts/production-go-39-cpu-caches-data-oriented.html
Attribution: please link the canonical URL when citing or quoting this post.
