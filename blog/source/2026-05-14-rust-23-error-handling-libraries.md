# Error Handling with anyhow and thiserror

*Module 1 covered Rust's error-handling foundation — `Result`, `Option`, and the `?` operator. It works, but as programs grow, two friction points appear: defining custom error types by hand is tedious boilerplate, and propagating many different error types through `?` gets awkward. The Rust ecosystem answers with two small, near-universal crates — `thiserror` and `anyhow` — that make error handling ergonomic. Knowing which to use where is a piece of practical Rust fluency every real project needs.*

Module 1 introduced Rust's error handling (`Result`, `Option`, `?`). This post covers the ecosystem's ergonomic error-handling crates: **`thiserror`** (for defining custom error types easily) and **`anyhow`** (for easy error propagation in applications). These aren't in the standard library but are near-universal in real Rust code, and knowing *which to use when* is essential practical knowledge. It builds directly on the `Result`/`?` foundation, making it ergonomic at scale.

## Recap: Result, Option, and ?

Briefly recapping Module 1's foundation, since these crates build on it:

- **`Result<T, E>` and `Option<T>` for errors and absence.** Rust has no exceptions — errors are ordinary values: `Result<T, E>` (`Ok(T)` or `Err(E)`) for operations that can fail, and `Option<T>` (`Some(T)` or `None`) for values that may be absent. You *handle* these explicitly (the compiler makes you), so failures can't be silently ignored. Errors as data — Module 1's core idea.
- **The `?` operator propagates errors.** The `?` operator on a `Result` *returns the error early* if it's `Err` (propagating it up), or *unwraps* the value if `Ok` — making error propagation concise. `let x = may_fail()?;` returns the error if `may_fail` failed, else gives the value. `?` is the ergonomic way to propagate errors up the call stack. It's the workhorse of Rust error handling.
- **The friction at scale.** This foundation is solid, but at scale two frictions appear: (1) *defining custom error types* (implementing the `Error` trait, `Display`, conversions) is *boilerplate-heavy* to do by hand; (2) *propagating many different error types* through `?` requires them to convert to a common type, which is awkward to set up manually. These frictions are what `thiserror` and `anyhow` solve. The foundation is good; the ergonomics need help.

Rust's error foundation (`Result`, `Option`, `?` — no exceptions, errors as handled data) is solid, but at scale defining custom error types is boilerplate-heavy and propagating diverse error types through `?` is awkward. `thiserror` and `anyhow` address exactly these frictions. They serve different situations — libraries vs applications.

## thiserror: defining error types easily

