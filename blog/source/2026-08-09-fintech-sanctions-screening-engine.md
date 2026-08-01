# Building a Sanctions Screening Engine That Controls False Positives

*How to ingest watchlists, match names across scripts and spellings, and turn a fuzzy score into an auditable clear, alert, or block.*

Sanctions screening is deceptively simple to describe and unforgiving to build. You have a set of official watchlists naming sanctioned people, companies, vessels, and countries. You have a stream of parties moving through your platform — a new customer, a payment beneficiary, a counterparty on a trade. Your job is to decide, for each party, whether it plausibly refers to a listed entity, and to do it well enough that you neither let a sanctioned name through nor bury your analysts under thousands of false hits every day.

The hard part is that names do not match cleanly. The same person appears as "Mohammed", "Muhammad", and "Mohamed"; a company is listed in Cyrillic but arrives in Latin transliteration; a middle name is dropped, a birth year is off by one. A screening engine is fundamentally a fuzzy-matching pipeline wrapped in controls that make every decision explainable — one engineers can operate and auditors can trust.

## The shape of the pipeline

Screening is a data flow with a fan-out in the middle and a human at the end. Watchlists are ingested and normalized into a searchable index. Each party is normalized the same way, matched against the index, and scored. The score meets a set of thresholds that route the party to one of three outcomes — auto-clear, alert for review, or hard block — and analyst decisions feed back as whitelist entries that suppress known-good matches on the next pass.

```
   ingest            normalize          match               score        route             disposition
┌──────────┐      ┌──────────┐      ┌──────────┐         ┌───────┐   ┌──────────┐      ┌──────────┐
│ OFAC/UN/ │ ───▶ │ transli- │ ───▶ │ phonetic │ ──────▶ │ combine│──▶│ threshold│ ───▶ │ analyst  │
│ EU lists │      │ terate + │      │ + edit-  │  cand.  │ + secondary│  │ clear /  │ alert│ disposition
│ (deltas) │      │ tokenize │      │ distance │         │ signals│   │ alert /  │      │ + whitelist
└──────────┘      └────┬─────┘      └──────────┘         └───────┘   │ block    │      └────┬─────┘
                       │                  ▲                          └──────────┘           │
                  ┌────┴─────┐            │ same normalize                      whitelist ◀──┘
                  │ party    │ ───────────┘                                     suppresses
                  │ (KYC/txn)│                                                  next pass
                  └──────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-sanctions-screening-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Ingesting lists as versioned, delta-aware data

Watchlists are published by multiple authorities, each with its own format and cadence. Treat every list as a versioned dataset, not a live feed you overwrite in place. On each refresh, compute the delta — entries added, amended, or removed — because deltas are what drive **rescreening**: when an authority adds a name today, every customer you already cleared must be re-evaluated against that one new entry, not the whole book.

Normalize every listed entity into a canonical record with the fields matching actually uses: primary name, all aliases (`a.k.a.` and weak aliases), entity type, and secondary identifiers such as date of birth, nationality, or a registration number. Keep the raw source record alongside the normalized one so an analyst can always see exactly what the authority published.

```python
def ingest(list_id, records, store):
    prev = store.current_version(list_id)
    incoming = {r.uid: normalize_entity(r) for r in records}
    delta = diff(prev.entries if prev else {}, incoming)
    version = store.commit_version(list_id, incoming)   # immutable snapshot
    if delta.changed:                                   # added + amended uids
        enqueue_rescreen(list_id, version, delta.changed)
    return version, delta
