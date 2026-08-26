# Equity, Cap Tables, and Dilution

*The single most misunderstood thing about startup ownership is what happens to your slice when you raise money. Founders imagine they're "giving up 20%" and keeping a fixed 80% forever — but ownership isn't a slice carved from a fixed pie; it's a percentage of a share count that keeps growing. Every round issues new shares, and every new share makes everyone's existing percentage smaller. Understanding this — dilution, the cap table, and the option pool — is understanding what you actually own, and it's where founders most often get an unpleasant surprise.*

Funding is fundamentally selling equity (ownership). This post covers the mechanics of that ownership: **equity and shares**, the **capitalization table** that tracks who owns what, and **dilution** — how ownership percentages shrink as you raise. It also covers the **option pool** for employees. This is the least intuitive and most consequential part of funding for founders and early employees, and getting the intuition right protects you from expensive misunderstandings.

## Equity and shares

**Equity** is ownership of the company, divided into **shares**. Owning shares means owning a proportional piece of the company:

- **Ownership is a percentage of total shares.** Your ownership percentage is *your shares ÷ total shares outstanding*. If there are 1,000,000 total shares and you hold 600,000, you own 60%. The percentage — not the raw share count — is what matters, because it's your share of the whole.
- **Shares can be issued.** Critically, a company can *create and issue new shares* — the total isn't fixed. When it does (to raise money, or for employees), the total share count *grows*, which changes everyone's percentage even though their share *count* is unchanged. This is the key mechanism behind dilution (below), and the thing that surprises people.
- **Different share types exist.** Founders and employees typically hold *common* stock; investors typically get *preferred* stock, which carries special rights (like liquidation preferences — the term-sheet post). For now, the key point is just that equity = shares = proportional ownership, and that new shares can be created.

The mental shift that matters: **ownership is a *percentage of a changeable total*, not a fixed slice.** You don't own "60%" as a permanent fact — you own 600,000 shares, which is 60% *of the current total*, and that percentage changes when the total changes. This reframing is the foundation for understanding dilution, which trips up people who think of ownership as a fixed pie.

## The cap table

The **capitalization table** (cap table) is the record of *who owns what* — every shareholder, how many shares they hold, and therefore what percentage of the company each owns:

- **What it tracks.** All the equity: founders' shares, investors' shares, the employee option pool, and everyone's resulting ownership percentages. It's the authoritative picture of the company's ownership at any point.
- **It changes with every equity event.** Each funding round, option grant, or share issuance updates the cap table — new shares are added, and percentages recalculate. So the cap table is a living document that tells the current ownership story, and modeling how it *will* change (with a new round, say) is how founders understand the impact of raising *before* they do it.
- **Why it matters to founders and employees.** The cap table is where you see what you actually own — and what you *will* own after future rounds. Founders use it to understand and plan dilution; employees use it (and the total share count) to understand what their shares/options are really worth as a fraction of the company. Being able to read a cap table is essential financial literacy for anyone with startup equity.

The cap table is simply the ledger of ownership, but it's the tool that makes dilution and ownership concrete and plannable. Every funding decision shows up as a change to the cap table, so understanding it is understanding the ownership consequences of your choices.

## Dilution: the key concept

**Dilution** is the reduction in existing owners' *percentage* ownership when new shares are issued. It's the single most important — and most misunderstood — ownership concept in funding:

- **How it works.** When a company issues *new* shares (to investors in a round, or to the option pool), the total share count grows, so existing shares now represent a *smaller percentage* of the larger total. Your share count is unchanged, but your *percentage* drops because the pie now has more slices. That percentage reduction is dilution.
- **A simple illustration.** Suppose you own all 1,000,000 shares (100%). You raise money by issuing 250,000 *new* shares to an investor. Now there are 1,250,000 total shares; you still hold 1,000,000, but that's now 80%, and the investor holds 20%. You were "diluted" from 100% to 80% — not by losing shares, but because new shares were created. Every round does this to everyone who came before.

