# Audio and Speech

*Sound is the modality that makes AI conversational — the difference between typing to a machine and talking to it. And the same architectural ideas that transformed text and vision transformed audio too: treat the waveform as a sequence, train at scale, and one model can transcribe speech across languages, or synthesize a natural-sounding voice from text. Understanding how AI handles audio — recognition, synthesis, and understanding — completes the picture of the core modalities and shows how general the multimodal recipe has become.*

Beyond text and images, **audio** — especially **speech** — is a crucial modality. This post covers how AI handles sound: **speech recognition** (audio → text), **speech synthesis / text-to-speech** (text → audio), audio *understanding* and *generation* more broadly, and how these fit the multimodal picture. Audio (and speech) is central to conversational AI and voice interfaces, and it follows the same patterns (sequences, transformers, scale, cross-modal connection) as the other modalities.

## Audio as a modality

**Audio** is sound represented as data — fundamentally a *waveform* (air pressure over time), digitized into a sequence of samples. Like other modalities, the challenge is turning this raw signal into something a model can understand or generate:

- **Audio is a sequence over time.** Sound is inherently *temporal* — a signal unfolding over time — represented digitally as a sequence of samples (or, often, as a *spectrogram*: a representation of which frequencies are present over time, which is more model-friendly). Because audio is a *sequence*, it fits naturally with sequence models like transformers (as text does), which is part of why the same techniques transfer to audio.
- **Speech is the key sub-case.** While "audio" includes music, environmental sounds, etc., **speech** (spoken language) is the most important audio modality for AI — it's how humans naturally communicate, and it bridges audio and language (speech *is* language, in audio form). Much of audio AI focuses on speech: recognizing it, generating it, understanding it. Speech is where audio meets the language modality.
- **Raw audio → useful representation.** As with images, audio models turn the raw signal (waveform/spectrogram) into meaningful *representations* (embeddings) — capturing the content (what words were spoken, or what the sound is). And, as with other modalities, these representations can be connected to language (speech ↔ text) in shared/aligned ways, following the multimodal patterns from earlier posts. The recipe generalizes to audio.

Audio is a temporal signal (waveform/spectrogram) that models turn into meaningful representations, with *speech* the key sub-case (bridging audio and language). Because audio is a sequence, the same transformer/sequence techniques transfer, and audio connects to language following the multimodal patterns. The two core speech capabilities are recognition and synthesis.

## Speech recognition: audio to text

**Speech recognition** (ASR — automatic speech recognition) converts *spoken audio into text* — transcribing what was said. It's a cross-modal translation (audio → text) and a mature, widely-used capability:

- **From audio to transcribed text.** ASR takes speech audio and outputs the text of what was spoken — powering transcription, voice assistants, captions, voice input, and more. It's the audio → text direction of cross-modal translation, and it's foundational to voice interfaces (you speak, ASR transcribes, then a text model processes it).
- **Modern ASR: sequence-to-sequence at scale.** Modern speech recognition uses transformer-based *sequence-to-sequence* models (audio sequence → text sequence), trained on large amounts of audio-text (speech with transcripts) data. A prominent example, *Whisper*, was trained on a very large and diverse dataset of audio paired with transcripts (weakly-supervised, from varied web sources) — which made it *robust* across languages, accents, and conditions. The pattern echoes CLIP: large-scale, naturally-paired (audio, text) data yields a general, robust model. Scale and diverse data drive quality and robustness.
- **It's mature and broadly deployed.** Speech recognition has become quite accurate and is widely deployed (dictation, captioning, voice assistants, meeting transcription, accessibility). It's one of the most mature and practically-impactful multimodal capabilities. And it's the entry point for voice-based AI: converting speech to text that language models can then process.

