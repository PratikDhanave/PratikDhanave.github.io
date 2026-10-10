# Option Pricing — Black-Scholes and the Greeks

*The Black-Scholes model is one of the most consequential equations ever written — it turned option pricing from guesswork into engineering and arguably created the modern derivatives industry. Its genius is not a formula to memorize but an idea: you can price an option by continuously replicating it with the underlying and cash, so no-arbitrage pins down its value without any forecast of the market. This post builds that idea and the Greeks that make it operational.*

Post 5 priced a forward by replication. An option's asymmetric payoff makes replication harder — but Black-Scholes-Merton showed it can be done *continuously*, and that insight is the crown jewel of financial engineering. This post explains how options are priced, the astonishing concept of risk-neutral valuation, what the famous model says and assumes, and the **Greeks** that traders actually use to manage option risk day to day.

## Why options are hard to price

A forward's payoff is linear, so a static buy-and-hold portfolio replicates it (post 5). An option's payoff is *curved* — flat below the strike, sloped above — and that kink breaks static replication. The option's sensitivity to the underlying *changes* as the underlying moves: near expiry and far in-the-money it behaves almost like the stock; far out-of-the-money it barely responds. No fixed portfolio can match a payoff whose slope keeps changing.

Black, Scholes, and Merton's insight: replicate it **dynamically**. Hold a continuously-adjusted position in the underlying plus cash, rebalancing as the price moves, so that at every instant the little portfolio moves exactly like the option. If you can replicate the option's payoff this way, then by no-arbitrage (post 5) the option must cost exactly what that replicating strategy costs — and that cost *is* the Black-Scholes price. The option is priced by the cost of the hedging strategy that neutralizes it.

## Risk-neutral valuation: the beautiful trick

Dynamic replication leads to a startling simplification. Because the replicating portfolio is *risk-free* at every instant (it's perfectly hedged), its return must equal the risk-free rate — and crucially, the actual expected return of the underlying **drops out of the pricing entirely.**

This gives **risk-neutral valuation**, the deepest idea in derivatives pricing:

> To price a derivative, pretend every asset grows at the risk-free rate, compute the expected payoff under that pretend ("risk-neutral") world, and discount it at the risk-free rate.

The real-world expected return — whether you think the stock will boom or crash — is **irrelevant** to the option's price. This feels wrong at first: surely a bullish forecast makes a call worth more? No — because the option can be *replicated and hedged*, its price depends only on the underlying's *current price and volatility*, not its expected direction. Your opinion about direction is already expressible by trading the underlying itself; the option adds nothing a forecast would price. Risk-neutral valuation is no-arbitrage pushed to its logical conclusion, and it's why derivatives pricing needs *volatility* as an input but not *expected return*.

## What Black-Scholes says and assumes

The **Black-Scholes-Merton model** gives a closed-form price for a European option (exercisable only at expiry) as a function of five inputs:
- the **underlying price** (S),
- the **strike** (K),
- **time to expiry** (T),
- the **risk-free rate** (r),
- and the **volatility** (σ) of the underlying.

Four of the five are observable. The fifth — **volatility** — is the heart of the matter: it's the single number encoding how much the underlying is expected to move, and it's what option pricing is really about. More volatility means a wider range of outcomes, which (given the option's capped downside) makes both calls and puts *more* valuable — optionality is worth more when more can happen.

Like every model, Black-Scholes rests on **assumptions that are not literally true**, and the discipline is knowing them (post 1's "models are assumption-bound"):
- the underlying follows a continuous, log-normal random walk with *constant* volatility (post 7),
- you can trade continuously with no transaction costs and no gaps,
- the risk-free rate is constant, and no jumps occur.

Real markets violate all of these — volatility changes, prices jump, trading has costs. The famous evidence is the **volatility smile**: if the model were perfectly true, every option on an underlying would imply the same volatility, but in practice implied volatility varies with strike — the market's correction for the model's unrealistic assumptions. So practitioners use Black-Scholes not as literal truth but as a *common language*: they quote options in terms of **implied volatility** (the σ that makes the model match the market price), turning the model into a translation layer between prices and a standardized risk measure. That is the right engineering posture — a flawed model, understood and used for what it's good at.

## The Greeks: operating an option book

The model's lasting practical gift is the **Greeks** — the sensitivities of an option's price to each input. If the price is a function of several variables, the Greeks are its partial derivatives, and they are how traders actually measure and hedge risk:
- **Delta** — sensitivity to the underlying's price. It's the hedge ratio: how much underlying to hold to neutralize the option's directional risk (the "dynamic replication" of above, made concrete). Delta-hedging is the daily work of an options desk.
- **Gamma** — how delta itself changes as the underlying moves (the second derivative, the curvature). High gamma means your hedge goes stale fast and you must rebalance often — the practical cost of the option's curvature.
- **Vega** — sensitivity to volatility. Since volatility is the key uncertain input, vega is the exposure traders watch most; a vol spike can move an option more than a price move.
- **Theta** — sensitivity to the passage of time ("time decay"): an option loses value as expiry approaches, all else equal, because there's less time for favorable moves.
- **Rho** — sensitivity to the interest rate, usually the least important.

The Greeks turn an abstract price into a **risk dashboard**. A desk doesn't predict prices; it monitors its aggregate delta, gamma, vega, and theta across hundreds of positions and trades to keep them within limits — managing an option book is managing its Greeks. This is risk management (post 8) at the instrument level, and it's the operational legacy of Black-Scholes far more than the formula itself.

The takeaway: Black-Scholes prices an option by **dynamic replication** — continuously hedging it with the underlying and cash — so no-arbitrage sets its price as the cost of that hedge, with the startling consequence that the underlying's *expected return is irrelevant* (**risk-neutral valuation**: price under a pretend risk-free-growth world and discount at the risk-free rate). The model needs five inputs, of which **volatility** is the crux, and rests on assumptions that are false but useful — which is why the market speaks in **implied volatility** and the **volatility smile** reveals the model's limits. Its enduring operational gift is the **Greeks** (delta, gamma, vega, theta, rho), the sensitivities that let traders run an option book as a managed risk dashboard.

## Key takeaways

- Options are hard to price because their payoff is **curved** (changing sensitivity), breaking static replication; Black-Scholes-Merton prices them by **dynamic replication** — a continuously-rebalanced hedge of underlying + cash — so by no-arbitrage the option's price = the cost of that hedge.
- **Risk-neutral valuation** is the deep consequence: because the hedged portfolio is risk-free, the underlying's **real expected return drops out** — price a derivative by taking the expected payoff in a pretend "everything grows at the risk-free rate" world and discounting at the risk-free rate. Direction is irrelevant; **volatility** is what matters.
- Black-Scholes needs five inputs (price, strike, time, rate, **volatility**); four are observable, and **volatility is the crux** (more vol → options worth more). It assumes constant-vol continuous log-normal prices and frictionless trading — all false, exposed by the **volatility smile**.
- Practitioners therefore use it as a **common language**, quoting options in **implied volatility** (the σ matching the market price) — a flawed model used knowingly for translation, the right engineering posture.
- The **Greeks** — **delta** (price sensitivity / hedge ratio), **gamma** (curvature of delta), **vega** (volatility), **theta** (time decay), **rho** (rate) — are the model's lasting practical gift, turning option risk into a **dashboard** a desk hedges to limits rather than forecasting prices.

## Further reading

- [Black–Scholes model — option pricing and risk-neutral valuation](https://en.wikipedia.org/wiki/Black%E2%80%93Scholes_model)
- [The Greeks (finance) — option risk sensitivities](https://en.wikipedia.org/wiki/Greeks_(finance))
