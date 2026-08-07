# Getting Started with Microsoft Agent Framework (Python)

*From the smallest possible agent to a browsable service — the core loop, the four ways to run it, how memory and tools attach, and two ways to put a server in front of it.*

---

An agent, stripped to its essentials, is smaller than it looks. In Microsoft Agent Framework it is a chat client bound to a deployed model, an instruction string, and a name — plus one verb, `run()`. Everything else the framework offers (tools, memory, hosting, workflows) is a layer on top of that single loop. This guide builds the whole picture from the bottom up: construct an agent, learn the ways to call it, give it memory and tools, then wrap it in a server so you can use it like a product.

Every example drives a `FoundryChatClient` on Azure AI Foundry, authenticated with `AzureCliCredential`. Because that setup is identical everywhere, we do it once here and never repeat it.

---

## The one-time setup: client and credentials

The client binds an agent to your Foundry project and reuses the token from your `az login` session, so there are no secrets in code:

```python
client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ["FOUNDRY_MODEL"],
    credential=AzureCliCredential(),
)
```

`FoundryChatClient` binds the agent to your Foundry project endpoint, keyed by the deployed model name. `AzureCliCredential` reuses the token from `az login`. That is the entire authentication story — the same three inputs power every agent below.

**The gotcha:** the client reads `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_MODEL` from the environment (via `load_dotenv()`), and auth comes from your `az login` session. Miss any of those three and construction fails before a single token is generated. Every live example needs Foundry creds and an active `az login`.

---

## The smallest agent

With a client in hand, an agent is one more line. Factor construction out of `main` so it can be built and tested on its own:

```python
instructions = (
    "You are a terse, knowledgeable travel guide. "
    "Answer in at most two sentences and never use bullet points."
)
agent = Agent(client=client, name="HelloAgent", instructions=instructions)
```

That is the Agent primitive at full strength: a model, an instruction string, and a name. `instructions` is the system prompt; `name` is how the agent identifies itself. This single object is what tools, memory, and hosting all build on.

The important idea here is that **the instructions *are* the agent.** That one string shapes persona, tone, and guardrails. Tweak it, re-run, and the behavior shifts — no other code changes. Before reaching for anything more elaborate, most of an agent's character lives in this string.

---

## Four ways to call `run()`

The base `Agent` gives you exactly one verb — `run()` — with a few dials on it. Knowing all four is most of what "using an agent" means in practice.

**1. Non-streaming.** `result = await agent.run(prompt)` returns a single `AgentResponse`. Its `.text` is the aggregated answer, and `.messages` is the full produced list — tool calls, reasoning, and usage, not just the final text. Reach for `.messages` when you need to see *how* the agent arrived at the answer.

**2. Streaming.** The same call with `stream=True` returns a `ResponseStream` you async-iterate for chunks as they arrive, then finalize:

```python
stream = agent.run("Tell me one fun fact about Amsterdam's canals.", stream=True)
async for update in stream:
    if update.text:
        print(update.text, end="", flush=True)
final = await stream.get_final_response()  # aggregated result from the updates above
```

**3. Sessions.** `agent.run(prompt, session=session)` threads conversation state across turns — the subject of the next section.

**4. Run options.** `agent.run(prompt, options={...})` sets per-call generation settings like `temperature` and `max_tokens`. Defaults are set once at construction with `default_options=`; per-run `options=` merge over them and win on conflict:

```python
agent = Agent(..., default_options={"temperature": 0.7, "max_tokens": 500})
# a single call can override the baseline:
await agent.run(prompt, options={"temperature": 0.2})
```

**The gotcha:** streaming is `run(..., stream=True)`, **not** a separate `run_stream()` method. It returns a `ResponseStream`: iterate it for `AgentResponseUpdate` chunks (guard each with `if update.text`, since some carry no text), then `await stream.get_final_response()` for the aggregated `AgentResponse`. That finalize step reuses the collected updates and does **not** re-run the model. One more trap: `tools` and `instructions` stay their own keyword arguments — they don't go inside the `options` dict.

