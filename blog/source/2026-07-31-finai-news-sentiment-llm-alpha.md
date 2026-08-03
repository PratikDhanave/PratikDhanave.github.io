# News-Driven Alpha: LLM Sentiment Analysis for Markets
*Turning a firehose of unstructured headlines into a disciplined, point-in-time trading signal.*

Markets react to information, and a large share of that information arrives as text: wire stories, regulatory filings, earnings commentary, and the endless churn of the web. For decades, quantitative desks have tried to squeeze a tradable signal out of this stream using keyword lists and bag-of-words sentiment. Large language models change the economics of that problem. They can read a paragraph, understand *which* asset it concerns and *what* actually happened, and produce a structured judgment that a downstream engine can act on. The hard part is not calling a model. The hard part is building a pipeline that is fast, honest about time, and skeptical of its own inputs.

This post walks through that pipeline end to end: ingestion and deduplication, entity and event extraction, sentiment and impact scoring, aggregation into a per-asset time series, and the constraints that keep the whole thing from quietly lying to you.

## The shape of the pipeline

At a high level the flow is a straight line with a few reference inputs feeding in and a quantitative engine waiting at the end.

```
 Sources            Ingest         Understand         Signal            Consume
 ┌─────────┐                                                          ┌───────────┐
 │ news    │──raw articles──┐                                    ┌───▶│ signal    │
 │ feeds   │                │                                    │    │ store     │
 └─────────┘                ▼                                    │    └───────────┘
 ┌─────────┐  primary   ┌────────┐ clean  ┌────────┐ scored ┌────────┐    │ feature
 │ filings │──docs─────▶│ dedup +│──docs─▶│ LLM    │─events▶│  PIT   │────┘   ▼
 │ + wires │            │ cluster│        │ extract│        │ signal │  ┌───────────┐
 └─────────┘            └────────┘        │ + score│        │ builder│  │ strategy  │
 ┌─────────┐  ticker +      ▲             └────────┘        └────────┘  │ engine    │
 │ asset   │──alias map─────┘                                           └───────────┘
 │ universe│                                                    price + factors ▲
 └─────────┘                                            ┌───────────┐           │
                                                        │ quant     │───────────┘
                                                        │ factors   │
                                                        └───────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-news-sentiment-llm-alpha.html)** — News-to-signal data flow: ingest and dedup, LLM extraction and scoring, point-in-time aggregation, and a blended trading signal.

## Ingestion and deduplication

The first job is to turn a chaotic set of sources into a clean stream of distinct stories. A single corporate event can produce dozens of near-identical articles within minutes as it is syndicated across outlets. If you score all of them, you overweight whatever happened to get republished most, which is a popularity signal, not an information signal.

Deduplication has two layers. Exact duplicates are cheap: hash the normalized body text and drop repeats. Near-duplicates are harder because a wire story gets lightly reworded, retitled, and re-summarized. A practical approach is to embed each article and cluster by cosine similarity within a short time window, then keep one canonical representative per cluster while retaining a count of how many outlets carried it. That count is itself useful metadata later, but it should never be confused with the sentiment itself.

Every document must carry a precise ingestion timestamp and, where available, the original publication time. These two clocks differ, and the gap matters. A story republished today about an event from last quarter is stale news wearing a fresh timestamp, and the pipeline needs to know the difference before it lets that item move a signal.

## Entity and event extraction

Once you have distinct stories, the model's first task is comprehension, not opinion. Given a document, extract a structured record: which assets are involved, what type of event occurred, and the direction of that event. This is where a language model earns its keep, because the same sentence can mention several companies in different roles. A supplier warning is bullish or bearish depending on which side of the relationship you hold.

Resolving names to tradable instruments is its own discipline. Free text says "the chipmaker" or uses a brand name that maps to a parent entity that trades under a different ticker. You anchor extraction against a maintained asset universe: a reference table of instruments with their aliases, subsidiaries, and known ambiguous names. The model proposes an entity; the resolver confirms it exists and is tradable before anything downstream trusts it. This step is your primary defense against the most dangerous failure mode in the whole system, which we will get to shortly.

## Sentiment and impact scoring

Sentiment alone is a weak signal. "Positive" tells you tone, not magnitude, and not relevance. A far stronger design asks the model for several fields at once: a directional sentiment, an estimated *impact* on the asset, and a *confidence* in its own reading. Impact captures the difference between a routine product mention and a surprise earnings miss. Confidence lets you discount hedged, speculative, or thinly sourced text automatically.

The scores need to be calibrated to be comparable across thousands of items. A number the model emits in isolation drifts; the same event described two ways can score differently. Anchoring the prompt with a fixed rubric and a handful of graded reference examples tightens this considerably. It also helps to force structured output so every item returns the same fields in the same shape, which makes the aggregation stage trivial and auditable. Keep the raw model output alongside the parsed score so a human can always trace a signal back to the sentence that produced it.

## Aggregation into a per-asset signal

Individual scored events are noisy. The tradable object is a smooth, per-asset time series that reflects the balance of recent information. Aggregation nets bullish against bearish items, weights each by impact and confidence, and applies a time decay so that a headline's influence fades over hours or days rather than persisting forever. The decay half-life is a genuine tuning parameter: too short and you chase noise, too long and you are trading yesterday's news.

This stage is also where the single most important rule lives. Every event is stamped with an *as-of* time, and the signal at any moment may only incorporate information that had actually arrived by that moment. This sounds obvious and is violated constantly. Look-ahead leaks in through publication timestamps that get revised, through backfilled data, and through models that were trained on text describing the very period you are testing. A backtest that quietly peeks at the future produces gorgeous returns that evaporate in production. The discipline is to store the signal itself point-in-time, so that a backtest replays exactly the series a live system would have seen, no more.

## Combining with the quantitative engine

The news signal is one input, not a strategy. It is most valuable when blended with conventional quantitative factors: price momentum, volatility, liquidity, and the rest. The strategy engine consumes the sentiment feature alongside these numeric factors, decides sizing, and manages risk. Treating the qualitative signal as just another factor keeps it honest, because it now has to earn its weight against everything else rather than being trusted on its own narrative appeal.

Latency shapes how you can use it. If your edge is reacting faster than the market fully prices an event, the whole pipeline from ingestion to signal update must run in seconds, which pushes you toward lighter extraction and streaming aggregation. If your horizon is days, you can afford heavier analysis and batch scoring. Neither is wrong; they are different products, and conflating them leads to a system that is too slow to be fast and too shallow to be deep.

## Pitfalls worth naming

Three failure modes deserve permanent vigilance. **Stale news** re-enters as fresh and double-counts an event; guard against it with strict event timestamps and dedup that spans a wide enough window. **Source bias** means some outlets are systematically breathless or systematically late; weight sources by demonstrated reliability rather than treating every byline as equal. And most insidiously, **hallucinated tickers**: a model confidently attributes an event to an instrument that the text never mentioned, or invents a symbol outright. This is why extraction must be validated against a real asset universe and why an unresolved entity should drop the item rather than guess. A single hallucinated ticker that reaches the strategy engine can put on a position based on news that does not exist. In a pipeline that turns words into trades, that is the difference between a signal and a liability.
