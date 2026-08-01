# Stand-In Processing (STIP): Authorizing When the Issuer Is Down

*How a network authorizes on the issuer's behalf when the issuer host is unreachable — and how the books get squared afterward.*

Every card authorization is, at heart, a question routed to the issuer: *is this account good for this amount right now?* The issuer's authorization host answers in real time, usually within a few hundred milliseconds. But hosts fail. Maintenance windows overrun, a data center partitions, a garbage-collection pause blows past the timeout, or the whole platform simply goes dark. When that happens at a terminal in a store, the cardholder does not care whose fault it is. The transaction either completes or it does not.

Stand-In Processing (STIP) is the answer the industry built for that moment. When the issuer cannot respond, the network — or a delegated processor — steps in and authorizes on the issuer's behalf, inside a envelope of pre-agreed rules and limits. It is one of the highest-stakes fallback systems in payments: it trades a small, bounded amount of credit risk for continuity, and then it reconciles that risk back to the issuer the moment the issuer is reachable again.

## Why not just decline?

The naive answer to "issuer is down" is to decline everything. It is safe and it is terrible. A widespread decline storm during an issuer outage means every cardholder of that bank is stranded at once — groceries abandoned, fuel pumps refused, hotel check-ins blocked. The reputational and contractual damage dwarfs the fraud risk of approving a bounded set of small transactions.

So networks let issuers pre-authorize a fallback posture. The issuer effectively says: *if you cannot reach me, here is how to behave.* STIP is that behavior, encoded as parameters the network holds on the issuer's behalf.

## The fallback trigger

The first engineering problem is deciding *when* to stand in. This is not a single flag; it is a cascade of conditions:

- **Hard connectivity loss** — the network's link to the issuer host is down or the signon (0800/0810 in ISO 8583 terms) is stale.
- **Timeout** — the issuer received the auth request (0100) but did not return a response (0110) within the network's response-time window, often ~2–5 seconds.
- **Malformed or repeated failures** — the issuer answers, but with format errors or a rising error rate that crosses a health threshold.

The subtlety is the timeout case. A timeout does not mean the issuer did not process the request — it may have approved it and posted a hold, but the response was lost in transit. That ambiguity is precisely why reconciliation later is non-negotiable: the issuer may already have a record the network does not know about.

## Stand-in rules and limits

Once STIP engages, the network evaluates the transaction against the issuer's stand-in parameter set. This is where the risk appetite lives, and it is deliberately conservative:

- **Per-transaction ceiling** — approve only up to some amount (say, a modest floor limit); anything above declines.
- **Cumulative exposure cap** — a rolling limit on total stand-in approvals per card during the outage, so a single compromised card cannot rack up unbounded charges.
- **Velocity rules** — a maximum count of approvals per card per interval.
- **Category and geography filters** — block high-risk MCCs (cash advance, gambling, crypto) or transactions far outside the card's normal footprint.
- **Card status checks** — the network still enforces what it *does* know: expired cards, cards on a negative/hotlist file, or blocked BINs decline regardless of amount.

Everything above the envelope declines. That decline is a real, terminal outcome for the transaction — not a queued item — because approving beyond the limit would create exposure the issuer never agreed to carry.

```
   STIP AUTHORIZATION LIFECYCLE

   [Online Auth] --> [Issuer Timeout] --> [Stand-In Eval] --> [Advice Queued] --> [Reconciled]
    routed to         no response         rules + limits       store & forward     issuer posts
    issuer                |                    |                    |                   |
                     (fallback armed)          |                    |                   |
                                               v                    v                   v
                                        [Declined by Limit]   [Advice Retry]     [Force-Post
                                         exposure cap          issuer offline      Reversal]
                                                                    |             issuer rejects
                                                                    v
                                                             [Advice Expired]
                                                              TTL exhausted
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-stand-in-processing-stip.html)** — the STIP state machine: online auth, issuer timeout, stand-in decision within limits, advice store-and-forward, and reconciliation with its terminal exits.

## The advice: a promise to reconcile

Here is the part engineers most often underestimate. When the network approves (or declines) in stand-in, it has made a decision the issuer knows nothing about. The issuer's own ledger has not moved. To close that gap, the network generates an **advice** — in ISO 8583 terms a 0120 authorization advice (or a 0220 financial advice for single-message flows).

An advice is not a request; it does not ask permission. It *informs*: "while you were unreachable, I authorized this transaction for this amount on this card under your stand-in rules." Advices are held in a store-and-forward queue on the network side. They carry the original transaction data plus a flag marking them as stand-in-generated, so the issuer can treat them differently from normal traffic.

The queue is the risk ledger. Every advice sitting in it represents money the issuer is on the hook for but has not yet booked. Engineering this queue well matters:

- **Durability** — advices must survive a network-side restart; they are the only record of the approval.
- **Ordering and idempotency** — each advice needs a stable key (network reference / retrieval reference number) so replaying it never double-posts.
- **Retry with backoff** — while the issuer host is still down, advices retry on a schedule rather than hammering a recovering system.
- **Time-to-live** — advices cannot retry forever; an undeliverable advice eventually expires, and the exposure is settled through network dispute or clearing files instead.

## Reconciliation: settling the advices

When the issuer host comes back and signs on again, the network drains the advice queue to it. This is the "issuer reconciles" state — and it is where the stand-in period is finally squared against reality.

The issuer replays each advice against its own account state as it exists *now*, post-outage:

1. **Normal case** — the account had funds/credit; the issuer posts the hold or debit and acknowledges the advice. The transaction is now fully consistent across network and issuer.
2. **The timeout ambiguity resolves** — if the issuer had actually processed the original 0100 before the response was lost, it deduplicates against the advice's reference number so the cardholder is charged once, not twice.
3. **Reversal** — occasionally the issuer, replaying against current state, finds the stand-in approval untenable (the account was closed, or hit its true limit). It cannot un-ring the bell — the merchant was already told "approved" — but it can generate a reversal or push the item into the dispute/chargeback rails to recover funds. This is the residual cost of standing in.

The reconciliation phase is what makes STIP honest. Continuity is delivered at the moment of the outage; correctness is restored afterward. The window between them is exactly the exposure the limits were designed to bound.

## What the state model teaches

Reduced to a state machine, STIP is a clean lesson in designing for partial failure. The happy path — online auth to reconciled ledger — is a straight rail. Everything interesting hangs off the later phases as bounded exceptions: an over-limit decline that terminates immediately, an advice that retries then expires, a reconciled item the issuer later reverses.

The engineering discipline is in the boundaries. Stand-in is not "approve when unsure"; it is "approve *this much*, *this often*, for *these categories*, and record every approval as a durable, idempotent promise you will make good the instant the issuer is reachable." Build the limits too tight and you recreate the decline storm you were avoiding. Build them too loose and an issuer outage becomes an issuer *loss event*. STIP lives in the narrow band between availability and exposure — and the advice queue is the ledger that keeps that trade honest.
