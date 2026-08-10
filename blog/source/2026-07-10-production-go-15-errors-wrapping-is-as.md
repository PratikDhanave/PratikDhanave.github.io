# Errors, Wrapping, and errors.Is / errors.As

*Go treats errors as ordinary values, not exceptions — which means everything you know about passing, comparing, and inspecting values applies. This is a working guide to sentinel errors, wrapping with %w, and the two verbs that make error chains navigable: errors.Is and errors.As.*

---

Most languages hide failure behind control flow: you `throw`, the stack unwinds, and a `catch` block far away decides what to do. Go made a different bet. An error is just a value implementing a one-method interface, returned like any other value and inspected with the same tools you'd use on a `string` or a struct. That's why `if err != nil` shows up on nearly every page of Go — and why error handling here rewards being deliberate.

This post is about that deliberateness: how to construct errors, how to compare them without brittle code, how to preserve context as an error travels up the stack, and how `errors.Is` and `errors.As` let a caller ask precise questions about a failure three layers down.

---

## Errors are values

The entire contract is this interface from the standard library:

```go
type error interface {
    Error() string
}
```

Anything with an `Error() string` method *is* an error — that's the whole type. A `nil` error means success; a non-nil error carries the details itself. Because it's an interface, an error can be a trivial string, a rich struct with fields, or a chain of nested errors — the caller decides how much it wants to know.

The idiom that falls out of this is the multiple-return signature: a function hands back its result *and* an error, and the caller checks the error before trusting the result.

```go
func parseTimeout(raw string) (time.Duration, error) {
    d, err := time.ParseDuration(raw)
    if err != nil {
        return 0, err
    }
    if d < 0 {
        return 0, fmt.Errorf("timeout must be non-negative, got %s", raw)
    }
    return d, nil
}
```

Two conventions worth internalising early. First, the error is the *last* return value, always. Second, when you return a non-nil error, return the zero value for everything else — callers are entitled to ignore the result when `err != nil`, and a half-populated result on failure is a trap.

**The gotcha:** an interface value is only `nil` when both its type and its value are nil. If you store a concrete error pointer that happens to be `nil` into an `error` variable and return that, the caller's `err != nil` check will be *true* even though "nothing went wrong." Never declare `var err *MyError` and return it as an `error`; return the interface directly and return a literal `nil` on the success path.

---

## Sentinel errors, and why `==` is fragile

Sometimes a caller needs to react to a *specific* failure — end of input, record not found, permission denied. The oldest pattern for this is the **sentinel error**: a package-level variable the caller can compare against.

```go
package store

import "errors"

var ErrNotFound = errors.New("store: record not found")

func (s *Store) Load(id string) (*Record, error) {
    r, ok := s.data[id]
    if !ok {
        return nil, ErrNotFound
    }
    return r, nil
}
```

`errors.New` returns a pointer under the hood, so each call produces a distinct value — that's exactly why exporting it *once* as `ErrNotFound` matters. Callers compare identity:

```go
r, err := s.Load(id)
if err == ErrNotFound {
    // fall back to a default
}
```

This works right up until someone adds context on the way up. The moment an intermediate layer does `fmt.Errorf("loading user %s: %v", id, err)`, the returned value is a *brand-new* error whose text mentions "record not found" but which is no longer `==` to `ErrNotFound`. The comparison silently stops matching, and a fallback that used to fire now doesn't.

**The gotcha:** direct `==` comparison against a sentinel only works if the error is returned completely unwrapped, all the way up. Any layer that adds context with `%v` breaks it, and it breaks *quietly* — the code compiles, the test that only checks the happy path passes, and the bug hides until production. The fix is to wrap deliberately and compare with `errors.Is` instead, which we'll get to below.

---

## Wrapping with `%w` to preserve the chain

Go 1.13 added a way to add context to an error *without* discarding the original: the `%w` verb in `fmt.Errorf`. Where `%v` formats the error as text and throws the value away, `%w` stores the original error inside the new one, forming a chain you can walk later.

```go
func (s *Service) User(id string) (*User, error) {
    r, err := s.store.Load(id)
    if err != nil {
        return nil, fmt.Errorf("service.User(%s): %w", id, err)
    }
    return userFromRecord(r), nil
}
```

The returned error prints as `service.User(42): store: record not found` — you get the readable, layered message *and* the original `ErrNotFound` stays reachable inside. Under the hood, `%w` produces an error with an `Unwrap() error` method returning the wrapped error. That single method is the entire mechanism the `errors` package builds on.

A few rules keep wrapping clean:

- Use exactly **one** `%w` per `fmt.Errorf` call in the common case. (Go 1.20+ allows several, which builds a multi-error — more on that later.)
- Don't repeat the callee's message. Add what *this* layer knows — the id, the operation, the file path — not a paraphrase of what you're wrapping.
- Don't start the message with "error" or "failed to." The caller may prefix it again; you'll end up with "failed to failed to."

