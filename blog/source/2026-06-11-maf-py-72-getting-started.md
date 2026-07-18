# AG-UI Getting Started in Python

*Exposing an agent to any HTTP front-end over AG-UI, an SSE protocol, with one FastAPI helper.*

---

## What it demonstrates

AG-UI is a lightweight HTTP + Server-Sent-Events protocol that exposes an Agent Framework agent to a front-end (or any HTTP client). You wrap a normal Agent in a FastAPI app: a single helper call registers a `POST` endpoint that accepts a `{"messages": [...]}` body and streams the agent's reply back as SSE events — `RUN_STARTED`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`, `RUN_FINISHED`. It is the last stop in the hosting module: a browser-ready streaming surface for your agent.

## One real excerpt

```python
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from fastapi import FastAPI

agent = build_agent()  # a Foundry-backed Agent

app = FastAPI(title="AG-UI Server")
add_agent_framework_fastapi_endpoint(app, agent, "/")  # one call: parsing + SSE streaming

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8888)
```

## The gotcha

The whole integration is that one helper, from the separate `agent-framework-ag-ui` package (`pip install agent-framework-ag-ui --pre`). It streams via SSE (`data: {json}\n\n`); event *types* are `UPPERCASE_WITH_UNDERSCORES` while event *field* names are camelCase (`threadId`, `runId`, `messageId`) — easy to mix up. The agent's `instructions` are the default persona, but a client can override them by sending its own system message in the request body. AG-UI is still under active development and subject to change.

## Azure / MAF mapping

The hosted agent is a plain `Agent` over `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`). The upstream doc's sample uses `OpenAIChatCompletionClient`, but `add_agent_framework_fastapi_endpoint` is client-agnostic — it only needs an Agent — so swapping in the Foundry client is a drop-in.

## Run it

`uv run tutorial/04-hosting/ag-ui/01_getting_started.py` — needs Foundry creds (`az login`). Worked if uvicorn boot logs appear; from another terminal, a header curl (`Accept: text/event-stream`) streams SSE from `RUN_STARTED` to `RUN_FINISHED`.

---

Next: [My upstream Microsoft Agent Framework Go contributions](/agent-framework/)
