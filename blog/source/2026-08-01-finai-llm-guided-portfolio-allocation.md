# LLM-Guided Portfolio Allocation

*A hybrid allocator where a quantitative core owns the money, a language model only whispers tilts, and hard constraints plus a human bound everything before a single order goes out.*

There is a seductive demo that makes the rounds every so often: you paste a week of headlines into a chat window, ask "how should I position the book," and the model returns a confident, well-written set of weights. It reads beautifully. It is also the single most dangerous way to use a language model in asset management, because it hands a probabilistic text generator direct authority over capital while giving you nothing you could defend to a risk committee. The interesting question is not whether language models have anything useful to say about portfolios — they do — but how to capture that value without ever letting the model be the thing that decides how money moves.

The design that works is a hybrid one. A quantitative core sets a defensible baseline. The language model is kept strictly advisory: it proposes *tilts* and *views* from the qualitative context a pure optimizer cannot read. Then hard risk constraints and a human sign-off bound the result before anything reaches an execution venue. Each layer distrusts the one before it, and the model never gets a hand on the money.

## The quant core owns the baseline

Everything starts with a number the model never produces: a baseline set of weights from a deterministic optimizer. Depending on the mandate this is mean-variance optimization, risk parity, or a views-based construction where subjective opinions are blended into equilibrium returns in a principled, weighted way. The specific method matters less than the property it gives you: the starting portfolio is reproducible, explainable, and owned by a process with a clear mathematical rationale.

This baseline is doing more than producing weights. It anchors the entire system. The language model is never asked to fill an empty portfolio from a blank page, where its errors would be unbounded and its confidence unearned. It is only ever allowed to propose *deltas* — small, bounded adjustments away from a portfolio that already stands on its own. If every downstream layer failed and you shipped the baseline untouched, you would still have a coherent, risk-aware allocation. That is the whole point of anchoring: the worst case is "the quant portfolio," not "whatever the model imagined."

## Where the language model actually helps

If the optimizer is so good, why involve a model at all? Because optimizers are blind to everything that is not already a number. A covariance matrix does not know that a key supplier just issued a going-concern warning, that a regulator opened an inquiry, that management quietly changed guidance language in the latest filing, or that a sector's narrative has shifted in a way that will show up in the data only weeks later. This qualitative context — news, filings, transcripts, disclosures — is exactly where a language model is strong: reading large volumes of unstructured text and distilling it into structured signals.

So the model's job is narrow and well-defined. Given the current baseline and a curated bundle of recent qualitative context, it proposes a small set of tilts: increase this exposure, trim that one, flag this name for elevated uncertainty. Critically, each proposed tilt must arrive with a written rationale that points back to specific source material. A tilt without a traceable "why" is not a suggestion, it is noise, and the system should treat it as such. The model is not forecasting returns with false precision; it is translating text into candidate adjustments that a human and a rules engine will scrutinize.

## Hard constraints are non-negotiable

A proposal is not a decision. Between the model's suggested tilts and any change to the live book sits a deterministic constraint layer, and its checks are absolute rather than advisory. Position limits cap how large any single holding or sector can become. Turnover caps prevent the model's enthusiasm from generating churn that quietly bleeds returns into transaction costs. Liquidity and concentration rules keep the portfolio inside the mandate. Leverage and exposure bounds keep it inside the risk budget.

The essential design choice is that these constraints are code, not prompts. You do not *ask* the model to please respect the limits; you clamp, project, or reject its output against them programmatically. If the tilted portfolio would breach a limit, the breach is caught here, deterministically, every time — not left to the good behaviour of a system that is confidently wrong on a bad day. A tilt that survives this layer is one you already know is inside every hard boundary the mandate defines.

## A human sits on the consequential path

Even a constrained, plausible proposal does not execute on its own. A qualified person reviews it, and — this is the part that makes the review real rather than ceremonial — they see the model's rationale and the underlying context alongside the numbers. The reviewer is not rubber-stamping weights; they are judging whether the *reasoning* holds up, whether the cited context actually supports the tilt, and whether anything about the current environment argues for caution. Routine, small, well-supported adjustments can be approved quickly. Large or unusual ones are genuinely blocking. Only after sign-off does the allocation reach execution, where orders are worked through the normal order-management path.

## What happens when something fails

The branches matter as much as the happy path, because the branches are where discipline is proven. If the constraint layer detects a breach, or the human rejects the proposal, the system does not improvise and it does not push a half-approved portfolio. It falls back to the baseline — the defensible quant weights it started from. The failure mode of the entire apparatus is "trade the anchor," which is a perfectly acceptable outcome, rather than "trade something nobody approved," which is not.

```
  Market Data ─▶ Baseline Weights ─▶ Propose Tilts ─▶ Risk Constraints ─▶ Human Review ─▶ Execute
                       ▲              ▲  (LLM,           │ limits/          │ sign-off        Orders
                       │              │   advisory)      │ turnover         │
                  Context ───────────┘                  │ breach           │ reject
              (news / filings)                          ▼                  ▼
                       ▲                              ┌───────────────────────┐
                       └──────────────── fall back ──│   Reset to Baseline    │
                                                      └───────────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-llm-guided-portfolio-allocation.html)** — the advisory allocator: quant baseline, LLM-proposed tilts from qualitative context, hard risk constraints, human sign-off, and a breach-or-reject fall back to the baseline.

Notice what the shape refuses to allow. The model has no path to place an order. Its output is always a proposal, never an instruction. The constraint layer is deterministic and blocking. The human sits *on* the consequential path, not beside it as an optional courtesy. Even a model that hallucinates a tilt, is fed a manipulated news item, or is coaxed by a crafted prompt cannot do more than emit a suggestion that fails a hard check or a human rejects.

## The trade you are making

None of this is free. You are accepting extra latency, extra engineering, and the humility of never letting the smartest-sounding component be in charge. In return you get something you can actually run against real capital: an allocator that reads the qualitative world a pure optimizer ignores, while remaining explainable, bounded, and reversible. The model earns its place not by being trusted, but by being useful inside a structure that assumes it will occasionally be wrong. That is the difference between a demo that impresses a room and a system you can put in front of a risk committee — and in this domain, only the second one is worth building.
