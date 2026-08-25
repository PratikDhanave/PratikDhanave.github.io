# Closures

*Closures are anonymous functions that can capture variables from around them — and in Rust, the ownership model makes "capture" a precise, three-way question: does the closure borrow, mutably borrow, or take ownership of what it captures? Understanding that is what makes closures (and the iterators that depend on them) click.*

Closures are functions you write inline that can *capture* their surrounding environment, and they're everywhere in idiomatic Rust — especially with iterators (the next post). But Rust's ownership model makes closures more interesting than in most languages: *how* a closure captures a variable (by reference, by mutable reference, or by taking ownership) matters and is governed by the same ownership rules from Module 1. This post covers closure syntax, the three capture modes, the `Fn` traits, and why closures and ownership interact.

## What a closure is

A **closure** is an anonymous function you can define inline and that can *capture* variables from its enclosing scope. The syntax uses `|params| body`:

```rust
let x = 10;
let add_x = |n| n + x;        // captures x from the environment
println!("{}", add_x(5));     // 15

// closures are often passed to other functions:
let mut nums = vec![3, 1, 2];
nums.sort_by(|a, b| a.cmp(b));   // an inline closure as the comparator
```

The defining feature — capturing the environment — is what distinguishes a closure from a plain function. `add_x` uses `x` from the surrounding scope without `x` being a parameter; the closure "closes over" `x`. This is why closures are so useful for short, inline behavior passed to other functions (sorting, filtering, mapping, callbacks) — they can reference the local context. Rust infers closure parameter and return types (unlike named functions, which require annotations), so closures are concise.

## The three capture modes

Here's where Rust's ownership model makes closures distinctive. When a closure captures a variable, it does so in one of *three* ways, mirroring the ownership/borrowing rules from Module 1:

- **By immutable reference (`&T`)** — the closure only *reads* the captured variable, so it borrows it immutably (many-readers rule). The default when the closure just reads.
- **By mutable reference (`&mut T`)** — the closure *modifies* the captured variable, so it borrows it mutably (one-writer rule).
- **By value (taking ownership)** — the closure *takes ownership* of the captured variable (moves it in). Needed when the closure must own the value — e.g. to return it, or to send it to another thread.

```rust
let s = String::from("hi");

let read = || println!("{}", s);          // borrows s immutably (&)
let mut owned_s = String::from("hey");
let mut modify = || owned_s.push('!');    // borrows owned_s mutably (&mut)

let take = move || println!("owns {}", s);  // `move` forces capture BY VALUE (ownership)
```

Rust *infers* the least-restrictive capture mode the closure needs (immutable borrow if it only reads, mutable if it modifies, by-value only if required). The **`move` keyword** forces capture *by value* — moving captured variables into the closure. This is essential when a closure must *outlive* the current scope or own its data — most importantly for **spawning threads** (a later concurrency topic): a thread's closure must `move` its captures because the thread may run after the current scope ends, so it can't borrow from it. So capture mode isn't arbitrary; it follows directly from ownership — a closure that borrows can't outlive what it borrows (lifetimes, Module 1), while a `move` closure owns its captures and can.

## The Fn traits

Closures are represented by three traits, corresponding to the capture modes — and knowing them lets you *accept* closures as parameters:

- **`Fn`** — closures that capture by immutable reference (only read their captures); can be called multiple times.
- **`FnMut`** — closures that capture by mutable reference (modify their captures); can be called multiple times, mutating each time.
- **`FnOnce`** — closures that capture by value (take ownership) and might consume their captures; can be called *at least once* (possibly only once, if calling consumes a captured value).

These form a hierarchy (every `Fn` is also `FnMut` and `FnOnce`; every `FnMut` is `FnOnce`), reflecting that a closure needing less (just reading) can be used where more is allowed. You use these traits as bounds when a function *accepts* a closure:

```rust
fn apply<F: Fn(i32) -> i32>(f: F, x: i32) -> i32 {
    f(x)                       // accepts any closure that reads its captures
}

fn apply_mut<F: FnMut()>(mut f: F) {
    f(); f();                  // accepts a closure that mutates captures, calls it twice
}
```

So closures connect back to traits (last posts): a function that takes a closure bounds it on `Fn`/`FnMut`/`FnOnce` (via generics for static dispatch, or `Box<dyn Fn>` for dynamic — the trait-object choice from the last post). The trait you require signals how the closure may use its captures. This is how the whole standard library accepts closures — `map`, `filter`, `sort_by`, thread spawning, and more all take `Fn`/`FnMut`/`FnOnce`-bounded parameters. (Closures are also zero-cost: a closure passed to a generic function is monomorphized and inlined like any generic, so closure-heavy code — including iterators — runs fast.)

## Why closures and ownership interact

The deeper point: in many languages closures capture the environment loosely (by reference, garbage-collected), and you rarely think about *how*. In Rust, because there's no garbage collector and ownership is explicit, *how a closure captures* is a real, checked question:

- A closure that **borrows** its captures is tied to their lifetime — it can't outlive them, and the borrow checker enforces this (a closure borrowing a local can't be returned from the function, because the local would be dropped — the dangling-reference rule from Module 1, applied to closures).
- A closure that **`move`s** (takes ownership) owns its captures, so it *can* outlive the scope and be returned, stored, or sent to a thread — but the moved variables are no longer usable outside the closure (move semantics, Module 1).

So closures are another place ownership shows up concretely: the capture mode determines what the closure can *do* (outlive, be returned, be threaded) and follows the same borrow/move rules as everything else. Understanding closures well means understanding their captures in ownership terms — which is exactly the discipline Module 1 built. This matters most for the next post (iterators, which use closures pervasively) and for concurrency (where `move` closures carry data into threads safely). The next post puts closures to work: iterators.

## Key takeaways

- A closure is an anonymous inline function (`|params| body`) that captures variables from its enclosing scope — the capturing is what distinguishes it from a plain function, making closures ideal for short behavior passed to `map`/`filter`/`sort_by`/callbacks; parameter and return types are inferred.
- Rust closures capture in one of three ways, following the ownership rules: by immutable reference (reads only), by mutable reference (modifies), or by value/ownership — Rust infers the least-restrictive mode, and the `move` keyword forces by-value capture.
- `move` is essential when a closure must outlive its scope or own its data — most importantly for spawning threads (the thread's closure can't borrow from a scope that may end first), so it takes ownership of its captures.
- Closures are represented by the `Fn` (reads captures), `FnMut` (mutates captures), and `FnOnce` (consumes captures) traits, forming a hierarchy; functions accept closures by bounding on these (generics for static dispatch, `Box<dyn Fn>` for dynamic), which is how the standard library takes closures — and closures are zero-cost (monomorphized/inlined).
- Because Rust has no GC, *how* a closure captures is a checked question: a borrowing closure is tied to its captures' lifetime (can't outlive them), while a `move` closure owns them (can be returned/stored/threaded, but the moved variables are unusable outside) — closures are another concrete place the ownership rules apply.

## Further reading

- [Trait objects and dynamic dispatch (previous post)](/blog/posts/rust-12-trait-objects.html)
- [The Rust Book — closures](https://doc.rust-lang.org/book/ch13-01-closures.html)
- [Borrowing and references (Module 1) — the rules closures capture by](/blog/posts/rust-05-borrowing-and-references.html)
