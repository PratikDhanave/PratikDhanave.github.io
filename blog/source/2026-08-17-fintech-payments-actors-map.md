# The Card Payment Actors Map: Who Actually Does What

*One reference model of every party in a card transaction — cardholder, merchant, gateway, acquirer/processor, scheme, and issuer — and the settlement path that moves the real money back the other way.*

---

## Why the actor map is the first thing to get right

Most confusion about card payments comes from collapsing six distinct parties into two words: "the bank" and "the processor." When you are integrating, debugging a decline, or reasoning about where a fee or a liability lands, that shorthand fails you immediately. A card transaction is a relay between roles, and each role owns a specific decision, a specific record, and a specific slice of the money.

The single most useful mental model is this: a card payment runs on **two flows moving in opposite directions**. An authorization message travels *from* the cardholder *toward* the issuer to ask "is this allowed?" A settlement flow later travels *from* the issuer *back toward* the merchant to actually move funds. The request path answers a question in real time; the funding path fulfils it hours or days later. Keep those two flows separate in your head and the whole system stops feeling like magic.

## The request path, drawn out

Here is the forward path an authorization takes, from the person tapping a card to the bank that issued it.

```
  [Cardholder] ──card──> [Merchant] ──> [Gateway] ──> [Acquirer /
       ^                                                 Processor]
       │                                                     │
       │                                                     v
       │                                               [Card Scheme]
       │                                                     │
       │        approve / decline                            v
       └─────────────────────────────────────────────── [Issuer]
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-payments-actors-map.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Every hop adds something and forwards the rest. The merchant captures the card credentials and an amount. The gateway encrypts and formats them. The acquirer routes to the correct network. The scheme finds the right issuer. The issuer makes the actual approve-or-decline decision against the cardholder's account. Then a response threads all the way back along the same chain in milliseconds. Nothing has moved yet — this is purely a question and an answer.

## The six actors, one responsibility each

**Cardholder.** The person or business whose account is charged. They hold a card issued against a line of credit or a deposit account. In the message flow they contribute exactly two things: the card credentials (PAN, expiry, and increasingly a network token instead of the raw number) and consent to the amount.

**Merchant.** The party selling something and getting paid. Critically, the merchant does not talk to banks directly. They hold a *merchant account* provisioned by an acquirer and identified by a merchant ID (MID) and a merchant category code (MCC). Their job is to capture the transaction and hand it upstream — and, later, to reconcile what actually landed in their bank account against what they sold.

**Gateway.** The merchant's technical front door to the payment networks. The gateway takes the raw transaction, encrypts sensitive fields, applies tokenization to keep the merchant out of PCI scope, and translates the request into the network's message format. A gateway makes no money-movement decision; it is plumbing and security. Many providers bundle the gateway and the acquirer, which is exactly why people conflate the two — but the roles are distinct.

**Acquirer / Processor.** The acquirer is the merchant's bank in the transaction: it holds the merchant account and is financially responsible for routing the payment and, ultimately, for funding the merchant. The *processor* is the operational engine — often a separate company — that handles the connectivity, authorization routing, and clearing files on the acquirer's behalf. One is the licensed financial institution; the other is the technical operator. They are frequently the same brand and almost always discussed as one box, but liability sits with the acquirer.

**Card scheme.** Visa, Mastercard, and their peers. The scheme is the network and the rulebook. It does not hold anyone's money and it does not approve transactions. It routes the authorization to the correct issuer, sets the interchange rates, defines the message standards, and later calculates who owes whom at settlement. Think of it as a switch plus a clearinghouse plus a regulator for its own ecosystem.

**Issuer.** The bank that gave the cardholder the card. The issuer is where the real decision happens: it checks the balance or credit line, runs fraud and risk models, applies velocity and spending controls, and returns an approve or decline. The issuer carries the credit risk on the cardholder and, at settlement, is the party that actually pays.

## The settlement path: where money moves the other way

Authorization is a promise; settlement is the payment. This is the flow engineers most often forget to model, because it happens asynchronously and off the request path.

After authorizations are captured, the acquirer batches them and submits clearing records to the scheme. The scheme nets the day's activity across all its participants and instructs each issuer to fund. The money then travels **back down the chain in the opposite direction to the request**:

```
  [Issuer] ──funds──> [Card Scheme] ──net──> [Acquirer] ──payout──> [Merchant]
                          (settlement / interchange applied here)
```

Two things happen on this return leg that define the economics. First, **interchange** — a fee set by the scheme and paid by the acquirer to the issuer — is deducted here. Second, the acquirer's own markup (the *acquirer margin*, plus scheme fees) is applied before the merchant is paid. The merchant receives the transaction amount minus the merchant discount rate, which bundles interchange, scheme fees, and acquirer margin. This is why the merchant's payout never equals the sticker price, and why reconciliation has to match gross sales against net deposits with the fee breakdown in between.

The timing gap matters too. Authorization is instant; funding typically lands a day or two later depending on the acquirer's settlement schedule and cut-off times. Your ledger must therefore carry a receivable between capture and payout, and your reconciliation job must age anything that is captured but not yet funded.

## Where liability and fees actually sit

The actor map pays off when you use it to answer the two questions behind every real incident: who bears the loss, and who takes the fee.

- **Fees flow up on the return leg.** Interchange goes to the issuer, scheme fees go to the network, and the acquirer keeps its margin. The merchant absorbs all of it as the discount rate.
- **Fraud liability depends on authentication.** For card-present chip and for card-not-present transactions authenticated with 3-D Secure, liability generally shifts to the issuer. For unauthenticated card-not-present fraud, it typically sits with the merchant. The scheme's rules, not your code, decide this — but your integration determines which authentication path you took.
- **Chargebacks run the chain in reverse.** A disputed transaction originates with the cardholder, is raised by the issuer, travels through the scheme to the acquirer, and lands on the merchant to defend. Same six actors, same relay, opposite direction.

Keep the map in front of you and these stop being mysteries. A decline is an issuer decision, so no acquirer retry will fix it. A missing payout is an acquirer settlement question, not a gateway bug. The six-actor model is not trivia — it is the coordinate system you debug and design against.

## What to hold onto

A card payment is a relay across six parties with two flows in opposite directions: an authorization question travelling from cardholder to issuer, and a settlement payment travelling from issuer back to merchant. Each actor owns exactly one responsibility — the merchant sells, the gateway secures and formats, the acquirer routes and funds, the scheme switches and sets rules, the issuer decides and pays. Money never moves on the request path; it moves only on settlement, minus interchange, scheme fees, and acquirer margin. Fix the map first, and declines, missing payouts, fee surprises, and chargebacks all resolve to a specific actor and a specific leg of the flow instead of a vague "the bank did something."
