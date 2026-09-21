# Speech-to-Speech and the New Realtime Architectures

*The cascaded pipeline — ASR, then LLM, then TTS — has powered voice agents for years, but it has an inherent ceiling: every stage adds latency and every conversion loses information. A newer architecture collapses the three models into one that goes from speech directly to speech, promising lower latency and richer understanding. This post compares the cascade with the emerging end-to-end approach, and where each fits.*

Six posts built the cascaded pipeline. This one steps back to a genuine architectural shift: **speech-to-speech** (end-to-end multimodal) models that replace the ASR→LLM→TTS chain with a single model. It's one of the most active frontiers in voice AI, and understanding the cascade-vs-end-to-end tradeoff is understanding where the field is going. As with the MoE architecture series, the theme is capability and latency per unit of complexity — the same forces, applied to voice.

## The cascade's inherent limits

The cascaded pipeline is modular and practical, but its very structure imposes two ceilings:

- **Additive latency.** Each stage (ASR, LLM, TTS) adds delay; even fully streamed (post 5), there's overhead at each boundary and each conversion. The cascade will always carry the cost of three separate models and the hops between them.
- **Information loss at each conversion.** This is the deeper limitation. Speech carries far more than words — tone, emotion, emphasis, pace, hesitation, who's speaking. When ASR converts speech to *text*, all of that is thrown away; the LLM sees only words, stripped of how they were said. And when TTS converts text back to speech, it must *guess* the appropriate tone from text alone. The cascade is lossy by construction: it funnels rich audio through a narrow text bottleneck twice.

So a cascaded agent literally cannot hear that you sound frustrated, or excited, or uncertain — that information died at the ASR step. It also can't easily produce speech whose emotion matches the content's intent, because the LLM communicated only text to the TTS. These aren't implementation bugs; they're consequences of routing everything through text.

## Speech-to-speech: one model, no text bottleneck

**Speech-to-speech** (end-to-end, or "realtime multimodal") models take audio in and produce audio out *directly*, within a single model, without the intermediate text conversions. The model natively understands and generates speech.

The advantages follow directly from removing the cascade's ceilings:
- **Lower latency.** One model instead of three, and no stage-to-stage hops, means less inherent delay — closer to the fast turn-taking of natural conversation.
- **Preserved paralinguistic information.** Because audio isn't funneled through text, the model can *perceive* tone, emotion, and emphasis in the user's speech, and *produce* speech with appropriate expressiveness. It can hear that you're frustrated and respond in a matching tone — impossible for the cascade.
- **More natural interaction.** Native handling of the audio stream can make turn-taking, backchannels, and barge-in feel more fluid, since the model works in the medium of conversation directly rather than reconstructing it from text.

This is a genuine architectural leap, and it's why realtime speech-to-speech models are a major frontier: they attack the cascade's two fundamental limits (latency and information loss) at the root rather than optimizing around them.

## The tradeoffs: it's not a clean win yet

Speech-to-speech is powerful but comes with real costs and immaturities, and an honest comparison matters:
- **Less modularity and control.** The cascade's separation is also a strength: you can swap the ASR, choose a specific LLM, pick a TTS voice, and inspect the transcript at each stage. An end-to-end model is more of a black box — harder to customize, debug, and control each piece independently. If you need a specific LLM's capabilities or a particular voice, the cascade gives you that directly.
- **Text is where a lot of tooling lives.** The cascade's intermediate text is useful: it's what you log, moderate, feed to tools/RAG, and evaluate. An end-to-end audio model makes it less obvious where to insert guardrails, tool calls, retrieval, and transcripts for records — the ecosystem of text-based tooling doesn't plug in as cleanly.
- **Maturity and availability.** The cascade is battle-tested, flexible, and built from mature, swappable components; end-to-end speech models are newer, offered by fewer providers, and evolving fast. The cascade remains the pragmatic default for many production systems today.
- **Cost and control profile differs.** Different pricing, different operational characteristics, and (as a single black box) fewer knobs to right-size per stage.

So it's a classic architectural tradeoff: **the cascade offers modularity, control, mature tooling, and flexibility; speech-to-speech offers lower latency, richer understanding, and more natural interaction, at the cost of control and maturity.** Neither is universally right.

## Which to choose, and where it's heading

A practical read:
- **Choose the cascade** when you need control and flexibility — a specific LLM, a particular voice, transcript-based logging/moderation/tools, mature swappable components, or when end-to-end options don't fit your provider/cost constraints. This is most production systems today.
- **Choose (or lean toward) speech-to-speech** when latency and natural, expressive interaction are paramount and you can accept less granular control — increasingly viable as the models mature.
- **Hybrids exist** — using an end-to-end model for the conversational core while still extracting text for logging/tools, or mixing approaches — and the line will keep blurring.

The direction of travel is clear: end-to-end speech models are improving rapidly and address the cascade's root limitations, so more of voice AI will move that way over time. But the cascade won't vanish soon — its modularity, control, and mature text-based tooling keep it the right choice for many systems, and understanding it remains essential (it's still what most agents are, and the concepts transfer). As with the MoE and modern-architecture story, the enduring lesson is the *tradeoff shape*: you're choosing between a modular pipeline you can control stage by stage and an integrated model that's faster and richer but more of a black box. Know which your use case needs.

## Key takeaways

- The **cascaded pipeline** (ASR→LLM→TTS) has two inherent ceilings: **additive latency** (three models + hops) and **information loss at each conversion** — speech's tone/emotion/emphasis die at the ASR-to-text step, and TTS must guess tone from text alone (lossy by construction, funneling audio through a text bottleneck twice).
- **Speech-to-speech** (end-to-end / realtime multimodal) models take audio in and produce audio out in one model, removing the text bottleneck — giving **lower latency**, **preserved paralinguistic information** (it can hear you're frustrated and respond in tone), and more natural interaction.
- The tradeoffs are real: end-to-end sacrifices the cascade's **modularity and control** (swap ASR/LLM/voice, inspect transcripts), makes **text-based tooling** (logging, moderation, tools/RAG, eval) harder to insert, and is **newer/less mature/less available** than the battle-tested cascade.
- **Choose the cascade** for control, flexibility, and mature text tooling (most production systems today); **lean speech-to-speech** when latency and expressive naturalness dominate and you can accept a black box; **hybrids** blur the line.
- The direction is toward end-to-end (it attacks the cascade's root limits), but the cascade persists for its control and tooling — the enduring lesson is the **tradeoff shape**: a controllable modular pipeline vs. a faster, richer, more black-box integrated model.

## Further reading

- [OpenAI — Realtime API guide](https://platform.openai.com/docs/guides/realtime)
- [Speech synthesis — overview](https://en.wikipedia.org/wiki/Speech_synthesis)
