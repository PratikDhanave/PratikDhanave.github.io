# Forbearance, Hardship, and Loan Restructuring
*Modeling borrower hardship as an explicit state machine, so relief, delinquency, and accounting never disagree.*

A loan is a promise expressed as a schedule: pay this amount on these dates. Hardship is what happens when the borrower can no longer keep the schedule but still intends to. The business responds with relief — a payment holiday, a deferral, a term extension, a full restructuring — and each of those responses quietly changes three things at once: the delinquency clock, the way interest accrues, and how the loan is reported for accounting. The engineering mistake is to treat relief as a flag you set on a row. It is not a flag. It is a transition in a state machine, and if the transition is not modeled explicitly, the three downstream systems drift apart until an auditor finds the gap.

This post is about that state machine: the states a loan passes through during hardship, the events that move it, and the audit trail that has to survive every move.

## The states that matter

A performing loan sits in **current**: zero days past due (DPD), interest accruing on the normal schedule. When a borrower signals distress, they enter **hardship-requested** — an attestation, sometimes with supporting documents, that they cannot meet the next payments. Nothing about the contract has changed yet; the loan is still accruing and still aging if a payment is missed. Requesting relief is not the same as receiving it.

The request lands in **under-review**, the eligibility gate. Here the servicer checks program rules: is the borrower within a hardship window, is the delinquency shallow enough, are the documents present. This is a decision state, and it has two exits. Approval moves the loan to **forbearance/modified**. Denial drops it out of the relief path entirely — the loan keeps aging under its original schedule as if nothing happened, which is exactly why a denied request must be recorded, not silently discarded.

**Forbearance/modified** is the state where the contract has actually been altered. And this is where you must be precise, because "modified" covers several mechanically different things:

- **Payment holiday / deferral** — scheduled payments are paused. The key modeling question is what happens to the paused interest: is it waived, capitalized (added to principal), or parked in a separate deferred-interest bucket to be repaid later? Each choice is a different money movement.
- **Term extension** — the maturity date moves out, spreading the same balance over more periods and lowering the installment. Amortization is recomputed from the modification date forward.
- **Re-aging** — the delinquency counter is reset to zero after the borrower makes a defined number of consecutive on-time payments. Re-aging changes *reporting status*, not the contract. It is powerful and easily abused, which is why regulators cap how often it can happen.
- **Full restructuring** — a new schedule, sometimes a new rate, occasionally partial principal forgiveness. The old obligation is effectively replaced.

From forbearance, two things can happen. The borrower resumes paying and reaches **cured** — the relief plan worked, the payment stream is flowing again. Or they breach the new terms and land in **re-defaulted**, which reopens the loss path toward **charged-off**. A modification is not a cure; it is a bet that a cure will follow.

## The lifecycle, drawn

```
 [current] ── request ─▶ [hardship-requested] ── file ─▶ [under-review] ── approve ─▶ [modified] ── resume ─▶ [cured] ──▶ [re-aged]
                                                              │                           │                    (DPD reset)
                                                        deny  │                     breach │
                                                              ▼                           ▼
                                                          [denied]                   [re-defaulted]
                                                              │                           │
                                                     keeps aging                    uncollectible
                                                              ▼                           ▼
                                                         [defaulted] ──────────────▶ [charged-off]
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-loan-forbearance-restructuring.html)** — the loan hardship and restructuring lifecycle, from a current loan through reviewed relief to cure, re-age, or terminal default.

## Delinquency, accrual, and accounting move together

The reason to model this as one machine is that a single transition fans out into three subsystems, and they must all read the same state.

**Delinquency status** is a counter driven by the payment schedule. A deferral has to *suppress* delinquency progression for the paused periods — otherwise the loan keeps aging toward default while the borrower is doing exactly what the relief plan asked. Re-aging resets that counter outright. If your delinquency engine does not know the loan is in forbearance, it will happily roll a compliant borrower into default.

**Interest accrual** forks on loan quality. A performing loan accrues on schedule. A deeply impaired one may move to **non-accrual**, where interest stops hitting income and cash receipts reduce principal instead. Forbearance sits in between and forces explicit decisions: does interest keep accruing during the holiday, and if so, is it capitalized into principal or deferred? Getting this wrong misstates both the borrower's balance and the lender's revenue.

**Accounting treatment** is the part teams underestimate. A concession granted to a borrower in financial difficulty is a **modified loan** — historically called a troubled-debt restructuring (TDR). That classification changes how impairment and expected credit loss are measured and how the loan is disclosed. It is set at the moment of modification and it is sticky: the loan carries the marker even after it cures, until defined seasoning criteria are met. So `modified` in your state machine is not just an operational status; it is the trigger that stamps an accounting flag with its own lifecycle.

The invariant to enforce: **status, accrual mode, and accounting flag are all functions of the same state transition.** They should never be updated by three independent code paths, because that is precisely how a loan ends up "current" to the collections team, "non-accrual" to finance, and "unflagged" to the auditor.

## The state machine and its audit trail

Model transitions as an append-only event log, not as mutable columns. The current status is a *projection* of that log — a fold over events — never the source of truth.

Two engineering disciplines make this reliable.

**Guarded transitions.** Every edge has a precondition and an idempotency key. `under-review → modified` requires an approval decision with an authorizing actor. `current → cured` is illegal — you cannot cure a loan that was never in relief. Encode the allowed edges as data and reject anything else at the boundary, so a malformed message can never fabricate an impossible history.

**An event that carries its own justification.** Each transition record should hold: the from-state and to-state, the triggering event (a payment, a decision, a batch delinquency roll), the actor (human user id or the system job that fired it), the effective date *and* the booking date — they differ for backdated relief — and the concrete parameters of the modification (new term, capitalized amount, deferred-interest balance). Reconstructing "why is this loan in forbearance and what exactly changed" should require reading one record, not reverse-engineering a diff.

This is also what makes reversal safe. Relief gets granted in error; a borrower disputes a modification; an approval is clawed back. With an event log you record a **compensating event** that moves the loan back and explains itself, preserving the fact that the erroneous transition happened. You never edit history — you extend it. That property is worth more than any convenience of a mutable status column, because the questions that matter in lending are almost always historical: what did we know, when did we know it, and who decided.

## Where teams go wrong

The recurring failure is optimizing for the happy path — current, modified, cured — and bolting on the rest. But the branches carry the risk and the regulatory exposure. A denied request that silently vanishes is a fair-lending question waiting to be asked. A re-default that reuses the "modified" state without distinguishing a first concession from a second understates loss. A re-aging with no cap and no audit trail is how a portfolio's delinquency numbers get quietly laundered.

Draw the whole machine — every terminal state, every guard, every compensating edge — before writing the first migration. In lending, the states you forgot to model are exactly the ones the regulator will ask about.
