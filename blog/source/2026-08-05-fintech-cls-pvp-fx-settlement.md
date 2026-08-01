# Payment-versus-Payment: Settling FX Without Principal Risk

*How matched-leg submission, net pay-in scheduling, and conditional simultaneous settlement remove Herstatt risk from cross-currency trades.*

Every spot FX trade is two payments in two different currencies, and almost always across two different timezones. One party owes dollars, the other owes euros. The dangerous window opens the moment you release your leg before you have irrevocably received the other. If your counterparty fails in that gap, you are out the full principal — not a mark-to-market difference, the entire notional. This is settlement risk in its rawest form, and the engineering answer to it is payment-versus-payment (PvP): a settlement system that guarantees both legs move together or neither moves at all.

This post walks through how a PvP settlement service is built as a pipeline: matched-leg intake, a settlement snapshot, net pay-in funding, a conditional simultaneous debit/credit, and net pay-out. The mechanics are more subtle than "swap two numbers atomically," because the money lives in central-bank accounts the settlement service does not directly control.

## The window that PvP closes

Consider a trade where Member A sells USD to buy EUR, and Member B takes the other side. Settled naively across timezones, the sequence looks like this:

```
Time ->   Asia close            Europe close           US close
Member A:  [pays USD] ----------------- (waiting) ------ [receives EUR]?
Member B:  (holds EUR) --------- [pays EUR] ----------- [receives USD]?

           ^ A has paid its leg    ^ B still solvent?   ^ if B failed here,
             and is now exposed       unknown              A loses full USD notional
             to B's full default
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-cls-pvp-fx-settlement.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The gap between "A has paid" and "A has received" is the principal-risk window. PvP collapses it to zero by making both transfers conditional on each other inside a single settlement processor. Neither leg is final until both are funded and both can be booked in the same instant.

## Matched legs and the settlement snapshot

The first engineering constraint is that a PvP system only settles what it can prove is a two-sided, agreed trade. Each member submits its leg independently; the system pairs them by a shared trade reference, matches economic terms (currency pair, amount, value date, direction), and only then admits the trade into a settlement cycle.

Matching must be idempotent and deterministic. Members retransmit; networks duplicate. Key each submitted leg by `(submitter, trade_ref, value_date)` and treat a re-submission of identical terms as a no-op, a submission of *different* terms for the same reference as a mismatch alert. Once matching completes for a value date, the system takes a **settlement snapshot**: a frozen set of matched obligations that will settle in this cycle. Trades arriving after the snapshot roll to the next cycle. This freeze is what makes the downstream net figures stable enough to fund against.

## Net pay-in: fund your short currency, not every trade

A member might have thousands of trades settling on the same value date. Funding each gross would require enormous intraday liquidity. Instead the system nets: for each member and each currency, it sums all obligations into a single net position.

```python
# per member, per currency: net of everything settling this cycle
net = defaultdict(lambda: defaultdict(int))  # net[member][ccy] in minor units
for t in snapshot.trades:
    net[t.buyer][t.buy_ccy]  += t.buy_amount    # long: they receive
    net[t.buyer][t.sell_ccy] -= t.sell_amount   # short: they must fund
    net[t.seller][t.sell_ccy] += t.sell_amount
    net[t.seller][t.buy_ccy]  -= t.buy_amount

# a member funds only currencies where net < 0 (its "pay-in")
pay_in = {(m, c): -amt for m, ccys in net.items()
                       for c, amt in ccys.items() if amt < 0}
```

Only the negative net positions become **pay-in obligations**. A member funds the currencies it is net-short and receives the currencies it is net-long. This can reduce required funding by an order of magnitude versus gross settlement, which is the whole liquidity argument for PvP. The system publishes a pay-in *schedule* — deadlines by currency, staggered to follow each currency's own RTGS operating hours — and members move central-bank money into the settlement service's accounts against it.

## The conditional simultaneous settlement

Here is the invariant at the core of the design: a trade settles only if **both** legs are fully funded, and the two book entries are applied as one indivisible unit.

```
for each matched trade in the snapshot:
    if funded(buyer, sell_ccy)  and funded(seller, buy_ccy):
        atomically:
            debit(buyer,  sell_ccy);  credit(seller, sell_ccy)
            debit(seller, buy_ccy);   credit(buyer,  buy_ccy)
    else:
        leave trade unsettled  # rolls to a later attempt or fails the cycle
```

Two properties make this safe. First, **PvP itself**: the two currency movements for a trade commit together, so there is no instant where one member has given value without receiving it. Second, a **positional risk control** — no member's settlement-account balance in any currency is allowed to go negative during the cycle, and short positions are capped. That means the system can settle trades progressively as funding arrives, always maintaining the invariant that booked positions are backed by real money, without waiting for every last pay-in.

Settlement therefore runs as an algorithm over the snapshot, not a single transaction. It repeatedly tests which trades are now fundable given balances received so far, settles those, and recomputes. Gridlock — where A is waiting on B's pay-in and B is waiting on A's — is resolved by finding a subset that can all settle simultaneously, the same class of problem an RTGS queue resolver solves.

## Pay-out, and what engineers build around it

Once a currency's obligations are settled, the member's net-long balances are paid out back to their nostro accounts via that currency's RTGS. Pay-out is deliberately last: the service holds funds until settlement finality is certain, then disburses net.

Around this core, real systems need:

- **Idempotent, replayable messaging.** Every pay-in, settlement, and pay-out event carries a stable identifier so a reconnect or replay never double-books. The settlement ledger must be the single source of truth and safe to rebuild from its event log.
- **Currency-aware time.** Cutoffs, pay-in deadlines, and finality are per-currency because each rail keeps its own hours. Model value dates and deadlines in each currency's calendar, never one global clock.
- **Deterministic reconciliation.** At end of cycle, sum of pay-ins minus pay-outs must equal zero per currency across all members. Any residual is a break to investigate before finality is declared, not after.
- **Graceful failure.** If a member misses a pay-in, its trades are excluded from that cycle rather than settled unfunded. Downstream systems must treat "matched but not settled" as a first-class state, not an error.

The lesson that transfers to any money-movement system: eliminating principal risk is not about moving faster, it is about making two transfers *conditional on each other*. Net where you can to save liquidity, snapshot before you fund so the numbers hold still, and never let a booked position exist without the money behind it. PvP is simply that discipline enforced at the scale of the global FX market.
