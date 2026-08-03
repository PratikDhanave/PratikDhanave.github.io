# Building a FATCA/CRS Tax Reporting Pipeline

*Classify account tax residency and generate withholding and FATCA/CRS reporting files.*

Tax reporting is one of those obligations that looks like a form-filling exercise until you try to build it. A financial institution has to tell tax authorities, once a year, which of its account holders are reportable, in which jurisdictions, and how much income and withholding attaches to each. FATCA covers US persons; CRS is the OECD's multilateral version covering everyone else. Domestically in the US you also emit 1099 forms. The forms differ, the schemas differ, the deadlines differ — but underneath they are the same pipeline: classify residency, compute amounts, generate structured files, submit, and reconcile the acknowledgements.

The mistake teams make is treating each regime as a separate reporting job bolted onto the ledger at year end. That produces three parallel batch scripts that each re-derive residency slightly differently and drift out of agreement. The better model is a single pipeline where residency is computed once and every downstream file is a projection of it.

```
  self-cert ┐
            ├─▶ residency ─▶ withholding ─▶ ┬─▶ 1099 batch ─┐
  account ──┘   classifier    engine        └─▶ CRS XML ─────┴─▶ tax authority
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-fatca-crs-tax-reporting.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Residency is a classification, not a country field

The tempting design is a single `tax_country` column on the account. It is wrong for two reasons. First, an account holder can be tax-resident in more than one jurisdiction at once, and CRS requires you to report to *each* reportable jurisdiction. Second, residency is derived, not declared: it comes from combining a self-certification with the "indicia" your own records carry.

Indicia are the observable signals that suggest a tax residence: a residential or mailing address, a phone country code, a place of birth, a standing payment instruction to an account in another country, or a power of attorney granted to someone there. Under FATCA, US indicia are specifically enumerated. If your records show any of them and the customer has not documented themselves with a valid self-certification, the account is treated as reportable by default — silence is not neutral.

So classification consumes two inputs. From the customer you take the self-certification form (a W-9 for US persons, a W-8BEN for non-US individuals, or a CRS self-cert declaring one or more residences with tax identification numbers). From your own systems you take the indicia. The classifier reconciles them:

```
def classify(account, self_cert, indicia):
    residences = set(self_cert.declared_residences)
    for jurisdiction in indicia.jurisdictions():
        if jurisdiction not in residences and not self_cert.cures(jurisdiction):
            # unexplained indicia -> treat as reportable until cured
            residences.add(jurisdiction)
    return [r for r in residences if r.is_reportable(account)]
```

The output is a *set* of reportable residences per account, each with a validated tax identification number (TIN) or a documented reason the TIN is absent. Persisting this set — rather than a scalar country — is what lets the same classification feed both the FATCA and CRS files without re-derivation.

## Withholding is a separate axis from reporting

It is easy to conflate withholding and reporting because both key off the same documentation, but they answer different questions. Reporting says "here is what this account earned." Withholding says "we held back this fraction of a payment at the time it was made." Withholding happens continuously through the year, at payment time; reporting happens once, in arrears.

The withholding engine sits in the payment path, not the year-end batch. When US-source income is paid to an account that lacks valid documentation, a statutory withholding rate applies and the withheld amount is remitted. Backup withholding kicks in for a missing or mismatched TIN on otherwise reportable domestic income. The engine's job is to look up the account's documentation status at the moment of payment, apply the correct rate, book the withheld amount to a liability, and — critically — write an immutable withholding record keyed to the payment.

That record is what closes the loop at year end. The reporting job does not recompute withholding; it sums the withholding records already written. If you try to recompute, you will disagree with what was actually withheld, because documentation status changed during the year.

## Generating the files: same data, three schemas

Once you have the reportable set and the summed amounts per account, file generation is a projection. Each regime is a serializer over the same in-memory reporting record:

- **1099 series** — flat, fixed-layout records for US domestic reporting, batched by form type and transmitted through the tax authority's electronic filing channel. Each record carries the payee TIN, income amounts by box, and any federal withholding.
- **FATCA report** — an XML document keyed by reporting financial institution, listing US reportable accounts with balances, income, and the account holder's US TIN.
- **CRS report** — an XML document in the OECD schema, but *partitioned by receiving jurisdiction*. One account resident in three CRS countries produces three account entries across three jurisdiction-scoped messages.

Because CRS partitions by jurisdiction, the natural internal representation is a flat list of `(account, jurisdiction, amounts)` rows, not `(account, amounts)`. Generate that flat table first, then group by jurisdiction to emit messages. If you model it the other way — one row per account with a nested list of jurisdictions — every serializer has to flatten it again and they will flatten it inconsistently.

Every message also needs a stable message reference and each account entry a stable document reference identifier. Those identifiers are not cosmetic: they are the primary key the correction mechanism uses later.

## Corrections are the part everyone underestimates

The first year you ship this, you will produce a clean file, submit it, and feel finished. Then a customer's self-certification turns out to have been wrong, or an amount was restated, and you have to amend a report you already filed. Both FATCA and CRS handle this with correction messages that reference the original document identifier and carry a corrected, void, or amended action code. This is why the document references must be stable and stored: a correction is meaningless if you cannot point at the exact entry you are replacing.

The design consequence is that file generation cannot be a stateless dump. You must persist, per filing period, the exact set of document references you emitted and their content hash. A regeneration then diffs against the stored baseline:

```
new state   vs   filed baseline   ->   action
--------------------------------------------------
present, unchanged   present        ->   omit (already filed)
present, changed     present        ->   correct  (reference original)
absent               present        ->   void
present              absent         ->   new
```

That diff is the whole correction engine. Get it right and amendments are boring; get it wrong and you duplicate reports or silently drop them.

## Submission and acknowledgement

Submission is a transport concern, but a fussy one. Files often go through an encrypted upload channel with the authority's public key, and the response is asynchronous: you upload, then poll for an acknowledgement that may reject the whole batch on a schema error or reject individual records on a data error like an invalid TIN format. Treat the acknowledgement as a first-class inbound event. A rejected record is not a submission failure to retry blindly — it is a data-quality signal that feeds back into classification or the source record, and only then regenerates.

The end-to-end invariant worth enforcing in code is simple to state: every reportable account, in every reporting period, resolves to exactly one live document reference per regime — plus a chain of corrections behind it. If you can assert that at the end of a run, the pipeline is sound. If you cannot, no amount of correct XML formatting will save you when the authority asks why an account was reported twice.

## Closing thought

None of the individual steps here are algorithmically hard. What makes tax reporting an engineering problem is *identity and time*: an account has multiple residencies, its documentation status changes mid-year, and every file may need to be amended a year later. Model residency as a set, withholding as an event stream, and filings as a diff against a stored baseline, and the three regimes stop being three projects and become one pipeline with three serializers on the end.
