# The P&L: Reading an Income Statement

*The income statement is the one financial document every engineer should be able to read, because it's the scoreboard everyone above you is watching. It answers, for a period of time, the most basic business question — did we make money? — but the real value is in its structure: the journey from "money customers paid us" at the top to "profit we actually kept" at the bottom, with every cost that eats into it along the way. Once you can read that journey, a huge amount of business behavior stops being mysterious.*

The income statement, or **P&L** (profit and loss), shows a company's *profitability over a period* — revenue, costs, and the profit or loss that results. This post walks through it top to bottom: **revenue**, **cost of goods sold** and **gross profit/margin**, **operating expenses** and **operating income**, and finally **net income**. Understanding the P&L's structure — how you get from top-line revenue to bottom-line profit — is the single most useful piece of financial literacy.

## The shape of a P&L

The income statement is essentially a *subtraction story*: start with the money customers paid you, subtract categories of cost step by step, and arrive at profit. Its structure, top to bottom:

```text
   Revenue (top line)              — money earned from customers
   – Cost of Goods Sold (COGS)     — direct cost of delivering the product/service
   = Gross Profit                  — (Gross Margin = gross profit / revenue)
   – Operating Expenses (OpEx)     — running the business (sales, R&D, admin)
   = Operating Income              — profit from core operations
   – Interest, Taxes, etc.
   = Net Income (bottom line)      — the profit actually kept
```

The key insight is that a P&L isn't one number — it's a *sequence of profitability measures* (gross profit, operating income, net income), each subtracting more costs. Each level answers a different question: gross profit shows the profitability of the *product itself*; operating income shows the profitability of the *core business operations*; net income shows what's *ultimately left*. Reading a P&L means understanding this journey and what each level tells you — not just glancing at the bottom line. Let's walk down it.

## Revenue and the top line

**Revenue** (the "top line") is the money a company earns from its business activities — from selling its products or services — over the period. It's where the P&L starts and the foundation everything else subtracts from.

- **Revenue is earned, not necessarily collected.** An important subtlety: revenue is recognized when it's *earned* (the product/service is delivered), which isn't always when cash is *received* (a customer might pay later, or pay upfront for future service). This is part of why profit (P&L) and cash (cash flow) differ — revenue on the P&L isn't the same as cash in the bank. (This "accrual" basis is why the cash flow statement exists separately.)
- **Growth in revenue is closely watched.** Revenue and its growth rate are headline metrics — how fast the top line is growing signals the business's trajectory and is a major focus (especially for startups, where growth can matter more than current profit). "Revenue growth" being a company obsession makes sense once you see it's the top of the whole P&L.
- **Not all revenue is equal.** The *quality* of revenue matters too — recurring/predictable revenue (subscriptions) is more valuable than one-off revenue, and revenue at high margin is worth more than revenue at low margin. Revenue is the start of the story, not the whole of it — what matters is how much *profit* survives the journey down the P&L.

Revenue is the top line — money earned from customers — and the base of the P&L. But top-line revenue alone says little about whether the business is *good*; that depends on how much profit remains after costs, which the rest of the statement reveals.

## Gross profit and margin

The first subtraction is **cost of goods sold (COGS)** — the *direct* costs of delivering the product or service — yielding **gross profit**:

- **COGS is the direct cost of delivery.** COGS covers the costs directly tied to producing/delivering what you sell — for a physical product, materials and manufacturing; for software, things like hosting/infrastructure and support directly tied to serving customers. It's the cost that scales directly with delivering the product, *not* the cost of running the broader business (that's operating expenses, below).
- **Gross profit = revenue − COGS.** What's left after the direct cost of delivery — the profit from the product itself, before the costs of running the company.
- **Gross margin is the key ratio.** **Gross margin = gross profit ÷ revenue** (as a percentage) — what fraction of each revenue dollar remains after direct costs. This is one of the most important numbers in a business: it shows how *inherently profitable* the product is, and it determines how much is left to cover everything else (operating expenses) and still profit. High-gross-margin businesses (like software, where delivering one more unit costs little) have much more room than low-margin ones (like some hardware or services). Gross margin heavily shapes what kind of business you have and how it can grow.

