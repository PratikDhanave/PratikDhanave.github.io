# Forecasting in Practice — Choosing Methods and Shipping Forecasts

*Knowing the methods is the easy part; building a forecasting system that's accurate, honest, and maintainable is the real job. This closing post assembles the series into practical judgment — how to choose a method, how to ship forecasts that keep working, and the hard-won lessons (start simple, respect baselines, monitor for drift) that no single technique teaches. It turns the series into something you can actually run.*

Posts 1–7 built the toolkit — components, classical methods, evaluation, ML, deep learning, uncertainty. This post is how to use it as a practitioner. The theme, consistent across the whole series, is disciplined simplicity: forecasting rewards starting simple, benchmarking honestly, and escalating complexity only when it earns its place.

## Choosing a method: the complexity ladder

There's no universally best forecasting method — the right choice depends on the data and the problem. A reliable decision process is to climb a **complexity ladder**, stopping when added complexity stops helping:

1. **Start with naive baselines** (post 4) — "predict the last value," "repeat last season." Free, instant, and shockingly hard to beat. They set the floor every other method must clear.
2. **Try classical methods** (post 3) — ETS/exponential smoothing and auto-ARIMA. Fast, robust, strong on single and short series, and frequently the winner. For most individual business series, this is where you should *expect* to land.
3. **Try ML** (post 5) — gradient-boosted trees on lag/rolling/calendar/driver features — when you have **many related series, rich external drivers, or complex nonlinear patterns**. Benchmark against classical.
4. **Try deep learning** (post 6) — only with **many long series, abundant data, and complex multivariate dynamics**, and only if it *demonstrably beats* the simpler options on honest backtests.

The decision factors that place you on the ladder: **how much data** (little → classical; lots → ML/deep), **how many series** (one → classical; thousands → global ML/deep), **external drivers** (none → classical; many → ML), **pattern complexity** (simple trend/season → classical; complex nonlinear → ML/deep), and **interpretability/cost needs** (high → classical). The governing principle, repeated all series long: **start simple and only add complexity when it measurably helps** — because in forecasting, uniquely, the simple methods win far more often than intuition suggests, and the M-competition evidence (posts 3, 6) backs this hard. Reaching for deep learning first is the classic mistake.

## Shipping forecasts: the practical realities

Getting a good backtest number is not shipping — production forecasting has its own realities:

- **Evaluate honestly, always** (post 4). Backtest with walk-forward validation at the real horizon, no leakage in any feature, and *always* against naive baselines. This is non-negotiable and is where most forecasting projects secretly fail.
- **Forecast with uncertainty** (post 7). Ship prediction intervals, not just points, so decisions use the range; check calibration continuously. A point forecast in production is a confidently-wrong decision waiting to happen.
- **Monitor and re-forecast.** Forecasts go stale as the world changes — the patterns the model learned shift (**concept drift**, as in all ML). Monitor forecast accuracy in production against what actually happens, and **retrain/refresh** on a schedule or when accuracy degrades. A forecasting model is a maintained asset, not a one-time artifact (the MLOps lesson, again).
- **Watch for regime changes and shocks.** The hardest forecasting failure: a structural break (a pandemic, a policy change, a new competitor) that invalidates everything the model learned from history. No model forecasts a shock it has never seen, so detect regime changes fast, and don't trust any forecast blindly through one — this is where human judgment must override the model.
- **Mind the data pipeline.** As in all ML (ML series, post 8), most production forecasting incidents are *data* problems — a late data feed, a changed unit, a revised historical value. Monitor the inputs, not just the outputs.

The reality: a forecasting *system* is the model plus honest evaluation, uncertainty quantification, monitoring, retraining, and data hygiene — and the model is often the smallest part.

## The hard-won lessons

Closing the series with the wisdom that outlasts any method:

