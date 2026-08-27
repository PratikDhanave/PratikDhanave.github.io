# Building a Command-Line Application

*Everything so far has been pieces — ownership, traits, error handling, modules. Now we put them together into the kind of thing you'd actually ship: a small command-line application. Building a real program reveals how Rust's features combine in practice — structuring the code, parsing arguments, handling errors gracefully with `Result` and `?`, separating logic from `main` for testability, and returning proper exit codes. It's where the language stops being a set of concepts and becomes a tool for building software.*

This post assembles Module 4's advanced features and the whole curriculum into **building a command-line application** — a small but real Rust program. It covers structuring a CLI app, parsing arguments, error handling (with `Result` and `?`), separating logic from `main` (for testability), and exit codes. Rather than new features, it *applies* what you've learned to a real program — showing how Rust's pieces combine. This is where the language becomes a practical tool.

## Structuring a CLI application

A well-structured CLI app *separates* concerns — argument parsing, the core logic, and error handling — and keeps `main` thin:

```rust
use std::env;
use std::process;

// Configuration parsed from arguments.
struct Config {
    query: String,
    filename: String,
}

impl Config {
    // Parse args into a Config, returning a Result (errors are data).
    fn build(args: &[String]) -> Result<Config, &'static str> {
        if args.len() < 3 {
            return Err("not enough arguments");
        }
        Ok(Config {
            query: args[1].clone(),
            filename: args[2].clone(),
        })
    }
}
```

- **Separate parsing, logic, and errors.** A good CLI structure *separates*: parsing *arguments* into a config (like `Config::build`), the *core logic* (a `run` function — below), and *error handling*. This separation makes the code *clear* and *testable* (you can test the logic separately from `main`). Separate parsing, logic, and errors. Clean structure.
- **Parse arguments into a config type.** Reading arguments (via `std::env::args`) and *parsing* them into a *config struct* (with validation, returning a `Result` — errors as data, Module 1) centralizes argument handling. `Config::build` returns `Result` (handling bad args gracefully). Parse args into a validated config. Errors as `Result`.
- **Keep `main` thin.** `main` should be *thin* — just wiring: parse args, call the logic, handle top-level errors. Keeping `main` minimal (delegating to testable functions) is idiomatic and testable. Thin `main`, logic elsewhere. Delegate from main.

A well-structured CLI app separates argument parsing (into a validated config type, returning `Result`), core logic (a `run` function), and error handling — keeping `main` thin (just wiring). This structure is clear and *testable*. The core logic goes in a `run` function.

## The run function and error handling

The **core logic** goes in a `run` function that returns a `Result` — so errors *propagate* (via `?`) and are handled at the top, gracefully:

```rust
use std::error::Error;
use std::fs;

// Core logic in run(), returning Result so errors propagate with `?`.
fn run(config: Config) -> Result<(), Box<dyn Error>> {
    let contents = fs::read_to_string(&config.filename)?; // `?` propagates errors

    for line in contents.lines() {
        if line.contains(&config.query) {
            println!("{line}");
        }
    }
    Ok(())
}
```

