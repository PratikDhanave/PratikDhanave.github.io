# context: Cancellation, Deadlines, and Values

*How Go's `context` package carries a cancellation signal, a deadline, and a small bag of request-scoped values across every API and goroutine boundary in a request — and the handful of rules that keep it from leaking or lying to you.*

---

Every non-trivial Go program is a tree of goroutines doing work on someone's behalf: an HTTP handler that queries a database, which opens a connection, which runs a goroutine to read from the socket. When the caller at the top gives up — the client hangs up, a timeout fires, a sibling request fails — that signal has to travel *down* the whole tree so the leaf work stops instead of burning CPU and holding connections for an answer nobody will read.

There is no language feature for that. Go's answer is a plain value you pass by hand: a `context.Context`. It carries three things across boundaries — a **cancellation signal**, an optional **deadline**, and a set of **request-scoped values** — and it does so in a way that composes: a context derived from another inherits everything the parent carried. Master the derivation tree and the four rules below and you have most of what production Go concurrency asks of you.

---

## Why context exists: the propagation problem

Before `context`, cancellation was ad hoc — every library invented its own `Stop()` method, `done chan struct{}`, or timeout argument, and none of them composed. To abandon a slow database call, you had to hope the driver exposed *some* hook, and hope every layer in between forwarded it.

`context.Context` standardizes that hook into one interface every layer agrees to speak:

```go
type Context interface {
    Deadline() (deadline time.Time, ok bool)
    Done() <-chan struct{}
    Err() error
    Value(key any) any
}
```

`Done()` returns a channel that is closed when the work should stop. `Err()` tells you *why* once it is closed. `Deadline()` reports when it will fire on its own. `Value()` retrieves request-scoped data. Because it is a single interface, a cancellation started in an HTTP handler flows unchanged through your service layer, into the SQL driver, and down to the socket read — every layer only has to accept a `ctx` and pass it along.

---

## The roots: `Background` and `TODO`

Every context tree starts at a root you never cancel. There are exactly two:

```go
ctx := context.Background() // the top of the tree: main, init, top-level requests
ctx := context.TODO()       // a placeholder — "I haven't decided which context yet"
```

Functionally they are identical — both are empty, never cancelled, no deadline, no values. The difference is *intent*. `Background()` is what you use in `main`, in tests, and as the root of an incoming request when you have nothing else. `TODO()` is a marker you leave when you know a context *should* be threaded through but the surrounding code doesn't provide one yet; static analysis tools and reviewers read it as "come back and fix this."

**The gotcha:** you almost never call `Background()` deep inside a request. If you find yourself minting a fresh `context.Background()` in a helper function, you have severed the tree — the cancellation and deadline from the real caller no longer reach that code. Accept a `ctx` parameter instead and derive from it.

---

## Deriving cancellable contexts — and always `defer cancel()`

You don't cancel a context directly; you *derive* a child that comes with a cancel function, and calling that function cancels the child (and everything derived from it). There are three constructors:

```go
ctx, cancel := context.WithCancel(parent)                 // cancel manually
ctx, cancel := context.WithTimeout(parent, 5*time.Second) // cancel after a duration
ctx, cancel := context.WithDeadline(parent, someTime)     // cancel at an absolute time
```

`WithTimeout` is just `WithDeadline(parent, time.Now().Add(d))` — same machinery, friendlier argument. All three return a `cancel` function, and **you must always call it**, even when a timeout will fire on its own:

```go
ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
defer cancel()

if err := doWork(ctx); err != nil {
    return err
}
```

**The gotcha:** forgetting `cancel()` leaks resources. Deriving a cancellable context registers it with its parent so cancellation can propagate; until `cancel` runs, that registration — and any timer `WithTimeout` started — stays alive, even after the function returns and the context is otherwise unreachable. `defer cancel()` on the line right after the constructor is the idiom, and `go vet` ships a `lostcancel` check that flags a cancel function you never call. Calling `cancel` a second time is a harmless no-op, so `defer` is always safe.

---

## Reacting to cancellation: `Done()`, `Err()`, and `select`

Accepting a `ctx` is only half the contract; the other half is *acting* on it. A function that takes a context but never checks it is lying to its callers — it accepts the cancellation signal and ignores it.

For code that blocks or loops, `select` on `ctx.Done()`:

