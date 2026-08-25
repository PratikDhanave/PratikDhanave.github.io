# Generics

*Writing the same function three times for three types is the kind of duplication that rots a codebase. Generics let you write it once, over any type — and Rust's twist is that this abstraction costs nothing at runtime, because the compiler generates the specialized versions for you. Zero-cost abstraction starts here.*

The collections post used `Vec<T>` and `HashMap<K, V>` — those angle-bracketed type parameters are **generics**, and now we write our own. Generics let you write code that works over *many* types without duplication, and in Rust they're a **zero-cost abstraction**: the flexibility is resolved at compile time, so generic code runs exactly as fast as if you'd hand-written each specialized version. This post covers generic functions, structs, and enums, and the monomorphization that makes them free — setting up traits, which give generics their real power.

## The problem: duplication across types

Suppose you want the largest element of a list. Without generics, you'd write one function for `Vec<i32>`, another for `Vec<f64>`, another for `Vec<char>` — identical logic, different types. That duplication is exactly what generics eliminate. A **generic** function is parameterized by a *type* (conventionally named `T`), so one definition works for all types:

```rust
fn largest<T: PartialOrd>(list: &[T]) -> &T {
    let mut biggest = &list[0];
    for item in list {
        if item > biggest {
            biggest = item;
        }
    }
    biggest
}

// works for any comparable type:
let n = largest(&[3, 7, 2, 9, 4]);        // T = i32
let c = largest(&['y', 'a', 'z', 'm']);   // T = char
```

`<T>` declares a type parameter, and `list: &[T]` means "a slice of any type `T`." One function, every type. (The `T: PartialOrd` part — a *trait bound* — says `T` must be comparable with `>`; more below and in the traits post. It's how the generic promises the compiler that `>` will work.)

## Generic structs and enums

Generics aren't just for functions — structs and enums are commonly generic, which is exactly how `Vec<T>` and `Option<T>` are defined:

```rust
struct Point<T> {
    x: T,
    y: T,
}

let int_point = Point { x: 1, y: 2 };        // Point<i32>
let float_point = Point { x: 1.5, y: 2.5 };  // Point<f64>

enum Option<T> {   // this is how the standard Option is defined!
    Some(T),
    None,
}
```

A generic struct/enum defines a *family* of types — `Point<i32>`, `Point<f64>`, etc. — from one definition. This is why the Module 1 enums `Option<T>` and `Result<T, E>` had those type parameters: they're generic over the value/error types they hold, so one `Option` works for any contained type. Generic data structures are everywhere in Rust's standard library (every collection is generic), and writing your own is the same mechanism. You can also implement methods generically with `impl<T> Point<T> { ... }`.

## Trait bounds: constraining the type

Pure "any type `T`" is often too permissive — the `largest` function needs `T` to be *comparable*, or `item > biggest` wouldn't make sense. **Trait bounds** constrain a generic type to those that have certain capabilities:

```rust
fn largest<T: PartialOrd>(list: &[T]) -> &T { /* ... */ }
//           ^^^^^^^^^^^^ T must implement PartialOrd (be comparable)

fn print_all<T: std::fmt::Display>(items: &[T]) {   // T must be printable
    for item in items {
        println!("{}", item);
    }
}
```

A bound like `T: PartialOrd` says "`T` can be any type *that implements the `PartialOrd` trait*" (i.e. is comparable). This is the crucial connection: **generics + trait bounds let you write code over any type that has the capabilities you need.** The generic is flexible (any type) but *constrained* (only types with the required behavior), so inside the function you can rely on those capabilities (comparison, printing, etc.). Trait bounds are what make generics genuinely useful rather than "any type but you can't do anything with it" — and they're why the next post, on traits, is where generics come alive. (Bounds can be written with a `where` clause for readability when there are many.)

## Zero-cost abstraction: monomorphization

Here's what makes Rust generics special, and it embodies a core Rust value: **generics are a zero-cost abstraction — they have no runtime overhead.** In some languages, generic/polymorphic code pays a runtime price (boxing, dynamic dispatch, type checks). In Rust, generics are resolved *at compile time* through **monomorphization**:

- When you call `largest` with `i32`, the compiler generates a *concrete* version specialized for `i32`. When you call it with `char`, it generates another specialized for `char`. Each call site uses the specialized version.
- So `largest::<i32>` is, at runtime, exactly the hand-written i32 version — same machine code, no generic indirection, no runtime type information, no boxing.

```text
Your generic code:        largest<T>(...)
Compiler monomorphizes → largest_i32(...)   (used where T = i32)
                        → largest_char(...)  (used where T = char)
   → each is as fast as if you'd written it by hand; the generic was free
```

This is the "zero-cost abstraction" principle central to Rust: **you don't pay at runtime for the abstractions you use.** Generics give you the *convenience* of writing code once over many types, and the compiler gives you the *performance* of specialized code — you get both, no trade-off. The cost is at compile time (the compiler generates the specializations, so generic-heavy code compiles more slowly and can produce larger binaries), not at run time. For a systems language where performance is the point, this matters enormously: you abstract freely without the usual runtime penalty. (This contrasts with *dynamic* dispatch via trait objects — the next-but-one post — which trades a small runtime cost for different flexibility.)

## Generics as the foundation of abstraction

The takeaway: generics let you write reusable code over many types without duplication, constrained by trait bounds to the capabilities you need, and made zero-cost at runtime through monomorphization. They're the foundation of Rust's abstraction story — every collection, `Option`, and `Result` is generic — and they pair inseparably with **traits**, which define the capabilities that trait bounds require and are Rust's core mechanism for shared behavior. Generics give you "code over many types"; traits give you "the behaviors those types share." Together they're how Rust does abstraction without a garbage collector or runtime cost — the subject of the next post.

## Key takeaways

- Generics let you write code once over many types (a type parameter `T`), eliminating the duplication of writing near-identical functions/types per concrete type — `<T>` on a function, struct, or enum defines a family that works for all types.
- Generic structs and enums are how the standard library is built (`Vec<T>`, `Option<T>`, `Result<T, E>` are all generic over their contained types) — writing your own uses the same mechanism, including generic methods via `impl<T>`.
- Trait bounds (`T: PartialOrd`) constrain a generic to types with the needed capabilities, so inside the code you can rely on those behaviors (comparison, printing) — generics + trait bounds = code over any type that has what you need, which is what makes generics useful.
- Rust generics are a zero-cost abstraction via monomorphization: the compiler generates a specialized concrete version per type used, so generic code runs exactly as fast as hand-written specialized code — no runtime overhead, boxing, or type info.
- The cost is at compile time (specialization → slower compiles, larger binaries), not runtime — embodying Rust's "don't pay at runtime for abstractions you use" principle; generics pair with traits (next post) to form Rust's full abstraction story without a GC.

## Further reading

- [Collections: Vec, String, and HashMap (previous post)](/blog/posts/rust-09-collections.html)
- [The Rust Book — generic types](https://doc.rust-lang.org/book/ch10-01-syntax.html)
- [Structs, enums, and pattern matching (Module 1)](/blog/posts/rust-07-structs-enums-pattern-matching.html)
