# The Agentic Checkout Flow, End to End
*How an AI agent turns a shopper's intent into a settled purchase, and where ACP and AP2 plug into the same eight-stage skeleton.*

When an agent buys something on your behalf, the purchase does not skip any of the steps a human checkout would take. It just moves them behind a program. The interesting engineering question is not "can an agent click Buy" but "what contract does each step expose so the agent can act, the merchant can trust it, and the payment network can settle it." Two protocols dominate the conversation right now: the Agentic Commerce Protocol (ACP) from Stripe and OpenAI, which powers Instant Checkout inside ChatGPT, and Google's Agent Payments Protocol (AP2), built around a chain of signed mandates. They look different on the wire, but they ride the same skeleton. Learn the skeleton once and both protocols become variations on a theme.

## The shared skeleton

Every agent-driven purchase moves through eight stages:

1. **Discovery** on an AI surface, backed by a product feed or catalog.
2. **Cart assembly**, where the agent selects items and resolves price and availability.
3. **User approval**, where the human authorizes the purchase. AP2 has the user sign a Cart Mandate; ACP has the user grant scoped checkout permission.
4. **Delegated payment token**, a scoped credential handed to the agent instead of a raw card. This is an ACP shared payment token, an AP2 Payment Mandate, or a network-issued agentic token.
5. **Merchant checkout endpoint** receives the order plus the token.
6. **Authorization** through the payment provider or card network.
7. **Fulfillment**, where the merchant captures funds and ships or provisions.
8. **Async status** delivered through webhooks and receipts.

The rest of this post walks each stage as an engineer building or integrating against it.

```
   DISCOVERY --> CART --> APPROVE --> PAYMENT --> CHECKOUT --> AUTHORIZE --> FULFILL --> WEBHOOK
   (feed)       (agent)  (mandate/   TOKEN       (merchant    (network)    (capture)   + RECEIPT
                          permission) (scoped)    endpoint)        |                    (async audit)
                                                                   |
                                                                   +--> DECLINED --> retry
                                                                        (reason code)  (same idempotency key)
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-checkout-flow.html)** — the eight-stage agentic checkout workflow with its approval, delegated-token, and decline-and-retry paths.

## Discovery and the product feed

Discovery is the one stage most teams already have infrastructure for: a structured product feed. The agent needs machine-readable inventory with stable identifiers, current price, availability, and enough attributes to match intent to SKU. ACP formalizes this as a product feed the AI surface ingests, so that when a user asks for "a waterproof jacket under 150," the agent is reasoning over your catalog rather than scraping a page. Treat the feed as an API contract, not a marketing artifact: freshness matters, because an agent that assembles a cart from stale prices will fail at authorization and erode trust. Version your feed schema and keep identifiers durable across updates.

## Cart assembly and approval

Once items are chosen, the agent assembles a cart and locks in the amounts it intends to charge. This is the boundary where autonomy stops and consent begins, and it is the stage where the two protocols diverge most visibly.

Under **AP2**, approval is cryptographic. The user signs a Cart Mandate: a verifiable credential that says "I authorize this exact cart, at this exact total, under these constraints." It sits in a chain that runs from an Intent Mandate (what the user wants) through the Cart Mandate (the specific basket) to a Payment Mandate (how it may be paid). Because each link is signed, the whole chain is non-repudiable and independently verifiable later.

Under **ACP**, approval is a granted permission scoped to a checkout, established through an OAuth-style flow. The user consents on the AI surface, and the agent receives authority to complete that specific purchase rather than a standing license to spend.

Either way, the engineering invariant is the same: no charge happens without an explicit, recorded act of approval, and that record must survive the transaction so you can answer "who authorized this and to what limit" months later.

## The delegated payment token

This is the stage that makes agentic payments tolerable from a risk standpoint. The agent never touches a raw card number. Instead it receives a scoped, delegated credential:

- **ACP** issues a shared payment token the agent presents to the merchant, which the merchant hands to the payment processor.
- **AP2** carries a Payment Mandate that binds the payment method to the approved cart.
- **Card networks** are rolling out their own agentic tokens that carry an agent-present signal into authorization.

The common property is scoping. A good delegated token is narrow in amount, merchant, and time. If it leaks, the blast radius is one purchase, not a wallet. Design your integration so the token is single-purpose and short-lived, and so that the thing you store for reconciliation is a token reference, never the credential itself.

## The merchant checkout endpoint

Now the request reaches your checkout endpoint carrying the cart, the approval reference, and the delegated token. ACP models this as an agentic checkout with an explicit lifecycle: create the checkout, pay it, then complete it. Keeping those as distinct transitions matters, because an agent can crash or time out between any two of them and needs to resume without duplicating work.

Two things belong on this endpoint from day one. First, an **idempotency key** on every mutating call, because agents retry aggressively and network timeouts are ambiguous. Second, **strict validation** that the presented token and cart still match what was approved. If the agent tries to complete a checkout whose total drifted from the signed mandate, reject it rather than reconcile it silently.

## Authorization and decline handling

The checkout endpoint forwards the payment to the provider or network for authorization. This is a synchronous decision with three broad outcomes: approved, declined, or needs-more (step-up, additional verification). The failure path deserves as much design attention as the happy path, because an agent cannot read a modal or improvise around a vague error.

Return structured, actionable decline information. "Payment failed" is useless to an agent; a reason code that distinguishes insufficient funds from an expired token from a risk hold lets the agent decide whether to retry, ask the user to re-approve, or abandon. Keep authorization conceptually separate from capture and fulfillment: authorizing confirms the money can move, and only after your business rules pass do you capture and fulfill.

## Fulfillment, receipts, and webhooks

After authorization, the merchant captures funds and fulfills. Fulfillment is rarely instantaneous, so the truth about an order arrives asynchronously. Emit **webhooks** for every state change (paid, shipped, refunded, disputed) and issue a **receipt** the agent can relay back to the user. The receipt plus the mandate or token chain forms the complete audit record for the transaction: what was wanted, what was approved, how it was paid, and what was delivered.

Because the agent may not be listening at the moment a webhook fires, make status independently queryable. An agent that reconnects tomorrow should be able to ask "what happened to checkout X" and get the same answer the webhook carried.

## Idempotency and retries

The single most consequential difference between human and agent checkout is retry behavior. Humans give up or refresh; agents retry programmatically, often within milliseconds, and often after a request that actually succeeded but whose response was lost. Without idempotency this produces double charges.

Every state-changing operation in the flow (create checkout, pay, capture) must accept an idempotency key and return the original result on replay rather than performing the action again. Scope the key to the operation and the cart so a legitimate second purchase of the same item is not mistaken for a retry. Pair this with webhooks and a queryable status endpoint, and the agent has everything it needs to recover from partial failure without human intervention.

## What to remember

ACP and AP2 are not competing skeletons; they are competing implementations of the same one. ACP leans on OAuth-style permission and a shared payment token with a create-pay-complete lifecycle. AP2 leans on a signed Intent to Cart to Payment mandate chain. Both give the agent a discovery feed, a scoped credential, a merchant checkout, a network authorization, and asynchronous settlement. If you build the skeleton with idempotency keys, structured declines, webhooks, and a durable audit trail from the mandate or token chain, adopting either protocol becomes a matter of adapters, not architecture.

## Sources

- https://docs.stripe.com/agentic-commerce/acp
- https://ap2-protocol.org/
