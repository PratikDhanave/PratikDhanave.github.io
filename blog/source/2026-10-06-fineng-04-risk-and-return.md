# Risk and Return

*You cannot have higher expected return without accepting more risk — that trade-off is the deepest law in investing, and quantifying it precisely is the achievement that launched modern finance. The surprising twist is that risk is not simply additive: combine imperfectly related assets and some risk cancels out for free. Diversification is the closest thing finance has to a free lunch, and portfolio theory is the math of exploiting it.*

Posts 2 and 3 valued cash flows by discounting, and kept hinting that the discount rate must reflect risk. This post makes risk precise and shows how it relates to return. It's the conceptual heart of investing: how to measure risk, why diversification works, and how the market prices risk into expected returns. These ideas — portfolio theory and the Capital Asset Pricing Model — are the foundation of asset management and the reason the discount rate in post 2 is what it is.

## Measuring risk and return

To reason about risk quantitatively, finance represents an asset's future return as a **random variable** — you don't know next year's return, but you can describe its distribution. Two numbers summarize it:
- **Expected return** — the probability-weighted average return, the "center" of the distribution; what you expect to earn on average.
- **Risk** — the *dispersion* of returns around that average, usually measured by **variance** or its square root, **standard deviation (volatility)**. High volatility means returns swing widely and unpredictably; low volatility means they cluster near the average. Volatility is finance's workhorse risk measure.

This is the key abstraction: **an asset is a point in risk–return space** — an expected return and a volatility. The whole problem of investing becomes positioning yourself well in that space, and the central empirical fact is that higher expected returns come paired with higher volatility. Treasury bills are low-return, low-volatility; stocks are higher-return, higher-volatility; and no asset offers high return with low risk, because if one did, everyone would buy it until its price rose and its return fell. The risk–return trade-off isn't a preference; it's an equilibrium.

## Why diversification is (almost) a free lunch

Here is the idea that makes portfolio theory profound. When you combine assets into a **portfolio**, the portfolio's expected return is just the weighted average of the assets' expected returns — no surprise. But the portfolio's *risk* is **not** the weighted average of the assets' risks. It's less — often much less — as long as the assets don't move perfectly together.

The reason is **correlation**. When two assets are imperfectly correlated, their ups and downs partially cancel: when one zigs, the other sometimes zags, and the combined swing is smaller than either alone. The math is captured by **covariance** — how assets move together — and the result is that a portfolio's variance depends not just on each asset's volatility but on the *correlations between them*. Combine assets with low or negative correlation and a chunk of risk simply disappears, for free, with no sacrifice in expected return.

This is **diversification**, and it's the closest thing to a free lunch in finance: you reduce risk without reducing expected return, purely by combining imperfectly correlated assets. The practical lesson — "don't put all your eggs in one basket" — is quantitatively exact. It also distinguishes two kinds of risk:
- **Idiosyncratic (specific) risk** — risk unique to one asset (a company's product fails). This *can* be diversified away by holding many assets, because the surprises are unrelated.
- **Systematic (market) risk** — risk shared by all assets (a recession, a rate shock). This *cannot* be diversified away, because it hits everything at once.

That distinction is the hinge to asset pricing: since idiosyncratic risk can be eliminated for free, the market shouldn't reward you for bearing it — only **systematic** risk, which no one can escape, earns a return.

## The efficient frontier

Given a universe of assets, you can form countless portfolios by varying the weights. Plot them all in risk–return space and the best ones trace out a curve: the **efficient frontier** — the set of portfolios offering the **maximum expected return for each level of risk** (equivalently, minimum risk for each level of return). Any portfolio below the frontier is suboptimal: you could get more return for the same risk, or the same return for less risk.

This is **Modern Portfolio Theory** (Markowitz): investing becomes an *optimization problem* — choose portfolio weights to sit on the efficient frontier, then pick the point along it that matches your risk tolerance. It reframes "which stocks should I pick?" into "what's the optimal combination?", and it formalized the intuition that *you should judge an asset by its contribution to portfolio risk and return, not in isolation.* A volatile asset that's uncorrelated with your portfolio can *reduce* your overall risk — so it might be a great addition despite its individual volatility. Judging assets in portfolio context, not alone, is portfolio theory's enduring lesson.

## How the market prices risk: CAPM

If only systematic risk is rewarded, how much reward does it earn? The **Capital Asset Pricing Model (CAPM)** gives the classic answer. It says an asset's expected return depends on its exposure to *market* (systematic) risk, measured by **beta** — how much the asset moves with the overall market:

```
Expected return = Risk-free rate  +  β × (Market risk premium)
```

- **Beta** of 1 means the asset moves with the market; beta of 2 means it amplifies market moves (more systematic risk, higher expected return); beta near 0 means it's largely uncorrelated with the market (little systematic risk, little premium).
- The **market risk premium** is the extra return the market as a whole earns over the risk-free rate — the price of bearing one unit of systematic risk.

CAPM's core message: **the market compensates you only for systematic risk you can't diversify away, in proportion to beta.** Idiosyncratic risk earns nothing, because you could have diversified it. Whatever its empirical limitations (real markets are messier, and models like multi-factor pricing extend it), CAPM gives the foundational relationship between risk and expected return — and it closes the loop back to post 2: **the discount rate for a risky cash flow is the return investors require for its risk**, which CAPM makes concrete. The riskier (higher-beta) the cash flows, the higher the discount rate, the lower the present value.

The takeaway: risk and return are inseparably linked — higher expected return requires higher risk (volatility), an equilibrium not a preference. The profound twist is **diversification**: because imperfectly correlated assets' swings partially cancel, combining them reduces risk for free, splitting risk into diversifiable **idiosyncratic** risk and undiversifiable **systematic** risk. **Modern Portfolio Theory** turns investing into optimizing toward the **efficient frontier**, and **CAPM** prices risk by rewarding only systematic risk in proportion to **beta** — which is exactly the risk-adjusted discount rate that values every cash flow in finance.

## Key takeaways

- An asset's future return is a **random variable**; summarize it by **expected return** (the average) and **risk = volatility** (standard deviation of returns). An asset is a point in **risk–return space**, and higher expected return comes paired with higher volatility — an equilibrium, since any high-return/low-risk asset would be bid away.
- **Diversification** is finance's near-free lunch: a portfolio's return is the weighted average of its assets', but its **risk is less** than the weighted average whenever assets are imperfectly **correlated** — their swings partially cancel (via **covariance**).
- This splits risk into **idiosyncratic** (asset-specific, *diversifiable* for free) and **systematic/market** (shared, *undiversifiable*) — so the market rewards only systematic risk.
- **Modern Portfolio Theory** makes investing an optimization toward the **efficient frontier** (max return per unit risk); its lesson is to judge an asset by its **contribution to portfolio** risk/return, not in isolation.
- **CAPM** prices risk: `Expected return = Risk-free + β × market risk premium` — reward scales with **beta** (systematic-risk exposure), idiosyncratic risk earns nothing — which concretely sets the **risk-adjusted discount rate** that values every cash flow (closing the loop to post 2).

## Further reading

- [Modern portfolio theory — diversification and the efficient frontier](https://en.wikipedia.org/wiki/Modern_portfolio_theory)
- [Capital Asset Pricing Model — beta and the risk–return relationship](https://en.wikipedia.org/wiki/Capital_asset_pricing_model)
