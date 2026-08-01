# Push-to-Card and Instant Disbursements

*How Original Credit Transactions move money onto a card in near real time — and why pushing is a different animal from pulling.*

Most people meet card rails from one direction: they tap a card and a merchant *pulls* money out of their account. Push-to-card runs the same rails backwards. Instead of debiting a card, you send a credit *to* it. The recipient never shares a bank account number, an IBAN, or routing details — just a card number they already carry in their wallet. Behind that simplicity sits a specific message type, the **Original Credit Transaction (OCT)**, and two network products built around it: **Visa Direct** and **Mastercard Send**.

This post walks the anatomy of a disbursement: the eligibility and limit checks, funding, the OCT authorization itself, and how reversals and returns unwind a push when something goes wrong. Along the way it contrasts a push with the pull transaction every engineer already half-understands.

## Why push instead of an ACH transfer?

The obvious alternative is a bank transfer — ACH in the US, SEPA in Europe. Those are cheap and fine for payroll, but they are slow (ACH settles in one to three business days) and require the recipient to hand over bank credentials. Push-to-card wins on two axes that matter for consumer-facing payouts:

- **Speed.** An OCT typically posts to the recipient's available balance in seconds to minutes, not days. The funds are usable almost immediately, even on weekends.
- **Reach and simplicity.** Nearly everyone has a debit card. Collecting a 16-digit PAN is a far lower-friction onboarding step than a bank-account micro-deposit dance.

That combination is why push-to-card shows up wherever money needs to reach an individual quickly:

- **Gig and marketplace payouts** — a driver or seller cashes out same-day instead of waiting for a weekly batch.
- **Insurance claims** — a claim is approved and the payout lands before the customer leaves the call.
- **P2P transfers** — the "send to a friend's debit card" feature inside many wallet apps.
- **Lending and refunds** — loan disbursement or an early refund pushed straight to a card.

## Push vs. pull: the same rails, reversed

A purchase (pull) is a **financial authorization**: the merchant asks the issuer "may I take X?", the issuer holds the funds, and clearing/settlement moves the money later. The cardholder is the *source*.

An OCT is a **credit push**: the sender is the source of funds, and the recipient's card is the *destination*. The issuer is not being asked to approve a debit against its cardholder — it is being told to credit them. That inversion changes several things:

- **Direction of funds.** Money flows sender → network → issuer → cardholder, the opposite of a purchase.
- **Who is on the hook.** In a pull, the acquirer funds the merchant. In a push, the *originator* must fund the OCT — the money has to exist before the credit is guaranteed.
- **Decline semantics.** An issuer can decline an OCT (bad PAN, ineligible card, sanctions block), but it is not evaluating the cardholder's spending limit — there is no balance to check on the way in.

Because it reuses existing card infrastructure, an OCT is not a magic new pipe; it is a well-defined transaction type carried over the same authorization network as purchases.

## The disbursement flow, step by step

A production push runs through four stages: check, fund, push, confirm — with a fifth branch for reversals. Here is the happy path with the reversal branch attached.

```
 Payer/Platform        Network            Recipient Issuer
      |  check limits      |                     |
      |------------------->|   verify PAN        |
      |                    |-------------------->|
      |                    |<-- eligible --------|
      |<-- OCT ready ------|                     |
      |                    |                     |
      |  fund OCT          |                     |
      |==================>>|   OCT push          |
      |                    |==================>>>|--> credit
      |                    |<-- approved --------|   cardholder
      |<-- confirmed ------|                     |
      |                    |                     |
   - - - reversal / return branch - - - - - - - - -
      |  reversal          |                     |
      |- - - - - - - - - ->|   return OCT        |
      |                    |- - - - - - - - - - >|
      |                    |<-- returned --------|
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-push-to-card-disbursements.html)** — the push-to-card OCT flow: eligibility, funding, the OCT push, issuer credit, and the reversal branch.

### 1. Eligibility and limit checks

Before any money moves, the platform asks two independent questions. First, *its own* limits: does this payout respect per-transfer ceilings, daily and monthly velocity caps, and the recipient's KYC tier? These are your risk controls, not the network's.

Second, *card eligibility*: not every card can receive a push. The network exposes a lookup that returns whether a given PAN supports OCTs, whether it is a debit/prepaid/credit product (payout economics and rules differ), the issuing country, and any fast-funds capability flag. A card that only supports "standard" funding will still credit — just not in seconds. Running this check up front lets you fail fast and, importantly, quote the recipient an honest arrival time.

### 2. Funding the OCT

An OCT is a guaranteed credit, so the originator must have the money first. Depending on the program, funding is either **prefunded** (you maintain a settlement balance the network draws from) or **debited** from a linked source as part of the flow. This is the step with no analog in a pull transaction: in a purchase the issuer's cardholder is the funding source, but in a push *you* are. Get this wrong and you have credited a stranger's card with money you did not have — which is exactly why funding is authorized before the OCT is submitted downstream.

### 3. The OCT authorization

Now the network submits the Original Credit Transaction to the recipient's issuer. The issuer validates the PAN, screens for sanctions and fraud, and either approves or declines. On approval it credits the cardholder's available balance — often instantly for fast-funds-eligible cards — and returns an approval code up the chain. Clearing and settlement between the network and the two banks happen afterward on the normal cycle; the *availability* to the cardholder is decoupled from settlement, which is what makes it feel instant.

### 4. Confirmation

The approval propagates back to the platform, which marks the payout complete and notifies the recipient. Because the credit posts to available balance, "complete" here genuinely means spendable — a stronger guarantee than an ACH "submitted."

## Reversals and returns: unwinding a push

Two distinct mechanisms undo a push, and confusing them causes real bugs.

A **reversal** cancels an OCT the network still owns — typically when the original authorization timed out, was duplicated, or errored before it was fully confirmed. It nets out the transaction as though it never posted.

A **return** happens *after* the credit has posted: the issuer sends the funds back because the account is closed, the card is invalid, or the recipient disputes the credit. Returns arrive asynchronously, sometimes days later, so your ledger cannot assume "confirmed" is final forever. Both paths must restore the payer's funding source and reconcile against the original transaction ID.

Idempotency is the engineering lesson here. Network timeouts are common, and a naive retry can push twice. Every OCT should carry a client-generated idempotency key so a retried request returns the original result instead of minting a second credit.

## What to build around it

Treat push-to-card as a state machine, not a single API call: `checked → funded → pushed → confirmed`, with `reversed` and `returned` as branches off the later states. Persist the network transaction ID and your idempotency key on every row, expose limit checks before you take the recipient's card, and never mark a payout immutable — a return can arrive after the money looked settled. Do those four things and instant disbursement stops being a demo and becomes a rail you can trust with payroll.
