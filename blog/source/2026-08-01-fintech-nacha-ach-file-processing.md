# Building a NACHA ACH File Processor: Records, Hash Totals, and Return Codes

*Model the fixed-width record hierarchy, warehouse entries until their effective date, and turn R-series returns into automated re-presentment.*

ACH is deceptively simple to describe and unforgiving to implement. You assemble a text file, hand it to your originating bank, and money moves a day or two later. But the file format is fixed-width and positional, the totals are validated with a hashing scheme that predates most of us, and the interesting engineering is not in the happy path at all — it is in what happens when an entry comes back three days later carrying a two-character code that decides whether you retry, update a mandate, or write the debt off. This post walks through the record model, the control-total math, the effective-date warehouse, and the return/NOC handling that a production ACH processor has to get right.

## The four-level record hierarchy

A NACHA file is a flat stream of 94-character lines, but those lines form a strict nested structure enforced by a leading one-digit record type code. There are exactly four levels plus control records.

```
1  File Header  (immutable routing + creation timestamp)
  5  Batch Header      (SEC code, company, effective entry date)
    6  Entry Detail    (routing, account, amount, trace number)
      7  Addenda       (remittance / return / NOC info)
    6  Entry Detail
  8  Batch Control     (entry count, hash, debit + credit totals)
5  Batch Header ...
8  Batch Control
9  File Control        (batch count, block count, grand totals)
```

Each batch groups entries that share a Standard Entry Class (SEC) code — `PPD` for consumer debits/credits, `CCD` for corporate, `WEB` for internet-authorized, `TEL` for phone. The SEC code matters far beyond labeling: it drives which return windows apply and whether you needed an authorization record on file. Model the hierarchy as a real tree in your domain layer, not as a list of lines. Parsing produces `File → Batch[] → Entry[] → Addenda[]`; serialization walks it back down. Keep the raw 94-char line alongside each parsed node so you can round-trip byte-for-byte, because banks reject files on the smallest positional drift.

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-nacha-ach-file-processing.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The file is also block-aligned: records are grouped into blocks of ten, and the File Control record's block count must reflect a file padded with all-nines filler lines to the next multiple of ten. This is trivial to forget and a common source of same-day rejects.

## Control totals: the entry hash nobody explains

Every Batch Control (type 8) and the File Control (type 9) carry totals that the receiving bank recomputes and compares. Three of them are obvious — total debit amount, total credit amount, entry/addenda count. The fourth, the *entry hash*, is the one that trips people up.

The entry hash is **not** a cryptographic hash. It is the sum of the first eight digits (the routing number without its check digit) of every Entry Detail record, truncated to the low-order ten digits. That is the entire algorithm:

```python
def entry_hash(entries) -> str:
    total = sum(int(e.rdfi_routing[:8]) for e in entries)
    return str(total % 10_000_000_000).zfill(10)
```

The batch hash sums its entries; the file hash sums the batch hashes (with the same 10-digit truncation). It is a cheap integrity check that catches truncated or reordered files without any real cryptography. The lesson for implementers: compute these totals as a fold over your entry tree at serialization time, never by hand-maintaining running counters as you append entries — the counter approach drifts the moment an entry is reversed or dropped, and a wrong hash bounces the whole file.

## Warehousing until the effective entry date

The Batch Header carries an *effective entry date* — the banking day on which the RDFI should post the entry. Originators routinely submit files early, so a processor cannot simply transmit everything the instant it is built. You warehouse.

A submitted entry sits in a pending store keyed by effective date. A scheduler wakes on each banking day, resolves that day's window against a holiday calendar, and releases the entries whose effective date has arrived into the outbound file for the ODFI. Two rules make this correct:

- **Banking-day math, not calendar math.** Effective dates skip weekends and Federal Reserve holidays. Adding "two days" naively will schedule a settlement on a day the rail is closed and the file will be redated by your bank — silently shifting your reconciliation.
- **Cutoff awareness.** Each transmission window has a hard cutoff. An entry that misses today's cutoff rolls to the next window, not into the void. Same-day ACH adds multiple intraday windows with their own cutoffs and dollar caps, which is really just a warehouse with a shorter release interval.

Treat the warehouse as the single point where a submitted entry becomes an irrevocable transmitted entry. That transition is where you snapshot the ledger reservation and where idempotency has to hold: re-running the release job for a date must never emit an entry twice.

## Returns and NOCs: the state machine that matters

Days after settlement, the RDFI can send entries back. Returns arrive as their own inbound NACHA files, where each returned item is an Entry Detail plus an addenda carrying an **R-series code**. Notifications of change arrive the same way with **C-series codes**. Correlating them back to the original entry — by trace number — and dispatching on the code is the core of the whole system.

```
Return code   Meaning                     Automated action
-----------   -------------------------   --------------------------
R01           Insufficient funds          Re-present (soft, retry)
R09           Uncollected funds           Re-present (soft, retry)
R02           Account closed              Stop; flag payment method
R03           No account / unable to      Stop; flag payment method
R10           Customer advises unauth.     Stop; do not retry
C01           Incorrect account number     Apply NOC; update on file
C05           Incorrect transaction code   Apply NOC; update on file
```

The classification split is the whole game. **Soft returns** (R01 insufficient funds, R09 uncollected) mean the account is real but the money was not there — these are re-presentable, and the rules cap you at two re-presentments within a bounded window per original authorization. Build a retry-budget guard so a runaway job cannot re-present the same debit five times and rack up return fees. **Hard returns** (R02, R03, R04) mean the account is unusable — stop immediately, mark the payment method dead, and route to dunning. **Unauthorized returns** (R05, R07, R10, R11) carry a 60-day consumer window and legal weight; never auto-retry them, and quarantine the payment method.

Notifications of change are not returns — the entry *posted*. A C01/C05 is the RDFI telling you the account or routing was slightly wrong and to fix it for next time. Applying the NOC means updating the stored account record so the next debit uses corrected data; ignoring NOCs eventually escalates to fines. Model both R and C as inbound events that transition one entry through a lifecycle:

```
submitted → warehoused → transmitted → settled
                                          ├─ returned(R01) → re-presented → settled
                                          ├─ returned(R02) → written-off
                                          └─ NOC(C01)      → corrected → (next cycle)
```

Every transition should post a corresponding ledger movement — a settled entry credits, a return reverses, a re-presentment re-debits — so that the money ledger and the ACH state machine never disagree. The interactive diagram above traces these transitions: the fork at settlement, the soft-return path into re-presentment, and the terminal write-off.

## What to get right first

If you are building this from scratch, the ordering that saves pain is: get byte-exact serialization and the entry-hash fold correct before anything else, because a malformed file never even enters the return flow. Then build the effective-date warehouse on banking-day math, since a wrong effective date corrupts every downstream reconciliation. Only then wire the return/NOC handler — but design its code table as data, not a switch statement, because the R and C code sets grow and their required actions are regulated, not up to you. An ACH processor is ultimately a small set of pure functions (parse, hash, classify) wrapped around one scheduler and one durable state machine — keeping those boundaries clean is what lets you sleep while money moves overnight.
