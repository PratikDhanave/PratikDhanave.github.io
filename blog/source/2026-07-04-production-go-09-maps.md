# Maps

*How Go's built-in hash table really behaves — reference semantics, the nil-write panic, comma-ok, randomized iteration, why `&m[k]` is illegal, and the presizing and concurrency rules that separate correct map code from the code that bites you at 2 a.m.*

---

The map is the workhorse collection in Go. You reach for it dozens of times a day and it mostly does what you expect, which is exactly why its sharp edges are dangerous — they hide behind an interface that feels obvious. Most of the "surprising" map behavior is not surprising at all once you know one fact: a map is a *handle* to a hash table living somewhere else on the heap. Almost every gotcha in this guide falls out of that single idea.

This is a teaching guide for engineers who already use maps fluently but want the model that explains *why* the compiler rejects `&m[k]`, why your test passed a hundred times and then failed in CI, and why a map written from two goroutines crashes the whole process instead of just corrupting a value. We'll build that model, then walk each trap with code that gets it right.

---

## A map is a header, not the table

When you write `m := map[string]int{}`, the variable `m` is not the hash table. It's a small header — a pointer, essentially — to a `runtime.hmap` structure that owns the buckets. That indirection is the root of map semantics.

```go
func addOne(m map[string]int) {
    m["count"]++ // mutates the caller's table
}

func main() {
    counts := map[string]int{"count": 0}
    addOne(counts)
    fmt.Println(counts["count"]) // 1
}
```

Passing a map to a function copies the header, not the table. Both copies point at the same buckets, so `addOne` mutates what `main` sees. People call maps a "reference type" for this reason. Be precise about what that means: the map value is still passed *by value* — you just copied a pointer-sized handle, so the copy and the original alias the same underlying data.

**The gotcha:** because the header is a value, reassigning the parameter inside the function is invisible to the caller. `m = make(map[string]int)` inside `addOne` rebinds the local copy of the header and the caller keeps the old map. You can mutate the *contents* through any copy of the header, but you cannot swap out *which table* the caller points at. If you need that, return the new map or take a `*map` (rarely worth it).

---

## The zero value is nil, and writing to it panics

The zero value of a map type is `nil`, not an empty map. This is the single most common map bug in real code, because a `nil` map is *readable* — it just behaves like an empty one — so the mistake stays silent until the first write.

```go
var m map[string]int // nil

fmt.Println(m["missing"]) // 0 — reads are fine
fmt.Println(len(m))       // 0 — fine
for k := range m {        // fine, zero iterations
    _ = k
}

m["key"] = 1 // panic: assignment to entry in nil map
```

Reading a `nil` map returns the element type's zero value; ranging over it does nothing; `len` is zero; `delete` on it is a no-op. The moment you *assign*, the runtime panics because there are no buckets to write into.

**The gotcha:** the danger is that `nil` maps read like empty maps, so a struct field or a map returned from a function can be `nil` and pass every read path in your tests, then panic in production on the first write. Always initialize before writing:

```go
type Registry struct {
    handlers map[string]func()
}

func NewRegistry() *Registry {
    return &Registry{handlers: make(map[string]func())} // never leave it nil
}
```

Initialize map fields in your constructor. If a function returns a map that callers might write to, return `make(map[K]V)`, not `nil`. Returning `nil` for "no results" is fine *only* when you can guarantee callers will read but never write.

---

## Comma-ok: presence versus zero

Indexing a map always succeeds. `m[k]` for an absent key returns the zero value, which means you cannot distinguish "the key is missing" from "the key is present with a zero value" using the single-value form. The two-value *comma-ok* form is how you tell them apart.

```go
scores := map[string]int{"alice": 0}

v := scores["bob"]      // 0 — but bob isn't here
v = scores["alice"]     // 0 — and alice IS here, with value 0

v, ok := scores["bob"]  // v == 0, ok == false
v, ok = scores["alice"] // v == 0, ok == true
```

Any time zero (or `""`, or `nil`, or `false`) is a legitimate stored value, you *must* use comma-ok to check presence. This matters for the set idiom too, where the value carries no information and presence is the whole point:

```go
seen := map[string]struct{}{}
seen["x"] = struct{}{}

if _, ok := seen["x"]; ok {
    // x has been seen
}
```

`struct{}` occupies zero bytes, so `map[K]struct{}` is the idiomatic Go set — leaner than `map[K]bool` and it forces you to write the presence check explicitly, which reads more honestly than testing a boolean value.

---

## delete, and deleting while you range

`delete(m, k)` removes a key. It's a no-op on a missing key and a no-op on a `nil` map — it never panics — so you don't need to guard it.

Deleting during iteration is one of the few mutation-while-ranging operations Go explicitly permits and defines:

