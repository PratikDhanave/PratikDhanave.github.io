# Nonce and Gas: The Sending Side Nobody Budgets For

*Solving the sending-side reliability problem — nonce sequencing, fee estimation, and replacing a transaction that gets stuck in the mempool.*

Most teams building on a blockchain spend their design energy on the read side: indexing blocks, reconciling balances, reorg handling. Then they ship a service that *sends* transactions and discover the sending side is its own distributed-systems problem. A transaction is not an HTTP call. You do not get a synchronous 200. You hand a signed blob to a peer-to-peer network, it may or may not be included in a block minutes later, and in the meantime your account is effectively a serial channel that one bad transaction can jam completely.

The two mechanics that govern that channel are the **nonce** (the per-account sequence number that enforces ordering) and **gas** (the fee that buys inclusion). Get either wrong under load and you do not get a clean error — you get a queue of transactions that silently stop confirming. Model the whole thing as a lifecycle and the failure modes become states you can name and handle.

```
Queued ──▶ Nonce Assigned ──▶ Gas Priced ──▶ Pending ──▶ Mined
                                                │  ▲
                                        stuck   ▼  │ resend
                                              Stuck ─▶ Replace
                                                │
                                                ▼ evicted
                                             Dropped
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-nonce-gas-management.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## The account is a serial channel

Every transaction from a given sending address carries a nonce, and the network will only include them in strict ascending order with no gaps. Nonce 42 cannot be mined until 41 is mined. This single rule is the source of most sending-side outages I have seen. If nonce 41 is underpriced and sits unconfirmed, then 42, 43, and everything behind it are stuck too — not because *they* are underpriced, but because they are queued behind a transaction that will not move. One slow transaction becomes a head-of-line block for the entire account.

The immediate engineering consequence is that you cannot let concurrent workers each fetch "the next nonce" from a node and race. Two workers both read nonce 42, both sign a 42, and now you have a collision: one confirms, the other is rejected as a duplicate nonce, and any code that assumed both landed is wrong. Nonce allocation has to be serialized per sending address through a single source of truth — a row lock, a per-address queue, an allocator service — so that each nonce is handed out exactly once.

## Nonce: assign it yourself, do not ask the chain

The naive approach is to ask the node for the account's transaction count and use that as the next nonce. That count reflects only *mined* transactions, so under any concurrency it lags reality: you have three transactions pending in the mempool, the node still reports the old count, and you reissue a nonce that is already in flight.

The reliable pattern is a local allocator that tracks the highest nonce you have *dispatched*, not the highest the chain has *confirmed*. You persist a monotonic counter per address, hand out `next = last_dispatched + 1` under a lock, and only reconcile against the chain's confirmed count to detect and repair gaps — for example after a restart, or when a transaction was dropped and its nonce needs to be reused.

```go
// One allocator per sending address; callers serialize on it.
func (a *Allocator) Next(ctx context.Context) (uint64, error) {
    a.mu.Lock()
    defer a.mu.Unlock()
    if !a.synced {
        onchain, err := a.node.PendingNonceAt(ctx, a.addr)
        if err != nil {
            return 0, err
        }
        if onchain > a.next { // chain moved ahead of us
            a.next = onchain
        }
        a.synced = true
    }
    n := a.next
    a.next++
    return n, nil
}
```

The subtle rule: a nonce you assign but never successfully broadcast, or one whose transaction gets dropped, leaves a *hole*. Until you fill that exact nonce, nothing behind it confirms. So "release the nonce back to the pool on failure" is not an optimization — it is required for liveness.

## Gas: pricing for inclusion, not correctness

Gas has two independent jobs, and conflating them causes bugs. The **gas limit** is a ceiling on computation — how much work the transaction may do. The **gas price** (on modern fee markets, a base fee plus a priority tip) is what you bid to be included. Underestimating the limit makes the transaction revert as out-of-gas; underbidding the price makes it sit unmined.

The base fee moves with network congestion block to block, so a price that was generous when you estimated it can be stale by the time you broadcast. Practical estimation means reading the recent fee history, choosing a base-fee ceiling with headroom for a few blocks of increase, and adding a priority tip sized to how urgently you need inclusion. The tradeoff is direct: bid low and save fees but risk getting stuck; bid high and pay for speed you may not need. Batch, non-urgent transactions can bid patiently; a user-facing withdrawal cannot.

Crucially, gas pricing is a *retry-time* decision, not a *build-time* one. The price you signed with is only a promise; if the market moves past it, your only lever is to replace the transaction — which brings us to the stuck path.

## Pending, stuck, and replacement

Once broadcast, a transaction enters the mempool and becomes **Pending**. Pending is not a terminal state and it is not an error — it is a wait. The bug is treating "still pending after N seconds" as failure and blindly re-sending, because a re-send at a *new* nonce does not cancel the old one; it just adds another stuck transaction behind the first.

The correct recovery is **replacement**: broadcast a new transaction with the **same nonce** and a higher fee. The network keeps whichever version of that nonce it eventually mines and discards the other, so replacement is safe by construction — you can never accidentally send twice, because both compete for one slot. Most networks require the replacement to raise the fee by a minimum percentage over the original, so a "bump" that only nudges the price by a rounding error is silently rejected; your escalation policy has to clear that threshold on every attempt.

A transaction that stays underpriced long enough can also be **Dropped** — evicted from the mempool entirely. This is the genuinely dangerous terminal state, because the nonce it held is now a hole that blocks everything behind it. Detecting a drop and re-issuing a transaction at that exact nonce is what keeps the account's serial channel flowing.

## Invariants worth asserting

A dependable sender comes down to a handful of properties you can encode and test:

- **One nonce, one dispatch.** A nonce is handed out exactly once; concurrent allocation is serialized per address. Assert it in the allocator, not in review.
- **Holes are liveness bugs.** Any assigned-but-unconfirmed nonce blocks its successors. Dropped or failed transactions must have their nonce reused, not abandoned.
- **Replace, never duplicate.** Recovery re-broadcasts the *same* nonce at a higher fee and clears the minimum-bump threshold. Never "retry" onto a fresh nonce.
- **Pending is not failure.** A timeout triggers replacement, not a second transaction. Only eviction is terminal.

Model the sender as this lifecycle first — allocate, price, broadcast, and treat stuck as a first-class state with a replacement loop — and the reliability problems stop being mysterious mempool folklore. They become transitions you can observe, alert on, and prove correct.