- **Logic in `run`, returning `Result`.** The core logic lives in `run(config) -> Result<(), Box<dyn Error>>` — returning `Result` so *any* error (file read, etc.) *propagates* cleanly (via `?`) rather than panicking. `run` is *separate from `main`* (testable) and *fallible* (returns `Result`). Logic in `run`, returning `Result`. Fallible and testable.
- **`Box<dyn Error>` for flexible errors.** Returning `Box<dyn Error>` (a trait object — Module 2, and the error-handling libraries post) lets `run` return *any* error type (from file I/O, parsing, etc.) — a flexible error type for an application (like `anyhow`). `Box<dyn Error>` allows any error. Flexible error propagation.
- **`?` propagates errors cleanly.** Inside `run`, the `?` operator (Module 1) *propagates* errors up (returning them from `run`) instead of panicking — so errors flow to the top for graceful handling. `?` gives clean error propagation. Errors flow up, not crash.
- **Separation enables testing.** Because `run` is *separate* from `main` and returns `Result` (not printing/exiting itself), you can *test* it (call it, check the result) — the testability payoff of the structure (Module 3's testing). `run` being separate and fallible makes it testable. Test the logic directly.

The core logic goes in a `run` function returning `Result<(), Box<dyn Error>>` (flexible error type) — so errors *propagate* via `?` (cleanly, not panicking) to be handled at the top, and `run` being separate and fallible makes it *testable*. `main` then wires it together with proper error handling and exit codes.

## Wiring main with exit codes

**`main`** ties it together — parsing args, running the logic, and handling errors with proper **exit codes** (so the program behaves correctly as a CLI tool):

```rust
fn main() {
    let args: Vec<String> = env::args().collect();

    // Parse args; on error, print to stderr and exit with a non-zero code.
    let config = Config::build(&args).unwrap_or_else(|err| {
        eprintln!("Problem parsing arguments: {err}");
        process::exit(1);
    });

    // Run the logic; on error, print to stderr and exit non-zero.
    if let Err(e) = run(config) {
        eprintln!("Application error: {e}");
        process::exit(1);
    }
}
```

- **Handle errors at the top, in `main`.** `main` *handles* the errors that `run` and parsing return — deciding what to *do* on error (here: print a message and exit). Top-level error handling belongs in `main` (where you decide how to *respond* to errors). Handle errors at the top. `main` decides the response.
- **Print errors to stderr.** Error messages go to *stderr* (`eprintln!`), not stdout (`println!`) — the Unix convention (stdout for output, stderr for errors — the OS series). Using stderr for errors makes the tool behave correctly (errors don't pollute the output stream). Errors to stderr (`eprintln!`). Correct stream usage.
- **Exit with a proper code.** On error, `main` *exits with a non-zero code* (`process::exit(1)`) — signaling *failure* to the shell/caller (exit 0 = success, non-zero = failure, the Unix convention). Proper exit codes make the tool *scriptable* (other programs can check if it succeeded). Exit non-zero on failure. Scriptable behavior.
- **This makes a well-behaved CLI tool.** Together — parse, run, handle errors to stderr, exit with codes — `main` makes a *well-behaved* command-line tool (proper output/error streams, exit codes) that fits the Unix ecosystem (pipeable, scriptable — the OS series). Well-behaved CLI conventions. Fits the ecosystem.

`main` wires it together — parsing args, running the logic, and handling errors properly (printing to *stderr* via `eprintln!`, exiting with a *non-zero code* on failure) — making a well-behaved CLI tool that fits the Unix ecosystem (correct streams, exit codes, scriptable). This assembles the pieces into a real program.

## Bringing it all together

Building this CLI app *combines* the whole curriculum — showing how Rust's pieces work together in a real program:

- **It uses the whole curriculum.** This small app uses: *ownership/borrowing* (passing `config`, `&str`), *structs* (`Config`), *error handling* (`Result`, `?`, `Box<dyn Error>` — Module 1 & 3), *traits* (`Error` trait object), *iterators* (`.lines()`, `.contains()` — Module 2), *modules* (organizing into files — Module 2), and *testing* (testable `run` — Module 3). A real program *combines* everything. Everything combines in a real program. The pieces work together.
- **The structure is idiomatic.** The pattern — thin `main`, config parsing, a fallible `run`, error handling with proper streams/codes — is *idiomatic* Rust CLI structure (from the Rust Book's own project). Following idiomatic structure makes real Rust programs clear and testable. Idiomatic structure for real programs. The standard shape.
- **Crates make it easier.** In practice, *crates* (from the ecosystem — next post) make CLIs easier: `clap` for argument parsing (robust arg handling), `anyhow`/`thiserror` for errors (Module 3). Real Rust CLIs use crates for the heavy lifting; the *structure* stays the same. Crates handle the heavy lifting. Build on the ecosystem.
- **This is where Rust becomes a tool.** Building a real program is where Rust *stops being concepts and becomes a tool* — you *apply* the features to *build software*. The curriculum's payoff is *building things* (correct, safe, real programs), which this demonstrates. Rust becomes a tool for building. Concepts to software.

Building a command-line application assembles the whole curriculum into a real program — separating parsing (config), core logic (a fallible `run` with `?` and `Box<dyn Error>`), and top-level error handling (`main` with stderr and exit codes) — an idiomatic, testable structure that combines ownership, traits, error handling, iterators, modules, and testing. This is where Rust becomes a tool for building software. Next: the crate ecosystem and tooling.

## Key takeaways

- A well-structured CLI app separates concerns — argument parsing (into a validated `Config` type, returning `Result` so bad args are handled gracefully as data), core logic (a `run` function), and error handling — keeping `main` thin (just wiring: parse, run, handle top-level errors).
- The core logic goes in a `run` function returning `Result<(), Box<dyn Error>>` — a flexible error type (a trait object accepting any error, like `anyhow`) — so errors propagate cleanly via `?` (not panicking) to be handled at the top, and `run` being separate from `main` and fallible makes it *testable*.
- `main` handles errors at the top (deciding how to respond), printing error messages to *stderr* (`eprintln!`, not stdout — the Unix convention) and exiting with a *non-zero code* (`process::exit(1)`) on failure — making a well-behaved, scriptable CLI tool that fits the Unix ecosystem (correct streams, exit codes).
- Building this small app combines the whole curriculum — ownership/borrowing, structs, error handling (`Result`, `?`, `Box<dyn Error>`), traits (the `Error` trait object), iterators (`.lines()`, `.contains()`), modules, and testing (a testable `run`) — showing how Rust's pieces work together in a real program, in idiomatic structure.
- In practice, crates make CLIs easier (`clap` for argument parsing, `anyhow`/`thiserror` for errors) while the structure stays the same — and building a real program is where Rust stops being a set of concepts and becomes a *tool for building software* (correct, safe, real programs), the curriculum's payoff.

## Further reading

- [The Rust Book — An I/O Project: Building a Command Line Program](https://doc.rust-lang.org/book/ch12-00-an-io-project.html)
- [Rust: Error handling with anyhow and thiserror (Module 3)](/blog/posts/rust-23-error-handling-libraries.html)
- [Closures and function pointers, revisited (previous post)](/blog/posts/rust-29-closures-and-function-pointers.html)
