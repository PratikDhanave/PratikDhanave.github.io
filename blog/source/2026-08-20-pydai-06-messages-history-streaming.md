# Messages, History, and Streaming

*A single agent run answers one question; a conversation needs memory, and a good user experience needs the answer to appear as it's generated. Pydantic AI handles both through its message system — the record of what was said that you pass between runs — and streaming, which delivers typed output progressively. Together they turn one-shot agents into conversational, responsive ones.*

The previous posts built agents that run once and return typed output. Real applications need more: **conversation** (an agent that remembers previous turns) and **streaming** (output that appears progressively, not all at once). Pydantic AI provides both through its **message** system and streaming support. This post covers how conversation history works, how you control it, and how streaming delivers responsive output — the pieces that make Pydantic AI agents usable in interactive applications.

## Messages: the record of the conversation

Every agent run produces and consumes **messages** — the structured record of what happened: the user's input, the model's responses, tool calls and their results, and system prompts. Pydantic AI exposes these messages on the result of a run, and the key operation is that you can **pass the messages from one run as history into the next**:

```python
# Illustrative shape — see the Pydantic AI docs for exact API.
result1 = agent.run_sync("My name is Alice.")
result2 = agent.run_sync(
    "What's my name?",
    message_history=result1.new_messages(),   # carry the prior conversation forward
)
print(result2.output)   # knows the name from history
```

This is how conversation works: an agent run is stateless by itself, but by feeding the *messages* from prior runs into the next run, you give the agent the conversation's context. The agent "remembers" not because it holds state, but because you carry the message history forward explicitly. This explicit-history model is deliberate and important — it means *you* control the conversation state (where it's stored, what's included), rather than the framework hiding it in mutable agent state. The messages are data you manage.

## Why explicit history matters

Making history explicit data (rather than hidden agent state) has real benefits that reflect the framework's design values:

- **You control storage.** Because history is just messages you pass in, you decide where to persist it — in memory, a database, a session store — fitting your application's architecture. The agent doesn't dictate where conversation lives.
- **It's serializable.** Messages can be saved and restored, so a conversation can span requests, sessions, or processes — essential for web applications where each request is separate (the stateless-backend point from the identity and distributed-systems series).
- **It's inspectable and controllable.** You can examine the messages (what the model said, which tools it called), and you can *shape* the history you pass forward — which is the basis for managing context length (below).
- **It keeps agents reusable.** Because the agent doesn't hold conversation state, the same agent object serves many concurrent conversations — you just pass each conversation's own history. This preserves the "define once, run many" reusability from the Agents post.

The design mirrors good backend practice: keep the component (the agent) stateless and reusable, and carry state (the messages) explicitly. It's the opposite of a stateful chatbot object, and it's what makes Pydantic AI agents clean to use in real, multi-user, multi-request applications.

## Managing context length

Because you control the message history, you also own the responsibility that comes with it: **conversation history grows, and context windows are finite** (the lesson from the LLM serving and context-engineering series). Passing an ever-growing history into each run eventually fills the context, raising cost and latency and risking truncation. Since history is explicit data you manage, you handle this the way those series described:

- **Trim** — pass only the recent messages, dropping older ones when the history gets long.
- **Summarize** — condense older turns into a summary you carry forward instead of the full messages, preserving gist at lower token cost.
- **Hybrid** — keep recent turns verbatim plus a summary of older ones.

Pydantic AI gives you the messages as manipulable data, so implementing these strategies is straightforward — you shape the `message_history` you pass forward. The framework doesn't force a particular strategy (again, you're in control), which means managing context is your job, but a tractable one because history is explicit, inspectable data rather than opaque internal state.

## Streaming: responsive output

The second piece is **streaming** — delivering the agent's output progressively as it's generated, rather than waiting for the complete response. This matters for user experience: as the LLM serving series noted, generation takes time, and streaming makes an application feel responsive by showing output as it arrives instead of a spinner until the end. Pydantic AI supports streaming runs:

- **Stream the response** as tokens/text are produced, so a UI can render it live — the standard responsive-chat experience.
- **Stream structured output** — and this is where Pydantic AI does something distinctive: it can stream *structured* outputs, validating the partial data as it arrives. So even when the agent returns a typed object, you can stream and progressively validate it, rather than waiting for the whole structure. This combines the responsiveness of streaming with the type safety of structured outputs — you don't have to choose between them.

Streaming structured output is a notable strength: many frameworks make you pick between "structured but all-at-once" and "streamed but unstructured text," while Pydantic AI streams *and* keeps the typed-validation guarantees. For applications that want both a live, responsive feel and reliable typed data, that's a meaningful capability.

## Conversation and responsiveness, the Pydantic AI way

Put together, messages and streaming extend the typed, controlled Pydantic AI model to interactive applications:

- **Conversation** is explicit message history you pass between runs — you control its storage, serialization, and length, keeping agents stateless and reusable across many conversations.
- **Streaming** delivers output progressively for responsiveness, including streamed-and-validated structured output — responsiveness without giving up type safety.

Both reflect the framework's consistent stance: give you *control* (over state, over how output arrives) with *type safety* intact, rather than hiding state or forcing a trade-off. This is what makes Pydantic AI practical for real conversational and interactive apps, not just one-shot calls. With conversation and streaming covered, the next post turns to the framework's standout strength — testing and evaluation — which the typing and dependency injection have been setting up all along.

## Key takeaways

- Agent runs produce and consume messages (the structured record of inputs, responses, tool calls, results); conversation works by passing the messages from one run as `message_history` into the next — the agent "remembers" because you carry history forward explicitly, not via hidden state.
- Explicit history is a deliberate design win: you control where it's stored, it's serializable (spanning requests/sessions — fitting stateless backends), it's inspectable and shapeable, and it keeps agents stateless and reusable across many concurrent conversations.
- Because you manage history, you own context-length management: trim, summarize, or hybrid (recent verbatim + older summarized) the history you pass forward — the framework gives you messages as manipulable data rather than forcing a strategy.
- Streaming delivers output progressively for responsiveness, and Pydantic AI can stream *structured* output while validating partial data — so you get responsiveness without giving up type safety, a capability many frameworks force you to trade off.
- Together, messages and streaming extend the framework's typed, controlled model to interactive apps: explicit controllable conversation state plus responsive (optionally typed) streaming, consistent with Pydantic AI's give-you-control-with-type-safety stance.

## Further reading

- [Dependency injection (previous post)](/blog/posts/pydai-05-dependency-injection.html)
- [Context Engineering series — managing finite context](/blog/series/context-engineering/)
- [Pydantic AI documentation — messages and streaming](https://ai.pydantic.dev/)
