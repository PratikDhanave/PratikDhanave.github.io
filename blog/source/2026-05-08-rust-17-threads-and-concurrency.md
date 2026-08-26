# Threads and Fearless Concurrency

*Rust's boldest promise is "fearless concurrency" — the claim that you can write multithreaded code and have the compiler guarantee, at compile time, that you have no data races. Coming from languages where concurrency bugs are a dark art of subtle, intermittent horror, this sounds too good to be true. It isn't: the same ownership and borrowing rules that give Rust memory safety extend naturally to threads. This module explores concurrency, starting with the basics — spawning threads and moving data into them.*

This post opens **Module 3** of *Rust from the Ground Up* — concurrency, async, testing, and macros. We start with **threads**: spawning them with `std::thread`, joining them, and the crucial role of `move` closures in getting data safely into threads. Rust's ownership system, which you learned in Module 1, turns out to be exactly what makes concurrency safe — the compiler prevents data races using the same rules that prevent memory bugs. This is "fearless concurrency," and it starts here.

## Spawning threads

Rust's standard library provides threads via `std::thread`. You spawn a thread with `thread::spawn`, passing a closure with the code to run:

```rust
use std::thread;

fn main() {
    // Spawn a new thread that runs the closure.
    thread::spawn(|| {
        for i in 1..5 {
            println!("hi number {i} from the spawned thread");
        }
    });

    for i in 1..3 {
        println!("hi number {i} from the main thread");
    }
}
```

- **`thread::spawn` takes a closure.** You pass `spawn` a closure containing the code the new thread will run. The spawned thread runs concurrently with the thread that spawned it. The `main` thread and the spawned thread now execute independently.
- **Threads run independently and unpredictably.** The two threads' output *interleaves* unpredictably — the OS scheduler decides when each runs (as the OS series covered). You can't assume any ordering between threads; they run concurrently.
- **The main thread doesn't wait by default.** A subtlety: when `main` returns, the program exits — *even if spawned threads haven't finished*. So the spawned thread above might not complete all its iterations before `main` ends. To ensure a spawned thread finishes, you need to *join* it.

Spawning a thread is simple — `thread::spawn` with a closure — but the spawned thread runs independently and won't necessarily finish before `main` exits. Controlling that requires joining.

## Joining threads

`thread::spawn` returns a `JoinHandle`. Calling `.join()` on it *waits* for that thread to finish:

```rust
use std::thread;

fn main() {
    let handle = thread::spawn(|| {
        for i in 1..5 {
            println!("hi number {i} from the spawned thread");
        }
    });

    for i in 1..3 {
        println!("hi number {i} from the main thread");
    }

    // Wait for the spawned thread to finish before continuing.
    handle.join().unwrap();
}
```

- **`join` blocks until the thread finishes.** Calling `handle.join()` makes the current thread *wait* until the spawned thread completes. Placing it after the main loop ensures the spawned thread runs to completion before `main` ends. Now the spawned thread's output is guaranteed to all appear.
- **`join` returns a `Result`.** `join()` returns `Result` — `Ok` if the thread finished normally, `Err` if it *panicked*. The `.unwrap()` here propagates a panic from the spawned thread. This is how a thread's completion (and failure) is surfaced to the joiner.
- **Where you place `join` matters.** If you `join` *before* the main loop instead of after, the main thread would wait for the spawned thread *first*, serializing them (no concurrency). Placing `join` after the work you want to run concurrently is what lets both threads run in parallel, then synchronizes at the end.

`join` gives you control over thread completion — wait for a thread to finish (and observe whether it panicked) — which is essential for coordinating threads. But the more interesting question is getting *data* into a thread safely, which is where ownership meets concurrency.

## `move` closures: getting data into threads

Threads usually need *data*. To use data from the surrounding scope in a thread, the closure must *take ownership* of it with the `move` keyword — and understanding why reveals how ownership makes threads safe:

```rust
use std::thread;

fn main() {
    let v = vec![1, 2, 3];

    // `move` transfers ownership of `v` into the thread's closure.
    let handle = thread::spawn(move || {
        println!("Here's a vector: {v:?}");
    });

    handle.join().unwrap();
}
```

- **Why `move` is required.** Without `move`, the closure would *borrow* `v` — but the spawned thread might outlive the scope where `v` lives, leaving a *dangling reference*. Rust *won't allow* this (it can't guarantee `v` outlives the thread). The `move` keyword makes the closure *take ownership* of `v`, moving it into the thread — so the thread owns the data and there's no dangling-reference risk. The compiler *requires* `move` here.
- **Ownership prevents data races.** This is the key insight: because `v` is *moved* into the thread, the original scope can *no longer use* `v` (it was moved — Module 1's move semantics). So there's no way for two threads to access `v` simultaneously through this path — ownership *transferred* it to one thread. Rust's ownership rules, applied to threads, prevent the shared-mutable-access that causes data races. The same rules that gave memory safety give concurrency safety.
- **This is fearless concurrency's foundation.** Because ownership is transferred (not shared) by default, and the compiler enforces it, you *can't accidentally* share data unsafely between threads — the compiler stops you at compile time. This compile-time prevention of data races is "fearless concurrency": you write threaded code, and the compiler guarantees no data races. What's a runtime horror in other languages is a compile error in Rust.

`move` closures transfer ownership of data into a thread, which the compiler requires to prevent dangling references — and this same ownership transfer prevents data races, because data moved into a thread can't be simultaneously accessed elsewhere. This is the foundation of fearless concurrency: Rust's ownership rules make threads safe at compile time. But sometimes you genuinely need to *share* data between threads — which needs the tools of the next post.

## Key takeaways

- Rust provides threads via `std::thread::spawn`, which takes a closure containing the code to run concurrently; the spawned thread runs independently and its output interleaves unpredictably with other threads (the OS scheduler decides ordering).
- By default the program exits when `main` returns, even if spawned threads haven't finished — so `thread::spawn` returns a `JoinHandle`, and calling `.join()` blocks until that thread completes (returning a `Result` that's `Err` if the thread panicked); placing `join` after the concurrent work lets threads run in parallel then synchronize.
- Threads that use data from the surrounding scope need a `move` closure (`thread::spawn(move || ...)`) that *takes ownership* of the data — the compiler *requires* this because otherwise the closure would borrow data that might not outlive the thread (a dangling reference).
- The deep insight is that ownership prevents data races: because data is *moved* into a thread (not shared), the original scope can no longer access it (move semantics from Module 1), so two threads can't simultaneously access it through that path — Rust's ownership rules, applied to threads, prevent data races.
- This is "fearless concurrency": the same compile-time ownership/borrowing rules that give memory safety also guarantee no data races, so what's a subtle intermittent runtime horror in other languages is a compile error in Rust — you write threaded code and the compiler proves it's race-free.

## Further reading

- [The Rust Book — Using Threads to Run Code Simultaneously](https://doc.rust-lang.org/book/ch16-01-threads.html)
- [The Rust Book — Fearless Concurrency (overview)](https://doc.rust-lang.org/book/ch16-00-concurrency.html)
- [Rust: Ownership (Module 1)](/blog/posts/rust-04-ownership.html)
