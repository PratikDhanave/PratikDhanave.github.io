# Data-Oriented Design and CPU Caches

*How a settlement matching loop that looked CPU-bound turned out to be memory-bound — and what fixing the data layout, not the algorithm, did for our end-of-day batch.*

---

The pager went off at 23:40, forty minutes into the nightly settlement run. Nothing was down. The batch just wasn't going to finish before the bank's cut-off window closed. We match incoming settlement legs against a book of open positions, and the matcher — a tight loop over a few million records — was running at maybe a third of the throughput I expected from the hardware. No lock contention. No GC pressure worth mentioning. `pprof` showed the CPU pinned inside the matching function, doing what looked like honest work.

That's the trap. A profile saying "we spend all our time in this loop" is not the same as "this loop is doing useful arithmetic." Our matcher was CPU-bound the way a car stuck in traffic is engine-bound: the engine's running, but that's not the bottleneck. The loop was stalling on memory — waiting for cache lines to arrive from RAM — and the CPU idled through those stalls without anything in the profile telling me so.

This post is about the fix, which touched zero lines of matching logic and roughly doubled throughput. The backbone is the thing every senior Go engineer eventually internalizes: **the CPU is not slow, memory is far away, and your data layout decides how often you pay the trip.**

---

## The memory hierarchy your algorithm forgot about

The mental model most of us carry — memory is a flat array you index in O(1) — hasn't been true since roughly the 1990s. What's actually underneath a Go program is a hierarchy, and each step down is an order of magnitude slower:

| Level | Rough latency | Rough size |
|---|---|---|
| L1 cache | ~1 ns | 32–64 KB per core |
| L2 cache | ~4 ns | 256 KB–1 MB per core |
| L3 cache | ~15 ns | tens of MB, shared |
| Main memory (RAM) | ~100 ns | gigabytes |

A load from L1 versus a load from RAM is the difference between reaching into your pocket and walking to another building. And the CPU can't do useful work while it waits — a full memory stall on a modern core burns hundreds of instructions' worth of time.

The unit of transfer matters as much as the latency. The CPU never fetches one byte, or one `int64`. It fetches a **cache line** — 64 bytes on amd64 and on the server-class arm64 we run (Graviton, Ampere); note Apple Silicon's M-series arm64 uses 128-byte lines, so don't assume 64 everywhere — and everything in that line comes along for free. That single fact is the lever behind everything below: if the next thing your loop needs is already in the line you just pulled, the access is nearly free. If it isn't, you eat another ~100 ns.

One more piece of the CPU does a lot of quiet work here. The **hardware prefetcher** watches your access pattern; when it detects a predictable stride — walking sequentially through memory — it fetches the next lines before you ask, hiding the latency entirely. It rewards predictable, linear, dense access, and gives up when you chase pointers around the heap.

So the real performance question for a hot loop isn't "how many operations?" It's "how many cache lines does this loop touch, and can the prefetcher see them coming?"

---

## Array of structs: the layout that looked reasonable

Here's the shape of our original position record. It reads like clean, obvious domain code, which is exactly why it survived review for two years.

```go
type Position struct {
	Notes       string    // 16 bytes — rarely read in the hot loop
	CreatedAt   time.Time // 24 bytes — audit only
	Counterparty string   // 16 bytes — matched on, but rarely
	AccountID   uint64    // 8 bytes  — the hot field
	Amount      int64     // 8 bytes  — the hot field (minor units)
	Currency    uint16    // 2 bytes  — the hot field
	Status      uint8     // 1 byte   — the hot field
	Matched     bool      // 1 byte   — written in the hot loop
}

book := make([]Position, numPositions) // array of structs
```

The matcher walks the whole book looking for open positions in a given currency that can absorb an incoming leg:

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

Look at what the CPU actually does per iteration. The hot path reads `Status`, `Currency`, `Matched`, `Amount` — 12 bytes of the record (1 + 2 + 1 + 8). But `Position` is far larger. With the field ordering above plus alignment padding, each element is **`TODO: real number` bytes** (`unsafe.Sizeof(Position{})`). Every iteration pulls one or two 64-byte cache lines out of RAM, uses ~12 bytes of them, and throws the rest away. The `Notes`, `CreatedAt`, and `Counterparty` fields — cold data the loop never touches — are riding in the same cache lines as the hot fields, evicting useful data and multiplying the number of lines we have to fetch.

**The gotcha:** an array of structs (AoS) co-locates *all* of a record's fields in memory. That's great when you use most fields together, and actively harmful in a loop that reads only a few. You pay to haul the cold fields into cache on every pass. The profiler blames the loop because that's where the stalls surface, but the real cost was decided at `struct` definition time.

Two things are wrong here, and they compound: the struct is bloated with cold data, *and* its fields are ordered so the compiler inserts padding. Fix the ordering first — it's free.

