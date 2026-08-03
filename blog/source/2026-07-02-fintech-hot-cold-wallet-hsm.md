# Building Custody: Hot, Warm, and Cold Wallets Without a Single Point of Compromise

*How to architect wallet tiers, HD-derived deposit addresses, HSM/MPC signing quorums, and sweep flows so no one key, and no one person, can move funds.*

Custody is the part of a crypto platform where a single mistake is unrecoverable. There is no chargeback, no issuer to call, no reversal. If a private key leaks or a withdrawal signs when it should not have, the money is gone and the on-chain record is permanent. So the entire discipline of custody engineering is about arranging keys, approvals, and money movement so that no single failure — a compromised server, a rogue operator, a leaked secret — can drain funds.

The organizing idea is a tiered wallet model. You do not keep customer funds in one big wallet. You split holdings across tiers that trade off availability against blast radius, and you move value between them under strict controls. Get the tiering and the signing model right and the rest of the platform inherits its safety.

## The tiered wallet model

Three tiers, each with a different risk posture:

```
                       DEPOSITS                          WITHDRAWALS
                          │                                  ▲
                          ▼                                  │
   ┌───────────────┐  fund   ┌──────────────┐  refill  ┌───────────────┐
   │  HOT wallet   │◄────────│ WARM wallet  │◄─────────│  COLD storage │
   │ online signer │         │ HSM, quorum  │          │ offline / air │
   │ small float   │──sweep─▶│ larger float │──sweep──▶│ gapped, deep  │
   └───────────────┘         └──────────────┘          └───────────────┘
      auto-signs               2-of-3 human              m-of-n ceremony
      capped amounts           approval                  rarely touched
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-hot-cold-wallet-hsm.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The **hot wallet** is online and can sign automatically. It holds a small operating float — enough to service the normal rate of customer withdrawals for a bounded window, and no more. If it is fully compromised, your loss is capped at that float, which you treat as a known, insured operational cost rather than an existential risk.

The **warm wallet** holds a larger balance and requires human approval plus HSM-held keys to sign. It refills the hot wallet on a schedule or when the hot float drops below a threshold. It is online enough to act within minutes but never signs without a quorum.

**Cold storage** holds the bulk of assets with keys that never touch an internet-connected machine. Moving cold funds is a deliberate, audited ceremony involving multiple people, often air-gapped signing devices. You touch it rarely and never on a customer's timeline.

The critical invariant: **value flows downward toward cold under automation, and upward toward hot only under increasing human control.** Deposits and sweeps push funds to safety cheaply; pulling funds back out costs approvals. That asymmetry is the whole design.

## HD wallets: one seed, unlimited deposit addresses

Every customer needs a unique deposit address so you can attribute incoming funds without a memo field. Generating and independently backing up a fresh keypair per customer does not scale. Hierarchical Deterministic (HD) wallets solve this: a single master seed deterministically derives a practically unlimited tree of child keys along a derivation path.

```
master seed ──▶ m / purpose' / coin' / account' / change / index
                                                             │
              index 0 ─▶ address for customer A ◄────────────┤
              index 1 ─▶ address for customer B              │
              index 2 ─▶ address for customer C  (derive on demand)
```

Two properties make this operationally powerful. First, you back up **one seed** and can regenerate every derived address forever — your disaster-recovery surface is a single well-guarded secret, not a growing database of keys. Second, HD wallets support **public derivation**: from an extended *public* key you can generate deposit addresses on an online system that holds no private material at all. The address-vending service watches the chain and attributes deposits; the private keys that could spend those deposits stay in the cold tier. An attacker who owns your deposit-address generator learns addresses, not the ability to move a single coin.

Watch the derivation-path conventions and the gap limit — wallets and explorers only scan a bounded number of unused addresses ahead, so sweeping stale addresses requires walking the tree deliberately.

## Signing: HSM key hierarchies and MPC quorums

The deposit side is public-key-only, so the sharp end of custody is the *signing* side: how a withdrawal or a sweep actually authorizes spending. Two approaches dominate, and mature platforms often combine them.

**HSM-backed hierarchies.** Private keys are generated inside a Hardware Security Module and are non-exportable — the HSM signs on request but the raw key never leaves the hardware boundary in cleartext. You layer keys: a master key protects operational keys, which protect working keys. Access to the signing operation is gated by authenticated, quorum-enforced requests, so obtaining a database dump or a server's memory gets an attacker nothing spendable.

**MPC (multi-party computation).** Instead of one whole key sitting in one place, the key is *never assembled at all*. It exists as mathematical shares distributed across several parties (services, devices, or people), and signing runs a protocol where each party contributes without ever revealing its share or reconstructing the full key. A threshold — say 3 of 5 — must cooperate to produce a signature. Compromising any two shares yields nothing. MPC also gives you on-chain privacy: the result is an ordinary single signature, so the quorum structure is invisible to the network, unlike a multisig script.

The engineering point is the same in both: **no single machine ever holds a spendable key.** HSMs enforce it with hardware; MPC enforces it with math. Choose based on your chains, your latency budget, and whether you need cross-chain key portability.

## The withdrawal path: policy before signature

A withdrawal must never go straight from an API call to a signer. Every spend passes through a policy engine that evaluates the request *before* any signing party is asked to participate:

- **Velocity and limits** — per-customer, per-address, and platform-wide caps over sliding windows.
- **Allowlist / travel-rule checks** — is the destination known, sanctioned, or newly added within a cooldown window?
- **Anomaly signals** — unusual amount, destination, or timing relative to the account's history.
- **Approval quorum** — amounts above a threshold require N human approvers, each authenticating independently. No approver can also be the requester.

Only after policy passes does the request reach the signing quorum. Then the transaction is constructed, signed by the HSM or MPC parties, broadcast, and tracked to confirmation depth before the ledger marks it settled. Structure it as an explicit state machine — `requested → policy-approved → quorum-approved → signed → broadcast → confirmed` — with every transition written to an append-only audit log. When an auditor or an incident responder asks "who approved this and on what basis," the answer is a query, not an archaeology project.

## Sweeps: consolidating deposits safely

Deposits land on thousands of HD-derived addresses, each holding a customer's incoming balance. Leaving funds scattered there is both a security liability and a UTXO-management headache, so a **sweep** process periodically consolidates them into the hot or warm wallet, and from there pushes excess down to cold.

Sweeps are the one place where per-address private keys get exercised, so treat them as sensitive automation: derive the key just-in-time inside the secure boundary, sign, broadcast, and never persist the derived private key. Batch sweeps to amortize network fees, and gate the fee logic so a fee spike cannot spend more value than it recovers. Because HD derivation is deterministic and replay-safe, a sweep job that crashes mid-run can be re-run from a checkpoint without minting duplicate keys or losing track of what was already moved.

## What makes custody defensible

The teams that sleep at night share a few habits. They size the hot float to a bounded, insurable loss and let cold hold the rest. They keep deposit-address generation public-key-only so the online attack surface has nothing to steal. They ensure no single key and no single person can move funds — hardware or math enforces the quorum, and requester-approver separation enforces the human side. And they route every spend through a policy engine and an append-only audit trail, so custody is a property they can *prove* rather than a promise they hope holds. Custody is not one clever trick; it is making the failure of any single component survivable by design.
