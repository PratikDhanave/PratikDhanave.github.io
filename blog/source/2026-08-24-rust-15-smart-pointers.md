# Smart Pointers: Box, Rc, and RefCell

*Module 1's ownership rules — one owner, borrow-checked references — cover most code. But some data structures genuinely need more: a value on the heap, shared ownership, or mutation through a shared reference. Smart pointers are Rust's escape hatches that provide these while keeping the safety, and knowing the big three is knowing how to model the shapes ownership alone can't.*

Ownership's rules (single owner, one-writer-XOR-many-readers) are strict, and occasionally too strict for a data structure's real shape — a recursive type, a graph where nodes are shared, a value mutated through a shared handle. **Smart pointers** are types that act like pointers but add capabilities, providing controlled ways around the basic rules *without* sacrificing safety. This post covers the three you'll meet most: **`Box<T>`** (heap allocation), **`Rc<T>`** (shared ownership), and **`RefCell<T>`** (interior mutability) — and when each is the right tool.

## Box: a value on the heap

**`Box<T>`** is the simplest smart pointer: it puts a value on the *heap* and owns it, giving you a pointer-sized handle on the stack. It follows all the normal ownership rules (single owner, dropped when out of scope — which frees the heap value); it just relocates the data to the heap. You reach for `Box` in a few specific cases:

- **Recursive types.** A type that contains itself (a tree, a linked list) has no fixed size, which Rust needs to know at compile time. `Box` gives a fixed-size (pointer) indirection, making recursive types possible:

```rust
enum List {
    Cons(i32, Box<List>),   // Box breaks the infinite-size recursion
    Nil,
}
use List::{Cons, Nil};
let list = Cons(1, Box::new(Cons(2, Box::new(Nil))));
```

- **Large values** you want on the heap rather than copied on the stack.
- **Trait objects** — `Box<dyn Trait>` (from the trait-objects post) stores a trait object on the heap.

`Box` is the "just put it on the heap, single-owner" tool — minimal, cheap, and the most common smart pointer. It doesn't relax the ownership rules; it just enables heap placement and recursive/trait-object types.

## Rc: shared ownership

Sometimes a value genuinely needs *multiple owners* — think a graph node referenced by several others, or shared configuration used across parts of a program. This violates ownership's "one owner at a time" rule. **`Rc<T>`** (Reference Counted) provides **shared ownership**: multiple `Rc` handles can own the same value, and the value is dropped only when the *last* owner goes away:

```rust
use std::rc::Rc;

let shared = Rc::new(String::from("config"));
let a = Rc::clone(&shared);     // a new owner (increments the reference count)
let b = Rc::clone(&shared);     // another owner
// the String is dropped only when shared, a, and b are ALL gone
println!("owners: {}", Rc::strong_count(&shared));   // 3
```

`Rc` keeps a *count* of how many owners exist; `Rc::clone` increments it (cheaply — it clones the handle, not the data), and dropping an `Rc` decrements it. When the count hits zero, the value is freed. This is how Rust safely allows shared ownership without a garbage collector: the reference count *is* the mechanism deciding when to free. Two caveats: `Rc` is for **single-threaded** sharing (its thread-safe cousin is `Arc`, for concurrency — a later topic), and `Rc` gives *shared* (immutable) access — to *mutate* shared data, you combine it with `RefCell`.

## RefCell: interior mutability

Ownership normally enforces the borrowing rules (one mutable XOR many immutable references) *at compile time* via the borrow checker. But sometimes you need to mutate data through a *shared/immutable* reference — a pattern the compile-time rules forbid, yet is genuinely needed (e.g. mutating a node in an `Rc`-shared graph, or mutating internal state behind an immutable API). **`RefCell<T>`** provides **interior mutability**: it lets you mutate the value inside even through a shared reference, by enforcing the borrowing rules *at runtime* instead of compile time:

```rust
use std::cell::RefCell;

let cell = RefCell::new(5);
*cell.borrow_mut() += 10;        // mutate through a shared reference
println!("{}", cell.borrow());   // 15
```

