# Advanced Types

*Rust's type system has a few corners that don't come up in beginner code but explain things you've quietly wondered about — why some functions "return" a type that isn't really a type, why `str` behaves differently from other types, and how to give a complicated type a readable name. These advanced type features are small individually but together deepen your understanding of how Rust's type system actually works, which pays off when reading real code and library internals.*

Continuing Module 4's advanced features, this post covers **advanced types**: **type aliases** (giving types readable names), the **never type** `!`, and **dynamically sized types** and the `Sized` trait. These are lesser-known corners of Rust's type system that explain real behavior and appear in serious code. Together with advanced traits (the previous post), they round out your understanding of Rust's type system. None is essential daily, but each clarifies how Rust works.

## Type aliases

A **type alias** gives an *existing* type a *new name* — reducing repetition and improving readability for complicated types:

```rust
// A type alias: Kilometers is another name for i32.
type Kilometers = i32;

// More useful: a readable name for a verbose type.
type Thunk = Box<dyn Fn() + Send + 'static>;

fn takes_long_type(f: Thunk) { /* ... */ }
fn returns_long_type() -> Thunk { Box::new(|| println!("hi")) }

fn main() {
    let x: i32 = 5;
    let y: Kilometers = 5;
    // Kilometers IS i32 — they're interchangeable (unlike a newtype).
    println!("{}", x + y); // 10
}
```

- **A type alias is just another name.** `type Kilometers = i32;` makes `Kilometers` a *synonym* for `i32` — they're the *same type* (interchangeable, no distinction). Unlike a *newtype* (which creates a *distinct* type — the previous post), a type alias is *just a name* for an existing type. Alias = synonym; newtype = distinct type. A key difference.
- **Its main value: readability for complex types.** Type aliases shine for *verbose, repeated* types — `Box<dyn Fn() + Send + 'static>` is a mouthful; aliasing it to `Thunk` makes code *readable* and *DRY* (write the long type once). Aliases reduce repetition of complex types. Readability for verbose types.
- **It's not for type safety (that's newtypes).** Since an alias is the *same* type (interchangeable), it gives *no* type-safety distinction (`Kilometers` and `i32` mix freely). For *distinct* types (preventing mixing), use a *newtype* (previous post). Aliases are for *readability*, newtypes for *distinctness*. Use the right tool. Alias for naming, newtype for safety.

A type alias (`type Name = ExistingType`) gives an existing type a new *name* (a synonym, interchangeable — unlike a distinct newtype) — mainly valuable for readability with verbose, repeated types (like a long boxed closure type), not for type safety. A stranger corner is the never type.

## The never type

The **never type** `!` is a special type representing computations that *never return* — it enables things you've relied on without knowing:

