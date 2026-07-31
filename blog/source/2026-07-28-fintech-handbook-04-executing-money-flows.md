# Executing Money Flows: Invariants, Reservations, and Overdrafts
*A transfer is a state machine with money on the line. Model the states explicitly, reserve funds before you commit, and decide up front what an overdraft even means.*

The first time you move money in production, you learn that "success" is a lie. A transfer is not a function that returns `true` or `false`. It is a small, stubborn machine that lives across time, survives process restarts, and occasionally gets stuck halfway between "the money left" and "the money arrived." If your code represents that machine as a single boolean column called `is_complete`, you have already lost — no boolean honestly describes a payment whose funds are held but not yet posted.

This post treats money movement as what it is: an explicit state machine, guarded by invariants you refuse to violate, funded through a two-phase reserve-then-capture pattern, and bounded by an overdraft policy you decided on purpose.

## Model the transfer as a state machine, not a flag

Every money movement occupies exactly one state at any instant, and moves between states only along edges you have explicitly allowed. Write the states down, persist the current one, and make every illegal transition impossible to express.

```
                 +-----------+
                 | INITIATED |
                 +-----+-----+
                       | reserve()
                       v
             +-------------------+       expire / release
             |  FUNDS_RESERVED   +----------------+
             +---+-----------+---+                |
      capture()  |           | reject            v
                 v           v             +-----------+
            +--------+   +--------+         | EXPIRED   |
            | POSTED |   | FAILED |         +-----------+
            +---+----+   +--------+
                | settle()
                v
           +----------+     reverse()   +-----------+
           | SETTLED  +---------------->| REVERSED  |
           +----------+                 +-----------+
```

> **▸ [Open the interactive lifecycle diagram](/blog/handbook-diagrams/transfer-state-machine.html)** — pan, zoom, and trace every transition in the state machine above.

Notice what the diagram forbids. You cannot go from `INITIATED` straight to `POSTED`; funds must be reserved first. You cannot `capture()` a transfer that already `EXPIRED`. `FAILED` and `EXPIRED` are terminal. `REVERSED` exists because `SETTLED` is terminal for the *forward* flow — you never mutate a settled transfer, you post a compensating one.

In code, this is a transition table, not a pile of `if` statements scattered across services — something like `ALLOWED = {("initiated","funds_reserved"), ...}`. Every write goes through one function that checks membership before it touches the row. An unknown transition raises, loudly, before any balance changes. The state column is the source of truth; timestamps, ledger rows, and webhook receipts hang off it.

The payoff is that "where is this payment?" stops being a forensic exercise. When something breaks at 3am, the on-call engineer sees `funds_reserved` and knows which recovery path applies, instead of staring at `is_complete = false` and guessing whether the money moved.

## The invariants you enforce at every edge

A state machine tells you *what order* things happen in. Invariants tell you *what must stay true* regardless of order. Run these checks inside the same database transaction as the state change, so a violation aborts the whole thing. Three earn their keep in almost every system:

- **Balances never go negative unless overdraft is explicitly permitted.** A guard on the debit side of every posting. Default to a hard floor of zero; loosen it only where policy says so.
- **The sum of a transfer's postings is zero.** Money is conserved. A `$50` movement is a `-50` on one account and a `+50` on another — double-entry, always balanced. If your postings sum to anything but zero, you have invented or destroyed money. A cheap `assert sum(postings) == 0` before commit has caught more bugs than any amount of unit testing.
- **Reserved funds are never double-spent.** Once an amount is held, it is unavailable to any other movement until the hold is captured or released — which only holds if "available balance" accounts for holds.

Enforce these at the lowest layer you own, ideally with database constraints backing the application checks. A `CHECK (balance >= overdraft_limit)` constraint is a seatbelt: application code should never trip it, but the day a race condition slips through, the database refuses rather than recording a negative balance you can't explain to an auditor.

## Reserve first, capture second

