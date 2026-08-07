# Models, Providers & Endpoints in Microsoft Agent Framework (Python)

*A complete guide to where a Microsoft Agent Framework agent gets its model — from direct Foundry inference to OpenAI-compatible endpoints, service-managed agents, hand-rolled providers, and container hosting.*

---

An agent needs a brain, and in Microsoft Agent Framework (MAF) that brain is a **chat client** — the object that turns your messages into a model call and streams the reply back. Everything else in the framework (tools, sessions, streaming, approvals) is layered on top of a small, uniform agent interface, which means the *provider* underneath is a swappable detail. That swappability is the whole point of this guide: you can point an agent at an Azure AI Foundry deployment, at any OpenAI-compatible server, at a service-managed agent whose definition lives in a portal, or at code you wrote yourself — and the caller barely changes.

There are really two axes to reason about. The first is **who owns the agent's behavior** — your process, or a remote service. The second is **what wire protocol the model speaks** — Foundry's Responses endpoint, the OpenAI Chat Completions API, or the stateful OpenAI Responses API. Get those two axes straight and the rest of MAF's provider surface falls into place. Every example below drives a model deployed in a Foundry project with `AzureCliCredential()`, so `az login` first.

---

## 1. FoundryChatClient: direct inference you control

Microsoft Foundry gives you two doors to a model deployed in a Foundry project, and picking the right one decides who owns the agent's behavior. The first door — and the one you'll reach for most — is `FoundryChatClient`: direct inference against the Foundry Responses endpoint. *Your* app owns the instructions, tools, and conversation loop; you wrap the client in a plain `Agent(client=...)` and drive it locally.

```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ["FOUNDRY_MODEL"],
    credential=AzureCliCredential(),
)
agent = Agent(client=client, name="FoundryJoker",
              instructions="You are good at telling short, clean jokes.")
```

From there, `await agent.run(...)` returns one full response, and `async for update in agent.run_stream(...)` yields it token by token — same client, both modes. Auth is credential-based: `AzureCliCredential()` reads your `az login` session, so there are no API keys to manage. And because the loop runs in your process, per-run instructions and tools are always honored.

**The gotcha:** `FoundryChatClient` uses the **project** endpoint (`https://<project>.services.ai.azure.com`), *not* an Azure OpenAI resource endpoint (`*.openai.azure.com` — that one belongs to the OpenAI provider covered below). All Foundry clients now live under `agent_framework.foundry`; the older `agent_framework.azure` surfaces were removed, so update any imports you're carrying over. Hosted tools attach as class-method factories like `FoundryChatClient.get_web_search_tool()`, passed via `tools=[...]` — they build without a client instance.

---

## 2. FoundryAgent: when the service owns the definition

The second door inverts ownership. A `FoundryAgent` is a **service-managed** agent whose definition — its instructions and tools — lives in the Foundry portal, not your code. You connect to it by name and version, and the server is the source of truth. This is the right posture when a team maintains an agent centrally and you just want to call it, or when governance requires the definition to live somewhere auditable rather than scattered across client apps.

The behavioral split between the two doors is the thing to internalize. With `FoundryChatClient` the loop is local, so per-run instructions and tools are honored — you're in charge. With `FoundryAgent` the Foundry-side definition wins, and run-time overrides are mostly ignored — the portal is in charge. Reaching for run-time instruction overrides and finding them silently dropped is the classic surprise here; if you need that control, you want the chat-client door, not the service-managed one.

---

## 3. OpenAI-compatible endpoints: consuming other servers

MAF speaks the OpenAI wire protocols — the Chat Completions API and the newer, stateful Responses API — on both sides of an agent. On the *consuming* side, you point the framework at any OpenAI-compatible endpoint via `base_url`: Ollama, vLLM, LM Studio, or a hosted OpenAI-flavored service. The agent interface doesn't change; only the client underneath does.

