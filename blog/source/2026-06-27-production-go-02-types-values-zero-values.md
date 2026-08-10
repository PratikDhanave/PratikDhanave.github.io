# Types, Values, and Zero Values

*How Go's type system actually behaves — predeclared types, the zero-value guarantee that removes a whole class of null bugs, the "no implicit conversions" rule and why it exists, and the difference between a named type and a mere alias.*

---

Most languages let you get sloppy with types and quietly clean up after you: promote an `int` to a `float` mid-expression, treat a fresh struct field as `null` until you remember to set it, let two type names be interchangeable because they happen to wrap the same thing. Go does none of that. Its type system is small, but every rule in it is load-bearing — and once you internalize the four ideas below, a surprising amount of "why won't this compile" friction disappears and stays gone.

This post is about *values and their types*: what the predeclared types are, what a value is worth before you assign to it, why the compiler refuses to convert numbers for you, and when two types are genuinely the same versus merely similar. Constants get their own treatment later — here we only note that untyped constants exist, because they're the one place the conversion rules bend.

---

## The predeclared types: a short, deliberate list

Go ships a fixed set of built-in types. There are no surprises hiding in a standard library import — this is the whole basic vocabulary:

- **`bool`** — `true` or `false`. Not an integer in disguise; you cannot add it, and `if 1` does not compile.
- **Integers** — signed `int8 int16 int32 int64` and unsigned `uint8 uint16 uint32 uint64 uintptr`, plus the platform-sized `int` and `uint`.
- **Floating point** — `float32` and `float64`.
- **Complex** — `complex64` and `complex128`, for the rare numeric code that wants them.
- **`string`** — an immutable sequence of bytes, usually UTF-8 text.

Everything else — slices, maps, channels, structs, pointers, functions, interfaces — is a *composite* type built from these. The distinction matters for the next section: basic types and structs are **value types** (assigning copies them), while slices, maps, and channels are reference-like headers pointing at shared backing storage. That single fact explains most "why did my copy also change" confusion in Go, and it's worth holding onto.

```go
var (
    ok      bool    // false
    count   int     // 0
    ratio   float64 // 0
    label   string  // ""
    scores  []int   // nil
    lookup  map[string]int // nil
)
```

**The gotcha:** the value types in that block are *ready to use*; the reference types are not. `count++` is fine, `label + "!"` is fine, but writing to a nil map (`lookup["x"] = 1`) panics, because a nil map has no backing store. Reading from it is safe and returns the zero value — the asymmetry trips up nearly everyone once.

---

## `int` is not a fixed width — and that's the point

`int` and `uint` are the sizes the compiler picks for the target platform: 64 bits on every mainstream 64-bit build, 32 bits on 32-bit targets. `int` is *not* a synonym for `int64`. It is the type you should reach for by default — loop counters, lengths, indices, anything counting things in memory — precisely because it matches the machine word and the language uses it everywhere (`len`, `cap`, and slice indices are all `int`).

Reach for a **sized** integer only when the width is part of the contract: a wire format that says "32-bit big-endian," a bitmask with a fixed layout, a hash that must be exactly 64 bits, or a field where you're counting bytes of memory and the width matters. If you find yourself writing `int64` for an ordinary counter, you're usually overspecifying.

```go
func averageLatency(samples []int) int {
    total := 0            // int — the natural counter type
    for _, ms := range samples {
        total += ms
    }
    if len(samples) == 0 { // len returns int; comparison is int-to-int
        return 0
    }
    return total / len(samples)
}
```

**The gotcha:** because `int`'s width is platform-dependent, never *assume* it's 64 bits. Code that stuffs a value near 2^31 into an `int` works on your laptop and silently overflows on a 32-bit build. If a number can genuinely exceed a 32-bit range, say `int64` and mean it.

---

## The zero value guarantee: no such thing as "uninitialized"

Here is Go's quietest, most consequential design decision: **every variable has a well-defined value the instant it's declared**, whether or not you assign one. There is no "garbage memory," no "undefined behavior for reading before write," no uninitialized-variable class of bug. `var x T` gives you `T`'s zero value, and that value is deterministic:

| Type | Zero value |
|---|---|
| numeric (`int`, `float64`, …) | `0` |
| `bool` | `false` |
| `string` | `""` (empty, not nil) |
| pointer, slice, map, channel, func, interface | `nil` |
| struct | each field set to its own zero value, recursively |

The payoff is that well-designed Go types are **usable at their zero value** — you don't need a constructor to get a working object. `sync.Mutex` locks correctly when zero. `bytes.Buffer` is a ready-to-write buffer when zero. A struct of value-typed fields is fully formed the moment it's declared:

```go
type Counter struct {
    total int
    max   int
}

var c Counter          // {total:0, max:0} — no constructor needed
c.total++              // works immediately; no nil surprise
```

This is why idiomatic Go often skips the constructor a Java or C++ engineer reflexively writes. When you design a struct, ask: *does its zero value do something sensible?* If yes, callers can just `var t T` and go. If the zero value would be a broken half-object, that's a signal to either redesign the fields or provide a `NewT()` — and to document that the zero value is not ready.

**The gotcha:** the guarantee protects *value* types, not what pointers and reference types point *at*. A struct's `*Foo` field zeroes to `nil`, and dereferencing it panics exactly as you'd expect. The zero value removes the "did I forget to initialize this?" question for value types; it does not conjure a heap object behind a pointer. "Zero value is safe to read" and "the thing it references exists" are two different promises.

---

## Conversions are always explicit — the compiler will not coerce numbers

Go has no implicit numeric conversion. You cannot add an `int` to an `int64`, or assign a `float64` to a `float32`, without saying so:

```go
var i int = 3
var f float64 = 2.5

// total := i + f          // compile error: mismatched types int and float64
total := float64(i) + f    // 5.5 — explicit conversion, no ambiguity
count := int(total)        // 5   — truncates toward zero, and you can SEE it truncate
```

To a newcomer this reads as bureaucracy. To anyone who has chased a bug where a language silently widened, narrowed, or reinterpreted a number, it reads as relief. The rule exists so that **every lossy or representation-changing operation is visible in the source**. When you see `int(total)`, you know a float was truncated right there; nothing rounds or overflows off-screen. There's no C-style promotion ladder to memorize, no "which operand wins" table, no surprise where mixing a `uint32` and an `int` produces a value you didn't intend.

The one deliberate exception is **untyped constants**, which is why `f := 2.5` and `x := i + 1` just work. A literal like `1` or `2.5` has no fixed type until it's used; it adapts to context, so you rarely convert constants by hand. That flexibility is confined to constants precisely so that *variables* stay strict — the two rules reinforce each other rather than fighting. (Constants have enough depth to deserve their own post; for now, just know the strictness you feel with variables is intentional, and constants are the sanctioned escape hatch.)

**The gotcha:** a conversion is not a runtime check — `int(someFloat)` truncates without complaint, and converting a value that doesn't fit a narrower integer type quietly wraps. The compiler guarantees you *wrote* the conversion; it does not guarantee the result is meaningful. Explicitness buys you visibility, not validation.

---

## `byte` and `rune`: aliases that document intent

Two names in the predeclared set are pure aliases:

- `byte` is exactly `uint8`.
- `rune` is exactly `int32`.

They are the *same type* as what they alias — no conversion needed between `byte` and `uint8` — but the name carries meaning the raw integer type doesn't. `byte` says "this is raw data, an octet." `rune` says "this is a Unicode code point," which is what you get when you range over a string:

```go
s := "héllo"
fmt.Println(len(s)) // 6 — BYTES; é is two UTF-8 bytes

for i, r := range s {   // r is a rune (int32), a decoded code point
    fmt.Printf("%d:%c ", i, r) // index jumps 0,1,3,4,5 — the é spans two bytes
}
```

**The gotcha:** `len(s)` counts bytes, not characters, and indexing `s[i]` gives you the `byte` at that offset — a raw UTF-8 octet, not a character. Ranging over a string decodes runes for you; indexing does not. If you need character counts, use `utf8.RuneCountInString`. Confusing "length" with "number of characters" is the single most common string bug in Go, and it comes straight from not respecting the byte/rune distinction.

---

## Named types vs. aliases: same underlying type, different identity

You can build new types two ways, and they are *not* the same thing:

```go
type BasisPoints float64 // a DEFINED type — new identity, same underlying float64
type Percent = float64    // an ALIAS — literally another name for float64
```

A **defined type** (`type BasisPoints float64`) creates a genuinely new type. It shares `float64`'s underlying representation and operations, but it is a distinct type in the type system: you cannot assign a `BasisPoints` to a `Percent`, or mix a `BasisPoints` with a bare `float64`, without an explicit conversion. That's the feature — it lets the compiler stop you from adding an interest-rate spread to a raw ratio, or passing a `UserID` where an `OrderID` was expected. You also get to hang methods off it.

```go
type BasisPoints float64

func (bp BasisPoints) ToPercent() float64 { return float64(bp) / 100 }

var spread BasisPoints = 25
// var wrong float64 = spread        // compile error: distinct types
var ok float64 = float64(spread)     // explicit — intent is visible
fmt.Println(spread.ToPercent())      // 0.25 — methods ride on the defined type
```

An **alias** (`type Percent = float64`, note the `=`) creates no new type at all — it's a second spelling for the exact same type. `Percent` and `float64` are interchangeable everywhere, no conversion needed, and you cannot attach methods to an alias that you couldn't attach to `float64` itself. Aliases exist mainly for large refactors (gradually renaming a type across packages) and for re-exporting a type under a friendlier name — not for adding type safety.

**The gotcha:** the single `=` is the whole difference, and it's easy to skim past. `type T U` gives you a new, incompatible type (safety, methods, explicit conversions); `type T = U` gives you a nickname (zero safety, fully interchangeable). Reach for a defined type when you want the compiler to enforce a distinction; reach for an alias only when you explicitly want two names to mean one type.

---

## Key takeaways

- **The predeclared types are a short, fixed list**, and the value-vs-reference split among them explains most copy and nil surprises. Value types are ready at declaration; nil maps and channels are not.
- **Default to `int`.** Use a sized integer only when the width is genuinely part of the contract — wire formats, bitmasks, memory accounting.
- **Every variable is born with a defined zero value.** Design types so their zero value is useful, and you can skip constructors — but remember the guarantee covers value types, not what pointers reference.
- **Conversions are always explicit** so every lossy operation is visible in the source. Untyped constants are the one sanctioned exception, which keeps variables strict.
- **`byte`/`uint8` and `rune`/`int32` are the same types** — the aliases document intent (octet vs. code point), and the byte/rune distinction is why `len(s)` is not a character count.
- **`type T U` makes a new type; `type T = U` makes a nickname.** One `=` is the line between compiler-enforced safety and pure convenience.

Get these four rules — the zero value guarantee, explicit conversions, sensible defaults for `int`, and defined-type identity — into your fingers, and Go's type system stops feeling strict and starts feeling like a colleague that catches your mistakes before they ship.

## Further reading

- [The Go Programming Language Specification — Types](https://go.dev/ref/spec#Types) — the authoritative rules for predeclared types, zero values, conversions, and type identity.
- [The Go Blog](https://go.dev/blog/) — long-form articles on the type system, including the classic pieces on strings, bytes, and runes.
