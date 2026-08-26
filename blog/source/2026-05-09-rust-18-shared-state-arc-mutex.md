# Shared State: Arc and Mutex

*Moving data into a single thread is safe but limiting — sometimes multiple threads genuinely need to share and mutate the same data. This is exactly where data races live in other languages, and where Rust's guarantees shine brightest. The answer is a pair of types, `Arc` and `Mutex`, that let you share mutable state across threads — and the compiler will refuse to compile code that shares it unsafely. You literally cannot forget the lock, because the data lives inside it.*

The previous post moved data *into* one thread. This post covers *sharing* mutable data *across* threads safely, using **`Arc`** (atomic reference counting for shared ownership) and **`Mutex`** (mutual exclusion for safe mutation). Together, `Arc<Mutex<T>>` is the standard Rust idiom for shared mutable state across threads — and the type system ensures you use it correctly. This is where Rust's fearless concurrency handles the hardest case: genuinely shared state.

## The problem: sharing across threads

To share data across threads, you need *shared ownership* (multiple threads owning the data) and *safe mutation* (no data races when mutating). Rust's ownership rules make the naive approaches fail to compile — for good reason:

- **`Rc` won't work across threads.** In Module 2, `Rc<T>` provided shared ownership (multiple owners of the same data) — but `Rc` is *not thread-safe* (its reference counting isn't atomic), so the compiler *won't let you* send an `Rc` across threads. Rust catches this at compile time: you can't use the non-thread-safe `Rc` for cross-thread sharing. This is the compiler preventing a real bug.
- **Plain shared mutable data is forbidden.** Rust's borrowing rules (one mutable reference XOR many shared references — Module 1) forbid multiple threads mutating shared data — because that's exactly a data race. So you *can't* just share `&mut` data across threads. The compiler stops the unsafe pattern.
- **You need thread-safe shared ownership + synchronized mutation.** Sharing mutable state across threads safely requires two things: a *thread-safe* way to share *ownership* (so multiple threads can own the data) and a way to *synchronize mutation* (so only one thread mutates at a time — no races). Rust provides these as `Arc` (shared ownership) and `Mutex` (synchronized mutation), used together.

Sharing mutable state across threads needs thread-safe shared ownership *and* synchronized mutation — and Rust's compiler forbids the unsafe approaches (`Rc` across threads, plain shared `&mut`), forcing you toward the safe tools. Those tools are `Arc` and `Mutex`.

## `Mutex`: synchronized mutation

A **`Mutex<T>`** (mutual exclusion) protects data so only *one* thread can access it at a time — and in Rust, the data lives *inside* the mutex, so you *can't* access it without locking:

```rust
use std::sync::Mutex;

fn main() {
    let m = Mutex::new(5);

    {
        // lock() returns a guard; access the data through it.
        let mut num = m.lock().unwrap();
        *num = 6;
    } // the lock is released here, when `num` goes out of scope

    println!("m = {m:?}");
}
```

- **The data lives inside the `Mutex`.** Unlike languages where a mutex is a *separate* lock you must remember to acquire, in Rust the data is *inside* the `Mutex<T>` — and the *only* way to access it is to `lock()` first. You *can't forget the lock*, because there's no way to reach the data without locking. The type system enforces correct locking. This eliminates the classic "forgot to lock" bug.
- **`lock()` returns a guard.** `m.lock()` returns a `Result` containing a `MutexGuard` (here unwrapped) — a smart pointer that gives access to the inner data (via `*num`) and, crucially, *releases the lock automatically when it goes out of scope* (RAII — like the smart pointers from Module 2). You don't manually unlock; the lock releases when the guard is dropped. No forgotten unlocks.
- **Only one thread holds the lock at a time.** While one thread holds the lock (has the guard), others calling `lock()` *block* until it's released. This *mutual exclusion* ensures only one thread accesses the data at a time — preventing data races on mutation. The mutex synchronizes access.

