# Engineering SEPA: Mandates, Sequence Types, and the R-Transaction State Machine

*How to engineer SEPA SCT and SDD flows: mandate lifecycle storage, pre-notification timing, FIRST/RCUR sequence types, and the R-transaction taxonomy modeled as an explicit state machine.*

---

SEPA gives you two euro rails that look symmetric on a slide and are anything but in code. SEPA Credit Transfer (SCT) is a push: the payer's bank moves money out, and once it settles there is very little to unwind. SEPA Direct Debit (SDD) is a pull: the creditor reaches into the debtor's account on the strength of a signed mandate. That inversion of who initiates the debit is the whole reason SDD carries a mandate lifecycle, pre-notification timing rules, sequence types, and a rich family of reversals collectively called R-transactions. Get the state machine wrong and you will either debit accounts you were not authorized to touch or strand money you already collected.

This post is about the engineering model behind that: what you actually store, when you are allowed to submit, and how every failure or reversal maps to a named state.

## Two schemes, one message family

Both schemes ride ISO 20022 XML. A credit transfer is initiated with `pain.001` from the payer and interbanked as `pacs.008`. A direct debit collection is initiated with `pain.008` from the creditor and interbanked as `pacs.003`. Everything that goes *wrong* comes back as a `pacs.004` return or a `camt.056` recall/request, carrying an ISO reason code such as `AC04` (closed account), `MS03` (reason not specified), or `MD06` (refund requested by end customer).

The engineering consequence: your domain model should never hold free-text status strings. Every transition is triggered by a message with a typed reason code, and your state machine should be keyed off those codes. If a status can only be set by parsing an inbound `pacs.004`, encode that in the type system so no service can hand-write it.

## Modeling the mandate as durable state

For SCT there is no mandate — authorization is implicit in the payer pushing funds. SDD is the opposite: the mandate is the legal object that everything else references, and it long outlives any single collection.

A workable mandate record carries at minimum:

- **Unique Mandate Reference (UMR)** — your stable primary key, quoted on every collection.
- **Creditor Identifier (CI)** — the scheme-issued identity of who is allowed to pull.
- **Debtor IBAN + signature date** — the account and the day authorization was given.
- **Status** — `draft`, `active`, `amended`, `cancelled`, `expired`.
- **Last-used timestamp** — SDD Core mandates lapse after 36 months of no collection, after which they must not be reused.

The 36-month dormancy rule is a real trap: a mandate can be perfectly valid legally and still be *stale* for submission purposes. Enforce it as a guard on the collection path, not as a background job you hope ran.

```text
        signed              first collection            recurring
  DRAFT ------> ACTIVE ---------------------> ACTIVE ------------> ACTIVE
                  |                              |                    |
                  | debtor revokes /            | 36 months idle     |
                  | creditor cancels            v                    |
                  +--------------------------> CANCELLED / EXPIRED <--+
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-sepa-sct-sdd-mandates.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Sequence types: FRST, RCUR, OOFF, FNAL

Every SDD collection declares a **sequence type**, and getting it wrong is a common source of rejects:

- `OOFF` — one-off. The mandate authorizes exactly one collection and is spent afterward.
- `FRST` — first of a recurring series. Historically banks pre-validated it more strictly.
- `RCUR` — every subsequent recurring collection.
- `FNAL` — the final collection; the mandate should not be used again after it settles.

Since the 2016 rulebook, `FRST` and `RCUR` are processed identically by most CSMs, so treating the first collection as just another `RCUR` is tolerated. I still recommend tracking the distinction internally: it is the cleanest signal that a mandate has moved from "signed but never used" to "proven," and that transition is exactly where your business logic (activation emails, first-payment risk checks) hangs.

Alongside the sequence type sits **pre-notification**: the creditor must tell the debtor the amount and collection date ahead of time — 14 calendar days by default, though the mandate can specify a shorter period. Model this as a timestamp on the collection, and refuse to submit a collection whose due date is inside the pre-notification window. It is a scheme obligation, not a nicety.

## The R-transaction taxonomy as a state machine

R-transactions are the reason SDD engineering is hard. They are the family of messages that undo or refuse a collection, and each one lives at a different point in the timeline. Model them as an explicit state machine and the whole scheme becomes tractable:

```text
                              settlement line
                                    |
  submitted --> pending ------------|------------> settled --> completed
                   |                |                 |
        REJECT (pre-settlement)     |        RETURN (D+2, debtor bank)
        AC04/AM04/MS03              |        AC04/MD01
                   v                |                 v
               rejected             |             returned
                                    |
                          REFUND (debtor claim)
                          MD06 -> within 8 weeks: no reason
                                  within 13 months: unauthorized
                                    |
                                    v
                                 refunded
```

The distinctions that matter to code:

- **Reject** happens *before* interbank settlement. Nothing moved, so recovery is just marking the collection dead and, if warranted, retrying.
- **Return** happens *after* settlement, initiated by the debtor bank (typically up to two business days), because the account was closed, lacked funds, or similar. Money did move and must be clawed back, so a return has to reverse ledger entries you already posted.
- **Refund** is debtor-initiated. Under SDD Core the debtor can demand a **no-questions-asked** refund for **eight weeks** after debit, and up to **thirteen months** for an *unauthorized* collection. This is the one that hurts, because it can arrive long after you have recognized the payment as final.
- **Reversal** is creditor-initiated — you collected in error and voluntarily give it back.
- **Revocation** targets the instruction before it is sent; recall (`camt.056`) targets it after.

The engineering rule that falls out: **do not treat "settled" as "final."** A settled SDD collection is provisionally final and stays refund-eligible for eight weeks minimum. Any downstream system that releases goods, pays out to a marketplace seller, or recognizes revenue must respect that window — usually by holding a reserve or gating payout until the refund horizon passes.

## Building the collection engine

A few invariants make an SDD engine safe to operate:

1. **Idempotent submission keyed by `(UMR, due_date, amount)`** or an end-to-end ID. Retries on timeouts must never produce a second real debit.
2. **A due-date scheduler, not an immediate sender.** Collections are warehoused until their submission cutoff (Core collections are submitted one business day before due date under the 2016 timings). The scheduler is where pre-notification and mandate-dormancy guards run.
3. **Reason-code-driven transitions.** Inbound `pacs.004`/`camt.056` parse into a typed reason code that drives exactly one legal transition. Unknown codes route to a manual queue rather than silently completing.
4. **Ledger reversibility.** Every posting from a settled collection needs a matching reversal path for returns and refunds, ideally as compensating double-entry rather than in-place mutation, so the audit trail shows both the debit and its unwind.

```python
def apply_r_transaction(collection, reason_code):
    if collection.state == "pending":
        collection.state = "rejected"          # pre-settlement, no ledger unwind
    elif collection.state == "settled":
        if reason_code == "MD06":
            collection.state = "refunded"       # debtor claim, reverse ledger
        else:
            collection.state = "returned"       # bank return, reverse ledger
    else:
        raise IllegalTransition(collection.state, reason_code)
    return collection
```

Kept this disciplined, SEPA stops being a pile of acronyms. SCT is a near-irreversible push; SDD is a mandate-gated pull whose every reversal is a named state with a deadline attached. Encode the mandate lifecycle, the sequence types, and the R-transaction timeline as first-class state, and the rulebook edge cases become guard clauses instead of production incidents.
