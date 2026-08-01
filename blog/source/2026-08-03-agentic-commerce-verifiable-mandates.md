# Mandates and Verifiable Credentials: Proving an Agent Was Authorized

*When an AI agent spends your money, "the user said so" is not evidence. A signed mandate chain is.*

An agent that books travel or restocks your pantry acts on your behalf, but it acts without you in the loop at the moment of purchase. That gap breaks the assumption every payment system quietly relied on: that a human clicked the button. When something goes wrong, the merchant, the network, and the issuing bank all need to answer one question — was this actually authorized, and to what limit? A log line that says the agent claimed permission is not an answer. It is a claim, and claims can be forged, replayed, or misremembered.

Emerging agentic-payment designs, including Google's AP2 protocol and card-network approaches, answer this with cryptography rather than trust. The user's authorization is captured as a chain of cryptographically signed **mandates**, expressed as **Verifiable Credentials (VCs)**. The chain is not just a control that gates the purchase; it is the evidence that survives it.

## The old model and why it breaks for agents

In a card-present or even a normal web checkout, authorization is implicit in the act. The cardholder tapped, typed a one-time code, or passed a biometric check. The system does not store a portable proof of intent because the human presence *was* the proof.

Delegate that checkout to software and the proof evaporates. The agent asserts "my user authorized a hotel booking up to a nightly rate." Everyone downstream has to take that assertion on faith. If the agent overspends, buys the wrong thing, or is compromised, there is no artifact that pins down what the user genuinely agreed to. Disputes collapse into "he said, the bot said." Liability has nowhere to land. "Trust me, the user said so" does not scale to autonomous software making thousands of decisions.

## What a verifiable credential actually is

A verifiable credential is a tamper-evident, cryptographically signed statement of a claim. Three parts make it work:

- **Issuer** — the party that asserts the claim and signs it with a private key. For a mandate, this is effectively the user (or a wallet acting under the user's key).
- **Subject** — who or what the claim is about, and the substance of the claim: the constraints, the cart, the amount.
- **Proof** — a digital signature over the credential's contents. Anyone holding the issuer's public key can check the signature.

Two properties make VCs the right primitive here. First, **offline verification**: because the proof is a signature over the data, a verifier confirms authenticity by checking math, not by phoning the issuer on every transaction. Second, **revocation and expiry**: a credential can carry a short lifetime and can be listed as revoked, so a leaked or stale authorization stops working without rewriting the whole system.

## The mandate chain as evidence

The authorization is not one credential but a linked sequence, each signed, each narrowing the one before it:

- **Intent Mandate** — the user's authorization and its constraints. "Book a hotel in this city, these dates, under this nightly cap." It sets scope, not specifics.
- **Cart Mandate** — the exact items and price the user (or the user's rules) approved. Scope becomes a concrete, priced cart.
- **Payment Mandate** — the payment method and amount, plus a flag marking that an agent was involved. This is what the network and issuer see.

Read forward, the chain is a control: each step must fit inside the last. Read backward after the fact, it is a non-repudiable audit trail — a signed record of who authorized what, within which limits, and when. Because each link is signed, no party can later fabricate a broader authorization than the user actually granted, and the user cannot plausibly deny an authorization they signed.

```
   USER KEY (signs)
       │  VC proof
       ▼
 ┌───────────────┐   scope    ┌──────────────┐   price    ┌────────────────┐
 │ Intent Mandate│──────────▶ │ Cart Mandate │──────────▶ │ Payment Mandate│
 │ scope + limits│  constrains│ items + price│   locked   │ method + amount│
 └───────────────┘            └──────────────┘            └────────┬───────┘
                                                    submit signed chain
                                                                    ▼
  Revocation Registry ──── revocation + expiry ────▶  ┌──────────────────┐
  (status + expiry)                                   │     VERIFIER     │
                                                      │ checks signatures│
                                                      └───┬──────────┬───┘
                                          all proofs valid│          │ invalid / revoked
                                                          ▼          ▼
                                                ┌──────────────┐  ┌─────────┐
                                                │ Authorization│  │ Reject  │
                                                │ approve charge│  │ + log  │
                                                └──────┬───────┘  └─────────┘
                                                       │ persist signed chain
                                                       ▼
                                              ┌──────────────────┐
                                              │   AUDIT STORE    │
                                              │ non-repudiable   │
                                              └──────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-verifiable-mandates.html)** — the signed Intent→Cart→Payment chain flowing through offline verification and revocation into an approve/reject decision and the audit store.

## Signing, keys, expiry, revocation, replay

Turning this from a diagram into a system surfaces a familiar set of hard problems, now load-bearing:

- **Key management.** The whole scheme rests on the user's signing key being genuinely the user's. Keys live in a wallet or secure element; they must be provisioned, protected, and rotated without silently invalidating outstanding mandates. Card-network approaches pair VCs with **FIDO Alliance** standards so the signing key is bound to authenticated user hardware rather than a copyable secret.
- **Short expiry.** A mandate should be valid for as narrow a window as the task allows. A booking authorization that lingers for weeks is a standing liability; a minutes-long one limits the blast radius of a leak.
- **Revocation.** Users change their minds and keys get compromised. A revocation mechanism — a status list the verifier consults — lets an authorization be killed before its natural expiry.
- **Replay protection.** A signed mandate is a bearer artifact: capture it and you might resubmit it. Nonces, unique mandate identifiers, and binding each mandate to a specific transaction context stop a valid proof from being reused for a second charge.

## Verification at the merchant and network

At the point of purchase, the verifier — merchant, gateway, or network — does not take the agent's word for anything. It checks the signature on each mandate against the expected public key, confirms the chain links up (this cart falls within that intent, this payment matches that cart), and looks up revocation status and expiry. Only if every proof holds does it authorize the charge. If any check fails, the flow **fails closed**: the request is rejected and the reason logged. Crucially, most of this is local signature verification, so the check adds cryptographic assurance without a synchronous round trip to the credential issuer.

## Disputes and non-repudiation

The payoff arrives when something is contested. In the old model, "my agent bought this without permission" is unanswerable — there is no artifact of what permission looked like. With a signed mandate chain, there is. The stored Intent, Cart, and Payment mandates show exactly what the user authorized, signed by the user's own key. That is **non-repudiation**: the authorizing party cannot credibly disown a signature only they could have produced.

This reshapes liability. If the charge fell within a signed mandate, the authorization is provable. If the agent exceeded scope, the chain shows the mismatch and points responsibility at the agent or its operator rather than the user. Either way, the argument moves from memory and assertion to verifiable fact. That is why the chain must be stored as durable evidence, not discarded once the payment clears.

## What to remember

- Autonomous agents remove the human from the moment of purchase, so authorization has to become a portable, verifiable artifact rather than an implied click.
- A verifiable credential — issuer, subject, proof — gives you offline verification plus revocation and expiry, the exact properties a delegated authorization needs.
- The Intent → Cart → Payment chain is both a forward-looking control and a backward-looking audit trail; each signed link narrows the last.
- The engineering hard parts are ordinary crypto-system problems made critical: key custody, short expiry, revocation, replay protection, and verifying signatures at the edge.
- Store the chain. Its real value shows up in a dispute, when cryptographic proof replaces "trust me, the user said so."

## Sources

- https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol
- https://ap2-protocol.org/
