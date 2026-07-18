# Running Agents

*The four ways you actually call run(): non-streaming, streaming, sessions, and per-run options.*

---

## What it demonstrates

The base `Agent` gives you one verb — `run()` — with a few dials:

1. **Non-streaming:** `result = await agent.run(prompt)` → one `AgentResponse`
2. **Streaming:** `agent.run(prompt, stream=True)` → a `ResponseStream` you async-iterate
3. **Sessions:** `agent.run(prompt, session=session)` → conversation state across turns
4. **Run options:** `agent.run(prompt, options={...})` → per-call temperature / max_tokens / etc.

Defaults are set once at construction via `default_options=`; per-run `options=` merge over them and win on conflict.

## The code

```python
# 2. Streaming — iterate the ResponseStream, then finalize.
stream = agent.run("Tell me one fun fact about Amsterdam's canals.", stream=True)
async for update in stream:
    if update.text:
        print(update.text, end="", flush=True)
final = await stream.get_final_response()  # aggregated result from the updates above
```

Non-streaming `run()` returns an `AgentResponse` whose `.text` is the aggregated answer and `.messages` is the full produced list (tool calls, reasoning, usage — not just final text).

## The gotcha

Streaming is `run(..., stream=True)`, **not** a separate `run_stream()` method. It returns a `ResponseStream`: iterate it for `AgentResponseUpdate` chunks (use `update.text`), then `await stream.get_final_response()` for the aggregated `AgentResponse` — that reuses the collected updates and does not re-run. Also, `tools` and `instructions` stay their own keyword arguments; they don't go inside the `options` dict.

## Azure / MAF mapping

The runner agent is built on `FoundryChatClient` (Azure AI Foundry) with `AzureCliCredential`, and `default_options={"temperature": 0.7, "max_tokens": 500}` baselines every run. Per-run `options=` override those Foundry generation settings for a single call.

## Run it

`uv run tutorial/02-agents/06_running_agents.py` — needs Foundry creds. It worked if you see four labelled blocks: non-stream, stream, session recall, per-run options.

---

Next: [Agent Pipeline](/blog/posts/maf-py-15-agent-pipeline.html)
