# Text-to-Speech: Giving the Agent a Voice

*The last stage of the pipeline is where the agent finally speaks, and it's where an interaction either sounds human or sounds like a robot reading a menu. Modern text-to-speech is remarkably natural, but for a voice agent it must also be fast and streaming — synthesizing speech as the LLM's words arrive, not after — and it must pronounce the messy real world correctly. This post covers TTS for real-time voice.*

The LLM produced a response; TTS turns it into sound. Like ASR in reverse, modern neural TTS has largely solved the *naturalness* problem that made old synthesis sound robotic — so the voice-agent challenges are again *latency, streaming*, and handling real text. This post covers how TTS works, the streaming that keeps it fast, and the normalization that keeps it from mispronouncing your content.

## How modern TTS works

**Text-to-Speech (TTS)** synthesizes an audio waveform of speech from text. Modern neural TTS produces speech that is often nearly indistinguishable from a human recording — natural prosody (rhythm and intonation), clear articulation, and expressive delivery — a dramatic leap over the flat, robotic concatenative synthesis of the past.

Because naturalness is largely a solved problem for good models, the differentiators for a voice agent are elsewhere:
- **Latency** — how fast the first audio is ready (the TTS analog of ASR's and the LLM's speed problem).
- **Streaming** — synthesizing incrementally as text arrives, rather than waiting for the full response.
- **Voice quality and choice** — which voice, and how expressive/controllable it is.
- **Pronunciation correctness** — saying names, numbers, and symbols right.

As with ASR, model choice trades quality against speed: the most natural voices may be slower, so voice agents often pick a voice that hits the latency budget while sounding good enough, rather than the absolute most lifelike one.

## Streaming synthesis: the latency key

The single most important TTS property for a voice agent is **streaming synthesis** — starting to produce audio from the *beginning* of the text while the rest is still arriving, rather than synthesizing the whole response and then playing it.

This is what closes the loop on the streaming-everything principle (post 1). Recall the LLM streams tokens (post 3); streaming TTS consumes those tokens as they arrive and synthesizes audio chunk by chunk, and playback begins on the first chunk. So the chain runs *concurrently*: the LLM is still generating the middle of its answer while TTS synthesizes the beginning and the user is already hearing it. The user's perceived wait is just the time to the *first spoken words*, not the time to generate-and-synthesize the whole response.

Without streaming TTS, you'd wait for the full LLM response, then wait for the full synthesis, then play — the additive latency the whole pipeline is fighting. Streaming TTS is therefore non-negotiable for real-time voice, and it must integrate with the LLM's token stream (synthesize at natural boundaries — a phrase or sentence — as enough tokens arrive to sound right, without waiting for the whole answer). Getting this hand-off smooth (chunking the text stream so speech sounds continuous, not choppy) is a real engineering detail.

## Text normalization: saying it right

A subtle but high-impact TTS problem is **text normalization** — converting written forms into their spoken equivalents. Written text is full of things that aren't spelled the way they're spoken:
- **Numbers** — "1234" → "one thousand two hundred thirty-four" (or "twelve thirty-four" as a year — context matters).
- **Currency and units** — "$50" → "fifty dollars"; "5km" → "five kilometers."
- **Dates and times** — "9/21" → "September twenty-first"; "3:30" → "three thirty."
- **Abbreviations** — "Dr." → "Doctor" or "Drive" (context again); "St." → "Street" or "Saint."
- **Symbols and URLs** — "%", "&", "example.com" all need spoken forms.

Get normalization wrong and the agent says "dollar sign five zero" or spells out a URL character by character — instantly breaking the illusion of a natural speaker. Good TTS systems handle much of this, but it's context-dependent and imperfect, which is why it's partly the *LLM's* job too (post 3: produce speakable text) — the two stages share responsibility for making the output pronounceable. For domain-specific content (product names, jargon), you may need to guide pronunciation explicitly.

## Voice, expressiveness, and control

Beyond correctness, TTS offers expressive dimensions that shape the agent's character:
- **Voice selection** — the persona of the agent (its voice is a big part of its identity and brand). Many systems offer a range of voices.
- **Prosody and emotion** — some TTS can vary tone, emphasis, and emotion, making responses more engaging and appropriate (a warm tone for support, a neutral one for facts). Over-expressiveness can be as off-putting as monotone, so it's a design choice.
- **Voice cloning and custom voices** — creating a specific brand voice, which raises real consent and ethical considerations (using someone's voice requires their permission; misuse is a genuine harm) — worth flagging as a responsibility, not just a feature.
- **Speed and control tags** — some systems accept markup to control pacing, pauses, and pronunciation for tricky words.

The voice is the most *human* part of the whole pipeline, and it's what users remember — so it's worth choosing deliberately for your use case (consistent, appropriate to the context, and correct in pronunciation), while respecting the ethical line around cloning real voices.

The takeaway: modern TTS makes natural-sounding speech easy; the voice-agent work is making it *fast* (streaming synthesis integrated with the LLM's token stream), *correct* (text normalization so it pronounces the real world right), and *appropriate* (a deliberately-chosen voice used ethically). It's the stage where all the pipeline's speed pays off as words the user actually hears — and where a mispronounced number or a full-response wait can undo everything upstream.

## Key takeaways

- **Modern neural TTS** produces near-human speech, so naturalness is largely solved — the voice-agent differentiators are **latency, streaming, voice choice, and pronunciation correctness** (and, as with ASR, model choice trades quality against speed).
- **Streaming synthesis** is the latency key: synthesize audio from the *start* of the text as the LLM's tokens arrive (at phrase/sentence boundaries), so playback begins on the first chunk while the LLM still generates — closing the streaming-everything loop; without it you pay full-generation + full-synthesis additive latency.
- **Text normalization** (numbers, currency, dates, abbreviations, symbols, URLs → spoken forms) is high-impact and context-dependent — get it wrong and the agent says "dollar sign five zero," breaking the illusion; it's shared responsibility between TTS and the LLM producing speakable text.
- **Voice and expressiveness** shape the agent's identity — deliberate voice selection, appropriate prosody/emotion (not over-done), and control tags — with **voice cloning** carrying real consent/ethical responsibilities.
- TTS is where the pipeline's speed pays off as heard words — make it fast (streaming), correct (normalization), and appropriate (chosen voice, used ethically), or a mispronunciation or full-response wait undoes everything upstream.

## Further reading

- [Speech synthesis — overview](https://en.wikipedia.org/wiki/Speech_synthesis)
- [OpenAI — Realtime API guide](https://platform.openai.com/docs/guides/realtime)
