# Agent Identity, Delegation, and Scoped Authorization

*When software spends money on your behalf, the merchant has to answer two questions before the charge clears: which agent is this, and what did the human actually let it do.*

Agentic commerce breaks a comfortable assumption. For two decades, "the party at the checkout" and "the account holder" were treated as the same entity, verified with the same password, the same card, the same one-time code. An autonomous agent snaps that link in half. The buyer is a piece of software; the human who authorized it is somewhere else entirely, possibly asleep. So the merchant and the payment provider now have to reason about a delegation chain rather than a single identity.

That reasoning collapses into two questions, and everything in this post is machinery for answering them.

## The two questions

The first question is **who is the agent**. Not "is there a valid card," but "is this specific piece of software a legitimate agent bound to a real user who chose to delegate to it." An agent with a stolen card number should fail here even if the number is valid.

The second question is **what may it do**. Delegation is never blanket. A human who says "book me a hotel under $400 in Lisbon next month" has not said "drain my account." The provider needs the exact boundary of the grant: the amount, the merchant or category, the time window. Anything outside that boundary should be refused no matter how well-formed the request looks.

Keep both questions in view. Identity without scope is a blank cheque; scope without identity is a boundary nobody is bound to.

## Agent identity

Answering "who is the agent" means the agent carries a verifiable identity of its own, distinct from the user's. The industry converged fast on treating an agent as a first-class principal that can be named, credentialed, and revoked independently of the human behind it. The card networks made this explicit: Visa Intelligent Commerce and Mastercard Agent Pay both issue tokenized credentials scoped to a *specific agent*, so a token minted for one agent is worthless in another's hands.

The security stakes here are not theoretical. Visa reported roughly a 450 percent jump in dark-web chatter mentioning "AI Agent" in the first half of 2026. A credential that lets software move money is a hijacking target, and identity binding is the first line of defense: even a leaked token should be inert unless it is presented by the agent it was cut for.

## Delegated authorization: consent once

The mechanism for handing an agent a bounded grant is delegated authorization, and it looks a lot like OAuth 2.x because it essentially is. The human consents once, in a context where they can actually be authenticated, and the authorization server mints a credential that encodes the grant. The agent receives that credential. It does **not** receive the user's password, and it does **not** receive the raw primary account number.

This "consent once, act many times within bounds" shape is what makes agents usable without making them dangerous. The consent event is where the human's real authority is exercised; everything afterward is the agent replaying a bounded slice of that authority. Agentic Commerce Protocol (ACP) implementations lean directly on OAuth 2.0, passing delegated or shared payment tokens rather than card data. The OAuth machinery — authorization endpoint, consent screen, token issuance — maps cleanly onto the delegation problem because it was already built to answer "this third party may do this narrow thing on my behalf."

## Scopes, limits, and expiry

The grant is only as safe as its boundaries, so three constraints travel with every token.

**Scope** restricts *what kind* of action is allowed — a particular merchant, a spending category, a single intended purchase rather than open-ended access.

**Limits** restrict *how much* — a hard spending cap, sometimes a per-transaction ceiling on top of a cumulative one.

**Expiry** restricts *how long* — the token is short-lived by design. A grant for one purchase should die in minutes, not linger for weeks waiting to be abused.

These are enforced at validation time, not merely stated at issuance. When the agent presents its token, the provider re-checks that the requested amount is under the cap, the merchant matches the scope, and the clock has not run out. A request one dollar over the cap is refused with the same finality as a forged token.

## Step-up consent for high-risk actions

Some actions are too consequential to ride on a token alone. A charge far above the norm, a new payee, a category the user never delegated — these should interrupt the automation and put the human back in the loop. That interruption is **step-up consent**: the provider forces a re-authentication of the person before the action proceeds.

Step-up is what lets the everyday grant stay narrow. Because a real human can be pulled in for the rare risky case, the default token does not need to be broad enough to cover it. The common path stays fast and low-privilege; the dangerous path pays a friction tax that a hijacker cannot easily pay, because they cannot satisfy the re-authentication.

## Never hand over raw credentials

The load-bearing principle underneath all of this: the agent never holds the raw instrument. Not the PAN, not the CVV, not the account password. What it holds is a scoped, short-lived token that stands in for those secrets and carries its own leash.

The payoff is blast-radius control. A compromised agent leaks a token that is scoped, capped, and about to expire — bad, but bounded. A compromised agent holding a raw card number leaks something that works everywhere, for any amount, until the card is cancelled. Tokenization turns a catastrophic loss into a contained one, which is exactly why every serious scheme in this space refuses to put the real instrument in the agent's memory.

## How the diagram fits together

```
User            Auth Server        Agent          Merchant/Provider
 |                   |               |                    |
 |-- consent+scope ->|               |                    |
 |                   |-- scoped tok->|                    |
 |                   |               |--- present tok --->|
 |                   |<---- validate scope + limits ------|
 |                   |----- within limits -------------->|
 |<-------------- step-up (high-risk) -------------------|
 |--------------- re-auth ok --------------------------->|
 |                   |               |<-- authorize ------|
 (consent once -> scoped token -> validated -> step-up if risky -> authorized)
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-agent-identity-auth.html)** — the delegated-authorization flow: consent once, issue a scoped token, validate scope and limits, step up for high-risk actions, then authorize.

## How AP2, ACP, and network tokens express this

The same skeleton shows up under three vocabularies. **AP2** captures the delegation as signed *mandates* — Intent, Cart, and Payment — expressed as verifiable credentials, so the grant itself is a cryptographically checkable object rather than a session assumption. **ACP** rides OAuth 2.0 and moves delegated or shared payment tokens between the parties. **Network schemes** (Visa Intelligent Commerce, Mastercard Agent Pay) issue tokenized credentials bound to a specific agent within set limits. Different nouns, one idea: a verifiable statement of who may spend, how much, where, and until when.

## Pitfalls

- **Over-broad scopes.** "Shopping access" instead of "this cart at this merchant." Broad scope means a leaked token buys the attacker room to maneuver. Scope to the narrowest intent that still lets the task complete.
- **Long-lived tokens.** A token that outlives its purpose is a standing liability. Short expiry is not a nicety; it is the difference between a minute of exposure and a month of it.
- **Credential hijacking.** Treat every delegated credential as a target. The defenses stack: bind the token to the agent, keep scope tight, keep expiry short, log every use for audit, and reserve step-up for the actions worth interrupting a human over.

## What to remember

Agentic payments are not "the same checkout with a robot typing." They are a delegation problem wearing a payment costume. Answer the two questions — which agent, and what may it do — with agent-bound identity and a scoped, short-lived, tokenized grant. Enforce the scope and the limits at validation, not just at issuance. Keep the raw instrument out of the agent entirely, and pull the human back for the rare high-risk action. Do that, and an agent can spend on someone's behalf without becoming a way to spend everything.

## Sources

- https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce
- https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol
