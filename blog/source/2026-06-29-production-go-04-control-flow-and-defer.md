# Control Flow and defer

*Go's control flow is deliberately small — one loop keyword, a switch that doesn't fall through, an `if` that can scope its own variable — and then there's `defer`, the one construct that repays close reading. A tour of the whole surface, with the sharp edges labelled.*

---

Coming from most languages, Go's control flow feels almost aggressively plain. There is exactly one loop keyword. `switch` refuses to fall through unless you beg it. There is no ternary, no `while`, no `do/while`, no comprehensions. That minimalism is a feature: it means there is very little to memorise and very little to argue about in review. The interesting depth is concentrated in two places — the way `if` and `switch` can bind and scope a variable, and the semantics of `defer`, which are subtle enough that even experienced engineers get burned by them. This is a tour of the whole surface, aimed at the details that actually cost you in production.

---

## `if` with an init statement, and the scope that comes with it

An `if` can run a short statement before its condition. The variables it declares are scoped to the `if` — including its `else` branches — and nowhere else. This is the canonical way to handle the "call, check error, use result" shape without leaking a variable into the surrounding function.

```go
func loadConfig(path string) (Config, error) {
    if data, err := os.ReadFile(path); err != nil {
        return Config{}, fmt.Errorf("read config: %w", err)
    } else {
        return parse(data)
    }
    // data and err do not exist here.
}
```

Most Go engineers avoid the `else` and let the error path return, which keeps the happy path un-indented:

```go
data, err := os.ReadFile(path)
if err != nil {
    return Config{}, fmt.Errorf("read config: %w", err)
}
return parse(data) // data stays in scope for the rest of the function
```

Notice the trade-off. The init-statement form scopes `data` tightly to the branch; the flat form keeps it alive for the whole function. Reach for the init form when the value genuinely only matters inside the conditional — a lookup guard is the classic case:

```go
if user, ok := cache.Get(id); ok {
    return user, nil
}
// fall through to the slow path; user and ok are gone
```

**The gotcha:** the init statement uses `:=`, so it *shadows* any outer variable of the same name. Write `if err := doThing(); err != nil { ... }` inside a function that already has an `err`, and you have created a second `err` that vanishes at the closing brace. If a later line expects the outer `err` to have been set, it won't be. `go vet`'s shadow analysis and most linters flag this, but it's an easy way to silently drop an error.

---

## `for` is the only loop, in four dresses

Go collapses every loop into one keyword. There are four shapes, and they are all just `for` with different pieces present or absent.

The C-style three-clause form, when you genuinely need an index:

```go
for i := 0; i < len(items); i++ {
    process(i, items[i])
}
```

The condition-only form — this is Go's `while`:

```go
for scanner.Scan() {
    handleLine(scanner.Text())
}
```

The bare infinite loop, which you exit with `break`, `return`, or a channel receive. This is the backbone of most long-lived workers:

