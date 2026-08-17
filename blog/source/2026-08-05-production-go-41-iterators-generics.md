# Range-over-func and Generics, Used Sparingly

*Two Go features I reached for in production payments code — range-over-func iterators and generics — and the discipline that keeps them from turning readable code into clever code. Both earn their place only when you stop reaching for them everywhere.*

---

Every language feature ships with an enthusiasm phase. When Go got generics in 1.18, half the codebase suddenly wanted a `Map[T, U]` helper. When range-over-func landed in 1.23, the temptation was to turn every slice into an iterator. I've done the cleanup on both. This post is about the narrow band where each of these features is genuinely the right tool — and, just as important, where a plain slice or a plain interface is still the better call.

The setting is a payments ledger service: a Postgres-backed store of transaction records, tens of millions of rows, queried constantly for reconciliation, reporting, and fraud review. The kind of code where "load it all into a slice" quietly becomes an OOM at 3 a.m.

---

## Part 1 — Range-over-func: streaming without materializing

Here's the problem range-over-func actually solves for me. A reconciliation job needs to walk every ledger entry for an account over a date range. The naive version returns `[]LedgerEntry`:

```go
func (s *Store) EntriesForAccount(ctx context.Context, acct string, from, to time.Time) ([]LedgerEntry, error) {
    rows, err := s.db.QueryContext(ctx, entriesQuery, acct, from, to)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var out []LedgerEntry
    for rows.Next() {
        var e LedgerEntry
        if err := rows.Scan(&e.ID, &e.Amount, &e.Currency, &e.PostedAt); err != nil {
            return nil, err
        }
        out = append(out, e)
    }
    return out, rows.Err()
}
```

For a retail account this is fine. For a merchant account with a few million entries in the window, `out` is a multi-hundred-megabyte slice that exists only so the caller can loop over it once and throw it away. We hold every row in memory at peak even though the consumer touches one at a time.

Before 1.23 the idiomatic fix was a callback: `func Each(..., fn func(LedgerEntry) error) error`. It works, but it inverts control — the caller can't `break`, can't easily accumulate across a couple of sources, and every consumer learns a bespoke signature. Range-over-func lets the streaming version *look* like the slice version at the call site.

### A push iterator over the DB cursor

`iter.Seq2[LedgerEntry, error]` is just a function that takes a `yield` callback. We call `yield` once per row and stop the moment it returns `false`:

```go
import "iter"

func (s *Store) Entries(ctx context.Context, acct string, from, to time.Time) iter.Seq2[LedgerEntry, error] {
    return func(yield func(LedgerEntry, error) bool) {
        rows, err := s.db.QueryContext(ctx, entriesQuery, acct, from, to)
        if err != nil {
            yield(LedgerEntry{}, err)
            return
        }
        defer rows.Close() // runs when the consumer breaks OR the range completes

        for rows.Next() {
            var e LedgerEntry
            if err := rows.Scan(&e.ID, &e.Amount, &e.Currency, &e.PostedAt); err != nil {
                yield(LedgerEntry{}, err)
                return
            }
            if !yield(e, nil) {
                return // consumer broke out; defer closes rows
            }
        }
        if err := rows.Err(); err != nil {
            yield(LedgerEntry{}, err)
        }
    }
}
```

The call site reads exactly like ranging over a slice, but memory stays flat — one `LedgerEntry` on the stack at a time, plus whatever the driver buffers:

```go
var total Money
for e, err := range s.Entries(ctx, acct, from, to) {
    if err != nil {
        return fmt.Errorf("scan ledger: %w", err)
    }
    total = total.Add(e.Amount)
}
```

Peak resident memory for the million-row reconciliation dropped from **`TODO: real number`** (materialized slice) to **`TODO: real number`** (streamed), which is the entire reason this function exists.

**The gotcha:** the `defer rows.Close()` inside the iterator is load-bearing and subtle. When the consumer does `break` (or `return`, or a labeled break), the runtime makes the current `yield` call return `false`, your iterator function returns, and *only then* do its deferred calls run. If you instead close `rows` in the caller, an early `break` leaks the DB cursor — the iterator body never got to its cleanup because nothing told it the loop ended. Put all resource cleanup inside the iterator, deferred, and early exit becomes correct for free.

### Error handling is a design decision, not an afterthought

