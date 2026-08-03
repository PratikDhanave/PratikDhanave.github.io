# Account Updater and the Card-on-File Lifecycle
*How Visa Account Updater and Mastercard Automatic Billing Updater keep stored credentials alive when cards get reissued, expire, or change numbers.*

Every subscription business runs on a quiet assumption: the card a customer entered last year still works today. It usually does not. Cards expire on a rolling schedule, get reissued after breaches, and are re-numbered when a portfolio migrates between issuers. When the stored credential goes stale, the next recurring charge fails, and the customer churns without ever deciding to leave. That is *involuntary churn* — cancellation caused by payment failure rather than intent — and for a healthy subscription book it can quietly account for a large share of monthly losses.

Account Updater is the network machinery built to close that gap. Visa calls its version VAU (Visa Account Updater); Mastercard calls it ABU (Automatic Billing Updater). Both solve the same problem: keep a merchant's stored card credentials synchronized with the issuer's current view of the account, so a reissued card keeps billing without the customer ever touching their payment settings.

## The credential-on-file problem

A card-on-file (CoF) credential is any card a merchant stores to charge later — the classic recurring subscription, but also one-click checkout and installment plans. The card networks treat stored credentials as a regulated category. Merchants must flag the first transaction as credential establishment, tag subsequent charges as merchant-initiated or cardholder-initiated, and honor mandates about how long a dormant credential may sit unused. The point of these rules is trust: an issuer needs to know that a charge arriving with no cardholder present is a legitimate continuation of a relationship the customer agreed to.

But storing a credential creates a synchronization duty. The moment the issuer reissues that card, the merchant's copy is wrong. Account Updater is the network-sanctioned channel for repairing that drift — and using it is increasingly not optional. Both networks expect merchants with stored credentials to participate in an updater program or an equivalent, precisely because stale credentials generate the declines and retries that clog the authorization network.

## How the update flow works

The mechanics are a matching service. The merchant submits its vault of stored credentials; the network cross-references each one against issuer records and returns what changed.

```
  Merchant / Biller        Updater Service          Network / Issuer
   (card-on-file vault)    (VAU / ABU)             (scheme + issuer)
         |                      |                        |
         |--- submit batch ---->|                        |
         |   (PAN, expiry)      |--- query updates ----->|
         |                      |                        |
         |                      |<-- new PAN / expiry ---|
         |                      |<-- closed / contact ---|
         |                      |                        |
         |<-- update responses -|                        |
         |   (apply to vault)   |                        |
         |                      |                        |
         |------------- retry billing ----------------->|
         |<------------ authorized ---------------------|
         v                      v                        v
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-account-updater-cof.html)** — Card-on-file batch submission, network resolution, and rebilling with refreshed credentials.

Two delivery models coexist. The **batch** model is the traditional one: a merchant packages its stored PANs on a schedule — often weekly or monthly — submits the file, and receives a response file listing the changes. It is efficient for large books but introduces latency; a card reissued the day after your batch runs stays stale until the next cycle. The **real-time** model queries the updater inline, typically just before a scheduled charge or immediately after a decline, so the freshest data is applied at the moment it matters. Mature billing systems use both: batch to keep the whole vault broadly current, real-time to rescue a specific charge that is about to fail.

Either way, the merchant never sees a full replacement dump of the portfolio. The updater returns a delta — only the credentials that changed — keyed so the merchant can match each response back to a specific stored card.

## Reading the responses

The value of Account Updater is entirely in how carefully the merchant handles the responses. Each returned credential carries a reason code, and the three broad outcomes demand three different behaviors.

**Updated.** The card was reissued with a new number, a new expiration date, or both. The merchant replaces the stored PAN and expiry in its vault and continues billing normally. This is the happy path and the whole reason the program exists — the customer's subscription survives a reissue they never noticed.

**Closed / do not honor.** The account was closed and there is no forwarding card. Continuing to bill it will only generate declines and, worse, can attract network fines for repeatedly authorizing against a known-dead credential. The correct action is to stop billing that credential and move the customer into a dunning or recovery flow that asks them to add a new card.

**Contact cardholder.** The issuer signals that something about the account needs the customer's attention — a new card exists but cannot be auto-propagated, or the account status is ambiguous. Here the merchant should not silently retry; it should prompt the customer directly. Treating this as a soft failure and hammering the network with retries is exactly the behavior the reason code is trying to prevent.

The discipline that separates a good integration from a lazy one is respecting the *closed* and *contact* codes as firmly as the *updated* code. It is tempting to only wire up the happy path and let the rest fall into generic retry logic, but that reintroduces the decline noise Account Updater was meant to remove.

## Network tokenization as the alternative

Batch updater programs are a repair mechanism — they fix credentials after they drift. Network tokenization attacks the problem from the other side: it removes the drift.

Instead of storing the raw PAN, the merchant stores a network-issued **token** that references the underlying card. When the issuer reissues the physical card, the token stays stable and the network re-maps it to the new PAN behind the scenes. There is no batch to submit and no response file to parse — the credential is effectively self-healing. The token is also domain-restricted and useless if stolen from the merchant's vault, which shrinks the breach blast radius and can improve authorization rates because issuers trust tokenized transactions more.

Tokenization does not make Account Updater obsolete, though. Not every card in a merchant's book is tokenizable — coverage depends on issuer participation and card type — and merchants migrating a legacy PAN vault still need the updater to keep the untokenized remainder current. The pragmatic posture is to treat them as complementary: tokenize everything you can so those credentials never go stale, and run an updater program over the residual PANs so the rest still get repaired. Together they cover far more of the portfolio than either does alone.

## What to build around it

Account Updater is not a fire-and-forget integration. The engineering that surrounds it matters as much as the connection itself. Schedule batches to run ahead of your billing cycle so refreshed credentials are in place before charges fire, not after they fail. Match every response back to a stored credential idempotently, so a re-sent file never double-applies a change. Record the reason code and update timestamp against each credential — that history is what lets you distinguish a card that was genuinely updated from one you should stop billing. And instrument the outcome: the metric that proves the program is working is a falling involuntary-churn rate, measured as recovered charges that would otherwise have declined.

Done well, the whole lifecycle is invisible. A customer's bank sends them a new card, they activate it, and their subscriptions keep running as if nothing happened. That silence is the product.