```go
for {
    select {
    case job := <-queue:
        handle(job)
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

And `range`, which iterates over slices, arrays, maps, strings, channels, and (since Go 1.22/1.23) integers and iterator functions:

```go
for i, item := range items {
    _ = i
    process(item)
}
```

`range` has enough depth of its own — copy semantics of the loop value, rune-vs-byte iteration over strings, the per-iteration variable change in Go 1.22, and range-over-func iterators — that it gets its own treatment later in this series. For now the point is structural: there is one loop, and everything else is sugar you already know under a different name.

**The gotcha:** in the C-style form the condition is re-evaluated every iteration, so `for i := 0; i < len(s); i++` calls `len(s)` each pass. That's free for a slice (length is a cheap field read), but if your condition calls something expensive — a function, a lock-guarded accessor — hoist it into a local before the loop. And a `for` with no condition and no `break`/`return` is an infinite loop; the compiler won't save you, but it will happily let a goroutine spin a core forever.

---

## `switch`: no implicit fallthrough, and the tagless form

Go's `switch` inverts C's default. Cases do **not** fall through — each case ends implicitly with a `break`, so you never write one. This kills an entire category of bug (the forgotten `break`) at the cost of one keyword when you actually want fall-through.

```go
switch status {
case "pending", "queued":       // a case can list several values
    return retryLater()
case "done":
    return finalize()
default:
    return fmt.Errorf("unknown status %q", status)
}
```

When you do want C-style continuation into the next case, ask for it explicitly with `fallthrough`. It is rare and worth a comment, because it transfers control to the next case *unconditionally* — it does not re-test that case's expression:

```go
switch tier {
case "enterprise":
    enableAudit()
    fallthrough      // enterprise also gets everything below
case "pro":
    enablePriority()
default:
    enableBasic()
}
```

The most idiomatic use of `switch` in Go is the **tagless** form — `switch` with no expression, which is just a clean chain of `if/else if`. Each case is a boolean condition, evaluated top to bottom:

```go
switch {
case n < 0:
    return "negative"
case n == 0:
    return "zero"
case n < 10:
    return "small"
default:
    return "large"
}
```

This reads far better than a ladder of `else if` and is the preferred shape whenever you have three or more branches. `switch` also takes an init statement, exactly like `if`: `switch x := compute(); { ... }`.

There is one more form — the **type switch** — which branches on the dynamic type of an interface value (`switch v := x.(type)`). It's the tool for handling a small closed set of concrete types behind an interface, and because it leans on interfaces and type assertions it belongs with that discussion later in the series. Just know the syntax exists and that it reuses the same `switch` you already understand.

**The gotcha:** because Go has no implicit fall-through, a `switch` on an enum-like value silently does nothing for cases you forgot to list — control just falls off the end. There's no compiler exhaustiveness check for a plain `switch`. If a value having no matching case is a bug, add a `default` that panics or returns an error, rather than letting it slip through as a no-op. (The `exhaustive` linter can enforce this for typed constants.)

---

## `break`, `continue`, labels, and the honest case for `goto`

Inside loops, `break` and `continue` do the obvious thing — but only for the *innermost* loop. When you're nested, or when a `select` sits inside a `for`, a bare `break` breaks the wrong thing. That's what **labels** are for:

```go
outer:
    for _, row := range grid {
        for _, cell := range row {
            if cell == target {
                found = true
                break outer   // leaves both loops, not just the inner one
            }
        }
    }
```

A subtle trap worth internalising: inside a `for { select { ... } }`, a `break` in a `select` case breaks the `select`, not the loop. To leave the loop you need a labelled `break` (or a `return`):

```go
loop:
    for {
        select {
        case <-tick.C:
            work()
        case <-ctx.Done():
            break loop   // a bare break here would only exit the select
        }
    }
```

`continue label` works the same way, jumping to the next iteration of the labelled loop.

Then there's `goto`, which Go keeps but almost nobody reaches for. It can only jump within a function and cannot jump over a variable declaration into that variable's scope, which defuses its worst historical abuses. The honest case for it is narrow: generated code, or a hand-written state machine where the alternatives are worse. Cleanup-on-error chains — the one place C programmers reach for `goto` — are better served by `defer` in Go, so that use effectively disappears. Treat `goto` as a tool you recognise in someone else's parser or codegen output, not one you introduce into ordinary business logic.

---

## `defer`: the construct that repays close reading

`defer` schedules a function call to run when the *surrounding function* returns — whether it returns normally, hits an error path, or panics. It's Go's answer to "make sure this cleanup happens no matter how we leave." The mechanics are simple to state and easy to get wrong under pressure, so let's be precise.

**Arguments are evaluated when `defer` runs, not when the deferred call runs.** This is the single most misunderstood point. The deferred *call* is delayed; its *arguments* are snapshotted immediately.

```go
func trace() {
    x := 1
    defer fmt.Println("deferred saw x =", x) // captures 1 right now
    x = 2
    fmt.Println("normal saw x =", x)         // prints 2
}
// Output:
// normal saw x = 2
// deferred saw x = 1
```

If you want the deferred call to see the *final* value, defer a closure instead — a closure captures the variable by reference, so it reads whatever the value is at return time:

```go
defer func() { fmt.Println("deferred saw x =", x) }() // reads x when the func runs
```

**Deferred calls run in LIFO order.** The last one deferred runs first. This matters when cleanups have ordering constraints — you release resources in the reverse of the order you acquired them, which is exactly what nested acquisition wants:

```go
mu.Lock()
defer mu.Unlock()          // runs last

