# The Ledger: Double-Entry Bookkeeping
*Every movement of money touches at least two accounts, and the entries always sum to zero. That one invariant is the backbone of a correct financial system.*

If you have ever built a wallet, a payments processor, or a lending platform, you have probably reached for the obvious data model first: an `accounts` table with a `balance` column, and an `UPDATE` statement that adds or subtracts money. It works in a demo. It falls apart the moment two things happen at once, or a support agent asks "where did this $12 come from?" and you have no answer.

The fix is five hundred years old. Double-entry bookkeeping is not accounting trivia you can delegate to the finance team. It is a data-integrity discipline, and it maps cleanly onto everything engineers already care about: invariants, immutability, and auditability. This post is the mental model I wish every backend engineer had before touching money.

## Postings, and the invariant that never bends

A **transaction** is not a single number. It is a set of **postings**, and every posting moves value into or out of exactly one account. A debit on one account is always matched by a credit somewhere else. The rule that makes the whole system trustworthy is simple:

> The postings in a transaction MUST sum to zero.

Money is never created or destroyed inside your ledger; it only moves. A customer paying a $100 invoice does not "reduce a balance." It moves $100 out of their cash account and into your revenue account. Two postings, equal and opposite.

```
Transaction #48213 — customer pays invoice
+-------------------------+--------+--------+
| Account                 | Debit  | Credit |
+-------------------------+--------+--------+
| customer:cash           |        | 100.00 |
| platform:revenue        | 100.00 |        |
+-------------------------+--------+--------+
| SUM                     | 100.00 | 100.00 |   debit - credit = 0  ✓
+-------------------------+--------+--------+
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/double-entry-postings.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Notice there is no "balance" being written anywhere. A balance is *derived*: it is the sum of an account's postings, nothing more. That derivation is the second pillar of the whole design, and I will come back to it.

The invariant is not a nice-to-have you check in a nightly reconciliation job. It is a **hard constraint enforced at write time**. If a transaction's postings do not net to zero, the write fails — the transaction never lands. In code, the guard is almost embarrassingly small:

```python
def assert_balanced(postings: list[Posting]) -> None:
    net = sum(p.amount for p in postings)  # signed minor units
    if net != 0:
        raise UnbalancedTransaction(net=net, postings=postings)
```

Use signed integers in the smallest currency unit (cents, not dollars) so a debit is `+` and a credit is `-`, and this check is exact. Never store money as a float. The whole point of the ledger is that `+1` and `-1` cancel perfectly; binary floating point cannot promise you that.

## Account types and normal balances

Not every account behaves the same way when you debit it. Accounts fall into five types, and each has a **normal balance** — the side (debit or credit) that increases it:

- **Asset** (cash, receivables, reserves) — normal balance: debit
- **Liability** (customer wallet balances you owe, payables) — normal balance: credit
- **Equity** (retained earnings, capital) — normal balance: credit
- **Revenue** (fees, interest earned) — normal balance: credit
- **Expense** (processing costs, write-offs) — normal balance: debit

The counterintuitive one for engineers: a customer's wallet balance is a **liability** on your books. You are holding their money; you owe it back. When they deposit $50, you debit your asset (cash you now hold) and credit their liability (what you owe them) — both go *up*, on their respective normal sides, and the transaction still nets to zero. Getting the types right is what makes your balance sheet actually balance later. I have written separately about enforcing these invariants in a real P2P-lending ledger — see [double-entry ledger invariants](/blog/posts/p2p-lender-double-entry-ledger-invariants.html) — but the principle is universal.

## The ledger is append-only

Here is the rule that turns a database table into an audit trail: **postings are never updated and never deleted.**

Once a posting is written, it is history. If you got something wrong — a fat-fingered amount, a transaction against the wrong account — you do not `UPDATE` the row and you certainly do not `DELETE` it. You write a *new* transaction that reverses the effect, and if needed a second one that records the correct version. The bad entry stays visible forever, alongside the correction that cancels it. (The mechanics of reversals and adjustments deserve their own treatment, and get one later in this series.)

This is not bureaucratic caution. An append-only ledger gives you three properties for free:

1. **Reproducibility** — any balance at any past instant is recomputable by replaying postings up to that time.
2. **Auditability** — every cent has a provenance you can trace, which is exactly the question regulators and support agents both ask.
3. **Concurrency safety** — appending rows contends far less than mutating a shared `balance` cell that every transaction fights over.

Model postings as immutable facts. Your storage layer should make mutation *impossible*, not merely discouraged — no `UPDATE` grant on the table, ideally.

## Three clocks engineers keep conflating

A single `created_at` column is where naive ledgers go to die. A money movement has at least three distinct timestamps, and they are genuinely different moments:

- **Booking time** — when the transaction hit your ledger. This is your system clock, the moment the postings were appended.
- **Value time** — when the movement becomes economically effective. Interest accrues from the value date. A payment "as of" the first of the month may be booked on the third.
- **Settlement time** — when money actually moved between institutions. A card authorization books instantly but settles days later, when funds truly leave the counterparty.

```
booked            value-dated         settled
  |------------------|-------------------|-----> time
 Jul 26            Jul 25 (backdated)  Jul 29
 (append)         (interest basis)   (funds land)
```

Store all three as separate fields. The instant you flatten them into one column, you have made whole categories of correct reporting impossible: interest calculations go wrong, cut-off reconciliation breaks, and "money we've promised but don't yet hold" becomes invisible.

## Current, available, and pending balances

Because timing is layered, "the balance" is not one number either. Users and risk systems care about at least three:

- **Current (booked) balance** — the sum of all *settled* postings. What you definitively hold.
- **Available balance** — current minus holds and reservations. What can actually be spent right now.
- **Pending balance** — the effect of authorized-but-not-yet-settled movements still in flight.

A customer with $500 current and a $200 hold has $300 available. Show them the wrong one and you either let them overspend or wrongly decline them. Each of these is, again, *derived by summing postings* — filtered by state and by clock. You do not store them; you compute them, and you can afford to because the ledger is append-only and every posting is right there.

## Why it matters

Double-entry is not overhead you tolerate to keep accountants happy. It is the cheapest correctness guarantee available to anyone who moves money. The sum-to-zero invariant catches a whole class of bugs at write time, before bad state ever exists. The append-only rule gives you an audit trail that answers "what happened and when" without archaeology. Separating the three clocks and the three balances keeps you honest about the difference between money promised, money available, and money held.

Build the ledger this way from day one and the hard questions — reconciliation, disputes, regulatory reporting — become queries over facts you already have. Skip it, and you will be reconstructing the truth from logs at 2 a.m. while your balances quietly drift. Money systems do not forgive drift. Make the invariant the backbone, and everything else has something solid to hang from.
