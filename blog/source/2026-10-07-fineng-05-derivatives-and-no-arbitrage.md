# Derivatives and the No-Arbitrage Principle

*Derivatives sound exotic, but a derivative is just a contract whose value derives from something else — a stock, a rate, a commodity. What makes them intellectually beautiful is how they are priced: not by predicting the future, but by insisting that their price be consistent with the things they depend on. That insistence — the no-arbitrage principle — is the single most powerful idea in quantitative finance, and this post builds it from the ground up.*

Post 4 priced risk in terms of expected return. Derivatives are priced on a completely different and more powerful principle: no-arbitrage. This post introduces forwards, futures, and options — the core derivatives — and the no-arbitrage reasoning that prices them *without any forecast of where the market is going*. Understanding this principle is the prerequisite for option pricing (post 6), and it's the idea that separates financial engineering from mere speculation.

## What a derivative is

A **derivative** is a financial contract whose value *derives from* the value of an underlying asset (the "underlying"). You don't own the underlying; you own a contract referencing it. The three foundational types:

- **Forwards and futures** — an agreement to buy or sell the underlying at a fixed price on a future date. Both lock in a price today for a future transaction; a *forward* is a private bilateral contract, a *future* is its standardized, exchange-traded cousin with daily settlement. If you agree to buy wheat at $7/bushel in three months, you profit if wheat rises above $7 and lose if it falls — your payoff is *linear* in the underlying's price.
- **Options** — the **right, but not the obligation**, to buy (a **call**) or sell (a **put**) the underlying at a fixed **strike price** by a certain date. Because it's a right not an obligation, an option's payoff is *asymmetric*: you exercise only when it's favorable, and walk away otherwise. That optionality is what makes options both powerful and harder to price (post 6).

Derivatives exist for two real reasons: **hedging** (an airline locks in fuel prices with futures to remove risk) and **speculation/leverage** (a trader gains amplified exposure for a small premium). Both uses rest on the same pricing logic.

## Payoffs: the shape of the contract

