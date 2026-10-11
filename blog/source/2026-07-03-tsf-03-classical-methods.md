# Classical Methods — Exponential Smoothing and ARIMA

*Before neural networks, two families of methods dominated forecasting for decades — and they still win surprisingly often. Exponential smoothing and ARIMA are the classical workhorses: well-understood, fast, interpretable, and shockingly hard to beat on many real series. This post explains both without heavy math, and makes the case that for a lot of forecasting, the right answer is still a classical model, not a deep one.*

Post 2 showed series decompose into trend, seasonality, and noise. This post covers the classical methods that model those components explicitly. They're essential not just as baselines but as genuine production tools — and understanding them teaches the core logic (extrapolate structure, model dependence) that every forecaster shares.

## Exponential smoothing: weighted memory of the past

The first family starts from a simple, intuitive idea: to forecast the next value, take a **weighted average of past values, where recent observations count more than old ones.** The weights decay *exponentially* into the past — yesterday matters a lot, last week less, last year barely — which is why it's called **exponential smoothing**. It's the formalization of "the recent past is the best guide to the near future."

The family builds up by adding the components from post 2:
- **Simple exponential smoothing** — for a series with no trend or seasonality: forecast the next value as an exponentially-weighted average of the past. One parameter controls how fast the weights decay (how much to trust recent vs old data).
- **Holt's method** — adds a **trend** component, so the forecast extrapolates the recent direction, not just the level.
- **Holt-Winters** — adds **seasonality** too, so it captures level + trend + seasonal cycle. This is the classic full exponential-smoothing model, and it maps directly onto decomposition (post 2) — it's essentially "track the level, trend, and seasonal pattern, updating each as new data arrives, and project them forward."

Exponential smoothing is beloved because it's **simple, fast, robust, and interpretable**, needs little data, and performs remarkably well — it's often the first thing to try and frequently the thing that wins. The modern statistical framework around it (**ETS** — Error, Trend, Seasonal models) makes it principled and automatic. For a huge number of business series (demand, sales, operational metrics), Holt-Winters or ETS is a genuinely strong forecaster, not a toy.

## ARIMA: modeling the dependence directly

The second family takes a different angle — instead of weighting past *values*, it explicitly models the *autocorrelation* structure (post 1) of the series. **ARIMA** (AutoRegressive Integrated Moving Average) combines three ideas, each named in the acronym:

- **AR (AutoRegressive)** — model the next value as a linear combination of *past values* ("today depends on the last few days"). This captures the series' dependence on its own recent history.
- **I (Integrated)** — **differencing** the series (modeling *changes* rather than levels) to make it **stationary** (post 1). Since ARIMA requires stationarity and real series often trend, you difference until the trend is removed — this is the "I", and it's how ARIMA handles non-stationary data.
- **MA (Moving Average)** — model the next value in terms of past *forecast errors* ("adjust based on how wrong we recently were"). This captures short-term shocks.

ARIMA is specified by three numbers (how many AR terms, how many differences, how many MA terms), and **SARIMA** extends it with seasonal versions of each to handle seasonality. ARIMA is more flexible and often more powerful than exponential smoothing on series with complex autocorrelation, and it's backed by a rich theory for diagnosing and validating models. Its cost is complexity: choosing the orders traditionally took expertise (reading autocorrelation plots), though modern **auto-ARIMA** tools automate the search, making it nearly as easy to apply as exponential smoothing.

The two families are complementary lenses on the same problem: exponential smoothing thinks in *components* (level/trend/season), ARIMA thinks in *autocorrelation* (dependence on past values and errors) — and interestingly, many exponential-smoothing models have ARIMA equivalents, so they're less rivals than two formalizations of "extrapolate the structure in the past."

## Why classical methods still win

The most important practical point: **classical methods remain the state of the art for a large fraction of real forecasting**, and reaching for deep learning first is often a mistake. The reasons:

- **They're strong, especially on limited data.** Many real series are short (a few years of monthly data = a few dozen points), and classical methods shine with little data where deep learning (data-hungry) overfits. A huge amount of business forecasting is exactly this regime.
- **They're fast, cheap, and interpretable.** They train in milliseconds, need no GPUs, and their components are understandable — you can explain and sanity-check them, which matters for trust and debugging (and the interpretability concerns of the XAI series).
- **They're hard to beat.** Large forecasting competitions (the M-competitions) have repeatedly found that **simple classical methods, and simple combinations of them, match or beat sophisticated ML/deep methods on many real series** — a famous, humbling, and under-publicized result. Complexity does not reliably win in forecasting.
- **They're excellent baselines even when you do go complex.** You should *always* build a classical baseline (even a trivial "predict the last value" or "repeat last season" — naive forecasts) before anything fancy, because if your deep model can't beat Holt-Winters, it's not worth its cost (post 5–6 lean on this).

So the honest guidance: for most forecasting, *start classical* — a naive baseline, then exponential smoothing (ETS) and/or auto-ARIMA — and only escalate to ML/deep learning (posts 5–6) when you have lots of data, many related series, complex external drivers, or evidence that classical methods have plateaued. Classical forecasting isn't the "before" picture that deep learning replaced; it's a living, often-winning approach, and knowing it well is knowing when you *don't* need the heavy machinery.

The throughline: two classical families still dominate much of forecasting. **Exponential smoothing** forecasts as an **exponentially-weighted average of past values** (recent counts more), building up through **simple → Holt's (adds trend) → Holt-Winters (adds seasonality)** — mapping directly onto decomposition (post 2), formalized as **ETS**; it's simple, fast, robust, interpretable, data-thrifty, and often wins. **ARIMA** instead models the **autocorrelation** directly — **AR** (depend on past values), **I** (difference for stationarity), **MA** (depend on past errors), extended to **SARIMA** for seasonality — more flexible, with **auto-ARIMA** automating order selection. They're complementary lenses (components vs autocorrelation). Crucially, **classical methods remain state-of-the-art for a large fraction of real forecasting**: strong on **limited data**, fast/cheap/interpretable, and repeatedly shown (M-competitions) to **match or beat deep learning** on many series — so **start classical** (naive baseline → ETS → auto-ARIMA) and escalate only with lots of data/drivers or evidence of a plateau.

## Key takeaways

- **Exponential smoothing** forecasts as an **exponentially-weighted average of past values** (recent observations weighted more), building up: **simple** (level only) → **Holt's** (adds trend) → **Holt-Winters** (adds seasonality) — directly mirroring decomposition (post 2), formalized as **ETS**; simple, fast, robust, interpretable, data-thrifty, and frequently a *winner*, not a toy.
- **ARIMA** models the **autocorrelation** directly: **AR** (next value from past values), **I** (**differencing** for **stationarity**, handling trend), **MA** (next value from past forecast errors), with **SARIMA** adding seasonality; more flexible/powerful on complex dependence, with order-selection automated by **auto-ARIMA**.
- The two families are **complementary lenses** (components vs autocorrelation) and often have equivalent formulations — both formalize "extrapolate the structure in the past."
- **Classical methods remain state-of-the-art for much real forecasting**: strong on **limited/short data** (where deep learning overfits), **fast/cheap/interpretable**, and the **M-competitions** repeatedly found simple classical methods **match or beat sophisticated ML/deep** approaches on many series — complexity doesn't reliably win.
- Practical guidance: **always build a classical baseline** (even naive "last value"/"repeat last season"), **start classical** (ETS, auto-ARIMA), and **escalate to ML/deep learning only** with abundant data, many related series, complex external drivers, or evidence classical has plateaued — classical forecasting is a living, often-winning approach, not a superseded one.

## Further reading

- [Autoregressive integrated moving average (ARIMA)](https://en.wikipedia.org/wiki/Autoregressive_integrated_moving_average)
- [Exponential smoothing — weighted-memory forecasting](https://en.wikipedia.org/wiki/Exponential_smoothing)
