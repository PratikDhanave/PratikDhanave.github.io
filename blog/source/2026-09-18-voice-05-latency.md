# Latency: The Make-or-Break Constraint

*Everything about voice AI comes down to one number: how long the user waits to hear a reply. Get it under the threshold where conversation feels natural and the agent is a delight; miss it and no amount of intelligence saves the experience. This post is about the latency budget — where the milliseconds go, and how streaming the entire pipeline turns an additive delay into something that feels instant.*

Latency has shadowed every post so far because it drives every design decision in voice AI. This post confronts it directly: the target, the budget across stages, and the techniques — above all, streaming — that make a chain of models feel like real-time conversation. If there's one post that explains *why* voice agents are built the way they are, it's this one.

## The target: conversational latency

Human conversation has a rhythm. The typical gap between one person finishing and the other starting is remarkably short — on the order of a couple hundred milliseconds — and we're exquisitely sensitive to it. A delay of a second feels like a lag; several seconds feels broken. This sets the bar for a voice agent: **the user should hear the beginning of a response within a fraction of a second of finishing speaking**, to feel natural.

That's a brutal target when the pipeline chains ASR, an LLM, and TTS, each taking real time. The gap between "what conversation expects" and "what a naive cascade delivers" is the central problem — and closing it is what separates a natural voice agent from a frustrating one. Note the emphasis on the *beginning* of the response: the user doesn't need the whole answer instantly, just to start hearing it quickly. That distinction is the escape hatch.

## Where the milliseconds go

The end-to-end latency, from the user finishing to hearing a reply, is the sum of several stages:

- **Endpointing delay** — the time to *decide* the user has stopped (post 2). Conservative endpointing (waiting to be sure) adds directly to perceived latency, so this is a real contributor, not just a preliminary.
- **ASR finalization** — producing the final transcript. With streaming ASR, most of this overlapped the user's speech, so only the tail remains.
- **LLM time-to-first-token** — from sending the transcript to the first response token. Often the single biggest chunk (post 3).
- **TTS time-to-first-audio** — from the first tokens to the first synthesized audio (post 4).
- **Network and playback** — round-trips to model APIs and audio buffering, each adding milliseconds (and telephony adds more, post 8).

Naively, run serially, these *sum*: wait for endpoint, then ASR, then the full LLM response, then full TTS, then play — easily several seconds. That additive total is what makes a naive voice agent feel sluggish, and it's why the design goal is to stop the stages from summing.

## Streaming: turning a sum into an overlap

The core technique — the one that makes voice AI work at all — is **streaming and pipelining every stage** so they overlap instead of running in sequence. Here's a single turn, streamed end to end, with the stages running concurrently:

```
 User        Client         ASR          LLM          TTS
   │ speaks    │              │            │            │
   │──────────▶│ stream audio │            │            │
   │           │─────────────▶│(partials)  │            │
   │ (stops)   │  final transcript (endpoint)           │
   │           │              │───────────▶│ stream tokens
   │           │              │            │───────────▶│ stream audio
   │◀────── plays response ───│◀───────────│◀───────────│
   │  (hears reply within a fraction of a second)        │
```

> **▸ [Open the interactive sequence diagram](/blog/handbook-diagrams/voice-conversation-turn.html)** — pan, zoom, and trace the streamed turn and barge-in (light/dark, self-contained).

The key move: each stage starts working on *partial* output from the previous one instead of waiting for it to finish. ASR streams partial transcripts while the user talks (so it's nearly done at endpoint); the LLM streams tokens (so TTS starts on the first words); TTS streams audio (so playback starts on the first chunk). The stages *overlap in time*, so the user's perceived latency collapses from the *sum* of all stages to roughly the *longest single "time-to-first"* plus a little — often the LLM's time-to-first-token. A pipeline that would take several seconds serially can start speaking in well under a second when fully streamed.

This is why "stream everything" has been the refrain: it's not an optimization, it's the architecture. A voice agent that streams feels real-time; one that doesn't never can, no matter how fast each individual stage is.

## Squeezing the budget further

Beyond streaming, teams shave latency with:
- **Faster/right-sized models** at each stage — a slightly-less-accurate ASR or a faster LLM that hits the budget beats a slower, marginally-better one (the routing/right-sizing idea from the AI-gateway series).
- **Aggressive but smart endpointing** — minimizing the wait-to-be-sure delay without cutting users off (post 6), since endpointing delay is pure perceived latency.
- **Speculative / eager processing** — starting the LLM on a near-final transcript before the absolute end, or pre-warming, to trim the tail. (Trades a little wasted work for latency.)
- **Co-location and connection reuse** — reducing network round-trips between stages; running stages close together; keeping provider connections warm.
- **Filling gaps with sound** — when a real delay is unavoidable (a tool call, post 3), a spoken "let me check that" or a subtle sound keeps the interaction alive rather than dead silence — perceived latency, managed.

The last point is worth its own note: **perceived** latency is what matters, and it can be managed even when actual latency can't be fully eliminated — a filler phrase, an early acknowledgment, or a natural-sounding pause makes a given delay feel far shorter than dead air.

## Why latency defines voice AI

Step back and latency explains the whole design of a voice agent: streaming pipelines, model choices, endpointing tuning, speech-friendly concise LLM output, streaming TTS — nearly every decision in this series traces back to the latency constraint. It's the reason voice AI is *harder* than text AI despite using the same models: text tolerates a multi-second wait; conversation does not. Master latency — by streaming everything, right-sizing models, tuning endpointing, and managing perception — and you have a voice agent that feels alive. Miss it, and you have a very smart system nobody enjoys talking to. Everything else is in service of getting the user to hear a reply, fast.

## Key takeaways

- The target is **conversational latency**: the user should hear the *beginning* of a reply within a fraction of a second of finishing — humans are exquisitely sensitive to turn-gap delay, so multi-second responses feel broken regardless of answer quality.
- End-to-end latency is the **sum** of endpointing + ASR finalization + LLM time-to-first-token + TTS time-to-first-audio + network/playback — run serially, this easily reaches several seconds (why naive voice agents feel sluggish).
- **Streaming/pipelining every stage** is the architecture, not an optimization: each stage works on the previous stage's *partial* output (ASR partials, LLM tokens, TTS chunks), so stages **overlap** and perceived latency collapses from the *sum* to roughly the longest *time-to-first* (often LLM TTFT) — sub-second when fully streamed.
- Squeeze further with **right-sized faster models**, **smart aggressive endpointing** (endpointing delay is pure perceived latency), speculative/eager processing, connection reuse/co-location, and **filling unavoidable gaps with sound** ("let me check that") so there's no dead air.
- **Perceived** latency is what matters and can be managed even when actual latency can't be eliminated — and latency explains the entire design of a voice agent, which is why voice AI is harder than text AI despite using the same models.

## Further reading

- [End-to-end principle — overview](https://en.wikipedia.org/wiki/End-to-end_principle)
- [OpenAI — Realtime API guide](https://platform.openai.com/docs/guides/realtime)
