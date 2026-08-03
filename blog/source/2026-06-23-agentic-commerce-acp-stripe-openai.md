# ACP: The Agentic Commerce Protocol Behind ChatGPT Instant Checkout

*How Stripe and OpenAI turned "buy it for me" into an open standard — product feeds, delegated payment tokens, and OAuth consent.*

For years, the last mile of AI shopping was a copy-paste chore. An assistant could recommend a jacket, compare three pairs of running shoes, or draft a gift list, but the moment you wanted to actually buy, you were dumped back into a browser tab to re-enter your card and address. Instant Checkout in ChatGPT closes that gap: you find the product, confirm, and the purchase completes inside the conversation. The plumbing that makes this safe and portable is the **Agentic Commerce Protocol (ACP)**, an open standard co-developed by Stripe and OpenAI.

## Why ACP exists

The naive way to let an agent buy things is to hand it your card number and let it fill out checkout forms like a human. That is a security and accountability nightmare: raw credentials leak, there is no clean audit trail of what the agent was permitted to do, and every merchant would need bespoke logic for every AI surface. ACP replaces that with a structured contract between the parties, so a merchant can **build once and distribute to any ACP-compatible AI agent** instead of writing a custom integration per assistant.

It is already live in the real world: US buyers can purchase from US Etsy sellers today, and it is rolling out to more than a million Shopify merchants, with brands like Glossier, Vuori, Spanx, and SKIMS in the mix. Salesforce has also announced support. The point of an open standard is exactly this fan-out — the merchant does the work once and reaches every compliant surface.

## The four parties

ACP is easiest to reason about as a conversation between four roles.

- **The buyer.** A shopper who discovers a product on an AI surface, chooses a saved or new payment credential, and grants permission for the agent to check out on their behalf. Crucially, the buyer stays in control of consent.
- **The AI agent.** The surface — ChatGPT, for example — that shows products, presents the checkout, and collects the buyer's payment details. It orchestrates the flow but never becomes the merchant of record.
- **The business (merchant).** The seller that receives the checkout request along with a secure payment credential, runs its own cart and checkout logic, and fulfills the order.
- **The payment provider.** The party that relays the actual payment credentials as a secure token, so the raw card never travels through the agent or sits in the merchant's request payload in the clear.

Keeping these roles distinct is what makes the protocol auditable. Each party has a narrow job, and the sensitive material — the payment credential — is handled by exactly one of them.

## The product feed

Before anyone can buy, the agent has to know what exists. ACP starts with a **product feed**: a structured catalog the merchant publishes and the agent can browse. This is the merchant's inventory rendered in a machine-readable shape — items, prices, availability, variants — so the agent can answer "show me black running shoes under $120" without scraping a storefront. Because the feed is standardized, the same catalog feeds every ACP-compatible agent. Publish it once; it works everywhere.

## Agentic checkout

Once the buyer commits, the agent drives **agentic checkout** — cart management plus payment processing — against the merchant's endpoints. Conceptually the flow moves through three stages:

1. **Create the checkout / cart.** The agent sends the selected items to the merchant, which builds a checkout session, calculates totals, tax, and shipping, and returns the state to display to the buyer.
2. **Attach payment.** The agent supplies the secure payment token (more on that below) so the merchant can charge without ever touching a raw credential.
3. **Complete the order.** The merchant processes the payment, confirms the order, and returns a confirmation the agent shows in the conversation.

The important design choice: the **merchant still owns checkout**. The agent is a client of the merchant's checkout, not a replacement for it. Pricing, promotions, tax logic, and fraud rules stay where they belong.

## Delegated and shared payment tokens

The heart of ACP's security model is tokenization. Rather than passing a card number around, the buyer's chosen credential is converted into a **delegated (or shared) payment token** — a secure token that is programmatically controlled, permissioned, and logged. Three properties matter:

- **Scoped.** The token is not a blank check. It is permissioned for a specific purchase context, so its authority is bounded rather than open-ended.
- **Controlled.** It is programmatically governed, which means the rules around when and how it can be used are enforced by the system, not by trusting the agent to behave.
- **Logged.** Every use is recorded, producing the audit trail that raw-credential sharing never could.

Wrapping this is **OAuth 2.0 delegated authorization**. The buyer grants the agent permission to act on their behalf through a standard consent step, and that grant is what unlocks minting the payment token. If you have ever clicked "allow this app to access your account," the mental model is identical — except here the delegated capability is "check out this purchase," and it is deliberately narrow.

Here is the end-to-end path, from browse to confirmed order:

```
 Buyer          AI Agent         Business          Payments
   |                |                |                 |
   |  find product  |                |                 |
   |--------------->|                |                 |
   |                |  read feed     |                 |
   |                |--------------->|                 |
   |                |<-- catalog ----|                 |
   |                |                |                 |
   | OAuth consent  |                |                 |
   |--------------->|                |                 |
   |                | request token  |                 |
   |                |------------------------------->  |
   |                |<-- scoped payment token -------- |
   |                |                |                 |
   |                | create checkout + token         |
   |                |--------------->|                 |
   |                |                | charge on token |
   |                |                |---------------->|
   |                |                |<-- authorized --|
   |                |<- order confirmed                |
   |<-- show order -|                |                 |
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-acp-stripe-openai.html)** — the ACP Instant Checkout sequence: discover, delegated authorization, and tokenized settlement across the four parties.

## What a merchant actually implements

The promise that keeps this from being another integration tax is **build once, distribute to any ACP-compatible agent**. A merchant exposes its product feed and its agentic checkout endpoints in the standard shape, and it is reachable from every compliant AI surface — not one integration for ChatGPT, another for the next assistant. For sellers already on Stripe, enabling agentic payments can be as little as one line of code, because the tokenization and payment relay are handled by the provider. The merchant's job narrows to feed plus checkout; the credential handling is somebody else's specialty.

## How ACP relates to AP2

ACP is not the only agent-payments effort, and it is worth being precise about scope. Google's Agent Payments Protocol (AP2) centers on a **mandate chain** — a cryptographically verifiable record of the user's intent and authorization that travels with the transaction. ACP centers on the **checkout-plus-token flow**: the concrete mechanics of browsing a feed, creating a checkout, and settling with a scoped token. They solve adjacent problems and are best read as **complementary** rather than competing — one is about proving authorization, the other about executing the purchase.

## What to remember

- ACP is an open standard from Stripe and OpenAI that powers Instant Checkout in ChatGPT, and it is already live (US Etsy sellers, rolling out across Shopify).
- Four parties, clean separation: buyer consents, agent orchestrates, merchant owns checkout, payment provider handles the credential.
- A standardized product feed lets the agent browse; standardized checkout endpoints let it buy.
- Security lives in the token: scoped, programmatically controlled, and logged, unlocked by OAuth delegated authorization — not in trusting the agent with a raw card.
- Build once, reach every compatible agent. For Stripe merchants, that can start with a single line of code.

## Sources

- https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce
- https://docs.stripe.com/agentic-commerce/acp