`RefCell` moves the borrow check from compile time to *runtime*: `borrow()` and `borrow_mut()` track borrows dynamically, and if you violate the one-writer-XOR-many-readers rule (e.g. two `borrow_mut()` at once), it **panics at runtime** rather than failing to compile. So the safety guarantee is *preserved* — you can't actually alias mutably — but it's checked when the program runs, not when it compiles. This is the trade: `RefCell` gives flexibility (mutate through shared refs) at the cost of runtime checking (and a possible panic if you break the rules). Use it when you genuinely need interior mutability and the compile-time checker is too restrictive for a correct pattern — not as a way to avoid learning borrowing.

## Combining them: Rc<RefCell<T>>

The three compose, and the most common combination is **`Rc<RefCell<T>>`** — *shared ownership of mutable data*. `Rc` gives multiple owners; `RefCell` lets those owners mutate the shared value:

```rust
use std::rc::Rc;
use std::cell::RefCell;

let shared = Rc::new(RefCell::new(vec![1, 2, 3]));
let clone = Rc::clone(&shared);
clone.borrow_mut().push(4);              // mutate through a shared owner
println!("{:?}", shared.borrow());       // [1, 2, 3, 4]
```

This pattern — `Rc<RefCell<T>>` — is how you build data structures that need *both* multiple owners *and* mutation: graphs, trees with parent pointers, shared mutable state in single-threaded code. It's the standard Rust idiom for "several things share this, and any of them can change it," achieving what ownership's basic rules forbid, safely (shared ownership via reference counting, safe mutation via runtime borrow checking). Its thread-safe analog for concurrency is `Arc<Mutex<T>>` (a later topic) — same idea, made safe across threads.

## Smart pointers as controlled escape hatches

The takeaway: smart pointers are Rust's *controlled* ways past the basic ownership rules, each for a specific need — `Box<T>` for heap allocation (recursive types, large values, trait objects), `Rc<T>` for shared ownership (multiple owners, freed at zero references, single-threaded), and `RefCell<T>` for interior mutability (mutate through shared refs, borrow-checked at runtime) — composing as `Rc<RefCell<T>>` for shared mutable data. Crucially, they don't *abandon* safety: `Rc`'s reference counting frees correctly, and `RefCell`'s runtime checks still enforce the borrowing rules (panicking rather than allowing a data race or aliasing bug). They're escape hatches from the *compile-time* strictness, not from safety itself. The guidance: reach for plain ownership and references first (they cover most code and catch errors at compile time), and use smart pointers when a data structure genuinely needs heap placement, shared ownership, or interior mutability — which real graphs, trees, and shared-state designs do. The final Module 2 post covers organizing all this code: modules and crates.

## Key takeaways

- Smart pointers are types that act like pointers with added capabilities, providing controlled ways around ownership's basic rules without sacrificing safety — reach for plain ownership/references first, and smart pointers when a data structure genuinely needs more.
- `Box<T>` puts a value on the heap with single ownership (normal ownership rules) — used for recursive types (breaking infinite-size recursion), large values, and trait objects (`Box<dyn Trait>`); the simplest, most common smart pointer.
- `Rc<T>` provides shared ownership (multiple owners via reference counting; the value is freed when the last owner drops) for single-threaded sharing (its thread-safe cousin is `Arc`) — giving immutable shared access, safely, with no garbage collector.
- `RefCell<T>` provides interior mutability — mutating through a shared reference by moving the borrow check from compile time to runtime (panicking if you violate one-writer-XOR-many-readers) — preserving safety but checked at runtime; use it when the compile-time checker is too strict for a correct pattern.
- They compose: `Rc<RefCell<T>>` is the standard idiom for shared mutable data (graphs, trees, shared single-threaded state), with `Arc<Mutex<T>>` its thread-safe analog — escape hatches from compile-time strictness, not from safety.

## Further reading

- [Iterators (previous post)](/blog/posts/rust-14-iterators.html)
- [The Rust Book — smart pointers](https://doc.rust-lang.org/book/ch15-00-smart-pointers.html)
- [Ownership: Rust's big idea (Module 1) — the rules smart pointers work around](/blog/posts/rust-04-ownership.html)
