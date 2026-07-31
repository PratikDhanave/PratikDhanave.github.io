# Controls, Access, and Testing a System That Moves Money
*The last mile of a financial system isn't code — it's who can do what, who approves it, and how you prove the whole thing is correct.*

You can build a beautiful double-entry ledger, a clean event log, an idempotent payment gateway — and still lose money because one engineer with a database console ran an `UPDATE balances SET ...` to "fix" a support ticket. The code was fine. The controls were missing.

This is the finale of the handbook, and deliberately the least glamorous part. The controls layer is where financial engineering stops being about data structures and starts being about people, permissions, and proof. Every serious money system converges on the same four ideas: split powerful actions across people, scope access to the minimum, make every change auditable, and test invariants instead of examples.

## Segregation of duties: split the dangerous action

The founding rule is simple. No single human should be able to both initiate and complete a consequential action — not a payment, not a fee-table change, not a credit-limit bump.

This isn't distrust of your colleagues — it's an acknowledgment that a single compromised account, a bad day, or a fat-fingered mistake should never be enough to move money incorrectly. You split the powerful action into two roles so any incorrect movement requires two independent failures.

Segregation of duties is a boundary across the system:

```
         ┌─────────────────────────────────────────────┐
         │              INITIATE domain                 │
         │   create payment · propose fee change        │
         │   raise limit · schedule payout              │
         └───────────────────┬─────────────────────────┘
                             │   (hard boundary)
         ══════════════════ ╪ ══════════════════════════
                             │
         ┌───────────────────┴─────────────────────────┐
         │               APPROVE domain                 │
         │   authorize payment · confirm config change  │
         │   grant elevation · release the batch        │
         └─────────────────────────────────────────────┘
```

Whoever operates in the initiate domain for a transaction must never also operate in the approve domain for that same transaction. The boundary is enforced by the system — checked at the point of action — not printed in a policy PDF everyone signed once and forgot.

## Four-eyes and maker-checker: enforced, not requested

The concrete implementation of segregation of duties is maker-checker, or four-eyes. The maker creates something; a different person — the checker — reviews and approves it before it takes effect.

```
  MAKER                    SYSTEM                  CHECKER (≠ maker)
   │                          │                          │
   │  create payment          │                          │
   ├─────────────────────────▶│                          │
   │                          │  state = PENDING         │
   │                          │  maker_id recorded       │
   │                          │                          │
   │                          │   surfaced for review    │
   │                          ├─────────────────────────▶│
   │                          │                          │
   │                          │      approve / reject     │
   │                          │◀─────────────────────────┤
   │                          │                          │
   │                          ▼                          │
   │            ┌──────────────────────────┐             │
   │            │ checker_id == maker_id ?  │             │
   │            └───────┬──────────┬────────┘             │
   │                  yes│        no│                     │
   │                    ▼          ▼                      │
   │               REJECTED    EXECUTED  /  REJECTED      │
   │            (self-approval)  (money moves) (declined) │
```

The crucial check is the boring one in the middle: `checker_id != maker_id`. If your approval endpoint doesn't reject self-approval at execution time, you don't have four-eyes — you have a suggestion.

```python
def approve(action, checker):
    if action.state != "PENDING":
        raise Conflict("not awaiting approval")
    if checker.id == action.maker_id:
        raise Forbidden("maker cannot approve own action")
    if not checker.can_approve(action.type, action.scope):
        raise Forbidden("checker lacks approval authority")
    action.transition("EXECUTED", checker_id=checker.id)
```

This pattern shows up well beyond payments. Onboarding and risk decisions use it constantly — see how [maker-checker in KYC/AML and credit-bureau flows](/blog/posts/p2p-lender-kyc-aml-credit-bureau-maker-checker.html) gates identity verification and bureau pulls the same way a payment release does. The shape is identical: one person proposes, a different person with distinct authority commits.

