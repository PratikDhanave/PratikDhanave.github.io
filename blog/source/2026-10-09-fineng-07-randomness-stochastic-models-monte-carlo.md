# Randomness — Stochastic Models and Monte Carlo

*Prices are random, so finance is fundamentally a probabilistic discipline — and the tools for reasoning about randomness are what let quants price the instruments that have no tidy formula. A stochastic model describes how a price wanders through time; Monte Carlo simulation lets you compute almost anything by running that model thousands of times and averaging. Together they are the computational engine of modern quantitative finance, and they're territory engineers find immediately familiar.*

Black-Scholes (post 6) gave a closed-form price, but only because its assumptions are simple enough to solve by hand. Most real instruments and risk questions have no closed form — and that's where stochastic models and simulation take over. This post covers how finance models the randomness of prices (Brownian motion and geometric Brownian motion) and how Monte Carlo simulation turns that model into a general-purpose pricing and risk engine. It's where financial engineering becomes, unmistakably, computation.

## Modeling a price as a random process

A **stochastic process** is a quantity that evolves randomly over time — exactly what a market price is. To reason quantitatively about an uncertain future price, finance needs a *model* of that randomness, and the foundational one is **Brownian motion** (a "random walk" in continuous time): a path that moves in tiny random increments, with no memory of its past direction. It captures the core intuition that price changes are unpredictable and that uncertainty grows with the time horizon — the further out you look, the wider the cone of where the price might be.

Prices aren't modeled as plain Brownian motion, though, for two reasons: prices can't go negative, and a $1 move means something different for a $10 stock than a $1000 stock. The fix is **geometric Brownian motion (GBM)** — the model behind Black-Scholes — where it's the *percentage* (log) returns, not the absolute price, that follow a random walk. GBM has two parameters that map directly onto post 4's ideas:
- **Drift (μ)** — the average rate the price trends upward over time (the expected return).
- **Volatility (σ)** — how much the price jitters around that trend (the risk).

GBM produces price paths that trend upward on average while wandering randomly, never going negative, with log-normally distributed future prices. It's a simplification (real volatility changes, prices jump — post 6's assumptions), but it's the workhorse model, and understanding it is understanding how finance turns "prices are random" into something you can compute with.

## Monte Carlo: compute anything by simulating

Once you have a model of how a price moves randomly, you can answer almost any question about its future by **simulation** — this is the **Monte Carlo method**, and it's the most general tool in quantitative finance. The idea is beautifully simple:

1. **Simulate** many possible future price paths by running the stochastic model (GBM) forward with random increments — thousands or millions of them.
2. **Evaluate** the quantity you care about on each path — the option's payoff, the portfolio's final value, the loss.
3. **Average** across all paths to get the expected value, and look at the *distribution* across paths to understand the risk.

Why is this so powerful? Because it computes **expectations by brute force**, and risk-neutral valuation (post 6) already told us a derivative's price *is* an expected payoff. So Monte Carlo can price *anything* you can describe as a payoff — including instruments far too complex for any formula:
- **Path-dependent options** whose payoff depends on the whole price path (e.g. the average price, or whether a barrier was ever touched), not just the final price — intractable analytically, trivial to simulate.
- **Multi-asset derivatives** depending on several correlated underlyings, where the dimensionality defeats closed-form math but simulation handles it directly.
- **Portfolio risk** — simulate thousands of market scenarios and read the distribution of portfolio outcomes to compute risk measures like Value at Risk (post 8).

The trade-off is cost and precision: Monte Carlo is computationally expensive, and its error shrinks only with the *square root* of the number of simulations (to halve the error you need four times as many paths). That slow convergence is why practitioners use **variance-reduction techniques** and why Monte Carlo is a serious *software-engineering and high-performance-computing* problem — vectorization, parallelism, GPUs, careful random-number generation. For an engineer, this is the most comfortable corner of finance: it's a simulation pipeline with a performance budget.

## Why this is the engine of modern quant finance

Closed-form models like Black-Scholes are elegant but rare — they exist only for the simplest instruments under the simplest assumptions. The moment you add realism (changing volatility, jumps, path dependence, multiple correlated assets, exotic payoffs), the formulas disappear and **numerical methods** take over. Stochastic simulation is the most general of these, which is why it underpins so much of real quant work:
- **Pricing** instruments with no analytic solution (the majority of exotics).
- **Risk management** — simulating the distribution of portfolio outcomes to measure tail risk (post 8).
- **Stress testing** — running extreme but plausible scenarios to see what breaks.
- **Model validation** — checking simpler models against simulation, and checking simulations against reality.

The deeper point: finance is a **probabilistic** discipline, so its answers are *distributions*, not single numbers. A price is an expected value; a risk is the shape of a tail. Stochastic models give you a way to *generate* those distributions, and Monte Carlo gives you a way to *compute* with them. This is also the bridge to modern AI-in-finance: the same simulate-and-average machinery, scaled up and accelerated, is how banks compute firm-wide risk overnight. Mastering randomness is mastering the part of finance that doesn't fit in a formula — which is most of it.

The takeaway: prices are random, so finance models them as **stochastic processes** — foundationally **Brownian motion**, and in practice **geometric Brownian motion** (random walk in log-returns, with **drift** = expected return and **volatility** = risk, never negative). **Monte Carlo simulation** turns that model into a universal engine: simulate many paths, evaluate the payoff or outcome on each, and average — computing expectations (hence prices) and distributions (hence risk) by brute force, for instruments far beyond any formula's reach. It's expensive and converges slowly (a genuine HPC problem), but it's the most general tool in quantitative finance and the one that makes financial engineering unmistakably computational.

## Key takeaways

- Prices are **random**, so finance models them as **stochastic processes**: foundationally **Brownian motion** (continuous random walk — unpredictable increments, uncertainty growing with horizon), and in practice **geometric Brownian motion (GBM)** where *log-returns* random-walk, keeping prices positive and scale-relative.
- GBM's two parameters map onto post 4: **drift (μ)** = average trend (expected return), **volatility (σ)** = jitter (risk) — the same model under Black-Scholes.
- **Monte Carlo simulation** is the universal engine: **simulate** many price paths, **evaluate** the payoff/outcome on each, **average** → expected value (= price, via risk-neutral valuation) and the full **distribution** (= risk).
- It prices what formulas can't — **path-dependent** and **multi-asset** derivatives — and drives **portfolio risk, stress testing, and model validation**; its cost is slow (√N) convergence, making it an HPC/software problem (parallelism, GPUs, variance reduction).
- The deep point: finance is **probabilistic** — answers are **distributions**, not single numbers (a price is an expectation; a risk is a tail's shape) — and stochastic models + Monte Carlo are how you *generate* and *compute with* those distributions, the computational core of modern quant finance.

## Further reading

- [Geometric Brownian motion — the standard price model](https://en.wikipedia.org/wiki/Geometric_Brownian_motion)
- [Monte Carlo methods in finance — simulation-based pricing and risk](https://en.wikipedia.org/wiki/Monte_Carlo_methods_in_finance)
