# Subledger to General Ledger: Posting and Aggregation

*Why fintechs keep a transaction-grain subledger separate from the accounting general ledger, and how the posting, aggregation, and tie-out actually work.*

---

## Two ledgers, two jobs

The first thing that confuses engineers new to financial systems is discovering there are two ledgers, not one. There is the **general ledger** (GL) — the small, slow, authoritative book the accounting and finance teams close every month — and there is the **subledger**, a high-volume operational store that records every economic event at transaction grain. They are separate on purpose, and conflating them is the most expensive design mistake a fintech can make.

The GL is deliberately coarse. It holds a few thousand accounts and, for any given period, a modest number of journal entries per account. Its job is to answer "what is the balance of *Card Settlement Receivable* on the last day of the month?" — and to answer it identically every time an auditor asks. It optimizes for correctness, immutability, and a clean trial balance, not for volume.

The subledger is the opposite. It is where a payout of a few cents, a foreign-exchange fee, a chargeback, and an interest accrual each land as their own row, tagged with the customer, the instrument, and the originating event ID. A payments platform can write tens of millions of subledger lines a day. If you tried to post each of those directly into the GL, you would destroy the very thing the GL is good at: nobody can reconcile a general ledger with fifty million entries in a single account.

So the architecture is a pipeline: business events become balanced subledger lines through **posting rules**, and many subledger lines collapse into a handful of GL journal entries through **aggregation**. A reconciliation control sits across both to guarantee they never drift.

## Posting rules: events become debits and credits

A posting rule is the translation layer between the language of the product and the language of accounting. The product emits events — `payout.completed`, `fee.charged`, `refund.issued`. Accounting only understands debits and credits against accounts. The posting rule maps one to the other.

Concretely, a rule for a card payout might say: debit *Merchant Payable*, credit *Settlement Cash*, for the payout amount, in the payout currency. Every rule must produce a **balanced** entry — debits equal credits — or it is rejected before it ever touches storage. This double-entry invariant is what makes the whole system auditable later; a single unbalanced line poisons every downstream total.

The rules themselves are configuration, not code buried in a service. Treating them as versioned data means an accountant can review a mapping, you can replay history against a corrected rule, and you can prove which rule version produced a given line. The posting engine reads the event, selects the rule by event type and effective date, and emits the lines.

```
 Business Events        Posting Rules
 (orders, fees) ─┐      (event → Dr/Cr)
                 │           │
                 ▼           ▼
            ┌──────────────────────┐
            │    Posting Engine     │  idempotent, balanced
            └───────────┬──────────┘
                        │ journal lines (txn grain)
                        ▼
                 ┌─────────────┐
                 │  Subledger   │ append-only, millions of rows
                 └──────┬───────┘
             period slice │        │ detail totals
                        ▼          └──────────┐
              ┌──────────────────┐            ▼
              │ Aggregation Job   │      ┌───────────────┐
              └────────┬─────────┘      │ Reconciliation │
                       │ summary entries │  subledger↔GL  │
                       ▼                 └───────▲────────┘
              ┌─────────────────┐  GL balances   │
              │ General Ledger   │────────────────┘
              │ (period entries) │
              └─────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-subledger-gl-posting.html)** — trace posting, aggregation, and the subledger-to-GL tie-out (pan, zoom, light/dark, self-contained).

## Idempotent posting is non-negotiable

The posting engine runs in a world of retries. The event bus delivers at least once, the service crashes mid-batch, an upstream producer replays a partition after a deploy. If posting is not idempotent, every one of those situations double-counts money — and in accounting, a duplicated entry is not a rounding error, it is a material misstatement.

The discipline is to derive a deterministic **idempotency key** for each posting from the source event, typically the event ID plus the rule version, and to make the subledger write conditional on that key not already existing. A unique constraint on the key column turns a duplicate delivery into a no-op instead of a second entry. The posting is then safe to retry indefinitely: the first write wins, every replay is absorbed silently.

Two subtleties matter. First, the key must survive rule changes — if you reprocess an event under a new rule version, that is a *different* posting and needs its own key, or you will suppress a correction. Second, an event that no rule maps to must not vanish. It goes to a suspense account so the money is visible and someone is forced to define the missing rule, rather than silently dropping value.

## Aggregation: many lines, few journal entries

The aggregation job is what protects the GL from the subledger's volume. On a schedule — hourly, daily, or at period close — it reads the subledger lines for a window and groups them by the dimensions the GL cares about: account, currency, and sometimes a cost center or entity. It sums debits and credits within each group and emits one GL journal entry per group.

Fifty million subledger lines might collapse into a few hundred GL entries. That is the whole point. The GL stays at *reporting grain*; the subledger keeps *transaction grain*; and the aggregation is the lossy-but-reversible bridge between them. It is lossy in that the GL entry no longer names individual transactions, but reversible because every GL entry carries a reference back to the exact subledger window and grouping key that produced it. When finance asks "what makes up this $2.1M in fees?", you drill from the one GL line back to the millions of subledger rows behind it.

The job itself must be idempotent too, and re-runnable for a closed window without producing a second set of entries. The usual approach is to make each aggregation run produce a labeled batch keyed by window and grouping version; re-running the same window replaces rather than appends.

## Tie-out: proving the two ledgers agree

None of this is trustworthy without a reconciliation control that continuously proves the subledger and the GL tell the same story. The tie-out is arithmetic: for each account and period, the sum of subledger detail must equal the balance posted to the GL. If they match, the aggregation was faithful. If they diverge — a dropped batch, a late-arriving line, a partial run — the difference is quantified before anyone closes the books.

This control is strictly read-only. It never writes to either ledger; it observes both and raises a variance. A healthy fintech treats a non-zero, unexplained variance as a hard gate: the period cannot close until it is either driven to zero or documented with a known cause. Late events that arrive after a window is aggregated are handled explicitly — usually posted into the next open period rather than reopening a closed one, with the reconciliation noting the timing difference.

## The period-close handoff

Period close is where the pipeline hands control to the accounting team. The sequence is deliberate: stop or quiesce posting for the period, run the final aggregation so no subledger line is stranded, execute the tie-out until the variance is zero, then freeze the GL period so no further entries land in it. Only after the freeze do the financial statements get produced.

The engineering payoff of keeping the ledgers separate now shows: the operational subledger never stopped accepting new events for the *next* period while the *current* period was closing. The two-ledger split is not accounting pedantry — it is what lets a high-throughput system keep writing money movements continuously while the books close cleanly behind it.