```text
   Before round:  you own 1,000,000 / 1,000,000 = 100%
   Issue 250,000 new shares to investor:
   After round:   you own 1,000,000 / 1,250,000 = 80%   (investor: 250,000 = 20%)
   → your share count unchanged; your percentage fell because the total grew
```

- **It compounds across rounds.** Each round dilutes everyone who came before (founders, earlier investors, employees). Over several rounds, founders' ownership steadily decreases — it's normal for founders to own a much smaller percentage after several rounds than they started with. This isn't a mistake; it's the arithmetic of raising money by issuing shares.
- **Dilution isn't inherently bad.** The founder's bet (from post one) is that dilution is *worth it* if the capital grows the company enough — a smaller percentage of a much more valuable company can be worth far more than a larger percentage of a small one. Dilution is the *cost* of the capital; the question is whether the capital creates more value than the ownership it costs.

Understanding dilution — that raising money issues new shares that shrink everyone's percentage — is the crux of ownership literacy. It's why founders think carefully about how much to raise and at what valuation (which sets *how much* dilution a given amount of money causes — the next post), and why "we're giving up 20%" understates the cumulative effect across many rounds.

## The option pool

One more piece of the cap table specifically affects founders and employees: the **option pool** (or ESOP — employee stock option pool) — shares set aside to grant to employees as equity compensation.

- **What it is.** Startups reserve a chunk of equity (commonly a meaningful percentage) to give employees stock options — the right to buy shares — as part of compensation, to attract talent and align employees with the company's success. This pool sits on the cap table as reserved (and then granted) shares.
- **It's dilutive too.** Creating or expanding the option pool issues/reserves new shares, which dilutes existing owners just like an investment round does. So the pool is a form of dilution — one that benefits employees. Founders should account for it in their dilution planning.
- **The "option pool shuffle."** A subtle but important point for founders: investors often require the option pool to be *created or expanded before* their investment (so the new pool dilutes the *founders*, not the incoming investors). This detail — whether the pool comes out of the pre-money or post-money — materially affects founder dilution, and it's a commonly-overlooked term worth understanding when raising.
- **What it means for employees.** For employees with options, what matters is the *number of shares* relative to the *total* (the percentage of the company), not just a share count — and that their options will be diluted by future rounds too, like everyone's. Understanding the total share count and future dilution is essential to valuing an equity offer realistically.

Equity is ownership in shares; the cap table tracks who owns what; dilution is the shrinking of everyone's *percentage* as new shares are issued each round (normal, compounding, and worth it if the capital grows the company enough); and the option pool is reserved employee equity that's also dilutive. Together these are the ownership mechanics under every funding round. Next: valuation — which determines how *much* ownership a given amount of money costs.

## Key takeaways

- Equity is ownership divided into shares, and your ownership is a *percentage of the total shares outstanding* (your shares ÷ total) — and because companies can issue new shares, that total isn't fixed, so ownership is a percentage of a *changeable* total, not a permanent fixed slice (the key mental shift).
- The cap table is the living record of who owns what (founders, investors, option pool, and their percentages); it updates with every equity event, and reading/modeling it is how founders understand dilution before raising and how employees understand what their shares are really worth.
- Dilution is the reduction in existing owners' *percentage* when new shares are issued: your share count stays the same but your percentage drops because the total grew (e.g. issuing 250K new shares on 1M turns your 100% into 80%) — it compounds across rounds (founders normally own much less after several rounds) and isn't inherently bad.
- Dilution is the *cost* of capital, and the founder's bet is that it's worth it — a smaller percentage of a much more valuable company can be worth far more than a large percentage of a small one — which is why how much you raise and at what valuation (the dilution-per-dollar) matters so much.
- The option pool (reserved employee equity) is also dilutive; investors often require it expanded *before* their investment so it dilutes founders not them (the "option pool shuffle"), and employees should value equity offers by share count relative to the *total* (percentage) and account for future dilution.

## Further reading

- [Cap table (Wikipedia)](https://en.wikipedia.org/wiki/Cap_table)
- [Stock dilution (Wikipedia)](https://en.wikipedia.org/wiki/Stock_dilution)
- [The funding stages (previous post)](/blog/posts/fund-02-funding-stages.html)
