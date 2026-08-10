# panic, recover, and defer's Role

*Go handles ordinary failure with values, not exceptions — so what are panic and recover actually for? A working guide to how panic unwinds the stack through your defers, why recover only fires inside a deferred function, and the narrow set of places where catching a panic is the right call rather than a code smell.*

---

The previous post argued that Go treats errors as ordinary values: you return them, compare them, and inspect them with the same tools you'd use on any other value. That model covers the overwhelming majority of failure in a Go program. So it's fair to ask what `panic` and `recover` are even for — they look like the `throw`/`catch` Go deliberately walked away from.

They aren't. `panic` is not exception handling wearing a Go costume, and reaching for it as control flow is a clear sign that someone learned the language from another one. The mechanism is real and occasionally indispensable, but its correct uses are narrow. This post draws that line precisely: what `panic` does to the stack, why `recover` is welded to `defer`, and the handful of situations where catching a panic is engineering rather than a smell.

---

## What panic actually does

A `panic` stops the ordinary flow of the current function immediately. But it does not just crash — it begins *unwinding* the goroutine's stack, and on the way out it runs every deferred function that was registered, in last-in-first-out order, in each frame it passes through.

```go
func work() {
	defer fmt.Println("work: deferred")
	fmt.Println("work: before panic")
	panic("something broke")
	fmt.Println("work: after panic") // never runs
}

func main() {
	defer fmt.Println("main: deferred")
	work()
	fmt.Println("main: after work") // never runs
}
```

This prints `work: before panic`, then `work: deferred`, then `main: deferred`, and finally the program dies with the panic message and a stack trace. The two "after" lines never execute. The important detail is that deferred functions *still run* during a panic — that's the whole reason `defer` and `panic` belong in the same conversation. Your cleanup (closing files, releasing locks, flushing buffers) fires on the way out whether the function returns normally or panics. If nothing along the way stops the unwind, it reaches the top of the goroutine's stack and the runtime terminates the whole program.

That last clause matters more than it looks: **an unrecovered panic anywhere kills the entire process, not just the goroutine.** There is no "let this one goroutine die quietly" — a panic that escapes its goroutine takes everything down with it.

---

## recover: only from inside a defer

`recover` is the one function that can stop an unwind in progress. It has a strict contract: it only does anything **when called directly from a deferred function** while a panic is propagating. Call it anywhere else — in normal flow, or one call deeper than the deferred function — and it returns `nil` and does nothing.

```go
func safeDivide(a, b int) (result int, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("recovered: %v", r)
		}
	}()
	return a / b, nil // integer divide-by-zero panics at runtime
}
```

When `b` is zero the division panics, the unwind begins, and because `safeDivide` registered a deferred closure, that closure runs. Inside it, `recover()` returns the panic value (here a `runtime.Error`), the unwind stops there, and `safeDivide` returns normally — with `err` set. Call it with a non-zero `b` and `recover()` returns `nil`, the `if` is skipped, and the function returns its real result.

Two things make this work, and both are easy to get wrong:

- The `recover` call must be **directly inside the deferred function**. If you factor it into a helper that the deferred function calls, `recover` is no longer running at the right stack depth and returns `nil`.
- `recover` only reports a value **when there is an active panic**. On a normal return it always returns `nil`, which is exactly why the `if r := recover(); r != nil` guard is the canonical shape.

**The gotcha:** `recover()` invoked outside a deferred function — or invoked when no panic is in flight — is not an error and gives no warning. It silently returns `nil`. A `recover` you *thought* was catching panics but placed one call too deep will let every panic sail straight past it, and you won't find out until production.

---

## Convert a panic into an error with a named return

The `safeDivide` example above quietly used the single most useful pattern in this entire topic, so it's worth naming: a **named return value** lets a deferred `recover` change what the function returns.

Because `err` is declared in the signature, the deferred closure can assign to it *after* the panic has interrupted the normal `return`. The function still returns cleanly to its caller — with an error value instead of a crash. Without a named return there is no variable for the closure to write to, and the recovered function would return its zero values silently, which is almost never what you want.

```go
func parseConfig(raw []byte) (cfg Config, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("parseConfig: %w", asError(r))
		}
	}()
	return mustParse(raw), nil // mustParse may panic on malformed input
}

func asError(r any) error {
	if e, ok := r.(error); ok {
		return e
	}
	return fmt.Errorf("%v", r)
}
```

This is how a package with a panicking internal core presents a clean, boring `(T, error)` face to its callers. The `asError` helper is worth keeping around: a panic value is `any`, and it's frequently — but not always — an `error`, so you type-assert before wrapping.

---

## When panic is the right tool

The rule is short: **use `panic` for programmer errors and truly unrecoverable states, never for expected failures.** Expected failures — a missing file, a malformed request, a timed-out call — are values that go back to the caller as errors. Panic is for the situations where continuing would be meaningless or unsafe:

- **Invariants that must hold.** A `switch` over an enum that has covered every legitimate case can `panic("unreachable")` in the `default` — if you land there, the program's assumptions are already broken.
- **Impossible-to-handle constructor failures at init.** The standard library does this deliberately: `regexp.MustCompile` panics on a bad pattern because the pattern is a compile-time constant written by the programmer, not runtime input. The `Must*` naming is the convention that says "this panics; only feed it values you control."
- **Nil dereferences, out-of-range indexing, and the like** — these panic on their own. You don't write them; the runtime raises them when your code has a bug.

The test is simple: *could a correct program, given valid input, hit this?* If yes, it's an error value. If it can only happen because the code itself is wrong, a panic is defensible — it fails loudly and close to the bug instead of limping onward with corrupted state.

