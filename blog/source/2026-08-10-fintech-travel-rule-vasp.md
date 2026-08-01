# Implementing the FATF Travel Rule Between VASPs

*How to exchange originator and beneficiary data between crypto services before a transfer settles: counterparty discovery, IVMS101 payloads, and pre-transfer verification that gates the on-chain send.*

---

A bank wire carries the sender's and receiver's details inside the payment message itself. A blockchain transaction does not: it moves value between two opaque addresses and carries no identity at all. The FATF Travel Rule closes that gap for regulated crypto businesses by requiring that when one Virtual Asset Service Provider (VASP) sends value to another above a threshold, it must transmit originator and beneficiary information to the receiving VASP. The awkward engineering fact is that this data has to travel over a completely separate channel from the asset — the chain has no field to put it in.

So the Travel Rule is not a chain feature you can bolt on. It is a *pre-transfer messaging protocol* that runs alongside your custody and settlement stack, and it has to complete before your signer ever broadcasts. This post is about the shape of that protocol and the state you have to manage to run it safely.

## Why the data exchange must precede the broadcast

The naive design is to send the asset, then send the identity data afterward "for the record." That fails the rule's intent and creates a live compliance problem: once the transaction is on-chain it is irreversible, so if the receiving VASP would have rejected the counterparty — sanctioned beneficiary, unhosted-wallet policy mismatch, unknown originator — you have already moved the money and cannot claw it back.

The correct ordering is the opposite. Identity data is exchanged and accepted *first*; only an accepted exchange unlocks the signer.

```
Originator VASP                                  Beneficiary VASP
     │  1. discover  ──────────────────────────────▶  (who controls
     │     (which VASP owns the destination addr?)      this address?)
     │  2. IVMS101 originator + beneficiary payload ─▶  screen + verify
     │  3. accept / reject  ◀──────────────────────── decision
     │                                                     │
     ▼  4. broadcast on-chain  (ONLY if accepted)          ▼
  signer ──────────── blockchain ─────────────────▶  credit beneficiary
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-travel-rule-vasp.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The gate in step 4 is the whole design. Your withdrawal pipeline must treat "Travel Rule accepted" as a hard precondition for signing, the same way it treats an approval quorum or a sanctions clearance. A transfer whose Travel Rule exchange is still pending sits in a `HELD` state, not a `SIGNING` state.

## Counterparty discovery: whose address is this?

Before you can send data to the beneficiary VASP you have to know which VASP that is, and you only have a destination address to start from. Address ownership is not on the chain, so discovery is a lookup problem with a few possible answers.

- **The address is at a known custodial VASP.** You resolve it through a directory or address-attribution service and get back a reachable Travel Rule endpoint.
- **The address is self-hosted (unhosted wallet).** There is no counterparty VASP to talk to. Depending on jurisdiction you may still need to collect and record beneficiary information from your own customer, and possibly prove wallet control, but there is no peer exchange.
- **The address is unknown.** You cannot attribute it. Policy decides whether to proceed with self-hosted handling or block.

Discovery drives everything downstream, so model its outcome as an explicit enum rather than a boolean:

```python
class CounterpartyResolution(Enum):
    KNOWN_VASP     = "known_vasp"      # exchange required
    SELF_HOSTED    = "self_hosted"     # collect + record, no peer
    UNATTRIBUTED   = "unattributed"    # policy gate

def resolve(dest_address) -> CounterpartyResolution:
    hit = directory.lookup(dest_address)
    if hit and hit.travel_rule_endpoint:
        return CounterpartyResolution.KNOWN_VASP
    if wallet_proof.is_self_hosted(dest_address):
        return CounterpartyResolution.SELF_HOSTED
    return CounterpartyResolution.UNATTRIBUTED