---

## Field ordering and padding: the free win

Go lays out struct fields in declaration order and aligns each to its natural boundary, inserting padding bytes to make that work. Declare fields carelessly and you get holes. The failure mode is **interleaving small and large fields**: put a `bool` before an `int64` and the compiler inserts 7 bytes of padding after the `bool` so the `int64` lands on an 8-byte boundary. Do that repeatedly and the padding scatters through the middle of the struct.

Here's the pattern at its worst — the small fields are deliberately interleaved with the 8-byte ones:

```go
type BadLayout struct {
	A bool  // offset 0
	B int64 // offset 8  (7 bytes padding after A)
	C bool  // offset 16
	D int64 // offset 24 (7 bytes padding after C)
	E bool  // offset 32
} // unsafe.Sizeof == 40 bytes: 3 useful bool bytes, 8 int64 words, and 29 bytes of padding + tail
```

That struct holds 17 bytes of real data (`3×1 + 2×8`) and pays **40 bytes** for it. Every interleaved `bool` forces a 7-byte hole before the next `int64`, and the struct's own 8-byte alignment rounds the tail up too.

The rule of thumb: **order fields from largest to smallest.** Pointers and 8-byte types first, then 4-byte, then 2-byte, then 1-byte, so the small fields pack together at the tail instead of forcing padding between the big ones:

```go
type GoodLayout struct {
	B int64 // offset 0
	D int64 // offset 8
	A bool  // offset 16
	C bool  // offset 17
	E bool  // offset 18
} // unsafe.Sizeof == 24 bytes: the three bools pack into one tail word, no interior holes
```

Same fields, same data — **40 bytes down to 24, a 40% shrink** for a mechanical reorder. The `int64`s sit adjacent with no padding between them, and the three `bool`s share the final word instead of each dragging a 7-byte hole behind it.

You don't have to eyeball this. `go vet`'s `fieldalignment` analyzer finds and fixes it:

```
go run golang.org/x/tools/go/analysis/passes/fieldalignment/cmd/fieldalignment@latest ./...
# add -fix to have it rewrite the structs for you
```

More records per cache line, fewer lines fetched per pass. Do this everywhere you have large slices of structs; it's the cheapest performance work in Go.

**The gotcha:** `fieldalignment` optimizes for *size*, not for *access locality*. It will happily produce a smaller struct that still interleaves hot and cold fields in the same cache line. Shrinking the struct is necessary but not sufficient — for a hot loop over millions of records, you want the hot fields not just packed, but *separated* from the cold ones entirely. That's the next move.

---

## Struct of arrays: separate hot data from cold

The real fix is to stop storing records as records. Split the one bloated `[]Position` into parallel arrays — a struct of arrays (SoA) — so each field lives in its own contiguous slice:

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

Now walk through what the CPU does. When it reads `b.Status[i]`, it pulls a cache line of 64 *consecutive* `Status` bytes — the next 64 records' worth. The cold `Notes` and `CreatedAt` are in entirely different regions of memory and never get fetched. `b.Currency`, `b.Amount`, and `b.Matched` are each their own dense stream. Every one of these is a linear stride, so the prefetcher locks on immediately and starts pulling the next lines before the loop asks for them.

The loop body is nearly identical. The algorithm is identical — still O(n), still a linear scan. All that changed is where the bytes live. On our settlement book the SoA rewrite cut the matcher's wall-clock time by `TODO: real number`%, and `perf stat` showed L1 cache misses dropping from `TODO: real number`% to `TODO: real number`%.

**The gotcha:** SoA is not free — it costs you ergonomics. There's no single `Position` value to pass around anymore; a "record" is now an index `i` into a set of slices, and you have to keep every slice the same length or you get silent corruption. Reach for SoA only where it pays: large collections walked in tight loops that touch a subset of fields. For a config struct you read once, or a record you always use whole, AoS is clearer and just as fast. Don't SoA your whole codebase — SoA the hot loop.

---

## False sharing: when padding is the fix, not the problem

We parallelized the matcher across worker goroutines, one per CPU, each accumulating a count of matches into a shared slice indexed by worker ID:

```go
type Counter struct {
	Matched uint64
}

counters := make([]Counter, numWorkers)

// worker w does, in its hot loop:
counters[w].Matched++
```

Every worker writes only its *own* slot. No data race — `go test -race` is clean, and the logic is correct. But throughput barely improved with more workers, and on some runs got *worse*. This is **false sharing**, and it's one of the nastiest performance bugs in concurrent Go precisely because the code looks obviously correct.

