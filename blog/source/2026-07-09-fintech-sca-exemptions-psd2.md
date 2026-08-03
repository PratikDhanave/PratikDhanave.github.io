# Engineering SCA Exemptions Without Wrecking Conversion

*Deciding low-value, TRA, and trusted-beneficiary exemptions so low-risk payments stay frictionless while genuine risk gets challenged via 3DS.*

Strong Customer Authentication is a regulatory requirement, but from an engineering seat it is really a routing decision made a few hundred milliseconds before you authorize a card. Every online payment either goes through an authentication challenge — the 3-D Secure step-up a shopper sees as a one-time code or an in-app approval — or it slips through frictionless because a valid exemption applies. Get that routing right and most of your traffic never sees a challenge screen. Get it wrong and you either bleed conversion to unnecessary friction or hand the issuer an easy reason to decline.

This post is about the decision engine that sits in that gap: what an exemption actually is, the ones worth building, and why an exemption is a request rather than a guarantee. The examples are generic, but the shape holds across most acquirer and orchestration stacks.

## An exemption is a flag you set, not a challenge you skip

The first mental model to fix: your system does not decide whether authentication happens. The issuer does. What you control is the *exemption flag* you send in the authorization message, and the risk data you attach to justify it. You are making an argument to the issuer — "this payment is low risk, please authorize it without a challenge" — and the issuer is free to agree, ignore you and soft-decline back to a challenge, or authorize outright.

That framing changes how you build. The engine's output is not "frictionless, done." It is "requested frictionless, with this justification, now handle the case where the issuer disagrees." A clean flow makes both outcomes first-class:

```
 request --> rule engine --> decision --> frictionless (SCA exempted)
                                |
                                +--------> 3-D Secure (issuer step-up)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-sca-exemptions-psd2.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The rule engine evaluates the transaction against every exemption you support, picks the strongest one that qualifies, and the decision node either flags frictionless or routes to a challenge. The branch is not an error path — it is the expected outcome for anything the rules can't safely exempt.

## The exemptions worth building

You don't need all of them, and they don't carry equal weight. Four cover the bulk of real traffic.

**Low-value.** Transactions under a fixed threshold can skip authentication, subject to a cumulative counter — a running count and amount since the last successful challenge. This one is deceptively stateful. You cannot decide it from the current transaction alone; you need the card's recent exemption history, which means a lookup keyed on the payment instrument. Miss the counter and you'll claim the exemption on a card that has already exhausted it, and the issuer will bounce it straight back.

**Transaction Risk Analysis (TRA).** The high-value workhorse. If your acquirer's fraud rate sits inside a defined band, you may exempt payments up to a ceiling tied to that band — a lower measured fraud rate unlocks a higher exemption ceiling. TRA is the one that requires you to *earn* the right to use it: it is contingent on your own portfolio's fraud performance, calculated on a rolling window, and it degrades the moment fraud creeps up.

**Trusted beneficiary (allowlist).** After a successful challenge, a shopper can add a merchant to a list of trusted payees held at the issuer. Subsequent payments to that merchant qualify for frictionless. You don't own the list — the issuer does — but you signal that you believe the relationship exists, and you benefit from every repeat customer who opted in.

**Recurring and merchant-initiated.** Fixed-amount subscriptions authenticate once at setup; later charges ride an exemption because the shopper isn't in the loop. Merchant-initiated transactions more broadly fall outside the scope of a live authentication because there is no customer present to authenticate.

The engineering point is that these are ranked, not parallel. A single transaction might qualify for two at once — low-value *and* trusted-beneficiary. Pick deterministically: prefer the exemption that shifts fraud liability in your favor and is least likely to be overturned, and record which one you chose, because when a chargeback lands months later you will need to prove the basis for skipping the challenge.

## Why frictionless is a bet, not a free pass

Every frictionless authorization is a small wager. When you challenge and the shopper completes 3-D Secure, fraud liability for that transaction shifts to the issuer. When you exempt, liability generally stays with you. So the exemption you request to save a conversion point is the exemption that leaves you holding the loss if it turns out to be fraud.

That is the tension the whole engine has to balance, and it is why a naive "exempt everything under the ceiling" policy is a trap. You'd maximize frictionless rate and quietly maximize your own fraud exposure at the same time. The engine has to weigh the conversion gain of skipping a challenge against the expected loss of owning that transaction's fraud.

In practice this means the exemption decision leans on the same risk signals as your fraud model — device history, velocity, account age, the amount relative to the shopper's norm — not just the flat regulatory threshold. Two payments can both sit under the TRA ceiling; you might request the exemption on one and force a challenge on the other because the risk signals disagree. The regulation sets the outer boundary of what you're *allowed* to exempt. Your risk appetite sets what you *should*.

## Handling the issuer's veto

Because the issuer can override, the flow must treat a soft-decline as routine. You request frictionless; the issuer responds with a soft-decline signalling it wants authentication after all. The correct behavior is to fall through to 3-D Secure and re-present the transaction, not to surface a hard failure to the shopper.

Build this as an automatic step, not an exception handler:

```python
def route(txn, history):
    ex = strongest_exemption(txn, history)   # ranked, deterministic
    if ex and risk_ok(txn):
        resp = authorize(txn, exemption=ex)   # request frictionless
        if resp.soft_declined:
            return challenge_3ds(txn)          # issuer wants auth
        return resp
    return challenge_3ds(txn)                  # no exemption we'll stand behind
```

The shopper should never notice the retry. From their side, a soft-decline that flips to a challenge looks identical to a payment that was routed to 3-D Secure in the first place. What you must avoid is the double-hit: charging a challenge, failing, and *then* deciding whether to exempt — always resolve the exemption before you touch the authorization rail.

## What to instrument

The metric that tells you whether the engine is healthy is the pair, never either number alone. Watch **exemption rate** — the share of eligible traffic you send frictionless — directly against the **fraud rate** on exempted transactions. A rising exemption rate looks like a conversion win right up until the fraud on that slice sours, and because chargebacks lag by weeks, the damage is already booked by the time it shows.

Track a few more:

- **Soft-decline rate by exemption type** — a spike means issuers stopped trusting the argument you're making; the exemption is effectively dead weight.
- **TRA ceiling headroom** — how close your rolling fraud rate sits to the next band boundary, because crossing it silently shrinks what you can exempt.
- **Challenge abandonment** — how many shoppers drop at 3-D Secure, which is the conversion cost you're trying to avoid and the number that justifies every exemption you take.

The engine is doing its job when the frictionless rate is high, the fraud on that traffic is flat, and the challenges you do raise are landing on the payments that genuinely needed them. That balance is a live setting, not a one-time configuration — it moves with your fraud performance, and the instrumentation is what keeps you honest about which way it's drifting.
