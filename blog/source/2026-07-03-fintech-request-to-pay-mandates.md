# Request to Pay and Mandate Engines
*How R2P flips the pull model into a request-and-approve flow, and the engineering behind mandates, consent, and reconciliation.*

For decades, recurring payments meant one thing: you handed a biller permission to reach into your account and pull money on a schedule. Direct debit is a pull instrument. You sign a mandate once, and from then on the collecting party decides when to debit and how much. The account holder is a spectator to their own outflows, armed only with the blunt tools of a dispute or a cancellation after the fact.

Request to Pay (R2P) inverts that relationship. Instead of the payee pulling funds, the payee sends a *request* for payment, and the payer decides what happens next: approve it, decline it, or defer it to a later date. Money only moves when the payer says so, and settlement rides on instant rails so the payee sees cleared funds in seconds rather than days. This post walks through what that inversion means for the systems you have to build: the messaging layer, the mandate store, and the reconciliation loop.

## Pull versus request

The mechanical difference is who holds the decision to move money.

Under direct debit, the mandate is a standing grant of authority. The payer pre-authorizes an open-ended series of debits, and the scheme's rules — not the payer's real-time consent — govern each collection. Failures surface late: an unexpected debit bounces, an overdraft fee lands, a dispute gets filed weeks later.

Under R2P, every payment begins as a message the payer must act on. There is no standing authority to pull. The request carries context — amount, due date, reference, and the identity of who is asking — and the payer approves against that context. The result is fewer surprises, cleaner audit trails, and a payer who is never debited without an explicit yes.

```text
  DIRECT DEBIT (pull)          REQUEST TO PAY (request + approve)

  Payee ---- debit ----> Bank    Payee -- request --> Hub -- notify --> Payer
    (payer not consulted)                                    Payer -- approve --> Hub
                                                    Hub -- settle --> Payee (instant)
```

That said, R2P does not abolish standing arrangements. It reframes them as *mandates* the payer can inspect and govern.

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-request-to-pay-mandates.html)** — the R2P request, consent, and instant-settlement sequence across payee, hub, and payer.

## The mandate lifecycle

A mandate in an R2P world is a durable agreement between payee and payer that sets the rules future requests must obey. It is not a blank cheque; it is a bounded contract with a lifecycle your engine has to model explicitly.

- **Create.** The payee proposes a mandate — a subscription, a utility arrangement, a loan repayment plan. It carries the parties, a reference, and constraints: maximum amount per request, allowed frequency, an expiry, and often a total cap. The payer must accept it before it becomes active.
- **Amend.** Prices change, plans upgrade, billing dates shift. An amendment is a new proposed version of the mandate that the payer re-consents to. The old version is never mutated in place; you version it, so the state at the time of any past request stays reconstructable.
- **Cancel.** Either party can terminate. A cancelled mandate must immediately stop honoring new requests, and the cancellation event needs to propagate fast enough that an in-flight request is rejected against the right state.

Model this as a state machine, not a set of boolean flags. A mandate is `proposed`, `active`, `suspended`, `amended`, or `cancelled`, and every transition is an event you persist. The event log *is* the mandate; the current row is just a projection of it.

## Consent and variable recurring payments

The most interesting part of R2P is where it meets automation. Approving every single request by hand defeats the purpose of a subscription. This is where **variable recurring payments (VRP)** come in: the payer grants consent, once, for the hub to approve requests automatically *as long as they fall within agreed limits*.

VRP is the middle ground between the friction of manual approval and the blind trust of direct debit. The consent is a policy, not a blank authority:

- a maximum amount per single payment,
- a maximum total over a rolling window (per day, per month),
- an allowed frequency or minimum interval between payments,
- a start and end date,
- and the specific payee the consent applies to.

When a request arrives under a VRP consent, the engine evaluates it against the policy. Inside the limits, it auto-approves and settles. Outside the limits — an amount over the cap, too many payments this month, an expired consent — it falls back to explicit payer approval or a decline. The payer keeps a real ceiling on exposure while the common case stays frictionless.

The engineering subtlety is that limit checks must be *transactional* against a running tally. Two requests arriving within milliseconds of each other cannot both pass a "remaining monthly budget" check if only one fits. Treat the consent's consumed-amount counter like an inventory decrement: read, check, and reserve under a lock or an atomic conditional update, not a read-then-write race.

## The engineering: messaging, store, reconciliation

Three subsystems carry the weight.

**The messaging layer.** R2P is a conversation, so requests and responses need to be modeled as messages with correlation, not as one-shot RPC calls. Each request gets a unique id; every downstream event — notify, approve, decline, settle, confirm — references it. Messages are asynchronous and can be delivered out of order or more than once, so every handler must be idempotent: processing the same "approve" twice must not settle twice. A message that expires unanswered transitions the request to a timed-out state on its own; you never leave a request hanging on the assumption a reply will come.

**The mandate store.** This is the source of truth for consent. It holds mandates, VRP policies, their versions, and the event log behind each. It has to answer, at request time and under load, one question: *is this specific request permitted right now?* That means low-latency reads keyed by payer and payee, strong consistency on the limit counters, and an immutable audit trail so any past decision can be replayed. Because cancellation and amendment change what is permitted, staleness here is a correctness bug, not a caching nicety.

**Reconciliation.** Because the request, the approval, and the settlement are separate events on separate rails, they can drift. A request may be approved but the instant payment fails; a settlement may land with no matching request; a confirm may never arrive. Reconciliation is the loop that closes these gaps: match each settled amount back to its originating request, flag approvals with no settlement, flag settlements with no approval, and drive each request to a definitive terminal state — `settled`, `declined`, `expired`, or `failed`. Run it continuously, and treat any request stuck in an intermediate state past a threshold as an alert.

## Why this shape matters

R2P is not just a nicer UX layer over the old rails. It moves the locus of control from the collector to the account holder, and it forces the payment into an auditable, event-driven shape. Every movement of money traces back to an explicit request and an explicit consent — whether that consent was given in the moment or granted earlier as a bounded VRP policy.

For engineers, the discipline is the same discipline that makes any distributed system trustworthy: model consent as versioned state, make every message idempotent and correlated, keep the limit counters honest under concurrency, and never assume the three legs — request, approval, settlement — will agree without a reconciliation loop that checks. Build those four things well and the pull-to-request inversion stops being a compliance headache and becomes what it should be: a payment system the payer can actually see.
