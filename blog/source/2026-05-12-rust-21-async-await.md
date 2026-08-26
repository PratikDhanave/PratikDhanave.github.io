# Async and Await

*Threads are great for CPU-bound parallelism, but for handling thousands of network connections — each mostly waiting — spawning a thread per connection doesn't scale (recall the C10K problem from the OS series). Async/await is Rust's answer: write code that looks sequential but doesn't block a thread while waiting, letting a handful of threads handle enormous concurrency. Rust's async is powerful and zero-cost, with one distinctive twist — you bring your own runtime to actually run the async code.*

This post covers **async/await** — Rust's approach to *asynchronous*, non-blocking concurrency, ideal for I/O-bound work at high concurrency. It covers what async is (and how it differs from threads), `async`/`await` syntax, **futures**, and the role of the **runtime**. Async is a large topic; this post gives the conceptual foundation and the essential mechanics. It connects to the I/O-models ideas from the OS series — async is how you get high-concurrency non-blocking I/O.

## Async vs threads

**Async** (asynchronous) programming is a *different* model from threads — non-blocking concurrency suited to *I/O-bound* work at *high concurrency*:

- **Threads suit CPU-bound work; async suits I/O-bound.** *Threads* (previous posts) give parallelism for *CPU-bound* work (using multiple cores) but are relatively *heavy* (each has a stack, context-switch cost — the OS series). *Async* suits *I/O-bound* work (lots of waiting on network/disk) at *high concurrency* — where you have *many* tasks mostly *waiting*, and spawning a thread per task doesn't scale (the C10K problem, OS series). Async lets few threads handle many waiting tasks. Different tools for different workloads.
- **Async doesn't block while waiting.** The key idea: when an async task *waits* (e.g. for I/O), it *doesn't block a thread* — instead it *yields*, letting the thread do *other* work, and resumes when the I/O is ready. So one thread can handle *many* async tasks by working on whichever is ready and not blocking on the waiting ones. This is how async achieves high concurrency with few threads — non-blocking waiting. Waiting tasks don't hog threads.
- **It's the "async/await" model.** This non-blocking concurrency is expressed via `async`/`await` (the same model as in many modern languages, but zero-cost in Rust): write async functions, `await` operations that might wait, and the runtime multiplexes many async tasks over few threads. It's cooperative, non-blocking concurrency. (This is the event-loop / async I/O model from the OS series, in Rust.) Familiar syntax, Rust semantics.

Async is a different concurrency model from threads — non-blocking, suited to I/O-bound work at high concurrency (many tasks mostly waiting), where tasks *yield* instead of blocking a thread while waiting, letting few threads handle many tasks. It's the async/await model (the OS series' async I/O). Rust expresses it with `async` and `await`.

## async and await syntax

Rust's async syntax centers on `async` (marking async functions) and `.await` (awaiting async operations):

```rust
// An async function returns a Future; its body doesn't run until awaited.
async fn fetch_data() -> String {
    // ... imagine async I/O here ...
    String::from("data")
}

async fn process() {
    // .await runs the future, yielding while it waits, resuming when ready.
    let data = fetch_data().await;
    println!("Got: {data}");
}
```

- **`async fn` returns a future.** Marking a function `async` makes it return a *future* (below) instead of running immediately — calling `fetch_data()` returns a future that, when *run*, will produce the `String`. An `async` function's body doesn't execute when called; it's packaged into a future to be run later. `async` makes a function into a future-producer. Calling it does nothing until awaited.
- **`.await` runs a future, yielding while waiting.** `.await` on a future *runs* it — and, crucially, *yields* if the future isn't ready (letting other tasks run), *resuming* when it is. `fetch_data().await` runs the fetch, yielding the thread while waiting, resuming with the result when ready. `.await` is where the non-blocking waiting happens — it's a *yield point*. This is the heart of async: `.await` waits without blocking. Await = non-blocking wait.
- **Async is contagious (and composable).** `.await` can only be used *inside* `async` functions — so async "spreads" through your code (async functions calling async functions). This lets you *compose* async operations naturally (await one, then another) writing *sequential-looking* code that's actually non-blocking. Async code reads like sequential code but doesn't block — the appeal of async/await. It looks synchronous, behaves asynchronously.