There's no `return err` inside a `for range`. So an iterator has to decide how errors reach the consumer. I've seen three shapes; only two are good.

The `Seq2[T, error]` pattern above yields the error as the second value — clean, but it relies on the consumer checking `err` on every iteration. If they forget, a scan error silently becomes a zero-value entry. For a payments total that's a data-integrity bug, not a crash, which is worse.

The alternative I use when the consumer might be careless is a "capture" iterator: yield only values, stash the terminal error, and expose it after the loop.

```go
type EntryIter struct {
    seq func(yield func(LedgerEntry) bool)
    err error
}

func (it *EntryIter) All() iter.Seq[LedgerEntry] { return it.seq }
func (it *EntryIter) Err() error                 { return it.err } // check AFTER ranging
```

Now `for e := range it.All()` stays clean and the caller checks `it.Err()` once at the end — the same contract `bufio.Scanner` has used for a decade. The rule: if the loop can stop early on error, use `Seq2`; if you want the loop body uncluttered and a single post-loop check, capture the error. Pick one per package and be consistent.

### Composing iterators

Because an iterator is just a function, wrapping one is cheap and allocation-free. A filter that keeps only settled entries:

```go
func Settled(src iter.Seq2[LedgerEntry, error]) iter.Seq2[LedgerEntry, error] {
    return func(yield func(LedgerEntry, error) bool) {
        for e, err := range src {
            if err != nil {
                yield(LedgerEntry{}, err)
                return
            }
            if e.Status != StatusSettled {
                continue
            }
            if !yield(e, nil) {
                return
            }
        }
    }
}
```

`for e, err := range Settled(s.Entries(ctx, acct, from, to))` composes without ever building an intermediate slice. This is the part that feels like magic and is where restraint matters most: a three-stage `Map(Filter(Take(...)))` pipeline is elegant to write and miserable to debug, because a panic's stack trace runs through three anonymous `yield` frames. In production I keep composition to one, occasionally two, wrapping stages. Past that I write the plain loop — it's longer and far easier to read at 3 a.m.

**The gotcha:** early `break` propagates through composed iterators correctly *only if every layer honors `yield`'s `false` return*. The `if !yield(...) { return }` check isn't optional politeness — skip it in a wrapper and a downstream `break` won't stop the upstream source, so your DB cursor keeps pulling rows the consumer already abandoned. Every hand-written iterator must thread that boolean through. This is the single most common bug I see in range-over-func code.

---

## Part 2 — Generics: one abstraction that pays, and when interfaces still win

Generics tempt you toward a utility library of `Map`, `Filter`, `Reduce`. I've mostly deleted those. `slices` and `maps` in the standard library cover the common cases, and a bespoke `Reduce` reads worse than the loop it replaces. The place generics earned their keep in our service was a **typed, bounded LRU cache** — a genuine abstraction we needed at four different types (accounts, merchants, FX rates, risk scores) with identical mechanics.

Before generics this was either `map[string]interface{}` with a type assertion at every call site (a runtime panic waiting to happen) or four hand-copied caches that drifted apart. Generics collapse them into one type-safe implementation:

```go
type LRU[K comparable, V any] struct {
    mu    sync.Mutex
    cap   int
    ll    *list.List
    items map[K]*list.Element
}

type entry[K comparable, V any] struct {
    key   K
    value V
}

func NewLRU[K comparable, V any](capacity int) *LRU[K, V] {
    return &LRU[K, V]{
        cap:   capacity,
        ll:    list.New(),
        items: make(map[K]*list.Element, capacity),
    }
}

func (c *LRU[K, V]) Get(key K) (V, bool) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if el, ok := c.items[key]; ok {
        c.ll.MoveToFront(el)
        return el.Value.(*entry[K, V]).value, true
    }
    var zero V
    return zero, false
}

func (c *LRU[K, V]) Put(key K, value V) {
    c.mu.Lock()
    defer c.mu.Unlock()
    if el, ok := c.items[key]; ok {
        c.ll.MoveToFront(el)
        el.Value.(*entry[K, V]).value = value
        return
    }
    el := c.ll.PushFront(&entry[K, V]{key, value})
    c.items[key] = el
    if c.ll.Len() > c.cap {
        c.evict()
    }
}

func (c *LRU[K, V]) evict() {
    el := c.ll.Back()
    if el == nil {
        return
    }
    c.ll.Remove(el)
    delete(c.items, el.Value.(*entry[K, V]).key)
}
```

