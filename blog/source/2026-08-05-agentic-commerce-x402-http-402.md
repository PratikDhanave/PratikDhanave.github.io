# x402: Paying Over HTTP 402 with Stablecoins
*How Coinbase revived a dormant status code so software agents can pay for what they use, one request at a time.*

For most of the web's history, HTTP 402 has been a placeholder. Open the spec and you find "Payment Required" listed right next to 401 and 404, followed by a note that it is reserved for future use. Browsers never surfaced it, frameworks never returned it, and a whole generation of engineers learned to treat it as a curiosity. The economics of the web went a different way: pay with a subscription, pay with an ad impression, or pay with your attention, but almost never pay per request.

That gap is starting to matter now that the clients hitting our APIs are not always people. When an autonomous agent needs a market data snapshot, a document parse, or a single inference call, the human-shaped billing rails around it feel absurd. There is no one to enter a card number, click through a checkout, or manage a monthly plan. **x402**, an open payment protocol from **Coinbase** and the x402 Foundation, takes the obvious-in-hindsight step: it makes 402 do exactly what its name promised, so a service can charge for a resource at the moment it is requested and settle the payment onchain in seconds.

## Why 402 is back

The idea is not to invent a new payment surface but to use the one HTTP already has. A server that wants payment for a resource answers the request with a 402 status and a machine-readable body describing the terms: how much, in what asset, to which recipient address, on which network. That is the entire handshake from the server's side. No redirect to a hosted checkout, no session to maintain, no account to provision first.

What changed is the client. A modern agent can read a structured 402 challenge, decide whether the price is acceptable against its budget, produce a signed payment, and retry, all without a human in the loop. Pair that with stablecoins, which hold a predictable value, and you have a per-call payment that is small enough and fast enough to be worth doing for a single API hit. The status code was always the easy part; the ecosystem to answer it is what took twenty-five years to arrive.

## The flow, step by step

The whole exchange is a short round trip. The agent asks, the server names a price, the agent pays and asks again, a facilitator confirms the money moved, and the data comes back.

```
Agent                Server               Facilitator          Blockchain
  |                    |                       |                    |
  |  GET /resource     |                       |                    |
  |------------------->|                       |                    |
  |  402 + pay terms   |                       |                    |
  |<-------------------|  (amount, asset,      |                    |
  |                    |   recipient, network) |                    |
  |                    |                       |                    |
  | [sign stablecoin tx offchain]              |                    |
  |                    |                       |                    |
  |  retry + payment proof                     |                    |
  |------------------->|  verify payment       |                    |
  |                    |---------------------->|  settle transfer   |
  |                    |                       |------------------->|
  |                    |                       |  confirmed onchain  |
  |                    |                       |<-------------------|
  |                    |  valid + settled      |                    |
  |                    |<----------------------|                    |
  |  200 + data        |                       |                    |
  |<-------------------|                       |                    |
```

> **▸ [Open the interactive diagram](/blog/diagrams/agentic-commerce-x402-http-402.html)** — the x402 request → 402 → sign → retry → verify/settle → data sequence, with the facilitator and chain roles broken out.

Walking through it: the agent makes an ordinary GET. The server returns **402** with the payment instructions rather than the data. The agent constructs and signs a **stablecoin** transaction that satisfies those terms, then **retries** the same request with the signed payment proof attached. The server hands that proof to a **facilitator**, which verifies it and settles the transfer onchain. Once settlement confirms, the server returns **200** and the actual payload. No credit card, no login, no subscription account is created anywhere in that path, and the cycle completes in seconds.

## The facilitator's role

The one piece that keeps the server simple is the facilitator. Verifying a payment proof and settling a transfer onchain is real work: it means understanding the network, watching for confirmation, and handling the mechanics of moving stablecoins. x402 pushes that responsibility to a facilitator service so the resource server does not have to become a blockchain node operator to sell an API call.

From the server's point of view the contract is small. It emits the 402 terms, receives a proof on the retry, asks the facilitator "is this good, and did it settle?", and gates the response on the answer. The facilitator absorbs the onchain complexity. That separation is what lets an ordinary web service adopt per-request payments without rebuilding its stack around a wallet.

## Why stablecoins and onchain settlement

Two design choices make the per-call model actually work. The first is settling **onchain**, which gives the payment finality without a central intermediary reserving the right to claw it back. The second is denominating in **stablecoins**, which sidesteps the volatility that would otherwise make a token-priced API unusable. A caller paying a fraction of a cent for one request needs that fraction to still mean the same thing a minute later.

The combination has properties card rails struggle to match at small sizes. There are no chargebacks, because settlement is final. There is no minimum that makes a sub-cent charge uneconomical, because there is no interchange fee eating the transaction. And it is global by default: any wallet on the supported network can pay, with no merchant account, currency conversion, or regional gateway in between. x402 itself charges **zero protocol fees**, and the traction shows the model is being used in earnest, with over **119M transactions on Base**, **35M on Solana**, and roughly **$600M in annualized volume** as of early 2026.

## Where it fits: API monetization and agents paying agents

Two use cases stand out. The first is straightforward **API monetization**. A data provider or tool endpoint can price access per request and collect it inline, without building a billing portal, issuing keys, or reconciling invoices. The pricing lives in the 402 response, and the money arrives with the retry.

The second is more distinctly new: **machine-native micropayments**, where one agent pays another agent or a service directly. When an orchestrating agent fans out to specialized tools, each of those tools can charge for its work and be paid on the spot. That is a market that human-mediated checkout simply cannot serve, because there is no human in the loop to mediate.

## Trade-offs versus card rails

x402 is not a drop-in replacement for card payments; it is a better fit for a specific shape of transaction. The upside is finality with no chargebacks, sub-cent economics, and a self-serve global reach. The cost is that finality cuts both ways: there is no chargeback to protect a buyer who is defrauded, so dispute handling has to live at the application layer if you need it. The client also has to manage a wallet and its keys, which is a real operational and security responsibility rather than a stored card on file. Stablecoins handle the volatility problem that would otherwise sink the idea, but they introduce their own dependencies on the asset and the network. For a large, disputable, human purchase, card rails still make sense. For a tiny, automated, per-call charge, they mostly do not.

## How it plugs into A2A and AP2

x402 does not have to stand alone. There is an **A2A x402 extension**, developed with contributors including Coinbase, the Ethereum Foundation, and MetaMask, that brings this payment handshake into agent-to-agent communication so paying is part of how agents already talk to each other. And AP2, the agent payments effort in the broader agentic-commerce space, can use x402 as its crypto settlement path. The picture that emerges is layered: agent protocols handle intent and coordination, while x402 handles the "money actually moved" step underneath, onchain, when that is the right rail.

## What to remember

x402 takes the status code the web reserved and never used, and finally answers it. A request meets a 402 with machine-readable terms; the client signs a stablecoin payment and retries; a facilitator verifies and settles onchain; the data comes back. It shines exactly where card rails are awkward: tiny, automated, per-request payments between software. The status code was ready decades ago. What arrived recently is the client that can read it, the asset stable enough to price against, and the settlement fast enough to make a single API call worth charging for.

## Sources

- https://www.coinbase.com/developer-platform/discover/launches/x402
- https://docs.cdp.coinbase.com/x402/welcome
