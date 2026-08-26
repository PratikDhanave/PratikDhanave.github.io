# Send and Sync: The Traits Behind Fearless Concurrency

*How does the Rust compiler actually know that an `Arc<Mutex<T>>` is safe to share across threads but an `Rc<T>` isn't? The answer is two of the most elegant ideas in Rust: a pair of marker traits, `Send` and `Sync`, that encode thread-safety directly into the type system. They're rarely written by hand and often invisible, yet they're the machinery that makes fearless concurrency work — the compiler reasons about thread-safety by checking these traits, automatically, at compile time.*

This post reveals the machinery behind Rust's concurrency guarantees: the **`Send`** and **`Sync`** marker traits. They encode, in the type system, which types can be safely *moved to* another thread (`Send`) and *shared between* threads (`Sync`). The compiler uses them to check thread-safety automatically — this is *how* Rust catches data races at compile time. You rarely implement them yourself, but understanding them explains why the previous posts' rules hold.

## What Send and Sync are

`Send` and `Sync` are **marker traits** — traits with no methods, that simply *mark* a type as having a property. They mark thread-safety:

- **`Send`: safe to transfer ownership to another thread.** A type is `Send` if it's safe to *move* it to another thread (transfer ownership across a thread boundary). Most types are `Send` — you can move them into a thread (as `move` closures do). A type that's *not* `Send` cannot be moved to another thread. `Send` marks "safe to send to another thread."
- **`Sync`: safe to share references between threads.** A type is `Sync` if it's safe for *multiple threads to access it via shared references* (`&T`) simultaneously — i.e. `&T` is `Send`. A type is `Sync` if sharing it (by reference) across threads is safe. `Sync` marks "safe to share between threads by reference." (Roughly: `Send` is about moving the value; `Sync` is about sharing references to it.)
- **They're marker traits — no methods, just meaning.** `Send` and `Sync` have *no methods* — they just *mark* a type as thread-safe in these ways. They exist purely to let the *compiler reason* about thread-safety. They're not something you call; they're properties the compiler checks. Markers, not behavior.

`Send` (safe to move to another thread) and `Sync` (safe to share by reference between threads) are marker traits — no methods, just encoding thread-safety properties into the type system so the compiler can reason about them. They're the vocabulary in which Rust expresses thread-safety. And remarkably, the compiler assigns them automatically.

## They're automatic (auto traits)

The elegant part: `Send` and `Sync` are **auto traits** — the compiler *automatically* implements them for types whose components are all `Send`/`Sync`, so you rarely deal with them explicitly:

- **Automatically derived from components.** A type is *automatically* `Send`/`Sync` if all its parts (fields) are `Send`/`Sync`. The compiler propagates these traits *automatically* through your types — a struct of `Send` fields is `Send`, without you writing anything. So *most* types are `Send` and `Sync` automatically, and you never think about it. The compiler handles it for you.
- **This is why concurrency "just works" for safe types.** Because `Send`/`Sync` are automatic, ordinary safe types can be moved to and shared between threads without you doing anything — the compiler knows they're thread-safe. This automatic propagation is why the threading in the previous posts "just worked" for normal data: those types were automatically `Send`/`Sync`. Thread-safety is inferred, not annotated. It's invisible when things are safe.
- **Non-thread-safe types opt out.** Types that are *not* thread-safe *don't* get `Send`/`Sync` (their design opts out). The prime example: `Rc<T>` is *not* `Send` (its non-atomic reference counting is unsafe across threads) — so the compiler *automatically knows* `Rc` can't cross threads, and rejects it (from the previous post). `Arc<T>`, with atomic counting, *is* `Send`/`Sync` — so it's allowed. The traits encode exactly which types are thread-safe. Unsafe types simply aren't `Send`/`Sync`, so the compiler rejects them.

