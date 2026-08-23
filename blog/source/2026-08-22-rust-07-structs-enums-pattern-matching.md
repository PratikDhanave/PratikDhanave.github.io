# Structs, Enums, and Pattern Matching

*Rust's enums are not the feeble named-constants of other languages — they're full algebraic data types that can hold data, and combined with pattern matching they become one of Rust's most loved features. Together with structs, they're how you model your domain, and the compiler makes sure you handle every case.*

Having covered the ownership trio, we turn to how you *structure data* in Rust: **structs** (grouping related data), **enums** (a type that's one of several variants — far more powerful than most languages' enums), and **pattern matching** (destructuring and branching on that data exhaustively). This trio is how you model a domain in Rust, and enums-plus-pattern-matching is a genuine highlight of the language. This post covers all three and why they work so well together.

## Structs: grouping data

A **struct** groups related data into a named type — the familiar record/object idea:

```rust
struct User {
    name: String,
    age: u32,
    active: bool,
}

let u = User {
    name: String::from("Alice"),
    age: 30,
    active: true,
};
println!("{} is {}", u.name, u.age);
```

Structs are how you build up domain types from the basic types — a `User` bundles a name, age, and active flag into one coherent type. Rust structs come in a few forms (named-field structs as above, tuple structs like `struct Point(i32, i32)`, and unit structs with no fields), and you add behavior to them with `impl` blocks that define methods:

```rust
impl User {
    fn greet(&self) -> String {
        format!("Hi, {}", self.name)     // &self borrows the struct (from the borrowing post)
    }
}
```

Methods take `&self` (borrowing the struct immutably), `&mut self` (borrowing mutably to modify it), or `self` (taking ownership) — the ownership and borrowing rules from earlier posts, applied to methods. Structs are conventional and comfortable; the more distinctive Rust data type is the enum.

## Enums: far more than named constants

In many languages, an enum is just a set of named integer constants. Rust's **enum** is far more powerful: it's a type that can be *one of several variants*, and **each variant can hold data** — making it a true *algebraic data type* (a "sum type"):

```rust
enum Shape {
    Circle(f64),                 // holds a radius
    Rectangle(f64, f64),         // holds width and height
    Point,                       // holds nothing
}

let s = Shape::Circle(2.0);
```

This is the key idea: a `Shape` is *either* a `Circle` (with a radius) *or* a `Rectangle` (with width and height) *or* a `Point` (with no data) — one type representing a fixed set of possibilities, each carrying its own relevant data. This is enormously expressive: you can model "a value that is one of these specific cases, each with its own data" directly in the type system. Two of Rust's most important types are enums — `Option` and `Result` (the error-handling post) — and enums are how you model domains precisely (a state machine's states, a message's kinds, a value that might be absent). If you come from languages with weak enums, Rust's enums are a revelation: they let the type system express "one of these alternatives" exactly.

## Pattern matching: handling every case

Enums come alive with **pattern matching** via `match` — Rust's powerful branching construct that lets you match on which variant a value is *and destructure its data* in one step:

```rust
fn area(s: &Shape) -> f64 {
    match s {
        Shape::Circle(r) => 3.14159 * r * r,
        Shape::Rectangle(w, h) => w * h,
        Shape::Point => 0.0,
    }
}
```

`match` checks which variant `s` is and *binds its data* to names (`r` for the circle's radius, `w` and `h` for the rectangle's dimensions) for use in that branch — matching and destructuring together. This is far more powerful than a switch/if-else chain, because it *extracts the data* while branching. But the feature that makes it beloved is **exhaustiveness**:

> **`match` must handle every possible variant — the compiler enforces it.**

If you forget a case (say you add a `Triangle` variant to `Shape` but don't handle it in a `match`), the code *doesn't compile.* The compiler checks that your `match` covers every variant, so you can never silently forget a case. This is a genuine superpower: it means adding a new enum variant surfaces *every* place that needs updating (they stop compiling until you handle the new case), turning "did I handle this everywhere?" from a manual audit into a compile-time guarantee. Exhaustive matching is one of Rust's most-loved features, and it's why enums plus `match` are such a powerful combination — the type system ensures you handle all the possibilities you modeled. (For cases where you genuinely want a catch-all, `_` matches anything, but you opt into that explicitly rather than forgetting.)

## Why this combination is so powerful

Structs, enums, and pattern matching together give Rust a modeling power worth appreciating, because it's a highlight of the language:

- **Model exactly what's possible** — structs group related data; enums express "one of these specific alternatives, each with its data." Together they let you model a domain *precisely*, making illegal states hard to represent (a value that's "one of these" genuinely can only be one of those).
- **Handle every case, guaranteed** — exhaustive `match` means the compiler ensures you deal with every possibility your enums express. You model the possibilities in the type, and the compiler makes you handle them all — a powerful safety property that catches whole classes of "forgot a case" bugs.
- **Destructure elegantly** — pattern matching extracts data while branching, so working with structured data is concise and clear rather than a series of accessors and conditionals.

This "make illegal states unrepresentable, then handle every legal state exhaustively" is a distinctively powerful way to write correct programs, and it's why Rust programmers reach for enums and `match` constantly. It also sets up the next post directly: Rust's error handling (`Result` and `Option`) is built *entirely* on enums and pattern matching — errors and absence are just enum variants you `match` on, which is why Rust needs no exceptions. The data-modeling trio you've just learned is the foundation for how Rust handles errors.

## Key takeaways

- Structs group related data into named types (with named-field, tuple, and unit forms) and gain behavior via `impl` methods that take `&self`, `&mut self`, or `self` — the ownership/borrowing rules applied to methods.
- Rust enums are far more than named constants: an enum is a type that's *one of several variants, each able to hold its own data* (an algebraic/sum type), letting you model "a value that is one of these specific cases" directly in the type system.
- Pattern matching with `match` branches on which variant a value is *and destructures its data* in one step (binding the variant's data to names), far more powerful than switch/if-else because it extracts data while branching.
- `match` is exhaustive — the compiler requires every variant be handled, so you can never silently forget a case, and adding a new enum variant makes every unhandled `match` fail to compile (turning "did I handle this everywhere?" into a compile-time guarantee) — one of Rust's most-loved features.
- Together, structs + enums + exhaustive matching let you model exactly what's possible (making illegal states hard to represent) and handle every case with compiler enforcement — and this trio is the direct foundation for Rust's exception-free error handling (Result/Option) in the next post.

## Further reading

- [Lifetimes (previous post)](/blog/posts/rust-06-lifetimes.html)
- [The Rust Book — enums and pattern matching](https://doc.rust-lang.org/book/ch06-00-enums.html)
- [Road Go Ever On — how Go models data, for comparison](/blog/series/road-go-ever-on/)
