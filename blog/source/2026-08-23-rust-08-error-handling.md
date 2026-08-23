# Error Handling: Result, Option, and No Exceptions

*Rust has no exceptions. Errors and absent values are ordinary data — enum values you must handle — so the compiler forces you to deal with the possibility of failure instead of letting it propagate invisibly. It sounds tedious and turns out to be one of Rust's quiet strengths: you cannot forget to handle an error.*

The last post's enums and pattern matching were building to this: Rust's **error handling**, which uses no exceptions at all. Instead, failure and absence are represented as *values* — the `Result` and `Option` enums — that you handle with pattern matching. This is a deliberate design that makes error handling *explicit and unavoidable*, and it's a highlight of the language once you get used to it. This final post of the module covers `Option`, `Result`, the `?` operator, and why no-exceptions is a feature.

## No exceptions: errors as values

Most languages handle errors with **exceptions** — an error is *thrown*, unwinds the stack, and is caught somewhere (or crashes the program if not). Rust rejects this entirely: **there are no exceptions.** Instead, a function that can fail *returns* its error as part of its return value, using an enum. The caller then *must* deal with that return value — there's no invisible throwing that skips past the caller.

This is a significant philosophical choice, and its consequence is the whole point: **you cannot ignore an error, because it's part of the value you have to handle.** With exceptions, it's easy to forget to catch something, and errors propagate invisibly until they crash somewhere far away. In Rust, a fallible function hands you back a value that *encodes* the possibility of failure, and the type system makes you confront it. Errors are ordinary data, handled with ordinary code (pattern matching), not a separate control-flow mechanism. This makes error handling explicit, local, and impossible to accidentally skip.

## Option: representing absence

The simpler of the two is **`Option<T>`**, which represents a value that might be *absent* — Rust's answer to null, without null's dangers. It's an enum with two variants:

```rust
enum Option<T> {
    Some(T),      // a value is present
    None,         // no value
}

fn find_user(id: u32) -> Option<String> {
    if id == 1 { Some(String::from("Alice")) } else { None }
}
```

`Option<T>` is either `Some(value)` or `None` — and because it's an enum, you *must* pattern-match to get at the value, which means you *must* handle the `None` case:

```rust
match find_user(1) {
    Some(name) => println!("Found {}", name),
    None => println!("No user"),
}
```

This is how Rust eliminates the "billion-dollar mistake" of null. In languages with null, any reference might secretly be null, and forgetting to check causes null-pointer crashes. In Rust, there *is* no null — a value that might be absent has type `Option<T>`, and the compiler *forces* you to handle the `None` case (via exhaustive matching from the last post) before you can use the value. You can't accidentally use an absent value, because the type makes absence explicit and handling it mandatory. Absence is in the type, and the compiler won't let you ignore it.

## Result: representing failure

For operations that can *fail* (with an error, not just be absent), Rust uses **`Result<T, E>`**, an enum with a success variant and an error variant:

```rust
enum Result<T, E> {
    Ok(T),        // success, holding the value
    Err(E),       // failure, holding the error
}

fn parse_age(s: &str) -> Result<u32, std::num::ParseIntError> {
    s.parse::<u32>()      // parse returns a Result
}
```

A fallible function returns `Result<T, E>` — either `Ok(value)` on success or `Err(error)` on failure — and again, because it's an enum, the caller *must* handle both cases:

```rust
match parse_age("30") {
    Ok(age) => println!("Age is {}", age),
    Err(e) => println!("Invalid: {}", e),
}
```

This is Rust's exception replacement: instead of throwing, a function *returns* `Result`, and the caller pattern-matches to handle success or failure. The error is right there in the return value, impossible to ignore — you can't use the success value without acknowledging the error case. This makes every fallible operation's failure *visible in its type* (`-> Result<...>` tells you it can fail) and *handled at the call site*, which is a far more honest and local model than exceptions that propagate invisibly.

## The ? operator: ergonomic propagation

Handling every `Result` with a full `match` would be verbose, especially when you just want to *propagate* an error up (the common case). Rust's **`?` operator** makes this ergonomic:

```rust
fn double_age(s: &str) -> Result<u32, std::num::ParseIntError> {
    let age = s.parse::<u32>()?;    // if Err, return it from this function; if Ok, unwrap the value
    Ok(age * 2)
}
```

