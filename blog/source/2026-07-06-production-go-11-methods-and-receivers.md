# Methods and Receivers

*How Go attaches behavior to types without classes — the receiver, the value-versus-pointer decision, method sets and what they mean for interfaces, and the addressability rules that trip people up when a value lives in a map.*

---

Go has no classes. It has *methods*, and a method is nothing more than a function with an extra parameter written in a special place — the **receiver** — before the function name. That one syntactic move is the whole object model. Behavior attaches to a type not by living inside a class body but by naming that type in a receiver. Once you internalize that a method *is* a function and the receiver *is* just its first argument, most of Go's quirks around value versus pointer, method sets, and addressability stop being surprises and start being consequences.

This post is about those consequences. It assumes you've written Go for years and know the syntax; the goal is to make the rules feel inevitable rather than memorized.

---

## A method is a function with a receiver

Here is a method and the free function it is equivalent to:

```go
type Celsius float64

// Method: receiver (c) sits before the name.
func (c Celsius) Fahrenheit() Celsius {
	return c*9/5 + 32
}

// The same logic as an ordinary function.
func fahrenheit(c Celsius) Celsius {
	return c*9/5 + 32
}
```

`Celsius(100).Fahrenheit()` and `fahrenheit(100)` compute the same thing. The receiver is a parameter that happens to be written on the left of the method name so the call can be written with dot notation. That framing matters because it explains why the receiver obeys the same value-copy semantics as any other parameter: a value receiver gets a *copy* of the argument, exactly as `fahrenheit` would.

Note also `Celsius` is not a struct. It's a defined type whose underlying type is `float64`. Which brings us to the first thing most people under-use.

---

## You can define methods on any type you own

Methods are not a struct feature. You can attach a method to **any named (defined) type whose definition lives in your package** — a named slice, a named map, a named function type, a named integer. The only rule is that the receiver's base type must be defined in the same package (so you cannot bolt methods onto `int` or onto `time.Time`, but you can define your own type over them).

```go
// Named slice type with methods.
type IntSet []int

func (s IntSet) Contains(x int) bool {
	for _, v := range s {
		if v == x {
			return true
		}
	}
	return false
}

// Named function type with a method — surprisingly useful.
type HandlerFunc func(msg string) error

func (f HandlerFunc) Retry(n int, msg string) error {
	var err error
	for i := 0; i < n; i++ {
		if err = f(msg); err == nil {
			return nil
		}
	}
	return err
}
```

The named-function-type pattern is the mechanism behind `http.HandlerFunc`: it lets a plain function satisfy an interface by giving the function type a method. If you've ever wondered how a bare function becomes an `http.Handler`, that's it — a one-method function type doing an adapter's job.

**The gotcha:** you can only define methods on types declared in *your* package. `func (t time.Time) Foo()` won't compile, and neither will a method on a bare `[]int`. When you want to extend a foreign type, define your own named type over it (`type Timestamps []time.Time`) and hang the methods there.

---

## Value receivers versus pointer receivers

This is the decision you make on every method, so it's worth having a firm rule rather than a coin flip.

A **value receiver** operates on a copy. Mutations to the receiver are discarded when the method returns. A **pointer receiver** operates on the original through a pointer, so mutations stick — and no copy of the underlying value is made on the call.

```go
type Counter struct {
	n int
}

// Value receiver: mutates a copy — the caller sees nothing.
func (c Counter) IncBroken() {
	c.n++ // lost when the method returns
}

// Pointer receiver: mutates the original.
func (c *Counter) Inc() {
	c.n++
}
```

Three questions decide it, in order:

1. **Does the method need to mutate the receiver?** If yes, it must be a pointer receiver — a value receiver can't. This is the dominant reason.
2. **Is the struct large, or does copying it have a cost you care about?** A pointer receiver avoids copying the value on every call. For a small struct (a few words) the copy is free and irrelevant; for a big one, or one on a hot path, the pointer saves work.
3. **Consistency.** If any method of the type needs a pointer receiver, prefer giving *all* of them pointer receivers, so the type presents one coherent method set. Mixing value and pointer receivers on the same type is a smell that causes real confusion (and, as we'll see, subtle method-set differences).

There are secondary signals. Types that wrap something you must not copy — a `sync.Mutex`, a `sync.WaitGroup`, anything embedding one — must use pointer receivers, because copying the value copies the lock. Conversely, small immutable value types (a `time.Time`, a 2D point, our `Celsius`) read naturally with value receivers and are safe to pass around.

**The gotcha:** "value receiver = no mutation" is not merely a convention; the compiler enforces it. But it's easy to *think* you mutated something. `IncBroken` above compiles cleanly and does nothing — the copy is incremented and thrown away. There's no warning. If a mutating method isn't sticking, check the receiver is a pointer first.

---

## Pick one receiver kind per type

The advice to be consistent deserves its own emphasis because it's the most common review comment on Go types. Don't write this:

```go
type Account struct {
	balance int
}

func (a Account) Balance() int      { return a.balance }  // value
func (a *Account) Deposit(n int)    { a.balance += n }    // pointer
```

It compiles, and for a variable it even works, because Go auto-takes the address (next section). But the type now has a *split personality* in method-set terms, and the moment an `Account` value flows through something non-addressable — a map entry, an interface — the two halves behave differently. Choose pointer receivers for `Account` (it has mutating methods) and make `Balance` a pointer receiver too, even though it doesn't mutate. Uniformity buys you a predictable method set.

---

## Automatic address-of and dereference

Go quietly inserts a `&` or a `*` so you rarely write them at a call site. If you have a value and call a pointer-receiver method, Go takes its address; if you have a pointer and call a value-receiver method, Go dereferences it.

```go
c := Counter{}
c.Inc()   // c is addressable → Go rewrites this as (&c).Inc()
fmt.Println(c.n) // 1

p := &Counter{}
p.Inc()   // already a pointer, called directly
_ = p.n

// Value-receiver method through a pointer:
cel := &Celsius{} // silly but legal
_ = cel.Fahrenheit() // Go rewrites as (*cel).Fahrenheit()
```

The load-bearing word is **addressable**. Go can only take the address of something that has a home in memory it can point at — a local variable, a struct field of an addressable struct, a slice element, a dereferenced pointer. It *cannot* take the address of a value that has no such home, and that's where the real trap lives.

**The gotcha:** a value stored in a **map**, or a value **returned directly from a function call**, is *not addressable*. You therefore cannot call a pointer-receiver method on it, and the compiler rejects it:

```go
type Player struct {
	Score int
}

func (p *Player) Bump() { p.Score++ }

func main() {
	players := map[string]Player{"alice": {Score: 10}}

	// players["alice"].Bump()      // compile error:
	// cannot call pointer method Bump on players["alice"]
	// cannot take the address of players["alice"]

	// The fix: pull it out, mutate, put it back.
	p := players["alice"]
	p.Bump()
	players["alice"] = p

	// Or store pointers in the map so the element IS a pointer:
	ptrs := map[string]*Player{"alice": {Score: 10}}
	ptrs["alice"].Bump() // fine — no address-of needed
}
```

The same non-addressability applies to `someFunc().Bump()` when `someFunc` returns a `Player` by value. Slice elements are the happy exception — `xs[i].Bump()` works because a slice element *is* addressable. When a type has pointer-receiver methods and you plan to keep it in a map, store `*Player`, not `Player`, and the whole class of error disappears.

---

## Method sets: T versus *T

Every type has a **method set** — the set of methods you can call on it *through the machinery that only knows the static type*, which in practice means through an interface. The rule:

- The method set of **`T`** (value) contains only the methods with **value receivers**.
- The method set of **`*T`** (pointer) contains **both** value-receiver and pointer-receiver methods.

That asymmetry is the single most important fact about receivers, because it decides interface satisfaction.

```go
type Stringer interface {
	String() string
}

type Named struct{ name string }

// Pointer receiver.
func (n *Named) String() string { return n.name }

func main() {
	var s Stringer

	s = &Named{"ok"}   // *Named has String() in its method set ✓
	// s = Named{"no"}  // compile error: Named does NOT satisfy Stringer,
	//                   // String has a pointer receiver, so it's only
	//                   // in the method set of *Named.
	_ = s
}
```

Because `String` has a pointer receiver, only `*Named` satisfies `Stringer`. A plain `Named` value does not. If you'd written `func (n Named) String()` instead, *both* `Named` and `*Named` would satisfy it — the value-receiver method is in both method sets.

Why the asymmetry? It comes straight from addressability. To call a pointer-receiver method on a value, Go needs the value's address. When the value sits behind an interface, there *is* no addressable home to take — the interface holds a copy — so the language simply excludes pointer-receiver methods from `T`'s method set. Consistent with the map rule above; it's the same principle wearing a different hat.

The practical guidance falls out of this: this is another reason to keep receivers consistent, and, if you satisfy interfaces, to remember that pointer-receiver methods mean you must pass a pointer where the interface is expected. (The interfaces post goes deeper on satisfaction, embedding, and the empty interface; this is the receiver-side half of that story.)

| Receiver of method `M` | In method set of `T`? | In method set of `*T`? |
|---|---|---|
| Value: `func (t T) M()` | Yes | Yes |
| Pointer: `func (t *T) M()` | No | Yes |

---

## Nil receivers are valid

A method call is a function call, and passing `nil` as the receiver argument is not itself an error. A pointer-receiver method runs fine on a `nil` receiver *as long as the body doesn't dereference the nil pointer*. This is not a curiosity — it's a genuine design tool, especially for recursive data structures.

```go
type List struct {
	val  int
	next *List
}

// Works even when called on a nil *List.
func (l *List) Sum() int {
	if l == nil {
		return 0 // base case: the empty list
	}
	return l.val + l.next.Sum() // recursion bottoms out on nil
}

func main() {
	var l *List // nil
	fmt.Println(l.Sum()) // 0 — no panic
}
```

`l.next.Sum()` eventually calls `Sum` with a nil receiver, and the `l == nil` guard handles it instead of panicking. The empty tree, the empty list, the absent node — modeling these as a typed nil receiver lets you skip a separate "empty" sentinel type. The standard library uses the pattern; a nil `*html.Node` or a nil method-holding config can answer sensibly.

**The gotcha:** a nil receiver of an interface type is subtly different from a nil concrete pointer. An interface holding a `(*T)(nil)` is itself **non-nil** — it has a type but a nil value — so `iface == nil` is `false` even though the underlying pointer is nil. That mismatch is the classic "why is my error not nil" bug: returning a nil `*MyError` as an `error` yields a non-nil `error` interface. Nil *concrete* receivers are safe if the method guards them; nil *interfaces* are a separate hazard covered with interfaces.

---

## Method values and method expressions

Because a method is a function, you can grab it as a first-class value in two flavors.

A **method value** binds the receiver now and hands you a function that no longer takes one:

```go
c := Counter{n: 5}
inc := c.Inc     // receiver c bound here (its address, since Inc is *Counter)
inc()            // calls c.Inc()
```

A **method expression** leaves the receiver unbound — you get a plain function whose *first parameter* is the receiver:

```go
inc := (*Counter).Inc // func(*Counter)
c := Counter{}
inc(&c)               // pass the receiver explicitly
```

Method values are what you pass to `time.AfterFunc(d, obj.Cleanup)` or a goroutine — the receiver rides along. Method expressions are handy when you want to treat "the `Inc` method of all `Counter`s" as one function over receivers. Both are just the "method = function with a receiver" identity made concrete: a method value pre-applies the first argument; a method expression leaves it as an ordinary parameter. (The functions post covers closures and first-class functions in full; these two forms are the receiver-flavored corner of that topic.)

---

## Key takeaways

- **A method is a function with a receiver parameter.** Every rule below is a consequence of that, plus the copy semantics of ordinary parameters.
- **Methods attach to any defined type you own** — named slices, maps, and function types included, not just structs. Named function types are how a bare function satisfies an interface.
- **Choose pointer receivers to mutate, to avoid copying large or uncopyable values, and for consistency.** Pick one receiver kind per type and stick to it.
- **Method sets drive interface satisfaction:** `*T` has all methods, `T` has only the value-receiver ones. A type with pointer-receiver methods satisfies an interface only through a pointer.
- **Go auto-takes addresses for method calls on addressable values** — but map entries and function return values aren't addressable, so you can't call pointer-receiver methods on them directly. Store pointers in maps to sidestep it.
- **Nil concrete receivers are valid and useful** when the method guards them; a nil pointer inside an interface is a different, non-nil beast.

---

## Further reading

- [Effective Go — Methods, and Pointers vs. Values](https://go.dev/doc/effective_go#methods) — the canonical treatment of when to use a pointer receiver.
- [The Go Programming Language Specification — Method sets](https://go.dev/ref/spec#Method_sets) — the precise rules for what `T` and `*T` contain and how they govern interface satisfaction.
