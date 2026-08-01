# Audit Trails, Event Sourcing, and the GDPR Problem
*In finance you never update and never delete — you only append. Event sourcing gives you a perfect audit trail; the right to be forgotten is where it fights back.*

Every fintech engineer eventually gets the same support ticket: "The customer says their balance is wrong, and they want to know why." In most software you shrug, look at a `balances` row that says `142.30`, and have absolutely nothing to tell them. The number is correct as of right now, and the story of how it got there is gone — overwritten by the last `UPDATE`. In finance that answer is not merely unsatisfying; it is a compliance failure. The audit trail is not a log you bolt on later. It is a product requirement, and it belongs in your data model from line one.

## The audit trail is the product

Regulators, auditors, and disputes all ask the same question in different accents: who did what, when, and what did it change. A chargeback investigation, a suspicious-activity report, a reconciliation break, an angry customer — every one of them is a query against history. If your system can only answer "here is the current state," you are structurally unable to serve the people who pay for financial software to be trustworthy.

The trap is treating this as a logging concern. Teams sprinkle `logger.info("balance updated")` calls through the code and call it an audit trail. It isn't. Those logs are lossy, unstructured, best-effort, and disconnected from the transaction that actually changed the money. When the log and the database disagree — and they will — you have two unreliable narrators and no source of truth. The trail has to *be* the data, not a shadow of it. That is exactly the argument in [audit logs are the API of record](/blog/posts/audit-logs-are-the-api-of-record.html): if the history is authoritative, everything downstream can be derived from it and trusted.

## State is a fold over events

Event sourcing takes that idea to its logical conclusion. Instead of storing current state and mutating it, you store the sequence of **immutable events** that happened, and you treat current state as a *derived* value — the result of folding a reducer over the log from the beginning of time.

Concretely, you never write `UPDATE accounts SET balance = 142.30`. You append an event like `DepositReceived{account: A, amount: 50.00}` or `TransferSettled{from: A, to: B, amount: 20.00}`. The event log is append-only and the single source of truth. The balance is a projection: fold `+` and `-` over the events for that account and you get the current number. Any read model — balances, monthly statements, a fraud feature store — is just a different fold over the same immutable stream.

```
          APPEND-ONLY EVENT LOG (source of truth, immutable)
  ┌──────────────────────────────────────────────────────────────┐
  │ #1 AccountOpened   A                                          │
  │ #2 DepositRecvd    A  +100.00                                 │
  │ #3 TransferOut     A  -20.00  -> B                            │
  │ #4 TransferIn      B  +20.00                                  │
  │ #5 FeeCharged      A   -1.50                                  │
  │ #6 TransferOut     A  -30.00  (MISTAKE)                       │
  │ #7 TransferRevrsd  A  +30.00  (corrects #6, never edits it)   │
  └───────────────┬──────────────────────────────────────────────┘
                  │  fold / reduce  (replay left → right)
                  ▼
        reducer(state, event) -> state'
                  │
        ┌─────────┴──────────────────────────────┐
        ▼                                         ▼
  PROJECTION: balances                   PROJECTION: statement
  ┌───────────────────┐                 ┌────────────────────────┐
  │ A = 48.50         │                 │ A: opened, +100, -20,  │
  │ B = 20.00         │                 │    -1.50 fee, reversal │
  └───────────────────┘                 └────────────────────────┘
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/event-sourcing-fold.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The property that makes this powerful: projections are disposable. Corrupt your `balances` table, ship a bug in the fold, or invent a brand-new read model two years later — you `DELETE` the projection and replay the log to rebuild it exactly. The events are the asset; the tables are a cache.

## You correct with new events, never edits

Here is the discipline that separates a real ledger from a database with extra steps. When something is wrong, you do **not** go back and fix the offending event. Event `#6` above was a mistaken transfer. The naive instinct is to delete row `#6` or patch its amount. Do that and you have destroyed the one thing the whole system exists to preserve: the truth of what happened.