Now `NewLRU[string, Account](10_000)` and `NewLRU[MerchantID, RiskScore](5_000)` share one tested, race-checked implementation, and the compiler rejects putting an `Account` where a `RiskScore` belongs. `K comparable` is exactly the constraint a map key needs — the type system enforces it instead of a runtime panic on an unhashable key. Consolidating four caches into this one removed **`TODO: real number`** lines of near-duplicate code.

The `container/list` element still stores `any` internally, so there's a type assertion in `Get`/`Put` — but it's an assertion *we* control against a type *we* just stored, not one exposed to callers. That's the trade I'll take: an internal, provably-safe assertion in exchange for a fully typed public API.

### A constraints-based numeric helper, where generics are unambiguously right

The other place generics fit cleanly is arithmetic over a set of numeric types, which interfaces genuinely cannot express — you can't call `+` through an interface.

```go
import "golang.org/x/exp/constraints"

func Sum[T constraints.Integer | constraints.Float](xs []T) T {
    var total T
    for _, x := range xs {
        total += x
    }
    return total
}
```

Note I do **not** use this for `Money`. Payment amounts are a distinct type with rounding rules and currency; `Sum` over raw `int64` minor units is fine for a quick metric, but domain money gets its own `Add` method. Generics are for the mechanical, type-agnostic core — not for smuggling business rules into a `+`.

### When NOT to reach for generics

This is the half of the feature that gets skipped, so here it is plainly.

**When the behavior varies, use an interface.** If different types need different *logic* — not the same logic over different types — that's polymorphism, and an interface says it better. Our `PaymentProcessor` handles cards, ACH, and wallets with genuinely different code paths behind one interface. Making it generic would be a category error; there's no shared `T` body to parameterize.

```go
type PaymentProcessor interface {
    Authorize(ctx context.Context, p Payment) (AuthResult, error)
    Capture(ctx context.Context, id AuthID) error
}
```

**When there's exactly one type, don't parameterize on spec.** A `Cache[K, V]` used only ever as `Cache[string, Session]` is just a `SessionCache` wearing a costume. Write the concrete type; generalize the day the second caller actually appears, not before.

**Watch the readability and bloat costs.** Every type parameter is a mental variable the reader has to track; `Store[T, K, F comparable]` is a puzzle, not an API. And the compiler generates code per instantiation shape (GC-shape stenciling), so a generic function used at many pointer-ish and value types can quietly grow the binary — I've measured **`TODO: real number`** of binary growth from one over-eager generic package. Neither cost shows up in a toy example; both show up in a service you maintain for three years.

| Situation | Reach for | Why |
|---|---|---|
| Same mechanics, many types (cache, set, pool) | Generics | One tested body, compile-time safety |
| Arithmetic over numeric types | Generics + `constraints` | Interfaces can't express operators |
| Different logic per type | Interface | It's polymorphism, not parameterization |
| Exactly one concrete type today | Concrete type | Don't pay for flexibility you don't use |
| Common slice/map ops | `slices` / `maps` stdlib | Already written and tested |

---

## Key takeaways

- **Range-over-func is for streaming, not for style.** Its one killer use is walking an unbounded or huge source with bounded memory — a DB cursor, a paginated API, a file. If the data already fits in a slice, range the slice.
- **Cleanup lives inside the iterator, deferred.** That's what makes early `break` safe. And every wrapper must honor `yield`'s `false` return, or early exit won't propagate to the source.
- **Decide error handling up front:** `Seq2[T, error]` for stop-on-error loops, or a captured `Err()` checked once after the loop. Be consistent per package.
- **Generics pay when the mechanics are identical across types** — a cache, a set, a numeric reducer. They're the wrong tool when behavior varies (that's an interface) or when there's only one type today (that's a concrete type wearing a costume).
- **Both features punish overuse.** Deep iterator pipelines and gratuitous type parameters trade a little cleverness for a lot of debugging pain. Used sparingly, they're excellent; used everywhere, they're the reason the next engineer curses your name.

---

## Further reading

- [Range-Over Functions in Go](https://www.ardanlabs.com/blog) — Ardan Labs
