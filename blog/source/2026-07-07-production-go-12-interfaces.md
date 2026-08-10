# Interfaces

*How Go turns "what a value can do" into a first-class type — with implicit satisfaction, small contracts, the consumer-defined-interface rule, and the typed-nil trap that catches everyone once.*

---

An interface in Go is a **behavior contract**: a named set of method signatures. A value satisfies the interface if it has those methods — nothing more is required, and nothing more is checked. That single design decision, that satisfaction is *structural* rather than *declared*, is the reason Go's interfaces feel different from the `implements` clauses you know from Java or C#. Almost everything worth saying about Go interfaces follows from it.

This post is about using interfaces well: why implicit satisfaction is a superpower, why small interfaces beat big ones, where interfaces should be *defined*, and the one nil-related trap that every Go engineer walks into exactly once. The mechanical questions — how method sets work with pointer vs. value receivers, and how an interface value is laid out in memory — are covered in the methods post and the internals post respectively; I'll point at them where they matter.

---

## Implicit satisfaction: no `implements`, and why that wins

Here is a complete interface and a type that satisfies it. Notice what's *missing*.

```go
type Speaker interface {
    Speak() string
}

type Dog struct{ Name string }

func (d Dog) Speak() string { return d.Name + " says woof" }
```

`Dog` never mentions `Speaker`. There is no `implements Speaker`, no registration, no annotation. `Dog` satisfies `Speaker` because it has a `Speak() string` method — the compiler works this out at the point where you *use* a `Dog` as a `Speaker`:

```go
var s Speaker = Dog{Name: "Rex"} // compiles: Dog has Speak() string
fmt.Println(s.Speak())            // Rex says woof
```

This is **structural typing**, and it buys you two things you can't easily get with nominal `implements` systems.

First, **decoupling**. `Dog` doesn't import the package that defines `Speaker`. A type can satisfy an interface that didn't exist when the type was written, defined in a package the type's author never heard of. The dependency arrow points only one way: the code that *needs* the abstraction owns it.

Second, **retrofitting**. You can write an interface that describes types you don't control — including standard-library types — and they satisfy it for free if the methods line up. `*os.File` satisfies your `io.Reader`-shaped interface without `os` knowing your interface exists. This is impossible in a world where the type has to opt in by name.

**The gotcha:** implicit satisfaction means "does this compile" is your only satisfaction check, and it happens silently. If you *intend* a type to satisfy an interface and want the compiler to enforce it — say, so a missing method fails at build time in this package rather than at some distant call site — add a static assertion:

```go
var _ Speaker = Dog{}    // fails to compile if Dog stops satisfying Speaker
var _ Speaker = (*Dog)(nil) // same check, for a pointer receiver set
```

The blank identifier means "I want this checked, I don't want the value." Put one near the type definition and refactors that break the contract fail loudly and locally.

---

## Small interfaces are better: `io.Reader` as the model

The most reused interfaces in Go are the smallest. `io.Reader` is one method:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}
```

`io.Writer` is one method. `fmt.Stringer` is one method. `error` is one method. These are the load-bearing abstractions of the entire ecosystem, and their power comes *from* their smallness. A one-method interface is trivial to satisfy, so an enormous number of types satisfy it — files, network connections, byte buffers, HTTP bodies, gzip streams, cipher streams — and every function written against `io.Reader` composes with all of them.

Rob Pike's proverb states the principle directly: **the bigger the interface, the weaker the abstraction.** A ten-method interface describes almost nothing, because almost nothing has exactly those ten methods; you've coupled yourself to one concrete shape wearing an interface costume. A one-method interface describes a *capability*, and capabilities compose.

Concretely, prefer to accept the narrowest contract that does the job:

```go
// Weak: demands a whole *os.File, when all we do is read bytes.
func countLines(f *os.File) (int, error) { /* ... */ }

// Strong: accepts anything readable — file, socket, bytes.Buffer, strings.Reader.
func countLines(r io.Reader) (int, error) { /* ... */ }
```

The second version is testable without touching the filesystem (`strings.NewReader("...")` satisfies it), works over the network, and works in memory. Same code, dramatically wider reach — purely by asking for less.

---

## "Accept interfaces, return structs"

A companion idiom, and a good default: **accept interfaces, return concrete types.**

Accept interfaces because it maximizes what a caller can hand you, as we just saw. Return concrete types because it maximizes what the caller can *do* with the result. If a constructor returns an interface, the caller sees only that interface's methods — even when the concrete value has more to offer, and even when a later version of your type grows useful methods that the interface never learns about.

```go
// Good: caller receives the full, concrete *Client.
func NewClient(addr string) *Client { return &Client{addr: addr} }

