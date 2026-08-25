# Modules, Crates, and Project Structure

*As a program grows past one file, you need a way to organize it — to group related code, control what's public, and pull in libraries. Rust's module system does this with a clear hierarchy and privacy-by-default, and understanding crates, modules, and paths is what lets your projects scale beyond a single main.rs. This closes Module 2.*

Module 2 covered the building blocks — collections, generics, traits, closures, iterators, smart pointers. This final post covers how to *organize* code as it grows: Rust's **module system** (crates, modules, paths, and visibility). It's the practical knowledge that takes you from a single `main.rs` to a structured, maintainable project — and it rounds out the everyday Rust you need to build real programs. This post covers crates, modules, paths, `use`, and privacy.

## Crates: the compilation unit

From the Cargo post (Module 1), a **crate** is Rust's unit of compilation and distribution — a library or executable. Two kinds:

- **Binary crate** — an executable, with a `main` function (your application). `src/main.rs` is the default binary crate root.
- **Library crate** — a reusable library, no `main`, exposing functionality for other crates to use. `src/lib.rs` is the default library crate root.

A **package** (what `cargo new` creates) contains one or more crates plus a `Cargo.toml`. Your dependencies (from crates.io) are library crates your package uses. So the hierarchy is: a package holds crates, a crate is the compilation unit, and — *within* a crate — you organize code into **modules**. Understanding this nesting (package → crate → modules) is the frame for everything below.

## Modules: organizing within a crate

**Modules** organize code *within* a crate — grouping related items (functions, structs, traits) into a namespace and controlling their visibility. You declare a module with `mod`:

```rust
mod network {
    pub fn connect() { /* ... */ }      // pub = public, callable outside the module

    fn helper() { /* ... */ }           // private to the module (default)

    pub mod client {                    // nested module
        pub fn request() { /* ... */ }
    }
}

fn main() {
    network::connect();                 // path to the module's item
    network::client::request();         // path through nested modules
}
```

Modules form a *tree* — modules can nest inside modules — giving your crate a hierarchical namespace. This is how you group related code (a `network` module, an `auth` module, a `db` module) and keep the crate organized rather than one giant flat file. As a project grows, modules can live in separate files/directories: `mod network;` (without a body) tells Rust to load the module from `network.rs` or `network/mod.rs`, so your module tree maps onto your file structure. This is how you split a crate across many files while keeping a coherent module hierarchy.

## Privacy: private by default

A defining Rust choice, consistent with its safety-and-explicitness philosophy: **items are private by default.** A function, struct, field, or module is only accessible within its own module (and descendants) *unless* you mark it `pub` (public):

- **Default (private)** — accessible only within the defining module and its child modules. This is the default for everything.
- **`pub`** — makes an item accessible from outside its module (to parent modules and, for a library crate, to external users).
- **Struct fields are individually private** — a `pub struct` can still have private fields, so you expose the type but control access to its internals (encapsulation).

Private-by-default is deliberate: it means your module's internals are hidden unless you *choose* to expose them, so a module presents a controlled public interface and hides its implementation. This is encapsulation enforced by the language — you opt into what's public, rather than everything being public unless hidden. For library crates especially, `pub` defines your API surface: what you mark `pub` is your public contract; everything else is free to change. This "expose deliberately, hide by default" is good software design, built into Rust's module system.

## Paths and use: referring to items

To use an item, you refer to it by its **path** through the module tree — like a filesystem path, but with `::`:

- **Absolute path** — from the crate root: `crate::network::client::request()`.
- **Relative path** — from the current module: `network::connect()`, or `super::` for the parent module, `self::` for the current one.

Writing full paths everywhere is verbose, so the **`use`** keyword brings an item into scope so you can refer to it by a short name:

```rust
use std::collections::HashMap;         // now write HashMap, not std::collections::HashMap
use network::client::request;

fn main() {
    let map = HashMap::new();          // short name, thanks to `use`
    request();
}
```

