# Invoicing and Collection — From State to Document to Money

*The invoice is where billing's abstractions become a legal document and an attempted charge. Everything upstream — price versions, metered totals, prorations — converges into line items a human must be able to read and a regulator must be able to audit; then the system has to actually collect, which means confronting the fact that a meaningful fraction of payments fail. Invoicing is document engineering; collection is failure engineering; revenue requires both.*

Posts [2](/blog/posts/bill-02-pricing-models-in-code.html)–[4](/blog/posts/bill-04-the-subscription-state-machine.html) produced the inputs. This post turns them into money — and hands the ledger-side mechanics to the [Fintech Engineering Handbook](/blog/series/the-fintech-engineering-handbook/) where the actual payment rails live.

## The invoice is an immutable derivation

An invoice is a *derived document*: for a customer and a period, gather the subscription state, the pinned price versions, the finalized metered totals (post 3's batch truth, after the grace window), and any prorations, credits, or minimums — and compute line items, subtotals, tax, and total. Two properties make it trustworthy:

- **Re-derivable.** Because every input is versioned and immutable, the same inputs must always produce the same invoice. If a regenerated invoice differs from the issued one, something upstream mutated — and that's an incident, not a curiosity. Re-derivability is the practical test that posts 2–4 were built right.
- **Immutable once finalized.** Drafts can change; a finalized invoice never does. Corrections are *new documents* — credit notes and adjustment invoices that reference the original — exactly the append-only discipline of the ledger, because finance and auditors reconcile against issued documents, not current database rows.

The draft-finalize gap deserves design: a draft open during the metering grace window absorbs late events; finalization is the moment totals freeze, tax is computed, sequential numbering (a legal requirement in many jurisdictions) is assigned, and the document enters the collection path. Tax itself is a pluggable stage — rates and jurisdiction rules change under you, so invoices store *the tax decision made* (rate, jurisdiction, basis) rather than re-deriving it later from mutable rules.

## Collection: designing for the failed charge

Issuing the document is half the job; charging the stored payment method is the other half, and it fails routinely — expired cards, insufficient funds, issuer suspicion, stale mandates. The machinery that recovers this revenue is **dunning**, and it's among the highest-ROI systems in billing because every recovered failure is pure margin:

- **Retry with intelligence.** Failures split into *hard declines* (card reported stolen, account closed — do not retry) and *soft declines* (insufficient funds, try-later signals — retry on a schedule). Retrying hard declines burns processor reputation; not retrying soft ones abandons revenue. The schedule itself matters: spaced over days, biased toward paydays and local daytime, capped in attempts.
- **Involve the customer early.** Parallel to retries: notify, with a frictionless update-payment-method path. Many failures only resolve when a human replaces a card — the email *is* part of the collection system, and its copy, timing, and escalation deserve the same review as code.
- **Decide the end state.** Retries exhausted: now what? Suspend (past-due access policy from post 4), downgrade, cancel, write off, or hand to humans — per-segment policy (enterprise accounts get a person, self-serve gets automation), encoded as the dunning state machine's terminal edges.
- **Measure recovery.** Dunning is an optimization loop: involuntary-churn rate, recovery rate by retry number, time-to-recovery. Teams that instrument it find the second retry and the first email do most of the work — and that each later touch has a cost in goodwill.

One structural rule ties the halves together: **collection state lives on the invoice, not the subscription**. The subscription knows it's past-due (post 4); *which* invoice is unpaid, how many attempts, what's next — that's invoice-level state, because a customer can owe two invoices with different histories, and reconciliation (post 8) matches payments to documents, not to vibes.

The takeaway: an invoice is an **immutable derivation** — re-derivable from versioned inputs, frozen at finalization (with tax decisions stored, numbering assigned), corrected only by new referencing documents. Collection is failure engineering: dunning that distinguishes hard from soft declines, schedules retries deliberately, treats customer notification as part of the machinery, encodes explicit terminal policies per segment, and measures its own recovery. Document engineering plus failure engineering — that's how billing state becomes actual money.

## Key takeaways

- The invoice is **derived, re-derivable, and immutable once finalized** — regeneration mismatch means upstream mutation (an incident); corrections are new documents (credit notes), never edits.
- The **draft window** absorbs metering's grace period; finalization freezes totals, computes and *stores* the tax decision, and assigns sequential numbering where law requires it.
- **Dunning** is the highest-ROI billing subsystem: hard vs soft decline classification, deliberate retry schedules, early customer notification with a painless card-update path, explicit per-segment terminal policies.
- **Collection state attaches to invoices**, not subscriptions — multiple unpaid documents have independent histories, and reconciliation matches payments to documents.
- Instrument recovery (rate by attempt, involuntary churn) — the data reliably shows early touches doing most of the work.

## Further reading

- [Invoice — the document being engineered](https://en.wikipedia.org/wiki/Invoice)
- [Dunning — the discipline of collecting failed payments](https://en.wikipedia.org/wiki/Dunning_(process))
