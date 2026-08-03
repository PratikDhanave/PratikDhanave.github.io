# Dynamic Currency Conversion at the Point of Sale

*How a foreign cardholder is offered payment in their home currency, who earns the FX margin, and how the choice threads through authorization and clearing.*

A traveler taps a card issued in one currency at a terminal that prices everything in another. Somewhere between the tap and the printed receipt, a decision has to be made: charge the card in the merchant's local currency and let the cardholder's issuer convert it later, or convert it right there at the counter and charge the card in the traveler's home currency. That second path is Dynamic Currency Conversion (DCC), and it is one of the more misunderstood mechanisms in card acceptance. It is not a scam and it is not free money. It is a regulated, disclosure-bound service with a specific data flow, a specific consent gate, and a specific way of splitting the money it generates.

This post walks the engineering of DCC end to end: how the terminal decides a card is eligible, where the rate comes from, why the consent screen is legally load-bearing, who takes the margin, and how the choice is carried through authorization and settlement so every downstream system agrees on what currency the transaction happened in.

## Detecting an eligible card

DCC only makes sense when the card's billing currency differs from the merchant's local currency. The terminal figures this out from the card's Bank Identification Number (BIN), the leading digits of the account number. A BIN lookup table, distributed to the terminal or its gateway, maps BIN ranges to an issuer country and a currency code. When the lookup returns a currency that differs from the terminal's own settlement currency, the card is a DCC candidate.

Two guardrails matter at this step. First, the lookup must be conservative: if the BIN range is unknown or ambiguous, the terminal does not offer DCC and simply processes in the local currency. Second, some card products and some merchant categories are contractually excluded, so the eligibility check is a conjunction of BIN currency, card scheme rules, and merchant configuration, not a single comparison.

```
  Cardholder      Terminal        DCC Provider     Acquirer
  (foreign card)   (POS)           (rate svc)       (auth+clearing)
      |              |                 |               |
      | insert card  |                 |               |
      |------------->| BIN -> foreign  |               |
      |              |--- request rate ->|             |
      |              |<-- rate+margin --|              |
      |  offer home  |                 |               |
      |<-------------| show rate,      |               |
      |              | margin, choice  |               |
      | choose home  |                 |               |
      |------------->|                 |               |
      |              |--- auth + DCC indicator -------->|
      |              |<------------ approved -----------|
      |<-- receipt --|                 |               |
      |              |--- clear + settle ------------->|
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-dcc-dynamic-currency.html)** — pan, zoom, and trace the DCC offer, consent, and settlement path (light/dark, self-contained).

## Sourcing the rate and applying the markup

Once a card is flagged eligible, the terminal requests a quote from a DCC provider's rate service. The provider maintains a reference exchange rate, typically sourced from a wholesale interbank feed or a card scheme's daily rate, refreshed on a schedule that ranges from intraday to once per day depending on volatility and contract.

On top of that reference rate the provider applies a markup, a percentage margin that is the entire commercial reason DCC exists. A reference rate of 1.0850 with a 4% markup becomes a cardholder-facing rate of 1.1284. The rate service returns both numbers: the reference rate and the markup, or equivalently the marked-up rate plus the margin percentage. The terminal needs both because disclosure rules require showing the cardholder exactly what margin they are paying relative to a recognizable benchmark.

The returned quote is time-boxed. The provider commits to honoring the quoted rate for the life of this authorization, which is why the rate is captured now and carried forward rather than re-fetched at settlement. If the authorization is not completed within the quote's validity window, the terminal must re-request rather than settle on a stale rate.

## The disclosure and consent gate

This is the part of DCC that is legally load-bearing, and the part engineers most often get wrong by treating it as a cosmetic screen. Card scheme rules and consumer-protection regulation in most markets require that the cardholder be *offered a genuine choice* and be *shown the economics* before consenting.

Concretely, the consent screen must present:

- The amount in the merchant's local currency.
- The amount in the cardholder's home currency at the quoted rate.
- The exchange rate applied and the margin or markup over the reference rate.
- A clear statement that DCC is optional and that paying in the local currency is available.

Two anti-patterns are explicitly disallowed. The home-currency option must not be pre-selected as a default, and the local-currency option must be presented with equal prominence, not buried. The cardholder makes an active choice, and that choice is recorded. If they decline DCC, the transaction proceeds in the merchant's local currency and the entire rate flow is discarded. Getting this wrong is not a UX nit; it is a compliance failure that can trigger fines and forced refunds.

## Who earns the margin

The markup is not the provider's alone. It is split, by contract, among the parties that make the transaction happen. A representative arrangement divides the margin three ways:

- The **DCC provider** keeps a share for running the rate service, the BIN tables, and the settlement reconciliation.
- The **acquirer** takes a share for routing and for carrying the DCC-flagged transaction.
- The **merchant** receives a rebate, which is the incentive that gets DCC enabled on the terminal in the first place.

The exact split is a commercial term, but the structure explains the whole ecosystem: merchants enable DCC because they earn a rebate on the margin, and providers and acquirers earn on volume. The cardholder pays the full markup regardless of how it is divided downstream, which is exactly why disclosure is mandatory.

## Threading the choice through authorization and clearing

Once the cardholder consents to DCC, the choice has to survive every hop to settlement, because a mismatch between the authorized currency and the cleared currency is a reconciliation break.

The authorization request carries a **DCC indicator** along with the transaction currency and the converted amount. This flag tells the acquirer and, through the scheme, the issuer that conversion happened at the point of sale and that the issuer must *not* convert again. Double conversion, where both the terminal and the issuer apply a rate, is the classic DCC defect and the indicator exists specifically to prevent it. The issuer sees the amount already in the card's billing currency and posts it as-is.

Clearing must then present the same currency, the same amount, and the same rate that were disclosed and authorized. Settlement flows to the merchant in the transaction currency the acquirer supports, with the margin split applied during reconciliation. If the clearing record's currency or rate diverges from what was authorized, the transaction fails scheme validation and lands in an exceptions queue.

```
  Field                     Auth        Clearing    Must match?
  ---------------------------------------------------------------
  transaction currency      home ccy    home ccy    yes
  converted amount          quoted      quoted      yes
  applied FX rate           locked      locked      yes
  DCC indicator             set         set         yes
```

## What the engineering comes down to

DCC looks like a currency feature, but the hard parts are data integrity and consent. Source a rate you can defend against a benchmark, lock it for the authorization, present a fair and un-defaulted choice, record that choice, stamp the DCC indicator so nobody converts twice, and carry an identical currency, amount, and rate from authorization all the way through clearing. Do those six things and the margin split takes care of itself in reconciliation. Miss the consent gate or let the clearing currency drift, and you have turned a legitimate service into a compliance incident.
