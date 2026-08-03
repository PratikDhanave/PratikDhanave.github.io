# Crediting Crypto Deposits Without Getting Burned by Reorgs

*How to safely credit on-chain deposits and finalize settlement: confirmation-depth thresholds, mempool tracking, chain-reorg detection with balance rollback, and idempotent handling of replaced transactions.*

A crypto deposit is not a database insert. When a customer sends funds to a deposit address, nothing about that transaction is final at the moment you first see it. It sits in a mempool, gets mined into a block, and only becomes economically irreversible after enough subsequent blocks pile on top of it. Between "seen" and "safe" there is a window where the chain can reorganize, orphan the block your deposit landed in, and quietly un-happen the payment. If your ledger credited the customer during that window and they already withdrew, you have handed out money that no longer exists on-chain.

This post is about the state machine that sits between a raw chain event and a ledger credit, and how to make it survive reorgs without double-crediting or stranding funds.

## Why "confirmed" is a threshold, not a boolean

Every deposit you track moves through a small set of states driven by one input: the current confirmation depth, defined as `tip_height - block_height + 1` where `block_height` is the height of the block that contains the transaction. A transaction in the mempool has depth 0. Once mined it has depth 1, and each new block increments it.

The confirmation threshold `N` is a risk parameter, not a protocol constant. It is chosen per asset from the cost of rewriting `N` blocks versus the value being credited. High-throughput probabilistic chains need more confirmations for the same assurance than a chain with fast deterministic finality. A sane implementation makes `N` a function of both the asset and the deposit amount, so a large deposit waits longer than a small one.

```
depth:   0            1..N-1              >= N
        ┌──────┐     ┌──────────┐        ┌──────────┐
 mempool│ SEEN │ ──▶ │CONFIRMING│ ─────▶ │ CREDITED │
        └──────┘     └──────────┘        └──────────┘
          pending      counting            ledger
          no credit    up to N             posted
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-onchain-settlement-reorg.html)** — pan, zoom, and trace every step (light/dark, self-contained).


The critical rule: **no ledger credit before depth `N`**. Showing a "pending" balance in the UI is fine, but the double-entry journal that lets the customer spend or withdraw must not post until the threshold is met. Everything before that is display state, not money.

## Tracking the mempool without trusting it

You want to know about a deposit the instant it hits the mempool, both for user experience and for fraud signals, but a mempool transaction is a rumor. It can be evicted, replaced by a higher-fee version, or never mined at all. So the ingestion layer treats mempool sightings as advisory: it creates a deposit record keyed by transaction id and marks it `SEEN`, but attaches no ledger consequence.

Two properties matter here. First, **idempotency by transaction id plus output index**: the same deposit will be reported many times — once from the mempool, once when mined, and again on every block scan. Each observation is an upsert against `(txid, vout)`, never an insert, so replays and overlapping scans converge to the same row. Second, **replacement awareness**: fee-bump mechanisms mean the txid you saw in the mempool may never confirm because a replacement did. Your matcher keys deposits on the destination address and amount as well as txid, so a replacement that pays the same address is reconciled to the same logical deposit rather than counted twice.

## Detecting a reorg and rolling the credit back

A reorg happens when the node switches to a heavier competing chain and blocks you previously considered part of history get orphaned. The transactions inside them fall back to the mempool — or vanish, if a conflicting transaction took their place.

Detection does not require listening for a special event. You detect a reorg by **remembering the block hash at each height you have processed** and noticing when the node reports a different hash for a height you already recorded. Concretely, the deposit worker stores, per confirmed deposit, the `block_hash` it was mined into. On every poll it asks the node for the current block at that height. If the hash still matches, the confirmation count simply advances. If the hash differs, the block was orphaned and every deposit anchored to it must be re-examined.

```
             confirmed at height H, hash 0xAAA
                        │
        poll: block at H is now hash 0xBBB  ◀── mismatch
                        │
                        ▼
        ┌──────────────────────────────────┐
        │  UNCONFIRM: reverse ledger credit  │
        │  reset depth, freeze withdrawals   │
        └──────────────────────────────────┘
                        │
                        ▼
        re-evaluate the transaction on the new chain
```

When a credited deposit is orphaned, you post a **compensating journal entry** that reverses the original credit — you never delete or mutate the original posting. The customer's available balance drops back, and if they had already withdrawn against it you now hold a negative available balance that collections logic must chase. This is exactly why `N` exists and why it scales with amount: the whole point is to make the orphan-after-credit case vanishingly rare, because its cleanup is genuinely painful.

## Re-evaluating the replaced transaction

Rolling back is only half the job. After an unconfirm you have to decide what the transaction *is* now on the winning chain, and there are three outcomes:

- **Re-mined on the new chain.** The same transaction was included in a block on the heavier chain, just at a different height. You reset its depth from the new block and let it climb back toward `N`. No money is lost; the credit will re-post once the threshold is met again.
- **Back in the mempool.** The transaction is valid but unmined. It returns to `CONFIRMING` at depth 0 and waits.
- **Replaced or double-spent.** A conflicting transaction spent the same inputs and won. The original is now permanently invalid. The deposit is marked terminal — dropped — and stays reversed.

The engine that distinguishes these cases must be **idempotent and re-entrant**, because reorgs can nest: a reorg can occur while you are still processing a previous one. The safe design keeps the deposit's state as a pure function of what the chain currently says — current containing block, current depth, current chain tip — rather than an accumulation of events. On every poll you recompute the target state from the chain and move the deposit toward it. If you crash mid-rollback and restart, recomputing from the same chain state yields the same decision, so partial work is never double-applied.

## Making the whole thing replay-safe

Two disciplines keep this correct under the retries, restarts, and out-of-order events that are normal in chain ingestion.

**Derive, don't accumulate.** The deposit's status is computed from `(containing_block_hash, depth, chain_tip)` on each pass. Counters you increment by hand drift under retries; a value you recompute from the chain cannot.

**Guard every ledger effect with a natural key.** Each posting carries a deterministic idempotency key — credit uses `credit:{txid}:{vout}`, the reversal uses `reversal:{txid}:{vout}:{orphaned_block_hash}`. The ledger rejects a second write with the same key. So a credit that gets retried posts once, and a reversal for a specific orphan event applies once, even if the reorg is detected by three workers simultaneously.

```
state = f(containing_block, depth, tip)     ← recomputed each poll
ledger_effect(key) → applied_once            ← natural-key dedupe
```

The result is a settlement layer where "confirmed" is an explicit depth threshold, a credit is a reversible ledger fact rather than a deletion, and every reorg — even a nested one — resolves to a deterministic re-evaluation of the transaction on the chain that actually won. That is the difference between a wallet that occasionally gives away money and one that does not.