The `?` operator, applied to a `Result`, does this: if it's `Ok`, unwrap the value and continue; if it's `Err`, *return that error from the current function immediately*. So `?` propagates errors up the call stack concisely — you write the happy path, and `?` handles "on error, bubble it up." This gives you the *convenience* of exception-like propagation (errors flow up without manual matching at every level) while keeping the *explicitness* (the `?` is visible, and the function's return type still declares it can fail). It's the best of both: concise propagation, but errors are still values and still visible in the types. `?` is what makes Rust's no-exceptions error handling ergonomic rather than tedious — you handle errors where it matters and propagate them with a single character elsewhere.

## Why no-exceptions is a feature

Rust's error handling feels heavier than exceptions at first (you handle `Result` everywhere), so it's worth being clear on why it's a strength:

- **You cannot forget to handle errors** — because failure is in the return type and the compiler enforces handling it, the "forgot to catch an exception" bug is impossible. Every fallible operation's failure is confronted, which makes Rust programs robust.
- **Errors are visible in types** — a function's signature (`-> Result<T, E>`) tells you it can fail, and `Option<T>` tells you a value might be absent. Fallibility and absence are documented in the types, not hidden in "this might throw" that you have to know or discover.
- **Handling is local and explicit** — you deal with errors at the call site (or explicitly propagate with `?`), so control flow is clear — no invisible stack unwinding to somewhere distant.
- **It's built on the enum/matching foundation** — `Option` and `Result` are just enums (last post), handled by pattern matching, so error handling uses the same mechanisms as the rest of the language rather than a separate exception system. Errors are ordinary values handled by ordinary code.

Rust reserves actual crashing (`panic!`) for *unrecoverable* situations (bugs, invariant violations) — genuine errors that a caller might handle use `Result`, and only truly unrecoverable conditions panic. So the model is: expected, recoverable failures are `Result`/`Option` values you handle; unrecoverable bugs panic. This distinction — recoverable errors as values, unrecoverable as panics — is cleaner than exceptions conflating both. Once you've worked with it, the explicitness feels like a strength: you always know what can fail, and you always handle it.

## Module 1 complete

This closes the foundational module. You now have Rust's core: the toolchain (Cargo), variables and types (immutability by default), the ownership trio (**ownership**, **borrowing**, **lifetimes**) that gives memory safety with no GC, data modeling (**structs, enums, pattern matching**), and error handling (**Result, Option, `?`** — no exceptions). Notice how it all connects: ownership makes it safe, enums and matching model data and its cases, and error handling is *built on* enums and matching — the language is remarkably coherent, with each idea reinforcing the others. This is the foundation; later modules build on it (collections, generics, traits, concurrency, and more). But you now understand the *why* of Rust — the safety-without-GC bargain and the ideas that deliver it — which is what makes everything ahead comprehensible rather than mysterious.

## Key takeaways

- Rust has no exceptions: fallible functions *return* their error as part of the value (an enum), so the caller must handle it — errors are ordinary data handled by ordinary code, not invisible throwing, making error handling explicit and impossible to accidentally skip.
- `Option<T>` (Some/None) represents possible absence — Rust's null replacement — and because it's an enum, the compiler forces you to handle the `None` case before using the value, eliminating null-pointer bugs (absence is in the type).
- `Result<T, E>` (Ok/Err) represents possible failure — the exception replacement — and the caller must handle both success and error, making every fallible operation's failure visible in its return type and handled at the call site.
- The `?` operator makes propagation ergonomic: on `Ok` it unwraps and continues, on `Err` it returns the error from the current function — giving exception-like concise propagation while keeping errors as visible values in the types.
- No-exceptions is a feature: you can't forget to handle errors (compiler-enforced), fallibility/absence are visible in types, handling is local and explicit, and it's built on the same enum/pattern-matching foundation — with `panic!` reserved for unrecoverable bugs, cleanly separating recoverable errors (values) from unrecoverable ones (panics).

## Further reading

- [Structs, enums, and pattern matching (previous post)](/blog/posts/rust-07-structs-enums-pattern-matching.html)
- [The Rust Book — error handling](https://doc.rust-lang.org/book/ch09-00-error-handling.html)
- [Why Rust? — start of the series](/blog/posts/rust-01-why-rust.html)
