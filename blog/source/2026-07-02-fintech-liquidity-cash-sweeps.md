# Engineering Treasury Liquidity: Automated Cash Sweeps

*How to aggregate balances, compute target-vs-actual, and fire cutoff-aware sweeps that keep settlement accounts solvent without stranding idle cash.*

A payments platform holds money in dozens of operating accounts: one per scheme, per currency, per partner bank, per merchant float. Left alone, that cash drifts. One settlement account runs dry an hour before a scheme cutoff and a batch gets rejected for insufficient funds; meanwhile a concentration account two hops away is sitting on eight figures earning nothing. Treasury liquidity engineering is the discipline of moving money between your own accounts, on a schedule, so that every account that must settle can settle, and every surplus is swept somewhere useful.

This is deceptively hard because the transfers themselves ride external rails with cutoffs, the balances you read are always slightly stale, and a botched sweep can *cause* the shortfall it was meant to prevent. The engine below treats sweeping as a deterministic, replayable workflow rather than a nightly cron that hopes for the best.

## The shape of the problem

The core loop is small and runs continuously through the business day:

```
 balances        target logic        instructions      rails        monitor
┌──────────┐    ┌───────────────┐    ┌───────────┐   ┌────────┐   ┌──────────┐
│aggregate │ -> │ target vs     │ -> │ sweep     │ ->│ cutoff │-> │intraday  │
│ all acct │    │ actual (gap)  │    │ planner   │   │ + book │   │dashboard │
└──────────┘    └───────────────┘    └───────────┘   └───┬────┘   └──────────┘
                                                         │ missed
                                                         v
                                                    ┌──────────┐
                                                    │ queue for│
                                                    │next window│
                                                    └──────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-liquidity-cash-sweeps.html)** — pan, zoom, and trace every step (light/dark, self-contained).


Each stage is a pure function of the previous stage plus a snapshot timestamp. That property is what lets you re-run a cycle safely after a crash: the same balance snapshot produces the same instruction set, and instructions carry idempotency keys so a replay never double-transfers.

## Step 1 — Aggregate balances into one position view

You cannot sweep what you cannot see. The first stage pulls balances from every account into a single, timestamped position table. Sources are heterogeneous: some banks push near-real-time balance webhooks, some expose a polling API, and some only give you an end-of-day `camt.053` statement plus intraday `camt.052` reports. Normalize all of them into one internal shape.

The critical modeling decision is to separate **ledger balance**, **available balance**, and **projected balance**. Ledger balance is what has posted. Available balance subtracts holds and uncleared debits. Projected balance layers on the payments *you already know are coming* today — scheduled outbound settlements, expected inbound sweeps. Sweeping on ledger balance alone is how you drain an account that has a large debit landing in twenty minutes.

```python
@dataclass(frozen=True)
class Position:
    account_id: str
    currency: str
    ledger: int          # minor units, already posted
    available: int       # ledger minus holds/uncleared
    projected: int       # available plus known same-day flows
    as_of: datetime      # snapshot time, drives idempotency
```

Every downstream decision reads `projected`, never `ledger`.

## Step 2 — Compute target vs actual and choose a rule

Each account carries a sweep policy. Three rule families cover almost everything:

- **Zero-balance (ZBA):** at the sweep, the account is driven to exactly zero — surplus swept up to a concentration account, deficit funded down from it. Used for disbursement and collection accounts that should never hold a resting balance.
- **Target-balance:** the account is driven to a configured floor (say, one day of expected settlement plus a buffer). Surplus above the target is swept out; a balance below it is topped up. This is the rule for settlement accounts that must always be able to meet a cutoff.
- **Concentration (pooling):** many child accounts sweep into one header account so idle cash is pooled for investment or intraday funding, without commingling that would break client-money segregation rules.

The engine computes a signed `gap = projected - target` per account. A positive gap is sweepable surplus; a negative gap is a funding need. Netting matters here: if child A needs 200 and child B has 300 surplus, you route B→A directly rather than B→header and header→A, halving the transfer count and the fees.

```python
def compute_gap(pos: Position, policy: SweepPolicy) -> int:
    if policy.kind == "zba":
        return pos.projected                    # drive to zero
    if policy.kind == "target":
        return pos.projected - policy.target    # +surplus / -deficit
    raise ValueError(policy.kind)
```

## Step 3 — Generate cutoff-aware sweep instructions

Gaps become transfer instructions, but only ones the rails can still honor. This is where most naive sweep engines fail: they compute a perfect set of transfers at 4:55 PM and discover the 5:00 PM cutoff has already closed the window for a same-day book move.

Every instruction is tagged with the rail it will use and that rail's remaining window. A book transfer between two accounts at the *same* bank is effectively instant and has a late cutoff. An external transfer over ACH or a wire has a hard, earlier cutoff and a settlement lag. The planner sorts funding needs first (a deficit is urgent; an idle surplus is not), then assigns each instruction to the cheapest rail whose cutoff has not passed:

```python
def plan(gaps: list[Gap], now: datetime) -> list[Instruction]:
    needs   = [g for g in gaps if g.amount < 0]   # fund these first
    surplus = [g for g in gaps if g.amount > 0]
    out = []
    for g in needs + surplus:
        rail = pick_rail(g, now)                   # earliest viable, cheapest
        if rail is None:
            defer(g, reason="cutoff_passed")       # -> exception queue
            continue
        out.append(Instruction(
            key=idem_key(g.account_id, g.snapshot_as_of),
            source=rail.source, dest=rail.dest,
            amount=abs(g.amount), rail=rail.name,
            not_after=rail.cutoff,
        ))
    return out
```

The idempotency key binds the instruction to the *snapshot* it came from, so re-planning the same cycle produces byte-identical keys and the execution layer deduplicates.

## Step 4 — Execute, book, and reconcile on the dashboard

Execution submits each instruction to its rail and records the outcome as a double-entry pair against an internal transfer-clearing account, so the books stay balanced even while a transfer is in flight. An instruction that clears immediately (a book move) posts and settles at once. An external transfer posts a debit-in-transit entry now and settles when the rail confirms.

Everything feeds an intraday liquidity dashboard: projected end-of-day balance per account, funding needs still open, sweeps in flight, and — most importantly — any account trending toward a shortfall before its next cutoff. The dashboard is the human override surface. Treasury operators watch it and can pin a manual sweep when a rule-based one would be too conservative.

## Failure modes worth designing for

**Missed cutoffs.** When `pick_rail` finds no viable window, the instruction goes to an exception queue rather than being dropped. It is re-evaluated at the next window with a fresh snapshot — a funding need that missed the wire cutoff may still be satisfiable by an instant book move from a different surplus account.

**Stale snapshots.** Because gaps are computed from `projected` balances that may be seconds to minutes old, execution must re-check availability at the moment of booking. A sweep that would overdraw the source at post time is rejected and re-queued, never forced through.

**Partial failure.** If a batch of instructions is half-submitted when the process dies, the idempotency keys make replay safe: already-accepted transfers are deduplicated by the rail, and the clearing account reconciles in-transit entries against rail confirmations. No money is created or destroyed — the invariant a treasury system must never violate.

The whole design earns its keep by being boring and deterministic. Snapshots in, instructions out, every transfer keyed and reversible, every exception queued rather than lost. That is what keeps a settlement account solvent at 4:59 PM without a human doing arithmetic under pressure.
