# Iterators

*Iterators are how Rust does loops without writing loops — a chain of composable adapters (map, filter, collect) that reads like a description of what you want, not how to get it. And the astonishing part is that this high-level, functional style compiles to code as fast as a hand-written loop. Zero-cost abstraction, at its most delightful.*

Closures set up the star of Module 2's everyday toolkit: **iterators**. An iterator produces a sequence of values, and Rust's iterator ecosystem — `map`, `filter`, `collect`, and dozens more **adapters** — lets you express data transformations as readable, composable chains instead of manual loops. Best of all, iterators are a *zero-cost abstraction*: the functional style compiles to code as fast as a hand-written loop. This post covers the `Iterator` trait, laziness, adapters, and why iterators are both elegant and free.

## The Iterator trait

An **iterator** is any type implementing the `Iterator` trait, which has essentially one required method — `next`, returning `Option<Self::Item>` (`Some(value)` for each element, `None` when exhausted):

```rust
trait Iterator {
    type Item;
    fn next(&mut self) -> Option<Self::Item>;
    // ... plus dozens of default methods built on next()
}
```

This is the traits-with-default-methods pattern from earlier: you (or the standard library) implement *one* method, `next`, and get the entire ecosystem of iterator methods (`map`, `filter`, `sum`, etc.) *for free* as default implementations. That's why `Vec`, `HashMap`, ranges, and countless types are iterable — they provide `next`, and the whole toolkit comes with it. A `for` loop is really just calling `next` until `None`:

```rust
let v = vec![1, 2, 3];
for x in &v {              // desugars to repeatedly calling next() on v's iterator
    println!("{}", x);
}
```

So "iterator" isn't a special construct — it's a trait, and iterating is calling `next`. This uniformity means anything that implements `Iterator` plugs into `for` loops and every adapter.

## Adapters: composing transformations

The joy of iterators is the **adapters** — methods that transform one iterator into another, chainable into expressive pipelines:

```rust
let nums = vec![1, 2, 3, 4, 5, 6];

let result: Vec<i32> = nums.iter()
    .filter(|&&n| n % 2 == 0)    // keep evens
    .map(|&n| n * n)             // square them
    .collect();                  // gather into a Vec
// result = [4, 16, 36]

let total: i32 = nums.iter().sum();          // 21
let any_big = nums.iter().any(|&n| n > 5);   // true
```

Read that chain top to bottom: take the numbers, keep the evens, square them, collect into a vec. It's a *description* of the transformation, not a manual loop with indices and a mutable accumulator. Common adapters:

- **`map`** — transform each element.
- **`filter`** — keep elements matching a predicate.
- **`collect`** — consume the iterator into a collection (`Vec`, `HashMap`, `String`, etc.).
- **`sum` / `product` / `count`** — reduce to a single value.
- **`fold`** — general reduction with an accumulator.
- **`take` / `skip` / `zip` / `enumerate` / `chain` / `rev`** — and many more.

Most adapters take **closures** (the last post) — `filter`/`map` receive a closure describing the per-element operation — which is why closures set this up. Chaining adapters composes complex transformations from simple, named, readable steps, replacing error-prone manual loops (off-by-one bugs, mutable accumulators, index juggling) with a declarative pipeline. This functional style is deeply idiomatic Rust.

## Laziness: nothing happens until you consume

A crucial property: **iterator adapters are lazy** — they do *nothing* until the iterator is *consumed*. `map` and `filter` don't run their closures when called; they build up a description of the computation. Only a **consuming** operation — `collect`, `sum`, `for`, `count`, etc. — actually drives the iterator, pulling values through the whole chain:

```rust
let iter = nums.iter().map(|&n| n * 2).filter(|&n| n > 4);  // nothing computed yet!
let result: Vec<i32> = iter.collect();                       // NOW it runs
```

Laziness has real benefits:

- **Efficiency** — the chain processes each element *once*, pulling it through all adapters, rather than building an intermediate collection at each step. `filter(...).map(...)` doesn't create a filtered vec then a mapped vec; each element flows through both in one pass.
- **Composability without waste** — you can build long adapter chains and they only compute what's actually consumed. With `take(3)`, only the first three elements are ever processed, even on a huge (or infinite) source.
- **Infinite iterators** — because it's lazy, you can have infinite iterators (like `(1..)`) and `take` a finite prefix; nothing computes the infinite part.

The mental model: adapters *describe* a pipeline lazily; a consumer *runs* it, pulling elements through once. This is why iterators are efficient despite looking like they'd create many intermediate collections — laziness means they don't.

## Zero-cost: as fast as a hand-written loop

Here's the payoff that makes iterators more than syntactic sugar: **iterators are a zero-cost abstraction — the high-level chain compiles to code as fast as (often identical to) a hand-written loop.** Through monomorphization and inlining (the generics/closures posts), the compiler collapses the whole adapter chain — the closures, the laziness, the trait method calls — into a tight loop with no overhead. There's no runtime cost for the abstraction: no allocations for the intermediate iterators, no indirect calls, no penalty for the functional style.

```text
Your iterator chain:   nums.iter().filter(...).map(...).sum()
Compiles to:           a single tight loop, as fast as writing the loop by hand
   → the elegance is free; you don't trade performance for readability
```

This is the same "don't pay at runtime for abstractions you use" principle as generics — applied to iteration. In many languages, functional-style chains (map/filter) are slower than imperative loops (extra allocations, closures with overhead), so you trade performance for readability. In Rust, you don't: iterators are *both* the more readable/composable style *and* as fast as the manual loop. This is why idiomatic Rust favors iterator chains freely — there's no performance reason not to, and every readability reason to. It's one of Rust's most delightful features: high-level expressiveness with low-level performance, genuinely for free.

## Iterators: elegant and free

The takeaway: iterators are the `Iterator` trait (implement `next`, get the whole toolkit), composed via lazy adapters (`map`, `filter`, `collect`, ...) that take closures and build readable, declarative transformation pipelines — and compiled to code as fast as hand-written loops (zero-cost). They replace error-prone manual loops with expressive chains at no performance cost, which is why they're pervasive in idiomatic Rust. Iterators tie together Module 2's threads: the `Iterator` *trait* (traits), its generic adapters (generics), the *closures* they take, and *zero-cost* compilation (the recurring principle) — a showcase of how Rust's abstraction machinery delivers expressiveness without runtime penalty. The next post covers smart pointers, for the cases where ownership needs more than the basics.

## Key takeaways

- An iterator implements the `Iterator` trait, whose one required method `next` returns `Option<Item>` (`Some` per element, `None` when done); implement `next` and you get dozens of methods free (default methods) — and a `for` loop is just calling `next` until `None`.
- Adapters (`map`, `filter`, `collect`, `sum`, `fold`, `take`, `zip`, `enumerate`, ...) transform iterators and chain into readable, declarative pipelines that replace error-prone manual loops; most take closures (from the last post) describing the per-element operation.
- Adapters are lazy — they do nothing until a consumer (`collect`, `sum`, `for`, `count`) drives the iterator — which means each element is processed once through the whole chain (no intermediate collections), long chains only compute what's consumed, and infinite iterators work with `take`.
- Iterators are a zero-cost abstraction: monomorphization + inlining collapse the whole chain into a tight loop as fast as (often identical to) hand-written imperative code — no allocations, no indirection, no penalty for the functional style.
- Unlike many languages where functional chains are slower than loops, Rust iterators are both more readable/composable AND as fast as manual loops, so idiomatic Rust favors them freely — a showcase tying together traits, generics, closures, and the zero-cost principle.

## Further reading

- [Closures (previous post)](/blog/posts/rust-13-closures.html)
- [The Rust Book — processing a series of items with iterators](https://doc.rust-lang.org/book/ch13-02-iterators.html)
- [Generics — the monomorphization that makes iterators zero-cost](/blog/posts/rust-10-generics.html)