// Usually worse: caller is boxed into whatever Doer exposes, forever.
func NewClient(addr string) Doer { return &Client{addr: addr} }
```

Returning a struct also keeps documentation and discoverability honest: the reader sees exactly what they got. The caller can still assign your `*Client` into their own narrow interface — that's *their* choice to make at the point of use, which is precisely where the abstraction belongs.

**The gotcha:** the idiom is a default, not a law. The clearest justified exception is `error`, which is an interface everyone returns — because callers genuinely should treat errors abstractly and inspect them with `errors.Is`/`errors.As` rather than reaching for concrete fields. Return an interface when the abstraction is genuinely the point (multiple real implementations the caller must stay agnostic about); return a struct the rest of the time.

---

## Defining interfaces at the consumer, not the producer

Structural typing lets you put an interface definition wherever it's most useful — and the most useful place is almost always the **consumer**, the package that *calls* the methods, not the package that *implements* them.

This inverts the instinct trained by nominal languages, where the implementer declares "I implement `PaymentGateway`" and therefore the interface lives near the implementation. In Go, put the interface next to the code that needs it:

```go
// package report — the CONSUMER. It defines exactly the slice it needs.
package report

type stockQuery interface {
    QuoteAt(ctx context.Context, symbol string, day time.Time) (float64, error)
}

func Build(ctx context.Context, q stockQuery, symbols []string) (*Report, error) {
    // uses only q.QuoteAt — nothing else about the data source
}
```

The producer — say a `marketdata` package with a fat `*Client` exposing dozens of methods — defines *no* interface. `report` declares the one-method slice of behavior it actually depends on, and `*marketdata.Client` satisfies it implicitly. The benefits stack up:

- The interface is minimal by construction, because the consumer only writes down what it uses.
- Tests in `report` mock `stockQuery` — one method — instead of a huge client.
- `marketdata` has zero dependency on `report`, and stays free to grow methods.
- Two different consumers can define two different, smaller views of the same producer.

A producer-defined interface, by contrast, tends to grow to mirror the whole implementation ("everything `*Client` can do"), which is the fat-interface anti-pattern wearing a bow tie. Let the consumer decide what "enough" means.

---

## Composing interfaces by embedding

Interfaces build up from smaller ones by **embedding** — naming one interface inside another merges its method set in. The standard library does this in the open:

```go
type Reader interface{ Read(p []byte) (n int, err error) }
type Writer interface{ Write(p []byte) (n int, err error) }

type ReadWriter interface {
    Reader
    Writer
}
```

`ReadWriter` is exactly "has `Read` and has `Write`." Any type with both methods satisfies it, and — because satisfaction is structural — a type that already satisfies `Reader` and `Writer` separately satisfies `ReadWriter` with no extra work. `io.ReadWriteCloser` is the same trick with three parts.

This is how you keep interfaces small *and* express richer requirements when you truly need them: compose at the point of use rather than authoring a monolith. A function that needs to both read and write asks for `io.ReadWriter`; one that only reads asks for `io.Reader`; neither forces the other to over-specify.

---

## The empty interface and `any`: when not to use it

An interface with **zero** methods is satisfied by *every* type, since every type trivially has all zero of its methods. This is `interface{}`, and since Go 1.18 it has the alias `any` — they are identical, and `any` is the spelling to use.

```go
func describe(v any) string {
    return fmt.Sprintf("%T: %v", v, v)
}
```

`any` is the right tool when you genuinely handle values of unknown type: `fmt.Println`, JSON decoding into an unknown shape, a generic container from before generics existed. But it is a contract that promises *nothing* — the moment you accept `any`, you've thrown away the compiler's help, and to do anything meaningful you must claw the type back with a type assertion or type switch:

```go
func length(v any) (int, error) {
    switch x := v.(type) {
    case string:
        return len(x), nil
    case []int:
        return len(x), nil
    default:
        return 0, fmt.Errorf("length: unsupported type %T", v)
    }
}
```

That `default` branch is the tell: with `any` you've moved a whole class of errors from compile time to run time. Two guidelines keep it in check:

- If you can name the behavior you need, define a small interface (`Stringer`, `io.Reader`, your own one-method contract) instead of `any`. The compiler then checks callers for you.
- If you need to write the same logic over many concrete types without losing type information, reach for **generics** — a type parameter constrained by an interface keeps the static guarantees `any` discards.

**The gotcha:** `any` is contagious. A field, map value, or return type of `any` pushes assertions onto everyone downstream, and each one is a run-time panic waiting for a bad input. Treat it as a boundary tool — parse it into a concrete or interface type early, and let the rest of your code work with something the compiler understands.

---

## The typed-nil trap: a non-nil interface holding a nil pointer

This is the interface bug that catches every Go engineer once, and it deserves a clear mental model even though the full mechanism belongs to the internals post.

An interface value is really a **pair**: a type descriptor and a value. It is `nil` only when *both* halves are empty — no type and no value. The trap is that a nil *pointer* still carries a type, so wrapping one in an interface produces an interface that is decidedly **not nil**:

```go
type appError struct{ msg string }

