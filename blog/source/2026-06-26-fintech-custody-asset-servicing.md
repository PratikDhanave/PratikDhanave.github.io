# Custody and Asset Servicing Platforms

*How a custodian actually safekeeps client assets — account structures, the custody network, settlement instructions, and the books-and-records engine that keeps it all honest.*

Most securities you own do not sit in a vault with your name on them. They sit as electronic entries in a chain of ledgers, and a custodian's job is to make sure the entry that says *you own 1,000 shares* stays true, settles when you trade, and pays you when the issuer pays. Custody looks boring from the outside and is unforgiving on the inside: the whole business is a promise that a number in your books equals a number in someone else's books, forever, across time zones and corporate actions. This post walks the engineering surface of a custody and asset-servicing platform.

## What custody actually is (and isn't)

A custodian holds financial assets *on behalf of* clients and keeps the records that prove ownership. It is not a broker (it doesn't decide what to buy), not an exchange (it doesn't match trades), and not the issuer. It is the safekeeper and the record-keeper. The core product is trust expressed as data integrity: the custodian's ledger must reconcile, continuously, against the place the asset legally lives.

Two records exist for every position and they must agree. The custodian's internal ledger — the **books and records** — is its own claim about what each client owns. The **depository record** at the Central Securities Depository (CSD) or a sub-custodian is the authoritative external claim. Custody is the discipline of keeping those two in lock-step.

## Account structures and asset segregation

How accounts are structured determines what happens to client assets if the custodian fails — so this is a legal-and-engineering concern, not a preference.

- **Segregated accounts** hold one client's assets in an account identifiable as theirs all the way down to the depository. Maximum protection, higher cost, more accounts to maintain.
- **Omnibus accounts** pool many clients' assets into one account at the sub-custodian or CSD. The custodian's *own* books then track each client's slice. Cheaper and operationally simpler, but the external record only shows the pool — the per-client breakdown lives entirely in the custodian's ledger, which raises the stakes on reconciliation.

Layered on top is the distinction between **legal ownership** and **beneficial ownership**. The custodian (or its nominee) is often the *legal* holder of record at the depository, while the client is the *beneficial* owner who actually enjoys the economic rights. Your platform must always be able to answer "who beneficially owns this position?" even when the external world only sees a nominee name on a pooled account. Getting this mapping wrong is how client assets get commingled with the firm's own — the failure mode regulators care about most.

## The custody network: CSDs, ICSDs, and sub-custodians

No custodian connects directly to every market on earth. Assets are held through a network:

- The **global custodian** is the client's single point of contact. It holds nothing directly in most markets; it holds *relationships*.
- **Sub-custodians** are local agents in each market, appointed by the global custodian, that hold assets in that jurisdiction and connect to the local depository.
- The **CSD** is the national depository where a security ultimately settles and is recorded (one per market, typically). **ICSDs** are international depositories used for cross-border and eurobond settlement.

So a single position can be recorded as: client → global custodian's books → sub-custodian's account → CSD's register. Every hop is a ledger, and every ledger is a place your golden copy must reconcile against.

