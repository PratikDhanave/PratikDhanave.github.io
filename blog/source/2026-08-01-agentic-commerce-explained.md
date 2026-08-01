# Agentic Commerce, Explained

*How AI agents that discover, choose, and pay on your behalf break the assumptions baked into every checkout, and the protocol stack rushing in to fix them.*

For thirty years, online checkout has quietly assumed one thing: a human is sitting at a browser. They see the price, they click "buy," they type a card number, they solve the occasional puzzle to prove they are not a robot. Every fraud model, every consent flow, every "are you sure?" modal is tuned for that human in the loop.

Agentic commerce removes the human from that exact moment. An AI agent discovers products, compares them, decides, and completes the purchase, often inside a chat window, without the user ever visiting the merchant's site. That is genuinely useful. It is also a quiet demolition of the assumption the whole payment system was built on. This post walks through what agentic commerce is, the trust problem it creates, and the stack of protocols emerging to solve it.

## From human checkout to agent-led purchase

A normal purchase is a sequence a merchant can reason about: a browser loads a page, a session cookie ties requests together, a card is entered, a 3-D Secure challenge confirms the human, and money moves. The merchant's risk engine watches device fingerprints, typing cadence, and IP reputation to decide whether the buyer is real.

Now replace the buyer with an agent. You tell an assistant, "find me running shoes under 120 dollars in my size and buy the best-reviewed pair." The agent searches catalogs, narrows options, picks one, and pays. There is no page view in the usual sense, no human keystrokes, no puzzle to solve. From the merchant's side, a very capable automated client just tried to check out, which historically looked exactly like fraud.

The task did not get easier. The trust that used to be established implicitly, by a human physically doing the clicking, now has to be established explicitly, in data.

## The trust problem

Strip away the hype and agentic commerce comes down to three questions a merchant and a payment provider must answer before releasing goods or money.

**Authorization: is this really the user's agent?** Anyone can spin up an agent and point it at a store. The merchant needs cryptographic proof that this agent acts for a specific, real account holder, not an attacker impersonating one. A stolen API key or a spoofed identity here is a stolen wallet.

**Intent: what exactly did the user authorize?** "Buy shoes under 120 dollars" is not the same as "buy anything, any amount, forever." The system needs a verifiable, scoped mandate: what may be bought, up to what price, from which merchants, within what time window. Without it, a confused or manipulated agent could drain an account one legitimate-looking purchase at a time.

**Accountability: what happens when it goes wrong?** The agent buys the wrong item, or buys twice, or is tricked by a malicious product listing. Who is liable? Was the mandate exceeded, or honored? You cannot answer that after the fact unless the authorization and intent were captured as tamper-evident evidence at the moment of purchase.

Every serious protocol in this space is, underneath, an answer to those three questions. The good ones make the mandate cryptographically verifiable, so a merchant can check it without trusting the agent's word for anything.

## The emerging stack

No single protocol does all of this. What is forming instead is a layered stack, where agent capability sits on top and payment settlement sits at the bottom.

**MCP (Model Context Protocol)** gives an agent its tools and context. It is how an agent learns that a "search catalog" or "create cart" tool exists and how to call it. MCP is the agent's hands, not its wallet.

**A2A (Agent2Agent)** lets agents talk to other agents. A shopping agent might negotiate with a merchant's own agent, delegating sub-tasks across organizational boundaries with a shared message format.

Below those sits the part that actually moves money, and this is where the ecosystem is busiest:

- **AP2 (Agent Payments Protocol)**, from Google, centers on signed "mandates" that encode user intent and authorization so any payment method can be attached underneath. It launched with 60-plus partners and has since grown past 100.
- **ACP (Agentic Commerce Protocol)**, from Stripe and OpenAI, is the open standard powering ChatGPT's Instant Checkout, live today with Etsy and Shopify merchants. It defines how an agent submits an order and how the merchant confirms it.
- **x402**, from Coinbase, revives the long-dormant HTTP 402 "Payment Required" status code so an agent can pay per request with stablecoins directly over HTTP, no account or card on file.
- **Card-network approaches** bring the incumbents in: Visa Intelligent Commerce and Mastercard Agent Pay issue agent-specific credentials and network tokens, keeping the existing rails but scoping them to a verified agent.

These are not purely competing. AP2's mandate can wrap a card token; ACP can settle through a network; x402 covers cases where crypto-native, machine-speed micropayments make sense. Expect a merchant to speak several of these before the dust settles.

```
   +-----------------------------------------------+
   |                    User                       |
   |         states intent + a scoped budget       |
   +-----------------------------------------------+
                        |  delegates
                        v
   +-----------------------------------------------+
   |                   Agent                        |
   |     tools + context: MCP        agent-to-agent: A2A
   +-----------------------------------------------+
                        |  presents signed mandate
                        v
   +-----------------------------------------------+
   |                Payment Layer                   |
   |   AP2  |  ACP  |  x402  |  network tokens      |
   |   (authorization + intent, verifiable)         |
   +-----------------------------------------------+
             |                         |
             v                         v
   +------------------+      +-----------------------+
   |     Merchant     |<---->|   Payment Provider    |
   |  goods / catalog |      |  settle + capture     |
   +------------------+      +-----------------------+
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-explained.html)** — the agentic commerce stack, from a user's delegated intent down through the agent and payment layer to the merchant and payment provider.

## What changes for engineers

If you build checkout, catalogs, or payment infrastructure, four concerns move from nice-to-have to load-bearing.

**Identity becomes machine-first.** You need to authenticate a non-human caller and bind it to a human principal. That means agent credentials, attestation, and a way to tell "the user's authorized agent" from "some bot." Treat the agent as a first-class identity, not an anonymous client.

**Delegation must be explicit and scoped.** Capture the mandate as data your systems can enforce: amount caps, merchant allow-lists, item constraints, expiry. Verify the signature on every request rather than trusting a session. A mandate is a bearer of authority; check it like one.

**Idempotency stops being optional.** Agents retry. They run concurrently. They misread a timeout as a failure and try again. Without idempotency keys on every purchase operation, "buy once" quietly becomes "buy three times." This is the single most common way an agentic integration loses real money.

**Audit has to be tamper-evident.** When a dispute lands, "our logs say so" is not enough. Persist the signed mandate, the agent identity, and the decision trail so you can prove what was authorized and that you honored it. The evidence has to survive the argument.

## What to remember

Agentic commerce is not a new payment method bolted onto the old flow. It removes the human from the moment of purchase, which dissolves the implicit trust checkout was built around, and forces that trust to be re-established explicitly, in verifiable data. The protocol stack, MCP and A2A for capability, AP2, ACP, x402, and network tokens for payment, is the industry's coordinated attempt to answer three questions at machine speed: is this the user's agent, what did the user authorize, and can we prove it later. Build for those three, and idempotency and scoped mandates stop being edge cases and start being your foundation.

## Sources

- [Announcing Agents to Payments (AP2) protocol](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol)
- [Developing an open standard for agentic commerce](https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce)
- [x402: a new standard for internet-native payments](https://www.coinbase.com/developer-platform/discover/launches/x402)
