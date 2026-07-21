# Runtime & Events in ADK: The Runner, the Invocation, and the Event Stream

*How an agent actually runs — a Runner drives an invocation and hands you back a stream of events, not a single answer.*

---

By this point in the series you have agents, tools, callbacks, and services. This post is where they all meet. When you *run* an agent in Google's Agent Development Kit (ADK), you don't call a function that returns a string — you start an **invocation**, and the **Runner** drives it, streaming back a sequence of **`Event`** objects. Understanding that loop is what makes streaming, callbacks, and state updates stop feeling like magic.

## Three terms, in order

- **Invocation** — everything triggered by *one* user message. It can span multiple agents and multiple LLM calls before it's done.
- **Event** — one discrete thing that happened: user input, a partial or final model response, a tool call, a tool result. Events are the *only* output of a run.
- **Runner** — the engine. It owns the loop, holds the services (session, artifact, memory), fires the callbacks, and persists every event as it goes.

The loop is simple to state: the Runner appends the user message to the session, then repeatedly asks the agent to run, and each time the agent yields an event, the Runner persists it, applies any state or artifact deltas it carries, and forwards it to you. The invocation ends when the final response is emitted.

## You iterate a stream, not read a return value

In Python you consume the stream with `async for`:

```python
from google.adk.runners import InMemoryRunner
from google.genai import types

runner = InMemoryRunner(agent=root_agent, app_name="events")
session = await runner.session_service.create_session(
    app_name="events", user_id="ada"
)
trigger = types.Content(role="user", parts=[types.Part(text="go")])

async for event in runner.run_async(
    user_id="ada", session_id=session.id, new_message=trigger
):
    print(event.author, "->", event.content.parts[0].text if event.content else "")
    if event.is_final_response():
        print("FINAL:", event.content.parts[0].text)
```

`InMemoryRunner` bundles the in-memory services for you; you create the session first, then feed each new message in. There is a synchronous `runner.run(...)` too, but `run_async` is the primary path.

Go models the exact same stream, but with an idiom that fits the language — a range-over-function iterator that yields `(event, error)` pairs, so you check `err` on every step instead of catching an exception:

```go
r, err := runner.New(runner.Config{
    AppName:           "events",
    Agent:             a,
    SessionService:    session.InMemoryService(),
    ArtifactService:   artifact.InMemoryService(),
    MemoryService:     memory.InMemoryService(),
    AutoCreateSession: true,
})
if err != nil {
    log.Fatal(err)
}

msg := &genai.Content{Role: "user", Parts: []*genai.Part{{Text: "go"}}}
for ev, err := range r.Run(ctx, "ada", "s1", msg, agent.RunConfig{}) {
    if err != nil {
        log.Fatal(err)
    }
    if ev.IsFinalResponse() {
        fmt.Println("FINAL:", ev.Content.Parts[0].Text)
    }
}
```

Both give you a *stream*. Python's `is_final_response()` maps to Go's `ev.IsFinalResponse()`; `run_async(...)` maps to `r.Run(ctx, ...)`. Setting `AutoCreateSession: true` in Go means passing a fresh session id just works, mirroring how `InMemoryRunner` manages sessions in Python.

## Anatomy of an Event

Every event you receive carries the same shape, in both SDKs:

| Field | Meaning |
|-------|---------|
| `author` | who produced it — `user`, or an agent's name |
| `content` | the payload as `Part`s: text, `function_call`, `function_response`, inline data |
| `actions` | side effects: `state_delta`, `artifact_delta`, `escalate`, `transfer_to_agent` |
| `partial` | true for streaming chunks that aren't the complete message yet |
| `is_final_response()` | convenience predicate: is this the agent's finished answer for this turn? |

`is_final_response()` is roughly "has content, isn't a streaming `partial`, and isn't a pending function call." It's how you decide which event to *show the user*: a single invocation emits many events — tool calls, tool results, partial tokens — but usually only the final one is the answer. Caveat for multi-agent runs (Module 03): **each participating agent can emit its own final response**, so don't assume exactly one per invocation.

You can watch this directly with a tiny custom agent that yields a few events by hand — no model required. The core is that the agent's run method is itself a generator of events:

```python
from google.adk.agents import BaseAgent

class Narrator(BaseAgent):
    async def _run_async_impl(self, ctx):
        for text in ["processing step 1", "processing step 2", "final answer: 42"]:
            yield Event(
                author=self.name,
                content=types.Content(role="model", parts=[types.Part(text=text)]),
            )
```

Run that through the Runner and you'll see three events stream past, all authored by `narrator`, with the last classified as the final response. In Go the same agent is an `agent.New(agent.Config{Run: ...})` whose `Run` returns an `iter.Seq2[*session.Event, error]` — the yield function *is* the event stream.

## Why a stream at all?

You could imagine an API that just returns the final string. ADK streams events because that's what makes everything else in the framework work. **Callbacks fire between events. State deltas apply per event. The dev UI renders its trace from events. Streaming (next module) is just consuming `partial` events as they arrive.** The event stream is the backbone.

It also gives you durability almost for free. The Runner appends every event — each carrying its `state_delta` — to the session as it happens, so the session *is* an append-only log of exactly what occurred. There's no separate checkpoint to manage: to resume an interrupted run, ADK replays that log to rebuild state and continues from the last event, so completed work isn't re-run. This is the same machinery human-in-the-loop tools (Module 04) already ride: a paused tool records a pending function call as an event, control returns to you, and the run resumes when the matching function-response arrives.

A few honest caveats. Durability is only as good as your session store — in-memory services are wiped on process exit, so real resumption needs a persistent store (`DatabaseSessionService` / `VertexAiSessionService` in Python). Full durable resumption of a *normal* invocation is currently a Python feature (`App(resumability_config=...)`, experimental); the Go SDK carries the event-log-as-checkpoint principle and HITL re-entry, but not that specific knob yet. The dual of resuming is cancelling: in Python you `break` out of the `async for` (the runner cancels its root task) or set `ctx.end_invocation = True`; in Go you cancel the `context.Context` you passed to `Run`, or call `ctx.EndInvocation()`.

## Mental model

Think of the Runner as a driver reading the agent's script aloud, and the session as a stenographer transcribing every line as it's spoken. You're the audience receiving each line live — nothing is hidden until the end. You see the tool calls, the partial tokens, the state changes as they happen. The final answer is just the line marked as the conclusion.

Both SDKs converge here: the shape of an event, the meaning of "final," and the discipline of iterating a stream are the same across Python and Go. Get comfortable reading the event stream and the rest of ADK reads like open source, because it is — see the official docs at [google.github.io/adk-docs](https://google.github.io/adk-docs/).

**Next in the series:** Streaming — consuming `partial` events token by token, and bidirectional (live) streaming.