**The gotcha:** `%w` and `%v` look almost identical but differ in a way that matters. `%v` *severs* the chain — the original becomes unreachable text, and `errors.Is` / `errors.As` can no longer find anything inside. Reach for `%v` deliberately, only when you *want* to hide the underlying error (see the API-boundary section). When unsure, `%w` is the safer default: you can always stop unwrapping, but you can't recover what `%v` discarded.

---

## `errors.Is`: matching a sentinel through wraps

`errors.Is(err, target)` walks the chain — calling `Unwrap` at each step — and reports whether *any* error in it matches `target`. It's the wrap-aware replacement for `==`.

```go
r, err := svc.User(id)
if errors.Is(err, store.ErrNotFound) {
    // still matches, even though svc.User wrapped it twice
    return defaultUser(), nil
}
```

Rewrite every `err == ErrSomething` as `errors.Is(err, ErrSomething)` and your comparisons survive any amount of wrapping in between. It also handles the un-wrapped case, so use it uniformly.

You can teach `errors.Is` a broader notion of "matches" by giving a custom type an `Is(target error) bool` method — useful when several distinct values should count as the same category. But for the common sentinel case you write nothing: the default identity comparison at each link is enough.

**The gotcha:** `errors.Is` compares by *identity* at each link, so the target must be the same value the code produced — a package-level `var`. If you write `errors.Is(err, errors.New("record not found"))`, it will *never* match: `errors.New` mints a fresh pointer every call, and identity comparison against a throwaway value always fails. Sentinels exist precisely so there's one stable value to point `errors.Is` at.

---

## `errors.As`: extracting a typed error through wraps

`errors.Is` answers a yes/no question. Often you need more: the *fields* of a structured error — an HTTP status code, the offending field name, a retry-after duration. That's `errors.As`. It walks the chain looking for an error that matches a concrete type, and if it finds one, assigns it into a pointer you supply so you can read its fields.

```go
type ValidationError struct {
    Field string
    Rule  string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %q: %s", e.Field, e.Rule)
}
```

A caller three layers up can pull that structured value back out of a wrapped chain:

```go
var vErr *ValidationError
if errors.As(err, &vErr) {
    // vErr is now the concrete *ValidationError from deep in the chain
    http.Error(w, vErr.Error(), http.StatusBadRequest)
    log.Printf("bad field: %s", vErr.Field)
}
```

The second argument is a *pointer to* the type you want — here `**ValidationError`, because the error is `*ValidationError`. Get that indirection wrong and `errors.As` panics at runtime: the variable is `var vErr *ValidationError`, and you pass `&vErr`.

**The gotcha:** the type in the `As` target must exactly match how the error was *created*, pointer-ness included. If your `Error()` method has a pointer receiver, values of that type only satisfy `error` as pointers, so you construct `&ValidationError{...}` and match with `var vErr *ValidationError`. Match against the non-pointer `ValidationError` and it won't find anything. Pick pointer-or-value once per type and stay consistent — mixing them is the most common reason `errors.As` "mysteriously" returns false.

---

## Custom error types: `Error()` and `Unwrap()`

A struct error earns its place when callers need to branch on *data*, not just identity. Give it an `Error()` method to satisfy the interface, and — if it wraps something — an `Unwrap()` method so `errors.Is` and `errors.As` can see through it.

```go
type QueryError struct {
    Query string
    Err   error // the underlying cause
}

func (e *QueryError) Error() string {
    return fmt.Sprintf("query %q: %v", e.Query, e.Err)
}

func (e *QueryError) Unwrap() error {
    return e.Err
}
```

Now `QueryError` is both a rich, inspectable value *and* a transparent link in the chain. A caller can do `errors.As(err, &qErr)` to read `qErr.Query` *and* `errors.Is(err, sql.ErrNoRows)` to detect the wrapped cause — both work because `Unwrap` exposes the inner error. It's the same transparency `%w` gives you, written by hand so you can attach fields.

The distinction, plainly: `fmt.Errorf` with `%w` is the quick way to add a *message* to a chain; a custom type is what you reach for when callers need *structured data* to branch on.

---

## Wrapping vs. not-wrapping: the API boundary

Wrapping preserves information — which is usually what you want, but not always. When you wrap with `%w`, you make the underlying error part of your **public contract**. Callers can now write `errors.Is(err, sql.ErrNoRows)` against your function, and if you later swap your database layer, that comparison breaks. You've leaked an implementation detail across your API boundary.

So the rule is contextual:

- **Wrap (`%w`)** within a package or subsystem, and whenever callers legitimately need to detect the underlying cause. This is the default.
- **Don't wrap (`%v`, or a fresh error)** at a public boundary when the underlying error is an internal detail you don't want to commit to. Translate it into a stable error your package owns.