`use` is what you saw in earlier posts (`use std::collections::HashMap;`) — it imports a path into scope. You can `use` items from the standard library, from dependency crates, or from your own modules. Idiomatically, you `use` the *parent module* for functions (`use network::client;` then `client::request()`) and the *item directly* for types (`use ...::HashMap;`), which keeps call sites readable while showing where functions come from. `pub use` (re-exporting) lets a crate expose items from deep in its tree at a convenient top-level path — shaping a clean public API.

## Structuring a real project

Putting it together, a growing Rust project is organized like this:

```text
my_app/
├── Cargo.toml           # package manifest + dependencies
└── src/
    ├── main.rs          # binary crate root (or lib.rs for a library)
    ├── network.rs       # a module (mod network;)
    ├── auth/            # a module with submodules
    │   ├── mod.rs       #   (or auth.rs) — the auth module
    │   └── tokens.rs    #   a submodule (mod tokens;)
    └── db.rs            # another module
```

- Split code into **modules by responsibility** (network, auth, db), each in its own file, forming a module tree that maps to the file structure.
- Mark the intended interface **`pub`**, keeping implementation details private — each module exposes a controlled surface.
- Use **`use`** to bring dependencies and your own items into scope readably.
- For anything reusable, put it in a **library crate** (`lib.rs`) that a thin binary crate (`main.rs`) drives — a common, clean structure that also makes the library independently testable.

This is how Rust projects scale from a single file to large, maintainable codebases: a clear package → crate → module hierarchy, privacy by default defining clean interfaces, and paths/`use` tying it together. It's not glamorous, but it's what makes real Rust programs organized rather than sprawling.

## Module 2 complete

This closes Module 2. You now have the everyday Rust toolkit built on Module 1's foundations: **collections** (Vec/String/HashMap), **generics** (code over many types, zero-cost), **traits** (shared behavior, Rust's abstraction core), **trait objects** (dynamic dispatch for heterogeneous/runtime cases), **closures** (captured environment, ownership-aware), **iterators** (lazy, composable, zero-cost), **smart pointers** (Box/Rc/RefCell for heap, sharing, interior mutability), and now the **module system** to organize it all. Together with Module 1, you can now write real, idiomatic, well-organized Rust programs — abstractions that are safe (ownership) and free (zero-cost), composed into structured projects. Later modules build further (concurrency, async, testing, macros, and more), but you now command the core of the language: the safety of Module 1 and the abstraction and organization of Module 2.

## Key takeaways

- The hierarchy is package → crate → modules: a package (from `cargo new`) holds crates; a crate is the compilation unit (binary with `main`, or library `lib.rs`); and modules organize code *within* a crate — dependencies are library crates your package uses.
- Modules (`mod`) group related items into a namespaced tree, controlling organization and visibility; `mod name;` (no body) loads the module from `name.rs`/`name/mod.rs`, mapping the module tree onto your file structure so a crate can span many files coherently.
- Items are private by default and made accessible with `pub` (struct fields are individually private too) — enforcing encapsulation: modules expose a controlled public interface and hide internals, and for libraries `pub` defines your API contract.
- Items are referred to by paths (`crate::...` absolute, or relative with `super::`/`self::`) through the module tree; `use` brings a path into scope for a short name (idiomatically parent-module for functions, item directly for types), and `pub use` re-exports to shape a clean public API.
- Real projects split code into modules by responsibility (each in its own file), mark the interface `pub`, use `use` for readable imports, and put reusable logic in a library crate driven by a thin binary — scaling from one file to large, maintainable, independently-testable codebases; this completes Module 2's everyday Rust toolkit.

## Further reading

- [Smart pointers: Box, Rc, and RefCell (previous post)](/blog/posts/rust-15-smart-pointers.html)
- [The Rust Book — managing growing projects with packages, crates, and modules](https://doc.rust-lang.org/book/ch07-00-managing-growing-projects-with-packages-crates-and-modules.html)
- [Getting started: Cargo and the toolchain (Module 1)](/blog/posts/rust-02-cargo-and-toolchain.html)
