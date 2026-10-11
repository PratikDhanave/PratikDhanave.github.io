# Evaluation and Backtesting — Don't Let the Future Leak

*The single most common way to build a forecaster that looks brilliant and fails in production is evaluating it wrong — and time-series evaluation is riddled with ways to accidentally let the future leak into the past. Getting evaluation right, through proper backtesting that respects time order, matters more than the choice of model. This post is about measuring forecast quality honestly, which is the skill that separates real forecasters from people who fool themselves.*

Post 1 warned that you can't use a random train/test split on time series. This post is why, and what to do instead. It's arguably the most important post in the series, because a great model evaluated wrong is worse than a mediocre model evaluated right — the former ships and fails, the latter you can trust.

## Why the standard train/test split is catastrophic here

In normal ML you randomly split data into train and test (ML series, post 5). On a time series, **random splitting is a disaster**, because it lets the model train on *future* data to predict the *past* — a blatant form of **data leakage** (lookahead bias). If your test set contains January and your training set contains February, the model has effectively seen the future, and its test performance is fantasy: it will look far better than it could ever be in production, where the future genuinely isn't available.

This is the cardinal sin of time-series work, and it's insidious because:
- It produces *impressive* results — leakage inflates accuracy, so the broken evaluation looks like success, not error.
- It's *easy* to do accidentally — any random shuffle, any feature computed using the whole dataset (a global mean, a scaler fit on all data), any target that peeks ahead, leaks the future.
- It *only* reveals itself in production, when the model mysteriously underperforms its glowing test numbers — by which point you've shipped a forecaster that doesn't work.

The iron rule: **you must always train on the past and test on the future, never the reverse.** Every valid time-series evaluation respects the arrow of time — the model only ever sees data that would genuinely have been available at the moment of each forecast. Violating this is the number-one cause of forecasters that work in the notebook and fail in reality.

## Backtesting: evaluation that respects time

The correct approach is **backtesting** (time-series cross-validation): simulate how the model *would have* performed by repeatedly training on data up to a point in time and forecasting the period just after — always moving forward, never peeking ahead. Two standard schemes:

- **Rolling-origin / walk-forward with expanding window:** train on all data up to time *t*, forecast the next period, then move *t* forward (now training on everything up to *t+1*), and repeat. The training window *grows* as you walk forward through history. This mimics how you'd actually retrain a model over time.
- **Sliding window:** same, but the training window is *fixed-size* and slides forward (drop the oldest as you add the newest), useful when only recent data is relevant or the series is very long.

Either way, you get *multiple* forecasts across different time points, evaluated against what actually happened next — a realistic, robust estimate of production performance that respects causality. Backtesting is to forecasting what cross-validation is to normal ML: the honest way to estimate how the model will really do. Key disciplines within it:
- **Forecast the real horizon.** If you'll forecast 30 days ahead in production, backtest 30-days-ahead forecasts, not 1-day — accuracy degrades with horizon (post 1), and testing a shorter horizon than you'll use overstates performance.
- **Fit *everything* only on past data.** Not just the model — feature scaling, normalization, imputation, and any derived feature must be computed using *only* data available at forecast time. A scaler fit on the full series leaks future statistics; this subtle leakage is extremely common.
- **Respect gaps if needed.** If there's a delay before your forecast is used, build that gap into the backtest.

## Choosing error metrics — and the baseline that keeps you honest

With a valid backtest, you measure error — and metric choice matters (echoing the ML series' evaluation post):

- **MAE (mean absolute error)** — average absolute error, in the data's units, easy to interpret and robust to outliers.
- **RMSE (root mean squared error)** — penalizes large errors more, so use it when big misses are especially costly.
- **MAPE (mean absolute percentage error)** — error as a percentage, scale-free and good for comparing across series of different magnitudes — but it breaks near zero values (division by ~0 explodes) and is asymmetric, so use it carefully.
- **Scaled errors (like MASE)** — error *relative to a naive baseline*, which elegantly handles different scales and directly answers "are we beating the naive forecast?" — often the best choice.

That last point is the one that keeps forecasters honest: **always compare against naive baselines.** The two essential ones are "predict the last value" (random walk) and "predict the same as last season" (seasonal naive). These are shockingly hard to beat, and a sophisticated model that can't beat "repeat last week" is worthless *no matter how good its absolute metrics look.* Absolute error numbers are nearly meaningless without a baseline — RMSE of 500 is great or terrible depending on whether naive gets 400 or 5,000. The baseline comparison is what turns an error number into a verdict, and skipping it is how teams celebrate models that add nothing.

The through-line: in forecasting, *how you evaluate matters more than what model you pick*. Never random-split (it leaks the future — the cardinal sin that inflates accuracy and fails in production); always **backtest** by training on the past and testing on the future (walk-forward, expanding or sliding window), fitting *everything* (including scalers and features) only on past data, at the *real* forecast horizon. Then measure with an appropriate metric (MAE/RMSE/MAPE/MASE) and — above all — **compare against naive baselines**, because a model that can't beat "repeat last season" is worthless however good its raw numbers look. Honest evaluation is the skill that separates forecasters who ship working models from those who ship fantasies.

The throughline: time-series evaluation is where forecasters most fool themselves, and **getting it right matters more than the model**. A **random train/test split is catastrophic** — it lets the model train on the **future** to predict the past (**leakage/lookahead bias**), producing impressive numbers that collapse in production; the iron rule is **always train on the past, test on the future**. Do this via **backtesting** (walk-forward with an **expanding** or **sliding** window), which yields realistic multi-point estimates — and crucially **fit everything (model *and* scalers/features/imputation) only on past data** (a scaler fit on the full series is a common subtle leak) at the **real forecast horizon**. Measure with a fit-for-purpose metric (**MAE**, **RMSE**, **MAPE** — careful near zero, **MASE** — scaled to a baseline), and **always compare against naive baselines** ("last value", "last season"), because a model that can't beat them is worthless regardless of its absolute numbers — the baseline is what turns an error figure into a verdict.

## Key takeaways

- In forecasting, **how you evaluate matters more than which model you pick** — a great model evaluated wrong ships and fails; a mediocre one evaluated right you can trust.
- **Random train/test splitting is catastrophic**: it trains the model on the **future** to predict the past (**data leakage / lookahead bias**), inflating accuracy into fantasy that collapses in production — insidious because it *looks like success*, is *easy to do accidentally*, and *only shows up in production*. Iron rule: **always train on the past, test on the future.**
- Use **backtesting** (time-series cross-validation): repeatedly train up to time *t* and forecast the next period, walking forward — **expanding window** (growing training set, mimics retraining) or **sliding window** (fixed recent window) — for a realistic, multi-point performance estimate.
- Backtest disciplines: forecast the **real horizon** you'll use in production (accuracy degrades with horizon — testing shorter overstates it), fit **everything** (model *and* scaling/normalization/imputation/derived features) using **only past-available data** (a scaler fit on the full series is a common subtle leak), and build in any **delay gap**.
- Pick a metric by need — **MAE** (interpretable, robust), **RMSE** (punishes big misses), **MAPE** (scale-free but breaks near zero), **MASE** (scaled to a naive baseline) — and **always compare against naive baselines** ("predict last value", "repeat last season"): they're hard to beat, and a model that can't beat them is **worthless regardless of absolute metrics** — the baseline turns an error number into a verdict.

## Further reading

- [Backtesting — evaluating a model on historical data](https://en.wikipedia.org/wiki/Backtesting)
- [Forecasting — accuracy measurement and evaluation](https://en.wikipedia.org/wiki/Forecasting)
