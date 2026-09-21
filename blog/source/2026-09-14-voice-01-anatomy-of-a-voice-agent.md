# The Anatomy of a Voice Agent

*Talking to a computer feels simple — you speak, it answers — but under that simplicity is a real-time cascade of models racing a stopwatch. Audio becomes text, text becomes a response, the response becomes audio, and all of it has to happen fast enough to feel like conversation. This series builds voice AI from the ground up, and it starts with the pipeline that makes a voice agent work.*

Voice is the most natural interface humans have, and voice agents — assistants you talk to and that talk back — are one of the most visible frontiers of applied AI. But building one that feels natural is deceptively hard, because conversation is *real-time* and unforgiving: a delay that would be invisible in a chatbot is glaring when you're waiting for a reply out loud. This opening post lays out the anatomy of a voice agent — the stages a spoken turn flows through — so the rest of the series can go deep on each.

## The core loop: audio in, audio out

At its heart, a voice agent does this, over and over:

```
 🎤 Microphone → VAD → ASR/STT → LLM → TTS → 🔊 Speaker
    (audio)   (endpoint) (text)  (brain) (voice)  (audio)
        └─────────── one conversation turn ──────────┘
                     ↺ loops for the next turn
```

> **▸ [Open the interactive pipeline diagram](/blog/handbook-diagrams/voice-agent-pipeline.html)** — pan, zoom, and trace each stage of the cascade (light/dark, self-contained).

Each stage transforms the data into the next form: raw audio becomes a transcript, the transcript becomes a response, the response becomes speech. This is the **cascaded pipeline** — the classic, dominant architecture for voice agents, built by chaining separate specialized models. (A newer alternative, speech-to-speech models, collapses this into one — post 7.) Understanding the cascade is essential because it's what most voice agents are, and because its structure explains where the hard problems live.

## The stages

Walking the pipeline, each stage is its own discipline:

- **Capture + VAD (Voice Activity Detection).** The microphone streams audio, and *voice activity detection* decides when the user is speaking and, crucially, when they've *stopped* — the "endpointing" problem. Getting this right is subtle: end the turn too early and you cut the user off; too late and the agent feels sluggish. (Post 2 covers this with ASR.)
- **ASR / Speech-to-Text (STT).** Convert the captured speech into text — the transcript the rest of the pipeline reasons over. Modern ASR (Whisper-style models) is remarkably accurate, but accuracy, speed, and streaming all trade against each other (post 2).
- **The LLM.** The transcript goes to a language model — the "brain" — which produces the response. This is where the agent's intelligence lives, and where a lot of the latency budget is spent (post 3).
- **TTS / Text-to-Speech.** The response text is synthesized into natural-sounding speech. Naturalness and speed are the tensions here (post 4).
- **Playback.** The synthesized audio plays back to the user — and the loop begins again for the next turn.

Five stages, three model types (ASR, LLM, TTS), one continuous loop. That's the anatomy. The apparent simplicity of "speak and it answers" hides a coordinated relay across all of them.

## Why it's hard: the real-time constraint

If you could take your time, chaining these models would be routine. The reason voice AI is hard is the **latency constraint**: conversation has an expected rhythm, and humans notice delay acutely. In natural conversation, the gap between turns is roughly a couple hundred milliseconds; a voice agent that takes several seconds to respond feels broken, robotic, and frustrating, no matter how good its answer.

And the pipeline's total latency is *additive*: capture + endpointing + ASR + LLM + TTS + playback, each contributing delay, summed end to end. Worse, the LLM stage alone can take seconds if you wait for a full response. Making a cascade of models feel like real-time conversation is the central engineering challenge of voice AI, and it drives almost every design decision — which is why an entire post (post 5) is devoted to latency.

The answer, previewed here and detailed throughout, is **streaming everything**: don't wait for each stage to finish before starting the next. ASR emits partial transcripts as the user speaks; the LLM streams tokens rather than a finished answer; TTS synthesizes those tokens as they arrive; audio plays as it's synthesized. Streaming overlaps the stages instead of running them strictly in sequence, collapsing the additive latency into something that feels immediate. It's the single most important idea in making the cascade work.

## The other hard parts

Latency is the headline, but conversation has dynamics that a request-response chatbot never faces (later posts):
- **Turn-taking and endpointing** — knowing when the user is done speaking, and when it's the agent's turn (post 6).
- **Barge-in / interruption** — humans interrupt each other; a good voice agent lets you talk over it, which means detecting your speech mid-response and *stopping* — cancelling in-flight generation and synthesis (post 6).
- **Robustness to real audio** — background noise, accents, disfluencies ("um," restarts), and phone-quality audio all degrade ASR and must be handled (posts 2, 8).

These conversational dynamics are what separate a voice agent that feels alive from one that feels like a voice-activated form.

## What this series covers

With the anatomy in hand, the series goes stage by stage and then whole-system:
- **ASR** (post 2), **the LLM turn** (post 3), and **TTS** (post 4) — the three model stages in depth.
- **Latency** (post 5) — the make-or-break constraint and how streaming defeats it.
- **Turn-taking, interruption, and barge-in** (post 6) — the conversational dynamics.
- **Speech-to-speech and new realtime architectures** (post 7) — the emerging alternative to the cascade.
- **Building and productionizing** (post 8) — telephony, robustness, evaluation, deployment.

The mental model to carry through: a voice agent is a real-time cascade — audio → text → response → audio — where the whole engineering challenge is making a chain of models feel like an instant, natural conversation. Every stage matters, but *latency ties them together*, and streaming is how you win. Everything ahead builds on this pipeline.

## Key takeaways

- A voice agent is a **real-time cascade**: Microphone → VAD → ASR/STT → LLM → TTS → Speaker, looping each turn — the dominant **cascaded pipeline** architecture built by chaining separate specialized models.
- The pipeline has **five stages and three model types**: capture+VAD (endpointing — deciding when the user stopped), ASR (speech→text), the LLM (the brain), TTS (text→speech), and playback — each its own discipline.
- Voice AI is hard because of the **real-time latency constraint**: humans expect ~sub-second turn gaps, and pipeline latency is *additive* (every stage sums), so a multi-second response feels broken regardless of answer quality.
- The key answer is **streaming everything** — ASR emits partial transcripts, the LLM streams tokens, TTS synthesizes them as they arrive, audio plays as synthesized — overlapping stages instead of running them strictly in sequence, which collapses additive latency into something immediate.
- Beyond latency, conversation adds **turn-taking/endpointing, barge-in (interruption), and robustness to real audio** (noise, accents, disfluencies) — the dynamics that separate a natural voice agent from a voice-activated form.

## Further reading

- [Robust Speech Recognition via Large-Scale Weak Supervision (Whisper) — Radford et al. (arXiv:2212.04356)](https://arxiv.org/abs/2212.04356)
- [Speech recognition — overview](https://en.wikipedia.org/wiki/Speech_recognition)
