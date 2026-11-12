# Revenue Integrity — Reconciliation, Recognition, and the Metrics Finance Will Compute Anyway

*The billing system's last responsibility is proving itself: that every invoice matches money that actually moved, that revenue is recognized when it's earned rather than when it's charged, and that the metrics the business runs on — MRR, churn, net revenue retention — derive from billing data by defined rules rather than by whichever spreadsheet ran last. Revenue integrity is where billing engineering meets accounting, and the systems that skip it get audited into building it retroactively.*

This post closes the series by connecting posts [2](/blog/posts/bill-02-pricing-models-in-code.html)–[7](/blog/posts/bill-07-testing-billing-systems.html)'s machinery to the financial record — with the ledger mechanics themselves living in the [Fintech Engineering Handbook](/blog/series/the-fintech-engineering-handbook/).

## Reconciliation: three systems, one truth

Money state lives in three places that drift unless actively reconciled: the **billing system** (invoices issued, post 5), the **payment processor** (charges attempted, succeeded, refunded, disputed), and the **bank/ledger** (cash that actually settled, minus fees). Reconciliation is the continuous process of matching records across the three and explaining every difference:

- **Invoice ↔ charge** — every finalized invoice matches processor charges summing to its total; every charge references an invoice. Orphans on either side are incidents: an unpaid invoice is dunning's business (post 5), but a *charge with no invoice* is the scary direction — money taken without a document.
- **Charge ↔ settlement** — processor payouts arrive batched, net of fees, days later. Matching payouts back to their constituent charges (and fees to their own expense line) is tedious exactly in proportion to how little structure you kept; charge-level metadata carrying invoice IDs makes it a join instead of an investigation.
- **The exception queue** — reconciliation's product is a short, owned list of unmatched items with aging; its health metric is that list's size and age. A thousand-line "differences" spreadsheet nobody owns is reconciliation theater.

The design callback: this is why posts 3 and 5 insisted on immutable events, re-derivable invoices, and document-attached collection state. Reconciliation is cheap when every record was born with the keys to match it, and archaeologically expensive when it wasn't.

## Recognition: when revenue is actually earned

The accounting rule that surprises engineers: charging a customer is not earning revenue. A $1,200 annual plan paid in January is $100 of *earned* revenue per month; the rest sits as **deferred revenue** — an obligation to deliver service — until each month passes. Usage-based revenue recognizes as usage happens; setup fees may recognize over expected lifetime; refunds and credits reverse recognition. Engineers don't need to become accountants, but billing systems need to **emit the events recognition is computed from**: service-period boundaries on every line item (post 5's invoices already carry them), usage timestamps (post 3's event time — again), and credit/refund linkage to original lines. Get those on the record and recognition is downstream computation; omit them and finance reconstructs service periods by guessing, which is how restatements happen.

## Metrics: define once, derive always

MRR, ARR, churn, expansion, net revenue retention — the business will run on these numbers, and if engineering doesn't define them from billing data, three departments will define them differently from exports. The engineering stance: metrics are **derived, versioned definitions over billing facts** — e.g., MRR = normalized monthly value of active subscriptions' pinned price versions (post 2), with explicit, documented decisions for the ambiguous cases: trials (excluded until converted), usage revenue (trailing actual vs committed minimums), discounts (net, with gross tracked), pauses and past-due (post 4's states each get a rule), annual prepays (normalized to monthly). Every change event the lifecycle emits (post 4) becomes a *movement* — new, expansion, contraction, churn, reactivation — and MRR movement reports fall out of the state machine's own transitions. The integrity test mirrors the golden invoices of post 7: metric definitions are code, changes are reviewed, and the dashboard, the board deck, and the finance close all read the same derivation.

The takeaway: revenue integrity is three disciplines — **reconciliation** (invoice ↔ charge ↔ settlement, with a short owned exception queue, cheap only because earlier posts kept matchable, immutable records), **recognition** (revenue is earned over service periods, not at charge time — the system's job is emitting period boundaries, usage times, and credit linkage so deferral is computable), and **metrics as versioned derivations** (MRR and its movements defined once in code from the state machine's own transitions). It's the series' closing argument: billing built as engineering all along is billing that can *prove itself* — to finance, to auditors, and to you.

## Key takeaways

- Reconcile three systems continuously — **billing ↔ processor ↔ settlement** — with charge metadata carrying invoice keys so matching is a join; the deliverable is a short, owned, aging **exception queue**, and a charge-without-invoice is the five-alarm direction.
- **Recognition ≠ charging**: annual prepay defers, usage recognizes as it happens, credits reverse — the billing system's duty is emitting service periods, event times, and linkage, making deferral downstream math instead of forensic guessing.
- **Metrics are versioned code over billing facts**: MRR with documented rules for trials, usage, discounts, pauses; movements (new/expansion/contraction/churn) derived from lifecycle transitions — one definition for dashboard, deck, and close.
- The whole series converges here: immutable events, pinned versions, re-derivable documents — built for correctness, they make integrity *provable* rather than asserted.

## Further reading

- [Revenue recognition — when income is actually earned](https://en.wikipedia.org/wiki/Revenue_recognition)
- [Reconciliation (accounting) — matching records until differences are explained](https://en.wikipedia.org/wiki/Reconciliation_(accounting))
