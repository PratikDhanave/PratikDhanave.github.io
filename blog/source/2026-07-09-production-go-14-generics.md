# Generics: Type Parameters and Constraints

*How type parameters and constraints actually work in Go 1.18+ — writing functions and data structures that are type-safe across many types, when the compiler can infer type arguments for you, and the harder question of when a plain interface is still the better tool.*

---

For most of its life Go asked you to choose between two uncomfortable options when you wanted code to work across many types: write the same function once per type, or reach for `interface{}` and pay for it with runtime type assertions and lost compile-time safety. Generics, added in Go 1.18, give you a third option — parameterize code over types the way you already parameterize it over values. You write `Map` or `Stack` once, the compiler checks it once, and callers get a fully typed result with no assertions and no `reflect`.

This post is the foundation for everything generic in Go: how you declare type parameters on functions and types, how *constraints* describe what those types are allowed to do, when the compiler can infer the type arguments so you never type them, and — the part experience teaches — when generics are genuinely the right tool versus when an interface says what you mean more plainly. A later post picks up the sequel questions (iterators over generic containers, and the discipline of using generics sparingly); here we build the base.

---

## Type parameters on functions

A generic function carries an extra bracketed list *before* its ordinary parameter list. Each entry names a type parameter and gives it a *constraint* — the set of types that entry is allowed to be. The canonical starter is `Map`, which turns a `[]T` into a `[]U` by applying a function:

```go
func Map[T, U any](s []T, f func(T) U) []U {
	out := make([]U, len(s))
	for i, v := range s {
		out[i] = f(v)
	}
	return out
}
```

`[T, U any]` declares two type parameters, both constrained by `any` — meaning "any type at all, no operations assumed." Inside the body, `T` and `U` behave like real types: you can declare variables of them, form slices of them, pass them around. What you *cannot* do is anything `any` doesn't promise — no `+`, no `<`, no field access — because the constraint is the only contract the compiler will let the body rely on.

Callers use it like any other function:

```go
nums := []int{1, 2, 3}
strs := Map(nums, func(n int) string { return strconv.Itoa(n) })
// strs is []string{"1", "2", "3"}
```

Notice there are no `[int, string]` brackets at the call site. That is type inference, which we come back to shortly.

---

## Type parameters on types

Types take type parameters too, and this is where generics pay off most clearly — homogeneous containers that were previously either copy-pasted per element type or smeared into `[]interface{}`. A generic stack:

```go
type Stack[T any] struct {
	items []T
}

func (s *Stack[T]) Push(v T) {
	s.items = append(s.items, v)
}

func (s *Stack[T]) Pop() (T, bool) {
	var zero T
	if len(s.items) == 0 {
		return zero, false
	}
	v := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return v, true
}
```

Two details worth internalizing. First, the receiver repeats the type parameter: `(s *Stack[T])`, not `(s *Stack)`. The method is defined on the *generic* type and `T` has to be back in scope. Second, `var zero T` is the idiom for "the zero value of whatever `T` is" — you cannot write `nil` or `0`, because you don't know which is meaningful. `var zero T` gives you the right zero (`0`, `""`, `nil`, an empty struct) for free.

A caller instantiates the type by supplying the argument:

```go
var s Stack[int]
s.Push(10)
s.Push(20)
top, ok := s.Pop() // top == 20, ok == true
```

`Stack[int]` and `Stack[string]` are distinct types, each fully checked. There is no boxing and no assertion when you `Pop`.

---

## Constraints: from `any` to real contracts

A constraint is *an interface used as a type set*. That reframing is the single most useful idea in Go generics. An ordinary interface lists methods; a constraint interface lists methods **and/or** a set of permitted types, and the type parameter must be a member of that set.

`any` is the widest constraint — it is literally an alias for `interface{}`, the empty type set of "everything." At the other end, `comparable` is a built-in constraint for types that support `==` and `!=`. You need it the moment a type parameter becomes a map key:

```go
func Unique[T comparable](s []T) []T {
	seen := make(map[T]struct{}, len(s))
	out := s[:0]
	for _, v := range s {
		if _, ok := seen[v]; ok {
			continue
		}
		seen[v] = struct{}{}
		out = append(out, v)
	}
	return out
}
```

