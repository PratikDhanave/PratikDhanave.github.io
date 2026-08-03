# MPC Custody: Signing Without Ever Holding a Whole Key
*Design MPC / threshold-signature custody so no single party or HSM holds a whole key.*

Custody is the part of a crypto product where a single mistake is unrecoverable. A private key is a bearer credential: whoever reconstructs it can move the funds, and there is no chargeback, no issuer to call, and no reversal window. The obvious defense is to never let the whole key exist in one place. Multi-party computation (MPC), specifically threshold signature schemes (TSS), lets a set of independent parties jointly produce a valid signature while each holds only a mathematical *share* of the key. The full key is never assembled on any machine, at any time, including during signing. This post is about how that actually fits together as a system, and where the sharp edges are.

## The single-key problem

Put a raw private key on a server and you have one host whose compromise drains the wallet. Wrap it in an HSM and you narrow the attack surface, but you still have a single device, a single operator with access, and a single point whose failure or seizure ends the story. Backups make it worse: every copy of the key is another place it can leak.

The instinct to split the key is right, but the naive version is dangerous. Classic Shamir secret sharing splits a key into shares and needs *t* of them to rebuild it — but rebuilding means the whole key materializes in memory on whatever box does the reassembly, if only for microseconds. That reconstruction moment is exactly the window an attacker wants. Threshold signatures avoid it entirely: the parties run a protocol that outputs a signature directly, and the key is never recombined.

## Distributed key generation

The property that makes MPC custody trustworthy starts before any signing happens. In distributed key generation (DKG), each of the *n* parties generates its own secret share locally and they exchange only public commitments. At the end, there is a single public key (and therefore a single wallet address on chain), but the corresponding private key exists only as the implicit sum of shares that were never in the same place.

This is the load-bearing detail to get right in code review: if your key generation has a step where a coordinator produces the full key and then splits it, you have built Shamir with extra latency, not MPC. Real DKG has no such step. Verify it by asking where the full scalar ever lives — the honest answer must be *nowhere*.

## The signing ceremony

Signing is a short, choreographed protocol. A requester asks to move funds; a coordinator sequences the ceremony but holds no key material; a policy engine decides whether the request is even allowed; then the qualifying share holders each compute a partial contribution, which are combined into one ordinary signature and broadcast.

```
                          ┌────────────┐
                    ┌────►│  Signer A  │ share 1/3 ─┐
                    │     └────────────┘            │
 Requester          │     ┌────────────┐            ▼
    │    Coordinator │────►│  Signer B  │ share 2/3 ─► Assembly ─► Chain RPC
    ▼        │      │     └────────────┘            ▲     (combine
 sign req ──►│─► Policy    ┌────────────┐            │     partials)
             │  (2-of-3)──►│  Signer C  │ share 3/3 ─┘
             │             └────────────┘
        holds no key
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-mpc-threshold-wallets.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Two roles deserve attention. The **coordinator** is deliberately powerless over the keys: it routes messages and enforces ordering, so compromising it can stall or reorder a ceremony but cannot forge a signature. The **policy engine** is where your business controls live — spending limits, allow-lists of destination addresses, velocity checks, dual-authorization for large transfers. Because a signature cannot be produced without a quorum, the policy engine sits in front of that quorum and every party independently refuses to contribute to a request it has not seen approved. Approval is not a single yes; it is a threshold of parties each independently agreeing to sign.

## t-of-n: availability against blast radius

The two numbers in a scheme, threshold *t* and total *n*, encode a direct trade-off, and picking them is a systems decision, not a cryptographic one.

- Raising *t* increases security: an attacker must now compromise more independent parties to sign. It also reduces availability, because more parties must be online and healthy for any legitimate transfer.
- Raising *n* adds redundancy: more share holders means more can be offline or lost before you are stuck.

A 2-of-3 setup is a common starting point: it tolerates one party being fully compromised without loss of funds (the attacker holds one share, one short of a quorum) and tolerates one party being offline without loss of availability. For higher-value wallets, teams push toward 3-of-5 to widen both margins. Model these as independent failure domains — different clouds, different regions, different operators, different key custodians. Three shares in three pods on the same cluster is theatre; the correlated failure of that cluster takes all of them at once.

```python
scheme = ThresholdScheme(
    threshold=2,          # signatures need any 2 shares
    parties=3,            # shares held in 3 trust domains
    domains=["aws-us", "gcp-eu", "on-prem-hsm"],
)
assert scheme.threshold <= scheme.parties
assert len(set(scheme.domains)) == scheme.parties   # no shared blast radius
```

## Operational concerns

The cryptography is the easy part; the operations are where custody programs live or die.

**Share rotation.** Proactive secret sharing lets parties re-randomize their shares on a schedule without changing the public key or the on-chain address. Old shares become useless, so an attacker who slowly exfiltrates one share per quarter never accumulates a quorum of *currently valid* shares. Treat rotation as a routine, tested job, not an incident-only procedure.

**Liveness and partitions.** Because signing needs a quorum online, a network partition can leave a legitimate transaction unsignable even though no funds are at risk. Build for it: idempotent ceremony IDs so a retried request cannot double-sign, timeouts that abort cleanly rather than hang, and clear operator signals when a party is unreachable so you fix availability before it becomes an outage.

**Auditability.** Every party should log the request it agreed to sign, in a form you can reconcile after the fact. When something goes wrong, you want to prove which shares participated in which ceremony and under what policy decision — a tamper-evident trail per party, not one central log the coordinator alone controls.

## What MPC does not solve

MPC removes the single-key failure mode. It does not remove authorization risk. If your requester can be tricked into asking for the wrong destination address — through a compromised front end or social engineering — the parties will happily sign a fraudulent-but-authorized transaction, because from their view the policy passed. Address allow-lists, out-of-band confirmation for new destinations, and simulation of the transaction before signing all belong in front of the ceremony, not inside it.

MPC also is not the same as on-chain multisig. Multisig is enforced by a smart contract and is visible on chain as multiple signatures; MPC produces a *single* ordinary signature and is invisible to the chain, which keeps fees and privacy identical to a normal wallet but moves all the enforcement into your own infrastructure. That is a feature and a responsibility: with MPC, the quorum logic is yours to get right, test, and defend.

Threshold custody is worth the operational weight when the alternative is a single key you can never fully de-risk. Design for independent trust domains, insist that the full key exists nowhere, and put your real controls in the policy engine that every party consults before it contributes a single partial signature.
