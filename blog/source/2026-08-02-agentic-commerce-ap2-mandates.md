# AP2: Google's Agent Payments Protocol and the Three Mandates

*How three cryptographically signed mandates turn an agent's purchase into a non-repudiable audit trail.*

When an AI agent buys something on your behalf, a hard question surfaces before the money moves: who is actually accountable for the transaction? If a shopping agent overpays, buys the wrong item, or fires a purchase you never sanctioned, the merchant, the card network, and the issuing bank all need to know what you authorized, what the agent decided on its own, and where the two diverged. Traditional payment rails were built for a human tapping a card at checkout. They have no native way to represent "a piece of software acted for this person, within these limits."

AP2, the Agent Payments Protocol, is an open protocol led by Google to close that gap. Announced in September 2025 with more than sixty launch partners and later crossing a hundred, its backers read like a map of the payments industry: Mastercard, American Express, PayPal, Adyen, Worldpay, Coinbase, plus platform players such as Salesforce, ServiceNow, Intuit, Etsy, and Lowe's. The protocol's core idea is deceptively simple. Every agent-driven purchase is decomposed into three signed artifacts called **Mandates**, and each one captures a distinct slice of accountability.

## The problem AP2 solves

The missing primitive in agentic commerce is *provable authorization*. A merchant receiving an order from an agent needs to answer three questions with cryptographic confidence, not a log line: Did the user actually want this? Did the user approve these exact items at this exact price? And is everyone in the chain aware that an agent, not a human, pushed the button? Without that, disputes become unwinnable, fraud models break, and issuers have every reason to decline agent traffic outright. AP2 answers all three by making authorization an explicit, signed, inspectable object rather than an assumption baked into a session.

## The three mandates

The heart of AP2 is a chain of three mandates, each signed and each answering one of those questions.

**Intent Mandate — what the user wants, and the rules.** The Intent Mandate captures the user's goal together with the rules of engagement: price ceilings, timing windows, and any conditions that must hold. "Buy two concert tickets, no more than $250 each, only if they are in the lower bowl." For a delegated task where the user won't be present at purchase time, this mandate is signed upfront and becomes the agent's binding authority to act.

**Cart Mandate — the exact items and price.** Once the agent assembles a concrete order, the Cart Mandate pins down the specifics: the line items, quantities, and the total the user will pay. The principle here is "what you see is what you pay for." When a human is present, the user signs the Cart Mandate to approve that precise cart before any charge occurs, so the agent cannot silently substitute a pricier item.

**Payment Mandate — the method and the charge.** The Payment Mandate names the payment instrument and the amount to be charged. Crucially, it also signals to the network and the issuing bank that an agent is involved in the transaction. That visibility lets the issuer apply agent-aware risk logic instead of treating the charge as an ordinary card-present or card-not-present event.

## Verifiable credentials and the non-repudiable chain

Each mandate is signed using **Verifiable Credentials (VCs)**, the same class of tamper-evident, cryptographically verifiable objects used in decentralized identity. Signing matters for two reasons. First, tamper-evidence: any modification to a mandate after signing invalidates it, so a merchant can trust that the cart it received is exactly the cart the user approved. Second, non-repudiation: because the signature ties the mandate to a specific key holder, no party can later credibly deny having authorized their part.

Chained together, the three mandates form a complete, verifiable narrative of the purchase: intent, then cart, then payment. If a dispute arises, this chain is the evidence. It shows what the user asked for, what the agent built, and what was ultimately charged, with each link independently verifiable. That is the difference between an application log, which a defendant can dismiss as self-serving, and a cryptographic audit trail that stands on its own.

## Human-present versus delegated flows

AP2 supports two operating modes, and the difference lives in the timing of the signatures.

In the **human-present** flow, the user is in the loop at checkout. The agent assembles the cart, presents it, and the user signs the Cart Mandate in real time. Approval and purchase are close together, so the Intent Mandate can be light.

In the **human-not-present (delegated)** flow, the user won't be around when the moment to buy arrives. Here the user signs a detailed Intent Mandate upfront, encoding the full rules: "buy the tickets the instant they go on sale, up to $X, these dates only." When the agent's conditions are satisfied, it generates the Cart Mandate automatically and proceeds. The upfront Intent Mandate is what makes the later autonomous purchase legitimate; the specificity of its rules is the user's control surface.

Here is the delegated purchase as a signed sequence:

```
User            Shopping Agent        Merchant         Payments Network
 |                    |                   |                    |
 |  sign Intent       |                   |                    |
 |  Mandate (rules,   |                   |                    |
 |  price cap) ------> |                   |                    |
 |                    | request cart ---> |                    |
 |                    | <--- cart (items, price)               |
 |  present cart      |                   |                    |
 | <----------------- |                   |                    |
 |  sign Cart         |                   |                    |
 |  Mandate --------> |                   |                    |
 |                    | submit signed cart -->                 |
 |                    | Payment Mandate (agent-present) ------> |
 |                    |                   | <-- authorize -----|
 |                    |                   |                    |
 | <------ order confirmed --------------|                    |
 |                    |                   |                    |
 [ signed chain: Intent -> Cart -> Payment = audit trail ]
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-ap2-mandates.html)** — the delegated AP2 purchase, showing the three signed mandates chaining into a non-repudiable audit trail.

## Where AP2 fits

AP2 is deliberately narrow. It handles payments, and it sits alongside the other two protocols in the emerging agent stack: **MCP** (the Model Context Protocol) gives an agent tools and context, **A2A** (Agent-to-Agent) lets agents coordinate with each other, and **AP2** governs how value actually changes hands. They compose rather than compete.

The protocol is also payment-method agnostic. It works over cards, real-time bank transfers, and stablecoins or other crypto rails via the A2A **x402** extension. That neutrality is a design goal: the mandate chain describes authorization, not settlement mechanics, so the same three-mandate model applies whether the money is a Visa charge or an on-chain transfer.

## What engineers should note

If you are building on AP2, three areas deserve early attention.

**Signing and key management.** Mandates are only as trustworthy as the keys behind them. Where user keys live, how they are provisioned, and how signing is invoked at the right moment become first-class design decisions, not afterthoughts.

**Revocation and expiry.** A delegated Intent Mandate is a standing grant of authority. You need a story for revoking it, bounding its lifetime, and ensuring an agent cannot act on a mandate whose conditions no longer hold. Treat every mandate as having a well-defined validity window.

**Audit and dispute tooling.** The mandate chain is your evidence base. Persist the signed mandates, make them retrievable per transaction, and build the tooling to reconstruct the intent-to-payment narrative on demand. A dispute resolved from cryptographic mandates is a very different conversation from one argued over application logs.

## What to remember

AP2 turns "an agent bought this for me" from a liability into a provable claim. Three signed mandates, Intent, Cart, and Payment, each answer a distinct accountability question, and chained with verifiable credentials they produce a tamper-evident audit trail. The upfront Intent Mandate is what makes autonomous, human-not-present purchases legitimate; the Cart Mandate guarantees what-you-see-is-what-you-pay-for; and the Payment Mandate keeps the network and issuer in the loop. Payment-method agnostic and complementary to MCP and A2A, AP2 is the accountability layer agentic commerce was missing.

## Sources

- https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol
- https://ap2-protocol.org/