---

## Memory lives in the session, not the agent

An agent is **stateless by design**. `agent.run("A")` and then `agent.run("B")` are two unrelated calls — the model never sees "A" while answering "B". What carries history from one turn to the next is an `AgentSession`. Create one, then pass it to every run in the conversation:

```python
session = agent.create_session()          # an in-memory conversation buffer
await agent.run("My name is Pratik and I bank with HDFC.", session=session)
r = await agent.run(
    "Draft a one-line message to my bank's support desk, signed with my name.",
    session=session,
)
```

Without `session=`, that second turn has amnesia: the agent has no idea who "me" is or which bank. The probe works precisely because it can only be answered by combining the name and bank from turn one — a good way to prove your session is actually threaded through.

This stateless-agent / stateful-session split is not an accident; it is exactly what lets **one agent serve many users at once**. The agent holds no history, so a single stateless instance can back one session per conversation, each with its own memory. The session is an in-memory buffer: `create_session()` returns a fresh conversation, and each `run(..., session=session)` appends that turn so the model sees the full prior history. Under the hood, the session accumulates the message list that gets sent to Foundry on each call — Foundry itself is stateless per request; the SDK's session is what replays prior turns.

**The gotcha:** forgetting `session=` on any single turn silently drops that turn out of history. There is no error — the run just doesn't remember. If context seems to vanish mid-conversation, check that *every* run in the thread carries the session.

---

## Giving the agent tools

An agent with instructions can only talk. Give it tools and it can *act*. A tool is just a Python function the model may call: you decorate it, annotate its arguments, and the framework wires up the schema, the call, and the result back into the conversation. You never invoke the tool yourself — the model decides which one fits the question, the framework runs it and feeds the result back so the model can phrase a final answer.

Three things make a function usable as a tool: a docstring (WHAT it does), `Annotated` `Field` descriptions (what each argument means), and a human-readable return string:

```python
@tool(approval_mode="never_require")
def convert_currency(
    amount: Annotated[float, Field(description="The amount of money to convert.")],
    from_ccy: Annotated[str, Field(description="Source currency code, e.g. USD, EUR, GBP, INR.")],
    to_ccy: Annotated[str, Field(description="Target currency code, e.g. USD, EUR, GBP, INR.")],
) -> str:
    """Convert an amount between USD, EUR, GBP and INR using a fixed rate table."""
    ...
```

Attaching tools to the agent is a single argument:

```python
Agent(client=client, name="ToolAgent",
      instructions="Use your tools when they fit the question.",
      tools=[get_weather, convert_currency])
```

The docstring and `Field` descriptions **are the API the model sees.** The Foundry Responses API supports function calling: `@tool` turns your annotated function into the JSON schema Foundry advertises to the model, and the framework handles the call/return round-trip transparently. Vague descriptions produce bad tool choices — this is prompt engineering wearing a type annotation. `approval_mode` gates side effects: `"never_require"` runs the tool silently, while a side-effecting production tool should use `"always_require"` so a human confirms before it fires.

**The gotcha:** the model, not your code, decides which tool fires. A question like "How much is 250 US dollars in rupees?" routes to `convert_currency` purely because the wording matches its docstring. Write your docstrings for the model to read — they are the routing logic.

(Tools go far deeper than function calling — hosted sandboxes, MCP servers, Skills, and CodeAct — but the mechanics above are the foundation everything else builds on.)

---

## From script to service

Everything so far ran once and exited. To use an agent like a product, put a server in front of it. Microsoft Agent Framework gives you two hosting surfaces, and the same `build_agent()` you already have drops straight into both.

### DevUI — a local web chat in one call

`serve()` from `agent_framework.devui` wraps any agent (or several) in a local web inspector and chat surface, so you can interact with it live instead of editing print statements:

```python
try:
    from agent_framework.devui import serve
except ModuleNotFoundError as e:
    raise SystemExit(f"DevUI isn't installed: {e}\nInstall it: uv add agent-framework-devui")

agent = build_agent()
serve(entities=[agent])   # blocks, running a local web server until Ctrl-C
```

DevUI is only a front end — each chat message in the browser becomes a Foundry Responses call under the hood, over the same agent from earlier. Pass `entities=[a1, a2]` to host several agents at once. It ships as a separate package (`uv add agent-framework-devui`, or `uv sync --extra hosting`), which is why the import is guarded — the hint beats a raw traceback.

**The gotcha:** don't wrap `serve()` in `asyncio.run()`. It runs its own event loop and blocks, which is exactly why its entry point is a plain sync `main()` — wrapping it double-starts a loop and errors.

### AG-UI — a streaming HTTP endpoint for any front-end

When you need a browser-ready surface for your *own* front-end rather than DevUI's built-in chat, AG-UI is a lightweight HTTP + Server-Sent-Events protocol that exposes the agent over standard HTTP. You wrap a normal Agent in a FastAPI app, and one helper call registers a `POST` endpoint that accepts a `{"messages": [...]}` body and streams the reply back as SSE events:

```python
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from fastapi import FastAPI

agent = build_agent()  # a Foundry-backed Agent
app = FastAPI(title="AG-UI Server")
add_agent_framework_fastapi_endpoint(app, agent, "/")  # one call: parsing + SSE streaming

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8888)
```

The reply streams as SSE events — `RUN_STARTED`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`, `RUN_FINISHED`. The helper is client-agnostic; it only needs an Agent, so the Foundry client drops in even though upstream samples often use an OpenAI client.

**The gotcha:** the whole integration is that one helper, from the separate `agent-framework-ag-ui` package (`pip install agent-framework-ag-ui --pre`). It streams via SSE (`data: {json}\n\n`), and event *types* are `UPPERCASE_WITH_UNDERSCORES` while event *field* names are camelCase (`threadId`, `runId`, `messageId`) — easy to mix up. The agent's `instructions` are the default persona, but a client can override them by sending its own system message in the request body. AG-UI is still under active development and subject to change.

---

## Choosing a run style and a host

| Need | Use |
|---|---|
| One finished answer | `await agent.run(prompt)` → `AgentResponse` |
| Live token-by-token output | `agent.run(prompt, stream=True)` → iterate, then `get_final_response()` |
| Conversation that remembers | `agent.run(prompt, session=session)` |
| Per-call temperature / max_tokens | `agent.run(prompt, options={...})` over `default_options` |
| Let the model call your code | `tools=[...]` with `@tool` + `Annotated` `Field` docs |
| Interactive local testing | `serve(entities=[agent])` (DevUI) |
| Streaming endpoint for your own UI | `add_agent_framework_fastapi_endpoint(...)` (AG-UI) |

---

## Key takeaways

- **An agent is a client, instructions, and a name.** The instructions *are* the agent — persona, tone, and guardrails all live in that one string.
- **`run()` has four dials:** non-streaming, `stream=True`, `session=`, and `options=`. Streaming is a flag, not a separate method; finalize with `get_final_response()`, which reuses the chunks and never re-runs.
- **Memory is the session, not the agent.** Agents are stateless by design so one instance can serve many conversations; the `AgentSession` you thread through every `run()` is what remembers.
- **Tools turn talk into action.** The docstring and `Annotated` `Field` descriptions are the API the model reads to route calls, so write them for the model.
- **The same agent becomes a service unchanged.** DevUI wraps it in a local chat with one `serve()` call; AG-UI exposes it over SSE with one FastAPI helper — no rewrite required.

Everything here is provider-agnostic in shape: swap the `FoundryChatClient` for another chat client and the loop, the sessions, the tool wiring, and the hosting helpers all hold. Your job is to shape the instructions, decide what the agent is allowed to do, and choose where it runs.
