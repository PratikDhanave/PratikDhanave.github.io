# Threading a UETR Through SWIFT MT-to-MX Migration

*How to parse legacy MT103/MT202 fields, map them to MX pacs equivalents during coexistence, and thread a gpi UETR end-to-end so a cross-border payment stays trackable across correspondent hops.*

---

Cross-border payments are moving from the old block-and-tag MT message format to structured ISO 20022 MX messages. The awkward part is that the migration is not a flag day. For a long coexistence window your systems have to speak both, translate between them without losing meaning, and keep a single tracking identifier stable across every correspondent hop. Get the identifier wrong and a payment that is technically fine becomes operationally invisible: nobody can answer "where is my money?" until it lands.

This post is about the engineering that makes that window survivable — parsing MT, mapping it to MX, and threading one **UETR** (Unique End-to-end Transaction Reference) through the whole chain so gpi tracking actually works.

## Two message worlds, one coexistence window

The legacy world is line-oriented text. An MT103 (single customer credit transfer) or MT202 (bank-to-bank cover) is a set of fields keyed by numeric tags inside delimited blocks. The new world is XML with a schema: `pacs.008` for the customer/interbank credit transfer, `pacs.009` for the financial-institution transfer, `pacs.002` for status reports. Any bank in the chain might be sending MT while the next one expects MX, so a payment can be re-formatted several times before it reaches the beneficiary.

The identifier that survives all of this is the UETR: a UUID version 4 generated once at origination and carried unchanged on every message about that payment. Each participant reports status against that UETR to a shared tracker, so the observability plane can reconstruct the full journey even though the underlying format changed mid-flight.

```
Originator ──MT103 / pacs.008 (UETR:x)──▶ Correspondent ──pacs.008 (UETR:x)──▶ Beneficiary
     │                                          │                                    │
     │ status: initiated                        │ status: in-transit                 │ status: credited
     ▼                                          ▼                                    ▼
     └──────────────────────── gpi Tracker  (keyed on the same UETR) ────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-swift-mt-mx-gpi.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The rule your code must never break: **the UETR is assigned once and copied, never regenerated.** A correspondent that mints a fresh UETR when it re-formats the message severs the trace. In MX it lives in the transaction group header; in MT it rides in field 121 of the block-3 user header.

## Parsing MT: the field-tag grammar

An MT message is four blocks. Block 4 is the payload — a sequence of `:tag:value` lines terminated by `-`. Field tags like `:20:` (sender's reference), `:32A:` (value date / currency / amount), `:50K:` (ordering customer), `:59:` (beneficiary), and `:71A:` (charge bearer) each have their own sub-grammar. Field 32A, for example, is a fixed layout: six digits of date, three letters of currency, then a decimal amount using a comma as the separator.

A defensive parser treats each field as a typed extractor rather than a blob of text:

```python
def parse_32a(value: str) -> Amount:
    # YYMMDD + 3-letter currency + amount (comma decimal)
    date = value[:6]
    currency = value[6:9]
    raw = value[9:].replace(",", ".")
    minor = int(round(Decimal(raw) * 10 ** exponent_for(currency)))
    return Amount(value_date=to_iso(date), currency=currency, minor_units=minor)
```

Two things earn their keep here. First, amounts become **integer minor units** immediately, so no float ever touches money. Second, the currency's exponent (2 for USD, 0 for JPY, 3 for BHD) comes from a table, not an assumption — MT hides this and a naive `* 100` silently corrupts zero-decimal currencies.

## Mapping MT103 to pacs.008

Once fields are typed, mapping to MX is a field-by-field transform into the XML tree. The correspondences are mostly clean, but a few are lossy in one direction and you must decide the policy up front.

| MT103 field | pacs.008 element | Note |
|---|---|---|
| `:20:` sender ref | `PmtId/InstrId` | instruction-level id |
| block-3 `:121:` | `PmtId/UETR` | the tracking anchor |
| `:32A:` | `IntrBkSttlmDt` + `IntrBkSttlmAmt` | split into date and typed amount |
| `:50K:` | `Dbtr` + `DbtrAcct` | structured party |
| `:59:` | `Cdtr` + `CdtrAcct` | structured party |
| `:70:` remittance | `RmtInf/Ustrd` | free-text remittance |
| `:71A:` | `ChrgBr` | code: DEBT / CRED / SHAR |

The hard direction is MX-to-MT. ISO 20022 carries richly structured names, addresses, and structured remittance that legacy MT fields cannot hold at full length. When you down-convert you will **truncate**, and truncation that silently drops a beneficiary address line is a compliance problem, not a formatting nit. The safe pattern is to persist the full MX payload as the record of truth, emit the truncated MT for the hop that needs it, and flag the message as "truncated on down-conversion" so the receiving side knows the canonical version exists upstream.

## Threading the UETR for gpi tracking

gpi turns a chain of independent messages into one observable payment. Every bank in the route is expected to post a status against the UETR — a `pacs.002`-style status report or a tracker API call — as the payment passes through. The statuses form a small state vocabulary: `ACCP` accepted, `ACSP` in progress, `ACSC` settled/credited, `RJCT` rejected. The tracker keys everything on the UETR and exposes the end-to-end view.

The engineering discipline is idempotency at two layers. The UETR gives you a stable key for the *payment*; you still want a stable key for each *status event* so a retried tracker post does not double-count. A clean scheme is to derive the event key from `(UETR, participant-BIC, status-code, settlement-date)`, so the same bank reporting `ACSP` twice collapses to one tracker entry.

```python
def status_event_key(uetr, bic, status, sttlm_date):
    return sha256(f"{uetr}|{bic}|{status}|{sttlm_date}".encode()).hexdigest()
```

Because the UETR is format-agnostic, this works identically whether the hop that produced the status spoke MT or MX. That is the whole point: the tracker does not care about the wire format, only that the identifier is preserved.

## Failure modes to design against

- **UETR regeneration.** The single worst bug. Enforce it: on ingest, if the inbound message already carries a UETR, it is immutable through re-formatting; only a true origination may mint one.
- **Charge-bearer drift.** `SHAR` vs `DEBT` changes who pays correspondent fees and therefore the amount credited. Map it explicitly; never default it.
- **Value-date vs settlement-date confusion.** MT 32A carries a value date that must map to `IntrBkSttlmDt`, not the message timestamp. Getting this wrong breaks nostro reconciliation downstream.
- **Character-set narrowing.** MX permits a broader character set than MT's SWIFT-X. Down-conversion needs a deterministic transliteration table, applied and logged, not a lossy encode-and-pray.

## What to build

Treat the migration surface as three cooperating components rather than one translator. A **codec layer** parses MT into typed field objects and validates MX against the schema, so bad messages fail at the edge. A **mapping layer** transforms between the typed MT model and the MX tree with an explicit, tested table and a truncation policy that preserves the canonical payload. A **tracking layer** owns the UETR invariant and posts idempotent status events to the gpi tracker.

Kept separate, each is testable in isolation: golden-file tests for the codec, round-trip property tests for the mapping (MT to MX to MT should lose only what your policy documents as lossy), and idempotency tests for the tracker. The coexistence window will last longer than anyone plans for, so the code that carries you through it should read like infrastructure — boring, typed, and impossible to accidentally break the one identifier that keeps every payment findable.
