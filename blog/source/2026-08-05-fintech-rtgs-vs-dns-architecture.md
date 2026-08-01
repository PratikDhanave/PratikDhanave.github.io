# RTGS vs Deferred Net Settlement

*Two ways to move interbank money, and the engineering tradeoff that decides which one you build: settle every payment gross and pay in liquidity, or net at a window and carry settlement risk.*

Every interbank settlement system answers one question: when does a payment become final, and what does that finality cost in liquidity? There are only two honest answers. You either settle each payment individually, in full, the moment it clears — a real-time gross settlement (RTGS) system — or you accumulate obligations over a window and settle a single netted position per participant — a deferred net settlement (DNS) system. Almost every scheme you will integrate with is one of these two shapes, or a hybrid that borrows from both.

The choice is not academic. It changes the data model, the failure modes, the liquidity a bank must pre-fund, and the algorithms you need to keep the system from seizing up. This post walks the two architectures from an engineering seat: what each one guarantees, where each one hurts, and how the hard parts — gridlock in RTGS, the exposure window in DNS — are solved.

## The gross lane: settle one payment, right now

In RTGS, a payment instruction is settled against the sending bank's balance at the central settlement account the instant it is processed. There is no batch, no offsetting, no netting. Each instruction debits the payer bank and credits the payee bank as an atomic, irrevocable ledger move. Once posted, it is final — no clawback, no unwind.

The upside is that settlement risk is essentially zero. The moment the receiving bank sees the credit, the money is theirs. This is why high-value and time-critical payments run over RTGS rails: nobody wants a billion-dollar transfer to be provisional until 5pm.

The cost is liquidity. To settle gross, the sending bank must have the full amount in its settlement account *at the moment of processing*. A bank sending a large payment before its own incoming payments arrive will fail the balance check and the payment queues. Multiply that across thousands of participants trying to pay each other, and you get the RTGS engineer's central problem: gridlock.

```
RTGS: per-payment finality, at the price of liquidity

  Bank A instruction ──► [ liquidity check ]
                              │
                     balance >= amount ?
                        │            │
                       yes           no
                        │            │
                        ▼            ▼
                  post & settle   enter QUEUE
                  (final, irrev.)   (waiting for
                        │            incoming funds)
                        ▼            │
                  credit Bank B     └──► gridlock resolver
                                          scans queue for
                                          a settle-able cycle
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-rtgs-vs-dns-architecture.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Gridlock, and the offsetting algorithm that breaks it

Gridlock is a liquidity deadlock. Bank A cannot pay Bank B until B pays A, and B cannot pay A until A pays B. Each payment sits at the head of a queue waiting for liquidity that will only arrive when the other payment settles. Nothing is technically wrong — every instruction is valid — but the system stops moving.

The naive fix is more liquidity: make every bank pre-fund enough to never queue. That is enormously expensive; that cash sits idle. So real RTGS systems run a periodic *gridlock resolution* pass — an offsetting algorithm that looks for a set of queued payments which, if settled together, leave every participant's balance non-negative even though no single payment could settle alone.

Concretely, the resolver treats queued instructions as a graph, searches for a cycle (or a larger simultaneous subset) whose net effect is fundable for all parties, and settles that subset in one atomic step. It is a small optimization problem run on a timer:

```
queued: A→B 100, B→C 80, C→A 90   (balances: A=20, B=10, C=0)

  settle any one alone?  no — each sender is short.
  settle all three simultaneously?
     A: -100 +90 = -10  ... still short by 10
  drop A→B, settle B→C + C→A?
     B: -80      = short
  inject A's queued incoming first, re-check net positions...
     resolver finds fundable subset → atomic multilateral offset
```

The engineering point: an RTGS core is not just a ledger with a balance check. It is a ledger, a priority queue, and a periodically-invoked constrained solver that recovers throughput without abandoning gross finality. Payments also carry priority classes so that a stuck high-priority instruction can bypass or reorder the queue.

## The net lane: accumulate, then settle once

DNS inverts the tradeoff. Instead of settling each payment, the system records obligations throughout a cycle and computes, at a defined window, a single net position per participant: the sum of everything you owe minus everything owed to you. Only those net figures move across the settlement account, usually once or a few times per day.

The win is liquidity efficiency. If a bank sends 10,000 payments totalling a billion and receives roughly the same, its net position might be a few million. It only needs to fund that few million, not the gross billion. Netting collapses a dense mesh of obligations into one number per bank, and that number is small.

```
DNS: accumulate obligations, settle the net at the window

  during the cycle          at the cutoff snapshot
  ┌───────────────────┐     ┌────────────────────────┐
  │ A→B 100  A→C  40  │     │  net(A) = -140 + 60 = -80│
  │ B→A  60  B→C 200  │ ──► │  net(B) = +100+... = ... │
  │ C→A ... many ...  │     │  net(C) = ...            │
  └───────────────────┘     └────────────────────────┘
        gross mesh              one settle-able figure
                                per participant
                                       │
                                       ▼
                          single settlement transfer
                          (net debtors → net creditors)
```

The cost is settlement risk, and it lives in the exposure window. Between the moment a payment is accepted and the moment the net position settles, the receiving bank may have already given value to its customer on the strength of a payment that is not yet final. If a participant fails before the window settles, its obligations may need to be unwound — and unwinding one bank's payments changes everyone else's net positions, potentially cascading. This is the systemic risk DNS designers spend all their effort containing.

## Containing DNS risk: caps, collateral, and unwind rules

Three mechanisms do the work. First, **net debit caps**: a hard limit on how negative any participant's running net position may go during the cycle. When a payment would breach the cap, it is rejected or held, exactly like the RTGS liquidity check but applied to the accumulated position rather than the live balance. Second, **collateral and loss-sharing pools**: participants post collateral sized so that if the largest (or largest few) net debtors default, the pool covers the settlement without unwinding anyone. Third, explicit **unwind procedures**: a deterministic rule for which payments get removed and how remaining positions are recomputed if settlement still cannot complete.

Engineered together, these turn "settle risk" from an open-ended exposure into a bounded, pre-funded one. The cap enforcement is the interesting piece structurally: it means a DNS system, despite settling late, still runs a real-time check on every incoming instruction. You cannot defer the risk control just because you defer the settlement.

## Which one you build, and the hybrids

The rule of thumb: RTGS for high-value, time-critical, must-be-final-now flows; DNS for high-volume, low-value retail flows where liquidity efficiency matters more than instant finality. A large-value transfer between banks goes gross. A day's worth of card or ACH transactions nets.

Modern designs increasingly refuse to choose. Hybrid systems accept payments continuously like RTGS but run frequent offsetting cycles — every few minutes rather than once a day — so a payment is either settled gross immediately or settled net moments later, shrinking the exposure window toward zero while keeping liquidity demand low. From an implementation view a hybrid is an RTGS core whose gridlock resolver runs aggressively and continuously, blurring into a DNS engine.

If you take one thing from this: settlement finality and liquidity are a conserved tradeoff, not a feature you can maximize on both axes. Every mechanism in this post — queues, offsetting solvers, net debit caps, collateral pools — is an attempt to buy back a little of whichever side your chosen architecture gave away.
