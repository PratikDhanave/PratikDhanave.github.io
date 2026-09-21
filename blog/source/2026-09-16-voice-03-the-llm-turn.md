# The LLM Turn: The Brain in the Loop

*The language model is where a voice agent stops being a transcription toy and becomes something you can actually talk to. But dropping an LLM into a real-time voice loop imposes constraints a chatbot never faces: it must respond in a tight latency budget, produce speech-friendly text, and carry conversation state — all while streaming its answer so the user isn't left waiting. This post is about the LLM stage, adapted for voice.*

The ASR post produced a transcript; now the LLM turns it into a response. The mechanics of the LLM are covered elsewhere in depth — here the focus is what changes when the model sits in a *voice* loop: the latency pressure, the need for spoken-style output, and conversation-state management. The same model that's leisurely in a chat UI has to be a fast, concise, streaming conversationalist here.

## The latency budget squeezes the LLM

In the voice pipeline, the LLM is often the largest single latency contributor, and it sits in the middle of a tight end-to-end budget (post 5). Two facts collide:
- Conversation demands a response within a few hundred milliseconds to feel natural.
- LLM generation of a full response can take seconds.

The reconciliation is **streaming and time-to-first-token (TTFT)**. What matters for voice isn't how long the *whole* answer takes to generate — it's how long until the *first* words are ready to speak. If the LLM streams tokens and the TTS starts synthesizing the opening words while the rest is still generating, the user hears a response almost immediately, and the total generation time hides behind the playback. So for voice, **TTFT is the metric that matters**, and streaming is non-negotiable — a voice agent that waits for the full LLM response before speaking will always feel slow.

This reshapes model choice and prompting for voice:
- **Favor low-latency models** (or right-size, per the AI-gateway routing post) — a fast model that starts talking quickly often beats a slower, marginally-smarter one for conversational feel.
- **Keep responses concise.** Long spoken responses are tedious to listen to *and* take longer to generate and synthesize. Prompt the model for brief, conversational answers — voice rewards brevity in a way text doesn't.
- **Front-load the answer.** Because streaming starts speaking from the first tokens, prompt the model to lead with the substance rather than a long preamble, so the user hears something useful immediately.

## Writing for the ear, not the eye

An LLM's default output is written for reading — and read-aloud, written text often sounds wrong. The voice LLM must produce **speech-friendly text**:
- **No visual formatting.** Bullet lists, markdown, headers, tables, and code blocks are meaningless (or absurd) when spoken. The model should produce flowing prose, not a formatted document read aloud.
- **Speakable numbers, dates, and symbols.** "$1,234.56" should be spoken as "one thousand two hundred thirty-four dollars and fifty-six cents"; "Dr." and "St." and URLs need spoken forms. Some of this is handled in TTS normalization (post 4), but the LLM should avoid output that's awkward to speak.
- **Conversational register.** Spoken language is shorter-sentenced, more informal, and more direct than written prose. Prompt the model to *talk*, not to *write* — short sentences, natural phrasing, the way a person would actually say it.
- **Brevity, again.** Nobody wants a three-paragraph spoken answer. The model should say the essential thing and stop.

Getting the model to write for the ear is mostly a prompting and system-instruction problem, and it's one of the highest-impact things you can do for perceived quality — a technically-correct answer that sounds like a document being read is a worse voice experience than a shorter answer that sounds like a person.

## Conversation state and context

Voice conversations are multi-turn and often long, so the LLM needs the *history* to stay coherent — the same conversation-memory concerns as any chat system, with voice-specific wrinkles:
- **Maintain the dialogue history** so the agent remembers what was just said ("what about tomorrow?" only makes sense with context). Standard message-history management applies.
- **Transcripts are imperfect** (post 2), so the context contains ASR errors and disfluencies; the LLM's robustness to messy input is an asset here — it can often infer intent despite a garbled word.
- **Latency vs. context length.** More context can mean slower TTFT; voice's latency pressure argues for keeping context lean (summarize old turns rather than sending everything), balancing coherence against speed.
- **Tools and actions.** A useful voice agent often *does* things (look up an order, book a slot) via tool calls — which add latency (a tool round-trip mid-turn) and require the agent to fill the silence ("let me check that...") so the user isn't left in dead air while a tool runs. Managing that spoken "thinking" gap is a voice-specific design detail.

## The LLM as the agent's personality

Beyond mechanics, the LLM is where the agent's *character* lives — its tone, helpfulness, and how it handles not knowing something. In voice this matters more than in text, because tone comes through strongly in spoken interaction and there's no screen to soften an abrupt reply. A few voice-specific behaviors to design for: gracefully handling misheard input ("I didn't quite catch that — did you mean...?"), keeping the user informed during pauses, and knowing when to be brief versus when a bit more detail helps. These are shaped by the system prompt and are as much a part of the voice experience as the pipeline's speed.

The takeaway: the LLM in a voice agent is the same technology as anywhere, but the voice loop imposes a distinct discipline — stream for time-to-first-token, write for the ear, keep it concise, manage conversation state under latency pressure, and let the model's personality carry the interaction. The brain has to be a *fast, spoken-word* conversationalist, not an eloquent essayist.

## Key takeaways

- In the voice pipeline the LLM is often the **largest latency contributor**, so what matters is **time-to-first-token (TTFT)**, not total generation time — stream tokens so TTS starts speaking the opening words while the rest generates, hiding total latency behind playback (streaming is non-negotiable).
- This favors **low-latency (right-sized) models**, **concise responses** (long spoken answers are tedious and slow), and **front-loading the answer** so the first streamed tokens are already useful.
- Produce **speech-friendly text**: no visual formatting (bullets/markdown/tables sound absurd spoken), speakable numbers/dates/symbols, conversational register (short sentences, informal, the way a person talks), and brevity — mostly a prompting problem, and one of the highest-impact levers for perceived quality.
- Manage **conversation state** under voice constraints: keep dialogue history for coherence, tolerate imperfect transcripts, balance context length against TTFT (summarize old turns), and handle tool-call latency by filling the silence ("let me check that...") so there's no dead air.
- The LLM carries the agent's **personality** (tone matters more in voice — no screen to soften it): design graceful handling of misheard input and informative pauses via the system prompt — the brain must be a fast, spoken-word conversationalist, not an essayist.

## Further reading

- [End-to-end principle — overview](https://en.wikipedia.org/wiki/End-to-end_principle)
- [OpenAI — Realtime API guide](https://platform.openai.com/docs/guides/realtime)
