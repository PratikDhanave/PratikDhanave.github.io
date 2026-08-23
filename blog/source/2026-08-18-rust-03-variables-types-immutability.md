# Variables, Types, and Immutability by Default

*In most languages, variables vary — that's the default, and you opt into constancy. Rust flips it: variables are immutable unless you say otherwise. That one inverted default, plus a strong static type system with inference, quietly shapes how Rust code is written and prevents a whole class of bugs before you meet ownership.*

Before the hard ideas, the everyday ones: **variables**, **types**, and Rust's distinctive **immutability by default**. These are where you first feel Rust's personality — a strong static type system that mostly stays out of your way via inference, and a default that makes you *opt into* mutability. This post covers the basics you'll use in every program, and the design choices behind them that foreshadow Rust's safety focus.

## Immutability by default

The first surprise: in Rust, **variables are immutable by default.** When you bind a value with `let`, you can't reassign it unless you explicitly opt into mutability with `mut`:

```rust
let x = 5;
// x = 6;        // ERROR: cannot assign twice to immutable variable `x`

let mut y = 5;
y = 6;           // OK: y is mutable
```

This inverts the default of most languages, where variables are mutable and you opt into constancy (with `const`/`final`). Rust's reasoning is that **immutability is safer and should be the default** — an immutable value can't be changed unexpectedly, which eliminates a class of bugs (accidental mutation) and makes code easier to reason about (you know a `let x` binding won't change). You *can* have mutability — you just have to ask for it with `mut`, which makes mutation *visible and intentional* rather than the silent default.

This connects to Rust's whole philosophy: make the safe thing the default and the potentially-dangerous thing explicit. Immutability by default means that when you *do* see `mut`, it signals "this changes" — a useful signal — and that most of your values are safely constant. It's a small thing that shapes how Rust reads: mutation is marked, so you can trust the unmarked. (It also interacts with ownership and concurrency later — immutable data is easier to share safely.)

A related concept is **shadowing** — you can declare a new variable with the same name, which *shadows* the old one (this isn't mutation; it's a new binding):

```rust
let x = 5;
let x = x + 1;      // a new x, shadowing the old; x is now 6
let x = x * 2;      // another new x; x is now 12
```

Shadowing lets you transform a value through a sequence of immutable bindings (even changing its type), which is idiomatic Rust — you get the convenience of "reusing a name" without giving up immutability. It's distinct from `mut`: shadowing creates new bindings, `mut` allows reassigning one binding.

## A strong static type system, with inference

Rust is **statically and strongly typed** — every value has a type known at compile time, and the compiler checks types rigorously (no implicit surprising conversions). But — crucially for ergonomics — Rust has strong **type inference**, so you usually don't have to write types explicitly; the compiler figures them out:

```rust
let x = 5;              // inferred as i32 (the default integer type)
let name = "Rust";      // inferred as &str
let pi = 3.14;          // inferred as f64

let count: u32 = 10;    // explicit type annotation when you want or need it
```

So Rust gives you the safety of static typing (types checked at compile time, catching type errors before running) with much of the *convenience* of dynamic typing (you rarely write types, because inference handles it). You add explicit type annotations when the compiler needs help or when you want to be specific (e.g. choosing a particular integer size). This combination — strong static types, inferred — is a sweet spot: bugs caught at compile time, without the verbosity of annotating everything.

## The core types

Rust's basic types are what you'd expect from a systems language, with an emphasis on being *explicit about size*:

- **Integers** — signed (`i8`, `i16`, `i32`, `i64`, `i128`, `isize`) and unsigned (`u8`, `u16`, `u32`, `u64`, `u128`, `usize`), with the number being the bit width. `i32` is the default. Being explicit about integer size is a systems-language trait — you control memory layout and range.
- **Floats** — `f32` and `f64` (`f64` is the default).
- **Boolean** — `bool` (`true`/`false`).
- **Character** — `char`, a Unicode scalar value (four bytes, not one byte — a Rust `char` is a full Unicode character, not an ASCII byte).
- **Compound types** — **tuples** (`(i32, f64, char)` — fixed-size groups of possibly-different types) and **arrays** (`[i32; 5]` — fixed-size, same type). (Growable collections like `Vec` and strings come later.)

Two Rust characteristics show up here. First, **explicit sizing** — you choose your integer/float sizes, reflecting systems-programming control over memory. Second, **no implicit conversions** — Rust won't silently convert between types (e.g. `i32` to `i64`); you convert explicitly (with `as` or conversions), which prevents a class of subtle bugs from surprising coercions. Rust is deliberately explicit about types, consistent with its "make things visible" philosophy.

## Functions and basic flow

Rounding out the basics, functions and control flow are conventional but with Rust touches:

```rust
fn add(a: i32, b: i32) -> i32 {
    a + b            // no semicolon: this is the return expression
}

fn main() {
    let n = add(2, 3);
    if n > 4 {
        println!("big");
    } else {
        println!("small");
    }
}
```

- **Function signatures require type annotations** — parameters and return types are always explicit (`a: i32`, `-> i32`), even though local variables use inference. This is deliberate: function signatures are contracts, so being explicit there aids clarity and lets inference work within the body.
- **Expressions vs statements** — Rust is expression-oriented: the last expression in a block (with *no* semicolon) is its value. `a + b` with no semicolon *returns* it; adding a semicolon would make it a statement returning nothing. This matters and trips up newcomers — a trailing semicolon changes meaning. `if` is also an expression (it can produce a value), which is idiomatic Rust.

These basics — immutability by default, inferred static types, explicit sizing, expression-orientation — are the everyday texture of Rust, and each reflects the language's themes of safety and explicitness. With them in hand, the next post reaches Rust's defining idea, the one everything has been building toward: ownership.

## Key takeaways

- Rust makes variables immutable by default (`let x = 5` can't be reassigned); you opt into mutability with `mut` — inverting most languages' default so that mutation is visible and intentional, and unmarked values can be trusted not to change.
- Shadowing (re-declaring a name with `let`) creates a new immutable binding rather than mutating, letting you transform values (even changing type) through a sequence of immutable bindings — distinct from `mut`.
- Rust is strongly and statically typed with strong type inference, giving compile-time type safety with the convenience of rarely writing types; add explicit annotations when needed (e.g. a specific integer size).
- Core types emphasize explicit sizing (integers i8–i128/isize, unsigned u8–u128/usize, floats f32/f64), a Unicode `char`, and compound tuples/arrays — with no implicit type conversions (you convert explicitly), preventing surprising-coercion bugs.
- Functions require explicit parameter and return types (signatures are contracts) while bodies use inference, and Rust is expression-oriented: a block's last expression *without* a semicolon is its value (a trailing semicolon changes the meaning) — `if` is an expression too.

## Further reading

- [Getting started: Cargo and the toolchain (previous post)](/blog/posts/rust-02-cargo-and-toolchain.html)
- [The Rust Book — common programming concepts](https://doc.rust-lang.org/book/ch03-00-common-programming-concepts.html)
- [Road Go Ever On — the Go curriculum, for comparison](/blog/series/road-go-ever-on/)
