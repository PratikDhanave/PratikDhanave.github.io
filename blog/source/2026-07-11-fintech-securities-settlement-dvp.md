# Delivery-versus-Payment: Settling Securities on T+2 Without Principal Risk

*Settle securities delivery-versus-payment on T+2 through a central securities depository — the securities analog to FX PvP.*

When two parties agree a trade, the hard part is not agreeing the price. The hard part is the moment of exchange: the seller has to hand over securities and the buyer has to hand over cash, and if those two events happen at different times, whoever moves first is exposed to the other defaulting in between. That exposure is principal risk, and it is the entire reason delivery-versus-payment (DvP) exists. DvP is the securities-market cousin of payment-versus-payment (PvP) in FX: both are mechanisms to make two obligations settle as a single indivisible event so that neither party can be left having delivered without receiving.

This post walks through how a DvP settlement actually gets engineered on a standard T+2 cycle, where the atomicity comes from, and what happens when a leg fails.

## The settlement timeline is not the trade timeline

A trade executes on trade date, which everyone calls T+0. Settlement — the actual movement of securities and cash — happens on T+2, two business days later. That gap is deliberate. It gives both sides time to enrich the trade with settlement details, match instructions, allocate a block trade across sub-accounts, and source any securities they need to borrow.

The mistake engineers make coming from a payments background is treating T+2 as latency to be minimized. It is not. The two-day window is a batch-oriented reconciliation period, and the settlement instruction is a *promise to settle on a future date*, not a request to settle now. Your state model needs to represent "instructed but not yet settled" as a first-class, days-long status.

```
T+0  Trade executed        -> matched, novated to CCP
T+1  Instructions matched  -> pending settlement (positioned)
T+2  Settlement date       -> DvP swap at the CSD -> settled | failed
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-securities-settlement-dvp.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The three actors that matter for the mechanics are the central counterparty (CCP), the central securities depository (CSD), and the cash settlement system. The CCP sits between buyer and seller after novation, becoming the counterparty to each. The CSD is where securities positions are held in book-entry form and where finality is achieved. The cash system — typically a real-time gross settlement (RTGS) account at a central bank — holds the money leg.

## Novation moves the counterparty risk before settlement

Once a trade is matched, the CCP novates it: the original bilateral contract between buyer and seller is legally replaced by two contracts, buyer-to-CCP and CCP-to-seller. From an engineering standpoint this is important because it changes who your systems are settling against. After novation, the seller delivers to the CCP and the buyer receives from the CCP; neither party settles directly against a name they have to credit-assess.

Novation also enables netting. If a member has bought 10,000 of an instrument and sold 6,000 across the day, the CCP nets that to a single delivery obligation of 4,000. Your settlement instruction generation should run off net positions per instrument per settlement date, not per trade. Building settlement one-instruction-per-trade is a common early design error that inflates settlement volume and fail rates.

## The atomic swap is the whole point

At the CSD on settlement date, the DvP swap is a single conditional operation. The securities leg (debit seller's account, credit buyer's account) and the cash leg (debit buyer's cash, credit seller's cash) either both commit or both roll back. There is no intermediate state where securities have moved but cash has not.

Concretely, the CSD does something equivalent to this inside one transaction boundary:

```python
def settle_dvp(instruction):
    with ledger.transaction() as txn:  # both legs or neither
        if txn.securities_available(instruction.seller, instruction.isin,
                                    instruction.qty) is False:
            raise FailToDeliver(instruction)          # unwind, do not partial
        if txn.cash_available(instruction.buyer,
                              instruction.amount) is False:
            raise FailToReceive(instruction)          # unwind, do not partial

        txn.move_securities(instruction.seller, instruction.buyer,
                            instruction.isin, instruction.qty)
        txn.move_cash(instruction.buyer, instruction.seller,
                     instruction.amount)
        return txn.commit()                            # finality here
```

The `with` block is doing the work that makes this DvP rather than free-of-payment delivery. Because both checks and both moves live in one transaction, a shortfall on either side aborts the whole thing. That is what removes principal risk: the buyer's cash never leaves unless the securities arrive in the same atomic step, and vice versa.

In practice the CSD reserves the buyer's cash first — locking it in the RTGS account — so that by the time the securities leg is checked, the cash side is already guaranteed. This is why the sequence shows the cash leg being reserved before the delivery: it collapses a two-sided availability problem into a single securities-availability check at the moment of settlement.

## Fails are normal, and the design has to expect them

A settlement fail is not an exception in the error-handling sense — it is an expected business outcome that happens on a meaningful fraction of instructions. The most common cause is fail-to-deliver: the seller does not have the securities in place on settlement date, often because a securities loan was recalled or an upstream delivery to them also failed. Fails cascade.

The critical rule your engine must enforce is: **a fail unwinds the swap, it never partial-settles.** Delivering half the securities against full cash would reintroduce exactly the principal-risk exposure DvP exists to prevent. When the securities leg is short, the instruction stays unsettled and rolls to the next cycle as a retry candidate.

```
DvP attempt (T+2)
   |
   +-- securities present? --yes--> atomic swap --> settled (final)
   |
   +-- securities short? ----------> unwind ------> fail-to-deliver
                                        |
                                        +--> recycle to next cycle
                                        +--> buy-in triggered
                                        +--> settlement penalty accrues
```

When a fail persists past a tolerance window, the CCP or the receiving party can initiate a buy-in: they source the securities in the open market at the failing party's expense to make the buyer whole. Separately, settlement-discipline penalties accrue daily against the failing party for the duration of the fail. From an engineering view, both of these are downstream processes keyed off the same fail event, so your settlement engine should emit a durable, queryable "fail" record with the ISIN, the shortfall quantity, the counterparty, and the age of the fail — that record is what the buy-in and penalty systems consume.

## What to get right in the build

A few principles hold up across every DvP settlement system worth trusting:

- **Model the future-dated state explicitly.** "Instructed, awaiting T+2" is a real status that lives for days; do not collapse it into "pending" alongside sub-second states.
- **Net before you instruct.** Generate settlement obligations from net positions per instrument per date, not per trade, or your fail rate and message volume will balloon.
- **Keep the swap atomic in one transaction boundary.** The single most important invariant is that no path can commit one leg without the other. Reserve cash first to simplify the settlement-date check.
- **Treat fails as first-class data, not errors.** Emit durable fail records that buy-in and penalty processes can consume, and never let a fail degrade into a partial settlement.

DvP is conceptually simple — two obligations, settled together or not at all — but the value is entirely in the "or not at all." Get the atomicity and the fail semantics right, and the rest of the settlement stack is bookkeeping around a promise the system can always keep.
