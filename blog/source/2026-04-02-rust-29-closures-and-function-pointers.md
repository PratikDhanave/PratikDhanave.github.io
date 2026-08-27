# Closures and Function Pointers, Revisited

*Module 2 introduced closures as anonymous functions that capture their environment. But once you start passing functions around as values — storing callbacks, building higher-order APIs, returning behavior from functions — a few subtleties surface: functions and closures aren't quite the same type, returning a closure requires a boxing trick, and the `Fn` trait family has a precise structure worth knowing. These details show up constantly in real Rust APIs, and mastering them makes you fluent in Rust's functional side.*

Revisiting closures (from Module 2) with an advanced lens, this post covers **function pointers** (`fn`), the relationship between functions and the closure traits (`Fn`/`FnMut`/`FnOnce`), **returning closures** (the boxing requirement), and passing functions as arguments. These come up whenever you build APIs that take or return behavior (callbacks, higher-order functions). It deepens Module 2's closures into the practical fluency needed for real functional-style Rust.

## Function pointers

Beyond closures, Rust has **function pointers** (`fn`) — the type of a *plain function* used as a value, which can be passed like a closure:

```rust
fn add_one(x: i32) -> i32 { x + 1 }

// `f: fn(i32) -> i32` is a function pointer parameter.
fn do_twice(f: fn(i32) -> i32, arg: i32) -> i32 {
    f(arg) + f(arg)
}

fn main() {
    let answer = do_twice(add_one, 5); // pass the function by name
    assert_eq!(answer, 12);
}
```

- **`fn` is the function-pointer type.** A *function pointer* has type `fn(...) -> ...` (lowercase `fn`) — the type of a *plain function* used as a *value* (passed around, stored). You can pass a function *by name* where an `fn` is expected. `fn` = a plain function as a value. Functions as values.
- **Function pointers can be passed like closures.** Because functions can be *passed as values* (`fn` pointers), you can pass a *function* where a closure is expected (in many cases) — `do_twice(add_one, 5)` passes the function `add_one`. Functions and closures are *often interchangeable* as arguments. Pass functions where closures fit. Interchangeable, often.
- **`fn` vs the closure traits.** A function pointer (`fn`) is a *concrete type*; the closure traits (`Fn`/`FnMut`/`FnOnce`) are *traits*. Notably, a function pointer *implements all three* closure traits — so a `fn` can be used anywhere a closure trait is expected. `fn` implements the `Fn` traits. Functions satisfy closure bounds. (So preferring a closure-trait bound is more general.)

Function pointers (`fn(...) -> ...`, the type of a plain function used as a value) can be passed like closures (functions and closures are often interchangeable as arguments), and a function pointer implements all three closure traits (`Fn`/`FnMut`/`FnOnce`). Understanding the closure-trait structure clarifies this.

## The closure trait family

The **closure traits** — `Fn`, `FnMut`, `FnOnce` — form a hierarchy based on *how a closure uses its captured environment* (from Module 2, now with the structure clear):

- **Three traits by how they capture.** A closure implements one or more of: `FnOnce` (can be called *once* — takes ownership of / consumes captures), `FnMut` (can be called multiple times, *mutably borrowing* captures), and `Fn` (can be called multiple times, *immutably borrowing* or not capturing). Which one(s) a closure implements depends on *how it uses its captures*. Three traits by capture behavior. Own, mutate, or read.
- **They form a hierarchy.** The traits *nest*: every `Fn` is also `FnMut` and `FnOnce`; every `FnMut` is also `FnOnce`. So `Fn` is the *most* capable (usable everywhere) and `FnOnce` the *least* (only callable once). `Fn ⊂ FnMut ⊂ FnOnce`. A capability hierarchy. Fn is most general.
- **Bound your parameters by the least restrictive trait.** When *accepting* a closure, bound by the *least restrictive* trait that works: use `FnOnce` if you only call it once, `FnMut` if you call it and it may mutate, `Fn` if it's called multiply and only reads. Choosing the *right* bound makes your API accept the *widest* range of closures. Bound by the loosest trait that works. Accept more closures.
- **This is why you see `Fn`/`FnMut`/`FnOnce` in signatures.** APIs taking closures use these trait bounds (`fn foo<F: Fn(i32) -> i32>(f: F)`) — and knowing the hierarchy explains which to use and what each accepts. The trait family is how Rust types "a function passed as an argument." Closure traits type function arguments. Why signatures use them.

The closure traits — `Fn` (read/no capture), `FnMut` (mutate), `FnOnce` (consume) — form a hierarchy (`Fn ⊂ FnMut ⊂ FnOnce`) based on how a closure uses its captures, and you bound closure parameters by the *least restrictive* trait that works (to accept the widest range). This structure types "a function passed as an argument." Returning a closure has a special requirement.

## Returning closures

**Returning a closure** from a function requires special handling, because closures don't have a fixed known size — you must return them *boxed* (or via `impl Trait`):

```rust
// Return a boxed closure (a trait object) — the closure's concrete type is
// unnameable and unsized, so box it behind the Fn trait.
fn returns_closure() -> Box<dyn Fn(i32) -> i32> {
    Box::new(|x| x + 1)
}

// Or, more simply, with `impl Trait` (return "some type implementing Fn"):
fn make_adder(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x + n // `move` captures n by value
}

fn main() {
    let add_one = returns_closure();
    let add_five = make_adder(5);
    assert_eq!(add_one(1), 2);
    assert_eq!(add_five(10), 15);
}
```