Instead you append a **reversing entry** — event `#7`, `TransferReversed`, which references `#6` and posts the compensating amount. The mistake stays in history forever, and so does the correction. The net effect on the balance is zero, but the story is complete: the money moved, someone caught it, and it moved back. This is exactly how double-entry bookkeeping has worked for centuries, and it is not an accident that the accountants got there first. An auditor can see the error *and* the remediation. A customer disputing the transfer can be shown precisely what occurred.

Immutability is what makes the trail trustworthy. If any event could be silently rewritten, the log would be worth no more than a mutable `balances` row. Append-only is not a performance choice; it is an integrity guarantee. Many teams reinforce it by chaining a hash of each event into the next, so tampering breaks the chain and is detectable.

## The GDPR problem

Now the tension. You have built a log that must **never change**. Then a user in scope of GDPR (or CCPA, or any modern privacy regime) exercises their **right to erasure** and asks you to delete their personal data. Your immutability guarantee and the law are now pointing in opposite directions. You cannot rewrite the event — that breaks the ledger, the hash chain, and every projection derived from it. You also cannot ignore the request.

The mistake is assuming personal data and financial facts are the same data. They are not, and untangling them is the whole solution. An event like `TransferSettled` needs an amount, a currency, an account identifier, and a timestamp to be financially meaningful. It does **not** need the customer's name, email, home address, or national ID number embedded in it. Those are personally identifiable information (PII), and they have no business living inside an immutable financial event.

So the first move is architectural: **separate PII from financial events.** Keep the money-facts in the append-only log, keyed by an opaque subject identifier. Keep the human-facts — name, contact details, KYC documents — in a separate, *mutable* profile store that you are perfectly free to delete from. Erasing the profile satisfies the request without touching the ledger, and the financial history remains intact and referentially valid via the opaque key.

## Crypto-shredding: erasure without deletion

Sometimes PII genuinely has to ride along inside the event stream — a payment memo, a counterparty name required for the transaction, data you cannot fully normalize out. For that, the technique is **crypto-shredding**.

The idea is simple and surgical. Encrypt each subject's personal fields with a **per-subject key** — one key per customer — and store only the ciphertext in the immutable log. The key lives in a separate, deletable key store. Under normal operation you decrypt on read and everything works. When an erasure request arrives, you **destroy that subject's key.** The ciphertext remains in the log — the log never changed, the hash chain holds, the byte count is identical — but it is now permanently unrecoverable noise. The person is, cryptographically, forgotten.

```
  Immutable event log            Deletable key vault
  ┌─────────────────────┐        ┌──────────────────┐
  │ evt: {amount:20.00, │        │ subjectKey[A] ✔  │
  │   memo: <cipher>,   │◀──────▶│ subjectKey[B] ✔  │
  │   subject: A}       │  read  │                  │
  └─────────────────────┘        └──────────────────┘
        erasure request for A ──▶ destroy subjectKey[A]
  ┌─────────────────────┐        ┌──────────────────┐
  │ evt: {amount:20.00, │        │ subjectKey[A] ✗  │  (gone)
  │   memo: <cipher>,   │──✗ can't decrypt          │
  │   subject: A}       │        │ subjectKey[B] ✔  │
  └─────────────────────┘        └──────────────────┘
```

What survives is exactly what should: the amounts, the account identifiers, the timestamps — the financial facts your regulator requires you to retain for seven years. What disappears is exactly what should: the recoverable PII. You have satisfied two obligations that looked mutually exclusive by drawing the line between *facts about money*, which are immutable, and *facts about people*, which are erasable.

## Why it matters

An audit trail that can be edited is not an audit trail; it is a rumor. Event sourcing gives you the real thing — a history that can be replayed, reconciled, and defended, where every correction is itself part of the record. The privacy tension is real, but it is not a reason to abandon immutability. It is a reason to be precise about what your immutable log is *for*. Money-facts are append-only forever; people-facts are separated out and crypto-shredded on request. Get that boundary right and you can look a regulator, an auditor, and an angry customer in the eye and answer the only question that ever mattered: who did what, when, and what did it change.