```go
for k, v := range cache {
    if v.expired() {
        delete(cache, k) // safe and defined
    }
}
```

The spec guarantees this: if you delete a key that hasn't been reached yet, it won't be produced; keys already produced are unaffected. So deleting the current or a not-yet-visited key during range is well-defined.

**The gotcha:** *adding* keys during iteration is a different story. If you insert during a range, the new entry "may be produced during the iteration or may be skipped" — it's implementation-defined, not a crash but not deterministic either. Never rely on visiting entries you add mid-range. If you must add while iterating, collect the additions in a slice and apply them after the loop.

---

## Iteration order is randomized on purpose

Range over a map twice and you'll likely get two different orders. This is not "unspecified, happens to be stable" — the Go runtime *deliberately* randomizes the starting point of each range. It picks a random bucket and offset every time you start iterating.

```go
m := map[string]int{"a": 1, "b": 2, "c": 3}
for k := range m {
    fmt.Print(k, " ") // order differs run to run: "b c a", "a c b", ...
}
```

Why go out of the way to randomize? Because Go's authors wanted to kill the class of bug where code accidentally depends on hash-table order. A hash map has no meaningful order to begin with — the layout is an artifact of the hash function and insertion history. Had iteration happened to be stable in one Go version, people would have written code relying on it, and a future runtime change (or a different key set) would silently break them. Randomizing makes the non-determinism *loud*: you discover the dependency immediately, in development, instead of in a customer's edge case.

**The gotcha:** never rely on iteration order for anything — not test assertions, not output formatting, not hashing, not "the first key wins" logic. When you need order, extract the keys and sort them:

```go
keys := make([]string, 0, len(m))
for k := range m {
    keys = append(keys, k)
}
sort.Strings(keys)
for _, k := range keys {
    fmt.Printf("%s=%d\n", k, m[k])
}
```

This is the canonical pattern for deterministic map output, and it's why `fmt` prints maps sorted by key — the standard library does the sort for you so `%v` output is reproducible, but a raw `range` does not.

---

## You cannot take the address of a map element

This compiles for a slice but not for a map:

```go
s := []int{1, 2, 3}
p := &s[0] // fine

m := map[string]int{"a": 1}
p := &m["a"] // compile error: cannot take the address of m["a"]
```

The reason is mechanical, not arbitrary. A map grows by rehashing, which *moves* entries to new buckets. If the language handed you a pointer into a bucket, the next insert could relocate that entry and leave your pointer dangling. Rather than track and update every outstanding pointer, Go forbids taking the address at all. Map elements are not addressable.

The practical consequence bites hardest with struct values. You cannot mutate a field of a struct stored directly in a map:

```go
type Point struct{ X, Y int }

m := map[string]Point{"origin": {0, 0}}
m["origin"].X = 5 // compile error: cannot assign to struct field m["origin"].X
```

There are two correct fixes. Store pointers, so the map holds an addressable thing:

```go
m := map[string]*Point{"origin": {0, 0}}
m["origin"].X = 5 // fine — you're dereferencing a pointer, not addressing a map slot
```

Or, if you want value semantics, read the whole struct out, modify the copy, and write it back:

```go
m := map[string]Point{"origin": {0, 0}}
p := m["origin"] // copy out
p.X = 5
m["origin"] = p // whole-value reassignment
```

**The gotcha:** the read-modify-write pattern is safe but easy to get subtly wrong — if you forget the write-back, you've mutated a throwaway copy and the map is unchanged, with no error. Choose deliberately: `map[K]*V` when entries are large or frequently mutated in place, `map[K]V` with copy-out/write-back when values are small and you want the safety of value semantics. Don't mix the two mental models in one map.

---

## Comparable keys: structs and arrays are fair game