```
                        RECONCILIATION LOOP (positions + cash, daily/intraday)
         +-----------------------------------------------------------------------+
         |                                                                       v
   +-----------+        +-----------------------------------------+        +-----------------+
   |  CLIENT   |        |          GLOBAL CUSTODIAN               |        |  MARKET INFRA   |
   | asset     | -----> |  +-----------+  +------------------+    | -----> |  +-----------+  |
   | owner /   |  instr |  | Books &   |  | Instruction Mgr  |    |  SWIFT |  | Sub-      |  |
   | investment|        |  | Records   |  | (matching, DvP)  |----+------->|  | custodian |  |
   | manager   | <----- |  | GOLDEN    |  +------------------+    |        |  +-----+-----+  |
   +-----------+ reports |  | COPY      |  +------------------+    |        |        |        |
                        |  +-----------+  | Asset Servicing  |    | <----- |  +-----v-----+  |
                        |       ^         | (income, CA,     |    | status |  | CSD / ICSD|  |
                        |       |         |  proxy, tax)     |    |        |  | (registry,|  |
                        |       +---------+------------------+    |        |  |  DvP)     |  |
                        +-----------------------------------------+        |  +-----------+  |
                                                                          +-----------------+
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-custody-asset-servicing.html)** — the custody platform end to end: client instructions flowing to the depository via DvP, asset-servicing events, and the reconciliation loop that keeps the golden copy honest.

## Settlement instruction processing and DvP

When a client trades, the custodian must move the security and the cash. The instruction lifecycle is where most operational risk lives.

1. **Instruction capture** — the custodian receives a settlement instruction (classically over SWIFT ISO 15022/20022) describing the security, quantity, counterparty, cash amount, and value date.
2. **Enrichment and validation** — standing settlement instructions (SSIs), account mapping, and static data are applied; malformed or unfunded instructions are stopped before they reach the market.
3. **Matching at the depository** — the buyer's and seller's instructions must *match* at the CSD on the agreed economic terms. Unmatched instructions don't settle; they sit and age, and aging instructions are a leading indicator of a fail.
4. **Delivery versus Payment (DvP)** — the settlement mechanism that makes delivery of the security conditional on simultaneous payment of cash. DvP removes principal risk: neither leg happens unless both happen. This is the single most important safety property in settlement, and your platform models it as an atomic state transition, never as two independent updates.

A settlement fail — the trade doesn't settle on value date — triggers claims, buy-ins, and increasingly cash penalties. Tracking instruction state (matched, settled, failing, cancelled) is a first-class engineering concern.

## Asset servicing

Holding the asset is half the job; servicing what the asset *does* is the other half. Asset servicing is the set of downstream events an owned security generates:

- **Income collection** — dividends and coupon/interest payments, collected from the issuer through the chain and credited to the right beneficial owners, net of the right taxes.
- **Corporate actions** — mergers, splits, rights issues, tender offers. These come in *mandatory* (happens regardless) and *voluntary* (the owner must elect by a deadline) flavors. Voluntary actions with election deadlines are the sharpest timing risk in the whole platform.
- **Proxy voting** — passing voting rights and materials to beneficial owners and relaying their votes back to the issuer.
- **Tax reclaim** — recovering over-withheld withholding tax under treaty rates, often a long-tail, multi-jurisdiction workflow.

Each of these must fan an event that arrives at the omnibus/nominee level *back down* to individual beneficial owners in the correct proportion. That fan-out is only as correct as your ownership records on the record date.

## The books-and-records core and reconciliation

The heart of the platform is the **golden copy** of positions and cash: the authoritative internal ledger of who owns what, where it's held, and its lifecycle state. Everything else — reporting, servicing, settlement — reads from it.

The golden copy is only trustworthy if it is **reconciled**. Reconciliation compares the custodian's books against each external ledger (sub-custodian statements, CSD records, cash nostro accounts) and surfaces every mismatch as a **break**. A break is a difference in position quantity or cash balance that must be investigated and cleared. Healthy platforms reconcile positions and cash at least daily, often intraday, and track break age relentlessly — an unexplained break is a potential loss, a fraud signal, or a servicing error waiting to happen.

## Pitfalls

- **Asset segregation failures.** Mislabeling a beneficial owner or letting client assets touch a firm account is the cardinal sin. Model the legal-vs-beneficial mapping explicitly and make commingling structurally impossible, not merely discouraged.
- **Reconciliation breaks that age.** A break isn't a nuisance ticket; it means your golden copy might be wrong. Instrument break age and root-cause categories, and never auto-clear silently.
- **Corporate-action timing.** Missing a voluntary election deadline or applying an action to the wrong record-date holders creates real, unrecoverable client loss. Treat record dates and deadlines as hard, monitored constraints.
- **Omnibus opacity.** When the external record only shows a pool, the internal breakdown is the *only* proof of client ownership. Its integrity is non-negotiable.

## What to remember

Custody is a data-integrity business wearing a finance costume. The golden copy of positions is the product; reconciliation against every external ledger is what makes it true; DvP is what makes settlement safe; and asset servicing is the promise that owning a security keeps paying off. Build the ownership model — legal versus beneficial, segregated versus omnibus — correctly first, because every dividend, vote, and reclaim downstream inherits its correctness.
