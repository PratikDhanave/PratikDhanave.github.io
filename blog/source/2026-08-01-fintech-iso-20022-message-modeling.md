# Modeling ISO 20022 Payment Messages Without Losing Your Mind

*How to treat pain, pacs, and camt as one typed, schema-driven domain instead of a pile of XML you concatenate by hand.*

Most teams meet ISO 20022 the wrong way: someone opens a `pacs.008` sample in a browser, sees a wall of nested XML, and reaches for string templating. Six months later there is a `buildPacs008()` function that concatenates tags, a QA backlog full of "scheme rejected our file," and no one who can explain why a field is populated the way it is. The standard is verbose, but it is also *rigorously typed*. If you model it as a typed domain from day one, most of the pain disappears and the compiler starts catching the bugs the scheme would otherwise reject at settlement.

This is how I build ISO 20022 handling: schema-first types, a clean internal payment model, and thin adapters that translate between message variants. The messages you care about at first are `pain.001` (a customer telling their bank to pay), `pacs.008` (bank telling the clearing system to move interbank funds), `pacs.002` (the status answer), and the `camt` family (`camt.054` movement notifications, `camt.053` end-of-day statements) that closes the loop for reconciliation.

## Generate types from the schema, never hand-roll them

Every ISO 20022 message is defined by an XSD. Do not treat that XSD as documentation — treat it as your source of truth and generate code from it. Each message flavor has a variant and version (`pain.001.001.09`), and the schemes pin exact versions. Generated bindings give you three things for free: element ordering (ISO 20022 is order-sensitive; a `PmtInf` block out of sequence is an instant reject), cardinality (min/max occurrences), and the constrained primitive types.

Those primitive types are where hand-rolled code quietly bleeds. Amounts are not floats — they are a decimal with a currency attribute and a scheme-bounded fraction digit count. Identifiers are length-bounded strings with character-set restrictions (the payments-relevant `x` character set is far narrower than UTF-8). Encode these as real types:

```
type Amount struct {
    Value    decimal.Decimal  // never float64
    Currency string           // ISO 4217, validated against ccy fraction rules
}

type Max35Text string  // validated: 1..35 chars, restricted charset
```

If `Max35Text` validates on construction, an over-length remittance reference fails in your code, at the boundary, with a useful error — not three hops downstream inside a correspondent bank's parser.

## Keep one canonical model; messages are projections of it

The costly mistake is letting message shapes leak into your core. `pain.001` and `pacs.008` describe the *same* underlying payment from different vantage points, so model the payment once — debtor, creditor, amount, remittance info, references — and treat each message as a *projection* of that canonical object.

```
        ┌──────────────────────┐
        │  Canonical Payment   │
        │  debtor / creditor   │
        │  amount / remittance │
        │  end-to-end id       │
        └──────────┬───────────┘
      project      │      project
   ┌───────────────┼────────────────┐
   ▼               ▼                ▼
pain.001        pacs.008         camt.054
(initiation)  (interbank)     (notification)
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-iso-20022-message-modeling.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The translation from `pain.001` to `pacs.008` is not a field-rename exercise, and this is the part teams underestimate. Your bank sits between the customer instruction and the interbank message, so the adapter *adds* information the customer never supplied: settlement method (`SttlmMtd` — CLRG for a clearing system, INDA/INGA for on-us or agent postings), the clearing system member IDs for both agents, the interbank settlement date, and charge-bearer allocation. Model the adapter as an explicit function `Canonical + BankContext → pacs.008` so it is obvious which fields come from the customer and which your bank injects. Reviewers can then reason about correctness instead of guessing.

## References are the backbone — design them deliberately

ISO 20022 gives you a layered set of identifiers, and reconciliation lives or dies on how you use them. Three matter most:

- **End-to-End ID** — set by the originator, preserved *unchanged* across every hop and echoed back in `pacs.002` and `camt` notifications. This is your correlation key. Make it a deterministic function of your internal payment ID so any inbound message maps straight back to a row without a lookup table.
- **Transaction ID** — assigned by the instructing agent, unique on the interbank leg.
- **UETR** — a UUIDv4 that stays constant end-to-end and is the anchor for cross-border tracking.

Treat these as first-class typed fields with explicit generation rules, not strings you format inline. A single rule — "End-to-End ID = `PAY-` + internal id, always" — removes an entire category of reconciliation breaks, because every status and statement message that comes back is self-describing.

Message-level identity is separate and equally load-bearing. Each message carries a `MsgId` in its group header, and schemes treat it as an idempotency key inside a business window. Emit the *same bytes* on a retry and a well-behaved scheme deduplicates; emit a fresh `MsgId` and you risk a double payment. So `MsgId` must be deterministic per logical send and stored, not regenerated on each attempt. This is the single most important reliability property in the whole pipeline.

## Validate in layers, and reconcile on the way back

Do not rely on the scheme to be your validator. Run three tiers before anything leaves your boundary:

1. **XSD structural** — element order, cardinality, datatypes. Catches the mechanical errors.
2. **Scheme rulebook** — cross-field constraints the XSD can't express (e.g. `SttlmMtd = CLRG` requires clearing-system agent IDs; certain charge-bearer codes are barred on some rails). Encode these as explicit predicate checks with rule IDs in the error.
3. **Business** — sanctioned-country checks, limits, currency-rail eligibility.

Fail at tier 1 or 2 in your own system and you get a precise error; fail at the scheme and you get an opaque `pacs.002` rejection hours later.

The return path is where the typed model pays off. A `pacs.002` carries a group status and per-transaction `TxSts` (`ACSC` settled, `RJCT` rejected with a reason code, `ACSP` pending). You match it to the original by End-to-End ID and drive a state machine — never mutate the payment blindly. Then `camt.054` debit/credit notifications confirm the actual account movement intraday, and the `camt.053` end-of-day statement is the authoritative record you reconcile your ledger against. Match `camt.053` entries back by reference, assert your expected postings equal the bank's booked entries, and route any break to an exceptions queue. Do this and reconciliation becomes a property you *verify* every day rather than a fire drill you run when finance notices the numbers are off.

## What actually makes this maintainable

The teams that stay sane share three habits. They generate bindings from pinned schema versions and check the generated code in, so a scheme's version bump is a visible, reviewable diff. They keep the canonical model free of any single message's quirks, so adding a new rail is a new adapter, not a refactor. And they make every identifier and validation rule explicit and typed, so the knowledge lives in code instead of in the one engineer who read the rulebook. ISO 20022 is verbose, but it is not vague — lean into its type system and it will hold your payments together instead of fighting you.
