# Functions, Closures, and Variadics

*How Go treats functions as ordinary values — and what that buys you: the (result, error) idiom, variadic APIs, closures over shared state, and the decorator/middleware/option patterns that fall out of passing functions around.*

---

Most languages let you *call* functions. Go lets you *hold* them — pass them as arguments, return them, stash them in structs and maps, and close over the variables around them. Once a function is just another value, a surprising amount of idiomatic Go stops looking like a special feature and starts looking like the same small rule applied over and over: HTTP middleware, retry wrappers, functional options, the `sort.Slice` comparator, `defer`, `http.HandlerFunc`. This post walks the mechanics an experienced engineer needs in their head — multiple returns, named results, variadics, closures, and the higher-order patterns — with an eye on where Go's semantics bite.

Everything here is standard-library-only Go. Assume Go 1.22 or newer unless noted.

---

## Functions are values

A function type in Go is written by its signature: `func(int, int) int`. Any function or method with that shape is assignable to a variable of that type, storable in a slice, and passable as an argument. There is nothing special about a "top-level" function — it is a value that happens to have a name at package scope.

```go
type binOp func(a, b int) int

func add(a, b int) int { return a + b }
func mul(a, b int) int { return a * b }

func main() {
	ops := map[string]binOp{"add": add, "mul": mul}
	fmt.Println(ops["add"](3, 4)) // 7
	fmt.Println(ops["mul"](3, 4)) // 12
}
```

Two things fall out of this. First, a named function type like `binOp` is worth defining once you pass the shape around more than once — it documents intent and shortens signatures. Second, the zero value of a function type is `nil`, and calling a `nil` function panics.

**The gotcha:** a function-typed struct field or map entry that was never assigned is `nil`, not a no-op. `ops["divide"](3, 4)` panics with "invalid memory address or nil pointer dereference" because the map returns the zero value for a missing key. Guard optional callbacks with `if fn != nil` before calling, and check `map` membership with the comma-ok form when a missing key is legitimate.

---

## Multiple return values and the (result, error) idiom

Go functions return any number of values, and the language leans on this hard: the universal convention is `(result, error)`, with `error` last. The caller inspects the error before trusting the result.

```go
func parsePort(s string) (int, error) {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, fmt.Errorf("parse port %q: %w", s, err)
	}
	if n < 1 || n > 65535 {
		return 0, fmt.Errorf("port %d out of range", n)
	}
	return n, nil
}
```

The contract that makes this work: **when `error` is non-nil, treat every other return value as invalid.** On the failure path above we return `0` for the port, but the caller must not read it — the error is the signal, the zero is just filler. Some functions deliberately return a partially useful result alongside an error (`io.Reader.Read` returns bytes *and* a possible error in the same call), but those are documented exceptions, not the default.

Wrapping with `%w` (as above) preserves the underlying error so callers can `errors.Is` / `errors.As` against it. Use `%v` when you deliberately want to *sever* that chain and not leak an implementation detail.

**The gotcha:** the comma-ok forms — `v, ok := m[k]`, `v, ok := <-ch`, `x, ok := i.(T)` — look like the error idiom but are not it. `ok` is a `bool`, and there is no error to unwrap. Reaching for `err` where the language gives you `ok` (or vice versa) is a common slip; the second value's *type* tells you which protocol you're in.

---

## Named return values — and when they hurt

Go lets you name the return values in the signature. Named results are pre-declared as zero-valued variables you can assign to, and a bare `return` sends their current values back.

Where they genuinely help is in cooperation with `defer` — a deferred closure can read and modify named results *after* the `return` statement has set them but *before* the function actually returns to the caller. This is the standard way to decorate an error or recover from a panic:

```go
func doWork() (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("recovered from panic: %v", r)
		}
	}()
	// ... code that might panic ...
	return nil
}
```

Here `err` must be named — the deferred function has no other way to reach the value the function is about to return. Same trick for wrapping: `defer func() { if err != nil { err = fmt.Errorf("doWork: %w", err) } }()`.

Where named results *hurt* is bare `return` in any function longer than a few lines. A naked `return` forces the reader to scroll up to the signature to learn what is actually being returned, and it makes it easy to return a stale or half-assigned value by accident.

**The gotcha:** a named result is a real variable, so it silently shadows. Write `err := doSomething()` with `:=` inside a function that already has a named `err` result *in a nested block*, and you create a new `err` that never reaches the deferred wrapper — `go vet`'s shadow analysis and tools like `staticcheck` catch some of these, but not all. Prefer named results for the `defer`-decorates-error pattern and short helpers; assign explicitly and avoid naked `return` everywhere else.

