# Designing a Deterministic Order-Book Matching Engine

*How price-time priority, a single-threaded sequencer, and gap-free event streaming combine into an exchange core you can replay byte-for-byte.*

A matching engine is the smallest possible piece of an exchange that has to be perfectly correct. Everything around it — gateways, risk checks, market-data fan-out, clearing — can be scaled, retried, and load-balanced with ordinary distributed-systems tools. The core itself cannot. The moment two orders can match against the book in a non-deterministic order, you lose the one property the whole venue is sold on: that every participant sees the same book evolve the same way, and that you can prove it after the fact.

This post walks through the engineering decisions that give you that property: how the book is structured for price-time priority, why the hot path is single-threaded on purpose, how order types fold into one match loop, and how the engine emits a gap-free event stream that doubles as its own replay log.

## The order book as two priced ladders

An order book is two sorted collections: bids (descending by price) and asks (ascending by price). Within a price level, resting orders queue in arrival order — this is the "time" in price-time priority. The data structure choice is driven entirely by the operations the match loop performs: read the best price, walk orders at a level in FIFO order, and insert or cancel at an arbitrary level.

A common and cache-friendly layout is a map from price level to an intrusive doubly-linked list of orders, plus a structure that tracks the best bid and best ask cheaply. Prices are stored as integer ticks, never floats — a price is `mantissa * 10^-scale` carried as an `int64`, so comparisons are exact and the "best price" is an integer min/max.

```
        BIDS (buy)                    ASKS (sell)
  price   qty   FIFO queue      price   qty   FIFO queue
  ┌──────────────────────┐     ┌──────────────────────┐
  │ 100.03  5  [o7,o2]    │     │ 100.05  8  [o4]      │  ← best ask
  │ 100.02  12 [o9]       │     │ 100.06  3  [o1,o5]   │
  │ 100.01  4  [o3,o8,o6] │     │ 100.07  20 [o11]     │
  └──────────────────────┘     └──────────────────────┘
     ↑ best bid 100.03            spread = 100.05 - 100.03
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-matching-engine-design.html)** — pan, zoom, and trace every step (light/dark, self-contained).

An incoming buy order at 100.06 crosses the spread: it matches the best ask (100.05, qty 8) first, then walks up to 100.06 until it is filled or its limit price is exhausted. Each match generates a trade at the *resting* order's price — the passive side sets the price, the aggressor pays it. That single rule, applied consistently, is what makes the book fair and auditable.

## Order types are variations on one match loop

It is tempting to write a separate handler per order type. Resist it. Every order type is a combination of three independent parameters: a limit price (or none, for market orders), a time-in-force, and a fill constraint. Model them as fields, then run one loop.

- **Limit** — match against the opposite side while the price crosses; rest the remainder on the book.
- **Market** — a limit with no price bound; match until filled or the book is empty, never rest.
- **IOC (immediate-or-cancel)** — match what you can right now, cancel the remainder instead of resting.
- **FOK (fill-or-kill)** — a pre-check: if the available liquidity across levels cannot fully fill the order, reject it whole before mutating any state.

The FOK pre-check is the only one that needs a "dry run" pass over the book before committing. Everything else is the same walk: peek the best opposing level, take `min(incoming_qty, resting_qty)`, emit a trade, decrement both, advance the FIFO queue when a resting order is exhausted. When you are done, the residual either rests, cancels, or the order was rejected. One loop, four behaviors selected by fields.

## Determinism means one thread and one clock

Here is the decision that surprises engineers coming from typical service work: the match loop runs on a single thread, and that is a feature, not a bottleneck. The instant you introduce concurrency into the book, order of execution depends on scheduler timing, and two replays of the same inputs can diverge. Determinism requires that the sequence of state transitions be a pure function of the input sequence.

So the architecture front-loads all the non-deterministic work — network I/O, parsing, credit and risk checks, memory allocation — into stages *before* the core, and drains everything else *after* it.

```
  gateways ──▶ sequencer ──▶ [ matching core ]  ──▶ event stream
  (parse,      (assign a       (single thread,       (trades +
   validate)    global seq #)   pure function)        book deltas)
```

The **sequencer** is the linearization point. It takes validated orders from many gateways and stamps each with a monotonic sequence number, producing one canonical input stream. From that point on, the sequence number *is* the clock — the engine never reads wall-clock time inside a decision, because wall-clock time is not reproducible. Any timestamp a trade needs is derived from the sequenced input, not from `now()`.

A well-tuned single-threaded core matches on the order of millions of operations per second because the working set stays in cache and there are no locks. Scaling out is done by *sharding by instrument* — each symbol (or group of symbols) owns an independent single-threaded engine — not by parallelizing one book.

## The event stream is the source of truth

The core does not "update a database." It emits an ordered stream of events — a trade event for every match, a book-delta event for every add, cancel, or fill that changes a price level. This stream is the primary artifact. Two very different consumers read it:

- **Market data**, which reconstructs the public book and trade tape for participants.
- **Clearing and settlement**, which turns fills into positions and money movement downstream.

Because every event carries the sequence number of the input that produced it, the stream is *gap-free and ordered by construction*. A consumer that receives event `N+2` after `N` knows `N+1` is missing and can request a replay rather than silently showing a wrong book. This is the same discipline as a database write-ahead log: append first, derive views later.

## Replay is what makes it auditable

Persist the sequenced input stream to an append-only journal, and the engine gains its most valuable property: **it can be rebuilt exactly by replaying its inputs.** Start a fresh engine at an empty book, feed it the journaled inputs in sequence order, and it produces bit-for-bit the same trades and book deltas as the original run — because the core is a pure function of that sequence and reads no external clock or random source.

This underwrites several things at once. Recovery is just replay from the last snapshot. A hot standby is an identical engine consuming the same sequenced stream, ready to take over at a known offset. And a dispute — "why did my order not fill?" — is answered by replaying to the exact sequence number and inspecting the book, not by guessing from logs.

```
  journal ──▶ replay ──▶ fresh engine ──▶ identical trades
  (inputs)   (in seq order)               (bit-for-bit)
```

To keep replay bounded, snapshot the full book state at periodic sequence numbers. Recovery then loads the latest snapshot and replays only the tail of inputs after it. The snapshot must be taken *between* sequenced inputs, never mid-match, so it always represents a clean, reproducible state boundary.

## What to get right first

If you build one of these, the invariants matter more than throughput. Integer prices and quantities, never floats. A sequencer that is the single linearization point, so ordering is decided once. A core that reads no clock, no random source, and no shared mutable state outside the book. And an event stream that is append-only and gap-checked end to end. Get those four right and you have an engine whose behavior you can prove; optimize the match loop afterward, because a fast engine that cannot be replayed is not an exchange core — it is a liability with good latency numbers.