Try that with `[T any]` and the compiler rejects `map[T]struct{}` and `seen[v]`, because `any` makes no promise that `T` can be compared. `comparable` is exactly the promise `map` keys require.

For method-based contracts, an ordinary interface *is* a constraint. If a function needs its type to stringify itself, constrain by an interface with that method:

```go
type Stringer interface {
	String() string
}

func Join[T Stringer](items []T, sep string) string {
	parts := make([]string, len(items))
	for i, it := range items {
		parts[i] = it.String()
	}
	return strings.Join(parts, sep)
}
```

**The gotcha:** `[T Stringer]` and taking a plain `[]Stringer` argument are *not* interchangeable. The generic form keeps `T` a single concrete type — every element is the same type, stored without boxing, and the return can be typed in terms of `T`. The `[]Stringer` form accepts a mixed slice of different `Stringer` implementations, each boxed. If you want homogeneity and no boxing, use the type parameter; if you genuinely want a heterogeneous collection, use the interface slice. They solve different problems that happen to look alike.

---

## Union elements and the `~` approximation

Method sets can't express "any type you can add with `+`" — that's an operator, not a method. Constraints solve this with *union elements*: a constraint interface can list concrete types separated by `|`, and the type parameter must be one of them (and may only use operations all listed types support).

```go
type Number interface {
	int | int64 | float64
}

func Sum[T Number](s []T) T {
	var total T
	for _, v := range s {
		total += v
	}
	return total
}
```

Because every type in the union supports `+`, the body may use `+`. `Sum([]int{...})` and `Sum([]float64{...})` both compile; `Sum([]string{...})` does not.

There's a subtlety that bites everyone once. A union of concrete types matches those types *exactly*. If a caller has a named type whose underlying type is `int` —

```go
type Celsius int
```

— then `Celsius` is **not** `int`, so `Sum([]Celsius{...})` would fail against the constraint above. The fix is the `~` token, the *underlying-type approximation*. Writing `~int` means "any type whose underlying type is `int`," which includes `int` itself and every named type built on it:

```go
type Number interface {
	~int | ~int64 | ~float64
}
```

**The gotcha:** default to `~` in numeric and ordered constraints. Without it, your library silently rejects perfectly reasonable caller-defined types like `Celsius`, `UserID`, or `Priority`, and the caller gets a baffling "does not satisfy" error for a type that is obviously an integer. The exceptions are constraints where you deliberately want to exclude derived types — rare — and unions of interface types, where `~` isn't permitted.

You rarely have to hand-write these. The standard library ships `cmp.Ordered` (Go 1.21+) for the `<`/`>`-capable types, and `golang.org/x/exp/constraints` provides `Ordered`, `Integer`, `Float`, `Signed`, `Unsigned`, and `Complex`. Prefer them over rolling your own:

```go
import "golang.org/x/exp/constraints"

func Max[T constraints.Ordered](a, b T) T {
	if a > b {
		return a
	}
	return b
}
```

---

## Type inference: when you can drop the brackets

You *can* always spell out type arguments — `Map[int, string](nums, f)` — but you almost never need to, because the compiler infers them from the ordinary arguments. In the `Map` call earlier, `nums` is `[]int` so `T = int`, and the function literal returns `string` so `U = string`. Both are pinned before you reach the body.

Inference works from function arguments, not return values. That's why it usually succeeds for `Map`, `Sum`, and `Filter` — the element type is present in the arguments — and why it *can't* help when a type parameter appears only in the result. A parser that produces a `T` out of a string has nothing to infer from:

```go
func Parse[T any](s string) (T, error) { /* ... */ }

v, err := Parse[int]("42") // explicit [int] is required
```

**The gotcha:** inference flows from arguments only. If a type parameter shows up nowhere in the parameter list, you must supply it explicitly at the call site, and no amount of context on the left-hand side of `:=` will rescue you — Go does not infer from assignment targets. When you find yourself always writing the brackets, that's the signal.

---

## Methods cannot introduce type parameters

