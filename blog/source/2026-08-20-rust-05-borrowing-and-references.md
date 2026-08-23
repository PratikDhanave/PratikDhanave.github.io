# Borrowing and References

*If ownership were the whole story, Rust would be exhausting — you'd move values in and out of every function by hand. Borrowing is the release valve: it lets code use a value without taking ownership, governed by one elegant rule that also happens to eliminate data races. Ownership makes Rust safe; borrowing makes it usable.*

The last post established ownership and hinted that moving values everywhere would be painful. **Borrowing** — accessing a value through a **reference** without taking ownership — is Rust's answer, and it's what makes ownership practical. But borrowing has its own rule, and that rule is one of the most consequential in the language: it's what prevents data races and a class of memory bugs. This post covers references, the borrowing rules, and why they matter.

## References: using without owning

A **reference** lets you access a value without owning it — you *borrow* it. You create a reference with `&`, and pass it where you'd otherwise pass the value:

```rust
fn length(s: &String) -> usize {   // borrows s, doesn't take ownership
    s.len()
}

fn main() {
    let s = String::from("hello");
    let n = length(&s);            // pass a reference; ownership stays with s
    println!("{} is {} chars", s, n);   // s is still valid here!
}
```

Contrast this with the last post: passing `s` *by value* would move ownership into the function, leaving `s` invalid afterward. Passing `&s` — a *reference* — lets `length` *use* `s` without taking ownership, so `s` is still valid in `main` after the call. This is borrowing: the function borrows access to the value, uses it, and when the reference goes out of scope, *nothing is freed* (the reference doesn't own the value, so it doesn't drop it). Borrowing is what lets you pass values around freely without the ownership-threading pain — it's the ergonomic complement to ownership.

## Mutable and immutable borrows

There are two kinds of references, and the distinction is central:

- **Immutable reference (`&T`)** — lets you *read* the value but not modify it. You can have *many* immutable references at once (many readers).
- **Mutable reference (`&mut T`)** — lets you *modify* the value. You can have only *one* mutable reference at a time (one writer).

```rust
fn append(s: &mut String) {
    s.push_str(" world");
}

fn main() {
    let mut s = String::from("hello");   // must be mut to borrow mutably
    append(&mut s);                      // mutable borrow
    println!("{}", s);                   // "hello world"
}
```

A mutable reference (`&mut s`) lets the function modify the borrowed value (and the owner must be `mut`). The read/write distinction in the type — `&T` for reading, `&mut T` for writing — makes access intent explicit, consistent with Rust's visibility philosophy. But the interesting part is the *rule* governing how many of each you can have at once.

## The borrowing rule: the heart of it

Here is the rule that defines Rust's borrowing, and one of the most important rules in the language:

> **At any given time, you can have *either* one mutable reference *or* any number of immutable references — but not both.**

In other words: **many readers, or one writer, never both at once.** You can have lots of immutable references (everyone's just reading, which is safe), *or* exactly one mutable reference (one writer, exclusive access), but you cannot have a mutable reference while immutable references exist, nor two mutable references. The compiler enforces this — the **borrow checker** — and code that violates it doesn't compile:

```rust
let mut s = String::from("hi");
let r1 = &s;         // immutable borrow
let r2 = &s;         // another immutable borrow — fine, many readers
// let w = &mut s;   // ERROR: cannot borrow as mutable while immutable borrows exist
println!("{} {}", r1, r2);
```

This rule feels restrictive at first — it's the other half of "fighting the compiler" (with move semantics). But it's preventing real bugs, and understanding *which* bugs makes the rule feel right.

## Why the rule matters: aliasing and races

The borrowing rule prevents two deep classes of bugs, which is why it's worth its strictness:

- **Data races (in concurrency)** — a data race happens when two threads access the same data at once and at least one is writing, with no synchronization. That is *exactly* what the borrowing rule forbids: you can't have a writer (`&mut`) at the same time as any other accessor. So the borrowing rule, applied across threads, makes data races *impossible at compile time* — this is the fearless concurrency from the first post, and it flows directly from this one rule. The rule that makes single-threaded borrowing safe *also* makes concurrent access safe, because both are the same problem: don't let a writer coexist with other accessors.
- **Aliasing bugs (even single-threaded)** — bugs where you modify data through one reference while another reference to it exists, invalidating assumptions the other holds (e.g. modifying a collection while iterating it, invalidating the iterator — a classic bug in other languages). The "no mutable reference while other references exist" rule prevents this: if you can mutate, you have exclusive access, so nothing else holds a stale view.

This is the elegance of Rust's borrowing: **one rule (one writer XOR many readers) simultaneously prevents data races and aliasing bugs**, single-threaded and concurrent, all at compile time. The rule that makes the borrow checker strict is the same rule that gives you fearless concurrency and eliminates a whole category of subtle bugs. Once you see that the rule *is* the data-race prevention (and the aliasing prevention), it stops feeling arbitrary and starts feeling like the point.

## Dangling references: also prevented

Borrowing also prevents **dangling references** — a reference to memory that's been freed (a use-after-free through a reference). The borrow checker ensures a reference never outlives the value it points to:

```rust
// This does NOT compile:
// fn dangle() -> &String {
//     let s = String::from("hi");
//     &s               // ERROR: returns a reference to s, but s is dropped when the function ends
// }
```

If you tried to return a reference to a local value, the value would be dropped when the function ends, leaving the reference dangling — so the compiler rejects it. The borrow checker tracks how long references must be valid versus how long values live, and rejects any reference that could outlive its value. This is the third bug class borrowing eliminates (with data races and aliasing): use-after-free through references, caught at compile time. Making this work in more complex cases requires *lifetimes* — the next post — which is how Rust reasons about how long references are valid.

## Borrowing makes ownership practical

The takeaway: ownership (last post) provides the safety foundation, and borrowing is what makes it *ergonomic and even more powerful*. Borrowing lets you pass and use values without the pain of moving ownership everywhere, and its one rule — one writer XOR many readers — elegantly prevents data races, aliasing bugs, and (with lifetimes) dangling references, all at compile time. The borrow checker enforcing this is the source of much early Rust frustration, but it's also the source of Rust's deepest guarantees: internalize that the rule *is* the safety, and borrowing becomes not a restriction but the mechanism that lets you write concurrent, aliasing-heavy code fearlessly. The next post covers lifetimes, which let the borrow checker reason about references in the general case.

## Key takeaways

- A reference (`&`) lets code borrow — use a value without taking ownership — so passing `&s` (instead of `s`) lets a function use a value while the owner keeps it valid, making ownership ergonomic without threading it through every call.
- There are immutable references (`&T`, read-only, many allowed) and mutable references (`&mut T`, read-write, requiring a `mut` owner), with the read/write intent explicit in the type.
- The borrowing rule is the heart of it: at any time you can have either one mutable reference OR any number of immutable references, never both — many readers XOR one writer — enforced by the borrow checker at compile time.
- That one rule prevents data races (a writer can't coexist with other accessors — so concurrent data races are impossible at compile time, giving fearless concurrency) and aliasing bugs (mutating through one reference while another holds a stale view) — one rule, both bug classes, single-threaded and concurrent.
- Borrowing also prevents dangling references (a reference outliving its value / use-after-free), rejected at compile time — and making this work in general requires lifetimes (next post); borrowing is what makes ownership practical while delivering Rust's deepest safety guarantees.

## Further reading

- [Ownership: Rust's big idea (previous post)](/blog/posts/rust-04-ownership.html)
- [The Rust Book — references and borrowing](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)
- [Distributed Systems / concurrency — why data races are so dangerous](/blog/series/distributed-systems-from-first-principles/)