```go
func worker(ctx context.Context, jobs <-chan Job) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err() // Canceled or DeadlineExceeded
        case job, ok := <-jobs:
            if !ok {
                return nil
            }
            process(job)
        }
    }
}
```

`ctx.Done()` returns a channel that is *closed* on cancellation — and a receive from a closed channel returns immediately, forever, which is exactly what you want: once cancelled, every future `select` takes the `Done` branch. After that, `ctx.Err()` is non-nil and tells you which of two sentinel errors applies: `context.Canceled` (someone called `cancel`) or `context.DeadlineExceeded` (a timeout or deadline elapsed).

**The gotcha:** `Done()` allocates a channel lazily, so poll it, don't hoard it — but more importantly, a tight compute loop with no blocking operation won't notice cancellation on its own. Add an explicit check at a sensible granularity:

```go
for i, item := range items {
    if i%1000 == 0 {
        if err := ctx.Err(); err != nil {
            return err // bail out of a long CPU-bound loop
        }
    }
    crunch(item)
}
```

Checking `ctx.Err()` every iteration of a hot loop is itself overhead; sampling every N iterations keeps the loop responsive without paying the cost on every pass.

---

## The rules of passing context

Two conventions are near-universal in idiomatic Go, and both are enforced by convention and tooling rather than the compiler.

**First parameter, always named `ctx`:**

```go
func FetchUser(ctx context.Context, id string) (*User, error) // yes
func FetchUser(id string, ctx context.Context) (*User, error) // no
```

Putting it first makes the threading obvious and lets `go vet` and linters reason about call sites. The one exception is variadic functions, where it still leads: `func Log(ctx context.Context, args ...any)`.

**Never store a context in a struct.** A context describes the lifetime of *one call*; a struct outlives any single call. Stashing a `ctx` in a field means later method calls use a stale cancellation signal and deadline — often one that already fired, or one that will never fire for the operation actually running.

```go
type Server struct {
    ctx context.Context // wrong: whose request does this belong to?
}

func (s *Server) Handle(ctx context.Context, r Request) error { // right: fresh per call
    ...
}
```

**The gotcha:** the tempting exception — "but I need the context in a background goroutine the struct spawns" — is exactly where storing it bites hardest, because the request context is cancelled the moment the request returns, killing your background work. If you need work to outlive the request, derive from `context.Background()` deliberately (perhaps with its own timeout), don't smuggle the request context out through a field.

---

## The derivation tree and the deadline-minimum rule

Every derived context points at its parent, forming a tree rooted at `Background()`. Cancellation flows *down*: cancel a node and every descendant's `Done()` closes too. It never flows up — cancelling a child leaves the parent and its siblings untouched.

Deadlines compose the same way, and the rule is worth memorizing: **a child's effective deadline is the minimum of its own and its parent's.** You can tighten a deadline by deriving a shorter one, but you can never loosen it — asking for more time than the parent allows gets you the parent's deadline.

```go
parent, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

// This asks for 10s, but the parent only has 2s left — the child fires at 2s.
child, cancelChild := context.WithTimeout(parent, 10*time.Second)
defer cancelChild()
```

This is why a per-request deadline set at the edge of your service silently bounds every downstream call: a database query deriving its own generous timeout still can't outrun the request's remaining budget. It also means you should derive tighter deadlines for individual sub-operations freely — the parent remains the ceiling.

---

## `WithValue`: request-scoped data, and only that

The fourth thing a context carries is a small set of key-value pairs, attached with `context.WithValue` and read with `ctx.Value(key)`. This is for data that is genuinely *scoped to the request and crosses API boundaries* — a request ID for correlating logs, an authenticated user identity, a trace span. It is emphatically **not** a way to pass optional function parameters.

The critical detail is the key. Using a bare string like `"userID"` invites collisions: another package (or a future version of yours) using the same string silently overwrites your value. The idiom is an **unexported custom type** so the key is unique across the entire program:

```go
package auth

// unexported type — no other package can construct this key
type contextKey int

const userKey contextKey = 0

// typed setter and getter keep the any-typed API off your callers
func WithUser(ctx context.Context, u *User) context.Context {
    return context.WithValue(ctx, userKey, u)
}

func UserFrom(ctx context.Context) (*User, bool) {
    u, ok := ctx.Value(userKey).(*User)
    return u, ok
}
```

Because `contextKey` is unexported, no code outside `package auth` can produce a key equal to `userKey`, so nobody can collide with or read your value except through the typed helpers you expose.

