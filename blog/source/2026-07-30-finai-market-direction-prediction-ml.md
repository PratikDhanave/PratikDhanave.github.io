# Predicting Market Direction with ML: Walk-Forward and Leakage
*How to build a quant model that predicts up-or-down moves without quietly fooling yourself into a backtest that never survives contact with real markets.*

Ask a machine learning model whether a stock will close higher tomorrow and it will happily give you an answer. Ask whether that answer is trustworthy, and you have signed up for the harder half of quantitative finance. Financial time series are noisy, non-stationary, and adversarial: the moment a real edge becomes widely known, it decays. Most impressive-looking market-direction models are not skillful. They are leaky. This post walks through the discipline that separates an honest, modest model from a spectacular fantasy.

## Framing the problem

The first decision is what you are actually predicting. Market direction is usually posed as **classification**: given information available at time *t*, will the return over the next *h* periods be positive or negative? That is cleaner than **regression** on the raw return, because raw returns are dominated by noise and a tiny number of extreme days. A model that nails direction 54% of the time can be tradeable, while a regression that "explains" returns with a high R-squared is almost always leaking.

The **horizon** *h* matters enormously. One-minute direction, one-day direction, and one-month direction are different problems with different signal-to-noise ratios and different cost structures. Fix the horizon early, and define the label precisely: the sign of the forward return measured from the same decision point you will have in production. A common and subtle mistake is labeling with a return that partially overlaps the feature window — that overlap is a leak.

## Features from price and volume

You rarely start with anything but open, high, low, close, and volume. The craft is turning those into features that carry information without carrying the future.

- **Returns** at several lookbacks (1, 5, 20 periods), preferably log returns, which are additive and better behaved.
- **Volatility** estimates: rolling standard deviation of returns, or range-based measures built from high/low. Volatility regimes are among the most persistent, learnable signals in markets.
- **Technical transforms**: momentum, moving-average distances, an RSI-style oscillator, volume relative to its own trailing average. These are just compact summaries of recent price behavior; none is magic.
- **Calendar features**: day of week, proximity to month end. Cheap, occasionally real.

Two rules govern every feature. First, it must be computable using only data available at the decision timestamp — no peeking at the bar you are trying to predict. Second, prefer stationary, scale-free quantities (returns, ratios, z-scores) over raw price levels, which drift and make yesterday's model meaningless tomorrow.

## Why random K-fold is a trap

Here is where most tutorials go wrong. Standard K-fold cross-validation shuffles rows into random folds. For independent samples that is fine. For a time series it is catastrophic, because it lets the model train on Thursday and Friday to predict Wednesday. Information flows backward through time in a way it never can in production. The reported accuracy is inflated, sometimes dramatically, and it evaporates live.

Time respects order, so validation must too. You always train on the past and test on the future — never the reverse.

## Walk-forward and purged validation

The honest alternative is **walk-forward validation**. Sort by time. Train on an initial window, test on the block that immediately follows, record the out-of-sample result, then roll the whole arrangement forward and repeat. Every test block is genuinely unseen at the time the model that scores it was fit. Averaging across many rolls gives a distribution of out-of-sample performance rather than one lucky number.

Two refinements make this robust:

- **Purging.** When your label looks *h* periods ahead, the last training samples overlap in time with the first test samples. That overlap leaks label information across the boundary. Remove — purge — the training rows whose label windows intersect the test window.
- **Embargo.** Add a small gap after the test window before training resumes, so autocorrelation near the boundary cannot smuggle information across. The gap costs a little data and buys a lot of honesty.

You can also let the training window expand (anchored) or slide at fixed length (rolling). Sliding adapts faster to regime change; anchored uses more history. Test both, but test them the same disciplined way.

```
  PAST  ─────────────────────────────────▶  FUTURE

  roll 1:  [==== train ====]·gap·[ test ]
  roll 2:        [==== train ====]·gap·[ test ]
  roll 3:              [==== train ====]·gap·[ test ]
                                    │      │
                              purge overlap │
                                     out-of-sample only
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-market-direction-prediction-ml.html)** — the full workflow from feature engineering through walk-forward splits to a cost-aware evaluation gate and the leakage revise loop.

## The many faces of leakage

**Look-ahead bias** is using information that would not have existed at decision time: a feature that quietly includes the current bar's close, a normalization computed over the whole dataset (its mean and standard deviation encode the future), or a fundamental value stamped with the report date instead of the later date it was actually published. Fit every scaler, imputer, and feature statistic *inside* each training fold only, then apply it to the test fold.

**Survivorship bias** is training on the companies that exist today. Delisted, bankrupt, and acquired names vanish from a naive dataset, so the model learns from a universe curated by hindsight to be full of survivors. Use point-in-time universes that include names as they actually traded.

**Data-snooping bias** is the slow leak you cause yourself. Try a hundred feature-and-model combinations against the same test set and one will look great by chance alone. Every peek at your final evaluation data spends some of its credibility. Keep a truly held-out period you look at once, and treat walk-forward results as your working feedback.

## Evaluating like the market will

A model that is right 53% of the time can still lose money, because being right and being profitable are not the same thing. Realistic evaluation means:

- **Transaction costs.** Subtract commissions, the bid-ask spread, and slippage from every simulated trade. A high-turnover signal that looks brilliant gross often dies net of costs. Report net performance, always.
- **Signal-to-noise honesty.** Directional accuracy hovers near 50% for a reason. Judge with metrics that respect class balance and, above all, with risk-adjusted return after costs, not raw accuracy.
- **Distributions, not points.** A single backtest number is nearly meaningless. Walk-forward gives you many out-of-sample results — look at the spread, the worst rolls, and the drawdowns, not just the average.
- **A baseline.** Compare against buy-and-hold and against a trivial "predict the last direction" rule. Beating a coin flip is not the bar; beating a cheap baseline after costs is.

## Why the modest model wins

A backtest showing 90% accuracy and a smooth equity curve is not a triumph; it is a bug report. Real directional edges are small, unstable, and expensive to harvest. The value of walk-forward validation, purging, embargoes, point-in-time data, and cost-aware metrics is not that they make your numbers bigger — they make them *true*. A model with 52% out-of-sample accuracy that holds up across many rolls, survives transaction costs, and beats a simple baseline is worth more than a leaky masterpiece, because only one of them will still be there when you trade it with real money.

Build the pipeline so leakage is hard and honesty is the default. Fit everything inside the fold. Roll forward, never shuffle. Purge the overlap. Pay the costs. Then, and only then, believe your results — a little.