func (e *appError) Error() string { return e.msg }

func doWork(fail bool) error {
    var e *appError       // e is a nil *appError
    if fail {
        e = &appError{"boom"}
    }
    return e              // BUG: always returns a non-nil error
}

func main() {
    err := doWork(false)  // no failure...
    if err != nil {
        fmt.Println("got error:", err) // ...yet this prints!
    }
}
```

Even on the success path, `return e` wraps a `(*appError)(nil)` into the `error` interface. The interface now holds type `*appError` and value `nil` — the type half is populated, so `err != nil` is **true**, and the caller's error check fires on a "success." Depending on what happens next, this shows up as a spurious error or as a panic when someone dereferences the nil pointer inside a method that assumed a live receiver.

The fix is to never let a typed nil escape into an interface. Return the untyped `nil` literal explicitly, and keep concrete error variables concrete until the last moment:

```go
func doWork(fail bool) error {
    if !fail {
        return nil       // the untyped nil — genuinely a nil interface
    }
    return &appError{"boom"}
}
```

For *why* the pair works this way — the itab/type-word layout that makes a typed nil non-nil — see the interface internals post. The rule to carry day to day: **don't declare a concrete pointer, populate it conditionally, and return it through an interface.** Return `nil` (or the concrete value) directly on each path.

---

## Method sets decide satisfaction (pointer vs. value)

One last thing that trips people up, and a forward-reference. *Which* methods count toward satisfying an interface depends on whether you have a value or a pointer, because of **method sets**:

- A value of type `T` has the methods declared with value receivers (`func (t T)`).
- A pointer `*T` has *both* value-receiver and pointer-receiver (`func (t *T)`) methods.

So if `Speak` is declared on `*Dog`, then `*Dog` satisfies `Speaker` but a plain `Dog` value does **not** — and `var s Speaker = Dog{}` fails to compile while `var s Speaker = &Dog{}` succeeds:

```go
func (d *Dog) Speak() string { return d.Name + " says woof" } // pointer receiver

var s Speaker = Dog{}   // compile error: Dog does not implement Speaker
var s Speaker = &Dog{}  // OK: *Dog's method set includes Speak
```

The reasoning behind receiver choice — when to use pointer vs. value receivers, and how addressability interacts with all this — is the subject of the methods post. For interfaces, just remember: **check whether you're satisfying with `T` or `*T`, and match the receiver.** The static-assertion trick from earlier (`var _ Speaker = (*Dog)(nil)`) is the fastest way to pin down which one your callers actually need.

---

## Choosing well: a quick reference

| Situation | Do this |
|---|---|
| Function needs some behavior from its input | Accept the smallest interface that covers it |
| Function produces a value | Return the concrete type (struct), not an interface |
| Deciding where an interface lives | Define it in the consumer package, not the producer |
| Need to guarantee a type satisfies an interface | Add `var _ Iface = T{}` (or `(*T)(nil)`) near the type |
| Handling values of genuinely unknown type | `any` at the boundary, then assert/switch immediately |
| Same logic over many known types | Generics with an interface constraint, not `any` |
| Returning an error / optional pointer through an interface | Return `nil` literal on the empty path — never a typed nil |

---

## Key takeaways

- **Satisfaction is implicit and structural.** A type satisfies an interface by having the methods — no `implements`, no import of the interface's package. That enables decoupling and retrofitting types you don't own.
- **Small interfaces are strong interfaces.** `io.Reader`-sized contracts compose with everything; big interfaces describe one concrete shape and nothing else. The bigger the interface, the weaker the abstraction.
- **Accept interfaces, return structs.** Ask for the least, hand back the most — with `error` as the standing exception.
- **Define interfaces at the consumer.** Let the code that calls the methods declare exactly the slice of behavior it needs; the producer defines no interface at all.
- **Compose with embedding, not accretion.** Build `ReadWriter` from `Reader` and `Writer`; don't author monoliths.
- **`any` is a boundary tool.** It promises nothing and moves errors to run time — prefer a named interface or generics wherever you can name the behavior.
- **A typed nil in an interface is not nil.** Return the untyped `nil` on your empty paths; the pair-based internals are covered separately.
- **Method sets gate satisfaction.** `*T` carries pointer-receiver methods, `T` does not — match the receiver to what your callers hold.

---

## Further reading

- [Effective Go — Interfaces](https://go.dev/doc/effective_go#interfaces) — the canonical treatment of interface names, embedding, and conversions.
- [Go Proverbs](https://go-proverbs.github.io/) — Rob Pike's list, including "The bigger the interface, the weaker the abstraction" and "accept interfaces, return structs."
- [The Go Blog — Rob Pike, *Go Proverbs* (Gopherfest 2015)](https://go.dev/blog/) — the talk the proverbs come from, on designing with small interfaces.
