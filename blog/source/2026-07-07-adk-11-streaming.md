# Streaming in Google ADK: Render as You Go, Confirm at the End

*token streaming, the accumulate-and-reconcile consumer pattern, and full-duplex live streaming for voice*

---

By default, a Runner in Google's [Agent Development Kit](https://google.github.io/adk-docs/) hands you the model's answer as a single finished event: you wait, then you get the whole thing. **Streaming** changes the timing — the answer arrives *as it's produced*, token by token — so a UI can render text live instead of staring at a spinner. There are two flavors: **SSE (token) streaming**, which is one-way and drives the "typing" effect, and **bidirectional (live) streaming**, a persistent duplex socket that makes real-time voice possible. Both reduce, at the event level, to a single boolean.

## The whole idea is one flag: `partial`

You already consume an event stream from the Runner. Streaming just adds `partial=True` events into that stream — incremental chunks that build toward the final message — followed by one terminating, non-partial event carrying the confirmed whole.

```mermaid
sequenceDiagram
    participant M as Model/Agent
    participant C as Consumer
    M-->>C: partial "The "
    M-->>C: partial "capital "
    M-->>C: partial "of France is "
    M-->>C: partial "Paris."
    M-->>C: FINAL "The capital of France is Paris."
    Note over C: render partials live; the final confirms the whole
```

`is_final_response()` is `False` for every partial and `True` only for the terminating event. That's your signal that the message is complete — you never have to guess.

## Turning it on

There are three modes on `RunConfig`. `NONE` (the default) buffers everything into one final event. `SSE` emits many partials then a final. `BIDI` is the full-duplex live mode. For token streaming against a real model, you flip one field and iterate `run_async` exactly as before:

```python
from google.adk.agents.run_config import RunConfig, StreamingMode

config = RunConfig(streaming_mode=StreamingMode.SSE)
async for event in runner.run_async(
    user_id=user_id, session_id=session.id,
    new_message=msg, run_config=config,
):
    ...  # now some events arrive with event.partial == True
```

In Go it's the same field on the `agent.RunConfig` you pass to `runner.Run(...)`. Nothing else about your loop changes — which is the point. Streaming isn't a different API, it's the same event stream with more events in it.

## The consumer pattern: accumulate, then reconcile

Whichever language, the consumer logic is identical: keep a buffer, append every partial's text as it lands (this is what you render live), and when the final event arrives, treat *it* as the authoritative message. Here is the offline shape — an agent that emits words one at a time, then the full sentence:

```python
async def stream_and_reassemble(runner, session):
    trigger = types.Content(role="user", parts=[types.Part(text="go")])
    buffer, partial_count, final = "", 0, ""
    async for event in runner.run_async(
        user_id=USER, session_id=session.id, new_message=trigger
    ):
        if not (event.content and event.content.parts and event.content.parts[0].text):
            continue
        text = event.content.parts[0].text
        if event.partial:
            buffer += text          # render this chunk live in a real UI
            partial_count += 1
        elif event.is_final_response():
            final = text            # the confirmed whole message
    return buffer, partial_count, final
```

The Go form is a direct transliteration — the field is `ev.Partial`, completion is `ev.IsFinalResponse()`, and the loop ranges over an `iter.Seq2[*session.Event, error]`:

```go
for ev, err := range r.Run(ctx, userID, "s1", msg, agent.RunConfig{}) {
    if err != nil {
        return err
    }
    if ev.Content == nil || len(ev.Content.Parts) == 0 || ev.Content.Parts[0].Text == "" {
        continue
    }
    text := ev.Content.Parts[0].Text
    switch {
    case ev.Partial:
        s.Buffer += text        // render live in a real UI
        s.PartialCount++
    case ev.IsFinalResponse():
        s.Final = text
    }
}
```

**Mental model.** Partials are for the *eyes*, the final is for the *record*. Paint chunks to the screen as they arrive, but persist, log, or act on the reconciled final event. Why reconcile instead of just concatenating partials? Because the final is the model's own confirmed rendering of the message — it's what you trust for storage and downstream logic, even though your accumulated buffer will usually match it byte for byte.

## Bidirectional / live streaming: two streams at once

SSE is strictly one-way — you send a message, then read a stream back. **Live** (`StreamingMode.BIDI`) opens one persistent duplex connection to a Live-API Gemini model and runs *two streams simultaneously*: you keep pushing audio frames *in* while events keep flowing *out* on the same socket. That concurrency is exactly what makes natural voice work — the user can **barge in** mid-sentence because your mic never stopped uploading, and the model hears it.

Two objects replace the plain `run_async` call:

- **`LiveRequestQueue`** — the *upstream*. Call `send_content(...)` for text turns and `send_realtime(Blob(...))` for raw PCM audio frames straight from the mic.
- **`runner.run_live(...)`** — the *downstream*. An async generator of events: audio parts, text parts, live transcripts, and control signals like `interrupted` and `turn_complete`.

```python
queue = LiveRequestQueue()

async def pump_mic():                     # UPSTREAM: never stops -> user can interrupt
    while True:
        pcm = await read_mic_frame()      # raw 16-kHz PCM bytes
        queue.send_realtime(types.Blob(data=pcm, mime_type="audio/pcm;rate=16000"))

async def drain_events():                 # DOWNSTREAM: events for the same turn
    async for event in runner.run_live(
        user_id="ada", session_id=session.id,
        live_request_queue=queue, run_config=config,
    ):
        if event.interrupted:             # user barged in -> stop playback
            stop_playback()
        if event.turn_complete:
            print("[turn complete]")

await asyncio.gather(pump_mic(), drain_events())
```

Live mode turns on a family of audio knobs on `RunConfig`: `response_modalities` (reply as `TEXT` or `AUDIO`), `speech_config` (the output voice), `input_audio_transcription` / `output_audio_transcription` (captions of user and model), and `realtime_input_config` — server-side **Voice Activity Detection** via `automatic_activity_detection`, which is what actually enables barge-in. Add `session_resumption` and a dropped socket reconnects without losing context.

This is genuinely dual-language. adk-go has a real live API too: `runner.RunLive(ctx, userID, sessionID, agent.LiveRunConfig{...})` returns an `agent.LiveSession` (push frames with `session.Send(agent.LiveRequest{...})`) plus an `iter.Seq2[*session.Event, error]` to range over. The `agent.LiveRunConfig` carries the same knobs — `ResponseModalities`, `SpeechConfig`, `Input`/`OutputAudioTranscription`, `RealtimeInputConfig`, `SessionResumption` — reusing the shared `google.golang.org/genai` types, so the mental model ports one-to-one.

## When to use which

Reach for **SSE** whenever a human is reading generated text and latency-to-first-token matters — chat UIs, code assistants, anything with a cursor. Reach for **BIDI** only when you actually need duplex media: voice assistants, live transcription, interrupt-driven interaction. And stay on the default **NONE** for batch jobs, tool-only agents, or any pipeline where nothing renders a stream — it's simpler and there's no live-typing payoff to collect. Note that live mode needs a `-live-` Gemini model plus real credentials; it can't run offline, whereas the token-reassembly pattern above runs against a plain in-memory Runner with no network at all.

**Next in the series:** Evaluation — measuring agent quality with eval sets and metrics.
