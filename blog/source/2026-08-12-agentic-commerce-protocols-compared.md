# AP2 vs ACP vs x402 vs Network Tokens: How the Approaches Compare

*A clear-eyed look at trust models, who signs what, rails, credential handling, and settlement — and why these four overlap more than they compete.*

---

## Why there are four answers, not one

When an autonomous agent needs to spend money, four families of technology now claim the job: Google's **AP2** (Agent Payments Protocol), the **ACP** (Agentic Commerce Protocol) from Stripe and OpenAI, Coinbase's **x402**, and the **network agentic tokens** coming from Visa Intelligent Commerce and Mastercard Agent Pay. It is tempting to treat this as a standards war with an eventual winner. It is not. Each was designed for a different point in the payment stack, and in practice they compose. This post compares them on the dimensions engineers actually have to reason about — trust model, who signs what, rails and settlement, credential handling, and dispute rights — then shows where they overlap and how to choose.

## Trust model and who signs what

The sharpest distinction is *what constitutes proof that a purchase was authorized*.

**AP2** builds trust from a **signed mandate chain**. The user (or their agent) produces verifiable credentials for an Intent mandate, a Cart mandate, and a Payment mandate. Each is cryptographically signed, so the chain is a non-repudiable record: you can later prove exactly what the human authorized, what the agent turned that into, and what was ultimately charged. Trust lives in the credentials, not in any single platform.

**ACP** takes a checkout-centric view. Trust flows through delegated or shared payment tokens issued under an OAuth-style authorization between the buyer's agent surface and the merchant. The merchant publishes a product feed, the agent runs an agentic checkout against it, and a scoped token authorizes the charge. The signer, in effect, is the platform that mints the delegated token on the user's behalf.

**x402** pushes signing down to the wallet. A machine hits an HTTP endpoint, receives an **HTTP 402 Payment Required** with payment terms, and responds with a signed onchain transaction. A facilitator verifies it before the resource is served. The cryptographic authority is the wallet key that signs the transfer.

**Network tokens** keep the trust anchor inside the card networks. The network issues a **scoped, tokenized credential** bound to a specific (agent, user, limits) tuple. Authorization is the same issuer approval that already governs card payments — the agent simply presents a token instead of a raw PAN.

## Rails, credential handling, and settlement

These four sit on very different rails, which drives everything downstream.

| Dimension | AP2 | ACP | x402 | Network tokens |
|---|---|---|---|---|
| Trust anchor | Signed mandate chain (VCs) | Delegated/shared token via OAuth | Wallet-signed onchain tx | Tokenized card credential |
| Rails | Rail-agnostic (cards, bank, stablecoins) | Existing card rails | Onchain stablecoins over HTTP 402 | Existing card auth/clearing |
| Credential handling | References a payment method, does not hold it | Delegated token, no raw PAN to merchant | Wallet key, no card data | Network token replaces PAN |
| Settlement & disputes | Depends on chosen rail | Card settlement, card chargebacks | Final onchain, no chargebacks | Card clearing, full dispute rights |
| Best-fit use | Portable, provable authorization across rails | Selling inside AI surfaces on card rails | API monetization, agent micropayments | Card-network reach + consumer protection |

A few things are worth drawing out. AP2 is deliberately **payment-method agnostic**: a mandate references a method (a card, a bank transfer, a stablecoin payment via its x402 extension) rather than embedding one, so settlement characteristics are inherited from whatever rail you pick. ACP and network tokens both ride the card rails you already use, which means card economics and card **chargeback** rights come along for free. x402 is the outlier on settlement: transfers are **final**, there are no chargebacks, and there are effectively **zero protocol fees** — which is exactly why it works for payments too small for card interchange to make sense.

## Chargebacks and disputes