```

Discovery also has to survive a real-world messiness: two VASPs may support different Travel Rule protocols. Interoperability is the recurring pain point, so your client should negotiate the protocol per counterparty rather than assume one wire format.

## Modeling the payload: IVMS101 as the shared type

The industry settled on a common data model, IVMS101 (InterVASP Messaging Standard), precisely so that a payload built by one VASP parses cleanly at another regardless of transport. Treat it as your canonical schema and keep transport concerns out of it.

An IVMS101 message has three top-level parties: the originator, the beneficiary, and the two VASPs. Each natural-person party carries structured name (with an explicit `nameIdentifierType` distinguishing legal from alias names), a national identifier, a date and place of birth, and a geographic address. The structure is deliberately strict because half the value of a shared standard is that fuzzy free-text names can be matched and screened on the far side.

```python
@dataclass(frozen=True)
class NaturalPerson:
    primary_name: str        # e.g. legal surname
    secondary_name: str      # given name
    name_type: str           # LEGL | ALIA | BIRT ...
    national_id: str | None
    country: str

@dataclass(frozen=True)
class IVMS101:
    originator: NaturalPerson
    beneficiary: NaturalPerson
    originating_vasp_lei: str
    beneficiary_vasp_lei: str
```

Two engineering disciplines matter here. First, **minimize and validate**: send exactly the fields the rule requires and no more, because you are shipping personally identifiable information to a third party and every extra field is liability. Second, **encrypt in transit and pin the peer**: the exchange carries PII, so it runs over an authenticated, mutually verified channel — you are not just POSTing JSON to a URL you found in a directory.

## The accept/reject decision and the settlement gate

When the beneficiary VASP receives the payload it does its own work: confirm the beneficiary is actually its customer, screen the originator against sanctions and watchlists, and apply its unhosted-wallet and jurisdiction policies. It then returns a decision. That decision is the signal your signer is waiting on.

Model the transfer as a small state machine so the gate is impossible to bypass:

```
DISCOVERING → DATA_SENT → (ACCEPTED → SIGNING → BROADCAST → SETTLED)
                        ↘ (REJECTED → CANCELLED)
                        ↘ (TIMEOUT  → HELD_FOR_REVIEW)
```

`ACCEPTED` is the only edge that reaches `SIGNING`. A `REJECTED` response cancels the withdrawal and releases any internal hold on the customer's balance. A timeout — the counterparty never answered — must *not* silently fall through to broadcast; it parks the transfer for an operator, because a missing answer is not a yes.

The idempotency concern mirrors any payment system. The peer exchange can be retried, the counterparty can reply twice, and your own broadcast attempt can be re-driven after a crash. Key the exchange on a stable transfer id and make the accept-then-sign transition a guarded, once-only step:

```python
def on_decision(transfer_id, decision):
    t = load(transfer_id)
    if t.state != "DATA_SENT":        # already resolved; ignore replay
        return
    if decision == "ACCEPTED":
        t.transition("SIGNING")       # unlocks the signer, exactly once
    else:
        t.transition("CANCELLED")
    save(t)
```

## Failure modes to design against

- **Broadcasting before acceptance.** The cardinal sin. The signer must physically require an `ACCEPTED` transfer id; do not leave "send anyway" as a reachable code path.
- **Treating timeout as success.** No response is a hold, never an implicit yes. Counterparties go down; your money must not.
- **PII over-collection or over-sharing.** Send the required fields to the verified counterparty only. Log that an exchange happened, not the plaintext identity payload, in systems that do not need it.
- **Protocol mono-culture.** Assuming every VASP speaks your wire format guarantees failed transfers. Negotiate per counterparty and degrade gracefully when a peer is unreachable.
- **Losing the link to the on-chain tx.** Persist the mapping from the Travel Rule exchange to the eventual transaction hash, so an audit can reconstruct which identity data authorized which settled transfer.

The mental model that keeps this correct is to stop thinking of the Travel Rule as paperwork attached to a transfer and start thinking of it as a **distributed handshake that gates an irreversible action**. The chain gives you no take-backs, so all the safety has to live in the ordering: discover, exchange, accept, and only then sign.
