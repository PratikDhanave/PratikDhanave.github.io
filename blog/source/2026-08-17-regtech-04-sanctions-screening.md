# Sanctions and Watchlist Screening

*Sanctions screening looks simple — check if a name is on a list — and is genuinely hard, because names are messy, lists are fuzzy, and the penalty for a miss is among the most severe in all of compliance. It's a string-matching problem with strict-liability stakes, which is exactly what makes the false-positive-versus-false-negative balance so unforgiving.*

Distinct from AML monitoring (watching behavior), **sanctions screening** checks *who* you're dealing with against official lists of prohibited parties — sanctioned individuals, entities, and countries you're legally forbidden to transact with. This post covers screening as an engineering problem: what the lists are, why matching names is far harder than it looks, the fuzzy-matching and false-positive challenge at its core, and why sanctions carry uniquely high stakes. It's a deceptively deep problem hiding behind "just check the list."

## What sanctions screening is

Governments and international bodies publish **sanctions lists** — the names of individuals, organizations, and countries that businesses are prohibited from doing business with. Screening is the obligation to check your customers (and often the parties to their transactions) against these lists, and to *block* prohibited parties. Common lists include those from bodies like OFAC (in the US) and equivalent national and international authorities; screening typically also covers related **watchlists** such as PEP lists and adverse-media lists.

The stakes make sanctions distinct from other compliance areas: sanctions violations are frequently **strict liability** — meaning you can be penalized *even without intent*, simply for the violation occurring — and penalties are among the most severe in compliance. This changes the engineering calculus: because a single missed match can be catastrophic and intent is no defense, screening must lean hard toward *not missing* prohibited parties, which drives the false-positive problem below.

Screening happens at multiple points: at **onboarding** (part of KYC), on an **ongoing basis** (re-screening as lists update — someone can be added to a list after you onboarded them), and often on **transactions** (screening counterparties in real time). Lists change frequently, so screening is continuous, not one-time.

## Why matching names is hard

The naive view is "check if the customer's name is on the list" — a simple lookup. In reality, exact string matching fails badly, because names are messy in ways that defeat literal comparison:

- **Spelling and transliteration variations** — names (especially transliterated from other scripts and alphabets) have many valid spellings. The same person's name can be rendered numerous ways, and the list and your customer data may differ.
- **Name order and formatting** — first/last order varies by culture, middle names and initials come and go, and formatting differs.
- **Aliases and partial information** — sanctioned parties use aliases, and you may have incomplete data.
- **Common names** — many legitimate people share a name with a listed party, so a match on name alone is often a *different person*.
- **Deliberate evasion** — bad actors intentionally misspell or alter names to slip past exact matching.

Exact matching would miss all the variations (dangerous false negatives) while doing nothing about common-name collisions. So screening requires **fuzzy matching** — matching names that are *similar* but not identical, using techniques like phonetic matching, edit-distance, and handling of transliteration and name structure. This turns screening into a nuanced similarity problem, not a lookup, and how well you do it determines both what you catch and how much noise you generate.

## The false-positive balance, sharpened

Fuzzy matching creates the central tension, and sanctions is where it's most acute because of strict liability:

- **Loose matching (high sensitivity)** — catches variations, aliases, and evasion (few false negatives, which is what strict liability demands), but flags many legitimate customers who merely *resemble* a listed name (many false positives). Every flagged transaction may need to be held and reviewed.
- **Tight matching (low sensitivity)** — fewer false positives, but risks *missing* a real match — a false negative that, under strict liability with severe penalties, is far worse than in most compliance areas.