The problem is the cache line again. `Counter` is 8 bytes; eight fit in one 64-byte line, so `counters[0]` through `counters[7]` all live on the *same* line. Cache coherency operates at line granularity, not variable granularity — when worker 0 writes its slot, the protocol invalidates that entire line in every other core's cache. Worker 1, writing its own independent slot, now has to re-fetch the line worker 0 just dirtied. The cores ping-pong the line between caches, and every increment that should have been an L1 hit becomes a coherency round-trip. Independent data, false dependency — hence "false" sharing.

The fix is to pad each counter out to its own cache line so no two workers ever share one:

```go
const cacheLine = 64

type Counter struct {
	Matched uint64
	_       [cacheLine - 8]byte // pad to a full line
}
```

Now `unsafe.Sizeof(Counter{})` is 64, each slot occupies its own line, and a worker's writes never invalidate another's. In our matcher this took the parallel scan from `TODO: real number` ns/op to `TODO: real number` ns/op at eight workers — the padding, counterintuitively, made it faster by *using more memory*.

**The gotcha:** false sharing is invisible to `-race` and invisible in a normal CPU profile — the time just quietly disappears into cache-coherency traffic. Suspect it whenever adding goroutines fails to scale a loop that writes to nearby slots of a shared slice. Confirm it before you pad: `perf c2c` (or `perf stat` watching for high `LLC-store-misses`) points straight at the contended line. And don't pad reflexively — 64 bytes per counter across a large array wastes real cache, so pad only the slots that goroutines actually hammer concurrently.

---

## Benchmark it, because intuition lies

Every claim above needs a benchmark, because cache behavior is deeply hardware-dependent and your intuition about it will be wrong more often than you'd like. Here's the scaffolding I use — the point is to measure the same workload across layouts and read `-benchmem` plus `perf` alongside `ns/op`:

```go
func BenchmarkMatch_AoS(b *testing.B) {
	book := makeAoSBook(2_000_000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = matchLegAoS(book, usd, 100_00)
	}
}

func BenchmarkMatch_SoA(b *testing.B) {
	book := makeSoABook(2_000_000)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = matchLegSoA(book, usd, 100_00)
	}
}
```

Run it and capture the layout-sensitive numbers:

```
go test -bench=Match -benchmem -count=10 | tee bench.txt
benchstat bench.txt

# cache misses tell the real story — ns/op is just the symptom:
perf stat -e cache-references,cache-misses,L1-dcache-load-misses \
	go test -bench=Match_SoA -benchtime=5x
```

Expected shape of the results (fill in from your own hardware — I won't quote numbers I didn't measure on the box in question):

| Variant | ns/op | B/op | L1 miss rate |
|---|---|---|---|
| AoS, unordered fields | `TODO: real number` | `TODO: real number` | `TODO: real number`% |
| AoS, `fieldalignment` | `TODO: real number` | `TODO: real number` | `TODO: real number`% |
| SoA, hot columns split | `TODO: real number` | `TODO: real number` | `TODO: real number`% |

**The gotcha:** benchmark on hardware that resembles production. Cache sizes, line size (still 64 bytes today, but don't hard-code the assumption forever), and prefetcher behavior differ across CPUs, and a layout that wins on your laptop's big L2 can lose on a smaller cloud instance. Also beware the compiler optimizing your benchmark away — assign the result to a package-level sink or the dead-code eliminator will delete the loop you're trying to measure, and you'll "prove" that memory layout is instantaneous.

---

## Key takeaways

- **Memory-bound masquerades as CPU-bound.** A loop pinned at 100% CPU in a profile may be stalling on RAM, not computing. When throughput is far below what the arithmetic should allow, suspect the data layout before the algorithm.
- **The cache line is the unit of cost.** The CPU fetches 64 bytes at a time. Performance is governed by how many lines your loop touches and how much of each line you actually use.
- **Order struct fields largest-to-smallest and run `fieldalignment`.** It's a free, mechanical shrink that packs more records per cache line — do it on every large slice of structs.
- **Split hot data from cold with struct-of-arrays in your hottest loops only.** Same algorithm, dramatically fewer cache-line fetches — but it costs ergonomics, so don't apply it everywhere.
- **False sharing is silent — pad concurrent hot slots to a full cache line.** `-race` won't catch it and the profiler won't name it; suspect it when goroutines fail to scale a loop writing to nearby slots.
- **Measure, don't reason.** Cache behavior is hardware-specific. Benchmark with `benchstat` and confirm the mechanism with `perf`'s cache-miss counters — the `ns/op` is only the symptom.

None of this changed a single matching rule. We shipped the same settlement logic, laid out differently in memory, and the nightly batch started finishing inside the window again. The CPU was never the problem. The distance to the data was.

---

## Further reading

- ["Getting Friendly With CPU Caches"](https://www.ardanlabs.com/blog) — Ardan Labs. The canonical Go-centric walk through cache lines, prefetching, and why data-oriented layout beats clever algorithms for memory-bound work.
