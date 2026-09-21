# Building and Productionizing Voice Agents

*A voice demo that works in a quiet room with a good headset is a long way from a voice agent that survives a noisy phone call from a real customer. Production voice AI has to handle bad audio, unpredictable humans, failures at every stage, and the peculiar demands of telephony — and it has to be evaluated in ways text systems never require. This closing post is about making a voice agent real.*

The series built the pipeline and its dynamics; this post is about shipping it. Production imposes conditions demos hide: real-world audio, telephony, robustness to failure, evaluation of a real-time multi-stage system, and deployment tradeoffs. These are what separate a voice agent that impresses in a demo from one that works for actual users, and they're where a lot of the real engineering lives.

## Telephony: voice AI's most common home

A huge fraction of production voice agents live on the *phone* — customer support, appointment booking, outbound calls — and telephony is a demanding environment the pipeline must adapt to:
- **Low-quality audio.** Phone calls are narrowband and compressed (traditional telephony is famously low-fidelity), which degrades ASR meaningfully versus a clean headset. Your ASR must be robust to phone-quality audio specifically — test on it.
- **Network latency.** The telephony network adds its own latency on top of the pipeline's, tightening the already-tight budget (post 5). Every millisecond counts more on a call.
- **Integration plumbing.** Connecting the pipeline to the phone network (via SIP/telephony providers) is real infrastructure work — bridging audio streams, handling call setup/teardown, DTMF (keypad) input, and transfers to humans.
- **Interruptions and background noise** are the norm on calls (crosstalk, hold music, noisy environments), stressing VAD, endpointing, and barge-in (post 6) harder than a quiet demo ever does.

Telephony is where much of the value is, so building for it — not just for a pristine web-mic demo — is often the actual job. Design and test for phone conditions from the start if that's your target.

## Robustness: real audio and real humans

Beyond telephony, production voice AI must be robust to the messiness demos avoid:
- **Bad and varied audio** — noise, echo, far-field, accents, poor connections. Test on realistic audio, not studio samples (post 2), and expect ASR errors as normal, not exceptional.
- **Unpredictable humans** — people mumble, trail off, change their minds mid-sentence, ask off-topic things, talk over the agent, and go silent. The agent must handle all of it gracefully rather than only the happy path.
- **Failure at every stage** — ASR can mis-hear, the LLM can err or be slow, TTS can mispronounce, providers can time out or go down. Each stage needs fallbacks and graceful degradation (an AI gateway, from that series, helps for the LLM/model stages — fallback, retries, timeouts). A voice agent that breaks on the first hiccup won't survive real traffic.
- **Graceful failure and escalation** — when the agent genuinely can't handle something (repeated misunderstanding, an out-of-scope request), it should recover or **hand off to a human** cleanly rather than loop in confusion. Knowing its limits and escalating well is a mark of a production-grade agent.

The mindset shift from demo to production is assuming things *will* go wrong at every stage and designing for graceful handling — because with real audio and real people, they will.

## Evaluating a voice agent

Voice agents are unusually hard to evaluate because quality spans several dimensions that text eval (from the AI-evaluation series) doesn't fully cover:
- **Transcription accuracy (ASR)** — measurable (word error rate on representative audio), and worth tracking on *your* real audio conditions.
- **Response quality (LLM)** — the usual LLM-eval problem (correctness, helpfulness), applied to conversational, spoken-style responses.
- **Latency** — measure it end-to-end and per stage, because it's make-or-break (post 5); track time-to-first-audio, not just total.
- **Speech quality (TTS)** — naturalness and correct pronunciation, which are partly subjective and often need human judgment.
- **Conversational quality** — the hardest and most important: does turn-taking feel natural? Does barge-in work? Does the *whole interaction* feel like a good conversation? This is inherently holistic and usually requires listening to real (or realistic) conversations, not just scoring components in isolation.

The key point: **evaluating the components separately isn't enough** — a voice agent can have great ASR, a smart LLM, and natural TTS and *still* feel terrible because the turn-taking is off or the latency is high. You have to evaluate the end-to-end conversational experience, which means human listening and realistic test conversations, not just component metrics. Build a set of representative test conversations (including messy audio and interruptions) and evaluate the whole thing.

## Deployment tradeoffs

Finally, where the pipeline runs shapes latency, cost, and privacy:
- **Cloud APIs** — the fastest way to build (managed ASR/LLM/TTS), but every stage is a network round-trip (latency) and your audio leaves your infrastructure (privacy/cost considerations).
- **Self-hosted / on-device** — running models yourself (or on-device, connecting to the on-device-AI series) cuts network latency and keeps audio private, at the cost of operating the models. On-device is especially compelling for privacy-sensitive or offline voice.
- **Hybrid** — common in practice: some stages local (e.g. VAD and wake-word on device), others in the cloud, balancing latency, cost, and privacy.
- **The AI-gateway pattern applies** to the model stages — routing, fallback, caching, cost control, and observability for the ASR/LLM/TTS calls (from the AI-gateway series), giving the reliability and governance a production voice system needs.

Pulling the series together: a voice agent is a real-time cascade (audio → text → response → audio, or increasingly end-to-end speech-to-speech) whose whole challenge is feeling like a natural, instant conversation. Building one that *works in a demo* means chaining ASR, an LLM, and TTS and streaming everything for latency. Building one that *works in production* means all of that plus robustness to real audio and real humans, telephony, failure handling and escalation, holistic conversational evaluation, and deliberate deployment choices. Get the pipeline fast (streaming), the dynamics natural (turn-taking and barge-in), and the production concerns handled (robustness, telephony, eval, deployment), and you have a voice agent people actually want to talk to — which, in the end, is the only measure that matters.

## Key takeaways

- **Telephony** is where most production voice agents live and it's demanding: **low-quality narrowband audio** (degrades ASR — test on it), added **network latency**, real integration plumbing (SIP, call setup, DTMF, human transfer), and constant interruptions/noise stressing VAD/endpointing/barge-in.
- **Robustness** is the demo-to-production shift: expect bad/varied audio and ASR errors as normal, handle unpredictable humans (mumbling, trailing off, off-topic, silence), build **fallbacks for failure at every stage** (an AI gateway helps for model stages), and **escalate to a human** cleanly when stuck.
- **Evaluate holistically**: component metrics (ASR word-error-rate, LLM response quality, latency/time-to-first-audio, TTS naturalness) are necessary but **not sufficient** — a voice agent with great components can still feel terrible from bad turn-taking or latency, so evaluate the end-to-end conversation with human listening and realistic (messy, interrupted) test conversations.
- **Deployment tradeoffs** shape latency/cost/privacy: cloud APIs (fast to build, network latency, audio leaves your infra), self-hosted/on-device (lower latency + private, more ops), and hybrids (VAD/wake-word local, rest cloud) — and the **AI-gateway pattern** applies to the model stages for reliability and governance.
- A demo voice agent = chain the models + stream for latency; a **production** voice agent = that plus robustness, telephony, failure handling/escalation, holistic evaluation, and deliberate deployment — the only measure that matters is whether people actually want to talk to it.

## Further reading

- [Speech recognition — overview](https://en.wikipedia.org/wiki/Speech_recognition)
- [OpenAI — Realtime API guide](https://platform.openai.com/docs/guides/realtime)