- **`!` is the type that has no values.** The *never type* `!` (written as `!`) is a type with *no values* — it represents a computation that *never produces a value* because it *never returns* (it diverges: panics, loops forever, or exits). Functions returning `!` are "diverging functions." A type for "never returns." No values.
- **It coerces to any type.** The key property: `!` can *coerce to any type* — because a computation that never returns can be used *anywhere* (it never produces a wrong-typed value; it just doesn't return). This lets expressions that *diverge* fit in *any* type context. `!` fits any type. Diverging fits anywhere.
- **Why it matters: `match` arms and `continue`/`panic!`.** This is why `match` arms can `continue`, `break`, `return`, or `panic!` — those have type `!`, which coerces to match the other arms' type:

```rust
fn main() {
    let values = vec!["1", "two", "3"];
    for v in values {
        // parse() returns Result; the Err arm uses `continue` (type `!`),
        // which coerces to match the Ok arm's type (u32). Without `!` coercion,
        // the match arms would have mismatched types.
        let num: u32 = match v.parse() {
            Ok(n) => n,
            Err(_) => continue, // type `!`, coerces to u32
        };
        println!("{num}");
    }
}
```

- **It's usually invisible.** You rarely *write* `!` explicitly (it appears in some function signatures), but you *rely on* it constantly (every `match` with a `panic!`/`continue` arm, every diverging expression). The never type makes such code type-check. `!` works behind the scenes. You use it without seeing it.

The never type `!` (a type with no values, for computations that never return — panics, infinite loops, `continue`) *coerces to any type*, which is *why* `match` arms can `continue`/`panic!`/`return` (they have type `!` that fits the other arms' type) — a mostly-invisible feature you rely on constantly. Another type-system corner explains `str` and trait objects.

## Dynamically sized types and Sized

**Dynamically sized types (DSTs)** are types whose *size isn't known at compile time* — and the `Sized` trait, which is *automatic*, governs how Rust handles them:

- **Most types have a known size; DSTs don't.** Most types have a *fixed, compile-time-known size* (an `i32` is 4 bytes). But some — *dynamically sized types* — have a size known only at *runtime*: notably `str` (a string slice — its length varies) and *trait objects* (`dyn Trait` — the concrete type/size varies). DSTs' size isn't known at compile time. Variable-size types.
- **DSTs must be used behind a pointer.** Because Rust needs to know sizes to lay out memory, DSTs *can't* be used *directly* (you can't have a bare `str` variable) — they must be used *behind a pointer* (like `&str`, `Box<str>`, `&dyn Trait`, `Box<dyn Trait>`), which *has* a known size (a pointer, plus length/vtable metadata — a "fat pointer"). This is *why* you always see `&str` (never bare `str`) and `Box<dyn Trait>` (never bare `dyn Trait`). DSTs live behind (fat) pointers. Why `&str` and `Box<dyn Trait>`.
- **The `Sized` trait marks known-size types.** Rust has a `Sized` marker trait (automatic) that marks types with a *known compile-time size*. *Most* types are `Sized` (automatically); DSTs are *not* `Sized`. Generic functions *implicitly require* `Sized` (`fn foo<T>` is really `fn foo<T: Sized>`), which is why generics work with normal types by default. `Sized` marks known-size types (automatic). Implicit on generics.
- **`?Sized` relaxes the requirement.** To write a generic that *also* accepts DSTs, you use `?Sized` (`fn foo<T: ?Sized>`) — relaxing the implicit `Sized` bound (and then `T` must be behind a pointer). `?Sized` is how you write generics over possibly-unsized types. Relax `Sized` for DSTs. Opt into unsized.

Dynamically sized types (like `str` and `dyn Trait`) have runtime-known sizes, so they must be used behind (fat) pointers (`&str`, `Box<dyn Trait>`) — which is *why* you always see those forms — and the automatic `Sized` marker trait (implicitly required on generics) marks known-size types, with `?Sized` relaxing it to accept DSTs. Advanced types — type aliases (readable names), the never type `!` (diverging computations, `match`-arm coercion), and DSTs/`Sized` (variable-size types behind fat pointers) — are lesser-known corners that explain real Rust behavior. Next: unsafe Rust.

## Key takeaways

- A type alias (`type Name = ExistingType`) gives an existing type a new *name* — a synonym, fully interchangeable (unlike a distinct newtype) — mainly valuable for readability and DRY-ness with verbose, repeated types (like `Box<dyn Fn() + Send + 'static>` aliased to `Thunk`); it gives no type-safety distinction (use a newtype for that).
- The never type `!` is a type with *no values*, representing computations that never return (panic, infinite loop, `continue`, `return`) — and it *coerces to any type* (a never-returning computation fits any context).
- This coercion is *why* `match` arms can use `continue`/`panic!`/`return`/`break` (those expressions have type `!`, which coerces to match the other arms' type) — a mostly-invisible feature you rely on constantly.
- Dynamically sized types (DSTs) like `str` and trait objects (`dyn Trait`) have sizes known only at runtime, so they can't be used directly — they must be used behind a (fat) pointer (`&str`, `Box<str>`, `Box<dyn Trait>`) that has a known size — which is *why* you always see `&str` and `Box<dyn Trait>` rather than bare `str`/`dyn Trait`.
- The automatic `Sized` marker trait marks types with a compile-time-known size (most types), and generics implicitly require it (`fn foo<T>` means `T: Sized`), which is why generics work with normal types by default — `?Sized` relaxes this bound to write generics that also accept DSTs (then behind a pointer).

## Further reading

- [The Rust Book — Advanced Types](https://doc.rust-lang.org/book/ch20-04-advanced-types.html)
- [Advanced traits (previous post)](/blog/posts/rust-25-advanced-traits.html)
- [Rust: Trait objects and dynamic dispatch (Module 2)](/blog/posts/rust-12-trait-objects.html)
