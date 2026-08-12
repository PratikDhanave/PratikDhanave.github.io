# Vector Search from Scratch

*Build a working in-memory vector store and exact k-nearest-neighbor search in Go by hand — no vector database — then understand precisely what HNSW, FAISS, and pgvector optimize when brute force finally runs out of road.*

---

In post 7 we turned text into numbers. An embedding model maps a sentence to a fixed-length vector — a `[]float32` — where geometric closeness tracks semantic closeness. We wrote a `cosine` function that scores how aligned two vectors are, and we saw that "a refund was issued" lands near "money was returned to the customer" and far from "the server caught fire."

That's a nice party trick with two vectors. The real question is the one that powers retrieval: given a *query* vector and a *collection* of thousands of stored vectors, which stored items are most similar? That operation — nearest-neighbor search over a vector collection — is the engine underneath semantic search, recommendations, and the retrieval half of RAG (which is post 9).

This post builds that engine from scratch in Go. No external vector database, no FAISS bindings, no `import` you don't already have. Just a struct, a slice, a heap, and the `cosine` function from last time. By the end you'll have a `VectorStore` that answers "give me the top *k* matches for this query," and — just as important — you'll understand exactly what the industrial-strength systems are buying you when you eventually outgrow it.

---

## The data model: what a vector store actually stores

Strip away the marketing and a vector store is a list of records. Each record is three things: an **id** so you can point back at the source, the **original text** (or a reference to it) so a match means something to a human, and the **embedding** — the `[]float32` you search over.

```go
package vstore

// Record is one item in the store: the vector plus what it points back to.
type Record struct {
	ID     string
	Text   string
	Vector []float32
}

// Result is one hit from a search, carrying its similarity score.
type Result struct {
	ID    string
	Text  string
	Score float32 // cosine similarity in [-1, 1]; higher is closer
}
```

The store itself is a slice of records behind a small type. That's the whole "database" — no B-tree, no index file, no server process. For thousands to tens of thousands of vectors this is not a toy; it's the right amount of machinery.

```go
type VectorStore struct {
	records []Record
	dim     int // embedding dimension; all vectors must match
}

func New(dim int) *VectorStore {
	return &VectorStore{dim: dim}
}
```

The `dim` field is a guardrail. Every embedding from a given model has the same length, and comparing vectors of different lengths is meaningless — so we pin the dimension at construction and reject anything that doesn't fit.

---

## Normalize on insert, and search becomes a dot product

Here's a move that pays for itself immediately. Cosine similarity is the dot product of two vectors divided by the product of their magnitudes:

```text
cosine(a, b) = (a · b) / (||a|| * ||b||)
```

If both vectors are already **unit length** — magnitude exactly 1 — the denominator is `1 * 1 = 1`, and cosine similarity collapses to a plain dot product. So instead of recomputing magnitudes on every comparison, we normalize each vector *once* when it enters the store. From then on, scoring a query against a stored vector is a single loop of multiply-and-add, no division, no `math.Sqrt` in the hot path.

```go
import "math"

// normalize returns a unit-length copy of v. A zero vector is returned as-is
// (it has no direction to preserve).
func normalize(v []float32) []float32 {
	var sum float64
	for _, x := range v {
		sum += float64(x) * float64(x)
	}
	norm := math.Sqrt(sum)
	if norm == 0 {
		return v
	}
	out := make([]float32, len(v))
	inv := float32(1.0 / norm)
	for i, x := range v {
		out[i] = x * inv
	}
	return out
}

// dot assumes both inputs are already unit length, so it equals cosine similarity.
func dot(a, b []float32) float32 {
	var sum float32
	for i := range a {
		sum += a[i] * b[i]
	}
	return sum
}
```

`Add` normalizes and appends:

```go
import (
	"fmt"
	"sync"
)

// Add stores a record, normalizing its vector so later searches are dot products.
func (s *VectorStore) Add(id, text string, vector []float32) error {
	if len(vector) != s.dim {
		return fmt.Errorf("vector has dimension %d, store expects %d", len(vector), s.dim)
	}
	s.records = append(s.records, Record{
		ID:     id,
		Text:   text,
		Vector: normalize(vector),
	})
	return nil
}
```

**The gotcha:** if you normalize *stored* vectors but forget to normalize the *query* before searching — or vice versa — your `dot` result is no longer cosine similarity. It's some arbitrary scaled number that still *sorts* roughly right for a single query but silently breaks the moment you compare scores across queries or apply a similarity threshold like "only show hits above 0.75." Normalize on both sides, every time, or don't normalize at all and pay for the full cosine. Mixing the two is the subtle bug you'll waste an afternoon on.

