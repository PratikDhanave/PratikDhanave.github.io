# Speech-to-Text: Hearing the User

*The first real stage of a voice agent is turning sound into words, and it's harder than it looks. Modern ASR is astonishingly good on clean audio, but real conversations are full of noise, accents, and disfluencies, and — for a voice agent — the transcript has to arrive fast and incrementally, while the model also figures out when the user has actually stopped talking. This post covers ASR for real-time voice.*

The anatomy post named ASR as the stage that produces the transcript everything else reasons over. This post goes deep: how modern speech recognition works, the accuracy-vs-latency tension that dominates real-time use, and the endpointing problem (deciding when the user is done) that sits right alongside it. Get ASR wrong and the whole agent misunderstands; get it slow and the whole agent feels slow.

## How modern ASR works

**Automatic Speech Recognition (ASR)**, or speech-to-text (STT), converts an audio signal into text. Modern ASR is dominated by large neural models trained on enormous amounts of audio — the Whisper family being the widely-known open example — which transcribe far more robustly than the older, brittle pipelines that preceded them.

The leap in the last few years is *robustness*: trained on huge, diverse audio, these models handle varied accents, background noise, and multiple languages far better than before, often approaching human transcription accuracy on clean speech. For a voice-agent builder, the practical upshot is that ASR is no longer the bottleneck on *accuracy* it once was — a good model transcribes clean speech reliably. The remaining hard problems for voice agents aren't "can it transcribe?" but "can it transcribe *fast enough, incrementally, and on messy real-world audio* — and know when the user stopped?"

## The accuracy–latency–streaming tension

For a *voice agent* specifically, ASR faces a three-way tension that batch transcription (transcribing a finished recording) never does:

- **Batch (non-streaming) ASR** transcribes a complete audio clip at once. It can be very accurate because it sees the whole utterance for context — but it can only start *after* the user finishes, adding its full processing time to the latency budget as a serial step.
- **Streaming ASR** transcribes *as the user speaks*, emitting partial transcripts incrementally. This is essential for low-latency voice agents because it overlaps ASR with the user still talking, so by the time they stop, the transcript is nearly ready. The cost is that streaming models must decide on words with *less* future context, which can slightly reduce accuracy, and partial transcripts may revise as more audio arrives.

The tension: batch is more accurate but adds serial latency; streaming is faster (overlapped) but sees less context. For real-time voice, **streaming wins** — the latency matters more than the small accuracy difference, and it's the streaming-everything principle from post 1 applied to the first stage. A common pattern is streaming partials for responsiveness with a final, more-confident transcript at endpoint. Model *size* is a third axis: bigger models are more accurate but slower, so voice agents often pick a model sized to hit the latency budget rather than the absolute-most-accurate one.

## Endpointing: knowing when the user stopped

Alongside transcription sits a deceptively hard problem: **endpointing** — detecting when the user has *finished* their turn so the agent can respond. This is where **Voice Activity Detection (VAD)** comes in — distinguishing speech from silence/noise — but endpointing is more than detecting silence:

- **End too early** and you cut the user off mid-thought (they paused to think, and the agent barged in) — deeply frustrating and the most common voice-agent annoyance.
- **End too late** and the agent sits there after the user clearly finished, feeling sluggish and unresponsive.

The difficulty is that natural speech is full of pauses — thinking, breathing, "um" — that are *not* the end of a turn. Simple silence-timeout endpointing (wait N ms of silence) is crude: short timeouts cut people off; long timeouts feel slow. Better endpointing uses the audio *and* the content (a semantically complete sentence is more likely a real endpoint than a trailing "and, um..."), and some systems predict turn-completion from the language itself. Endpointing quality is one of the biggest determinants of whether a voice agent *feels* natural, because it directly controls the rhythm of the conversation — and it's tightly coupled to turn-taking and barge-in (post 6).

## Handling real-world audio

Production ASR must survive conditions that demos never show:
- **Noise and far-field audio** — background sound, echo, and speaking from across a room degrade recognition; noise suppression and good capture help.
- **Accents and code-switching** — diverse speakers and mixed languages; robust multilingual models handle this far better than older systems, but it's still a real source of errors.
- **Disfluencies** — "um," false starts, repetitions, and self-corrections are normal human speech that ASR must transcribe and the downstream LLM must tolerate (an advantage of an LLM brain: it handles messy transcripts gracefully).
- **Domain vocabulary** — names, jargon, and product terms an ASR model hasn't seen well; some systems bias or adapt toward expected vocabulary.
- **Telephony audio** — phone calls are low-bandwidth and noisy (post 8), a notably harder condition than a good headset.

The practical stance: choose an ASR model robust to *your* real audio conditions (test on realistic samples, not clean studio audio), stream for latency, and lean on the LLM's tolerance for imperfect transcripts. Perfect transcription isn't required — good-enough, fast, incremental transcription that the LLM can reason over is.

## Key takeaways

- **Modern ASR** (Whisper-style large neural models trained on huge, diverse audio) is robust and near-human-accurate on clean speech, so accuracy is rarely the bottleneck — the hard part for voice agents is being *fast, incremental, and robust on messy audio*.
- Voice agents face an **accuracy–latency–streaming tension**: batch ASR is accurate but adds serial latency (starts only after the user finishes); **streaming ASR** transcribes incrementally as the user speaks (overlapping the wait) at a small accuracy cost — and for real-time voice, streaming wins.
- **Endpointing** (via VAD + content) — knowing when the user *stopped* — is deceptively hard because natural speech has non-final pauses; ending too early cuts users off, too late feels sluggish, and endpointing quality is a top determinant of whether the agent feels natural.
- **Real-world audio** (noise, far-field, accents, code-switching, disfluencies, domain vocab, telephony) is far harder than demos — choose a model robust to *your* conditions and test on realistic samples, not studio audio.
- Perfect transcription isn't required: **fast, incremental, good-enough transcription the LLM can reason over** beats slow, perfect transcription — and the LLM brain tolerates messy transcripts gracefully.

## Further reading

- [Whisper — Robust Speech Recognition (arXiv:2212.04356)](https://arxiv.org/abs/2212.04356)
- [Voice activity detection — overview](https://en.wikipedia.org/wiki/Voice_activity_detection)
