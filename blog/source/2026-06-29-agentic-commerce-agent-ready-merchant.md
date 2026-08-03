# Building an Agent-Ready Merchant

*The surface a store must expose when the buyer is an AI agent, not a browser — and why it is the fintech reliability playbook wearing a new hat.*

For twenty years the checkout flow assumed a human on the other side of the glass: a person who reads a product page, types a card number, clicks "Pay", and waits for a spinner. That assumption is dissolving. The buyer is increasingly an autonomous agent shopping on someone's behalf — comparing SKUs, filling a cart, and settling payment through a delegated token. If your store cannot be read, transacted against, and reconciled by software, the agent routes around you to a merchant that can.

"Agent-ready" is not a rebrand of "has an API". It is a specific contract: a machine-readable catalog, checkout endpoints an agent can call without a screen, payment that never touches a raw card number, and the reliability primitives — idempotency, webhooks, audit — that keep automated traffic from corrupting your order book. The good news for anyone who has read the fintech handbook: you already own most of these patterns.

## What "agent-ready" actually means

Break it into six exposed capabilities. A store is agent-ready when it publishes:

1. A **product feed** that is structured, current, and priced — not an HTML page an agent has to scrape.
2. **Agentic checkout endpoints** — create a checkout, apply payment, complete the order — callable headlessly.
3. **Delegated payment token acceptance** — the agent presents a scoped token, never a PAN you have to store.
4. **Idempotency** on every mutating call, because agents retry far more aggressively than humans.
5. **Webhooks** for asynchronous order status, so the agent learns of state changes without polling.
6. **Observability and audit** for agent traffic, so you can attribute, rate-limit, and dispute automated orders.

Emerging standards package this so you build it once. The Agentic Commerce Protocol (ACP) frames the goal as "build once, distribute to any ACP-compatible AI agent" — a Stripe merchant can enable agentic payments with as little as one line of code. Google's AP2 leans on signed **Payment Mandates** so the buyer's authorization travels with the request as verifiable intent. Different wire formats, same shape.

## The product feed: structured, fresh, priced

The feed is the front door. An agent cannot buy what it cannot parse. That means a structured document — JSON or a well-formed feed format — with a stable product identifier, title, description, price with currency, availability, and variant attributes. Two properties matter more than completeness:

- **Freshness.** A price or stock field that lags reality turns into a failed checkout or a chargeback. Serve the feed from the same source of truth your checkout reads, or reconcile them on a tight cadence. A stale feed is worse than no feed — it invites the agent to commit to a purchase you cannot honor.
- **Machine-first shape.** Availability should be an enum the agent can branch on, not the words "only a few left" in marketing copy. Prices are integers in minor units with an explicit currency, not `"$19.99"`.

Treat the feed as a read API with a cache contract: an `ETag` so agents fetch deltas cheaply, and a documented refresh interval so they know how much to trust a cached copy.

## Agentic checkout endpoints

Checkout for an agent is a small state machine exposed over three calls:

- **Create checkout** — the agent sends line items and quantities; you return a checkout object with a computed total, tax, shipping options, and a server-generated `checkout_id`.
- **Apply payment** — the agent attaches a delegated token (below) to the checkout.
- **Complete order** — you capture, transition the checkout to `confirmed`, and return an order reference.

Keep the transitions one-directional, and have every response echo the current state and total so the agent never infers what happened from an HTTP code alone. Reject ambiguous transitions loudly — a `complete` on an unpaid checkout is a `409`, not a silent no-op.

## Accepting delegated tokens, never a raw PAN

This is the line that separates agentic commerce from screen-scraping a card form. The agent does not hand you a card number. It presents a **delegated, scoped payment credential**: an ACP shared payment token, an AP2 Payment Mandate, or a network-issued agentic token. The credential is scoped — to an amount, a merchant, a window — and carries the buyer's authorization as a signed artifact.

Your job shrinks to verification and capture. You confirm the token is valid, that its scope covers this order's amount and currency, and that it has not expired, then pass it to your payment provider exactly as you would a normal payment method. You never see, store, or log the underlying account number, which keeps the agentic path outside the worst of your PCI scope. If a token's scope does not cover the total, fail closed — declining is safer than capturing against an authorization you cannot prove.

## Idempotency, because agents retry