---

## Brute-force k-NN: score everything, keep the best k

The simplest correct search is exhaustive: compute the query's similarity to *every* stored vector, then return the highest-scoring *k*. This is exact k-nearest-neighbor — no approximation, no chance of missing a true match. It is also, for a surprisingly large range of collection sizes, the right thing to do.

The naive implementation scores everything, sorts the whole list descending, and slices off the top *k*:

```go
import "sort"

// SearchSort is the obvious-but-wasteful version: score all, sort all, take k.
func (s *VectorStore) SearchSort(query []float32, k int) []Result {
	q := normalize(query)
	scored := make([]Result, len(s.records))
	for i, r := range s.records {
		scored[i] = Result{ID: r.ID, Text: r.Text, Score: dot(q, r.Vector)}
	}
	sort.Slice(scored, func(i, j int) bool {
		return scored[i].Score > scored[j].Score
	})
	if k > len(scored) {
		k = len(scored)
	}
	return scored[:k]
}
```

This works and it's easy to read. But look at what it does: it fully orders all *n* results just to keep *k* of them. When *k* is 5 and *n* is 50,000, we sorted 50,000 items to throw away 49,995. Sorting is `O(n log n)`; we're paying the `log n` factor on the entire collection to answer a top-5 question.

---

## Select, don't sort: a bounded min-heap

When `k << n`, the right tool is a **min-heap of size k**. Walk the records once. Keep a heap holding the *k* best scores seen so far, ordered so the *smallest* of those *k* sits at the root. For each new record: if the heap isn't full yet, push it; if it is full, compare the new score against the root (the current *k*-th best) — if the new score is larger, pop the root and push the newcomer; otherwise skip it. When the walk ends, the heap holds exactly the top *k*.

Each push/pop costs `O(log k)`, and we do at most one per record, so the whole search is `O(n log k)` instead of `O(n log n)`. Since *k* is a small constant like 5 or 20 while *n* grows without bound, `log k` is effectively a small fixed number — the search is linear in *n* with a tiny multiplier. That's a real, not cosmetic, win: you're doing `log k` work per item instead of `log n`.

Go ships `container/heap`, which needs a type implementing `heap.Interface`. We back it with a slice of results, ordered as a **min**-heap on `Score`:

```go
// minHeap orders results so the LOWEST score is at index 0 (the root).
// That lets us cheaply test whether a new candidate beats the weakest survivor.
type minHeap []Result

func (h minHeap) Len() int            { return len(h) }
func (h minHeap) Less(i, j int) bool  { return h[i].Score < h[j].Score }
func (h minHeap) Swap(i, j int)       { h[i], h[j] = h[j], h[i] }
func (h *minHeap) Push(x any)         { *h = append(*h, x.(Result)) }
func (h *minHeap) Pop() any {
	old := *h
	n := len(old)
	item := old[n-1]
	*h = old[:n-1]
	return item
}
```

Now the real `Search`:

```go
import (
	"container/heap"
	"sort"
)

// Search returns the top-k records by cosine similarity, highest first.
// It uses a bounded min-heap so the cost is O(n log k), not O(n log n).
func (s *VectorStore) Search(query []float32, k int) []Result {
	if k <= 0 || len(s.records) == 0 {
		return nil
	}
	q := normalize(query)

	h := &minHeap{}
	heap.Init(h)

	for _, r := range s.records {
		score := dot(q, r.Vector)
		if h.Len() < k {
			heap.Push(h, Result{ID: r.ID, Text: r.Text, Score: score})
			continue
		}
		// Heap is full: only keep this one if it beats the current weakest (root).
		if score > (*h)[0].Score {
			heap.Pop(h)
			heap.Push(h, Result{ID: r.ID, Text: r.Text, Score: score})
		}
	}

	// The heap holds the top k but in min-first order. Drain and reverse
	// so the caller gets highest similarity first.
	out := make([]Result, h.Len())
	for i := len(out) - 1; i >= 0; i-- {
		out[i] = heap.Pop(h).(Result)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Score > out[j].Score })
	return out
}
```

That final sort runs on at most *k* elements — a rounding error, not the `O(n log n)` we were trying to avoid. The heap did the selection over *n*; the sort just tidies the *k* survivors into descending order for the caller.

