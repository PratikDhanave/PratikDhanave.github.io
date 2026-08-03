# Securities Lending and Repo: Financing the Balance Sheet

*Two ways to borrow against securities — a lending fee or a repo rate — and the daily collateral servicing that keeps both alive.*

Every large book of securities is also a source of financing. If you own bonds or equities, you can lend them out for a fee, or you can sell them today and promise to buy them back tomorrow at a slightly higher price. The first is **securities lending**; the second is a **repurchase agreement**, or **repo**. Both are, underneath the wrapper, collateralized loans. For an engineer building the systems that run them, the interesting part is not the trade itself — it is the daily servicing that keeps the collateral matched to the exposure until the trade unwinds.

## Two instruments, one shape

**Securities lending** moves a specific security. A holder lends a stock or bond to a borrower, who posts collateral in return and pays a **lending fee** for the privilege. Why borrow a security at all? Usually to cover a short sale, or to deliver into a settlement that would otherwise **fail**. The lender keeps economic ownership — dividends and coupons are passed back as **manufactured payments** — but earns incremental yield on an asset that would otherwise sit idle.

**Repo** starts from the other side: you need cash, and you own securities. You sell them now and simultaneously agree to buy them back on a future date at a pre-agreed price. The difference between the sale price and the buy-back price, annualized, is the **repo rate** — the interest on what is effectively a secured loan. The buyer of the securities is the cash lender; they hold your bonds as collateral until you repay.

The two instruments are mirror images. In securities lending the driver is *the security* (someone needs that exact ISIN); in repo the driver is usually *the cash* (someone needs funding). But both leave one party holding an asset as protection against the other defaulting, and both must be serviced daily.

## Collateral mechanics: haircuts, margin, mark-to-market

Collateral can be **cash** or **non-cash** (other bonds, equities, or a basket). Cash collateral is reinvested by the lender, who returns a **rebate** rate to the borrower; non-cash collateral just sits in a segregated account and the borrower pays an outright fee.

Because the collateral itself can lose value, you never accept it one-for-one. You apply a **haircut**: to secure a 100 loan you might demand 105 of government bonds or 115 of equities. The haircut sizes the buffer to the collateral's volatility and liquidity. The required collateral value is then:

`required = exposure x (1 + haircut)`

Every day, both legs are **marked to market**. The loaned securities are revalued, the posted collateral is revalued, and the system compares the two. If the collateral has fallen below the required level, the exposed party issues a **margin call** for **variation margin**; if it has risen too far above, the over-collateralized party returns the excess. This daily cycle — revalue, compare, call — is the heartbeat of the whole business.

## The daily lifecycle

A single trade walks through a predictable state machine:

1. **Open.** Securities are delivered against collateral (ideally delivery-versus-delivery so neither side is briefly unsecured). The trade is booked as **term** (fixed end date) or **open** (rolls indefinitely until either side ends it).
2. **Mark.** Overnight, both legs are revalued at fresh prices.
3. **Margin.** A shortfall triggers a margin call; the borrower posts more collateral, or the lender returns excess.
4. **Recall / substitution.** The lender can **recall** the security if they need to sell it or vote it; the borrower can **substitute** one piece of collateral for another it would rather use elsewhere.
5. **Return.** At maturity or recall, securities come back, collateral is released, and the accrued fee or repo interest settles.

```
   Lender / Cash Provider          Tri-party Agent          Borrower / Collateral Provider
            |                            |                              |
   OPEN     |--- deliver securities ---->|                              |
            |                            |<---- post collateral + HC ---|
            |                            |------ release securities ---->|
            |                            |                              |
   DAILY    |                            |=== mark-to-market (both) ===|
            |                            |------ margin call: short ---->|
            |                            |<---- post variation margin ---|
            |                            |                              |
   CLOSE    |------ recall securities -->|                              |
            |                            |<------ return securities -----|
            |<---- return securities ----|                              |
            |                            |-- return collateral + fee -->|
            v                            v                              v
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-securities-lending-repo.html)** — the full securities-lending / repo lifecycle: open the trade, daily mark-to-market and margin call, then recall and return through a tri-party agent.

## Rehypothecation and collateral chains

Collateral rarely sits still. **Rehypothecation** is the right to re-use collateral you have received — the borrower's collateral becomes the raw material for the recipient's own trades. This is enormously capital-efficient: one bond can back a chain of transactions. It is also where hidden leverage lives. If A posts to B, B re-uses it with C, and C with D, then a default anywhere in the chain can leave several parties scrambling for the same piece of collateral. Systems must track not just *what* collateral is held but whether it is **re-usable**, and follow the chain far enough to know real exposure.

## Engineering it

Three components carry most of the weight:

- **Position and collateral ledger.** The source of truth for what is lent, what is posted, and who has title. It must handle partial returns, substitutions, and the split between economic and legal ownership. Model collateral as its own tracked inventory, not a footnote on the loan record.
- **Margin engine.** A daily (often intraday) batch that pulls fresh prices, recomputes `exposure x (1 + haircut)` per agreement, nets across a counterparty where a master agreement allows it, and emits margin calls. Idempotency matters: a re-run on the same prices must produce the same calls, not duplicate them.
- **Fails and settlement tracking.** Deliveries do not always settle on time. A **fail** — securities that did not arrive — must be detected, aged, and sometimes resolved by borrowing more securities, which loops you back to the start.

Prices, corporate actions, and reference data feed all three, and they are the usual source of bad margin calls.

## Pitfalls

- **Fails cascade.** One failed delivery can force a chain of borrows to plug the gap; treat fails as first-class events, not exceptions swept into a log.
- **Collateral optimization is a trap and a prize.** Posting your cheapest eligible collateral (the "cheapest-to-deliver") saves money, but an over-aggressive optimizer can leave you holding illiquid junk when you suddenly need to move. Constrain it with eligibility and concentration limits.
- **Recall races.** A recall issued the same day the borrower initiates a substitution can leave two workflows fighting over the same position. Serialize state transitions on a trade and make recall authoritative.
- **Stale marks.** A missing price silently under-calls margin. Fail loud on missing or stale prices rather than defaulting to yesterday's number.

## What to remember

Securities lending and repo are the same idea wearing different clothes: a **collateralized loan** priced as a fee or a repo rate. The trade is the easy part. The system's real job is the daily loop — mark to market, size the haircut, call the margin, honor recalls and substitutions, and chase fails — while tracking collateral re-use carefully enough that you always know your true, un-netted exposure. Build the collateral ledger and the margin engine to be boringly correct, and everything else is servicing on top.