`async fn` returns a future (its body doesn't run until awaited), and `.await` runs a future while *yielding* if it's not ready (non-blocking waiting) and resuming when ready — letting you write sequential-looking, non-blocking code. `.await` (usable only in `async` functions) is the yield point. Understanding what a future *is* clarifies the model.

## Futures: the foundation

A **future** is the core async abstraction — a value representing a computation that will *complete later*:

- **A future is a deferred computation.** A `Future` represents an async operation that *hasn't completed yet* but *will produce a value* eventually. An `async fn` returns a future; the future is the *promise* of a result to come. It's a computation-in-progress (or not-yet-started) that will yield a value when it's done. A future is "a value, later."
- **Futures are lazy — they do nothing until polled.** Crucially, Rust futures are *lazy*: creating a future (calling an `async fn`) does *nothing* — the computation only runs when the future is *driven* (polled) to completion, which happens when you `.await` it (and, ultimately, when a runtime runs it). This laziness is distinctive (in some languages async operations start immediately); in Rust, a future is inert until run. You must *drive* a future for it to do anything. No runtime → nothing runs. Lazy futures are a Rust hallmark.
- **The runtime polls futures.** A future advances by being *polled* — the runtime (below) *polls* the future, which either completes (returns its value) or signals it's *not ready yet* (pending, will be polled again when progress is possible). This polling model is how futures make progress without blocking — polled, yields if pending, polled again when ready. The runtime does this polling for you. Polling drives futures forward.
- **Futures compose and are zero-cost.** Futures *compose* (a future can await other futures, building complex async operations from simple ones), and Rust's futures are *zero-cost* — the async machinery compiles to efficient state machines with no required runtime overhead beyond what you use. Rust's async is high-performance (zero-cost abstraction, like the rest of Rust — Module 2). Efficient and composable.

A future is Rust's core async abstraction — a lazy, deferred computation that produces a value later, doing nothing until *driven* (polled) to completion (typically via `.await` and ultimately a runtime). Futures are lazy (inert until run), advanced by polling, composable, and zero-cost. Because futures are lazy and need polling, Rust async has a distinctive requirement: a runtime.

## The runtime: bring your own

Rust's most distinctive async trait: the language provides `async`/`await` and futures, but *not* a **runtime** to run them — you *bring your own*:

- **Rust has no built-in async runtime.** Unlike some languages, Rust's *standard library* provides the async *syntax* (`async`/`await`) and the `Future` trait, but *not* an executor/runtime to actually *run* futures. Because futures are lazy (do nothing until driven), you need a *runtime* to poll them to completion — and Rust doesn't include one. You must add a runtime. This is unusual and initially surprising: async Rust needs an external runtime. No runtime, no async execution.
- **You use a runtime crate.** In practice, you use a *runtime crate* — the most common being **Tokio** (and others like async-std) — that provides the *executor* (which polls/runs futures), plus async I/O and utilities. You add the runtime as a dependency and use it to run your async code (often via an attribute like `#[tokio::main]` on `main`). The runtime is what actually *executes* the async tasks. Tokio is the de facto standard. You pick a runtime and it drives your futures.
- **Why bring-your-own-runtime.** Rust's design leaves the runtime *out of the standard library* so that different runtimes can suit different needs (Tokio for general async, others for specific niches, custom for embedded) — Rust doesn't impose one, keeping async flexible and zero-cost (you only include the runtime you need). It's the Rust philosophy: provide the mechanism (futures, async/await), let the ecosystem provide the policy (runtimes). Flexibility over a one-size-fits-all built-in. The tradeoff is a bit more setup for a lot more flexibility.
- **Practical upshot.** To write async Rust, you: mark functions `async`, use `.await`, and run it all on a *runtime* (usually Tokio). The runtime multiplexes your many async tasks over a few threads, achieving high-concurrency non-blocking I/O. That's async Rust in practice: async/await + futures + a runtime. Add a runtime, and async works.

Rust's distinctive async trait is bring-your-own-runtime: the language provides `async`/`await` and lazy futures, but you supply a *runtime* (usually Tokio) to actually run them — a design that keeps async flexible and zero-cost. In practice: `async`/`await` + futures + a runtime give high-concurrency non-blocking I/O. Async is a deep topic, but this is its foundation. Next: testing in Rust.

## Key takeaways

- Async is a different concurrency model from threads — non-blocking, suited to I/O-bound work at high concurrency (many tasks mostly waiting), where tasks *yield* instead of blocking a thread while waiting, letting few threads handle many tasks (the OS series' async-I/O / event-loop model, solving C10K); threads suit CPU-bound parallelism, async suits I/O-bound concurrency.
- `async fn` returns a *future* (its body doesn't run when called), and `.await` runs a future while *yielding* if it's not ready (non-blocking waiting) and resuming when ready — letting you write sequential-looking, non-blocking code; `.await` is the yield point, usable only inside `async` functions (so async "spreads" through code).
- A future is Rust's core async abstraction — a lazy, deferred computation producing a value later — that is *lazy* (does nothing until driven/polled to completion), advanced by *polling*, composable, and zero-cost (compiles to efficient state machines); Rust futures being lazy/inert-until-run is distinctive.
- Rust's most distinctive async trait is bring-your-own-runtime: the standard library provides `async`/`await` and the `Future` trait but *no* runtime to run futures — so you add a runtime crate (usually Tokio) that provides the executor to poll futures to completion, plus async I/O (often via `#[tokio::main]`).
- Rust leaves the runtime out of std deliberately (flexibility — different runtimes for different needs, zero-cost by including only what you use), following its philosophy of providing the mechanism (futures, async/await) and letting the ecosystem provide the policy (runtimes); in practice, async/await + futures + a runtime give high-concurrency non-blocking I/O.

## Further reading

- [The Rust Book — Async and Await (Fundamentals)](https://doc.rust-lang.org/book/ch17-00-async-await.html)
- [The Rust Async Book](https://rust-lang.github.io/async-book/)
- [Message passing with channels (previous post)](/blog/posts/rust-20-message-passing-channels.html)
