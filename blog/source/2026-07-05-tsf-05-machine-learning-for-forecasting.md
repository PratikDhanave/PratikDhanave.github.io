# Machine Learning for Forecasting — Features Over Time

*When classical methods aren't enough — many related series, rich external drivers, complex nonlinear patterns — you can bring the full machine-learning toolkit to forecasting. But you can't just feed a time series to a standard model; you have to reframe forecasting as a supervised learning problem through the right features. This post is about that reframing, where ML genuinely helps, and the time-specific traps that make it easy to get wrong.*

Posts 3–4 covered classical methods and honest evaluation. This post bridges to the [machine learning foundations](/blog/series/machine-learning-from-first-principles/): using regression, gradient-boosted trees, and the like for forecasting. The key move is turning a time series into a feature matrix — and doing it without leaking the future (post 4), which is where most ML-forecasting attempts quietly fail.

## Reframing forecasting as supervised learning

A standard ML model (ML series) maps a feature vector to a target. A time series is just a sequence of values. To use ML, you **turn the series into a supervised dataset**: each row's target is the value to forecast, and its features are things known *before* that point. The central technique is **lag features** — using past values as inputs:

- **Lags:** the value 1 step ago, 7 steps ago, 365 steps ago, etc. become features (`sales yesterday`, `sales last week`, `sales last year`). These directly encode the autocorrelation (post 1) that makes forecasting possible — they're how an ML model "sees" the past.
- **Rolling-window statistics:** the mean/min/max/std over the last 7, 30, 90 days — summarizing recent behavior (recent trend and volatility) as features.
- **Date/time features:** day-of-week, month, hour, is-holiday, is-weekend — explicitly encoding **seasonality** (post 2) so the model can learn cyclical patterns from the calendar.
- **External drivers (the big ML advantage):** price, promotions, weather, upstream signals — any variable that influences the target, which classical univariate methods can't easily use. This is often *why* you reach for ML: to incorporate many predictors.

Once the series is a feature matrix, you train a standard model — very often **gradient-boosted trees** (ML series, post 4), which excel on this kind of tabular, engineered-feature data and are a dominant practical choice for ML forecasting. Forecasting becomes feature engineering plus a tabular model, which is a powerful and flexible reframing.

## Where ML beats classical methods — and where it doesn't

ML forecasting genuinely shines in specific situations, and it's important to know them rather than reaching for ML reflexively (post 3's warning):

- **Many related series at once.** If you forecast thousands of products' demand, a single **global** ML model trained across *all* series (with a series-ID feature) can learn shared patterns and share strength across series — often beating fitting a separate classical model per series, especially for series with little individual history. This cross-learning is a major ML advantage and a common industrial pattern.
- **Rich external drivers.** When the target depends on many external variables (promotions, prices, weather, events), ML naturally incorporates them as features, while classical univariate methods struggle. If "what drives this?" has many answers, ML fits.
- **Complex nonlinear patterns and interactions.** ML can capture nonlinear relationships and feature interactions that linear classical models miss.
- **Lots of data.** ML needs enough data to learn; with long histories and many series, it has room to shine.

But the honest counterbalance (post 3): for a *single* series with *limited* data and clear trend/seasonality, classical methods (ETS, ARIMA) are often **better, simpler, and more robust** than ML — and the M-competitions showed ML doesn't reliably beat classical on typical series. So the decision rule: **reach for ML when you have many series, rich drivers, complex patterns, or abundant data; stick with classical for single, short, well-behaved series.** And *always* benchmark ML against classical and naive baselines (post 4) — ML forecasting that can't beat Holt-Winters or seasonal-naive isn't worth its added complexity, and this happens more often than ML enthusiasts expect.

## The time-specific traps

ML forecasting has failure modes beyond ordinary ML, all stemming from the time dimension, and they're where most attempts go wrong:

- **Feature leakage (the big one).** Every feature must use *only* information available *before* the forecast time (post 4). A rolling mean that includes the target period, a scaler fit on the whole series, a "future" external value you won't actually know at prediction time — all leak the future and produce fantasy accuracy. This is even easier to do with engineered features than with classical methods, and it's the dominant way ML forecasting fools people. *Every* feature must pass the test: "would I actually have this value at the moment I make the forecast?"
- **Multi-step forecasting is awkward.** A model trained to predict one step ahead doesn't directly give you 30 steps. You either **recursively** feed predictions back as inputs (which compounds errors over the horizon) or train **separate models per horizon** (more work) or a **direct multi-output** model. Classical methods handle multi-step more naturally, so this is a real ML cost.
- **Evaluation must still backtest.** All of post 4 applies with full force — walk-forward validation, real horizon, no leakage in any feature. Random CV on the feature matrix silently leaks and is a classic mistake.
- **Models don't extrapolate trend well.** Tree-based models *cannot predict values outside their training range* — a gradient-boosted model will never forecast a value higher than it saw in training, so a strongly trending series needs the trend removed (differencing/detrending) before ML, or the model will systematically under-forecast. This is a subtle, important limitation that classical methods don't share.

Handled with these in mind, ML is a powerful forecasting tool for the right problems — reframe the series into leakage-free lag/rolling/calendar/driver features, use gradient-boosted trees (or similar), benchmark ruthlessly against classical and naive baselines, backtest properly, and watch the trend-extrapolation trap. Used reflexively or carelessly, it's slower and worse than a classical model while carrying hidden leakage. The skill is knowing it's a *fit for specific situations* (many series, rich drivers, complex patterns, big data), not a universal upgrade.

The throughline: to forecast with ML you **reframe the series as a supervised dataset** via features known *before* each point — **lag features** (past values — encoding autocorrelation), **rolling-window statistics** (recent trend/volatility), **date/time features** (encoding seasonality), and **external drivers** (price/promos/weather — the big advantage classical univariate methods lack) — then train a tabular model, very often **gradient-boosted trees**. ML **beats classical** with **many related series** (a single **global** model sharing strength across them), **rich drivers**, **complex nonlinear patterns**, and **abundant data** — but for **single, short, well-behaved series classical wins**, so benchmark ruthlessly against classical and naive baselines (post 4). The time-specific traps: **feature leakage** (every feature must be available at forecast time — the dominant failure, even easier with engineered features), **awkward multi-step** forecasting (recursive error-compounding vs per-horizon models), mandatory **backtesting** (no random CV), and **trees can't extrapolate trend** (remove the trend first or they under-forecast).

## Key takeaways

- Use ML by **reframing forecasting as supervised learning**: build features known *before* the forecast time — **lag features** (past values, encoding autocorrelation), **rolling-window stats** (recent mean/std — trend/volatility), **date/time features** (day-of-week/month/holiday — encoding seasonality), and **external drivers** (price, promotions, weather — ML's big advantage over classical univariate methods) — then train a model, very often **gradient-boosted trees** (strong on tabular engineered features).
- ML **beats classical** with **many related series** (a single **global** model trained across all, sharing strength — a major industrial pattern), **rich external drivers**, **complex nonlinear patterns/interactions**, and **abundant data**; **classical wins** for **single, short, well-behaved series** (post 3), so **always benchmark ML against classical and naive baselines** (post 4) — ML that can't beat them isn't worth the complexity.
- **Feature leakage is the dominant trap**: every feature must use only data available *before* the forecast (a rolling mean including the target period, a scaler fit on the whole series, a not-yet-known future driver all leak) — even easier to do with engineered features than classical methods; test every feature with "would I have this at forecast time?"
- **Multi-step forecasting is awkward** in ML — **recursive** (feed predictions back, compounding errors), **per-horizon models**, or **direct multi-output** — a real cost vs classical methods that handle it naturally; and you **must still backtest** (walk-forward, no random CV).
- **Tree models can't extrapolate** beyond their training range, so a **trending series must be detrended/differenced** before ML or the model systematically under-forecasts — a subtle limitation classical methods don't share. ML is a fit for specific situations, not a universal upgrade.

## Further reading

- [Time series — supervised reframing and features](https://en.wikipedia.org/wiki/Time_series)
- [Gradient boosting — a dominant model for ML forecasting](https://en.wikipedia.org/wiki/Gradient_boosting)
