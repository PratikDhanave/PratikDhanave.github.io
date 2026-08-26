# Testing in Rust

*Most languages treat testing as an afterthought — a separate framework you bolt on, a separate directory, a separate mental mode. Rust treats it as a first-class, built-in feature: testing is part of the language and its tooling, you write tests right next to the code they test, and `cargo test` just works. This tight integration, combined with Rust's culture of correctness, makes testing in Rust unusually pleasant and encourages a habit that pairs perfectly with the compiler's guarantees.*

This post covers **testing** in Rust — a first-class, built-in feature. It covers writing tests with the `#[test]` attribute, the assertion macros, running tests with `cargo test`, and the distinction between unit and integration tests. Rust's testing is integrated into the language and Cargo (from Module 1), making it low-friction and encouraging good testing habits. Combined with the compiler's guarantees, tests complete Rust's correctness story.

## Writing tests

A Rust test is just a function marked with the `#[test]` attribute. It passes if it runs without panicking, fails if it panics:

```rust
// A function to test.
fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adds_two_numbers() {
        assert_eq!(add(2, 3), 5);
    }

    #[test]
    fn adds_negatives() {
        assert_eq!(add(-1, -1), -2);
    }
}
```

- **`#[test]` marks a test function.** Any function annotated with `#[test]` is a test — `cargo test` finds and runs it. A test *passes* if it completes without *panicking*, and *fails* if it panics (e.g. from a failed assertion). That's the whole model: tests are functions that panic on failure. Simple and built-in.
- **Tests live with the code.** Unit tests conventionally live in the *same file* as the code they test, in a module marked `#[cfg(test)]` (so it's *only compiled during testing*, not in the normal build). This keeps tests *next to* the code, and `use super::*;` brings the module's items into the test module. Tests alongside code — low friction, easy to keep in sync. `#[cfg(test)]` means test code adds nothing to your release binary.
- **Testing is built in.** No external test framework is needed — `#[test]`, the assertion macros, and `cargo test` are *part of Rust and Cargo*. Testing is a first-class language feature, not a bolt-on. This built-in support makes testing low-friction and standard in Rust. It's there by default, part of the toolchain.

A Rust test is a `#[test]`-annotated function that passes if it doesn't panic and fails if it does; unit tests live alongside the code in a `#[cfg(test)]` module (compiled only for tests), and testing is built into the language and Cargo — no external framework. Tests express expectations through assertion macros.

## Assertion macros

Rust provides **assertion macros** to check conditions in tests — a test fails (panics) if an assertion fails:

- **`assert!(condition)` — check a boolean.** `assert!(expr)` passes if `expr` is `true`, and *panics* (failing the test) if it's `false`. Use it for boolean conditions. `assert!(result.is_ok())` checks something is true.
- **`assert_eq!(a, b)` and `assert_ne!(a, b)` — check equality.** `assert_eq!(a, b)` passes if `a == b` and panics if not — *and* helpfully *prints both values* on failure (so you see what you got vs expected). `assert_ne!` checks *inequality*. These are the most common assertions, and their failure output (showing the actual values) makes debugging failures easy. `assert_eq!` is the workhorse.

```rust
#[test]
fn assertions_demo() {
    let result = add(2, 2);
    assert_eq!(result, 4);              // fails and prints values if not equal
    assert!(result > 0);               // fails if the condition is false
    assert_ne!(result, 5);             // fails if equal
    assert_eq!(result, 4, "add(2,2) should be 4, got {result}"); // custom message
}
```

- **Custom failure messages.** You can add a *custom message* (with format args) as extra arguments to any assertion — shown on failure, to explain what went wrong. This makes test failures self-explanatory. Helpful context on failure.
- **Testing that code panics.** For code that *should* panic, `#[should_panic]` on a test asserts the test *does* panic (optionally checking the panic message). This tests error/panic behavior. And tests can *return `Result`* (using `?`), failing if they return `Err` — convenient for testing fallible operations (the error-handling from Module 1). Multiple ways to assert, fitting different needs.

Rust's assertion macros — `assert!` (boolean), `assert_eq!`/`assert_ne!` (equality, printing values on failure), with optional custom messages — express test expectations, and `#[should_panic]` and `Result`-returning tests handle panic/error cases. These make writing clear, debuggable tests easy. Running them is equally simple.

## Running tests with cargo test

`cargo test` (from Cargo, Module 1) builds and runs all your tests — one command, integrated into the tooling:

- **`cargo test` runs everything.** Running `cargo test` compiles your code in test mode and runs *all* `#[test]` functions, reporting which passed and failed (with output for failures — the assertion values and messages). One command runs your whole test suite. Integrated, zero-config testing.
- **It runs tests in parallel by default.** `cargo test` runs tests *in parallel* (across threads) by default for speed — so tests should be *independent* (not depend on shared state or order). This is fast but means you write tests that don't interfere. (You can force single-threaded with a flag if needed.) Fast by default, so keep tests independent.
- **Filtering and options.** You can run *specific* tests by name (`cargo test <name>` runs tests matching the name — useful when iterating on one test) and control output/behavior with flags. This makes running a focused subset easy during development. Run one test or all, as needed.
- **It's part of the workflow.** Because `cargo test` is built into Cargo and low-friction, running tests is a natural, frequent part of Rust development (and easy to run in CI). Testing being one command in the standard tool encourages testing as a habit. Tests are easy to run, so they get run.

`cargo test` runs your whole test suite with one integrated command — compiling in test mode, running all `#[test]` functions in parallel (so keep tests independent), reporting pass/fail with helpful failure output, and supporting name-based filtering. Its low friction makes testing a natural habit. Beyond unit tests, Rust distinguishes integration tests.

## Unit vs integration tests

Rust distinguishes **unit tests** (testing internals, alongside the code) from **integration tests** (testing the public API, from outside) — a useful separation:

- **Unit tests: internal, alongside the code.** *Unit tests* test *individual pieces* (functions, modules) — often including *private* internals — and live *in the same file* as the code (in the `#[cfg(test)]` module, as shown). They can access private items (they're inside the module). Unit tests verify the *internals* work, close to the code. Small, focused, inside the module.
- **Integration tests: external, testing the public API.** *Integration tests* live in a separate `tests/` directory (each file is a separate test crate) and test your library *from the outside* — using only its *public API*, as a real user would. They verify that the pieces *work together* through the public interface. Integration tests test the library as a whole, externally. They exercise the public API like a consumer.
- **The distinction reflects scope.** Unit tests (internal, fine-grained, can test private code) verify individual components; integration tests (external, public-API) verify the whole works together as users see it. Both are valuable — unit tests for detailed internal correctness, integration tests for end-to-end public behavior. Rust's structure (in-file unit tests, `tests/` integration tests) supports both cleanly. Test internals *and* the public whole. `cargo test` runs both.
- **Doc tests too.** A distinctive Rust feature: *documentation tests* — code examples *in your doc comments* are *run as tests* by `cargo test`, ensuring your documentation examples actually work (and stay correct). This keeps docs accurate and adds tests for free. Doc tests are a nice Rust bonus (tested documentation). Your examples can't rot silently.

Rust distinguishes unit tests (internal, alongside the code, can test private items — for detailed component correctness) from integration tests (in `tests/`, external, testing the public API as a user would — for end-to-end behavior), plus doc tests (examples in doc comments run as tests). `cargo test` runs all of these, giving comprehensive, low-friction testing. Combined with the compiler's guarantees, tests complete Rust's correctness story. Next: error-handling libraries (anyhow and thiserror).

## Key takeaways

- A Rust test is a function marked `#[test]` that passes if it doesn't panic and fails if it does; unit tests conventionally live *alongside* the code in a `#[cfg(test)]` module (compiled only during testing, so it adds nothing to release builds), and testing is a first-class, built-in feature of the language and Cargo — no external framework.
- Assertion macros express expectations: `assert!` (boolean), `assert_eq!`/`assert_ne!` (equality/inequality, helpfully printing both values on failure), all supporting custom failure messages — plus `#[should_panic]` for code that should panic and `Result`-returning tests (using `?`) for fallible operations.
- `cargo test` runs the whole suite with one integrated command — compiling in test mode, running all `#[test]` functions *in parallel* (so keep tests independent), reporting pass/fail with helpful output, and supporting name-based filtering — its low friction making testing a natural, frequent habit (and easy in CI).
- Rust distinguishes unit tests (internal, alongside the code, can access private items — for detailed component correctness) from integration tests (in a separate `tests/` directory, external, using only the public API as a real user would — for end-to-end behavior), and both are valuable.
- Rust also runs *doc tests* — code examples in doc comments are executed as tests by `cargo test` — keeping documentation examples correct (tested docs, for free); combined with the compiler's compile-time guarantees, this integrated, low-friction testing completes Rust's correctness story.

## Further reading

- [The Rust Book — Writing Automated Tests](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [Rust: Cargo and the toolchain (Module 1)](/blog/posts/rust-02-cargo-and-toolchain.html)
- [Async and await (previous post)](/blog/posts/rust-21-async-await.html)
