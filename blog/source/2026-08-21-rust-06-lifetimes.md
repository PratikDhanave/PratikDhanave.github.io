# Lifetimes

*Lifetimes are the part of Rust that looks most alien — those `'a` annotations scattered through function signatures — and the part most misunderstood. They don't change how your code runs; they're just the compiler making explicit a question it's always been asking: how long does this reference need to be valid? Understanding that reframes lifetimes from cryptic syntax to a natural extension of borrowing.*

The borrowing post ended with the borrow checker preventing dangling references, and noted that the general case requires **lifetimes**. Lifetimes are famously the most intimidating Rust feature, but they're conceptually simple once you see what they're *for*: they let the compiler verify that references never outlive the data they point to, in cases where it can't figure that out on its own. This post demystifies lifetimes — what they are, why they exist, and why they're less scary than they look. (This is an introduction; lifetimes have depth we'll return to.)

## What lifetimes are for

Recall the dangling-reference problem: a reference must never outlive the value it points to, or it becomes a use-after-free. The borrow checker prevents this by tracking, for every reference, *how long it's valid* versus *how long the referenced value lives*. A **lifetime** is the compiler's name for "the span during which a reference is valid." Every reference has a lifetime; usually the compiler infers it and you never write it. Lifetimes exist for the cases where the compiler *can't* infer the relationships and needs you to *tell* it.

The crucial reframe: **lifetimes don't change how your program runs.** They're not a runtime thing — they add no code, no overhead, nothing at execution time. They're purely *compile-time information* that helps the borrow checker verify references are valid. A lifetime annotation is you *describing* a relationship the compiler needs to know, not *creating* any behavior. So the mental model is: lifetimes are the compiler asking "how long does this reference need to live, relative to the data?" — a question it's always been asking (that's the borrow checker), now made explicit in cases where it needs your help.

## Why the annotations appear

Most of the time you never write a lifetime, because the compiler infers them (this is called lifetime elision — the compiler applies rules to figure out the common cases). Lifetime *annotations* (`'a`) appear when the compiler can't figure out the relationships on its own — most commonly, when a function takes references and returns a reference, and the compiler needs to know *which* input the output's validity depends on:

```rust
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

Read this carefully, because it's the canonical example. The function returns a reference to *one of its inputs* (whichever is longer), but the compiler doesn't know *at compile time* which one — so it can't know how long the returned reference is valid. The lifetime annotation `'a` tells it: "the returned reference is valid as long as *both* inputs are valid" (they share the lifetime `'a`). Now the compiler can verify that callers don't use the result after either input has been dropped. The `<'a>` declares a lifetime parameter (like a generic parameter), and `&'a str` says "a reference with lifetime `'a`."

The key insight: **the annotation doesn't create a lifetime; it describes the relationship between the inputs' and output's lifetimes** so the compiler can check it. You're telling the compiler "these references' validity are connected in this way," and it verifies your program respects that. Without the annotation, the compiler couldn't know the returned reference's validity depends on the inputs, so it couldn't prevent you from using a dangling result. The annotation supplies the missing information.

## Why lifetimes look scarier than they are

Lifetimes intimidate newcomers for understandable reasons, but each dissolves once you see what's happening:

- **The syntax is unfamiliar** — `'a` looks strange, and seeing it thread through signatures is off-putting. But it's just a name for a lifetime (like a generic type parameter `T` is a name for a type), and `'a` is a conventional name — nothing deep.
- **They seem to appear arbitrarily** — you write functions fine, then suddenly the compiler demands lifetime annotations. But there's a rule: they appear when the compiler genuinely can't infer the reference relationships (usually returning a reference derived from reference inputs). It's not arbitrary; it's exactly the cases where the compiler needs help.
- **They feel like they *do* something** — they don't, at runtime. Realizing lifetimes are *purely descriptive compile-time information* (not runtime behavior, not something you're "managing") removes most of the mystery. You're annotating, not implementing.

The reframe that makes lifetimes click: **you already understand lifetimes implicitly** — every time you reason "this reference is valid as long as the thing it points to exists," that's a lifetime. The `'a` syntax is just *writing down* that reasoning for the compiler in the cases it can't infer. Lifetimes aren't a new concept; they're the *explicit form* of the borrowing reasoning you're already doing. Seen that way, they're the least alien part of Rust wearing the most alien syntax.

## When you'll meet them

In practice, lifetime annotations show up in specific places, and knowing where sets expectations:

- **Functions returning references derived from reference parameters** — the `longest` example; the compiler needs to know which input the output's lifetime ties to.
- **Structs that hold references** — a struct storing a reference needs a lifetime annotation, because the struct can't outlive the data its reference points to, and the compiler needs that relationship declared.
- **Rarely in simple code** — much everyday Rust (especially code that works with owned values rather than storing references) needs few or no explicit lifetimes, thanks to elision. Lifetimes become prominent when you're holding references in data structures or returning references, which is intermediate territory.

So don't be alarmed if early Rust rarely requires them — that's normal, because elision handles the common cases and owned-value code sidesteps them. When they do appear, remember: the compiler is asking you to describe a reference-validity relationship it can't infer, so it can keep its dangling-reference guarantee. You're helping it help you.

## Lifetimes complete the borrowing picture

The takeaway: lifetimes are the final piece of Rust's reference safety, letting the borrow checker verify — in the general case — that references never outlive their data. They're compile-time-only descriptive information, not runtime behavior; they appear when the compiler can't infer reference relationships; and they're really just the *explicit form* of the "a reference is valid as long as what it points to" reasoning that underlies all of borrowing. Together, ownership (who owns what), borrowing (who can access it), and lifetimes (how long references are valid) form the trio that makes Rust memory-safe at compile time with no GC — the mechanism behind the whole language's promise. This closes the hardest stretch of the series; the remaining foundational posts (structs/enums/pattern matching, and error handling) build on this safe foundation. Lifetimes have more depth we'll revisit, but the concept — describing reference validity for the compiler — is what matters now.

## Key takeaways

- A lifetime is the compiler's name for how long a reference is valid; lifetimes let the borrow checker verify references never outlive their data (no dangling references / use-after-free) in the general case — the piece that completes borrowing's safety.
- Lifetimes are purely compile-time descriptive information: they add no runtime code or overhead, don't change how your program runs, and aren't something you "manage" — a lifetime annotation describes a relationship, it doesn't create behavior.
- Annotations (`'a`) appear when the compiler can't infer reference relationships — most commonly a function returning a reference derived from reference inputs (like `longest`), where `'a` tells the compiler the output is valid as long as the inputs are — describing, not creating, the relationship.
- They look scarier than they are: `'a` is just a name (like a generic `T`), they appear by a rule (not arbitrarily) exactly where inference fails, and they do nothing at runtime — and you already reason about lifetimes implicitly whenever you think "this reference is valid while what it points to exists."
- You meet them mainly in functions returning references from reference inputs and structs holding references; much everyday (owned-value) Rust needs few thanks to elision — and ownership + borrowing + lifetimes together are the trio giving Rust compile-time memory safety with no GC.

## Further reading

- [Borrowing and references (previous post)](/blog/posts/rust-05-borrowing-and-references.html)
- [The Rust Book — validating references with lifetimes](https://doc.rust-lang.org/book/ch10-03-lifetime-syntax.html)
- [Ownership: Rust's big idea](/blog/posts/rust-04-ownership.html)
