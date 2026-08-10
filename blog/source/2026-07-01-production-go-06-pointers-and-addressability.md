# Pointers and Addressability

*What a Go pointer actually is, why there's no pointer arithmetic, `new(T)` versus `&T{}`, the addressability rules that decide what `&` will even compile against, and when reaching for a pointer helps versus when it just adds indirection and GC pressure.*

---

Engineers arriving in Go from C or C++ think they already know pointers; engineers arriving from Python or Java think pointers are the scary part. Both are half right. A Go pointer is a genuine memory address — `&` takes one, `*` follows one — but the language deliberately strips away the two things that make pointers dangerous elsewhere: you cannot do arithmetic on them, and you cannot take the address of just anything. Those two restrictions are the whole story. Get them straight and the rest of Go's value-versus-pointer decisions stop being a matter of taste and start being a matter of mechanics.

This post is about those mechanics. Method receivers get their own treatment later in the series — here I'll only forward-reference them where the addressability rules force your hand. The goal is a reliable answer to two questions: *can I even take the address of this thing?* and *should I be passing a pointer here at all?*

---

## A pointer is an address, and that's genuinely all it is

A pointer holds the memory address of a value. `&x` produces the address of `x`; `*p` dereferences `p` to read or write the value it points at. The type `*T` is "pointer to a `T`", and it is a distinct type from `T` — the compiler tracks the difference for you.

```go
count := 42
p := &count // p has type *int, holds the address of count
*p = 43     // write through the pointer
fmt.Println(count) // 43 — count and *p are the same storage
```

The zero value of any pointer type is `nil` — a pointer that points at nothing. That single fact drives a lot of Go's idioms, and it's where most pointer bugs live. We'll come back to it.

What makes Go pointers *safe* relative to C is what you **can't** do with them. There is no `p++`, no `p + 1`, no casting an integer to a pointer in ordinary code. You cannot walk off the end of an array by nudging an address, because the language won't let you nudge an address at all.

**The gotcha:** the absence of pointer arithmetic is a design decision, not an oversight. Arithmetic on raw addresses is exactly what lets C code stride past the end of a buffer, and it's incompatible with a moving, compacting garbage collector — if the runtime relocates an object, any hand-computed address would silently point at garbage. Go keeps pointers as opaque handles the GC can track and rewrite. When you genuinely need address math (rare — think decoding a binary layout), it lives behind `unsafe.Pointer` and `unsafe.Add`, where the name is the warning label. If you find yourself reaching for `unsafe` to do ordinary work, step back; you almost certainly want a slice or a struct field instead.

---

## `new(T)` versus `&T{}`

There are two ways to allocate a value and get a pointer to it, and new Go engineers routinely wonder which one is "right".

`new(T)` allocates zeroed storage for a `T` and returns a `*T`. `&T{...}` builds a composite literal and takes its address. For structs, `&T{}` is the one you'll write ninety-nine times out of a hundred, because it lets you set fields at the same time.

```go
type Config struct {
    Retries int
    Verbose bool
}

a := new(Config)      // *Config → &Config{Retries: 0, Verbose: false}
b := &Config{}        // *Config → identical zero value
c := &Config{Retries: 3} // *Config with a field set — new() can't do this
```

For a struct, `new(Config)` and `&Config{}` produce exactly the same thing: a pointer to a fully zeroed value. `new` earns its place mainly with non-composite types where there's no literal syntax to take the address of — `new(int)` gives you an `*int` pointing at a zero, and there's no `&int{}` to write instead.

```go
n := new(int) // *int pointing at 0
*n = 5
```

**The gotcha:** don't agonize over this choice. The community convention is `&T{}` for structs (it reads as "a pointer to this specific value") and `new(T)` for the occasional pointer-to-primitive. Neither is faster; the compiler's escape analysis decides stack-versus-heap placement regardless of which spelling you used — that's the [escape analysis post](/blog/posts/production-go-37-escape-analysis-allocations.html) later in the series, not something the keyword controls.

