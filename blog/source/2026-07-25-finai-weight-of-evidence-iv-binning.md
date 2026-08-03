# Weight of Evidence and Information Value: Binning for Credit Models

*How WOE binning turns raw variables into monotonic, interpretable predictors on a log-odds scale, and how Information Value ranks which features earn a place in a regulator-defensible scorecard.*

Credit risk models live under a constraint that most machine learning work never feels: someone will eventually ask you to explain, line by line, why an applicant was scored the way they were. A model examiner, an internal validator, or a customer exercising their right to an explanation all expect the same thing. That a change in one input moves the score in a direction a human can defend. Weight of Evidence (WOE) binning and Information Value (IV) are the two techniques that make this possible, and they have quietly powered application and behavioral scorecards for decades. They are not glamorous, but they are the reason a logistic-regression scorecard can be both accurate and auditable.

## The problem WOE solves

Raw predictors arrive in awkward shapes. Age is continuous but its relationship to default risk is rarely a straight line. Number of recent delinquencies is a skewed count with a long tail. Employment type is a category with a handful of rare values that barely appear in the data. If you feed these directly into a linear model, you force a single coefficient to describe a relationship that bends, plateaus, or reverses. You also make the model brittle. A single outlier or a thinly populated category can swing a coefficient wildly.

WOE reframes every predictor onto a common, meaningful scale. The scale of the log-odds of the outcome. Instead of asking the model to learn the shape of each variable, you pre-encode that shape through binning, then hand the model clean, monotonic inputs it can weight linearly.

## What Weight of Evidence actually measures

Start by splitting the target into two groups. The "bads" (accounts that defaulted, charged off, or hit whatever adverse definition you chose) and the "goods" (everyone else). Then cut the predictor into bins. For a continuous variable these are ranges; for a categorical one they are groups of levels.

Within each bin you compute two distributions. The share of all goods that fall in the bin, and the share of all bads that fall in the bin. WOE is the natural log of the ratio of those two shares:

```
WOE(bin) = ln( (goods in bin / total goods) / (bads in bin / total bads) )
```

The intuition is clean. A bin with a WOE above zero holds proportionally more goods than bads, so it is safer than the overall population. A bin below zero is riskier. A bin near zero looks like the average book. Because WOE is a log-odds quantity, it lines up naturally with logistic regression, whose coefficients also live in log-odds space. When you replace a raw value with its bin's WOE, the model's job collapses to learning a single scaling coefficient per variable rather than an entire curve.

A crucial discipline follows. The WOE values across ordered bins should move monotonically. As age increases, or as delinquency count rises, WOE should trend consistently in one direction rather than zig-zag. Monotonicity is what makes the model defensible: you can state plainly that "more recent delinquencies never lowers predicted risk," and the scorecard will honor that claim for every applicant.

## Information Value: ranking a feature's strength

WOE describes each bin. Information Value summarizes the whole variable in a single number that answers "how well does this predictor separate goods from bads?" It sums, across all bins, the WOE weighted by the difference between the good and bad shares:

```
IV = Σ ( (goods in bin / total goods) − (bads in bin / total bads) ) × WOE(bin)
```

Each term is positive whether a bin leans good or bad, because the sign of the share difference always matches the sign of the WOE. So IV accumulates predictive signal from every bin. The conventional reading of the resulting number is widely shared across the industry:

- Below 0.02: the variable is essentially useless, drop it.
- 0.02 to 0.1: weak but possibly worth keeping.
- 0.1 to 0.3: medium strength, a solid contributor.
- 0.3 to 0.5: strong.
- Above 0.5: suspiciously strong. Investigate before trusting it.

That last band matters as much as the others. An IV over 0.5 frequently signals leakage. A field that is a proxy for the outcome, or a value that is populated only after the account has already gone bad. Treat an implausibly high IV as a warning, not a trophy.

## Binning in practice: monotonic and optimal

Good binning is where most of the real work sits. A common recipe starts with fine bins (say, twenty quantile-based slices of a continuous variable), computes WOE for each, then merges adjacent bins until the WOE sequence is monotonic and every bin holds enough observations to be stable. A frequent rule of thumb is that each bin should contain at least five percent of the population and a non-trivial count of bads, so the estimated distributions are not driven by a handful of accounts.

Optimal binning tools automate the merge step. They search for the set of cut points that maximizes separation (often IV, or a tree-based split criterion) subject to constraints. Monotonic WOE, a minimum bin size, and a cap on the number of bins. The output is a small, stable set of bins that a human can read as a table and a regulator can reproduce.

```
raw variable ─▶ fine bins ─▶ monotonic?
                                 │  no
                                 ▼
                          merge adjacent  ──┐
                                 ▲          │
                                 └──────────┘
                                 │  yes
                                 ▼
                     compute WOE ─▶ compute IV ─▶ keep / drop
                                                  (by IV band)
      missing / rare ─▶ own WOE bin ─▶ (joins WOE step)
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-weight-of-evidence-iv-binning.html)** — the WOE/IV binning workflow from a raw variable to a kept-or-dropped feature, with the re-bin loop and special-value handling.

## Missing values and rare categories

Two edge cases separate a toy pipeline from a production one.

Missing values are information, not noise. In credit data, a blank field often correlates strongly with risk. An applicant with no recorded credit history behaves differently from one with a rich file. So rather than imputing a mean and discarding that signal, give "missing" its own bin and let it earn its own WOE. If missingness turns out to be uninformative, its WOE will sit near zero and cost nothing; if it is informative, you have captured it honestly.

Rare categories need grouping. A categorical level that appears in a handful of records cannot support a stable WOE. Its distribution estimate is pure noise. The standard fix is to merge sparse levels, either into a shared "other" bucket or into the neighboring level whose risk profile they most resemble. This keeps every bin populated enough that its WOE will not swing on the next data refresh.

## Why this discipline produces defensible, stable models

The payoff is threefold. First, interpretability. Every input is a small table mapping bins to WOE, and every coefficient reads as a weight on a log-odds contribution. You can trace any score back to the exact bins the applicant landed in. Second, stability. Coarse, well-populated, monotonic bins do not lurch when the portfolio shifts slightly, and you can monitor them over time by watching whether the population distribution across bins drifts (the same binning underpins the population stability index). Third, defensibility. Monotonic relationships and documented, reproducible cut points are precisely what model validators and examiners ask to see. The relationship between each variable and risk is stated as a rule, not discovered as an accident.

WOE and IV will not win a leaderboard against a gradient-boosted ensemble on raw accuracy alone. But in a domain where a model must be explained, monitored, and defended for years, the modest cost of careful binning buys something a black box cannot. A scorecard whose every decision you can stand behind.