Gross profit and margin answer "how profitable is the product itself?" — the profitability of what you sell, before the cost of running the company. It's a foundational number because everything else (operating expenses, ultimate profit) has to fit within the gross margin. A business with thin gross margins has little room to cover its operating costs and profit; one with fat margins has room to invest and still profit. This is why gross margin is watched so closely.

## From operating income to the bottom line

Continuing down, **operating expenses (OpEx)** are subtracted from gross profit to get **operating income**, and then remaining items yield **net income**:

- **Operating expenses run the business.** OpEx covers the costs of *operating the company* beyond direct delivery — commonly sales and marketing, research and development (engineering!), and general/administrative (management, finance, HR, office). These are the costs of running and growing the business, not of delivering an individual unit. (Notably, most engineering salaries at a software company are OpEx, often R&D — worth knowing where *you* sit on the P&L.)
- **Operating income = gross profit − OpEx.** The profit from the company's *core operations* — after both delivering the product (COGS) and running the business (OpEx). This shows whether the fundamental business, as operated, is profitable. It's a key measure of business health because it reflects the actual operating reality (excluding financing and one-off items).
- **Net income = the bottom line.** After operating income, subtract remaining items — interest (on debt), taxes, and any one-offs — to reach **net income**, the "bottom line": the profit ultimately kept (or the loss). This is *the* profit figure, though as the layers show, the intermediate measures (gross profit, operating income) often tell you more about the business's health than net income alone.

- **Why the layers matter.** Reading these levels reveals *where* profit is made or lost. A company might have great gross margins (good product) but poor operating income (spending too much running the business), or strong operating income undercut by heavy interest (too much debt). The structure diagnoses the business, which is why financial literacy means reading the *whole* P&L, not just net income. A startup deliberately running at a net loss to grow (heavy OpEx on sales/R&D) can be perfectly healthy if its gross margins and unit economics are strong — which you can only see by reading the layers.

The P&L tells a subtraction story from revenue (top line) down through COGS to gross profit/margin (product profitability), through operating expenses to operating income (core-business profitability), to net income (the bottom line). Reading its structure — not just the final number — is what reveals where a business makes and loses money, and it's the most useful financial-literacy skill. Next: the balance sheet, which shows what the company owns and owes at a point in time.

## Key takeaways

- The income statement (P&L) is a subtraction story showing profitability over a period: it starts with revenue (top line) and subtracts categories of cost step by step to reach profit — and it's not one number but a *sequence* of profitability measures (gross profit → operating income → net income), each answering a different question.
- Revenue (the top line) is money earned from customers, recognized when *earned* not necessarily when *collected* (a reason profit ≠ cash); its growth is closely watched, but top-line revenue alone doesn't say whether the business is good — what matters is how much profit survives the journey down.
- Gross profit = revenue − COGS (the direct cost of delivering the product), and gross margin (gross profit ÷ revenue) is a key number showing how inherently profitable the product is and how much is left to cover everything else — high-margin businesses (software) have far more room than low-margin ones (hardware/services).
- Operating income = gross profit − operating expenses (sales, R&D — where most engineering salaries sit — and admin, the costs of running the business), showing whether the core operations are profitable; net income (the bottom line) subtracts interest, taxes, and one-offs to give the profit ultimately kept.
- Reading the *layers* (not just net income) diagnoses the business — great gross margin but poor operating income means overspending on operations; a startup running a net loss to grow can be healthy if gross margins and unit economics are strong — which is why financial literacy means reading the whole P&L.

## Further reading

- [Income statement (Wikipedia)](https://en.wikipedia.org/wiki/Income_statement)
- [Gross margin (Wikipedia)](https://en.wikipedia.org/wiki/Gross_margin)
- [Why engineers should understand business finance (previous post)](/blog/posts/finance-01-why-finance-matters.html)