A few things separate a real implementation from a checkbox one. Approval authority is scoped — a checker cleared for small payouts shouldn't release a million-dollar wire. The pending state is durable and idempotent, so a double-clicked approve button can't execute twice. And rejections are first-class outcomes with reasons, not silent deletions, because a rejected payment is evidence too.

## Access control: least privilege, scoped and time-bound

Maker-checker only means something on top of real access control — if everyone is an admin, the boundary is decorative.

The working principle is least privilege: every identity — human or service — gets exactly the permissions its job requires and nothing more. But in a money system, "permission" is more than a role name; it's scoped to accounts and actions. A support agent might read balances for accounts in their queue and nothing else. A settlement service can post to clearing accounts but cannot touch customer wallets. Permission is a function of `(who, what action, which accounts)`, not a global flag.

The most dangerous operations — reversing a settled transaction, editing a ledger entry, exporting the full customer table — shouldn't sit in anyone's standing permission set at all. Those go behind time-bound elevation: you request the power, someone approves it (four-eyes again), you get it for thirty minutes, and it evaporates. Standing god-mode is how a leaked credential becomes a breach report.

Every access decision — granted or denied — is logged. A stream of denied attempts against sensitive accounts is one of the earliest signals something is wrong, and you only see it if denials are recorded as carefully as approvals.

## The change trail: production config is production code

Engineers instinctively guard production code — reviews, CI, sign-off. Then they let someone edit the fee table, an interchange rate, or a fraud threshold through an admin panel with no review at all. That's backwards. A wrong fee applied to every transaction for six hours can cost more than most code bugs.

Treat configuration with the same discipline as code. Every change to anything affecting money movement answers four questions from the record alone: who changed it, what the old and new values were, when it took effect, and who approved it. That means config changes flow through the same maker-checker gate, land in an append-only change log, and are reversible to a known prior state.

The test I apply: if you can't reconstruct exactly what the fee schedule was on a given day last quarter, and who signed off on the version that was live, your change trail isn't good enough. Auditors will ask, but so will your own incident responders at 2 a.m. — and "I think someone changed it in the panel" is not an answer.

## Testing a money system: assert invariants, not examples

Example-based tests — "a $10 transfer leaves a $90 balance" — are necessary and nowhere near sufficient. Money systems fail in the combinations you didn't enumerate, so you test properties that must hold across thousands of generated scenarios.

- **Ledger invariants via property-based tests.** Generate random sequences of valid postings and assert the invariants that can never break: every transaction's postings sum to zero, no account violates its allowed sign. If a generated sequence breaks an invariant, the framework shrinks it to the minimal failing case for you.
- **Replay determinism.** Rebuild all balances purely from the event log and assert they match live state exactly, twice, identically. If replay is non-deterministic, your "source of truth" isn't one.
- **Simulation and fault injection.** Inject timeouts, duplicate deliveries, and partial failures between the payment and the ledger, then assert retries converge to the correct single outcome. This is where idempotency keys earn their keep — or reveal that they don't.
- **The golden reconciliation.** A scheduled job that sums every account across the system and asserts the total nets to zero. It must always pass. The day it doesn't, you stop new movements and investigate, because a nonzero total means money has been invented or destroyed.

The mindset shift is the whole point: you don't prove a money system correct with a handful of hand-picked cases. You state the laws it must obey and let generated chaos break them.

## Why it matters

Everything earlier in this handbook — the double-entry ledger, immutable events, idempotent gateways, reconciliation — gives you a system that is *correct by construction*. The controls layer keeps it correct *in operation*, once real humans with real access and real deadlines start using it.

That's the through-line of the whole series. A financial system isn't trustworthy because it's clever; it's trustworthy because no single person can move money alone, every change is attributable, elevated power is temporary, and correctness is asserted continuously rather than assumed. Get the data model right and you can sleep. Get the controls and testing right and you can let other people touch it while you sleep. That, in the end, is what it means to build a system that moves money — not just code that runs, but a machine you can *prove* is honest on the day someone asks.
