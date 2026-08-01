# Perpetual KYC: Continuous Due Diligence
*Retiring the calendar-driven refresh and rebuilding customer due diligence as an event-driven state machine with regulator-grade audit evidence.*

For two decades, Know Your Customer (KYC) refresh ran on a clock. A high-risk customer was re-reviewed every year, a medium-risk one every three, a low-risk one every five. The cycle was tidy for auditors and terrible for reality. A customer flagged low-risk in January can become a shell for sanctioned funds in March, and a five-year clock will not notice until 2031. Perpetual KYC (pKYC) discards the calendar. Instead of asking *"is it time to review this customer?"*, it asks *"has anything happened that changes what we know about this customer?"* — and the answer is computed continuously from events, not from a due date.

This is fundamentally an engineering problem. You are building an event pipeline that feeds a risk-scoring engine, which drives a per-customer state machine, which emits an immutable audit trail. Below is how those three pieces fit together.

## From Periodic to Event-Driven

The periodic model has a hidden assumption: risk changes slowly and predictably. It does not. Risk is bursty. Most customers generate no meaningful signal for years, then produce a cluster of them in a single week — a director change, a spike in cross-border volume, a name that suddenly matches an updated sanctions list.

pKYC inverts the default. A customer sits in a steady **monitored** state consuming events cheaply, and only escalates into a costly human review when a *trigger* fires. The economics are the point: you stop spending analyst hours on customers whose profile has not moved, and you spend them the day a customer's profile does move. Done well, pKYC both lowers total review cost and shortens the window in which a genuinely risky customer goes unexamined.

## The Trigger Taxonomy

A trigger is any event that could invalidate the current risk score. In practice they fall into four families, and each has a different source system and latency profile.

- **Transaction anomalies.** Sudden volume spikes, structuring patterns just under reporting thresholds, first-time payments to a high-risk jurisdiction, or velocity that breaks the customer's own historical baseline. These arrive from the transaction-monitoring stream in near real time.
- **Watchlist and screening hits.** A sanctions-list update, a new politically exposed person (PEP) designation, or adverse-media coverage. These are *pull* events — the list changes, and every existing customer must be re-screened against the delta, not just new applicants.
- **Static-data changes.** A registered-address change, a new phone or email, a nationality update. Individually mundane, but a cluster of them is a classic account-takeover fingerprint.
- **Ownership and control changes.** For corporate customers, a shift in ultimate beneficial ownership (UBO), a new director, or a corporate restructuring that pulls a sanctioned entity into the ownership graph.

The engineering trap is treating all four as the same event. They are not: watchlist deltas are batch and high-fanout, transaction anomalies are streaming and per-customer, ownership changes are rare but expensive to resolve. Normalise them into one canonical `RiskEvent` envelope, but keep the source-specific enrichment attached.

## The Event Pipeline

Every trigger source publishes onto a durable log — one topic per source, fanned into a single normalised stream. A normaliser stamps each event with `customer_id`, `event_type`, `severity`, `source`, and an `observed_at` timestamp, then hands it to the scoring engine. Two properties matter more than throughput.

First, **idempotency**. The same sanctions-list update will be replayed during reprocessing; scoring a customer twice must not create two review cases. Key every event by a stable hash of `(customer_id, source, event_signature)` and deduplicate at ingestion.

Second, **ordering per customer, not globally**. You do not need a global order across millions of customers, but you must process one customer's events in `observed_at` order, or an address change and its reversal can land out of sequence and leave the profile wrong. Partition the stream by `customer_id` and the ordering falls out for free.

The scoring engine consumes normalised events and recomputes a risk band. A material band change — or any event above a hard-severity floor, such as a direct sanctions match — emits a `ReviewRequired` command that transitions the customer's state machine.

## The Customer State Machine

Model each customer as one state machine. The main rail is the happy path; branches carry escalation and exit. The transition table, not prose, is the contract.

```text
   pKYC CUSTOMER LIFECYCLE  (main rail left->right)

   [Onboarded] -> [Monitored] -> [Triggered] -> [Re-Review] -> [Cleared]
       CDD          continuous      risk           targeted       risk
       baseline     screening       signal         refresh        re-scored
                        ^                                            |
                        |                                            |
                        +-------- re-scored, resume monitoring ------+
                                     |               |
   (escalation)                      v               v
                                 [EDD Review]     [Outreach]
                                 enhanced         await
                                 diligence        documents
                                     |               |
   (terminal exit)                   v               v
                                 [SAR Filed]     [Offboarded]
                                 FIU notified    exit relationship
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-perpetual-kyc-monitoring.html)** — the perpetual KYC customer lifecycle: monitored, trigger detected, re-review, clearance, with escalation and terminal-exit branches.

A customer enters **Monitored** once onboarding customer due diligence (CDD) sets the baseline. It stays there, cheaply, until an event moves it to **Triggered**. Triggering is a decision point: a low-severity signal routes to a targeted **Re-Review**, while a high-severity one — a confirmed sanctions match, a UBO change pulling in a listed entity — escalates straight to **EDD Review** (enhanced due diligence).

**Re-Review** is deliberately narrow. You do not re-run the whole onboarding questionnaire; you refresh only what the trigger invalidated. An address-change trigger refreshes proof of address, not source of wealth. If the refresh needs the customer, the machine parks in **Outreach**, a wait state that blocks on an external event (documents received) rather than burning an analyst. When the evidence lands, the risk is **re-scored** and the customer returns to **Monitored** — this loop back is what makes the model *perpetual*.

Two branches are terminal. **EDD Review** that confirms suspicion ends in **SAR Filed**, a Suspicious Activity Report to the financial intelligence unit. **Outreach** that goes unanswered, or a risk the institution will not accept, ends in **Offboarded**. Terminal states never point back into active review — that invariant is what lets you prove a case was actually closed.

## Audit Evidence for Regulators

The hardest requirement is not detecting risk; it is *proving, months later, that you detected it and acted correctly*. A regulator's question is always retrospective: "On this date, why was this customer rated medium-risk, and what did you do about the event on the fifth?"

Answering that requires event sourcing, not a mutable status column. Persist every transition as an append-only record: the `from` state, the `to` state, the triggering `event_id`, the risk score before and after, the model version that produced it, the analyst or rule that authorised it, and a timestamp. The customer's current state is a *projection* over that log, never the source of truth. This buys three things regulators specifically ask for: **reconstruction** (replay the log to see the exact state on any past date), **explainability** (every score change is tied to the concrete event that caused it), and **non-repudiation** (transitions are immutable and attributed).

Hang service-level clocks off the same log. The gap between `Triggered` and `Re-Review` is your detection-to-action latency; the age of the oldest open case is your backlog risk. Both are queries over the transition history, which means the metric you report to the regulator and the evidence behind it come from one source.

## What Changes for the Team

pKYC is less a new product than a shift in ownership. The compliance team stops managing a refresh calendar and starts tuning a trigger taxonomy and score thresholds. Engineering owns an always-on pipeline whose correctness is measured in ordering guarantees and idempotency, not batch completion. The two meet at the state machine — a small, boring, rigorously audited artifact that turns a stream of messy real-world events into a defensible answer to the only question that matters: do we still know who this customer is?
