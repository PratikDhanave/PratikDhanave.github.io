# Message Passing with Channels

*There are two great philosophies of concurrency: share memory (with locks, as the previous posts covered) or share nothing and communicate by passing messages. The message-passing school has a famous slogan — "do not communicate by sharing memory; instead, share memory by communicating" — and Rust supports it fully with channels. Instead of multiple threads carefully locking shared state, ownership of data is transferred from one thread to another through a channel, and Rust's ownership system makes that transfer clean and safe.*

This post covers the other major concurrency paradigm: **message passing** via **channels**. Instead of sharing state (`Arc<Mutex<T>>`), threads *communicate* by sending data through channels — transferring *ownership* of the data. Rust provides channels in `std::sync::mpsc`, and its ownership model makes message passing especially natural (sending transfers ownership). This post covers channels, sending and receiving, and why message passing is often a cleaner concurrency approach.

## The message-passing idea

**Message passing** is a concurrency approach where threads communicate by *sending messages* (data) to each other, rather than *sharing* mutable state. The philosophy:

- **Communicate instead of sharing.** Rather than multiple threads accessing shared mutable state (with locks), message passing has threads *own their own data* and *send messages* to communicate — a thread sends data to another thread, transferring it. The slogan (from Go, but apt for Rust): "do not communicate by sharing memory; instead, share memory by communicating." Threads pass data rather than sharing it. Communication over sharing.
- **It avoids shared-state complexity.** By transferring data rather than sharing it, message passing *avoids* much of the complexity and risk of shared mutable state (locks, races, deadlocks). Each thread works on data it owns, and ownership *moves* between threads via messages — no simultaneous shared access. This can make concurrent code simpler and safer to reason about. Passing ownership sidesteps sharing problems.
- **It fits Rust's ownership model perfectly.** Message passing aligns beautifully with Rust's *ownership*: sending data through a channel *transfers ownership* of it (a move — Module 1) from sender to receiver. After sending, the sender no longer owns the data (can't use it); the receiver does. Rust's move semantics make message passing clean — ownership transfer is exactly what sending is. Rust and message passing are a natural fit. Sending is moving.

Message passing — threads communicating by sending data (transferring ownership) rather than sharing mutable state — avoids shared-state complexity and fits Rust's ownership model perfectly (sending *is* transferring ownership, a move). It's an alternative to the `Arc<Mutex<T>>` shared-state approach. Rust implements it with channels.

## Channels: sending and receiving

Rust provides channels in `std::sync::mpsc` (multiple producer, single consumer). A channel has a **transmitter** (sender) and a **receiver**:

```rust
use std::sync::mpsc;
use std::thread;

fn main() {
    // Create a channel: tx (transmitter) and rx (receiver).
    let (tx, rx) = mpsc::channel();

    thread::spawn(move || {
        let val = String::from("hi");
        tx.send(val).unwrap(); // send transfers ownership of `val`
        // `val` can no longer be used here — it was moved into the channel
    });

    // Receive blocks until a value arrives.
    let received = rx.recv().unwrap();
    println!("Got: {received}");
}
```

- **Create a channel with `mpsc::channel()`.** It returns a tuple: a *transmitter* (`tx`) to send, and a *receiver* (`rx`) to receive. You move `tx` into the sending thread and keep `rx` for receiving. The channel connects them. `mpsc` = multiple producer, single consumer (you can clone `tx` for multiple senders, but there's one `rx`).
- **`send` transfers ownership.** `tx.send(val)` sends `val` down the channel — *transferring ownership* of it. After `send`, `val` *can't be used* in the sending thread (it was moved). This is Rust's ownership at work: sending *moves* the data, so there's no shared access to it — no data race. `send` returns a `Result` (`Err` if the receiver is gone). Ownership moves through the channel.
- **`recv` receives (and blocks).** `rx.recv()` *blocks* until a value arrives, then returns it (in a `Result`). The receiver now *owns* the received data. So ownership transferred from sender to receiver, cleanly, through the channel. (There's also `try_recv` for non-blocking receipt.) The receiver takes ownership.

A channel (`mpsc::channel()`) gives a transmitter and receiver; `tx.send(val)` transfers ownership of `val` through the channel (after which the sender can't use it — a move), and `rx.recv()` blocks until a value arrives and gives the receiver ownership. Ownership flows cleanly from sender to receiver, with no shared access. Channels also support receiving a stream of values.

## Receiving multiple values

You can send multiple values and receive them by treating the receiver as an *iterator* — a common, clean pattern:

```rust
use std::sync::mpsc;
use std::thread;
use std::time::Duration;

fn main() {
    let (tx, rx) = mpsc::channel();

    thread::spawn(move || {
        let vals = vec![
            String::from("hi"),
            String::from("from"),
            String::from("the"),
            String::from("thread"),
        ];
        for val in vals {
            tx.send(val).unwrap();
            thread::sleep(Duration::from_millis(200));
        }
        // when `tx` is dropped (end of thread), the channel closes
    });

    // Iterating over the receiver yields values until the channel closes.
    for received in rx {
        println!("Got: {received}");
    }
}
```

- **The receiver is an iterator.** Iterating `for received in rx` receives values *one by one* as they arrive, until the channel *closes* — a clean way to process a *stream* of messages. It combines message passing with the iterators from Module 2 (the receiver implements `Iterator`). Elegant: receiving a stream is just iterating.
- **The channel closes when the transmitter is dropped.** When the sending thread ends, `tx` is *dropped*, which *closes* the channel — and the receiving iterator *ends* (the `for` loop finishes). So the loop naturally terminates when the sender is done. Ownership and `Drop` (Module 2) cleanly handle channel closing. No sentinel value needed — dropping `tx` signals the end.
- **Multiple producers.** Since `mpsc` is *multiple producer*, you can `tx.clone()` to get multiple transmitters (for multiple sending threads) all feeding the *one* receiver. This lets many threads send to a single consumer — a common pattern. Multiple senders, one receiver.

Receiving multiple values is clean: iterate over the receiver (`for received in rx`) to get a stream of messages until the channel closes (when the transmitter is dropped), combining message passing with iterators — and `tx.clone()` allows multiple producers feeding one consumer. This makes stream-of-messages concurrency elegant. Message passing is often the cleaner choice.

## Message passing vs shared state

Rust supports *both* concurrency paradigms — message passing (channels) and shared state (`Arc<Mutex<T>>`) — and knowing when to use each is practical wisdom:

- **Message passing: transfer ownership, avoid sharing.** Message passing (channels) *transfers ownership* between threads, avoiding shared mutable state. It's often *simpler and safer to reason about* (no locks, no shared access, no deadlock risk from locking) — each thread owns its data, and data moves between them. Message passing suits *pipelines* and *producer-consumer* patterns (data flowing between threads). It's frequently the cleaner default. Prefer it when data flows between threads.
- **Shared state: when threads genuinely need shared access.** Shared state (`Arc<Mutex<T>>` — previous posts) suits cases where threads genuinely need to *share and access the same data* (like a shared counter, cache, or state many threads read/modify). When the pattern is inherently shared (not data flowing one way), shared state fits — with the compiler ensuring safety. Use it when sharing is the natural model.
- **Both are safe in Rust.** Crucially, *both* paradigms are made *safe* by Rust's ownership and type system — message passing via ownership transfer (send moves data), shared state via `Arc<Mutex<T>>` and `Send`/`Sync`. Rust doesn't force one; it makes *both* fearless. You choose the paradigm that fits the problem, and the compiler ensures safety either way. Safety comes free with both.
- **Often, prefer message passing.** A common guideline: *prefer message passing* where it fits (it's often simpler and avoids shared-state pitfalls), and use shared state when the problem genuinely calls for shared access. Message passing's clarity (and Rust's natural fit for it via ownership transfer) makes it an attractive default for many concurrent designs. When in doubt and data flows between threads, reach for channels. Communicate by passing when you can.

Rust supports both message passing (channels — transfer ownership, avoid sharing, often simpler, fits pipelines/producer-consumer) and shared state (`Arc<Mutex<T>>` — for genuinely shared access), both made safe by the ownership/type system — and message passing is often the cleaner default (prefer it where it fits). This completes the concurrency core; next we turn to a different topic — testing in Rust.

## Key takeaways

- Message passing is a concurrency approach where threads *communicate by sending data* (transferring ownership) rather than *sharing* mutable state — following the slogan "share memory by communicating" — which avoids shared-state complexity (locks, races, deadlocks) and fits Rust's ownership model perfectly (sending *is* transferring ownership, a move).
- Rust provides channels via `std::sync::mpsc` (multiple producer, single consumer): `mpsc::channel()` returns a transmitter (`tx`) and receiver (`rx`); `tx.send(val)` transfers ownership of `val` through the channel (after which the sender can't use it — a move, so no data race), and `rx.recv()` blocks until a value arrives and gives the receiver ownership.
- You can receive a stream of values by iterating over the receiver (`for received in rx`), which yields values until the channel *closes* (when the transmitter is dropped — ownership/Drop handles this cleanly, no sentinel needed), combining message passing with iterators; `tx.clone()` allows multiple producers feeding one consumer.
- Rust supports both concurrency paradigms and both are safe: message passing (channels — transfer ownership, often simpler, suits pipelines/producer-consumer) and shared state (`Arc<Mutex<T>>` — for genuinely shared access) — you choose the paradigm fitting the problem, and the compiler ensures safety either way (via ownership transfer or `Send`/`Sync`).
- A common guideline is to prefer message passing where it fits (its clarity and Rust's natural fit for it via ownership transfer make it an attractive default) and use shared state when the problem genuinely calls for shared access.

## Further reading

- [The Rust Book — Using Message Passing to Transfer Data Between Threads](https://doc.rust-lang.org/book/ch16-02-message-passing.html)
- [Send and Sync (previous post)](/blog/posts/rust-19-send-and-sync.html)
- [Rust: Iterators (Module 2)](/blog/posts/rust-14-iterators.html)