---

## Addressability: what `&` will actually let you point at

Here is the rule that trips up experienced engineers, because it's specific to Go and it surfaces as compile errors that look arbitrary until you know the principle. **You can only take the address of something that is *addressable*** — something that occupies a stable, named storage location the compiler can name.

Addressable, so `&` works:

- **Variables:** `&x` where `x` is a local or package-level variable.
- **Slice elements:** `&s[i]` — a slice's backing array lives on the heap and the element has a real location.
- **Struct fields of an addressable struct:** `&cfg.Retries` when `cfg` is a variable.
- **Array elements of an addressable array**, and the result of dereferencing a pointer (`&*p`).

Not addressable, so `&` is a compile error:

- **Map elements:** `&m["key"]` does not compile.
- **The return value of a function or method** called inline: `&f()` does not compile.
- **Constants and literals:** `&42`, `&"hi"`.
- **The result of most expressions:** `&(a + b)`.

```go
s := []int{1, 2, 3}
p := &s[0] // fine — slice element is addressable

m := map[string]int{"a": 1}
// q := &m["a"]  // compile error: cannot take the address of m["a"]
```

The map case is the one you'll hit in real code. Map elements are not addressable because Go's map implementation is free to move entries as the table grows and rehashes — an address into it could be invalidated at any insert. The consequence you feel every day is that you **cannot mutate a struct field in place through a map**:

```go
type Account struct{ Balance int }
accounts := map[string]Account{"alice": {Balance: 100}}

// accounts["alice"].Balance += 50 // compile error: not addressable

// The two working shapes:
a := accounts["alice"] // copy out
a.Balance += 50
accounts["alice"] = a  // copy back

// or store pointers so the value itself is addressable heap storage:
ptrs := map[string]*Account{"alice": {Balance: 100}}
ptrs["alice"].Balance += 50 // fine — you're mutating through the pointer
```

**The gotcha:** the error message "cannot assign to struct field ... in map" is really the addressability rule wearing a different hat — assigning to `accounts["alice"].Balance` needs the field's address, and the map element has none. If a map's values are structs you intend to mutate, either copy-modify-store or make the value type `*Account` from the start. Choosing `map[K]*V` up front is the usual fix for anything mutated repeatedly.

The function-return case is the other one worth internalizing. `&getConfig()` won't compile because the return value is a temporary with no home. If you want a pointer to what a function produced, bind it to a variable first — `c := getConfig(); p := &c` — and now `c` is addressable.

---

## When to use a pointer

Three legitimate reasons, and it's worth being honest that only three carry their weight.

**1. Mutation.** If a function must change its caller's value, it needs the address. Passing a value passes a copy, and writes to the copy die at the return.

```go
func deposit(a *Account, amount int) { a.Balance += amount } // caller sees the change
func brokenDeposit(a Account, amount int) { a.Balance += amount } // mutates a throwaway copy
```

**2. Avoiding an expensive copy.** Go passes everything by value, so a big struct passed by value is copied in full on every call. Passing `*T` copies only the address (a machine word). This matters when the struct is genuinely large or the call is genuinely hot — measure before assuming it's either.

**3. Signalling optional / absence.** A `*T` can be `nil`, so a pointer distinguishes "no value" from "the zero value". This is the honest way to model a field that may be absent — an `*int` field is "unset (nil)" versus "explicitly zero (`*p == 0`)", a distinction a plain `int` can't make. It's the standard shape for optional JSON fields and nullable database columns.

```go
type UpdateUser struct {
    Name *string // nil = "leave unchanged"; non-nil = "set to this, even if empty"
}
```

---

## When *not* to use a pointer

The reflex to "just use a pointer" is where a lot of otherwise-fine Go picks up needless overhead.

**Small, copyable structs.** A `time.Time`, a `struct{ X, Y int }`, a handful of fields — copying these is cheaper than the indirection of chasing a pointer, and it keeps the value on the stack where the GC never has to think about it. The standard library returns `time.Time` by value for exactly this reason.

