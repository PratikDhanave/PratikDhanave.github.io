# Building a Step-Up Authentication Orchestrator

*How a risk-driven layer escalates from silent approval to OTP, biometric, or 3DS challenge — holding a pending-challenge state and resuming the original transaction once the customer clears it.*

Most transactions should sail through untouched. A small, risky minority should be interrupted and asked for more proof. The hard part is not the individual challenge methods — OTP, biometric, and 3-D Secure are all well-trodden — it is the coordination layer that decides *which* challenge to raise, *parks the in-flight transaction* while the customer completes it, and then *resumes exactly where it left off*. That layer is a step-up authentication orchestrator, and getting its state model right is what separates a smooth escalation from a stuck checkout and a double charge.

The orchestrator sits between your risk engine and your challenge providers. It consumes a risk decision, selects a challenge tier, issues it, and blocks the transaction on a durable pending state until a verdict arrives.

```
 transaction intent
        |
   evaluate risk signals
        |
   +----+------+---------+---------+
   |          |         |         |
 no        OTP     biometric    3DS
 challenge    \       |        /
   |           challenge issued
 proceed             |
                pending state
                /           \
           verified      failed / expired
           resume txn    abandon txn
```


## Separate the decision from the challenge

The first design mistake is welding risk scoring to a specific challenge. When the payment path calls `send_otp()` directly, you cannot later slot in a biometric prompt without touching the payment code, and you cannot A/B two escalation policies. Keep two boundaries clean: a **risk engine** that emits a decision, and an **orchestrator** that turns that decision into an authentication ceremony.

The risk engine's output should be a small, typed verdict — not a raw score the orchestrator has to interpret. Bake the score-to-action mapping into the risk layer so the orchestrator only ever sees an action and the signals behind it:

```python
@dataclass
class RiskDecision:
    action: str          # "allow" | "challenge" | "deny"
    tier: str | None     # "otp" | "biometric" | "3ds" when action == "challenge"
    reasons: list[str]   # signals that drove it, for audit + adverse-action
    ttl_seconds: int     # how long a passed challenge stays valid
```

`allow` proceeds silently. `deny` stops the transaction outright — a step-up cannot rescue a transaction the risk engine has already decided to reject. Only `challenge` enters the orchestrator, and it arrives with the tier already chosen, so escalation policy lives in one place instead of being scattered across payment call sites.

## A ladder of challenge methods

Challenge tiers form a ladder of increasing friction and increasing assurance. A silent device-binding check costs the customer nothing; a full 3DS challenge with an issuer redirect costs conversion. The orchestrator's job is to raise the *lowest* tier that satisfies the risk the engine flagged.

- **Silent / device signals.** No user interaction — a trusted device cookie, a passkey assertion the platform can gather without a prompt, or a recent successful step-up still inside its TTL. Prefer this whenever the elevated risk is marginal.
- **OTP.** A one-time code over SMS, email, or an authenticator. Cheap to integrate, but phishable and dependent on deliverability, so treat a stalled OTP as a first-class failure mode, not an edge case.
- **Biometric.** A platform authenticator (fingerprint, face) via WebAuthn. High assurance, low friction *when the device supports it* — which is why the orchestrator must gracefully fall back to OTP when it does not.
- **3-D Secure.** Shifts liability to the issuer and runs the issuer's own challenge. The heaviest tier, reserved for high-value or clearly suspicious card transactions.

Each provider is wrapped behind one interface — `issue(context) -> challenge_id` and `verify(challenge_id, proof) -> result` — so the orchestrator treats them uniformly and a new method is a new adapter, not a new branch in the state machine.

## The pending state is the whole design

The moment you issue a challenge, the original transaction is in limbo. It has not succeeded and must not fail; it is *waiting*. That waiting has to be durable, because the customer might complete the challenge on another device, or thirty seconds later after fetching a code, or never. If the pending state lives only in the request thread, a load-balancer timeout or a pod restart strands the transaction.

Persist a challenge session that carries everything needed to resume the frozen transaction:

```python
@dataclass
class ChallengeSession:
    challenge_id: str
    txn_ref: str            # the parked transaction to resume
    tier: str
    status: str             # "pending" | "verified" | "failed" | "expired"
    attempts: int
    max_attempts: int
    expires_at: datetime    # hard wall-clock deadline
    resume_token: str       # opaque handle returned to the client
```

The `resume_token` is what the client polls or redeems on the callback; it never exposes the internal `txn_ref`. The `expires_at` deadline is non-negotiable — a pending challenge is a held resource (an authorization hold, an inventory reservation, a rate-limit slot), and an unbounded pending state leaks all of them. When the deadline passes, a sweeper transitions the session to `expired` and runs the same abandonment path a hard failure would.

Critically, issuing the challenge and writing the pending session must be atomic. Send the OTP *after* the session row commits, or a crash between the two leaves a code in the customer's pocket with no session to verify it against.

## Resume, retry, and abandon

When a verdict returns, the orchestrator resolves the pending session into exactly one terminal outcome and hands the parked transaction back to the payment flow.

**Verified.** The proof checks out, the session flips to `verified`, and the transaction resumes from the exact step where it paused. Resumption must be idempotent: the client may redeem the resume token twice (a retry, a double-tap), and the payment must complete once. Key the resumption on `txn_ref` so a second redemption returns the first result instead of charging again. On success, stamp the passed step-up with its TTL so an immediate follow-up transaction from the same context can skip re-challenging.

**Failed with budget left.** A wrong OTP is not fatal. Increment `attempts`; while it stays under `max_attempts`, re-prompt within the *same* session and the *same* expiry window — a retry must not reset the wall-clock deadline, or an attacker gets unlimited time by failing on purpose. Some designs escalate the tier on repeated failure (OTP → biometric) rather than merely repeating it.

**Abandoned.** Attempts exhausted, or the deadline hit. The session goes terminal, and — this is the step teams forget — the parked transaction must be *actively released*, not just left to rot. Void the authorization hold, free the reservation, and emit a clean decline the customer can retry from scratch. Silent abandonment is how holds pile up and inventory disappears.

## Operating it

Instrument the funnel, not just the endpoints. The numbers that matter are **step-up rate** (what fraction of transactions get challenged — too high and you are taxing good customers), **challenge completion rate by tier** (a low OTP completion often means a deliverability problem, not fraud), and **pending-session leak count** (sessions that should have terminated but did not). Alert on the leak metric specifically; it is the leading indicator that your sweeper or release path is broken.

A step-up orchestrator earns its keep by being invisible on the 98% of traffic that should never see a prompt, and rock-solid on the 2% that must. Keep the risk decision separate from the challenge, make the pending state durable and time-bounded, and treat resumption and abandonment as first-class terminal paths — and the rest is adding adapters.