A map key type must be *comparable* — it must support `==`. That rules out slices, maps, and functions as keys (they aren't comparable and the compiler will reject them). But it *includes* structs and arrays whose fields are all comparable, which is a genuinely useful tool.

```go
type Coord struct{ X, Y int }

grid := map[Coord]string{}
grid[Coord{1, 2}] = "tree"
grid[Coord{3, 4}] = "rock"

fmt.Println(grid[Coord{1, 2}]) // "tree"
```

A struct key gives you a clean composite key with no string concatenation and no delimiter-collision bugs (the classic `fmt.Sprintf("%d:%d", x, y)` approach breaks the moment a field can itself contain the delimiter). Arrays work as keys too — `[2]int{1, 2}` is comparable — while slices do not.

**The gotcha:** comparability is checked structurally. A struct containing a slice field is *not* comparable, so it can't be a key, and you'll only find out at compile time (or, worse, at runtime with `panic: runtime error: comparing uncomparable type` if the field is `interface{}` holding a slice). Also beware floating-point fields: `NaN != NaN`, so a struct key with a `NaN` float field can never be found again after insertion — you can store it but never read it back. Keep key types small and made of integers, strings, bools, and other clean comparables.

---

## Maps are not safe for concurrent use

A Go map is not safe for concurrent access when at least one goroutine is writing. This is not "you might get a torn read" — the runtime actively detects concurrent map writes and *crashes the program* with `fatal error: concurrent map writes`. It's a `fatal error`, not a `panic`, so you cannot `recover` from it; the whole process dies.

```go
m := map[int]int{}
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(i int) {
        defer wg.Done()
        m[i] = i // DATA RACE — may crash with fatal error
    }(i)
}
wg.Wait()
```

The crash-on-detection is intentional: a silently corrupted hash table is far more dangerous than a loud, immediate failure. The fix is to serialize access. A `sync.RWMutex` is the general-purpose answer — many concurrent readers, exclusive writers:

```go
type Counter struct {
    mu sync.RWMutex
    m  map[string]int
}

func (c *Counter) Inc(k string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.m[k]++
}

func (c *Counter) Get(k string) int {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.m[k]
}
```

**The gotcha:** concurrent *reads* with no writer are fine — the crash only triggers when a write races with any other access. That's a trap, because a read-heavy map can run correctly for months and then crash the day someone adds a write path. Guard the map from the start if it will ever be written concurrently. The standard library also offers `sync.Map` for two narrow cases (append-only caches, and keys written once then read many times by disjoint goroutines); for the common read-modify-write counter, a plain map behind a mutex is faster and clearer. We cover the concurrency toolkit — mutexes, `sync.Map`, and when each wins — in the concurrency module.

---

## Presize with make(map, n) when you know the size

`make(map[K]V, n)` gives the runtime a size hint. It's a *hint*, not a fixed capacity — the map still grows unbounded — but it lets the runtime allocate enough buckets up front to hold roughly `n` elements without rehashing.

```go
// Building a lookup from a known slice — presize it.
byID := make(map[int]*User, len(users))
for _, u := range users {
    byID[u.ID] = u
}
```

Without the hint, the map starts small and rehashes repeatedly as it grows, each rehash reallocating buckets and moving every entry. For a map you're about to fill with a known number of items, presizing eliminates that churn. It's a cheap, high-signal optimization on any hot path that builds a map from a collection of known size.

**The gotcha:** the hint only helps when you actually know the size and it's non-trivial. Don't cargo-cult `make(map[K]V, 0)` — that's identical to `make(map[K]V)`. And the hint doesn't cap growth or preallocate for a size you'll never reach, so wildly over-hinting just wastes memory. Match the hint to the real expected element count.

---

## Quick reference

| Operation | Behavior | Watch out for |
|---|---|---|
| `var m map[K]V` | `nil` map | Reads OK, **write panics** |
| `m[k]` (absent) | zero value | Can't tell missing from zero — use comma-ok |
| `v, ok := m[k]` | value + presence | The only way to check presence reliably |
| `delete(m, k)` | remove, no-op if absent | Safe on nil; safe during range |
| `range m` | randomized order | Never depend on order; sort keys for determinism |
| `&m[k]` | compile error | Elements not addressable — use `map[K]*V` or copy-out |
| concurrent write | `fatal error`, process dies | Guard with mutex; can't `recover` |
| `make(map, n)` | size hint | Only helps with a known non-trivial size |

---

## Key takeaways

- **A map is a header over a heap table.** Copies of the header alias the same table (mutations show through), but reassigning a copy doesn't reach the caller. Nearly every map rule follows from this.
- **The zero value is `nil` and writes to it panic.** Reads on `nil` succeed, which hides the bug until the first write — initialize map fields and returned maps that callers might write.
- **Use comma-ok whenever zero is a valid value.** Single-value indexing can't distinguish absent from zero.
- **Iteration order is deliberately randomized.** Sort keys when you need determinism; never encode order dependence.
- **Map elements aren't addressable.** Store `map[K]*V`, or read-modify-write the whole value — and don't forget the write-back.
- **Struct and array keys are comparable and useful**, but a slice/map/func field makes the whole key uncomparable, and `NaN` float fields are unfindable.
- **Concurrent writes crash the process.** Guard shared maps with a mutex from day one; read-only concurrency is the only exception.
- **Presize with `make(map, n)`** when the element count is known to skip repeated rehashing.

## Further reading

- [Go maps in action](https://go.dev/blog/maps) — the Go blog's tour of map semantics, the comma-ok idiom, and concurrency.
- [The Go Programming Language Specification — Map types](https://go.dev/ref/spec#Map_types) and [For statements with range clause](https://go.dev/ref/spec#For_range) — the normative rules on nil maps, comparable key types, and iteration-order and delete-during-range guarantees.