`Send` and `Sync` are auto traits — automatically implemented by the compiler for types whose components all have them — so most types get thread-safety automatically (why concurrency "just works" for safe types), while non-thread-safe types (like `Rc`, whose counting isn't atomic) don't get them, so the compiler automatically rejects unsafe cross-thread use. This automatic mechanism is how the compiler enforces thread-safety.

## How the compiler uses them

`Send` and `Sync` are the mechanism behind Rust's compile-time concurrency safety — the compiler *checks* them to enforce thread-safety:

- **`thread::spawn` requires `Send`.** When you move data into a thread (via a `move` closure to `thread::spawn`), the compiler *requires* that data to be `Send` (safe to move to another thread). If you try to move a non-`Send` type (like `Rc`) into a thread, the compiler *rejects* it — because it's not `Send`. This is *how* the compiler catches unsafe cross-thread moves: it checks the `Send` bound. The `Send` requirement is a compile-time gate.
- **Sharing across threads requires `Sync`.** When data is *shared* (by reference) across threads, the compiler requires it to be `Sync` (safe to share). Types that aren't `Sync` can't be shared across threads. So `Sync` gates safe cross-thread sharing. The compiler checks `Sync` for shared access.
- **This is the enforcement behind fearless concurrency.** The previous posts' guarantees — can't send `Rc` across threads, `Arc<Mutex<T>>` is safe to share — are *implemented via* `Send`/`Sync`: the compiler checks these traits and rejects unsafe code. `Send`/`Sync` are the *machinery* that makes Rust's data-race-free-at-compile-time guarantee work. When the compiler stops a data race, it's checking `Send`/`Sync`. They're the enforcement mechanism of fearless concurrency. This is *how* it works under the hood.

The compiler enforces thread-safety by *checking* `Send` (required to move data to a thread) and `Sync` (required to share data across threads) — rejecting types that lack them (like `Rc`). `Send`/`Sync` are the machinery behind Rust's compile-time data-race prevention: the guarantees of fearless concurrency are implemented as trait bounds the compiler checks. This is elegant, but it's also why you rarely touch them directly.

## What this means in practice

For everyday Rust, `Send`/`Sync` mostly work *invisibly* — but understanding them clarifies the concurrency model, and there are a few practical points:

- **You rarely implement them.** Because they're *automatic*, you almost never implement `Send`/`Sync` by hand — the compiler handles it. You mostly just *benefit* from them (thread-safety checked for free) and occasionally *encounter* them in compiler errors (when you try something not-thread-safe). They work behind the scenes. You benefit without writing them.
- **They explain the compiler errors.** When the compiler rejects your concurrent code ("`Rc<...>` cannot be sent between threads safely" — i.e. not `Send`), it's reporting a `Send`/`Sync` violation. Understanding these traits makes those errors *make sense* — the compiler is telling you the type isn't thread-safe. Recognizing `Send`/`Sync` in errors clarifies what's wrong and how to fix it (e.g. use `Arc` instead of `Rc`). They demystify concurrency compile errors.
- **They're the reason the guarantees hold.** Understanding `Send`/`Sync` explains *why* Rust's fearless concurrency actually works: it's not magic, it's a precise, checkable encoding of thread-safety in the type system, propagated automatically and enforced by the compiler. The guarantees rest on this concrete mechanism. Fearless concurrency is `Send`/`Sync` (plus ownership) checked at compile time. Now you know how it works.
- **They embody Rust's philosophy.** `Send`/`Sync` exemplify Rust's approach — encode safety properties in the *type system*, check them at *compile time*, make the safe path automatic and the unsafe path a compile error. Concurrency safety, like memory safety, is achieved through the type system, not runtime checks or programmer discipline. It's the same philosophy that runs through all of Rust, applied to threads. Types encode safety.

`Send` and `Sync` are the marker traits — automatic and mostly invisible — that encode thread-safety in Rust's type system: `Send` (safe to move to a thread), `Sync` (safe to share between threads). The compiler checks them to enforce data-race-free concurrency at compile time, which is the machinery behind fearless concurrency. You rarely implement them, but understanding them explains why the guarantees hold. Next: message passing — the other concurrency paradigm, using channels.

## Key takeaways

- `Send` and `Sync` are marker traits (no methods, just meaning) that encode thread-safety in the type system: a type is `Send` if it's safe to *move* to another thread, and `Sync` if it's safe to *share by reference* (`&T`) between threads — roughly, `Send` is about moving the value, `Sync` about sharing references to it.
- They're auto traits — the compiler *automatically* implements them for types whose components are all `Send`/`Sync` — so most types get thread-safety automatically (why concurrency "just works" for ordinary safe types), while non-thread-safe types opt out (e.g. `Rc` isn't `Send` because its reference counting isn't atomic, whereas `Arc` is).
- The compiler enforces thread-safety by *checking* these traits: `thread::spawn` requires the moved data to be `Send` (rejecting `Rc`), and sharing across threads requires `Sync` — so `Send`/`Sync` are the machinery implementing Rust's compile-time data-race prevention (when the compiler stops a data race, it's checking these traits).
- In practice you rarely implement `Send`/`Sync` (they're automatic) — you mostly benefit from them (free thread-safety checking) and encounter them in compiler errors (like "cannot be sent between threads safely"), which understanding them makes sensible (the fix is often using `Arc` instead of `Rc`).
- `Send`/`Sync` explain *why* fearless concurrency works — it's not magic but a precise, checkable, automatically-propagated encoding of thread-safety in the type system, enforced at compile time — embodying Rust's philosophy of achieving safety (memory and concurrency alike) through the type system rather than runtime checks or programmer discipline.

## Further reading

- [The Rust Book — Extensible Concurrency with Sync and Send](https://doc.rust-lang.org/book/ch16-04-extensible-concurrency-sync-and-send.html)
- [Shared state: Arc and Mutex (previous post)](/blog/posts/rust-18-shared-state-arc-mutex.html)
- [Rust: Traits (Module 2)](/blog/posts/rust-11-traits.html)
