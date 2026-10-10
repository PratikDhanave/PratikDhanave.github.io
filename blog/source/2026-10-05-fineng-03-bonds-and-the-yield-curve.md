# Bonds and the Yield Curve

*A bond is the simplest real instrument in finance — a contract to pay fixed cash flows on fixed dates — which makes it the perfect place to turn the time value of money into something concrete. But bonds also introduce the two ideas that run through all of fixed income: yield, the single number that summarizes a bond's return, and the yield curve, the market's price of time itself. Understanding bonds is understanding how markets discount the future.*

Post 2 gave us discounting; a bond is discounting made tangible. Fixed income — the world of bonds — is the largest asset class on earth and the foundation of interest rates, and it's where discounted cash flow stops being a formula and becomes a market. This post covers how bonds are priced, what yield really means, how sensitive a bond is to rate moves (duration and convexity), and what the yield curve tells you.

## What a bond is

A **bond** is a loan in tradable form. The issuer (a government or company) borrows money and contractually promises:
- **Coupon payments** — fixed periodic interest, say a fixed percentage of the bond's face value, paid (often) semi-annually.
- **Principal (face value)** — the lump sum repaid at **maturity**, the end of the bond's life.

So a bond is exactly the cash-flow stream from post 2: a series of coupons plus a final principal. Its fair **price** is therefore the discounted sum of those cash flows:

```
Price = Σ  Coupon / (1 + y)^t   +   FaceValue / (1 + y)^n
```

where `y` is the discount rate per period and `n` the number of periods. Pricing a bond is pure discounted cash flow — which is why bonds are the canonical first instrument. The subtlety is the rate `y`, and that leads straight to yield.

## Yield: the one number that summarizes a bond

A bond trades at a market price, which may differ from its face value. Given that price, the **yield to maturity (YTM)** is the single discount rate `y` that makes the discounted cash flows equal the market price. It is the internal rate of return of holding the bond to maturity — the one number that summarizes the bond's return.

The crucial relationship, and the most important intuition in fixed income: **bond prices and yields move in opposite directions.** When market interest rates rise, newly issued bonds pay more, so an existing bond paying less becomes less attractive — its price falls until its yield matches the new market level. When rates fall, existing higher-paying bonds become more valuable, so their prices rise. Price and yield are two sides of the same coin: quote one and you've determined the other. This inverse relationship is why "interest rates went up" and "bond prices went down" are the same sentence, and it's the central risk of holding bonds.

A few consequences fall out immediately:
- A bond priced *below* face value trades "at a discount" and has a yield *above* its coupon rate; *above* face value is "at a premium" with yield below coupon; *at* face value, yield equals coupon.
- Yield lets you compare bonds with different prices, coupons, and maturities on a common footing — it's the fixed-income analogue of an interest rate, quoted by the market.

## Interest-rate risk: duration and convexity

Because price moves inversely with yield, the key risk of a bond is a change in interest rates. How *much* a bond's price moves for a given rate change is captured by two measures:

- **Duration** — the sensitivity of the bond's price to a change in yield, and roughly the weighted-average time to receive the bond's cash flows. A higher duration means a bigger price swing for the same rate move: a long-maturity, low-coupon bond has high duration and is very rate-sensitive; a short-maturity, high-coupon bond has low duration and is relatively stable. Duration is the fixed-income trader's primary risk number — "how exposed am I to rates?" — and it's additive across a portfolio, so a bond desk manages its *portfolio duration* the way an engineer manages a load budget.
- **Convexity** — duration itself changes as yields change, so duration is only a first-order (linear) approximation of the price–yield relationship, which is actually curved. Convexity is the second-order correction that captures that curvature. It's usually favorable to the bondholder (prices rise more when rates fall than they fall when rates rise by the same amount), and it matters most for large rate moves, where the linear duration estimate is off.

Together, duration and convexity are how fixed income quantifies and hedges rate risk — a first-order sensitivity plus a second-order correction, which is exactly the Taylor-expansion instinct any engineer recognizes.

## The yield curve: the market's price of time

Different bonds have different maturities, and the market assigns a different yield to each maturity. Plot yield against maturity and you get the **yield curve** (the *term structure of interest rates*) — the yield the market demands for lending over 1 year, 2 years, 10 years, 30 years. The yield curve is one of the most watched objects in all of finance because it is, literally, **the market's price of time** across horizons.

Its shape carries information:
- **Normal (upward-sloping)** — longer maturities yield more, compensating for the greater uncertainty and the time commitment of lending for longer. This is the usual shape.
- **Flat** — little difference between short and long yields, often a sign of transition or uncertainty.
- **Inverted (downward-sloping)** — short-term yields exceed long-term ones, an unusual state widely watched as a signal of expected rate cuts or economic slowdown.

The yield curve matters far beyond bonds: it provides the **discount rates** used to value *everything* (post 2's discount rate comes from here), it anchors the pricing of derivatives and loans, and its shape reflects the market's collective expectations about future rates and the economy. When people say "the market is pricing in rate cuts," they're reading the yield curve. For a financial engineer, the curve is the fundamental input — the risk-free term structure against which all other instruments are priced.

The takeaway: a bond is a contract for fixed cash flows, priced by pure discounted cash flow, and summarized by its **yield to maturity** — the single rate that equates its discounted cash flows to its market price. Bond prices and yields move **inversely**, making interest-rate risk the central concern, quantified by **duration** (first-order rate sensitivity) and **convexity** (the second-order curvature correction). Across maturities, yields form the **yield curve** — the market's price of time — whose level provides the discount rates for all of finance and whose shape encodes expectations about rates and the economy. Fixed income is where discounting becomes a market.

## Key takeaways

- A **bond** is a tradable loan — fixed **coupon** payments plus a **principal** repaid at maturity — so it's a pure cash-flow stream, and its **price is the discounted sum of those cash flows** (post 2 made concrete).
- **Yield to maturity (YTM)** is the single discount rate that equates a bond's discounted cash flows to its market price — the one number summarizing its return, letting bonds of different coupons/maturities be compared.
- **Bond prices and yields move inversely**: rates up → existing bond prices down, and vice versa. This is the central risk of bonds and why "rates rose" and "bond prices fell" are the same statement.
- **Duration** measures first-order price sensitivity to yield changes (higher = more rate-sensitive; long-maturity/low-coupon bonds have high duration) and is additive across a portfolio; **convexity** is the second-order correction for the curved price–yield relationship, mattering most for large moves.
- The **yield curve** (term structure) plots yield vs. maturity — the **market's price of time** — normally upward-sloping (sometimes flat or **inverted**, a watched recession signal); it supplies the **discount rates for all of finance** and encodes expectations about rates and the economy.

## Further reading

- [Bond valuation — pricing a bond as discounted cash flows](https://en.wikipedia.org/wiki/Bond_valuation)
- [Bond duration — interest-rate sensitivity](https://en.wikipedia.org/wiki/Bond_duration)
