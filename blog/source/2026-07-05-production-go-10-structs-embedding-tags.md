# Structs, Embedding, and Tags

*How Go builds aggregate types from value semantics up — why a struct is a copy, when it stops being comparable, what embedding actually promotes (and what it deliberately doesn't), and how a backtick string in a field definition ends up steering `encoding/json`.*

---

Structs are the workhorse of Go's type system. There are no classes, no inheritance hierarchies, no attribute dictionaries — just named collections of fields with value semantics, and a small set of composition rules layered on top. That minimalism is deceptive. The behavior of a struct is governed by three things that trip up experienced engineers coming from other languages: it is copied by value, its comparability is derived from its fields, and its "inheritance" is actually delegation dressed up with syntactic sugar.

This guide walks each of those, plus the two features people reach for constantly without fully understanding — struct tags and the empty struct.

---

## 1. Definitions and composite literals

A struct is a fixed layout of named fields. You declare the type once and instantiate it with a composite literal.

```go
type Point struct {
	X, Y int
}

type Rectangle struct {
	Min, Max Point
	Label    string
}

r := Rectangle{
	Min:   Point{X: 0, Y: 0},
	Max:   Point{X: 10, Y: 5},
	Label: "viewport",
}
```

Prefer the **keyed** form (`Min: ...`) over the positional form (`Rectangle{Point{0,0}, Point{10,5}, "viewport"}`). Keyed literals survive field reordering and new-field additions without silently shifting values into the wrong slots, and they let you omit fields you want zero-valued. The zero value of a struct is every field at its own zero — no constructor runs, no field is left undefined. `var r Rectangle` gives you a fully usable value with empty points and an empty label.

**The gotcha:** the positional literal requires *every* field, in order, and breaks the moment someone adds a field to the struct. Worse, it compiles fine if two adjacent fields share a type — the values just land in the wrong fields. Reserve positional literals for tiny, stable types like `Point{0, 0}` where the field order is self-evident.

---

## 2. Value semantics: a struct is a copy

This is the single most consequential fact about structs in Go. Assigning a struct, passing it to a function, or ranging over a slice of them **copies the whole value**. Mutations to the copy do not touch the original.

```go
func moveRight(r Rectangle, dx int) {
	r.Min.X += dx // mutates the local copy only
	r.Max.X += dx
}

r := Rectangle{Min: Point{0, 0}, Max: Point{10, 5}}
moveRight(r, 3)
// r.Min.X is still 0 — the function mutated a copy
```

To mutate the caller's value, pass a pointer:

```go
func moveRightP(r *Rectangle, dx int) {
	r.Min.X += dx
	r.Max.X += dx
}

moveRightP(&r, 3) // now r.Min.X == 3
```

The same trap hides in `for range`. The loop variable is a copy of each element, so writing to it changes nothing on the backing array:

```go
rects := []Rectangle{{Label: "a"}, {Label: "b"}}
for _, rc := range rects {
	rc.Label = "changed" // writes to a copy, discarded each iteration
}
// rects is unchanged; index with rects[i].Label to mutate in place
```

**The gotcha:** copying is *shallow*. A struct that contains a slice, map, or pointer copies the header or pointer, not the data behind it. Two copies of such a struct share the same backing array or map — mutating an element through one copy is visible through the other, even though reassigning the field itself is not. Value semantics protect the struct's own fields, never the memory those fields point at.

---

## 3. Comparability: derived from the fields

Structs are comparable with `==` **if and only if all of their fields are comparable**. When they are, `==` does a field-by-field comparison, recursing into nested structs. This is what lets a comparable struct serve as a map key.

```go
type Coord struct {
	Lat, Lng float64
}

seen := map[Coord]bool{}
seen[Coord{12.97, 77.59}] = true
fmt.Println(seen[Coord{12.97, 77.59}]) // true — struct keys compared by value
```

The pitfall arrives the moment a field's type is *not* comparable. Slices, maps, and functions are not comparable in Go (only against `nil`), so any struct containing one of them is itself uncomparable — and the failure is a **compile error** the instant you try `==` or use it as a map key.

```go
type Record struct {
	ID   int
	Tags []string // slice — not comparable
}

// a, b := Record{}, Record{}
// _ = a == b            // compile error: struct containing []string cannot be compared
// m := map[Record]bool{} // compile error: invalid map key type
```

**The gotcha:** adding a slice, map, or func field to a previously comparable struct silently strips its comparability, and downstream code that used `==` or a `map[T]...` breaks at compile time — sometimes far from the change. If you need value equality on such a type, provide an explicit `Equal` method, or reach for `reflect.DeepEqual` (slower, and it compares unexported fields too). When the type must be a map key, restructure so the key portion is a separate comparable struct.

---

## 4. Embedding: composition with promotion

Embedding is Go's composition mechanism. Declare a field with a type but **no field name** — an *anonymous field* — and its exported fields and methods are *promoted* to the outer struct, callable as if they were declared there.

```go
type Logger struct {
	Prefix string
}

func (l Logger) Logf(format string, args ...any) {
	fmt.Printf(l.Prefix+": "+format+"\n", args...)
}

type Service struct {
	Logger // embedded — no field name
	Name   string
}

s := Service{Logger: Logger{Prefix: "svc"}, Name: "billing"}
s.Logf("started %s", s.Name) // promoted: really s.Logger.Logf(...)
fmt.Println(s.Prefix)        // promoted field access: really s.Logger.Prefix
```

`s.Logf(...)` is pure syntactic sugar for `s.Logger.Logf(...)`. The embedded value still exists as a field named after its type (`s.Logger`), and you can always address it explicitly.

The critical thing to internalize is what promotion is *not*. It is **not inheritance**, and there is **no subtype polymorphism**. A `Service` is not a `Logger`; you cannot pass a `Service` where a `Logger` is expected, and a method on `Logger` that calls another `Logger` method will never dispatch "up" into `Service`. Promotion resolves at compile time against the embedded type's own method set — there is no virtual table, no overriding in the OOP sense. Go composes behavior by *delegation*, and the promotion syntax just spares you writing the forwarding methods by hand.

**The gotcha:** embedding a struct **by value** copies it (Section 2 applies) — mutating methods on the embedded value operate on the outer struct's copy, which is usually what you want. But embedding a type whose methods have pointer receivers means those methods are promoted only when the outer value is addressable; embed `*Logger` (a pointer) instead if you need to share the embedded state or call pointer-receiver methods on non-addressable outer values.

---

## 5. Name collisions and shadowing

Promotion follows a depth rule: a name at a **shallower** depth wins over the same name deeper in the embedding tree. A field or method declared directly on the outer struct shadows anything promoted from an embedded type at the same or greater depth.

```go
type Base struct {
	ID int
}

func (Base) Kind() string { return "base" }

type Widget struct {
	Base
	ID   string // shadows Base.ID
}

w := Widget{Base: Base{ID: 42}, ID: "w-1"}
fmt.Println(w.ID)      // "w-1"  — the outer field wins
fmt.Println(w.Base.ID) // 42     — the embedded field is still reachable
```

When two embedded types sit at the **same depth** and expose the same name, neither is promoted. Accessing the ambiguous name directly is a compile error; you must qualify it.

```go
type A struct{ Name string }
type B struct{ Name string }

type C struct {
	A
	B
}

c := C{}
// _ = c.Name // compile error: ambiguous selector c.Name
c.A.Name = "from A" // must qualify — no promotion of the collided name
```

**The gotcha:** shadowing is silent by design — no warning when an outer field hides a promoted one, which is exactly how you deliberately "override" behavior. But it also means adding a field to an embedded type can silently shadow, or newly collide with, a name the outer type relied on. Same-depth collisions are the safer failure: they refuse to promote and surface as a compile error only *when the ambiguous name is used*, so an unused collision can lurk unnoticed.

---

## 6. Embedding interfaces in structs

You can embed an **interface** in a struct, not just a concrete type. The struct then satisfies that interface by delegating to whatever concrete value is stored in the embedded field — and it does so even if the outer struct implements none of the methods itself.

```go
type Reader interface {
	Read(p []byte) (int, error)
}

type CountingReader struct {
	Reader // embedded interface
	N      int
}

func (c *CountingReader) Read(p []byte) (int, error) {
	n, err := c.Reader.Read(p) // delegate to the wrapped Reader
	c.N += n
	return n, err
}
```

This is the standard decorator pattern: embed the interface, override the one method you care about, and every *other* method of the interface is promoted straight through to the wrapped value. A common variant embeds an interface you only partially implement — the compiler is satisfied that the type has the full method set (they're promoted), and any unimplemented method that actually gets called panics with a nil dereference if the embedded interface is nil.

**The gotcha:** an embedded interface field is `nil` until you assign a concrete value into it. Calling a *promoted* (not overridden) method on a struct whose embedded interface is nil panics at runtime, not compile time — the method set looks complete to the type checker. This is a deliberate, useful trick for test stubs (embed an interface, implement only the methods your test exercises), but ship it to production and the first call to an unimplemented method is a nil-pointer panic.

---

## 7. Struct tags: metadata the stdlib reads via reflection

A struct tag is a **string literal** following a field declaration. Go itself assigns it no meaning — it is opaque metadata that libraries read at runtime via reflection. The conventional format is space-separated `key:"value"` pairs, and by convention the value is a comma-separated list where the first element is the name and the rest are options.

```go
type User struct {
	ID        int       `json:"id"`
	Name      string    `json:"name"`
	Email     string    `json:"email,omitempty"`
	passwordH string    `json:"-"`         // unexported: never marshaled anyway
	Created   time.Time `json:"created_at"`
}
```

When you call `json.Marshal(user)`, `encoding/json` uses reflection to walk the fields and read each `json:"..."` tag: it renames `ID` to `id` in the output, drops `Email` entirely when it's empty (that's `omitempty`), and skips any field tagged `json:"-"`. None of this is compiler magic — it is `encoding/json` interpreting strings at runtime.

You can read tags yourself with the same machinery the standard library uses, which makes concrete that a tag is just a parsed string:

```go
t := reflect.TypeOf(User{})
f, _ := t.FieldByName("Email")
fmt.Println(f.Tag)              // json:"email,omitempty"
fmt.Println(f.Tag.Get("json")) // email,omitempty
```

Because tags are namespaced by key, one field can carry directions for several libraries at once — `json`, a database mapper, and a validator, each reading its own key and ignoring the others:

```go
type Product struct {
	SKU   string  `json:"sku" db:"sku" validate:"required"`
	Price float64 `json:"price" db:"price" validate:"gte=0"`
}
```

**The gotcha:** the tag grammar is enforced only by convention, not the compiler. Use straight double quotes around the value and a single space between pairs — `json:"name" db:"name"`, never a comma between the two keys. `reflect.StructTag.Get` returns an empty string for a malformed or missing key rather than erroring, so a typo like `json;"name"` (semicolon instead of colon) fails **silently**: the field marshals under its Go name and nothing tells you why. `go vet` catches many malformed tags, so run it. And tags only apply to what reflection can reach — an **unexported** field is invisible to `encoding/json` regardless of its tag.

---

## 8. The empty struct: `struct{}`

`struct{}` is a struct with no fields. It occupies **zero bytes** of memory, and every value of the type is identical. That "carries no data" property is precisely its value — it's how you say "I need a type here, but no information."

The canonical use is a **set**. A `map[T]struct{}` stores keys with a value type that costs nothing, communicating "membership only, no payload" more honestly than `map[T]bool`:

```go
seen := make(map[string]struct{})
seen["alpha"] = struct{}{}          // the value literal is struct{}{}
_, ok := seen["alpha"]              // ok == true → member
```

The second major use is a **signal channel**, where only the *timing* of a send matters, never the value carried:

```go
done := make(chan struct{})

go func() {
	// ... work ...
	close(done) // or: done <- struct{}{}
}()

<-done // block until the goroutine signals; the value is irrelevant
```

Closing the channel (rather than sending) is the idiom for broadcasting "done" to many waiters at once, since a closed channel yields the zero value to every receiver immediately.

**The gotcha:** the empty **value literal** is `struct{}{}` — the first braces are the type `struct{}`, the second construct a value of it. It reads oddly the first time. Note the payoff over `map[T]bool`: the set version can't be misused by checking a truthiness that was never meant to carry meaning, and a huge set stores no per-entry value bytes. For channels, prefer `chan struct{}` for pure signals so readers of the code know no data is meant to flow — reserve typed channels for when the value actually matters.

---

## Choosing the right tool

| Situation | Reach for |
|---|---|
| Pass a small value, no mutation needed | Struct by value (copy is cheap and safe) |
| Function must mutate the caller's struct | Pointer receiver / `*T` parameter |
| Struct must be a map key | All fields comparable — no slice/map/func fields |
| Value equality on a type with slice/map fields | An explicit `Equal` method (or `reflect.DeepEqual`) |
| Reuse behavior without rewriting forwarders | Embed the concrete type |
| Wrap/decorate an interface, override one method | Embed the interface, implement the one method |
| Attach library metadata to fields | Struct tags (`json:"..."`, etc.) |
| Set membership, or a pure signal channel | `map[T]struct{}` / `chan struct{}` |

---

## Key takeaways

- **Structs are values, and values are copied.** Assignment, function arguments, and `for range` all copy the whole struct; use pointers to mutate the original. The copy is shallow — slice/map/pointer fields still share their backing memory.
- **Comparability is inherited from the fields.** All fields comparable ⇒ the struct is comparable and usable as a map key. One slice, map, or func field makes the whole struct uncomparable, and `==` becomes a compile error.
- **Embedding is delegation, not inheritance.** Promotion is compile-time sugar for forwarding; there is no subtype polymorphism, and shallower names shadow deeper ones while same-depth collisions refuse to promote.
- **An embedded interface delegates to its stored value** — powerful for decorators and stubs, but a promoted method on a nil embedded interface panics at runtime.
- **Struct tags are just strings** that libraries interpret via reflection. Mind the grammar (quotes, spaces), run `go vet`, and remember unexported fields are invisible to `encoding/json` regardless of tag.
- **`struct{}` is the zero-cost placeholder** — `map[T]struct{}` for sets, `chan struct{}` for signals; the value literal is `struct{}{}`.

---

## Further reading

- *Effective Go* — the "Embedding" section, for the canonical treatment of anonymous fields and method promotion.
- The Go blog, *JSON and Go* — how `encoding/json` reads struct tags, and the `omitempty` / `-` conventions.
- `go doc reflect.StructTag` — the exact tag grammar and the `Get` / `Lookup` methods the standard library uses to parse tags at runtime.
