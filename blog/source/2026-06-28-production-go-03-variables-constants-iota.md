# Variables, Constants, and iota

*How Go's declaration forms, scope rules, and its unusual constant system fit together — including the untyped-constant model that makes numeric literals feel effortless, and the `iota` patterns that turn enums and bit-flags into a few tidy lines.*

---

After years in Go you stop thinking about `var` versus `:=` — the fingers just pick the right one. But the rules underneath those reflexes are worth making explicit, because two of them (the `:=` shadowing trap and Go's untyped-constant model) are where even seasoned engineers get bitten or, more often, never fully understand *why* the code compiles at all. This post walks the whole surface: declarations, scope, constants, and `iota`. The goal is not to teach you `var x int` — it's to make the mental model precise enough that the edge cases stop surprising you.

---

## Declarations: four ways to introduce a name

Go gives you several spellings for "bind a value to a name," and they are not interchangeable stylistically even though they overlap functionally.

```go
var count int              // zero-valued: count == 0
var name = "pratik"        // type inferred from the initializer
var timeout = 5 * time.Second
port := 8080               // short declaration: var + inference, function scope only
```

The `var name type` form gives you the **zero value** — `0`, `""`, `false`, `nil` — with no initializer. This is not "uninitialized memory" the way it is in C; Go guarantees the zero value, and a huge amount of idiomatic Go leans on it. A `var buf bytes.Buffer` is immediately usable. A `var mu sync.Mutex` is a ready-to-lock mutex. Designing your own types so the zero value is useful is one of the quiet marks of good Go.

Short declaration with `:=` is `var` plus inference, but it only works **inside a function**. Package-level declarations must use `var` or `const`. That single restriction is why you'll see `var` at the top of files and `:=` almost everywhere inside functions.

**The gotcha:** `:=` requires that at least one variable on the left is *new*. `a, err := f()` followed by `b, err := g()` is legal — `err` is reused, `b` is new. But `a, err := f()` followed by `a, err := g()` in the *same scope* is a compile error ("no new variables on left side"). The moment you open a new block, though, `:=` will happily create a fresh `err` that shadows the outer one — which is the bug we're getting to.

---

## Grouped declarations and the `var` block

Both `var` and `const` accept a parenthesized block. This is not just cosmetic grouping — it's the natural home for related package state.

```go
var (
    ErrNotFound   = errors.New("record not found")
    ErrPermission = errors.New("permission denied")

    defaultTimeout = 30 * time.Second
    maxRetries     = 3
)
```

Package-level `var`s are initialized in **dependency order**, not source order — Go figures out that if `b = a + 1`, then `a` initializes first, regardless of where each line sits. Within one file, initialization respects those dependencies; `init()` functions then run after all package-level variables are set. Relying on this is fine; relying on *source order* between unrelated vars is not, because the spec only promises dependency ordering.

**The gotcha:** package-level `var`s with expensive or side-effecting initializers run at program startup, before `main`, in every build that imports the package — including test binaries. A `var db = mustConnect()` at package scope will try to connect during `go test` even for tests that never touch the database. Push that work into a constructor or `sync.Once` instead of a package-level initializer.

---

## Scope and shadowing

Go is lexically (block) scoped: a name is visible from its declaration to the end of the enclosing `{ }` block. Every `if`, `for`, `switch`, and bare `{ }` opens a new scope. An inner declaration with the same name as an outer one **shadows** it — the inner name wins for the rest of the inner block, and the outer variable is untouched.

```go
limit := 100
if debug {
    limit := 10          // NEW variable, shadows the outer limit
    log.Println(limit)   // prints 10
}
log.Println(limit)       // prints 100 — outer limit never changed
```

Sometimes shadowing is exactly what you want — a tightly-scoped temporary that can't leak. The problem is when you *meant* to assign to the outer variable and accidentally declared a new one.

**The gotcha — the classic `:=` shadowing bug:**

```go
func loadConfig() (*Config, error) {
    var cfg *Config
    if useRemote {
        cfg, err := fetchRemote()   // BUG: := declares a NEW cfg AND a new err
        if err != nil {
            return nil, err
        }
        _ = cfg                     // this inner cfg is discarded at block end
    }
    return cfg, nil                 // outer cfg is still nil!
}
```

Because `err` didn't exist yet, `:=` was tempting — but it created a *new* `cfg` scoped to the `if` block, so the outer `cfg` the function returns is never set. The fix is to declare `err` up front and use plain `=` inside the block:

```go
var cfg *Config
var err error
if useRemote {
    cfg, err = fetchRemote()        // assigns to the outer cfg and err
    if err != nil {
        return nil, err
    }
}
return cfg, nil
```

This is common enough that the tooling catches it: install the `shadow` analyzer binary with `go install golang.org/x/tools/go/analysis/passes/shadow/cmd/shadow@latest`, then run it via `go vet -vettool=$(which shadow)`; and every serious linter config (`golangci-lint`'s `govet` shadow check) flags it. Turn it on in CI — it costs nothing and catches a genuinely nasty class of bug.

---

## Constants: values fixed at compile time

A `const` in Go is a compile-time value. It has no address (you can't take `&MaxInt`), it can never be reassigned, and it can only hold values the compiler can compute during compilation: booleans, runes, integers, floats, complex numbers, and strings. You cannot make `time.Now()` or a slice a constant — those need runtime.

```go
const (
    maxUploadBytes = 10 << 20      // 10 MiB, computed at compile time
    apiVersion     = "v2"
    pi             = 3.14159
)
```

The genuinely interesting part of Go's constant system — the part that separates it from most languages — is the distinction between **typed** and **untyped** constants.

---

## Typed vs untyped constants

A constant declared with an explicit type is **typed**. One declared without is **untyped**, and it carries only a *default type* it falls back to when forced.

```go
const typedMax int = 9000          // typed: this is an int, full stop
const untypedMax = 9000            // untyped integer constant
```

Untyped constants are Go's quiet superpower. Two properties make them worth understanding deeply:

**1. Arbitrary precision.** Untyped numeric constants are represented by the compiler with far more precision than any concrete type — the spec guarantees at least 256 bits for integers and generous mantissa/exponent for floats. So intermediate constant arithmetic doesn't overflow or lose precision until you assign the result to a typed variable:

```go
const huge = 1 << 100              // fine as an untyped constant
const usable = huge >> 92          // == 256, fits in an int
// var overflow int = huge         // compile error: overflows int
```

**2. Implicit conversion at the point of use.** An untyped constant adopts the type it's assigned to or combined with — no explicit cast needed. This is why numeric literals feel so frictionless in Go, a language that otherwise forbids implicit numeric conversion between variables.

```go
const two = 2                      // untyped
var f float64 = two                // becomes float64, no cast
var i int32 = two                  // becomes int32, no cast
var d = two * time.Second          // becomes time.Duration

var count int = 3
// var bad = count * time.Second   // ERROR: int and Duration are distinct TYPES
var ok = two * time.Second         // OK: untyped 2 adapts to Duration
```

Notice the asymmetry: `count` (a typed `int` variable) cannot multiply a `time.Duration`, but the untyped constant `two` can, because it isn't an `int` yet — it becomes whatever the context needs.

**The gotcha:** the moment you give a constant an explicit type, you throw away this flexibility. `const two int = 2` can no longer silently become a `float64` or `time.Duration` — you're back to needing explicit conversions. So prefer untyped constants unless you specifically need to pin the type (e.g. to control a struct field's type or an API's signature). Untyped is the more powerful default; type it only when you have a reason.

---

## iota: the constant generator

`iota` is a predeclared identifier that acts as an auto-incrementing counter *within a single `const` block*. It starts at `0` on the first `ConstSpec` (line) of the block and increments by one for each subsequent line — whether or not that line mentions `iota`.

```go
const (
    Sunday = iota   // 0
    Monday          // 1  (expression repeats: = iota)
    Tuesday         // 2
    Wednesday       // 3
)
```

The key mechanic that trips people up: when a `const` line omits its expression, it **repeats the previous line's expression** — and because `iota` has advanced, the repeated expression yields a new value. That's why `Monday` through `Wednesday` don't need `= iota` written out.

**The gotcha:** `iota` counts **lines in the block**, not the number of times you write `iota`. A blank line does *not* increment it, but a `const` line that hard-codes a value *does* still advance the counter for the next line. And `iota` resets to `0` in every new `const` block — it is not a global counter.

---

## iota patterns you'll actually use

**Enums with a typed base.** Give the constants a named type so they're type-safe and get a `String()` method:

```go
type State int

const (
    StatePending State = iota   // 0
    StateActive                 // 1
    StateClosed                 // 2
)
```

**Skipping values with `_`.** Use the blank identifier to burn a value — commonly to make the zero value an invalid/unknown sentinel so a zero-valued `State` is distinguishable from a real one:

```go
type Priority int

const (
    _        Priority = iota   // 0 — reserved as "unset"
    Low                        // 1
    Medium                     // 2
    High                       // 3
)
```

**Scaling expressions.** Because each line repeats the expression, you can build a formula off `iota` once and let it apply to every line. Say you're defining service plan tiers whose per-second burst allowance climbs geometrically:

```go
type BurstLimit int

const (
    _                     = iota            // skip tier 0
    Basic     BurstLimit = 1 << (4 * iota)  // 1 << 4  = 16 req/s
    Standard                                // 1 << 8  = 256 req/s
    Premium                                 // 1 << 12 = 4096 req/s
)
```

One expression, `1 << (4 * iota)`, written once, expands correctly down the block because `iota` advances on each line — each tier lands four bit-positions above the one before it.

**Bit-flag sets with `1 << iota`.** For flags you want to OR together, shift a single bit by `iota` so each constant occupies its own bit position:

```go
type Perm uint8

const (
    PermRead    Perm = 1 << iota   // 1  (0b001)
    PermWrite                      // 2  (0b010)
    PermExecute                    // 4  (0b100)
)

// Combine and test:
access := PermRead | PermWrite     // 0b011
canWrite := access&PermWrite != 0  // true
```

**The gotcha:** bit-flags and sequential enums are not interchangeable. `1 << iota` gives you `1, 2, 4, 8…` — distinct bits you can combine with `|`. Plain `iota` gives you `0, 1, 2, 3…` — mutually exclusive states you compare with `==`. Using `iota` (not `1 << iota`) for something you intend to OR is a real bug: `Read=1, Write=2, Execute=3` means `Read|Write == Execute`, and your permission check silently misfires.

---

## Giving enums a String() method

Integer enums print as integers, which is useless in logs. The convention is a `String()` method so the type satisfies `fmt.Stringer`. You can hand-write it, but the standard tool is `stringer` (`golang.org/x/tools/cmd/stringer`), driven by a `go:generate` directive:

```go
//go:generate stringer -type=State
type State int

const (
    StatePending State = iota
    StateActive
    StateClosed
)
```

Running `go generate ./...` produces a `state_string.go` with an efficient `String()` implementation. Two things to know: `stringer` reads the *source order* of your constants, so reordering them silently changes the generated names — regenerate after any edit. And it handles gaps and non-contiguous values just fine: it emits several contiguous runs (or falls back to a map) when your values jump around, so individual bit-flag values like `PermRead = 1`, `PermWrite = 2`, `PermExecute = 4` each map cleanly to their own name. The real limitation is *OR-combined* values: `PermRead | PermWrite == 3` has no constant of its own, so `stringer` has no name for it and it prints as `Perm(3)`. That's why bit-flag sets usually want a hand-written `String()` that decomposes the value into its set bits. (Note that `-linecomment` is unrelated to any of this — it lets you supply custom names via trailing `// comment` lines on each constant, not a remedy for non-contiguity.)

---

## Quick reference

| Construct | Where it works | Gives you | Watch out for |
|---|---|---|---|
| `var x T` | package or function | zero value of `T` | expensive pkg-level initializers run at startup |
| `var x = v` | package or function | inferred type | dependency-ordered init, not source order |
| `x := v` | function only | inferred type, one new name required | shadowing across block boundaries |
| untyped `const` | package or function | arbitrary precision, adapts at use | loses flexibility once you add a type |
| typed `const` | package or function | fixed type, type-safety | no implicit conversion |
| `iota` | inside one `const` block | line counter from 0 | counts lines, resets per block |
| `1 << iota` | inside one `const` block | distinct bit flags | don't confuse with sequential enums |

---

## Key takeaways

- **Prefer the zero value.** Design types so `var x T` is immediately usable; a lot of idiomatic Go depends on it.
- **`:=` creates; `=` assigns.** The shadowing bug is `:=` silently making a new variable in an inner block when you meant to assign outward. Turn on the vet shadow check.
- **Package-level `var` initializers run at startup**, including in tests — keep expensive work out of them.
- **Untyped constants are the powerful default.** Arbitrary precision plus implicit adaptation at the point of use is why literals feel seamless; only add a type when you truly need to pin one.
- **`iota` counts lines in a block**, repeating the previous expression. Use plain `iota` for exclusive enums, `1 << iota` for combinable bit-flags, `_` to reserve or skip, and `stringer` to make them print sensibly.

Constants and `iota` reward a precise mental model far out of proportion to how little syntax they involve. Once the untyped model clicks, a whole category of "why does this cast work but not that one" questions simply dissolves.

---

## Further reading

- [Constants — The Go Blog](https://go.dev/blog/constants) — the definitive explanation of the untyped-constant model and arbitrary precision.
- [The Go Programming Language Specification — Constants, Declarations and scope, Iota](https://go.dev/ref/spec) — the normative rules for everything above.