**The gotcha:** `Value` lookups walk the context chain link by link, and the API is untyped (`any` in, `any` out) — that's why you wrap it in typed helpers rather than sprinkling raw `ctx.Value(...)` and type assertions through the codebase. If you catch yourself passing a *behavioral* parameter — a page size, a flag, a callback — through the context, stop: those belong in the function signature where the compiler can check them. The context is for cross-cutting request metadata, nothing more.

---

## Knowing *why* it was cancelled: `WithCancelCause` and `Cause`

Plain `cancel()` collapses every reason into the same `context.Canceled` error. When several things can cancel the same context, that ambiguity hurts. Go 1.20 added `WithCancelCause`, whose cancel function takes an error explaining the reason, and `context.Cause(ctx)`, which retrieves it:

```go
ctx, cancel := context.WithCancelCause(parent)
defer cancel(nil) // nil cause is fine; still required to avoid a leak

go func() {
    if err := validate(input); err != nil {
        cancel(fmt.Errorf("validation failed: %w", err))
    }
}()

<-ctx.Done()
fmt.Println(ctx.Err())        // context.Canceled  (the generic signal)
fmt.Println(context.Cause(ctx)) // validation failed: ... (your specific reason)
```

`ctx.Err()` still returns the generic sentinel for compatibility, while `context.Cause(ctx)` returns the specific error you supplied — or `context.Canceled`/`context.DeadlineExceeded` when no custom cause was given. Go 1.21 rounded this out with `context.WithDeadlineCause` and `context.WithTimeoutCause`, letting you attach a descriptive error to a *timeout* as well, and `context.AfterFunc`, which registers a callback to run when a context is done.

**The gotcha:** `Cause` only tells you something richer than `Err` if you actually derived with a `*Cause` constructor and passed a meaningful error to `cancel`. `WithCancelCause` still returns a cancel function you must call — its signature is `func(cause error)`, and passing `nil` is the equivalent of a plain cancel. The `defer cancel(nil)` is still mandatory to avoid the leak.

---

## A cancellable worker with a timeout, tied together

The three pieces — a derived timeout, a `select` on `Done()`, and honest error propagation — compose into the shape you'll write constantly:

```go
func fetchWithTimeout(parent context.Context, url string) (string, error) {
    ctx, cancel := context.WithTimeout(parent, 2*time.Second)
    defer cancel()

    result := make(chan string, 1) // buffered: the goroutine never blocks on send
    go func() {
        result <- slowFetch(url) // real work; ideally slowFetch takes ctx too
    }()

    select {
    case <-ctx.Done():
        return "", ctx.Err() // timed out or parent cancelled — abandon the wait
    case r := <-result:
        return r, nil
    }
}
```

The buffered channel matters: if the timeout branch wins and the function returns, the goroutine can still complete its send into the buffer instead of blocking forever on an unbuffered channel nobody receives from. The truly correct version also threads `ctx` into `slowFetch` so the underlying work *stops* — abandoning the wait while the work grinds on is a leak of a different kind.

---

## Key takeaways

- **Context propagates three things across boundaries:** a cancellation signal, a deadline, and request-scoped values — through one interface every layer speaks.
- **Derive, then `defer cancel()`.** Every `WithCancel`/`WithTimeout`/`WithDeadline` returns a cancel function you must call, or you leak; `go vet`'s `lostcancel` check enforces it.
- **Accepting a context means acting on it.** `select` on `ctx.Done()` in blocking code, poll `ctx.Err()` in long CPU loops, and return the error you get.
- **Pass `ctx` first, never store it in a struct.** It describes one call's lifetime; a field outlives that call and hands out a stale signal.
- **The tree enforces `min(parent, own)` deadlines.** You can tighten a downstream budget but never exceed the parent's.
- **`WithValue` is for request-scoped metadata only, keyed by a private type.** Behavioral parameters belong in the signature; a bare-string key invites silent collisions.
- **`WithCancelCause`/`context.Cause` (1.20+) recover the *reason*** when the generic `context.Canceled` isn't enough to debug why work stopped.

---

## Further reading

- [Go Concurrency Patterns: Context](https://go.dev/blog/context) — the original Go blog post that introduced the pattern and its rationale.
- [`context` package documentation](https://pkg.go.dev/context) — the authoritative reference for every constructor, including the Go 1.20/1.21 `*Cause` and `AfterFunc` additions.