Speech recognition (audio → text) transcribes spoken language, using transformer sequence-to-sequence models trained on large-scale audio-text data (like Whisper's diverse weakly-supervised training for robustness), and it's a mature, widely-deployed capability foundational to voice interfaces. The reverse direction — generating speech — is equally important.

## Speech synthesis: text to audio

**Speech synthesis** (TTS — text-to-speech) is the reverse: converting *text into spoken audio* — generating a voice reading the text. It's the text → audio cross-modal direction and completes the voice-interaction loop:

- **From text to natural speech.** TTS takes text and produces *audio of it being spoken* — ideally in a natural, human-sounding voice. It powers voice assistants speaking responses, audiobook narration, accessibility (reading text aloud), and voice output generally. It's the output side of voice interfaces (a text response is spoken via TTS).
- **Modern TTS is highly natural.** Modern neural TTS produces remarkably *natural-sounding* speech — with realistic intonation, rhythm, and even emotion — a big advance over the robotic synthesis of the past. Some approaches use techniques related to the generative methods elsewhere in AI (including diffusion, from the image-generation post, applied to audio). The quality is now high enough for many production uses, and voices can be made expressive and even cloned (raising real ethical/misuse concerns, noted below).
- **It completes the voice loop.** ASR (speech → text) and TTS (text → speech) together enable *voice interaction*: you speak (ASR transcribes), a language model processes the text and responds, and TTS speaks the response. This ASR → LLM → TTS loop is how voice assistants work, and increasingly it's being unified into models that handle speech more directly. Speech in and speech out, with language understanding between, is the conversational-AI loop.

Speech synthesis (text → audio) generates natural-sounding spoken voice from text, now highly realistic (using neural, sometimes diffusion-based methods), completing the voice-interaction loop (ASR → language model → TTS) behind voice assistants. Together, recognition and synthesis let AI listen and speak. Beyond speech, audio understanding and generation extend further.

## Audio understanding, generation, and the multimodal picture

Beyond speech recognition and synthesis, audio AI extends to broader *understanding* and *generation*, and fits the overall multimodal picture:

- **Audio understanding beyond transcription.** Models can *understand* audio beyond just transcribing words — recognizing sounds/events (what's happening in an audio clip), understanding music, identifying speakers, detecting emotion/tone, and (in multimodal LLMs) reasoning about audio input. Just as VLMs bring reasoning to images, multimodal models increasingly bring understanding and reasoning to audio. Audio becomes another input modality to reason over.
- **Audio and music generation.** Beyond TTS, AI can *generate* audio and *music* — creating sound effects, music from descriptions (text-to-music), and other audio. This uses generative techniques (including diffusion and sequence models) analogous to image/text generation, extending generation to the audio modality. Generating audio content from text is another cross-modal (text → audio) capability, paralleling text-to-image.
- **Audio in multimodal models.** Increasingly, *multimodal LLMs* handle audio *natively* alongside text and images — accepting speech/audio input and producing speech/audio output, integrated with their language and visual abilities. The trend is toward general models that handle text, images, *and* audio together (moving toward the "any-to-any" future of the final post). Audio is becoming a first-class modality in general multimodal models, not a separate system.
- **The same recipe, another modality.** Audio AI follows the same patterns as the rest of multimodal AI: represent the modality as a sequence, use transformers, train at scale on naturally-paired data (audio-text), connect to language via shared/aligned representations, and generate via the same families of techniques. Audio demonstrates how *general* the multimodal recipe is — the same ideas (sequences, transformers, scale, cross-modal connection, generation techniques) transfer across text, vision, and audio. This generality is a key theme of the whole series.

Audio and speech extend multimodal AI to sound: speech recognition (audio → text) and synthesis (text → audio) enable voice interaction, audio understanding and generation extend further, and audio is increasingly a native modality in general multimodal models — all following the same patterns (sequences, transformers, scale, cross-modal connection) as text and vision. This generality is striking. Next: video and beyond — the frontier of modalities. (A note: audio/voice generation, especially voice cloning, raises real misuse concerns — deepfakes, impersonation — an ethical dimension of these capabilities worth keeping in view.)

## Key takeaways

- Audio is a temporal signal (waveform, often represented as a spectrogram) that models turn into meaningful representations — and because it's a *sequence*, the same transformer/sequence techniques from text and vision transfer; *speech* is the key audio sub-case, bridging audio and the language modality.
- Speech recognition (ASR, audio → text) transcribes spoken language using transformer sequence-to-sequence models trained on large-scale audio-text data (e.g. Whisper's diverse weakly-supervised training for robustness across languages/accents — echoing CLIP's scale-and-natural-pairing lesson); it's mature, widely deployed, and the entry point for voice interfaces.
- Speech synthesis (TTS, text → audio) generates natural-sounding spoken voice from text (now highly realistic, sometimes using diffusion-based methods), and together ASR + TTS complete the voice-interaction loop (speak → ASR → language model → TTS → speak) behind voice assistants.
- Audio AI extends beyond speech to audio understanding (recognizing sounds/events/music/emotion, reasoning about audio) and audio/music generation (text-to-music, sound effects via generative techniques), and audio is increasingly handled *natively* in general multimodal LLMs alongside text and images.
- Audio demonstrates how general the multimodal recipe is — represent the modality as a sequence, use transformers, train at scale on naturally-paired data, connect to language via shared/aligned representations, generate via the same technique families — the same ideas transferring across text, vision, and audio (and voice cloning/audio generation carries real misuse concerns worth noting).

## Further reading

- [Robust Speech Recognition via Large-Scale Weak Supervision — Whisper (Radford et al., 2022)](https://arxiv.org/abs/2212.04356)
- [Speech recognition (Wikipedia)](https://en.wikipedia.org/wiki/Speech_recognition)
- [Generating images (previous post)](/blog/posts/mm-05-generating-images.html)
