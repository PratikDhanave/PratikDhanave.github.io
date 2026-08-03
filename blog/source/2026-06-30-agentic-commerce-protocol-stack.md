# MCP, A2A, AP2, and ACP: The Agentic Commerce Protocol Stack
*Four protocols, four jobs: how tools, agent-to-agent messaging, and payment rails compose into one buying flow.*

When an agent buys something on your behalf, no single protocol does the whole job. The agent needs tools and context to reason about the purchase, a way to coordinate with other agents, and a rail to actually move money. Each of those concerns is a different specification, from a different vendor, solving a different problem. Confusing them is the fastest way to build the wrong thing.

The useful mental model is a layered stack. MCP gives an agent tools and context. A2A lets agents talk to each other. AP2, ACP, and x402 are the payment rails those agents invoke when money has to change hands. They interoperate and overlap far more than they compete, so the interesting engineering question is not "which one wins" but "which layer does this belong on."

## Why a stack, not a winner

Separation of concerns is why this reads as a stack rather than a bake-off. Tool access, inter-agent communication, and settlement have genuinely different trust models, failure modes, and owners. Tool calls are frequent and cheap to retry. Agent-to-agent messages cross organizational boundaries and need discovery. Payments are rare, irreversible, and demand cryptographic proof of authorization. Cramming all three into one protocol would force the weakest security assumption onto the most sensitive operation.

Keeping them distinct also lets each layer evolve independently. You can swap payment rails without retraining the agent's tool use, or add a new peer agent without touching how money settles.

```
        CAPABILITY LAYER
  +---------------------------+        +----------------------+
  | MCP: tools / context      |        | A2A: agent <-> agent |
  | (functions, resources)    |        | (discover, message)  |
  +------------+--------------+         +-----------+----------+
               |    both feed the same runtime      |
               +------------------+-----------------+
                                  v
                        +-------------------+
                        |   Agent Runtime   |
                        | (MCP + A2A client)|
                        +---------+---------+
                                  | invoke a rail only when money moves
        PAYMENT LAYER             v
  +-------------+   +---------------------+   +----------------+
  | AP2         |   | ACP                 |   | x402           |
  | mandates    |   | checkout + tokens   |   | onchain 402    |
  +------+------+   +----------+----------+   +--------+-------+
         |                     |                       |
         +----------+----------+                       |
                    v                                  v
              +-----------+                     +-------------+
              | Merchant  |------ settle ------>| Payment Rails|
              | + PSP     |                     | card/bank/chn|
              +-----------+                     +-------------+
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-protocol-stack.html)** — the layered protocol stack with the primary buy path traced from shopper to settlement.

## MCP: tools and context

The Model Context Protocol is the layer closest to the model. It connects an agent to tools, data, and context: function or tool calling, plus structured resources the model can read. When your agent needs to look up a product catalog, check inventory, or call an internal pricing service, that access is expressed as MCP tools and resources.

MCP knows nothing about payments or other agents. It is a client-to-tool contract. That narrowness is the point: it standardizes how a single agent reaches the outside world so any model runtime can consume any compliant tool server. In a purchase flow, MCP is how the agent gathers the facts it needs before any money is on the table.

## A2A: agent to agent

Agent2Agent is an open protocol for agents to discover and talk to each other. Where MCP is one agent reaching for tools, A2A is two or more agents collaborating: a shopping agent negotiating with a merchant's agent, or a planner delegating a subtask to a specialist. It defines how agents advertise their capabilities, find one another, and exchange messages.

This matters for commerce because a real transaction often spans parties. Your agent and the seller's agent may each represent different organizations with different tools and policies. A2A gives them a shared language to coordinate without either side exposing its internal MCP tools directly. It carries intent and negotiation, but on its own it still does not move money.

## The payment layer

When the conversation resolves into "buy this for this price," the agent drops down to a payment protocol. Three occupy this layer, each with a distinct shape.

**AP2 (Agent Payments Protocol, Google)** represents a purchase as a chain of signed mandates. The shopper authorizes an Intent, the agent assembles a Cart, and a Payment mandate captures the final authorization, each backed by verifiable credentials. The result is a cryptographic audit trail answering "who authorized exactly what." AP2 is payment-method agnostic: it handles cards, bank transfers, and stablecoins, and it is designed to ride as an extension of A2A and MCP rather than as a separate island.

**ACP (Agentic Commerce Protocol, Stripe and OpenAI)** is an agent-to-merchant standard covering the full checkout: a product feed the agent reads, an agentic checkout flow, delegated payment tokens, and OAuth for authorization. It is the machinery behind ChatGPT Instant Checkout. Where AP2 emphasizes a portable mandate chain, ACP emphasizes a concrete merchant integration: give the agent a feed and a checkout endpoint, hand it a scoped delegated token, and let it complete the order.

**x402 (Coinbase)** is the onchain option. It revives the dormant HTTP 402 Payment Required status so a server can demand payment inline, and settles in stablecoins over HTTP. For machine-to-machine microtransactions, an API charging per call, an agent paying another agent, this is settlement without a card network in the loop. An A2A x402 extension lets agents negotiate and pay onchain within an A2A exchange.

## How a purchase touches every layer

Trace one buy. The shopper prompts the agent. The agent uses **MCP** tools to fetch the catalog and confirm the item and price. If a second party is involved, it coordinates over **A2A** with the merchant's agent. Once terms are set, it moves to the payment layer: it might construct an **AP2** mandate chain to capture signed authorization, complete the order through an **ACP** checkout with a delegated token, or settle onchain with **x402**, sometimes composing more than one. The merchant and the underlying rails, card networks, bank transfer, or a chain, finalize settlement.

Every layer did exactly one job. Nothing about tool access leaked into settlement, and nothing about settlement constrained how the agent gathered context.

## Interoperation and overlap

These specs were not designed in isolation, and the seams between them are deliberate. AP2 is explicitly positioned as an extension of A2A and MCP, so the mandate chain travels inside the same channels the agent already uses. The A2A x402 extension folds onchain settlement into agent-to-agent negotiation. Network-issued agentic tokens sit alongside these as another authorization primitive the rails accept.

Because of this overlap, the boundaries blur in practice. AP2 and ACP can both close a card purchase; AP2 and x402 can both reach stablecoins; ACP and A2A both involve a merchant. Treat them as composable primitives, not mutually exclusive choices.

## What to build on which layer

- Need your agent to reach a tool, service, or dataset? That is **MCP**. Do not invent a bespoke tool channel.
- Need two agents from different parties to discover and coordinate? That is **A2A**.
- Need a portable, auditable authorization chain across payment methods? Reach for **AP2** mandates.
- Integrating agentic checkout with a specific merchant and payment stack? **ACP** with delegated tokens and OAuth.
- Settling machine-to-machine value onchain, especially small or metered charges? **x402**.

## What to remember

MCP is tools and context. A2A is agent-to-agent. AP2, ACP, and x402, plus network agentic tokens, are the rails those agents call when money must move. Design each part on its own layer, lean on the published extensions where they interoperate, and resist the urge to make any one protocol do a neighbor's job. The stack is the architecture.

## Sources

- https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol
- https://ap2-protocol.org/
