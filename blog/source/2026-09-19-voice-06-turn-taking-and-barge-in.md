# Turn-Taking, Interruption, and Barge-In

*The difference between a voice agent that feels like a conversation and one that feels like a walkie-talkie is turn-taking: knowing when to listen, when to speak, and — hardest of all — gracefully handling being interrupted. Humans do this effortlessly and unconsciously; making a machine do it is one of the subtlest problems in voice AI. This post is about the conversational dynamics that make an agent feel alive.*

The pipeline posts covered getting a single turn fast. This post covers the *choreography between* turns — the give-and-take that makes interaction feel like conversation rather than a rigid command-response exchange. Turn-taking, endpointing (revisited), and barge-in are what separate a natural voice agent from a stilted one, and they're where a lot of the perceived quality lives.

## Turn-taking: the rhythm of conversation

Human conversation is a beautifully coordinated dance of **turn-taking** — we know, mostly unconsciously, when someone is finishing, when it's our turn, and when to yield. We use cues: falling intonation, completed thoughts, pauses of the right length, even gaze and body language. We rarely talk over each other for long, and the gaps between turns are tiny.

A voice agent has to approximate this coordination without most of those cues, and it's genuinely hard. The failure modes are familiar to anyone who's used a clunky voice system:
- **The walkie-talkie feel** — rigid, one-at-a-time exchange with awkward pauses, where you're never sure if it's your turn. This is what happens when turn-taking is crude.
- **Talking over the user** — the agent starts responding while the user is still speaking, because it misjudged the turn end.
- **Dead air** — the agent doesn't realize the user finished, leaving an uncomfortable silence.

Good turn-taking eliminates these, and it rests on two capabilities: knowing when the *user's* turn ends (endpointing) and handling when the *user takes back* the turn (barge-in).

## Endpointing, revisited: when is the user done?

Endpointing (introduced with ASR, post 2) is the heart of turn-taking: detecting when the user has finished so the agent can respond. It bears repeating here because it's *the* turn-taking decision, and it's a genuine tradeoff:
- Respond too eagerly (short silence threshold) and you **cut the user off** when they merely paused to think — the single most infuriating voice-agent behavior.
- Respond too cautiously (long threshold) and you get **dead air** and a sluggish feel.

The subtlety is that silence alone is a poor signal — people pause mid-thought constantly. Better endpointing combines cues: the *duration* of silence, but also whether the utterance is *semantically complete* (a finished sentence is more likely a real turn-end than a trailing "and I was wondering if..."), and prosodic cues like falling pitch. Some modern systems use the language model itself to predict whether a turn is complete. The goal is to match human turn-end detection: fast when the user is clearly done, patient when they're mid-thought. Endpointing quality, more than almost anything, determines whether the conversation *flows*.

## Barge-in: letting the user interrupt

The capability that most makes a voice agent feel alive — and that walkie-talkie systems lack entirely — is **barge-in**: letting the user interrupt the agent mid-response, exactly as you'd interrupt a person who's going on too long or said something you want to correct.

Barge-in is technically demanding because it requires doing several things *at once*, while the agent is speaking:
- **Keep listening while talking.** The agent must run the microphone and VAD *during* playback, detecting the user's voice over (or under) its own output. This raises the **echo problem** — the agent hears its own speech through the mic and mustn't mistake it for the user; acoustic echo cancellation is needed to distinguish the user's voice from the agent's playback.
- **Detect a genuine interruption** versus a stray sound or a backchannel ("mm-hmm," "yeah") that isn't meant to take the turn. Reacting to every noise is as bad as ignoring real interruptions.
- **Stop immediately and cancel in flight.** On a real barge-in, the agent must *stop speaking at once* — halt playback — *and* cancel the in-flight LLM generation and TTS synthesis (the "cancel" messages in the request-flow sequence from the latency post). Continuing to generate and speak over an interrupting user is jarring and wastes work.
- **Switch to listening and handle the new input.** The interruption becomes the next user turn, which may correct or redirect — so the agent transitions cleanly from speaking to listening.

The interactive sequence diagram in the latency post traces exactly this: the agent streaming a response, the user interrupting, and generation + synthesis being cancelled at once as the agent starts listening again. Barge-in done well is what makes a voice agent feel *responsive and respectful* — you can stop it, correct it, hurry it along, just like a person. Its absence (an agent that plows through its whole response no matter what you do) is the clearest tell of a primitive system.

## Backchannels and natural flow

Beyond the big mechanics, subtler dynamics add naturalness:
- **Backchannels** — the little "mm-hmm," "right," "okay" that listeners emit to signal they're following, *without* taking the turn. A sophisticated agent distinguishes a backchannel (keep going) from an interruption (stop and yield), and some agents even *produce* backchannels to feel present.
- **Filler and thinking sounds** — a brief "let me see..." during an unavoidable delay (post 5) keeps the turn alive rather than dropping into dead air.
- **Graceful recovery** — when turn-taking goes wrong (both talk at once, or a misfire), handling it smoothly ("sorry, go ahead") rather than getting confused.

These are the fine details that push an agent from "works" to "feels human," and they're mostly about correctly *interpreting* the user's conversational signals and responding with the right dynamics.

The takeaway: turn-taking is the choreography that makes voice feel conversational, and it comes down to two hard problems — knowing when the user is done (endpointing, using silence + semantics + prosody) and letting the user interrupt (barge-in, which requires listening-while-speaking with echo cancellation, detecting genuine interruptions, and instantly cancelling in-flight work). Nail these and the agent feels like talking to a person; miss them and it feels like a walkie-talkie, however fast and smart the underlying pipeline is.

## Key takeaways

- **Turn-taking** — the coordinated give-and-take of who speaks when — is what makes voice feel conversational rather than walkie-talkie; its failure modes are talking over the user, dead air, and awkward one-at-a-time rigidity.
- **Endpointing** is *the* turn-taking decision and a genuine tradeoff: too eager cuts users off mid-thought (the most infuriating behavior), too cautious leaves dead air — good endpointing combines silence duration with **semantic completeness and prosody**, not silence alone.
- **Barge-in** (letting the user interrupt mid-response) is what most makes an agent feel alive, and is technically demanding: **listen while speaking** (with acoustic **echo cancellation** so the agent doesn't hear itself), detect a *genuine* interruption vs. a backchannel, and on interruption **stop instantly + cancel in-flight LLM generation and TTS**.
- **Backchannels** ("mm-hmm" that don't take the turn) must be distinguished from interruptions, and filler sounds/graceful recovery add naturalness — the fine details that push an agent from "works" to "feels human."
- Nail endpointing + barge-in and the agent feels like a person; miss them and it feels like a walkie-talkie **no matter how fast or smart the pipeline is** — turn-taking is where much of the perceived quality lives.

## Further reading

- [Turn-taking — overview](https://en.wikipedia.org/wiki/Turn-taking)
- [Voice activity detection — overview](https://en.wikipedia.org/wiki/Voice_activity_detection)