A `Mutex<T>` provides synchronized mutation — the data lives inside it, `lock()` gives access via a guard that auto-releases (so you can't forget to lock or unlock), and only one thread holds the lock at a time. But a single `Mutex` alone can't be *shared* across threads (ownership) — that needs `Arc`.

## `Arc`: thread-safe shared ownership

**`Arc<T>`** (Atomically Reference Counted) is the thread-safe version of `Rc<T>` — it provides *shared ownership* across threads:

- **`Arc` is thread-safe `Rc`.** `Arc<T>` works like `Rc<T>` (shared ownership via reference counting — Module 2) but its reference counting is *atomic* (thread-safe), so it *can* be shared across threads. You clone an `Arc` to get another owner (incrementing the atomic count), and each thread can own an `Arc` pointing to the same data. `Arc` is how multiple threads share ownership of data. (It has slightly more overhead than `Rc` due to atomics, so use `Rc` for single-threaded, `Arc` for multi-threaded.)
- **Combine `Arc` and `Mutex` for shared mutable state.** To share *mutable* state across threads, combine them: `Arc<Mutex<T>>` — `Arc` for *thread-safe shared ownership* (multiple threads own it) and `Mutex` for *synchronized mutation* (safe to mutate). Each thread gets an `Arc` clone (shared ownership), and locks the `Mutex` to mutate safely. `Arc<Mutex<T>>` is the standard idiom for shared mutable state across threads.

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let mut handles = vec![];

    for _ in 0..10 {
        let counter = Arc::clone(&counter); // clone the Arc: another owner
        let handle = thread::spawn(move || {
            let mut num = counter.lock().unwrap();
            *num += 1;
        });
        handles.push(handle);
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("Result: {}", *counter.lock().unwrap()); // 10
}
```

- **How it works.** `Arc::new(Mutex::new(0))` creates shared, lockable state. Each thread gets an `Arc::clone` (a shared owner) *moved* into it, locks the `Mutex` to increment, and the guard auto-releases. Ten threads safely increment the shared counter to 10 — no data race, guaranteed by the compiler.

`Arc<Mutex<T>>` combines `Arc` (thread-safe shared ownership) with `Mutex` (synchronized mutation) to safely share mutable state across threads — the standard Rust idiom. Each thread clones the `Arc` (shared owner) and locks the `Mutex` to mutate. The compiler ensures this is race-free. And it enforces exactly this correctness.

## The compiler enforces correctness

The remarkable thing is that the *compiler* ensures you use shared state safely — you can't easily get it wrong, which is fearless concurrency in action:

- **You can't share unsafely.** The compiler *won't compile* unsafe sharing: it rejects `Rc` across threads (not thread-safe), rejects sharing plain mutable data (data race), and requires the thread-safe tools. If your cross-thread sharing compiles, it's (as far as data races go) *safe*. The compiler is your data-race checker. Unsafe sharing is a compile error, not a runtime bug.
- **You can't forget to lock.** Because the data lives *inside* the `Mutex`, you *must* lock to access it — you can't accidentally access shared data without the lock (a classic concurrency bug in other languages). The type system makes forgetting the lock impossible. The lock isn't a discipline you must remember; it's structurally enforced.
- **The `Send` and `Sync` traits enforce it (next post).** Under the hood, the compiler uses two marker traits — `Send` and `Sync` (the next post) — to determine what can safely cross threads. `Arc<Mutex<T>>` is safe to share because these traits are satisfied; `Rc` isn't `Send`, so the compiler rejects it. These traits are the mechanism behind the compile-time safety. The next post explains how the compiler knows.
- **This is fearless concurrency for shared state.** Even the hardest case — genuinely shared mutable state, the classic home of data races — is made safe by Rust: the compiler guarantees no data races, using ownership, `Arc`/`Mutex`, and the `Send`/`Sync` traits. You share state, and the compiler proves it's race-free. Concurrency's scariest territory becomes compile-time-checked. That's fearless concurrency at its strongest.

Shared mutable state across threads — concurrency's hardest, most dangerous case — is made safe in Rust by `Arc<Mutex<T>>` (`Arc` for thread-safe shared ownership, `Mutex` for synchronized mutation with the data inside the lock), and the compiler *enforces* correct use (can't share unsafely, can't forget to lock). This is fearless concurrency for shared state. The traits that make it work — `Send` and `Sync` — are next.

## Key takeaways

- Sharing mutable state across threads needs thread-safe shared *ownership* and synchronized *mutation*, and Rust's compiler forbids the unsafe approaches — `Rc` isn't thread-safe (rejected across threads) and plain shared `&mut` data is a data race (forbidden by borrowing rules) — forcing you toward the safe tools.
- `Mutex<T>` provides synchronized mutation with the data living *inside* the mutex: the only way to access it is `lock()`, which returns a guard (smart pointer) that gives access and auto-releases the lock when dropped (RAII) — so you can't forget to lock *or* unlock, eliminating classic mutex bugs, and only one thread holds the lock at a time.
- `Arc<T>` (Atomically Reference Counted) is the thread-safe version of `Rc<T>` — shared ownership via *atomic* reference counting, so it can cross threads (clone it for another owner); use `Rc` for single-threaded, `Arc` for multi-threaded (Arc has slight atomic overhead).
- `Arc<Mutex<T>>` is the standard idiom for shared mutable state across threads — `Arc` for thread-safe shared ownership (each thread gets a clone, moved in) and `Mutex` for synchronized mutation (lock to mutate safely) — e.g. ten threads safely incrementing a shared counter, guaranteed race-free by the compiler.
- The compiler *enforces* correctness (fearless concurrency for shared state): it won't compile unsafe sharing (rejecting `Rc` across threads or shared `&mut`), you can't forget to lock (the data lives inside the `Mutex`), and it uses the `Send`/`Sync` marker traits (next post) to determine what safely crosses threads — so concurrency's scariest territory becomes compile-time-checked.

## Further reading

- [The Rust Book — Shared-State Concurrency](https://doc.rust-lang.org/book/ch16-03-shared-state.html)
- [Rust std::sync::Mutex documentation](https://doc.rust-lang.org/std/sync/struct.Mutex.html)
- [Threads and fearless concurrency (previous post)](/blog/posts/rust-17-threads-and-concurrency.html)