Because missing a true match is so costly, sanctions screening deliberately errs toward **sensitivity**, accepting a high false-positive rate as the price of not missing prohibited parties. The consequence is a large volume of matches to review — most of which are legitimate customers who happen to resemble a listed name — creating the same investigator-overload problem as AML, and often worse. The engineering challenge is therefore reducing false positives *without* lowering sensitivity: better matching algorithms, richer data (using date of birth, nationality, and other attributes beyond name to disambiguate — a "John Smith" match is dismissible if the DOB and nationality differ), and efficient review workflows. Using *additional identifying attributes* to disambiguate is one of the most effective levers — the more you can confirm it's a *different* John Smith, the more false positives you clear confidently.

## The screening and resolution workflow

Screening, like AML, is detection plus a human-in-the-loop workflow:

```text
1. Screen     → match customer/counterparty names against lists (fuzzy)
2. Alert      → potential matches generate alerts (often held pending review)
3. Review     → an analyst assesses whether it's a true match, using extra
                identifying data (DOB, nationality, address) to disambiguate
4. Resolve    → true match → block/report; false positive → clear (documented)
5. Record     → log the screening, the match, and the decision immutably
```

- **Potential matches are typically *held*.** Because of the stakes, a potential sanctions match often *blocks* the transaction or onboarding *until resolved* — you don't proceed and check later; you stop and verify. This makes screening latency and review speed a real operational and customer-experience concern.
- **Disambiguation is the analyst's job** — using the extra attributes above to decide true match vs. coincidence, and clearing false positives with documented reasoning.
- **Everything is recorded** — you must prove you screened against current lists and resolved matches correctly (auditability). Screening against *outdated* lists is itself a failure, so keeping lists current is part of the system.

The design goal mirrors AML: catch every true match (sensitivity, because strict liability), while making false-positive resolution fast and well-documented so legitimate customers aren't unduly delayed and analysts aren't overwhelmed.

## Why sanctions screening deserves special care

Sanctions screening earns its own post because it's uniquely unforgiving among compliance controls:

- **Strict liability** — no intent needed for a violation, so "we didn't mean to" is no defense. The system must be genuinely reliable.
- **Severe penalties** — among the harshest in compliance, sometimes with broad business consequences.
- **List volatility** — lists change often (and can change fast in response to world events), so ongoing re-screening against *current* lists is essential; screening once and forgetting is a violation waiting to happen.
- **Real-time pressure** — often required in the transaction path with tight latency, so screening must be both accurate and fast.

The upshot for engineers: sanctions screening is a high-stakes, continuously-updated, latency-sensitive fuzzy-matching system that must never miss a true match while resolving a flood of look-alikes efficiently. It's "check the list" the way search is "find the document" — simple to state, deep to do well. With who-you-serve and what-they-do covered, the next post turns to the backbone that makes all of it defensible: audit trails and immutability.

## Key takeaways

- Sanctions screening checks customers and transaction counterparties against official lists of prohibited parties (sanctioned individuals, entities, countries) and must block them — distinct from AML's behavior monitoring, and often strict liability with severe penalties.
- Exact name matching fails because names have spelling/transliteration variations, differing order/formatting, aliases, common-name collisions, and deliberate evasion — so screening requires fuzzy matching (phonetic, edit-distance, transliteration-aware), making it a similarity problem, not a lookup.
- Strict liability and severe penalties push screening toward high sensitivity (never miss a true match), which produces many false positives (legitimate people resembling listed names) — the central balance, sharper here than elsewhere.
- The best lever for cutting false positives without lowering sensitivity is disambiguation with additional identifying attributes (date of birth, nationality, address) beyond name — plus better matching algorithms and efficient review.
- Screening is continuous and latency-sensitive: potential matches are typically held/blocked until resolved, lists change frequently so re-screening against current lists is essential, and every screening and resolution must be recorded immutably.

## Further reading

- [AML and transaction monitoring (previous post)](/blog/posts/regtech-03-aml-transaction-monitoring.html)
- [OFAC — U.S. sanctions programs and lists](https://ofac.treasury.gov/)
- [Vector Search Internals — fuzzy/similarity matching techniques](/blog/series/vector-search-internals/)