```python
# Consuming side: point a generic OpenAI client at any compatible server.
# Chat Completions:
agent = OpenAIChatCompletionClient(
    base_url=..., api_key=..., model=...,
).as_agent(instructions="...")

# Stateful Responses API:
client = OpenAIChatClient(base_url=...)
```

Because tools, options, and streaming are client-agnostic, an agent built one way behaves the same whichever protocol fronts it. You can even prove the equivalence by driving a Foundry-backed agent with the exact JSON body an OpenAI SDK client would POST — the request shape is just data, and the agent doesn't care where it came from:

```python
# The exact JSON an OpenAI SDK client would POST to /v1/chat/completions.
chat_completions_request = {
    "model": "pirate",
    "stream": False,
    "messages": [{"role": "user", "content": "Hey mate, how be the weather?"}],
}
user_text = chat_completions_request["messages"][-1]["content"]
response = await agent.run(user_text)          # same agent, whatever protocol fronts it
async for chunk in agent.run_stream("Tell me a very short sea shanty."):
    if chunk.text:
        print(chunk.text, end="", flush=True)  # a Responses endpoint relays chunks like these
```

Between the two protocols, prefer the **Responses API**: it is stateful, and it adds a `conversation` parameter plus dedicated streaming event types. Chat Completions remains the lowest-common-denominator option for servers that only speak the older protocol. To consume another server, set `OPENAI_BASE_URL` (or pass `base_url`) and the generic OpenAI client picks it up.

**The gotcha:** in Python, only the **consuming** side ships. *Hosting* your agent behind `/v1/chat/completions` and `/v1/responses` so that arbitrary OpenAI SDK clients can call it is a **.NET-only** library (`Microsoft.Agents.AI.Hosting.OpenAI`) — there is no Python host API for the raw OpenAI endpoints. In Python, the hosting side is illustrative, not a runnable server. When you do need a Python agent served over HTTP, the path is Foundry hosting, next.

---

## 4. Foundry Hosted Agent: your agent as a managed container

A *hosted agent* is your plain `Agent` packaged as a container and run on Microsoft Foundry Agent Service's managed infrastructure. You wrap the agent in a host server that exposes it over the OpenAI-compatible Responses protocol — a `POST /responses` HTTP endpoint — and Foundry then handles scaling, session state, and a dedicated Entra identity for you. The agent itself is unchanged; the hosting layer wraps around it.

```python
from agent_framework_foundry_hosting import ResponsesHostServer

agent = Agent(
    client=client,
    name="hosted-helper",
    instructions="You are a helpful AI assistant. Keep your answers brief.",
    default_options={"store": False},  # the host persists history; don't double-store
)

server = ResponsesHostServer(agent)
server.run()  # blocking; listens on http://localhost:8088, exposes POST /responses
```

The client underneath is the same `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`) from Section 1 — Foundry supplies the container, scaling, and Entra identity around that unchanged agent. Locally you drive it with `azd ai agent`; for a real deployment you use `azd provision && azd deploy`.

**The gotcha:** install the extra package `agent-framework-foundry-hosting` and import `ResponsesHostServer` from `agent_framework_foundry_hosting`. Set `store` to `False` in `default_options` — the hosting layer persists conversation history itself, so storing again on the model side duplicates it. `server.run()` is **blocking**, and when scaffolded via `azd ai agent init` it listens on `http://localhost:8088` exposing `POST /responses`. This program is meant to be launched by the Foundry host (`azd ai agent run`), not run directly — running it just starts the server process with no visible output, which is expected, not a failure. One credential note: the official docs use `DefaultAzureCredential`, but this repo standardizes on `AzureCliCredential` (your `az login` session); both satisfy the same auth contract, so either works.

---

## 5. Custom providers: writing your own agent