A human who sees a spinner waits. An agent that sees a timeout retries — often immediately, often several times, sometimes from a fresh worker that has no memory of the first attempt. Without protection, three retries of "complete order" become three charges and three shipments.

The fix is the same idempotency key pattern the fintech handbook prescribes for any payment mutation. The agent generates a unique key per logical operation and sends it as a header. You persist the key with the first request's outcome; a replay with the same key returns the stored result instead of re-executing. Scope keys to the operation and checkout, give them a sane TTL, and store enough of the original response to replay it faithfully. This single mechanism absorbs the retry behavior that would otherwise make agent traffic unsafe.

```
                          AGENT-READY MERCHANT
                          ====================

   ┌─────────┐                 MERCHANT EDGE
   │   AI    │        ┌────────────────────────────────┐
   │  AGENT  │──(1)──▶│  Product Feed API   (read)     │
   │ (buyer) │        │  Checkout API       (mutate)   │
   └────┬────┘        │  Token Acceptance   (verify)   │
        │             └───────┬──────────────┬─────────┘
        │                     │              │
        │  (2) delegated      │ (3) persist  │ (4) capture
        │      token          ▼              ▼
        │             ┌──────────────┐  ┌──────────────┐
        │             │  Order Store │  │   Payment    │
        │             │ + idempotency│  │   Provider   │
        │             └──────┬───────┘  └──────┬───────┘
        │                    │                 │
        │◀───(6) webhook ────┤◀──(5) settled ──┘
        │    order.status    │
        │                    ▼
        │             ┌──────────────┐
        └─ audit ────▶│ Observability│
           trace      │  + rate limit│
                      └──────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-agent-ready-merchant.html)** — the agent-ready merchant surface: catalog read, headless checkout, delegated-token verification, capture, and signed webhook status flowing back to the agent.

## Webhooks and asynchronous status

Capture is rarely instantaneous, and fulfillment never is. The agent needs to know when a payment settles, when an order ships, when a refund clears — without hammering your API in a polling loop. Webhooks carry those transitions: `order.confirmed`, `payment.settled`, `order.shipped`, `refund.completed`.

The webhook contract is the handbook's contract, unchanged. Sign every payload so the receiver can verify origin. Make delivery at-least-once and tell consumers so — the agent must then dedupe on your event ID, the mirror image of the idempotency you enforce inbound. Emit events from an **outbox** written in the same transaction as the state change, so a crash between "commit order" and "send webhook" cannot drop the notification. Retry with backoff and expose a replay endpoint for gaps.

## Observability, audit, and rate limits

Agent traffic is different traffic, and you must be able to see it as such. Tag requests with the calling agent's identity so you can attribute orders, reconstruct a disputed purchase, and separate agent conversion from human conversion. An audit trail that ties a completed order back to a specific token and mandate is what lets you win a chargeback when the buyer's own agent placed the order.

Rate limits are non-negotiable. Agents fan out faster than any human, and a misbehaving one can exhaust inventory or hammer checkout creation. Apply per-agent quotas and return `429` with a `Retry-After` an agent will respect — generous enough for legitimate bursty shopping, tight enough to contain a runaway loop.

## You have already built most of this

Step back and the agentic surface is not new engineering — it is your existing reliability toolkit pointed at a new client:

- **Idempotency and resumability** — the retry-safety you built for human double-clicks now absorbs agent retries.
- **APIs and webhooks** — the async notification contract you built for order status now serves agent buyers.
- **Outbox and reconciliation** — the guarantees that keep your ledger and your events in step now keep an agent's view of an order consistent with yours.

The delegated-token layer is the genuinely new piece, and even that slots in as just another payment method behind your existing capture flow. Everything else is the fintech handbook applied to a client that never sleeps, never reads a screen, and always retries.

## What to remember

- Agent-ready means six exposed capabilities: a structured feed, headless checkout endpoints, delegated-token acceptance, idempotency, webhooks, and observability.
- Serve a machine-first feed from your real source of truth; a stale feed is worse than none.
- Accept scoped, signed tokens and fail closed when scope does not cover the order — never store a raw PAN.
- Idempotency keys are what make aggressive agent retries safe; webhooks plus an outbox are what make async status reliable.
- Almost none of this is new: it is idempotency, webhooks, and reconciliation — the reliability primitives you already own — applied to a software buyer.

## Sources

- https://docs.stripe.com/agentic-commerce/acp
- https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce
