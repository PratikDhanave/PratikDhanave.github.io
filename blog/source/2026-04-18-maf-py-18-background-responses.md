# Background Responses

*Starting long agent work in the background and polling with a continuation token.*

---

## What this lesson demonstrates

Some prompts take a while (deep reasoning, long generation). Background responses let an agent start the work and hand you back a `continuation_token` instead of blocking. You poll by re-running the agent with that token until the token comes back `None`, which means the operation finished and `response.text` holds the final answer. The same token also lets a streaming run resume after an interruption.

## The core loop

```python
session = agent.create_session()
response = await agent.run(
    messages="Briefly explain the theory of relativity in two sentences.",
    session=session,
    options={"background": True},
)
while response.continuation_token is not None:
    await asyncio.sleep(2)  # swap for exponential backoff
    response = await agent.run(
        session=session,
        options={"continuation_token": response.continuation_token},
    )
print(response.text)
```

A `session` ties the polling calls back to the original background run. Poll calls need no messages, just the token.

## The gotcha

The first call may finish immediately (token is `None`) or start a background job (token present), so always branch on the token, never assume. A `None` token means complete — done, failed, or awaiting input. For streaming, each update carries a `continuation_token`; keep the last one you saw so you can resume with `options={"continuation_token": last_token}`.

## The Azure / MAF mapping

The doc notes background responses are only fully supported by agents backed by the OpenAI / Azure OpenAI Responses API. On Foundry the client may decide autonomously whether to background a request, so the lesson is written to work either way: if no token comes back, it just prints the immediate result.

## Run it

`uv run tutorial/02-agents/10_background_responses.py` — needs Foundry credentials via `az login`.

---

Next: [Rag](/blog/posts/maf-py-19-rag.html)