**The gotcha:** the whole point of a size-*k* heap is that it never grows past *k*, so the comparison against `(*h)[0]` before pushing is not optional — drop it and you've pushed all *n* items and rebuilt `SearchSort` with extra steps. Also mind the *direction*: it's a **min**-heap even though you want the **maximum** scores, because the cheap thing to inspect is "who's the weakest survivor I might evict." Reaching for a max-heap here feels natural and is exactly wrong.

---

## Concurrency: a shared store needs a lock

The store above is fine single-threaded. The moment a real service uses it, though, one goroutine may be serving a `Search` while another calls `Add` to ingest a new document. Appending to `s.records` while another goroutine ranges over it is a data race — Go's race detector will flag it, and in production it corrupts reads or panics.

The fix is a `sync.RWMutex`. Reads (searches) can run concurrently with each other, so they take the read lock; writes (adds) take the exclusive write lock:

```go
type VectorStore struct {
	mu      sync.RWMutex
	records []Record
	dim     int
}

func (s *VectorStore) Add(id, text string, vector []float32) error {
	if len(vector) != s.dim {
		return fmt.Errorf("vector has dimension %d, store expects %d", len(vector), s.dim)
	}
	rec := Record{ID: id, Text: text, Vector: normalize(vector)}
	s.mu.Lock()
	s.records = append(s.records, rec)
	s.mu.Unlock()
	return nil
}

func (s *VectorStore) Search(query []float32, k int) []Result {
	s.mu.RLock()
	defer s.mu.RUnlock()
	// ... heap search over s.records exactly as above ...
}
```

Note the normalization happens *before* taking the write lock — no reason to hold the lock during math. And use `RWMutex` rather than a plain `Mutex`: searches vastly outnumber inserts in most retrieval workloads, and a read-write lock lets all those searches proceed in parallel.

**The gotcha:** an unguarded store searched while it's being written is not "usually fine" — it's a race that passes a thousand times and then panics under load. If your store is written and read from different goroutines, the mutex isn't optional. And if you *never* mutate after startup — build the whole store once, then only search — you can skip the lock entirely. Know which world you're in; don't cargo-cult the mutex onto a read-only store and serialize your searches for nothing.

---

## A complete, runnable example

Here's the whole thing end to end: build a store, add a handful of embedded texts, query it, print ranked results. The `embed` function stands in for post 7's embedding step — in real code it calls an embedding model; here it's whatever deterministic vectorizer you built last time. The search machinery doesn't care where the numbers come from.

```go
package main

import (
	"fmt"

	"example.com/vstore"
)

// embed is post 7's embedding step. Swap in your real model call; the store
// only needs same-dimension []float32 vectors, however they're produced.
func embed(text string) []float32 { /* ... from post 7 ... */ return nil }

func main() {
	const dim = 256
	store := vstore.New(dim)

	docs := map[string]string{
		"doc-1": "The refund was processed and the money returned to the customer.",
		"doc-2": "Our data center lost power when the backup generator failed.",
		"doc-3": "You can reset your password from the account settings page.",
		"doc-4": "The customer was reimbursed in full for the cancelled order.",
		"doc-5": "Deploy the service by pushing to the main branch.",
	}
	for id, text := range docs {
		if err := store.Add(id, text, embed(text)); err != nil {
			panic(err)
		}
	}

	query := "How do I get my money back?"
	hits := store.Search(embed(query), 3)

	fmt.Printf("Query: %q\n\n", query)
	for rank, h := range hits {
		fmt.Printf("%d. [%.3f] %s — %s\n", rank+1, h.Score, h.ID, h.Text)
	}
}
```

With a working embedding model behind `embed`, the two refund sentences (`doc-1`, `doc-4`) rank at the top because they're *semantically* close to "get my money back" — even though the query shares almost no literal words with them. That's the payoff of vector search over keyword matching, and you built the retrieval side of it yourself.

```text
Query: "How do I get my money back?"

1. [0.812] doc-1 — The refund was processed and the money returned to the customer.
2. [0.788] doc-4 — The customer was reimbursed in full for the cancelled order.
3. [0.301] doc-3 — You can reset your password from the account settings page.
```

(Exact scores depend on your embedding model; the *ranking* is the point.)

---

## Complexity, honestly: when brute force is right and when it isn't

Let's be precise about the cost, because this is where people over-engineer. Each query scores *n* stored vectors, and each score is a dot product over *d* dimensions — so one search is `O(n · d)`. With the heap, selecting the top *k* adds `O(n log k)`, dominated by the scoring. There's no index to maintain, inserts are `O(d)` (just normalize and append), and memory is simply the vectors themselves.