f, err := os.Open(path)
if err != nil {
    return err
}
defer f.Close()            // runs first (LIFO), before the unlock
```

The most common day-to-day use is unlocking and closing right next to the acquisition, so the reader can see both in one glance and no early return can leak the resource:

```go
func (s *Store) Update(id string, fn func(*Row)) error {
    s.mu.Lock()
    defer s.mu.Unlock()

    row, ok := s.rows[id]
    if !ok {
        return ErrNotFound   // unlock still happens
    }
    fn(row)
    return nil               // unlock still happens
}
```

**The gotcha — defer in a loop:** a deferred call runs at *function* return, not at the end of the loop iteration. So this leaks every file handle until the function finally returns, and can exhaust file descriptors on a large directory:

```go
for _, path := range paths {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close() // BUG: all N files stay open until the function returns
    scan(f)
}
```

The fix is to give each iteration its own function scope, so the defer fires per iteration:

```go
for _, path := range paths {
    if err := func() error {
        f, err := os.Open(path)
        if err != nil {
            return err
        }
        defer f.Close() // runs when this closure returns, each iteration
        return scan(f)
    }(); err != nil {
        return err
    }
}
```

There is also a real (if usually small) cost to deferring in a hot loop; when a cleanup is trivial and the iteration count is huge, calling `f.Close()` explicitly can be the right call. Measure before you contort the code for it.

---

## `defer` and named return values

The one place `defer` reaches back and changes behaviour rather than just running cleanup is with **named return values**. A deferred closure can read *and modify* named returns after the `return` statement has set them but before control actually leaves the function. This is the mechanism behind almost every "wrap the error on the way out" and `recover` pattern in Go.

```go
func doWork() (err error) {
    defer func() {
        if err != nil {
            err = fmt.Errorf("doWork: %w", err) // rewrites the named return
        }
    }()

    if err = step1(); err != nil {
        return err
    }
    return step2()
}
```

The same hook is how you turn a panic into an error at a package boundary:

```go
func safeParse(input string) (result Node, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("parse panicked: %v", r) // sets the named return
        }
    }()
    return parse(input), nil // parse may panic deep inside
}
```

`recover` only does anything inside a deferred function, and it only stops a panic that is unwinding through *that* function. That's the whole contract, and it's why `defer` and panic recovery are inseparable.

**The gotcha:** this trick only works when the return value is *named*. With an anonymous return signature — `func doWork() error` — the deferred closure has nothing to assign to; it can observe a local `err` but its changes never reach the caller, because the return value was already copied out. If you intend a defer to alter what the caller sees, the return must be named. Conversely, if you *don't* want that coupling, avoid named returns precisely so a defer can't silently rewrite your result.

---

## Key takeaways

- **`if`/`switch` init statements scope tightly — and shadow.** Use them to keep a guard variable local, but remember `:=` creates a new variable; a stray shadowed `err` is a silently dropped error.
- **One loop, four shapes.** C-style, condition-only (`while`), infinite, and `range` are all `for`. Hoist expensive loop conditions out; `range`'s copy and per-iteration semantics deserve their own study.
- **`switch` doesn't fall through, and that's the point.** Prefer the tagless form over `else if` ladders; add a `default` that fails loudly when an unmatched value is actually a bug, because there's no built-in exhaustiveness check.
- **Labels beat clever flags for nested exits** — and a bare `break` inside a `select` breaks the `select`, not the loop. `goto` is legitimate only in generated code and hand-rolled state machines.
- **`defer` snapshots its arguments immediately, runs LIFO at function return.** That makes the loop-defer leak the trap to watch for, and named returns the hook that lets a defer wrap errors or recover from panics.

Control flow in Go is small enough to hold in your head entirely — which is exactly why the few sharp edges (shadowing, loop defers, argument evaluation timing, named-return coupling) are worth knowing cold. They're not exotic; they're the ones that show up in incident reviews.

---

## Further reading

- *Effective Go* — the canonical treatment of Go's control structures and idioms, including the rationale for a single `for` and a non-falling-through `switch`. https://go.dev/doc/effective_go
- The Go Blog, *Defer, Panic, and Recover* — the definitive explanation of defer's evaluation and ordering rules and how they combine with panic/recover. https://go.dev/blog/defer-panic-and-recover