The clearest way to understand a derivative is its **payoff** — what it's worth at expiration as a function of the underlying's price. Payoffs are the vocabulary of derivatives:
- A **long forward** at price K pays `(S − K)` at expiry (where S is the final underlying price) — a straight line, profit above K, loss below, symmetric.
- A **call option** with strike K pays `max(S − K, 0)` — zero if the underlying ends below K (you don't exercise), rising linearly above K. The "hockey stick" shape.
- A **put option** with strike K pays `max(K − S, 0)` — profits when the underlying falls below K, zero above.

The asymmetry of options — flat on one side, sloped on the other — is the whole point: an option lets you capture upside while capping downside at the premium you paid. Combining options and forwards builds arbitrarily shaped payoffs (spreads, collars, straddles), which is why derivatives are the Lego bricks of financial engineering — you assemble a desired risk profile from simple payoff pieces.

## The no-arbitrage principle

Now the central idea. An **arbitrage** is a risk-free profit with no net investment — a "money pump" that costs nothing, risks nothing, and yields a sure gain. The **no-arbitrage principle** states that in a well-functioning market, such opportunities **cannot persist**: the instant one appears, traders pile in to exploit it, and their buying and selling move prices until the opportunity vanishes. So prices must settle at levels where *no arbitrage is possible*.

This sounds like an observation, but it's a pricing *engine* of astonishing power, because it lets you determine a derivative's price by a consistency requirement alone:

> If you can construct a portfolio of other instruments that **replicates** a derivative's payoff exactly, then the derivative must cost exactly what that replicating portfolio costs — otherwise you could arbitrage the difference.

That's the whole trick. You don't forecast the underlying. You find a combination of simpler instruments (the underlying itself, plus borrowing/lending at the risk-free rate) whose future payoff is *identical* to the derivative's, in every scenario. Since they pay the same no matter what, they must cost the same today — any gap would be free money. **The derivative's price is the cost of replicating it.**

## No-arbitrage in action: pricing a forward

The forward price falls straight out of no-arbitrage, with no view on where the asset is headed. Suppose you want to agree today to buy an asset in one year. Compare two ways to own the asset in a year:
1. **Enter the forward** — pay nothing now, pay the forward price F in a year, receive the asset.
2. **Buy it now, financed** — borrow the asset's current price S at the risk-free rate r, buy the asset today, hold it; in a year you owe `S × (1 + r)` and you have the asset.

Both routes leave you holding the asset in a year. By no-arbitrage they must cost the same, so the fair forward price is:

```
F = S × (1 + r)     (the spot price, compounded at the risk-free rate)
```

If the actual forward price were higher, you'd sell the forward and buy-and-hold to pocket a risk-free profit; if lower, you'd do the reverse. Either way, arbitrageurs force F to `S(1+r)`. Notice what's *absent*: any opinion about whether the asset will rise or fall. The forward price depends only on the current price and the interest rate — a pure consistency relationship. This is no-arbitrage pricing in miniature, and the same logic, applied to the asymmetric payoff of an option, produces Black-Scholes (post 6).

## Put-call parity: a free no-arbitrage identity

One more gift of no-arbitrage, because it's so clean. A call and a put on the same underlying with the same strike and expiry are linked by an exact relationship, **put-call parity**:

```
Call − Put = Underlying − PresentValue(Strike)
```

The reasoning is pure replication: a portfolio of "long a call, short a put" has exactly the same payoff as "own the underlying, owe the strike" — check it against the payoff formulas and they match in every scenario. Since the payoffs are identical, the prices must satisfy the identity, or arbitrage exists. Put-call parity means you **can't price a call and a put independently** — fix one and no-arbitrage fixes the other. It's a constraint every option model must respect, a sanity check on any pricing system, and a vivid demonstration that no-arbitrage *relates* instruments to each other rather than pricing each from scratch.

The takeaway: a derivative is a contract whose value derives from an underlying, with **payoffs** — symmetric for forwards/futures, asymmetric (optionality) for calls/puts — as its defining vocabulary. Derivatives are priced not by forecasting but by the **no-arbitrage principle**: risk-free free-money opportunities can't persist, so a derivative must cost exactly as much as a portfolio that **replicates** its payoff. This prices a forward as `S(1+r)` with no market view, and links calls and puts by **put-call parity** — and it is the foundation on which option pricing (post 6) is built. No-arbitrage, not prediction, is the engine of quantitative finance.

## Key takeaways

- A **derivative** is a contract whose value derives from an **underlying**; the core types are **forwards/futures** (obligation to transact at a set price — *symmetric*, linear payoff) and **options** (the *right not obligation* to buy (**call**) or sell (**put**) at a **strike** — *asymmetric* payoff).
- **Payoffs** are the vocabulary: forward `S − K`, call `max(S − K, 0)`, put `max(K − S, 0)`; options' asymmetry (capped downside, open upside) lets you assemble any risk profile from simple pieces.
- The **no-arbitrage principle** — risk-free, no-investment profits can't persist — is the pricing engine: if a portfolio **replicates** a derivative's payoff in every scenario, the derivative must cost exactly what that portfolio costs (price = cost of replication), with **no forecast** of the underlying needed.
- Applied to a **forward**, no-arbitrage gives `F = S × (1 + r)` — spot compounded at the risk-free rate — derived purely from consistency, with no view on direction.
- **Put-call parity** (`Call − Put = Underlying − PV(Strike)`) links calls and puts exactly, so they can't be priced independently — a constraint every option model must respect and the seed of Black-Scholes (post 6).

## Further reading

- [Put–call parity — a no-arbitrage identity](https://en.wikipedia.org/wiki/Put%E2%80%93call_parity)
- [Financial engineering — overview](https://en.wikipedia.org/wiki/Financial_engineering)