```

Two disciplines keep this honest. Never mutate a committed version — supersede it — so any past decision can be reproduced against the exact list state that produced it. And treat an ingest that shrinks a list dramatically or fails to parse as an operational alert; a silently truncated watchlist is a screening outage disguised as a green pipeline.

## Normalization is where matches are won or lost

Both listed entities and incoming parties must pass through the *same* normalization, or you are comparing apples to transliterated oranges. The steps that matter most:

- **Transliteration** — fold non-Latin scripts to a canonical Latin form so a Cyrillic listing can meet a Latin-typed party. Use a deterministic scheme and store the transliterated form.
- **Case, diacritic, and punctuation folding** — "O'Brien", "Obrien", and "OBRIEN" collapse to one token stream.
- **Token normalization** — strip corporate stopwords ("Ltd", "LLC", "GmbH") for company matching, and split personal names into tokens so word order and dropped middle names do not break the comparison.
- **Noise filtering** — drop titles and honorifics that add no discriminating signal.

Normalization must be pure and versioned. If you change the rules, you have effectively changed every score, so treat the normalizer version as part of every decision record.

## Matching: phonetic plus edit-distance, then combine

No single algorithm catches every variation, so run complementary matchers and combine their signals. A phonetic encoder (a Soundex- or Metaphone-style algorithm) catches "Mohammed" versus "Muhammad" — spellings that sound alike. An edit-distance measure (Levenshtein, or a token-set ratio for reordered multi-word names) catches typos and dropped tokens that sound different but read close.

```python
def name_score(party_name, listed_name):
    p = phonetic_ratio(party_name, listed_name)      # 0..1, sound similarity
    e = token_edit_ratio(party_name, listed_name)    # 0..1, spelling similarity
    return max(p, e)                                  # either signal can carry a hit
```

Taking the stronger of the two signals biases toward recall: for sanctions, a missed true match is far costlier than an extra alert. The name score is then adjusted by **secondary identifiers**. A strong name hit that also agrees on date of birth or nationality is escalated; a name hit that clearly *conflicts* on a reliable identifier can be attenuated. Never let secondary data silently veto a match on its own — treat conflicts as evidence to weigh, not a hard suppressor, because listed identifiers are often sparse.

Matching over an entire watchlist per party is expensive, so pre-filter candidates with a cheap blocking key — a phonetic prefix or an n-gram index — and run the expensive comparison only on that candidate set. Correctness comes from the scoring; performance comes from the blocking.

## Thresholds, three outcomes, and the analyst loop

The combined score meets a small, explicit threshold band that routes each party:

- **Below the lower threshold → auto-clear.** No plausible match; record the top score and move on.
- **Between the thresholds → alert.** A possible match a human must adjudicate. The party is held pending review, not blocked outright.
- **At or above the upper threshold, or an exact identifier match → block.** Treat as a hit until proven otherwise; stop the onboarding or payment.

Thresholds are configuration, not code — tuned per list, per entity type, and per business line, and versioned so you can prove which cutoff produced a given decision. Every routed party writes an immutable screening record: the party snapshot, the top candidates with their scores, the normalizer and list versions, and the threshold set applied.

Analyst dispositions close the loop. When a reviewer clears an alert as a false positive, capture *why* as a **whitelist** entry scoped to that party-and-listed-entity pair — not a blanket name suppression. On the next screening pass, the whitelist suppresses that specific known-good match so the analyst is not asked the same question twice, while any genuinely new match against the same party still surfaces. Blanket whitelisting by name is how sanctioned parties slip through; scope every suppression narrowly and expire it when the underlying list entry changes.

## Tuning and proving it works

A screening engine lives or dies on its false-positive rate, and you cannot tune what you cannot measure. Keep a labeled set of adjudicated alerts and replay it whenever you touch a matcher, a threshold, or a normalization rule, tracking recall (did true matches survive) and precision (how much noise reached analysts) as a pair. Moving a threshold to cut alert volume is only safe if recall on the labeled set holds.

Build it this way — versioned lists, shared normalization, complementary matchers, explicit thresholds, and narrowly scoped whitelists — and screening stops being a black box. It becomes a deterministic, replayable decision over auditable data, where every clear, alert, and block traces back to a specific list version, a specific score, and the rule that routed it. That traceability is exactly what a regulator or your own risk team will ask you to demonstrate on the day it matters.