The single most useful pattern in money movement is borrowed from card networks: **two-phase capture**. You do not debit an account the moment someone asks to move money. You *reserve* (authorize, hold, earmark) the amount first, then *capture* (post, settle) it in a separate step — or *release* the hold if the second step never comes.

Reserving does not move money. It records a claim: "this `$50` is spoken for." The funds still sit in the account, but are subtracted from what's spendable. That claim is what makes double-spending impossible — a second concurrent transfer sees the reduced availability and cannot grab the same dollars.

```
available = current_balance - active_holds + overdraft_limit
```

That formula is the heart of it. A `$100` balance with a `$30` hold and no overdraft exposes `$70` as available. Every reservation checks `available >= amount` before it succeeds, and the check plus the hold insert happen atomically so two requests can't both pass.

Capture converts the hold into a real posting: the balance drops, the double-entry rows are written, the transfer moves to `POSTED`. Release throws the hold away and returns the amount to availability — no ledger movement, because nothing was ever posted.

This two-phase shape also makes partial failures survivable. When a downstream step fails after you've reserved but before you've captured, you have a clean, reversible position: release the hold and you're back where you started. That is exactly the discipline you need when [rolling back a half-succeeded saga](/blog/posts/saga-rollback-half-succeeded.html) — each reservation is a compensable step, and "release" is its compensation.

## Holds expire; make expiry a first-class transition

A hold you never resolve is a slow leak. It quietly reduces available balance forever, and eventually a customer with money in their account is told they have insufficient funds because of three abandoned authorizations from last Tuesday.

So every hold gets an `expires_at` at creation. A background sweep — or a lazy check the next time the account is touched — moves any expired hold into `EXPIRED` and returns the amount to availability. Treat expiry as a real edge, not a cleanup script bolted on the side: `FUNDS_RESERVED -> EXPIRED` carries the same invariant checks and audit trail as any other transition.

The subtle part is ordering against capture. A capture arriving at the exact moment a hold expires is a race, and you must pick a winner deterministically. The safe rule: capture only succeeds against a hold still in `FUNDS_RESERVED`. If expiry got there first, the capture is rejected and the caller re-reserves — never let both win.

## Overdrafts are a policy decision, not an accident

"Can this account go negative?" is a product question, but engineering has to encode the answer precisely. There are two distinct behaviors, and conflating them is how you end up either blocking legitimate transactions or handing out unlimited free credit.

A **hard stop** rejects any movement that would push the balance below zero. `overdraft_limit = 0`, availability floors at the current balance, and the reservation fails. This is the correct default for the vast majority of accounts.

An **allowed overdraft** permits the balance to go down to `-X`. The limit is a negative floor, and it flows through the same availability formula: an account at `$0` with a `$200` overdraft limit exposes `$200` of availability. The invariant doesn't disappear — it shifts. "Balance never goes negative" becomes "balance never drops below `overdraft_limit`," and the database `CHECK` enforces the new floor as rigorously as it enforced zero.

Encoding the limit *per account* rather than as a global constant keeps this sane. Most accounts carry a limit of zero and behave as hard stops; a few carry a negative limit and are allowed to dip. Same code path, one number that varies.

## Why it matters

Money movement is unforgiving because the failures are visible, expensive, and sometimes illegal. A boolean success flag hides the exact states where money is most at risk — held-but-not-posted, posted-but-not-settled — and those are precisely the states an auditor, a customer, or a regulator will ask you to explain.

An explicit state machine makes "where is my money" a single column read. Invariants enforced inside the transaction mean the system fails closed — it refuses to invent money — instead of committing a corruption you find in a reconciliation report weeks later. Reserve-then-capture makes concurrency and partial failure survivable instead of catastrophic. And a deliberate overdraft policy turns "how did this account go negative" into a configured, defensible number.

None of this is exotic. It is the boring, load-bearing machinery that lets you move real money and still sleep. Model the states, guard the edges, reserve before you commit — and decide, on purpose, what an overdraft means before your system decides it for you.
