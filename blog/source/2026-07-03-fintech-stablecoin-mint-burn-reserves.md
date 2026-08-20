# Engineering a Fiat-Backed Stablecoin: Mint, Burn, and the Reserve Invariant

*How to engineer a fiat-backed stablecoin: mint-on-deposit and burn-on-redeem flows tied to a reserve ledger, a 1:1 reserve invariant, and continuous reconciliation between on-chain supply and off-chain custody balances.*

A fiat-backed stablecoin is, from an engineering standpoint, a distributed ledger problem with an unusually unforgiving correctness requirement. Two ledgers must agree at all times: the off-chain reserve ledger that tracks fiat held in custody, and the on-chain token supply that anyone can read from a public blockchain. Every unit of circulating token must be backed by a unit of reserve. If the two drift, the product is either insolvent or accidentally giving money away. Everything else in the system exists to protect that single equality.

This post walks through the moving parts: the mint and burn flows, the reserve ledger they hinge on, and the reconciliation loop that keeps the two sides honest.

## The reserve invariant

The core invariant is simple to state and worth writing down as a first-class check rather than an aspiration:

```text
backed_reserve >= circulating_supply     # 1:1 backing — alarm the instant circulating_supply > backed_reserve
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-stablecoin-mint-burn-reserves.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Here `backed_reserve` is not the raw cash balance. It is the portion of custody funds explicitly earmarked against issued tokens, net of pending mints and pending burns. Fees, interest earned on reserves, and operating float sit in separate ledger accounts so they never inflate the backing figure. The mistake teams make early is treating the bank balance as the backing number; the moment you earn yield or collect a redemption fee, the raw balance and the token supply diverge for legitimate reasons, and your invariant check starts screaming.

The flow that maintains this equality looks like this end to end:

```
 FIAT IN                       ON-CHAIN
 deposit ─▶ reserve ledger ─▶ mint svc ─▶ token contract
                 ▲                              │
 redeem ─▶ burn svc ◀──────── burn tx ──────────┘
                 │                              │
             reserve debit          on-chain supply
                 │                              │
                 └────────▶ reconciliation ◀────┘
                                  │
                             attestation
```


The left edge is fiat entering and leaving custody. The right edge is the public token supply. Reconciliation sits at the seam, and attestation is what you publish so holders can trust the seam without seeing your books.

## Mint on deposit

Minting is the sequence that turns received fiat into tokens. The ordering is the whole game: you credit the reserve ledger *before* you mint on chain, never after. If the chain call succeeds but the ledger write is lost, you have issued unbacked tokens. If the ledger write commits but the mint fails, you are merely holding fiat you have not tokenized yet, which is recoverable.

A safe mint is a small state machine keyed on the deposit reference:

```python
def process_deposit(deposit):
    # 1. Confirm funds actually settled in custody (not just initiated)
    if not custody.is_settled(deposit.reference):
        return  # wait; re-driven by the settlement webhook

    # 2. Reserve ledger credit — idempotent on deposit.reference
    entry = ledger.credit(
        account="reserve_backing",
        amount=deposit.amount,
        idempotency_key=f"mint:{deposit.reference}",
    )

    # 3. Only now request the on-chain mint
    mint = chain.mint(
        to=deposit.wallet,
        amount=deposit.amount,
        idempotency_key=f"mint:{deposit.reference}",
    )
    ledger.link_onchain_tx(entry.id, mint.tx_hash)
```

Two details make this robust. First, `is_settled` must mean the fiat has cleared, not that a transfer was requested — provisional credit that later reverses would leave tokens backed by nothing. Second, the same `idempotency_key` guards both the ledger credit and the chain mint. Deposit webhooks retry; blockchain submissions get replayed after timeouts. Keying both writes on the immutable deposit reference means a replayed message is a no-op instead of a double mint.

Confirmation depth matters too. A mint transaction is not "done" when it is broadcast; it is done when it has enough confirmations that a chain reorganization will not orphan it. Until then the ledger entry stays in a `pending_onchain` state and is excluded from the backing total.

## Burn on redemption

Redemption is mint in reverse, and its ordering flips accordingly: burn the tokens on chain *first*, then release the fiat. If you paid out fiat and the burn failed, the holder keeps both the cash and the tokens.

```python
def process_redemption(redeem):
    # 1. Burn on chain first — removes tokens from circulation
    burn = chain.burn(
        amount=redeem.amount,
        idempotency_key=f"burn:{redeem.id}",
    )

    # 2. After the burn finalizes, debit reserve and pay fiat
    if chain.is_final(burn.tx_hash):
        ledger.debit(
            account="reserve_backing",
            amount=redeem.amount,
            idempotency_key=f"burn:{redeem.id}",
        )
        custody.payout(redeem.bank_account, redeem.amount)
```

The window between burn and payout is the one place where circulating supply legitimately runs *below* backed reserve. That is the safe direction — the tokens are gone, the fiat is still in custody waiting to leave. Your invariant check should therefore tolerate `backed_reserve >= circulating_supply` transiently and only alarm on the dangerous inequality, `circulating_supply > backed_reserve`, which means tokens exist that reserves do not cover.

## Reconciliation: supply versus reserve

The two flows above are correct in isolation, but distributed systems drift. A missed webhook, a stuck transaction, a manual ledger correction — any of these can nudge the two ledgers apart. Reconciliation is the continuous job that reads both sides and classifies the gap.

It has three inputs: the on-chain `totalSupply` read directly from the token contract, the `backed_reserve` figure from the ledger, and the set of in-flight mints and burns that have not yet finalized. The reconciled equation accounts for the in-flight items:

```
totalSupply == backed_reserve + pending_burns - pending_mints  (± dust)
```

When the equation holds within a tiny tolerance for rounding dust, all is well. When it does not, the engine classifies the break by cause — an unfinalized mint waiting on confirmations (self-heals), a burn whose ledger debit never ran (a stuck job to replay), or a genuine unexplained delta (page a human immediately). Running this every block, not once a day, means a divergence is caught in seconds rather than after it has compounded. The classification matters as much as the detection: an operator woken at 3 a.m. needs to know whether to wait, replay, or freeze issuance.

## Attestation and proof of reserves

Holders cannot see your custody statements, so trust has to be manufactured. Attestation is the process of proving the reserve side of the invariant to outsiders. The engineering job is to make the reserve figure *provable* rather than asserted: snapshot the reserve ledger at a fixed block height, capture the corresponding on-chain `totalSupply` at that same height, and export both with the account breakdown that reconciles them.

Anchoring the snapshot to a specific block height is what makes the two numbers comparable — an auditor or a smart contract can independently read `totalSupply` at that block and check it against the attested reserve. The stronger the anchoring, the less anyone has to take your word for it. Some designs push this on chain entirely, publishing a signed reserve figure that the contract itself can compare against its own supply before permitting further mints.

## What holds it together

Strip away the blockchain novelty and this is disciplined double-entry accounting with a public counterparty. The reserve ledger is the source of truth; the chain is a second ledger you must keep in lockstep. Order writes so that failures leave you over-reserved rather than under-reserved. Make idempotency keys immutable and shared across the ledger and chain writes. Reconcile continuously and classify breaks by cause. Do those four things and the 1:1 invariant holds not because you asserted it, but because every path through the system is built to preserve it.
