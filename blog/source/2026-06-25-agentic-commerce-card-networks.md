# Card Networks Enter Agentic Commerce: Visa Intelligent Commerce and Mastercard Agent Pay

*How Visa and Mastercard are reshaping tokenization so an AI agent can pay on your behalf — with scoped credentials, agent-aware identity, and the network doing what it has always done: authenticate, authorize, tokenize.*

When an AI agent books a flight or restocks your pantry, someone has to move the money. For years the assumption in agent demos was crude: hand the agent a card number and hope for the best. That is exactly the wrong answer, and the two companies that run the world's largest payment rails have said so out loud. In the first half of 2026, Visa launched Intelligent Commerce and Mastercard expanded Agent Pay — two frameworks that answer the same engineering question from the same starting position: never let an autonomous agent hold a raw primary account number (PAN).

## Why the networks care

The obvious reading is defensive. If agents transact by scraping stored card numbers or replaying credentials, the networks lose visibility into who authorized what, and fraud teams lose the signals they rely on. There is a sharper reason too: Visa reported roughly 450% more dark-web chatter about "AI Agent" tooling in H1 2026, much of it aimed at hijacking agent credentials. An agent that carries a real PAN is a portable, reusable secret walking through untrusted software.

But there is an upside motive as well. Agent-initiated commerce is a new transaction category, and the networks want it to ride existing rails rather than route around them through closed wallets or bank-to-bank transfers. If an agent purchase looks like a tokenized card transaction, it inherits decades of infrastructure: authorization, clearing, dispute rights, and fraud scoring. Keeping agents on the network is both a safety story and a business one.

## The core idea: scoped agentic tokens, not raw PANs

The shared design move is deceptively simple. Instead of exposing the cardholder's PAN, the network issues a **scoped, tokenized credential** bound to a specific triple: *this agent, this user, these limits.* The agent never sees the underlying account; it holds a token that only means anything within its declared scope.

That binding is the whole trick. A scoped agentic token is not just a random surrogate for a card number — it carries a cryptographic proof of *delegated authorization*. When the token is presented, the network can verify that the consumer really did authorize this particular agent, and that the requested purchase falls inside the constraints the consumer set (merchant categories, per-transaction ceilings, total spend, time windows). Revocation is a token operation, not a card reissue.