- **Closures have unnameable, unsized types.** Each closure has a *unique, compiler-generated, unnameable* type (you can't write it), and it's *dynamically sized* (from the advanced-types post — you can't return it bare). So you *can't* just write the closure's type as a return type. Closures' types are unnameable and unsized. Can't return bare.
- **Box it (a trait object).** One solution: return the closure *boxed* behind a trait object — `Box<dyn Fn(i32) -> i32>` — which has a *known size* (a boxed pointer) and names the type by its *trait* (from the trait-objects post). `Box<dyn Fn...>` is the classic way to return a closure. Box the closure as a trait object. Known size, named by trait.
- **Or use `impl Trait` (simpler).** A cleaner modern way: `-> impl Fn(i32) -> i32` — "returns *some* type implementing `Fn`" — which lets you return a closure *without boxing* (the compiler knows the concrete type; you just don't name it). `impl Trait` returns is the ergonomic, zero-cost way (when a *single* concrete closure type is returned). `impl Trait` returns closures without boxing. Simpler and zero-cost.
- **When to use which.** Use `impl Trait` when returning a *single* concrete closure type (simpler, zero-cost); use `Box<dyn Fn...>` when returning *different* closure types from different paths (a trait object can hold any, at the cost of boxing/dynamic dispatch). `impl Trait` for one type, `Box<dyn>` for many. Choose by need.

Returning a closure requires handling its unnameable, unsized type — via `Box<dyn Fn...>` (a boxed trait object, for returning different closure types) or `impl Trait` (`-> impl Fn...`, simpler and zero-cost for a single concrete type). This is a common real-Rust need. These features enable functional-style APIs.

## Functional-style APIs in practice

Bringing it together, these features enable *functional-style* Rust APIs — passing and returning behavior — which are pervasive:

- **Higher-order functions everywhere.** Rust APIs frequently *take* closures/functions (higher-order functions) — iterator adapters (`map`, `filter` — Module 2), callbacks, configuration, strategies. Passing behavior as an argument is *pervasive* in idiomatic Rust. Higher-order functions are everywhere. Passing behavior is idiomatic.
- **Accept closures generically.** To *accept* behavior, use a *closure-trait bound* (`F: Fn...`) — more general than a function pointer (`fn`), accepting both closures and functions. Generic closure parameters make flexible APIs. Accept `F: Fn...` for flexibility. Widest acceptance.
- **Return behavior when needed.** To *return* behavior (a configured closure, a strategy), use `impl Trait` (usually) or `Box<dyn Fn...>` (for varied types). Returning closures enables factory-style APIs (`make_adder`). Return closures for factory APIs. Behavior as a return value.
- **This is Rust's functional side, done with zero cost.** Crucially, all this (closures, iterator chains, higher-order functions) is *zero-cost* (Module 2) — the functional style compiles to efficient code (closures inline, no overhead). Rust gives functional-style expressiveness *without* the runtime cost. Functional style, zero cost. Expressive and efficient.

Closures and function pointers, revisited — function pointers (`fn`) as function-values, the closure-trait hierarchy (`Fn`/`FnMut`/`FnOnce`, bound by the loosest that works), and returning closures (via `impl Trait` or `Box<dyn Fn>`) — enable Rust's pervasive, zero-cost functional-style APIs (passing and returning behavior). This deepens Module 2's closures into practical fluency. Next: building a real command-line application. 

## Key takeaways

- Function pointers (`fn(...) -> ...`, lowercase `fn`) are the type of a plain function used as a value (passed around, stored) — you can pass a function by name where a closure is expected (functions and closures are often interchangeable as arguments), and a function pointer implements all three closure traits (`Fn`/`FnMut`/`FnOnce`).
- The closure traits form a hierarchy based on how a closure uses its captures: `Fn` (immutably borrows or doesn't capture — callable multiply), `FnMut` (mutably borrows — callable multiply), `FnOnce` (consumes captures — callable once), nested as `Fn ⊂ FnMut ⊂ FnOnce` (Fn most capable) — so bound closure parameters by the *least restrictive* trait that works to accept the widest range.
- Returning a closure requires handling its unnameable, dynamically-sized type — you can't return it bare — via `Box<dyn Fn(i32) -> i32>` (a boxed trait object, which has a known size and is named by its trait) or, more simply and zero-cost, `-> impl Fn(i32) -> i32` (return "some type implementing Fn").
- Use `impl Trait` returns when returning a *single* concrete closure type (simpler, zero-cost); use `Box<dyn Fn...>` when returning *different* closure types from different code paths (a trait object can hold any, at the cost of boxing and dynamic dispatch).
- These features enable Rust's pervasive functional-style APIs — accept behavior generically via closure-trait bounds (`F: Fn...`, more general than `fn`), return behavior via `impl Trait` or `Box<dyn Fn>` (factory-style APIs) — all zero-cost (closures inline, compile to efficient code), giving functional expressiveness without runtime overhead.

## Further reading

- [The Rust Book — Advanced Functions and Closures](https://doc.rust-lang.org/book/ch20-05-advanced-functions-and-closures.html)
- [Rust: Closures (Module 2)](/blog/posts/rust-13-closures.html)
- [Foreign function interface (previous post)](/blog/posts/rust-28-ffi.html)