One rule surprises people arriving from other languages: **a method may use the type parameters of its receiver, but it cannot declare new ones of its own.** This is legal, because `T` comes from the type:

```go
func (s *Stack[T]) Push(v T) { s.items = append(s.items, v) }
```

This is **not** legal — a method trying to add its own parameter:

```go
// func (s *Stack[T]) MapTo[U any](f func(T) U) *Stack[U] { ... } // compile error
```

The reason is depth of implementation: allowing per-method type parameters would demand a much heavier dispatch mechanism. The practical workaround is to make it a *package-level function* that takes the generic type as an argument, which is exactly why the standard library exposes `Map` as a free function rather than a method:

```go
func MapStack[T, U any](s *Stack[T], f func(T) U) *Stack[U] {
	out := &Stack[U]{}
	for _, v := range s.items {
		out.Push(f(v))
	}
	return out
}
```

Keep transformations that change the element type as functions; keep operations that preserve it as methods.

---

## When generics help — and when an interface is better

Generics are not a general replacement for interfaces. They pull their weight in two situations, and are the wrong reach in a third.

Reach for generics when you're building a **container** — a stack, set, ring buffer, ordered map — where all elements are the same type and you want that type preserved end to end without boxing or assertions. And reach for them for **algorithms over a type set** — `Max`, `Sum`, `Sort`, `Filter`, `Keys` — where the operation is identical across many types and the only thing varying is the element type. In both cases the alternative was copy-paste or `interface{}`, and generics strictly improve on both.

Prefer an **interface** when the abstraction is behavioral — when callers supply *different implementations of the same behavior* and you don't care about their concrete types. An `io.Writer`, a `http.Handler`, a repository you mock in tests: these describe what a value *does*, and a value satisfying them can be swapped at runtime. Generics can't model "any of these unrelated implementations" the way a method-set interface does, and forcing it produces constraints nobody can read.

| Situation | Reach for | Why |
|---|---|---|
| Same-typed collection, no boxing | Generic type | Element type preserved end to end |
| One algorithm over many element types | Generic function | Replaces copy-paste / `interface{}` |
| Swappable implementations of a behavior | Interface | Runtime polymorphism, concrete types don't matter |
| Heterogeneous collection | Interface slice | Mixed concrete types, boxing is the point |
| Type param used in only one function | Generic function | The scope of the abstraction is that small |

**The gotcha:** if a type parameter is used by exactly one function and never constrains a relationship *between* parameters or results, you probably wanted an interface parameter, not generics — it reads more plainly and compiles faster. The strongest signal that generics are right is a type parameter that ties several places together: input element, output element, and return type all moving as one. The clearest signal you've overreached is a constraint so elaborate it takes a paragraph to explain what it admits. That "use generics sparingly" instinct — and the iterators that make generic containers pleasant to range over — is the subject of a later post; the foundation is knowing the mechanics well enough to feel where they stop paying off.

---

## Key takeaways

- **Type parameters go in brackets before the arguments** — on functions (`func Map[T, U any]`) and on types (`type Stack[T any]`), with the receiver repeating the parameter (`(s *Stack[T])`).
- **A constraint is an interface used as a type set.** `any` promises nothing, `comparable` promises `==`, a method interface promises methods, and a union (`~int | ~float64`) promises the operations shared by its members.
- **Use `~` for underlying types.** `~int` admits named types like `Celsius`; plain `int` rejects them. Prefer `cmp.Ordered` and `golang.org/x/exp/constraints` over hand-rolled numeric constraints.
- **Inference flows from arguments, not results or assignment targets.** Omit the brackets when the type shows up in the arguments; spell them out when it only shows up in the return.
- **Methods can't add type parameters** — lift element-changing transforms into package-level functions.
- **Generics for containers and type-set algorithms; interfaces for swappable behavior.** When a type parameter serves one function and ties nothing together, an interface usually says it better.

---

## Further reading

- [An Introduction to Generics](https://go.dev/blog/intro-generics) — the Go blog's walkthrough of type parameters and constraints from the language team.
- [The Go Programming Language Specification: Type parameters](https://go.dev/ref/spec#Type_parameter_declarations) — the normative rules for declarations, constraints, type sets, and inference.