```
  ┌──────────┐  authorize agent   ┌────────────────────┐
  │ Consumer │ ─────────────────► │ Network Token Svc  │
  └──────────┘                    │ mints scoped token │
                                  │  (agent + limits)  │
                                  └─────────┬──────────┘
                          scoped agentic token │
                                              ▼
                                        ┌──────────┐
                                        │ AI Agent │
                                        └────┬─────┘
                        agent-initiated purchase │
                                              ▼
                                      ┌────────────┐
                                      │  Merchant  │
                                      └─────┬──────┘
                                  present token │
                                              ▼
   ┌────────────────────────────────────────────────────┐
   │   Payment Network: authorize · tokenize · monitor   │
   └───────────────────────┬────────────────────────────┘
                authorize + clear │
                                  ▼
                            ┌───────────┐
                            │ Issuer    │
                            │ (bank)    │
                            └───────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-card-networks.html)** — Consumer delegates to one agent; the network mints a scoped token and later authorizes, monitors, and clears it on existing rails.

## Visa Intelligent Commerce

Visa's framing centers on what it calls **AI-Ready Cards**. The real card details are replaced by a tokenized credential that encodes one fact the network can check: the consumer authorized *a specific agent within set limits.* The agent transacts with that credential, and Visa positions itself in the middle to **authenticate** the agent and the delegation, **authorize** the resulting purchase, and **tokenize** the underlying account so the PAN never travels.

The commercial piece is **Intelligent Commerce Connect**, a single integration that lets merchants accept agent-initiated payments across **four protocols** and across both Visa and non-Visa cards. The point of one integration over four protocols is to spare merchants from betting on a winner in the still-forming agent-payments protocol space — they wire up once and accept agent traffic regardless of which mandate or checkout standard the agent speaks.

## Mastercard Agent Pay

Mastercard's **Agent Pay**, introduced in April 2025, combines **Agentic Tokens** — an evolution of Mastercard's existing tokenization — with **agent-aware identity and checkout**. The identity layer is anchored in verifiable credentials and **FIDO** standards, so the "who is this agent and did the user delegate to it" question is answered with the same cryptographic machinery already used for passwordless authentication and strong customer authentication.

This is worth dwelling on: Mastercard did not invent a bespoke agent-auth protocol. It reused FIDO and verifiable credentials, which means agent identity can plug into flows engineers already understand. Mastercard demonstrated live, authenticated agentic transactions in Hong Kong and Thailand during 2025, showing the pattern works against real acquirers and issuers rather than in a sandbox.

## Reusing the tokenization and authorization rails

The elegance here is how little is new. Network tokenization already replaces PANs with domain-restricted tokens for wallets and card-on-file merchants. Agentic tokens extend that domain restriction to include the *agent* as a first-class dimension of scope. When the agent's purchase reaches the network, it flows through the same authorization request, the same fraud scoring, the same clearing and settlement, and the same dispute framework as any tokenized transaction.

That reuse is the reason this approach is credible rather than aspirational. There is no parallel money-movement system to stand up. The authorization message carries additional context — which agent, under which delegation — but the pipes are the ones already carrying trillions in card volume. A 3-D Secure-style authentication step slots in to verify delegation the way it verifies a cardholder today.

## Identity, limits, and monitoring

Three properties make a scoped agentic token safer than a stored PAN. First, **identity**: the token is tied to a verified agent, so a stolen token is far less useful to a different piece of software. Second, **limits**: the scope encoded at issuance lets the network reject out-of-bounds purchases before they ever reach the issuer. Third, **monitoring**: because agent transactions look like tokenized card transactions, existing real-time monitoring and anomaly detection apply, now enriched with the agent dimension. A compromised agent shows up as anomalous behavior on a credential whose blast radius is already capped by its scope.

## How this relates to AP2 and ACP

Scoped tokens do not compete with the emerging agent-payment protocols — they underpin them. Standards like AP2 (the Agent Payments Protocol) and agentic checkout protocols define the *mandate and checkout layer*: how an agent expresses "the user asked me to buy X under conditions Y" and how a merchant accepts that intent. The network's job sits underneath, providing the actual **tokenized credential** that the mandate references and that the checkout ultimately charges. Both Visa and Mastercard support AP2 — Mastercard and American Express are AP2 partners — and both are working with OpenAI, Stripe, and Microsoft to make sure the credential layer and the protocol layer line up. Think of AP2/ACP as the contract language and the agentic token as the instrument the contract points to.

## Risks

The dominant risk is credential hijack, and the dark-web signal Visa cited is a warning, not a hypothetical. Scoping is the mitigation, not a cure: a token bound to one agent, one user, and tight limits is a much smaller prize than a PAN, but it is still an asset an attacker will target. The harder problems are delegation UX (consumers granting scope they do not understand), revocation latency (how fast a compromised agent's token can be killed network-wide), and dispute attribution (who is liable when an authorized agent makes an unwanted purchase within its limits). None of these are solved by tokenization alone.

## What to remember

Card networks are not letting agents hold your card number. They are issuing a scoped, cryptographically bound credential that proves a specific agent was delegated specific authority, and then running it through the authentication, authorization, tokenization, and clearing rails they already operate. Visa Intelligent Commerce and Mastercard Agent Pay differ in packaging — AI-Ready Cards and one four-protocol integration versus Agentic Tokens plus FIDO-anchored identity — but they converge on the same principle: the safe unit of agent payment is a scoped token, not a PAN, and the network's enduring role is to authenticate, authorize, and tokenize.

## Sources
- https://www.digitalcommerce360.com/2025/05/06/visa-mastercard-ai-agentic-commerce/
- https://techinformed.com/visa-opens-one-integration-for-ai-agent-payments/