Dispute rights track the rails. If you route through ACP or network tokens, you inherit the card networks' well-understood chargeback machinery and consumer-protection regime — valuable for consumer-facing purchases where buyers expect recourse. x402 gives you the opposite trade: finality with no reversal, which removes chargeback risk and fraud-driven reversals for the seller but offers the buyer no built-in clawback. AP2 doesn't define disputes itself; it inherits them from the settlement rail the mandate points at, while its signed chain gives *both* sides a stronger evidentiary record than a typical card dispute has.

## A decision view

The cleanest way to hold all this in your head is to start from the purchase's *need* and route from there. One requirement — an agent that must pay, carrying intent and spending limits — flows into a classifier that asks a small set of questions, and each answer points at the approach that fits.

```
                                 ┌──► [AP2]           ──► any rail (cards / bank /
                    portable proof?│    signed mandates      stablecoins via x402)
                                 │
 Purchase need ──► Requirement ──┼──► [ACP]           ──► card rails
 (intent+limits)     router      │    agentic checkout     (chargebacks)
                    "route by     │
                     need"        ├──► [Network tokens]──► card rails
                     card reach? ──┘    scoped credential   (dispute rights)
                                 │
                    micro pay?   └──► [x402]           ──► onchain stablecoins
                                      HTTP 402              (final, no chargeback)
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-protocols-compared.html)** — a data-flow view routing one purchase requirement to AP2, ACP, x402, or network tokens by need, and on to card or onchain settlement.

## How they overlap and interoperate

The routing picture makes the overlap obvious: multiple approaches feed the *same* settlement rails. This is the part the "standards war" framing misses.

- **AP2 can settle via x402.** The mandate chain provides portable, provable authorization; x402 provides an onchain method for that mandate to settle against. They are layers, not rivals — proof of authorization on top, settlement underneath.
- **Network tokens are a credential AP2 or ACP can reference.** A mandate or an agentic checkout still needs *something* to charge. A scoped network token is a natural payment method for either to point at, contributing card reach and dispute rights.
- **ACP rides card rails** — the same rails network tokens tokenize — so an ACP checkout and a network token are complementary, one handling the merchant-side checkout experience and the other the credential.

In other words, you can find a coherent stack that uses three of the four at once: an AP2 mandate authorizing an ACP checkout that charges a network token, or an AP2 mandate settling onchain through x402. Overlap, not a single winner.

## Which should you reach for?

- **You need portable, provable authorization across many rails and partners.** Reach for **AP2**. Its 100+ partner base and rail-agnostic mandate chain shine when the *audit trail* and cross-rail portability matter more than any one payment method.
- **You're a merchant who wants to sell inside AI surfaces.** Reach for **ACP**. "Build once, distribute to any ACP agent" is the pitch: it powers ChatGPT Instant Checkout and lets you keep the card rails and processor you already run.
- **You're monetizing an API or need tiny agent-to-agent and machine payments.** Reach for **x402**. Card interchange makes sub-dollar payments uneconomic; onchain stablecoin settlement with zero protocol fees does not. Its volume — well over a hundred million transactions and hundreds of millions of dollars annualized — shows the model is past the toy stage.
- **You want card-network reach, existing acceptance, and consumer protections.** Reach for **network tokens**. Visa Intelligent Commerce and Mastercard Agent Pay let agents transact on the rails merchants already accept, with familiar dispute rights.

Most real systems will combine these rather than pick one, because the questions ("card reach? onchain micropayment? portable proof? sell in an AI surface?") are not mutually exclusive.

## What to remember

AP2, ACP, x402, and network tokens answer different questions. AP2 is about **provable authorization** you can carry across rails; ACP is about **selling inside AI surfaces** on card rails; x402 is about **onchain machine micropayments** with final settlement; network tokens are about **card-network reach and consumer protection** via scoped credentials. They interoperate by design — mandates reference credentials, checkouts ride rails, and settlement can happen on cards or onchain. Design your agent commerce stack around the *need* of each purchase, not around a bet on a single winner, and you can adopt more than one without contradiction.

## Sources

- https://ap2-protocol.org/
- https://docs.stripe.com/agentic-commerce/acp
- https://www.coinbase.com/developer-platform/discover/launches/x402