**`thiserror`** makes *defining custom error types* easy — it removes the boilerplate of implementing the error machinery by hand, ideal for *libraries*:

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum DataError {
    #[error("file not found: {0}")]
    NotFound(String),

    #[error("invalid format")]
    InvalidFormat,

    // Automatically convert from io::Error via `?` (the #[from] attribute).
    #[error("I/O error")]
    Io(#[from] std::io::Error),
}
```

- **Derive custom error types with minimal boilerplate.** `thiserror` provides a `#[derive(Error)]` macro that *generates* the error-trait implementations (`Display` via `#[error("...")]` messages, the `Error` trait, etc.) for your custom error *enum* — so you define a clean error enum with messages, and the boilerplate is generated. It turns tedious hand-written error impls into a concise derive. Much less boilerplate for custom errors.
- **`#[error("...")]` sets the display message.** Each variant's `#[error("...")]` attribute defines its human-readable message (with access to fields like `{0}`) — so your errors have good messages, declaratively. Clear error messages without manual `Display` impls. Messages are declared inline.
- **`#[from]` enables automatic conversion for `?`.** The `#[from]` attribute on a variant auto-generates a `From` conversion, so *other* error types (like `std::io::Error`) *automatically convert* into your error type when using `?`. This makes propagating different underlying errors into your custom error type seamless — `?` just works across error types. `#[from]` solves the "propagate diverse errors" friction for your own error type. Conversions for free.
- **Best for libraries.** `thiserror` is ideal for *libraries* — where you want to define *specific, typed* error types (so callers can match on and handle distinct error cases) with minimal boilerplate. Libraries should expose meaningful error types (so users can handle errors precisely), and `thiserror` makes that ergonomic. Use `thiserror` when you need well-defined, typed errors (libraries). Precise, typed errors, easily.

`thiserror` makes defining custom, *typed* error enums easy — deriving the error-trait boilerplate, declaring messages with `#[error("...")]`, and enabling automatic conversions with `#[from]` (so `?` propagates diverse errors into your type) — ideal for *libraries* that should expose specific, matchable error types. When you don't need typed errors, `anyhow` is simpler.

## anyhow: easy error propagation for applications

**`anyhow`** makes error *propagation* easy when you *don't* need specific typed errors — ideal for *applications*:

```rust
use anyhow::{Context, Result};

// anyhow::Result<T> is Result<T, anyhow::Error> — one error type for everything.
fn load_config(path: &str) -> Result<String> {
    let contents = std::fs::read_to_string(path)
        .context("failed to read the config file")?; // add context, propagate any error
    Ok(contents)
}
```

- **One error type for everything.** `anyhow` provides `anyhow::Error` — a single, *dynamic* error type that *any* error can convert into — and `anyhow::Result<T>` (`Result<T, anyhow::Error>`). This means you can propagate *any* error type through `?` without defining custom types or conversions — everything becomes `anyhow::Error`. It removes the "many error types" friction by using *one* catch-all error type. Any error, one type, easy propagation. No custom error type needed.
- **Great for applications (where you just handle errors).** `anyhow` suits *applications* (binaries) — where you often *don't care* about distinguishing error types programmatically; you just want to *propagate* errors up and *report* them (log, show the user). For app code that just needs "propagate any error and eventually report it," `anyhow` is simpler than defining typed errors. Use `anyhow` when you just need easy propagation (applications). Simplicity when you don't need typed errors.
- **`.context()` adds helpful context.** `anyhow` adds `.context("...")` to attach a *message* to an error as it propagates — building a helpful *chain* of context ("failed to read config file" → underlying I/O error) that makes errors informative when reported. Context makes anyhow errors debuggable. It compensates for the loss of typed errors with rich context. Better error messages via context.
- **The distinction: typed (thiserror) vs dynamic (anyhow).** The key choice: `thiserror` for *typed, specific* errors (libraries — callers handle distinct cases), `anyhow` for a *single dynamic* error type (applications — just propagate and report). Libraries → `thiserror`; applications → `anyhow`. Knowing this distinction is the practical takeaway. Right tool for library vs app.

`anyhow` makes error propagation easy for *applications* — providing one dynamic catch-all error type (`anyhow::Error`) that any error converts into (so `?` propagates anything without custom types), plus `.context()` for helpful error context — ideal when you just need to propagate and report errors, not distinguish them. The `thiserror`-vs-`anyhow` choice is the practical crux.

## Choosing and using them

Putting it together, the practical guidance for ergonomic error handling in real Rust:

- **Libraries: use `thiserror`.** In *libraries*, define *typed* error types with `thiserror` — so your users can *match* on specific error cases and handle them precisely. Libraries should expose meaningful, typed errors (part of their API), and `thiserror` makes that low-boilerplate. Typed errors for library APIs. Give users errors they can handle.
- **Applications: use `anyhow`.** In *applications* (binaries), use `anyhow` for easy propagation — you usually just propagate errors up and report them, without needing typed distinctions. `anyhow`'s single error type plus `.context()` is simpler and sufficient for app code. Easy propagation for apps. Simplicity where typing isn't needed.
- **They build on the foundation.** Both crates build on Module 1's `Result`/`?` — they make it *ergonomic* (less boilerplate, easier propagation), not different. You still use `Result` and `?`; these crates just smooth the rough edges (`thiserror` for defining errors, `anyhow` for propagating them). The foundation is unchanged; the ergonomics improve. Same model, less friction.
- **They're near-universal in real Rust.** Though not in std, `thiserror` and `anyhow` are *extremely widely used* — near-standard in real Rust projects. Knowing them (and when to use each) is *practical Rust fluency* — you'll encounter and use them constantly. They're part of everyday Rust, so understanding the library/app distinction is essential real-world knowledge. Real Rust uses these crates.

Ergonomic error handling in real Rust uses `thiserror` (define typed error types easily — for libraries, so callers handle specific cases) and `anyhow` (one dynamic error type for easy propagation — for applications, just propagate and report), both building on Module 1's `Result`/`?` foundation. The library-vs-application distinction is the practical key, and these near-universal crates are essential Rust fluency. Next, the final Module 3 post: macros.

## Key takeaways

- Rust's error foundation (Module 1) — `Result<T, E>`, `Option<T>`, and `?` for propagation, with errors as handled data (no exceptions) — is solid, but at scale two frictions appear: defining custom error types is boilerplate-heavy, and propagating many different error types through `?` is awkward; `thiserror` and `anyhow` solve these.
- `thiserror` makes defining custom *typed* error enums easy: `#[derive(Error)]` generates the error-trait boilerplate, `#[error("...")]` declares display messages (with field access), and `#[from]` auto-generates conversions so `?` seamlessly propagates diverse underlying errors into your type — ideal for *libraries* that should expose specific, matchable error types.
- `anyhow` makes error *propagation* easy for *applications*: it provides one dynamic catch-all error type (`anyhow::Error`, and `anyhow::Result<T>`) that any error converts into (so `?` propagates anything without custom types), plus `.context()` to attach helpful context — ideal when you just propagate and report errors rather than distinguish them.
- The practical choice is typed-vs-dynamic: use `thiserror` (typed, specific errors) for libraries so callers can handle distinct cases, and `anyhow` (one dynamic error type) for applications where you just propagate and report — libraries → `thiserror`, applications → `anyhow`.
- Both crates build on (not replace) Module 1's `Result`/`?` — making error handling *ergonomic* (less boilerplate, easier propagation) with the same underlying model — and though not in std, they're near-universal in real Rust, so knowing them and when to use each is essential practical Rust fluency.

## Further reading

- [Rust: Error handling with Result and ? (Module 1)](/blog/posts/rust-08-error-handling.html)
- [The Rust Book — Error Handling (foundation)](https://doc.rust-lang.org/book/ch09-00-error-handling.html)
- [Testing in Rust (previous post)](/blog/posts/rust-22-testing.html)