```go
func (s *Service) Fetch(id string) (*Doc, error) {
    d, err := s.db.query(id)
    if errors.Is(err, sql.ErrNoRows) {
        // translate: callers depend on ErrDocMissing, not on our DB choice
        return nil, ErrDocMissing
    }
    if err != nil {
        // opaque: don't expose the raw driver error across the boundary
        return nil, fmt.Errorf("fetch %s: %v", id, err)
    }
    return d, nil
}
```

**The gotcha:** wrapping is a promise. Every error you expose with `%w` is something a caller may start matching against, and removing it later is a breaking change even though the compiler won't flag it. Wrap generously *inside* your own code where you control both sides; wrap *conservatively* at the edges where other people's code depends on you.

---

## `errors.Join`: more than one thing went wrong

Go 1.20 added `errors.Join`, which combines several errors into one. It's the tool for situations where a single "first error wins" return would throw away real information — validating many fields, closing several resources, running a batch where some items fail.

```go
func validate(u *User) error {
    var errs []error
    if u.Name == "" {
        errs = append(errs, errors.New("name is required"))
    }
    if u.Age < 0 {
        errs = append(errs, errors.New("age must be non-negative"))
    }
    if !strings.Contains(u.Email, "@") {
        errs = append(errs, errors.New("email is invalid"))
    }
    return errors.Join(errs...) // nil if errs is empty
}
```

`errors.Join` returns `nil` when every argument is nil (and skips nil arguments), so the empty-`errs` case just works — no special-casing needed. The joined error's `Error()` prints each sub-error on its own line, and — importantly — `errors.Is` and `errors.As` both search *across all* the joined errors, not just a single chain. So a caller can still ask `errors.Is(err, ErrRequired)` against a joined value and get a hit if any branch contributed it.

**The gotcha:** `errors.Join` builds a *tree*, not a linear chain, and there's no single `Unwrap() error` to walk — the multi-error implements `Unwrap() []error` instead. If you write code that manually calls `Unwrap()` expecting one error, it won't see the joined children. Always inspect joined errors with `errors.Is` / `errors.As`, which understand both shapes, rather than hand-rolling the traversal.

---

## When to return, handle, or log

The last piece is judgment, not syntax: an error should be dealt with **exactly once**. The common anti-pattern is handling it more than once — logging *and* returning it — so the same failure shows up three times in your logs, once per layer, each entry looking like a separate incident.

The discipline:

- **Return it** (usually wrapped) when the current function can't sensibly decide what to do. This is most functions most of the time. Add context, hand it up.
- **Handle it** when *this* layer is the right place to recover — retry, fall back to a default, degrade gracefully. Once you've handled it, the error is dealt with; don't also return it.
- **Log it** only at the layer that finally decides the outcome — typically the top of a request handler, a `main`, or a worker loop. Log once, with the full wrapped chain (which now carries context from every layer it passed through), and stop.

Wrapping and "handle once" reinforce each other: because each layer adds context with `%w` on the way up, a *single* log line at the top contains the whole story — operation, ids, and root cause — so you never needed the intermediate log lines.

| Situation | Do this |
|---|---|
| Callers may need to detect a specific failure | Sentinel `var Err… = errors.New(...)`, matched with `errors.Is` |
| Callers need structured fields off the failure | Custom type with `Error()` + `Unwrap()`, extracted with `errors.As` |
| Adding context as the error travels up | `fmt.Errorf("...: %w", err)` |
| Hiding an internal error at a public boundary | `fmt.Errorf("...: %v", err)` or a fresh package-owned error |
| Several independent failures at once | `errors.Join(errs...)` |
| You can recover here | Handle it — don't also return or log it |
| You're at the top of the call stack | Log the full chain once |

---

## Key takeaways

- **Errors are values.** They satisfy a one-method interface, travel as ordinary return values, and are inspected with ordinary tools — no exceptions, no unwinding.
- **`==` against a sentinel is fragile;** any layer that adds context breaks it silently. Use `errors.Is`, which walks the wrap chain.
- **`%w` preserves the chain, `%v` severs it.** Default to `%w` inside your code so `errors.Is` / `errors.As` keep working; drop to `%v` deliberately at boundaries you don't want to commit to.
- **`errors.Is` answers "is this *that* error?"; `errors.As` answers "give me the typed error so I can read its fields."** Match `As` targets to how the error was constructed, pointer-ness and all.
- **A custom type needs `Error()` to be an error and `Unwrap()` to stay transparent** to `Is`/`As`.
- **`errors.Join` (1.20+) collects multiple failures** into a tree that `Is`/`As` still search; don't hand-walk it.
- **Deal with each error once** — return, handle, *or* log. Wrap on the way up so a single log line at the top tells the whole story.

---

## Further reading

- [Working with Errors in Go 1.13](https://go.dev/blog/go1.13-errors) — the Go blog post that introduced `%w`, `errors.Is`, and `errors.As`.
- [`errors` package documentation](https://pkg.go.dev/errors) — the reference for `Is`, `As`, `Join`, `New`, and `Unwrap`.
