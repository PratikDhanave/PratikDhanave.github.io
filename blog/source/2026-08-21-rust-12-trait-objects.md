# Trait Objects and Dynamic Dispatch

*Generics with trait bounds give you many types, resolved at compile time. But sometimes you need a collection of different types that share a trait — a list of shapes, a set of plugins — decided at runtime. Trait objects provide that, trading a little performance for runtime flexibility. Knowing when to use which is a real Rust design decision.*

The last two posts used traits with generics for *static* dispatch — the compiler specializes code per concrete type (monomorphization). This post covers the other way to use traits: **trait objects**, which give *dynamic* dispatch — choosing behavior at runtime. Trait objects let you hold values of *different* types that share a trait in one place, which generics can't. This post covers `dyn`, the static-vs-dynamic dispatch trade-off, and how to choose — a genuine Rust design decision.

## The problem generics can't solve

Generics are monomorphized: `Vec<T>` holds elements of *one* concrete type `T`. But sometimes you want a collection of *different* types that all implement the same trait — a `Vec` of assorted shapes (circles, rectangles, triangles), a list of UI widgets, a set of plugins. Each is a different type; they only share a trait. Generics can't express "a `Vec` of any-type-implementing-Shape" as a single homogeneous `Vec<T>`, because `T` must be *one* type.

**Trait objects** solve this. A trait object is a value accessed through a *trait*, not its concrete type — written `dyn Trait` (usually behind a pointer like `Box<dyn Trait>` or `&dyn Trait`):

```rust
trait Shape {
    fn area(&self) -> f64;
}

struct Circle { r: f64 }
struct Rectangle { w: f64, h: f64 }

impl Shape for Circle { fn area(&self) -> f64 { 3.14159 * self.r * self.r } }
impl Shape for Rectangle { fn area(&self) -> f64 { self.w * self.h } }

// a Vec of DIFFERENT types that all implement Shape:
let shapes: Vec<Box<dyn Shape>> = vec![
    Box::new(Circle { r: 2.0 }),
    Box::new(Rectangle { w: 3.0, h: 4.0 }),
];

for shape in &shapes {
    println!("area = {}", shape.area());   // calls the right area() at runtime
}
```

`Vec<Box<dyn Shape>>` is "a vector of boxed values, each some type that implements `Shape`." The elements are *different* concrete types (`Circle`, `Rectangle`), unified by the `Shape` trait. This is what trait objects enable and generics don't: **heterogeneous collections of trait-implementing types.**

## Static vs dynamic dispatch

The core distinction — and the reason to choose one or the other — is *when the method to call is decided*:

- **Static dispatch (generics)** — the compiler knows the concrete type at compile time and monomorphizes, so the exact method is baked in. No runtime lookup. Fastest (and inlinable), but each type gets its own specialized code, and a generic value is one concrete type.
- **Dynamic dispatch (trait objects)** — the concrete type isn't known until runtime, so the call goes through a *vtable* (a table of function pointers) to find the right method at runtime. This has a small runtime cost (the indirection, and it prevents some inlining), but it allows one piece of code (or one collection) to work with *many different types* chosen at runtime.

```text
Static dispatch (generic):   compiler picks Circle::area at compile time → direct call
Dynamic dispatch (dyn):      at runtime, look up area() in the value's vtable → indirect call
```

The trade-off is **performance vs. flexibility**:

- Generics/static dispatch: maximum performance (zero-cost, inlinable), but homogeneous (one concrete type per generic instantiation) and more compiled code.
- Trait objects/dynamic dispatch: a small runtime cost (vtable indirection) and heap allocation (usually `Box<dyn>`), but the flexibility of heterogeneous collections and runtime-chosen behavior, with less compiled code (one version, not one per type).

Neither is "better" — they solve different needs, and this is a real design choice in Rust code.

## When to use which

The practical decision:

- **Use generics (static dispatch) when** the types are known at compile time and you want maximum performance — the common default. Writing a function over "any comparable type" or building a `Vec<T>` of one type: generics. Most Rust code is generic.
- **Use trait objects (dynamic dispatch) when** you need runtime flexibility that generics can't give:
  - **Heterogeneous collections** — a `Vec<Box<dyn Trait>>` of different types sharing a trait (the shapes example, plugin lists, UI element trees). This is the signature use case.
  - **Runtime-chosen behavior** — when which type/implementation to use is decided at runtime (e.g. based on config or input), not compile time.
  - **Reducing code bloat** — when monomorphizing a generic over many types would produce too much compiled code, a single dynamic-dispatch version can be leaner.
  - **Simpler APIs** — sometimes `Box<dyn Trait>` is simpler than propagating generic parameters everywhere.

The rule of thumb: **default to generics (performance, the common case); reach for trait objects when you specifically need heterogeneous collections or runtime-selected behavior.** Recognizing which situation you're in is the skill — "do I have many types known now (generics), or different types unified only by a trait and possibly chosen at runtime (trait objects)?"

## Object safety: the catch

One constraint to know: not every trait can be a trait object — the trait must be **object-safe**. Roughly, this means its methods must be dispatchable through a vtable — e.g. methods can't return `Self` by value or use generic type parameters, because the vtable needs a uniform, concrete signature. Most ordinary traits (like `Shape` above) are object-safe; you'll occasionally hit a trait that isn't (the compiler tells you clearly), which usually means that trait is meant for static dispatch (generics) only. This is a detail rather than a daily concern, but it explains why some traits work as `dyn` and some don't — object safety is the requirement for the vtable-based dynamic dispatch to work.

## Two ways to use the same traits

The big-picture takeaway: traits (last post) can be used *two* ways — with generics for **static dispatch** (compile-time, zero-cost, homogeneous, the default) or as trait objects for **dynamic dispatch** (runtime, small cost, heterogeneous, flexible). This dual nature is one of Rust's elegant design points: the *same* trait definitions serve both, and you choose the dispatch strategy per situation. Reach for generics by default for performance, and trait objects when you genuinely need runtime polymorphism (heterogeneous collections, runtime-chosen types). Understanding this choice — and recognizing which your problem calls for — is a mark of writing idiomatic, well-performing Rust. The next post shifts to a different everyday tool: closures.

## Key takeaways

- Generics are homogeneous (one concrete type per instantiation), so they can't hold *different* types that share a trait in one collection; trait objects (`dyn Trait`, usually `Box<dyn Trait>` or `&dyn Trait`) can — enabling heterogeneous collections like `Vec<Box<dyn Shape>>`.
- The distinction is dispatch timing: static dispatch (generics) resolves the method at compile time via monomorphization (fastest, inlinable, homogeneous, more code); dynamic dispatch (trait objects) resolves at runtime via a vtable (small indirection cost, heterogeneous, flexible, less code).
- The trade-off is performance vs. flexibility — neither is universally better; they solve different needs, making the choice a real Rust design decision.
- Default to generics (performance, the common case for types known at compile time); reach for trait objects when you need heterogeneous collections, runtime-chosen behavior, reduced code bloat, or simpler APIs — recognizing which situation you're in is the skill.
- Trait objects require object-safe traits (methods dispatchable through a vtable — no `Self`-by-value returns or generic methods); most ordinary traits qualify, and the compiler tells you when one doesn't — the same trait definitions serve both static and dynamic dispatch.

## Further reading

- [Traits: shared behavior (previous post)](/blog/posts/rust-11-traits.html)
- [The Rust Book — trait objects and dynamic dispatch](https://doc.rust-lang.org/book/ch18-02-trait-objects.html)
- [Generics — static dispatch and monomorphization](/blog/posts/rust-10-generics.html)
