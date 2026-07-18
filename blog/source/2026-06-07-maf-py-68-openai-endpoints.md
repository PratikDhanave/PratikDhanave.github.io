# Openai Endpoints

*Speaking the OpenAI Chat Completions and Responses wire protocols on both sides of an agent.*

---

## What it demonstrates

Agent Framework speaks the OpenAI wire protocols — the Chat Completions API and the newer, stateful Responses API — on both sides. On the HOSTING side you expose your agent behind `/v1/chat/completions` and `/v1/responses` so any OpenAI SDK client can call it. On the CONSUMING side you point the framework at any OpenAI-compatible endpoint (Ollama, vLLM, LM Studio) via `base_url`. This lesson builds a Foundry-backed "backend brain" agent and drives it with the exact JSON body an OpenAI client would POST.

## One real excerpt

```python
# The exact JSON an OpenAI SDK client would POST to /pirate/v1/chat/completions.
chat_completions_request = {
    "model": "pirate",
    "stream": False,
    "messages": [{"role": "user", "content": "Hey mate, how be the weather?"}],
}
user_text = chat_completions_request["messages"][-1]["content"]
response = await agent.run(user_text)          # same agent, whatever protocol fronts it
async for chunk in agent.run_stream("Tell me a very short sea shanty."):
    if chunk.text:
        print(chunk.text, end="", flush=True)   # a Responses endpoint relays chunks like these
```

## The gotcha

The Python pivot only ships the CONSUMING side: `OpenAIChatCompletionClient(base_url=..., api_key=..., model=...).as_agent(...)` for Chat Completions, and `OpenAIChatClient(base_url=...)` for the stateful Responses API. HOSTING an agent *as* OpenAI endpoints is a .NET-only library (`Microsoft.Agents.AI.Hosting.OpenAI`) — there is no Python host API, so the hosting side here is illustrative, not a runnable server. The Responses API is the recommended default: it is stateful and adds a `conversation` parameter plus streaming event types.

## Azure / MAF mapping

The backend agent is a plain `Agent` over `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`). Because tools, options, and streaming are client-agnostic, the same Foundry agent works whichever protocol fronts it; to consume another server set `OPENAI_BASE_URL` (or pass `base_url`) and the generic OpenAI client picks it up.

## Run it

`uv run tutorial/04-hosting/04_openai_endpoints.py` — needs Foundry creds (`az login`). Worked if it prints a simulated OpenAI request, a pirate reply, then a streamed reply.

---

Next: [Foundry Hosted Agent](/blog/posts/maf-py-69-foundry-hosted-agent.html)