---

## Legitimate recovery: the goroutine boundary

If panic is mostly for bugs, why ever recover? Because sometimes the blast radius of a single bug is unacceptable. The textbook case is a server: one HTTP handler hits a nil-pointer bug, panics, and without intervention that panic unwinds past the handler, escapes its goroutine, and **kills the entire server** — dropping every other in-flight request along with it. That's a terrible trade for one bad handler.

So a server recovers at the boundary between "framework code" and "your handler," converting a panic into a `500` and keeping the process alive. Go's own `net/http` does exactly this: the server recovers from handler panics so one request can't take down the rest.

```go
func recoverMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				log.Printf("panic serving %s: %v\n%s", r.URL.Path, rec, debug.Stack())
				http.Error(w, "internal server error", http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}
```

Two disciplines make this responsible rather than reckless. First, **log the panic and its stack** (`debug.Stack()`) — recovering silently just converts a loud crash into a mystery. Second, recover only at the boundary you own. This isn't "catch everything so nothing fails"; it's "contain a bug to the one request that triggered it, then surface it so someone fixes it."

The same reasoning applies to **libraries**: a well-behaved package should not let panics cross its public API. If your internals use panic for control (some parsers and recursive-descent evaluators do, because it's genuinely cleaner than threading errors through deep recursion), recover at the exported boundary and hand the caller an `error`. The caller of your `Parse` function should never have to wrap their call site in a defer/recover to use your library safely.

---

## Re-panicking: recover, then decide

Recovering doesn't oblige you to swallow. A common and correct pattern is to recover, inspect the value, handle the cases you understand, and **re-panic** on the ones you don't:

```go
defer func() {
	if r := recover(); r != nil {
		if pe, ok := r.(parseError); ok {
			err = pe // ours; convert to a clean error
			return
		}
		panic(r) // not ours — let it keep unwinding
	}
}()
```

This is how a package that uses panic internally distinguishes its own signalling from a genuine bug. A `parseError` it threw on purpose becomes a returned error; a `runtime.Error` (nil deref, index out of range) is a real defect that has no business being hidden, so it re-panics up the stack. Blanket-catching everything and returning `nil` is how you turn a crash into silent data corruption.

---

## The gotcha that bites everyone: recover is per-goroutine

Here is the mistake that survives code review and fails in production. A `defer`/`recover` protects **only the goroutine it runs in.** You cannot recover a panic that happens in a *different* goroutine — even one you just started.

```go
func doomed() {
	defer func() {
		// This recover protects doomed's goroutine — NOT the one below.
		if r := recover(); r != nil {
			log.Println("recovered:", r)
		}
	}()

	go func() {
		panic("in a child goroutine") // NOT caught above — crashes the process
	}()

	time.Sleep(time.Second)
}
```

The panic in the child goroutine unwinds *its own* stack, finds no `recover` there, reaches the top, and takes the whole program down. The parent's deferred `recover` never sees it, because recover only inspects the panicking goroutine's own stack. **Every goroutine is responsible for recovering its own panics.** If you spawn a goroutine that might panic — especially anything running handler logic — that goroutine needs its *own* deferred recover as its first statement, or a helper that wraps the work:

```go
func safeGo(work func()) {
	go func() {
		defer func() {
			if r := recover(); r != nil {
				log.Printf("goroutine panic: %v\n%s", r, debug.Stack())
			}
		}()
		work()
	}()
}
```

This is easy to forget precisely because the parent looks protected. It isn't. When you fan work out across goroutines, the recover has to travel with the work.

---

## panic(nil) and the Go 1.21 change

For years there was a genuine trap: `panic(nil)` would panic with a `nil` value, and the idiomatic `if r := recover(); r != nil` guard would then treat it as "no panic happened." Code could panic and be recovered, yet the recovery logic would silently skip its handling because the value tested as `nil`.

Go 1.21 closed this. Now `panic(nil)` (or panicking with any nil interface value) causes `recover` to return a non-nil `*runtime.PanicNilError`, so the standard guard works correctly and the panic is no longer swallowed. You can opt back into the old behavior with `GODEBUG=panicnil=1`, but there's no reason to. The practical takeaway: don't call `panic(nil)`; if you need a signal value, panic with a real one. And know that on any modern Go, the `r != nil` check you'll see everywhere is now genuinely reliable.

---

## Key takeaways

- **panic unwinds the stack, running every defer on the way out.** Cleanup still happens; if nothing recovers, the whole process dies — not just the goroutine.
- **recover only works when called directly inside a deferred function during an active panic.** One call too deep, or outside a defer, and it silently returns `nil`.
- **Panic is for programmer errors and unrecoverable states, not expected failure.** Expected failure is a returned error value — that's the contract from the previous post, and panic doesn't change it.
- **Named return + recover is how you convert a panic into an error** and present a clean `(T, error)` API over a panicking core.
- **Recover at boundaries: the server request handler and the library's public edge.** Log the stack, re-panic on values you don't own, and never blanket-swallow.
- **recover is per-goroutine.** A panic in a child goroutine is invisible to the parent's recover — every goroutine you spawn needs its own, or it will crash the process.
- **Don't `panic(nil)`.** Since Go 1.21 it yields a `*runtime.PanicNilError`, so the usual `r != nil` guard finally behaves.

---

## Further reading

- [Defer, Panic, and Recover](https://go.dev/blog/defer-panic-and-recover) — the Go blog's foundational walkthrough of how the three interact.
- [The Go Programming Language Specification: Handling panics](https://go.dev/ref/spec#Handling_panics) — the precise semantics of `panic` and `recover`.
