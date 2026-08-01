# Reconstructing an Order Book from a Market-Data Feed

*Handle a live market-data feed the way an engineer must: sequence checking, gap recovery, and snapshot-plus-delta order-book reconstruction.*

A market-data feed does not hand you a picture of the market. It hands you a stream of edits. Each message says "add 500 lots at 101.25," "the level at 100.90 now has 300," or "100.75 is gone." The order book you trade against is a *reconstruction* — a data structure you maintain locally by applying those edits in exact order. Get the order wrong, drop one message, or apply an edit twice, and your book silently diverges from the exchange's. Nothing crashes. You just start quoting against a book that no longer exists.

This post walks through the engineering that keeps a local book faithful: how sequence numbers form the correctness contract, how you detect and recover from gaps, and how snapshot-plus-delta reconstruction stays deterministic under packet loss.

## The feed is a stream of edits

Most venues publish incremental (L2/L3) updates: per-price-level or per-order deltas rather than a full book on every tick. This is a bandwidth decision. A liquid instrument might see tens of thousands of book changes per second; shipping the entire depth each time would be wasteful and slow. So the venue ships the diff and trusts every consumer to hold identical state and apply identical edits.

That trust is the hard part. The venue has no idea whether your copy of the book matches its own. There is no per-message acknowledgment, no server-side reconciliation. The only thing the venue gives you to prove you are in sync is a monotonically increasing **sequence number** stamped on every message. Sequence numbers are the entire correctness contract. Everything else in this post is machinery built around them.

## Sequence numbers are the contract

Each update on a channel carries a sequence number that increases by exactly one. Your ingest path does one thing before anything else: it checks that the number it just received is the number it expected. If `seq == expected`, apply the delta and bump the expected counter. If `seq < expected`, it is a duplicate or a reorder from a redundant line — discard it. If `seq > expected`, you have missed one or more messages, and the local book is now untrustworthy.

```
   Market Feed              Sequence Check                Order Book
  (seq-numbered)          expected = last + 1           (bids / asks)
        │                        │                            │
        │  delta[seq=n]          │                            │
        ├───────────────────────►│  seq == expected?          │
        │                        │        yes ── apply ──────►│  updated
        │  delta[seq=n+2]        │                            │
        ├───────────────────────►│  seq  >  expected?         │
        │                        │        GAP  ──► recover    │
        │                        │        (snapshot resync)   │
        │                        ▼                            │
        │                 buffer newer deltas, refetch base   │
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-market-data-orderbook-reconstruction.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Notice what the gap check protects. The dangerous case is not the message you lost — it is every message *after* it. Once `seq` jumps ahead, you cannot apply the new delta, because it assumes edits you never saw. Blindly applying it corrupts the book in a way that is invisible until a price crosses or a level goes negative. The only safe response to a gap is to stop applying deltas to the current book and begin recovery.

Many venues run two identical multicast lines (an A feed and a B feed) precisely so a drop on one can be filled from the other. Arbitrating between them is just sequence-number deduplication: take whichever line delivers `expected` first, drop the copy from the other. Line arbitration handles isolated single-packet loss cheaply; the snapshot path below is the fallback when both lines miss the same message.

## Recovering from a gap without losing determinism

Recovery is snapshot-plus-delta. The venue publishes a full book **snapshot** — either on a separate refresh channel or via a request/response endpoint — and each snapshot is itself stamped with the sequence number it is current as of. Call it `snap_seq`. The snapshot is your new known-good base.

The subtle part is the join. Deltas keep flowing while you fetch the snapshot, and the snapshot reflects some point in that stream, not the moment you asked. So the algorithm is:

1. On gap detection, keep receiving deltas but stop applying them to the live book. Buffer them.
2. Request (or wait for) a snapshot; read its `snap_seq`.
3. Discard every buffered delta with `seq <= snap_seq` — the snapshot already includes those edits.
4. Verify the first surviving buffered delta is exactly `snap_seq + 1`. If it is not, the buffer itself has a hole; throw the snapshot away and refetch.
5. Replay the surviving buffer in order onto the snapshot, then resume live application with `expected = last_applied + 1`.

Step 4 is what makes the whole thing deterministic. You never guess and you never interpolate. Either the buffered deltas chain cleanly onto the snapshot's sequence number or you refuse the reconstruction and try again. A book that is briefly stale is a recoverable condition; a book that is silently wrong is not.

## Applying deltas to the book

The book itself is two sorted maps — one for bids, one for asks — keyed by price, valued by resting size (or a queue of orders for L3). Applying a delta is a point edit:

```python
def apply_delta(book_side, price, size):
    if size == 0:
        book_side.pop(price, None)   # level removed
    else:
        book_side[price] = size      # level set to absolute size
```

Two details matter for correctness. First, know whether your venue sends *absolute* level sizes ("100.90 is now 300") or *relative* changes ("100.90 gained 50"). Mixing the two up is a classic reconstruction bug — the book looks plausible for a while, then drifts. Second, treat a size of zero as a delete, not a level with zero quantity, or your best-bid/best-ask scan will trip over phantom levels.

For latency, the hot path avoids allocation: pre-sized arrays or an intrusive tree keyed by integer price ticks, not floating-point prices in a general-purpose hash map. Best bid and best ask are cached and updated on each edit so top-of-book reads are O(1). The reconstruction logic is boring on purpose — the interesting engineering is making the boring path never wrong.

## What consumers need, and what to instrument

Downstream consumers want different projections of the same book. A strategy engine typically needs only top-of-book or a few levels of depth, delivered with minimal latency. A market-data service re-publishing L2 depth needs the fuller structure and cares more about consistency than microseconds. Both read from the single reconstructed book, which is why keeping that one structure correct is worth so much effort.

Instrument the reconstruction, not just the transport. The metrics that actually tell you the book is healthy:

- **Gap rate** and **gaps-per-instrument** — a rising gap rate on one channel points at a lossy network path, not a market event.
- **Recovery latency** — time from gap detected to book resynced. This is how long you were quoting on stale data.
- **Snapshot refetch count** — repeated refetches mean the buffer join keeps failing, usually a symptom of buffer overflow or a `snap_seq` mismatch.
- **Crossed-book counter** — best bid at or above best ask should be impossible on a correct book; every occurrence is a reconstruction defect, and it must alert, not just log.

The mental model to hold onto: you are not receiving a market, you are receiving a recipe for one. Sequence numbers tell you the steps are in order; snapshots give you a clean pot to start from when a step goes missing. Everything faithful about your book falls out of respecting those two invariants and refusing to proceed when either one breaks.
