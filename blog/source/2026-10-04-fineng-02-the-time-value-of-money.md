# The Time Value of Money

*A dollar today is worth more than a dollar tomorrow — and that single sentence, made precise, is the foundation beneath every price in finance. Discounting future cash flows back to their value today is the operation you perform, explicitly or implicitly, every time you value anything: a bond, a stock, an option, a company, a mortgage. Master this one idea and most of finance becomes arithmetic on top of it.*

Post 1 named the time value of money as the most important idea in finance. This post makes it precise. It's deceptively simple — compounding and discounting are just multiplication and division — but it is the operation that underlies all valuation, and getting fluent with it is the single highest-leverage thing an engineer can do in finance.

## Why time has value

A dollar today is worth more than the same dollar a year from now, for two reasons:
- **Opportunity.** You could invest today's dollar — at even a modest interest rate — and have more than a dollar next year. So a future dollar must be worth *less* than a present dollar, because it misses out on that growth.
- **Uncertainty and preference.** The future is uncertain (will you actually receive it?), and people generally prefer consumption now to consumption later. Both push the value of a future dollar down.

The rate that quantifies this — how much more a present dollar is worth than a future one — is the **interest rate** (or, when used to value, the **discount rate**). It is the exchange rate between money at different points in time. Everything in this post is bookkeeping around that exchange rate.

## Future value: compounding forward

If you invest an amount **PV** (present value) at an interest rate **r** per period, after one period you have `PV × (1 + r)`. After `n` periods, assuming the interest itself earns interest — **compounding** — you have:

```
FV = PV × (1 + r)^n
```

That exponent is the whole story of compounding: interest earns interest earns interest, so value grows *geometrically*, not linearly. A hypothetical $100 at 5% per year becomes $105 after one year, but about $162 after ten years — the extra $7 beyond simple interest is interest-on-interest. Over long horizons this exponential growth dominates everything, which is why compounding is often called the most powerful force in finance. The frequency of compounding matters too: the more often interest compounds (yearly, monthly, continuously), the faster value grows, with *continuous compounding* (using the exponential `e^(r×t)`) as the mathematical limit, widely used in derivatives pricing for its clean calculus.

## Present value: discounting backward

Valuation runs the compounding equation *backwards*. If a future cash flow **FV** will arrive in `n` periods, its value *today* — its **present value** — is found by dividing out the growth:

```
PV = FV / (1 + r)^n
```

This is **discounting**, and it is the single most-used operation in finance. The factor `1 / (1 + r)^n` is the **discount factor**: it shrinks a future amount to its present worth. A dollar far in the future, discounted, is worth noticeably less than a dollar soon — the further out and the higher the rate, the smaller the present value. Discounting is how you convert "money at different times" into a common unit — money today — so you can compare and add cash flows that arrive at different moments. Without it, you'd be adding quantities that aren't commensurable, like adding dollars to euros.

## Valuing a stream of cash flows

Real instruments aren't single future amounts; they're *streams* of cash flows at different times. The master valuation principle follows directly: **the value of any instrument is the sum of the present values of all its future cash flows.**

```
Value = Σ  CFₜ / (1 + r)^t      (sum over each future time t)
```

This one equation — **discounted cash flow (DCF)** — is the backbone of valuation across finance:
- A **bond** (post 3) is a stream of coupon payments plus a final principal; its price is the discounted sum of those cash flows.
- A **stock** can be modeled as the discounted stream of its future dividends (or free cash flows).
- A **company** or **project** is valued by discounting its projected free cash flows — the DCF valuation every finance analyst learns.
- A **mortgage or loan** is the same arithmetic solved for the payment that makes the discounted stream equal the loan amount.

So "valuation" across enormous swaths of finance reduces to: lay out the future cash flows, pick the right discount rate, discount each one, and add them up. The sophistication lives in two places — estimating the cash flows and choosing the discount rate — not in the arithmetic.

## The discount rate is where the judgment lives

The mechanics are trivial; the discount rate is where the real work and the real disagreement are. The right rate reflects the **riskiness** of the cash flows: safe, certain cash flows (like government bonds) are discounted at a low rate; risky, uncertain ones at a higher rate, because investors demand extra return to bear risk (post 4). This is the crucial coupling — **the discount rate encodes risk**:
- Discount a risky startup's projected cash flows at a government-bond rate and you'll massively *overvalue* it (you ignored the risk).
- The gap between the risk-free rate and the rate you actually use is the **risk premium** — the compensation for uncertainty, and the bridge to portfolio theory and asset pricing in post 4.

A related subtlety: future cash flows should themselves be *expected* values (probability-weighted), because the future is uncertain. Combining expected cash flows with a risk-adjusted discount rate is the standard way finance handles uncertainty in valuation — and it foreshadows the risk-neutral pricing of derivatives (post 6), where a clever change makes the math even cleaner.

The takeaway: the time value of money is the exchange rate between money at different times — a present dollar is worth more than a future one because it can be invested and because the future is uncertain. **Compounding** grows a present value forward (`FV = PV(1+r)^n`); **discounting** shrinks a future value back (`PV = FV/(1+r)^n`); and the value of any instrument is the **discounted sum of its future cash flows** (DCF). The arithmetic is simple; the judgment is in estimating the cash flows and, above all, choosing a discount rate that correctly reflects their risk — which is the thread that leads to everything else in the series.

## Key takeaways

- A present dollar is worth more than a future one (**opportunity** to invest it + **uncertainty**); the **interest/discount rate** is the exchange rate between money at different times.
- **Compounding** grows value geometrically — `FV = PV × (1 + r)^n` — interest earning interest, which dominates over long horizons; more frequent compounding grows faster, with **continuous compounding** (`e^(rt)`) as the limit used in derivatives math.
- **Discounting** is the reverse and the most-used operation in finance — `PV = FV / (1 + r)^n` — converting future money to today's units so cash flows at different times can be compared and added.
- The master principle is **discounted cash flow (DCF)**: the value of any instrument = the **sum of the present values of its future cash flows** — the backbone of valuing bonds, stocks, companies, projects, and loans.
- The arithmetic is trivial; the judgment lives in the **discount rate**, which must reflect the cash flows' **risk** (safe → low rate, risky → high rate) — the gap over the risk-free rate is the **risk premium**, the bridge to portfolio theory and asset pricing (post 4).

## Further reading

- [Time value of money — present/future value and discounting](https://en.wikipedia.org/wiki/Time_value_of_money)
- [Financial engineering — overview](https://en.wikipedia.org/wiki/Financial_engineering)