- **Start simple; respect the baselines.** The single most valuable habit is building naive and classical baselines first and never shipping a complex model that can't clearly beat them. Forecasting humbles complexity more than almost any ML domain — honor that.
- **Evaluation discipline beats model sophistication.** A simple model evaluated honestly (no leakage, real horizon, vs baselines) beats a fancy model evaluated carelessly — every time. If you get one thing right, make it the backtest (post 4).
- **Forecast uncertainty, not just values.** The range is usually more decision-relevant than the point; a calibrated interval is more honest and more useful than a precise-looking single number (post 7).
- **The future isn't the past — stay humble.** Forecasting assumes the future resembles the past, which is often true enough and sometimes catastrophically false. Respect irreducible uncertainty, widen intervals over the horizon, expect to be wrong sometimes, and keep a human in the loop for shocks and regime changes. Overconfidence is the forecaster's cardinal sin.
- **Match effort to value.** Not every forecast needs a sophisticated model — many decisions are fine with a simple, well-understood forecast, and the effort should scale with what the forecast is worth.

The series' synthesis: forecasting is the discipline of using the past to anticipate the future *while respecting that time breaks ordinary ML assumptions, that simple methods often win, that honest evaluation is everything, and that uncertainty is irreducible and decision-relevant.* Build up the complexity ladder from naive baselines, evaluate with leakage-free backtesting against baselines, ship calibrated uncertainty not bare points, monitor for drift and shocks, and stay humble about the limits of extrapolating the past. Do that, and you'll build forecasts people can actually trust and act on — which, in a field full of confidently-wrong single numbers, is rarer and more valuable than it should be.

The throughline: shipping good forecasts is mostly **disciplined judgment**, not method knowledge. Choose a method by climbing a **complexity ladder** — **naive baselines → classical (ETS/auto-ARIMA) → ML (gradient-boosted trees on features) → deep learning** — stopping when complexity stops measurably helping, placed by data volume, number of series, external drivers, pattern complexity, and interpretability/cost needs; the governing rule (backed by M-competition evidence) is **start simple and escalate only when it demonstrably wins**, because simple methods win far more than intuition expects. A forecasting *system* then adds the realities: **honest leakage-free backtesting vs naive baselines** (post 4, where projects secretly fail), **calibrated uncertainty intervals not bare points** (post 7), **monitoring + retraining** for concept drift, vigilance for **regime changes/shocks** (where human judgment must override), and **data-pipeline hygiene** (most incidents are data problems). The enduring lessons: respect the baselines, evaluation discipline beats sophistication, forecast uncertainty, stay humble that the future isn't the past, and match effort to value.

## Key takeaways

- **No universally best method** — climb a **complexity ladder**, stopping when complexity stops helping: **naive baselines** (post 4) → **classical** (ETS, auto-ARIMA — post 3, where most individual/short series should land) → **ML** (gradient-boosted trees on features — post 5, for many series/rich drivers/nonlinearity) → **deep learning** (post 6, only for many long series + abundant data + complex dynamics, and only if it *demonstrably beats* simpler options).
- Place yourself on the ladder by **data volume** (little→classical, lots→ML/deep), **number of series** (one→classical, thousands→global ML/deep), **external drivers**, **pattern complexity**, and **interpretability/cost** needs — governing rule: **start simple, add complexity only when it measurably helps** (forecasting humbles complexity; reaching for deep learning first is the classic mistake).
- A forecasting **system** is far more than the model: **honest backtesting** (walk-forward, real horizon, no leakage, always vs naive baselines — post 4, where projects secretly fail), **calibrated uncertainty** (ship intervals not points — post 7), **monitoring + retraining** for **concept drift** (a maintained asset, not a one-time artifact), vigilance for **regime changes/shocks** (no model forecasts an unseen shock — human judgment must override), and **data-pipeline hygiene** (most incidents are data problems).
- Hard-won lessons: **respect the baselines** (never ship a complex model that can't beat naive/classical), **evaluation discipline beats model sophistication** (an honestly-evaluated simple model beats a carelessly-evaluated fancy one), **forecast uncertainty not just values**, and **stay humble** (the future isn't the past — widen intervals over the horizon, expect to be wrong, keep a human in the loop for shocks).
- Synthesis: forecasting uses the past to anticipate the future **while respecting that time breaks ordinary ML assumptions, simple methods often win, honest evaluation is everything, and uncertainty is irreducible and decision-relevant** — do that and you build forecasts people can actually trust, which is rarer than it should be.

## Further reading

- [Forecasting — methods, practice, and evaluation](https://en.wikipedia.org/wiki/Forecasting)
- [Time series — the data and discipline this series builds on](https://en.wikipedia.org/wiki/Time_series)
