# Nostro/Vostro Reconciliation, From the Ledger Up

*Reconciling correspondent-bank balances with mirror-account bookkeeping, camt.053 matching, value-date breaks, and unreconciled-item aging.*

---

## Two views of the same money

When your institution holds an account at a correspondent bank so you can settle in a currency you do not clear yourself, that account is a **nostro** ("our account with you"). The same account, seen from the correspondent's books, is a **vostro** ("your account with us"). There is exactly one pool of money, but two ledgers describe it, and they never agree in real time.

The whole discipline of nostro reconciliation exists because those two ledgers drift. You book an entry the instant you *instruct* a payment; the correspondent books it when the money actually *moves*, which may be seconds, hours, or a value-date later. Reconciliation is the daily proof that every difference between the two views is explainable and shrinking, not a lost or duplicated payment.

The design starts with a bookkeeping choice: for every nostro account you keep an internal **mirror account** that shadows what you *expect* the correspondent's balance to be. You post to the mirror from your own payment events, then compare the mirror against the correspondent's actual statement.

```
  YOUR BOOKS                         CORRESPONDENT'S BOOKS
  ----------                         ---------------------
  payment event
      |
      v
  +-----------+   expected           +-----------------+
  |  mirror   |   postings           | actual postings |
  |  ledger   |                      |  (their vostro) |
  +-----------+                      +-----------------+
       \                                    /
        \        end of day (camt.053)     /
         \                                /
          v                              v
        +--------------------------------+
        |        matching engine         |
        +--------------------------------+
          |          |          |
       matched   value-date   missing
                   break       item
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-nostro-vostro-reconciliation.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Mirror-account bookkeeping

The mirror is an ordinary double-entry sub-ledger, but its counterparty is a *prediction*. When you release an outbound payment, you debit a customer or internal account and credit the nostro mirror — asserting "we expect our balance at the correspondent to fall by this amount." When you receive an inbound credit advice, you do the reverse.

The critical detail is that every mirror posting must carry the fields you will later match on:

```python
@dataclass(frozen=True)
class MirrorEntry:
    nostro_id: str          # which correspondent account
    direction: str          # "debit" | "credit"
    amount: Decimal
    currency: str
    value_date: date        # when funds are expected to settle
    our_reference: str      # end-to-end id we controlled
    instruction_id: str     # pacs/MT reference we sent
    booked_at: datetime
```

`our_reference` matters more than anything else. If you stamp a stable, unique reference on the outbound instruction and echo it into the mirror, the correspondent's statement will usually return it, and matching becomes a key lookup instead of a fuzzy guess. Reconciliation quality is decided at *payment initiation*, not at end of day.

## What you reconcile against: camt.053

The correspondent sends actuals as an ISO 20022 **camt.053** end-of-day statement (its intraday sibling is camt.052; individual debit/credit notifications arrive as camt.054). A camt.053 is a structured statement with an opening balance, a list of entries, and a closing balance. Each entry carries a status (`BOOK` for settled, `PDNG` for pending), an amount, a booking date, a value date, and a set of references under `Refs` — ideally including the `EndToEndId` you originally sent.

Parsing it, you normalise each statement entry into the same shape as a mirror entry:

```python
def to_statement_entry(ntry) -> StatementEntry:
    return StatementEntry(
        amount=Decimal(ntry.Amt.text),
        currency=ntry.Amt.get("Ccy"),
        direction="credit" if ntry.CdtDbtInd.text == "CRDT" else "debit",
        value_date=parse_date(ntry.ValDt.Dt.text),
        their_reference=ntry.Refs.AcctSvcrRef.text,
        end_to_end=find(ntry, "EndToEndId"),
        status=ntry.Sts.text,   # BOOK | PDNG | INFO
    )
```

Two normalised streams — mirror entries and statement entries for the same account and date — are the entire input to the matching engine. Balance reconciliation (opening + entries == closing) is a cheap sanity check you run first: if the correspondent's own arithmetic does not tie out, stop and query before matching anything.

## The matching engine

Matching runs in passes, from strictest to loosest, removing matched pairs from both pools as it goes.

1. **Exact reference match** — pair a mirror entry and a statement entry sharing `EndToEndId`, same amount, same currency, same direction. This clears the bulk of well-behaved traffic.
2. **Reference + tolerance** — same reference and direction, amount within a small tolerance (correspondent fees deducted from the principal are the usual cause). The residual becomes a separate fee line, not a break.
3. **Attribute match** — no usable reference, so pair on amount + currency + direction + value date within a narrow window. This is where false pairs creep in, so require uniqueness: if two candidates tie, leave both unmatched rather than guess.

Whatever survives all passes lands in one of three buckets:

- **Matched** — a mirror entry and a statement entry agree on all material fields. No action.
- **Value-date break** — they agree on amount, direction and reference but disagree on value date. The money is real; only the *timing* differs. These self-resolve once the later date arrives, so they are tracked, not escalated.
- **Missing item** — an entry exists on one side with no partner. A statement entry with no mirror is an *unexpected* movement (an incoming payment you had not booked, or a fee); a mirror entry with no statement line is a *pending* payment the correspondent has not yet posted.

## Value-date breaks and the timing problem

Value-date breaks are the reason naive reconciliation drowns in false alarms. You book the mirror on the instruction date; the correspondent values the entry two business days forward. On day one the pair looks like two half-matched missing items. A matching engine that lacks a value-date concept will flag both, an operator will investigate, and by the time they do the entry has already settled.

The fix is to make value date a first-class matching dimension. When amount, direction and reference agree but value dates differ, classify the pair as a **timing break** with an *expected resolution date*. Suppress it from the investigation queue until that date passes; only if it is still unresolved afterward does it graduate to a genuine break. This single rule is the difference between an operations team chasing real losses and one drowning in payments that were always going to settle tomorrow.

## Aging and the investigation queue

Every true break — a missing item that is not merely a timing difference — gets a row in an **aging** structure keyed by age band: 0–2 days, 3–5, 6–30, 30+. Age is measured from the entry's value date, not from when reconciliation noticed it, so a break cannot hide by being detected late.

Aging drives two things. First, **provisioning**: an unmatched debit that is 30 days old is a probable loss and should be reserved against, so finance needs the aged inventory, not just a count. Second, the **investigation queue**: each break carries a machine-readable reason (`no_statement_line`, `unexpected_credit`, `amount_mismatch`) and, where possible, a suggested action — issue a camt.056 recall, send an MT n99 free-format query to the correspondent, or auto-book an unexpected credit into a suspense account pending identification.

The engineering goal is not zero breaks; correspondent banking guarantees breaks. The goal is that every break is **explained, aged, and either self-resolving or actively worked** — and that the aged, unexplained tail stays small and gets smaller. A reconciliation system that produces a clean "everything matched" report every day is almost always a system that is silently dropping the items it could not classify.