For a collection of a few thousand to a few tens of thousands of vectors, this is genuinely fast — single-digit milliseconds on a modern CPU, and it's *exact*: it can never miss a true nearest neighbor the way an approximate method can. Say it plainly: **brute force is the correct default, not a placeholder.** Reaching for a vector database when you have 8,000 documents is solving a problem you don't have.

The catch is that the cost grows *linearly* with *n*. Double the collection, double every query's work. At a few thousand vectors that's invisible. At ten million it isn't — scoring ten million dot products per query, per user, blows your latency budget. That linear wall is exactly where **approximate nearest neighbor (ANN)** earns its place.

| Property | Brute-force (this post) | ANN (HNSW / IVF) |
|---|---|---|
| Query cost | `O(n · d)`, linear in n | roughly sub-linear / logarithmic in n |
| Exactness | exact — never misses | approximate — small recall trade-off |
| Index build | none | must build & tune an index |
| Memory | just the vectors | vectors + index overhead |
| Sweet spot | thousands–tens of thousands | hundreds of thousands–billions |

---

## What ANN buys you (and why you now understand it)

The intuition behind ANN is a trade: give up the *guarantee* of finding the exact nearest neighbors in exchange for not comparing against every vector. If you'll accept "the top 5 are almost certainly the true top 5, 98% of the time," you can skip the vast majority of the collection.

Two families dominate, and it's worth knowing them by name — without pretending to their APIs, which change and which you should read from the source:

- **HNSW (Hierarchical Navigable Small World)** — a *graph* method. Vectors become nodes connected to their near neighbors, in layers: a sparse top layer for long hops across the space and denser lower layers for local refinement. A search greedily walks the graph toward the query, touching a tiny fraction of the nodes. This is what many embedded libraries and vector databases use by default.
- **IVF and quantization (as in FAISS)** — a *partition-and-compress* method. IVF (inverted file) clusters vectors and, at query time, only scans the few clusters nearest the query instead of all of them. Product quantization compresses vectors into compact codes so more of the collection fits in memory and distance math gets cheaper. FAISS is the well-known library that packages these.

In production you rarely hand-roll ANN. You reach for **pgvector** (vector search inside Postgres, so your vectors live next to your relational data), a **dedicated vector database**, or an **embedded ANN library** you link into your service. But here's the thing — you now know precisely what each of those is optimizing. When pgvector asks you to pick between exact and HNSW indexing, or FAISS asks for an IVF cluster count, those aren't magic knobs. They're the exact trade-off you just felt in your own code: pay `O(n)` for a guaranteed-correct answer, or build an index that skips most of the work and accept a sliver of approximation. You built the baseline they improve on.

---

## Key takeaways

- **A vector store is a list of records** — id, text, and a `[]float32` embedding. The "database" part is far less machinery than the name suggests.
- **Normalize on insert** so every stored vector is unit length; then cosine similarity is a plain dot product with no division in the hot loop. Normalize the query too, or your scores stop meaning "cosine."
- **Brute-force exact k-NN is `O(n · d)` per query** and is the *correct default* for thousands to tens of thousands of vectors. It's not a placeholder — it never misses a true neighbor.
- **Select, don't sort.** A bounded min-heap of size *k* gets the top *k* in `O(n log k)`; sorting the whole collection wastes the `log n` factor on items you throw away.
- **Guard a shared store with `sync.RWMutex`** if it's searched while written — many concurrent reads, exclusive writes. Skip the lock only for a truly read-only store.
- **ANN (HNSW, IVF/quantization) trades exactness for speed** once *n* reaches the millions. pgvector, FAISS, and dedicated vector DBs are production implementations of that trade — and you now understand exactly what they optimize because you built the thing they replace.

Next up in post 9: retrieval is only half of RAG. We'll take this `Search` and feed its results into a prompt, so an LLM answers grounded in the documents you retrieved instead of its own memory.

---

## Further reading

- [Malkov & Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs" (arXiv:1603.09320)](https://arxiv.org/abs/1603.09320) — the HNSW paper.
- [pgvector](https://github.com/pgvector/pgvector) — vector similarity search as a Postgres extension, with exact and HNSW/IVFFlat indexing.
- [FAISS](https://github.com/facebookresearch/faiss) — Facebook AI's library for IVF, product quantization, and other ANN indexes; see its [wiki](https://github.com/facebookresearch/faiss/wiki).
- [Go `container/heap` package](https://pkg.go.dev/container/heap) — the standard-library heap used for top-k selection.
- [Go `sync` package](https://pkg.go.dev/sync) — `RWMutex` and friends for guarding the shared store.