**Immutable or read-only values.** If nobody mutates it, a value communicates that intent and can't be `nil`. A value parameter is a small proof that the callee won't reach back and change your data.

**Reflexive indirection.** Every pointer you introduce is a potential `nil`, a potential heap allocation (if it escapes), and more work for the garbage collector. A `*string` field that is never nil and never shared is pure cost — it turned a value that could ride on the stack into heap storage the GC now has to trace. The performance module goes deep on escape analysis and GC pressure; the short version is that pointers aren't free, and "pointer = fast" is exactly backwards for small values.

Here's the trade-off in one table:

| Situation | Prefer | Why |
|---|---|---|
| Callee must mutate caller's data | `*T` | Only an address lets writes escape the call |
| Large struct on a hot path | `*T` | Copy one word, not the whole struct |
| Field may be genuinely absent | `*T` | `nil` distinguishes unset from zero |
| Small struct, read-only | `T` | Cheaper copy, stack-friendly, never nil |
| Value that's logically immutable | `T` | Communicates intent, removes a nil case |

---

## nil pointers and handling them safely

A `nil` pointer points at nothing, and **dereferencing it panics** with `invalid memory address or nil pointer dereference`. This is Go's version of the null-pointer bug, and the whole game is making nil unreachable at the point of dereference.

```go
func total(a *Account) int {
    if a == nil {
        return 0 // guard before the deref
    }
    return a.Balance
}
```

The subtle trap is nested access. `order.Customer.Address.City` panics the moment any link in that chain is nil, and the panic won't tell you which one. Guard the fields that can legitimately be absent, and — more importantly — design so that fewer of them can be. A value type can't be nil; a pointer field that's "always set after construction" is better modeled as a value, or enforced in a constructor, than defended at every read site.

**The gotcha:** a `nil` pointer is not always the same as a `nil` interface, and this is the single most notorious Go footgun. An interface holds *(type, value)*; a `(*T)(nil)` stored in an `error` interface is an interface whose type is `*T` and whose value is nil — and that interface is itself **not** `nil`. So `err != nil` is true even though the underlying pointer is nil.

```go
type MyErr struct{}
func (*MyErr) Error() string { return "boom" }

func doThing() error {
    var e *MyErr = nil
    return e // returns a NON-nil error interface wrapping a nil *MyErr!
}

if doThing() != nil {
    // this branch runs — surprising almost everyone the first time
}
```

The fix is to return a literal `nil` for the success case (`return nil`), never a typed nil pointer that gets boxed into the interface on the way out. Keep "no error" as an untyped `nil`, and the interface stays nil.

---

## Key takeaways

- **A pointer is just an address** — `&` takes one, `*` follows one — and Go deliberately omits pointer arithmetic so the GC can move objects safely. Address math lives behind `unsafe`, where you rarely belong.
- **`&T{}` for structs, `new(T)` for the odd pointer-to-primitive.** They produce identical results for structs; the choice is stylistic, and escape analysis — not the keyword — decides stack versus heap.
- **Addressability decides what `&` compiles against.** Variables, slice elements, and struct fields of addressable structs are addressable; map elements and inline function returns are not. That rule is why you can't mutate a struct field through a `map[K]V` — reach for `map[K]*V` instead.
- **Use a pointer for mutation, to dodge a large copy, or to signal absence — and value semantics otherwise.** Reflexive pointers add nil cases and GC pressure for no gain on small values.
- **nil dereferences panic, and a typed nil pointer boxed in an interface is not a nil interface.** Guard the pointers that can be absent, and return untyped `nil` for "no error".

---

## Further reading

- [The Go Programming Language Specification](https://go.dev/ref/spec) — see "Address operators", "Composite literals", "Allocation", and the definition of *addressable* operands for the precise rules behind everything above.
- [Effective Go](https://go.dev/doc/effective_go) — the "Allocation with `new`", "Allocation with `make`", and "Pointers vs. Values" sections cover the idiomatic choices in the language authors' own words.