---

## Variadic parameters and `slice...` spreading

A trailing `...T` parameter accepts zero or more arguments; inside the function it is a `[]T`.

```go
func sum(nums ...int) int {
	total := 0
	for _, n := range nums {
		total += n
	}
	return total
}

sum()            // 0   — nums is nil (length 0, so range over it is still safe)
sum(1, 2, 3)     // 6
xs := []int{4, 5, 6}
sum(xs...)       // 15  — spread an existing slice
```

`fmt.Printf(format string, args ...any)` is the canonical example: the variadic tail is what lets you pass any number of format arguments. The spread form `sum(xs...)` passes an existing slice without re-listing its elements.

**The gotcha:** `f(xs...)` does **not** copy `xs` — the function receives a slice header pointing at the *same backing array*. If the function reassigns elements (`nums[0] = 99`), the caller's slice sees the change. And you cannot mix the two calling forms: `sum(1, xs...)` is a compile error — it's either individual arguments or a single spread, never both. Also note `append(dst, src...)` is this same spread syntax, and passing `nil...` is legal and yields a `nil` slice inside the callee (length 0, so `range` over it is safe).

---

## Closures: capture by reference

A function literal (an anonymous `func`) captures the variables it references from the enclosing scope — **by reference, not by value.** The closure and the surrounding code share the *same* variable, so mutations flow both ways and the variable outlives the scope that declared it as long as the closure is reachable.

```go
func counter() func() int {
	count := 0
	return func() int {
		count++
		return count
	}
}

c := counter()
fmt.Println(c(), c(), c()) // 1 2 3
```

`count` is a local of `counter`, yet it survives after `counter` returns because the returned closure still references it. Each call to `counter()` produces a fresh, independent `count` — closures capture variables, not values, and each activation has its own.

This is the mechanism behind memoization, lazy initialization, and stateful iterators. It is also the mechanism behind the single most-hit bug in Go's history.

---

## The loop-variable capture trap (and the Go 1.22 fix)

For over a decade, this code did not do what almost everyone expected:

```go
funcs := make([]func(), 0, 3)
for _, v := range []string{"a", "b", "c"} {
	funcs = append(funcs, func() { fmt.Print(v) })
}
for _, f := range funcs {
	f()
}
```

Under Go 1.21 and earlier, the loop variable `v` was **one variable reused across all iterations.** All three closures captured that same `v`, and by the time they ran the loop had finished with `v == "c"` — so the output was `ccc`, not `abc`. The canonical fix was to shadow the variable per iteration: `v := v` inside the loop body, creating a fresh binding for each closure to capture.

**The gotcha:** as of **Go 1.22, the loop variable's scope changed** — `for` loops now create a new instance of the loop variable each iteration, so the snippet above prints `abc` with no `v := v` workaround. This is gated by the `go` directive in `go.mod`: a module declaring `go 1.22`+ gets the new semantics; one declaring `go 1.21` or earlier keeps the old ones even on a newer toolchain — so the *same source* can behave differently depending on `go.mod`. Two takeaways: know which semantics your module is on, and remember the trap still exists for *any* closure over a mutable variable that isn't a loop variable — a `defer func(){ ... }()` over a variable you reassign later, or a goroutine capturing a shared accumulator, will still surprise you.

---

## Passing functions in: strategy and callbacks

Once functions are values, "inject the varying behavior as a function" replaces a lot of interface ceremony. The standard library does this everywhere — `sort.Slice` takes a `less func(i, j int) bool`; `filepath.WalkDir` takes a visitor.

```go
func Map[T, U any](in []T, f func(T) U) []U {
	out := make([]U, len(in))
	for i, v := range in {
		out[i] = f(v)
	}
	return out
}

lengths := Map([]string{"go", "rust"}, func(s string) int { return len(s) })
// []int{2, 4}
```

The callback is the extension point: `Map` knows nothing about `int` or `string`, only that some `f` turns a `T` into a `U`. This is Go's answer to a lot of what other languages reach for inheritance to do.

---

## Returning functions: decorators, middleware, and options

Returning a function is how you build behavior that wraps other behavior. Three patterns dominate real Go code.

**Decorators** wrap a function in cross-cutting behavior. A retry wrapper takes a function and returns one with the same signature:

```go
func withRetry(attempts int, fn func() error) func() error {
	return func() error {
		var err error
		for i := 0; i < attempts; i++ {
			if err = fn(); err == nil {
				return nil
			}
		}
		return fmt.Errorf("after %d attempts: %w", attempts, err)
	}
}
```

**Middleware** is the same idea applied to HTTP handlers. Because `http.HandlerFunc` is a function type, a middleware is "a function that takes a handler and returns a handler":

```go
func logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s took %s", r.Method, r.URL.Path, time.Since(start))
	})
}
// wrap: handler = logging(auth(mux))
```

**Functional options** solve the "constructor with many optional settings" problem without a giant config struct or a dozen `NewXxx` variants. Each option is a closure that mutates the thing being built:

```go
type Server struct {
	port    int
	timeout time.Duration
}

type Option func(*Server)

func WithPort(p int) Option        { return func(s *Server) { s.port = p } }
func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }

func NewServer(opts ...Option) *Server {
	s := &Server{port: 8080, timeout: 30 * time.Second} // defaults
	for _, opt := range opts {
		opt(s)
	}
	return s
}

srv := NewServer(WithPort(9000), WithTimeout(5*time.Second))
```

Note how this braids together three things from this post: variadic parameters (`opts ...Option`), functions as values (`Option` is a function type), and closures (`WithPort` closes over `p`). The pattern is verbose to define but reads beautifully at the call site, defaults are explicit, and adding a new option never breaks an existing caller.

**The gotcha:** decorators and middleware compose by **nesting**, and the order is easy to get backwards. `logging(auth(mux))` runs *logging's* pre-work first, then *auth's*, then the mux — because `logging` is the outermost wrapper. If you build the chain in a loop, decide deliberately whether you're wrapping outermost-first or innermost-first; reversing the slice is often what you actually want.

---

## Method values vs method expressions

Methods can become function values two ways, and the distinction is worth knowing precisely.

A **method value** binds the receiver *now* and gives you a function that no longer takes a receiver:

```go
var buf bytes.Buffer
write := buf.WriteString          // method value: receiver &buf is captured
write("hello")                    // func(string) (int, error)
```

A **method expression** leaves the receiver unbound — it becomes an explicit first parameter:

```go
write := (*bytes.Buffer).WriteString // method expression
write(&buf, "hello")                 // func(*bytes.Buffer, string) (int, error)
```

The method value is the everyday one: `buf.WriteString` captures `buf` and is exactly the kind of value you'd pass as a callback. The method expression is rarer but useful when you want to apply the same method across many receivers (e.g. as the `f` argument to a `Map`-style helper).

**The gotcha:** a method value on a *value receiver* snapshots the receiver at the moment you take it. `t := time.Now(); f := t.Add; ...; t = time.Now()` — `f` still adds to the *old* `t`, because value-receiver method values copy the receiver when bound. If you need the binding to track later mutations, use a pointer receiver (or a pointer to the value).

---

## Key takeaways

- **A function is a value.** That single fact underpins callbacks, middleware, functional options, `defer`, and the standard library's higher-order helpers — learn to see them as one pattern.
- **`(result, error)` is a convention, not a language feature.** When `error != nil`, the other results are filler. Don't confuse it with the comma-`ok` forms, which speak a different protocol.
- **Name return values for the `defer`-decorates-error pattern**, not as a default; avoid naked `return` in anything but the shortest helpers.
- **Variadics spread without copying** — `f(xs...)` shares the backing array, and you can't mix spread with individual args.
- **Closures capture by reference.** Go 1.22 fixed the loop-variable trap at the language level (gated by your `go.mod` version), but any closure over a variable you later reassign is still a hazard.
- **Method values bind the receiver eagerly** — value receivers snapshot, pointer receivers track.

---

## Further reading

- [Effective Go](https://go.dev/doc/effective_go) — the "Functions" and "Defer" sections, and the multiple-return-value discussion.
- [The Go Blog: "Fixing For Loops in Go 1.22"](https://go.dev/blog/loopvar-preview) — the loop-variable scoping change and why it was safe to make.
- [Dave Cheney: "Functional options for friendly APIs"](https://dave.cheney.net/2014/10/17/functional-options-for-friendly-apis) — Dave Cheney's write-up of the options pattern.
- [The Go Blog: "Error handling and Go"](https://go.dev/blog/error-handling-and-go) — the `(result, error)` idiom and wrapping with `%w`.