The last provider option isn't a model backend at all — it's writing your **own agent** instead of using a chat-client agent. A "custom provider" here means subclassing `BaseAgent` (which satisfies the `SupportsAgentRun` protocol) and implementing one `run()` method. Because you conform to the same protocol as the built-in agents, your hand-rolled agent is a **drop-in**: same `run()`, same streaming, same sessions. This is how you slot in deterministic logic, a rules engine, or a non-LLM backend behind the exact interface the rest of your code already speaks.

```python
def run(self, messages=None, *, stream=False, session=None, **kwargs):
    if stream:
        return ResponseStream(
            self._run_stream(messages=messages, session=session, **kwargs),
            finalizer=AgentResponse.from_updates,
        )
    return self._run(messages=messages, session=session, **kwargs)
```

`run()` is one method with two `@overload` signatures keyed on `stream`: `stream=False` returns an awaitable `AgentResponse`, while `stream=True` returns a `ResponseStream`. Inside `_run`, you coerce input with `normalize_messages(messages)` and build replies with `Content.from_text(...)` on a `Message(role="assistant", ...)`. A deterministic `EchoAgent` built this way needs no model quota at all — which makes it the ideal way to prove the interface holds: stand your custom agent next to a live `Agent(client=FoundryChatClient(...))` and the caller can't tell them apart.

**The gotcha:** the streaming branch **must** wrap its async generator in `ResponseStream(gen, finalizer=AgentResponse.from_updates)` — that finalizer is what lets callers still `await stream.get_final_response()` after consuming the stream. Sessions are optional; if you want multi-turn history you persist it yourself via `session.state` (a `setdefault("memory", ...)` dict is enough). And a custom agent is not required to call an LLM — the whole payoff is parity: because your agent implements `SupportsAgentRun`, swapping it for a live Foundry agent needs no change to caller code, model or no model.

---

## 6. Choosing a provider

| You want to… | Use | Who owns behavior | Wire protocol |
|---|---|---|---|
| Drive a Foundry model with your own loop, tools, instructions | `FoundryChatClient` in `Agent(client=...)` | Your process | Foundry Responses |
| Call a centrally-managed agent by name/version | `FoundryAgent` | Foundry portal | Foundry-managed |
| Talk to Ollama / vLLM / LM Studio / any OpenAI server | `OpenAIChatCompletionClient` or `OpenAIChatClient` (`base_url=...`) | Your process | OpenAI Chat Completions / Responses |
| Serve *your* Python agent over HTTP with scaling + identity | `ResponsesHostServer` (Foundry hosting) | Your process, Foundry infra | OpenAI Responses (`POST /responses`) |
| Slot in deterministic / non-LLM logic behind the agent interface | Subclass `BaseAgent` | Your code | None (or any) |

---

## Key takeaways

- **The chat client is the brain, and it's swappable.** The agent interface (`run`, `run_stream`, sessions, tools) is uniform; the provider underneath is a detail you choose.
- **`FoundryChatClient` vs. `FoundryAgent` is about ownership.** Local loop means your run-time instructions and tools win; a service-managed `FoundryAgent` means the portal definition wins and overrides are mostly ignored.
- **Watch the endpoint shape.** Foundry wants the *project* endpoint (`*.services.ai.azure.com`); `*.openai.azure.com` is the OpenAI provider's territory. Foundry clients live under `agent_framework.foundry`.
- **Python consumes OpenAI endpoints but only .NET hosts them.** Point at any compatible server with `base_url`; to serve a Python agent over HTTP, use Foundry hosting's `ResponsesHostServer` instead. Prefer the stateful Responses API.
- **Custom providers are drop-ins.** Subclass `BaseAgent`, implement `run()`, wrap streaming in `ResponseStream(..., finalizer=AgentResponse.from_updates)`, and the rest of your code never notices there's no model behind it.

Everything here shares one shape: an `Agent` over a chat client, driven by `run()`/`run_stream()`, authenticated with `AzureCliCredential()`. Decide *who owns the behavior* and *what protocol the model speaks*, and the right provider picks itself.
