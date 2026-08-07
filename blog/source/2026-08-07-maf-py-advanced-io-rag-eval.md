# Advanced I/O, RAG & Evaluation in Microsoft Agent Framework (Python)

*Once an agent can call tools, the next questions are what it can read, what it returns, how long it can run, where its facts come from, how it's defined, and whether it actually works — this guide answers all seven.*

---

A basic Microsoft Agent Framework (MAF) agent reads a string and writes a string. Real applications need more: to reason about an image, to hand back typed data instead of prose, to keep working on a long task without blocking, to ground its answers in your documents, to be defined in a file instead of code, and — critically — to be scored so you know it still works after a change. This guide takes an agent from a text-in/text-out box to a production-shaped component along exactly those axes.

Every example drives an `Agent` over a `FoundryChatClient` on Azure AI Foundry, authenticated with `AzureCliCredential` (so `az login` first, with `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_MODEL` set). That boilerplate is identical everywhere below, so it's stated once here and omitted from the snippets — the mechanics are what change, and most of them are provider-agnostic in shape.

---

## Richer input: a turn is a Message, not a string

Every prompt starts as a plain string, but that's a convenience. A user turn is really a `Message` made of one or more `Content` parts, and text is just one kind of part. To ask an agent about an image, you build a `Message` whose `contents=[...]` mixes a text part and an image part, then pass that `Message` to `agent.run(...)`. There are two ways to attach the image:

- `Content.from_uri(uri=..., media_type=...)` — point at a public URL
- `Content.from_data(data=<bytes>, media_type=...)` — embed local bytes

```python
url_message = Message(
    role="user",
    contents=[
        Content.from_text(text="What do you see in this image?"),
        Content.from_uri(uri=IMAGE_URL, media_type="image/jpeg"),
    ],
)
result = await agent.run(url_message)
```

The same shape works for local files: read the bytes with `"rb"` and pass `Content.from_data(data=image_bytes, media_type="image/jpeg")`. The vision-capable model reads all parts of the turn together.

**The gotcha:** a multimodal turn is a `Message`, not a `str` — and the text is *also* a content part, built with `Content.from_text(text=...)`, not passed as a bare string. `media_type` is a MIME type; `from_data` requires it and takes raw `data=<bytes>` (not a path), while `from_uri` strongly recommends it. And the deployed model must be vision-capable (e.g. gpt-4o) or the image part is silently ignored or rejected. Because this rides on the client-agnostic `Message`/`Content` API, the same turn works across providers — only the deployed `FOUNDRY_MODEL` needs vision support.

---

## Richer output: typed data instead of prose

The output side has the same story. By default an agent returns free-form text, which you then have to regex or hope-parse. Structured outputs make it return data that conforms to a schema you define, so you consume a typed object instead. The whole feature rides on one key: `response_format` inside the `options` dict on `agent.run(...)`.

The schema can be either a Pydantic `BaseModel` — then `response.value` is an instance of that model — or a JSON-schema dict, in which case `response.value` is the parsed JSON, usually a dict.

```python
class PersonInfo(BaseModel):
    name: str | None = None
    age: int | None = None
    occupation: str | None = None

response = await agent.run(PROMPT, options={"response_format": PersonInfo})
if response.value:
    p = response.value  # a typed PersonInfo instance
    print(f"name={p.name}  age={p.age}  occupation={p.occupation}")
```

Streaming works the same way: iterate the stream for live tokens, then call `await stream.get_final_response()` and read `.value` off the finalized response.

**The gotcha:** the parsed object lives on `response.value`, not `response.text`. `.text` is still the raw JSON string; `.value` is `None` when parsing fails, so always branch on it. Primitives and bare lists aren't supported directly — wrap them in a model or object. The framework handles the schema translation to the model's structured-output capability and parses the result back into `.value` for you.

---

## Long-running work: background responses

Some prompts take a while — deep reasoning, long generation — and you don't want to hold a request open the whole time. Background responses let an agent start the work and hand you back a `continuation_token` instead of blocking. You poll by re-running the agent with that token until it comes back `None`, which means the operation finished and `response.text` holds the final answer. The same token also lets a streaming run resume after an interruption.

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

**The gotcha:** the first call may finish immediately (token is `None`) or start a background job (token present), so always branch on the token — never assume. A `None` token means the operation is complete, whether done, failed, or awaiting input. For streaming, each update carries a `continuation_token`; keep the last one you saw so you can resume with `options={"continuation_token": last_token}`. Background responses are only fully supported by agents backed by the OpenAI / Azure OpenAI Responses API. On Foundry the client may decide autonomously whether to background a request, so write the loop to work either way: if no token comes back, it simply prints the immediate result.

---

## Grounding: RAG as a tool

A model answers from its parametric memory, which is frozen at training time and knows nothing about your data. Retrieval-augmented generation (RAG) grounds answers in your own knowledge base instead. The pattern is deliberately simple: expose a search tool over your documents, then instruct the agent to call it before answering and to cite the source it used. The model decides when and what to retrieve, the tool returns matching snippets, and the model composes a grounded, cited reply. The search tool is just a Python function the agent can call:

```python
def search_knowledge_base(
    query: Annotated[str, "The search query to find relevant support articles."],
) -> str:
    """Search the knowledge base and return matching snippets with citations."""
    q = query.lower()
    hits = [d for d in KNOWLEDGE_BASE if any(kw in q for kw in d["keywords"])]
    if not hits:
        return "No relevant articles found in the knowledge base."
    return "\n\n".join(f"[{d['title']}]({d['link']})\n{d['content']}" for d in hits)
```

You then pass `tools=search_knowledge_base` and instruct the agent to retrieve first, answer only from the snippets, cite the source, and decline when the base has nothing relevant. Giving each document a source name and link is what makes the "always cite your sources" instruction possible.

**The gotcha:** the example above uses keyword matching over an in-memory document list so it stays runnable on Foundry alone — but that is the *exact* RAG-as-a-tool shape the framework teaches; only the retrieval mechanism is simplified. For production, swap `search_knowledge_base` for a VectorStore-backed `collection.create_search_function(...).as_agent_framework_tool()`, which requires `semantic-kernel >= 1.38` and a live vector store (Azure AI Search, Qdrant, Redis, or in-memory). The agent contract — retrieve, ground, cite — does not change.

---

## Defining agents in a file, not in code

So far every agent has been constructed in Python. It can instead be described in a YAML spec — kind, name, instructions, model plus connection — and built by `AgentFactory`. That makes agents easy to version, share, and edit without touching code: the same spec drives dev, test, and prod. The `agent-framework-declarative` package provides `AgentFactory` with two entry points, `create_agent_from_yaml(<yaml str>)` and `create_agent_from_yaml_path(<path>)`, both returning an async context manager.

```python
async with (
    AzureCliCredential() as credential,
    AgentFactory(client_kwargs={"credential": credential}).create_agent_from_yaml(
        YAML_DEFINITION,
        safe_mode=False,
    ) as agent,
):
    response = await agent.run("What is a declarative agent, in one sentence?")
    print("Agent response:", response.text)
```

In the YAML, `=Env.NAME` pulls values from environment variables at load time, so `model.connection.endpoint` resolves to `=Env.FOUNDRY_PROJECT_ENDPOINT`.

**The gotcha:** this is the one Foundry pattern that does *not* use the usual `Agent(client=FoundryChatClient(...))` shape — the chat client is not built by hand. The YAML's `model.connection` block plus `AgentFactory(client_kwargs={"credential": ...})` build it, and `safe_mode=False` is required to let the spec instantiate a live client and tools. Note the async credential import: `from azure.identity.aio import AzureCliCredential`. The connection still targets Azure AI Foundry via `FOUNDRY_PROJECT_ENDPOINT`, so it stays Foundry-only.

---

## The batteries-included pipeline: the harness

At the other end from a hand-built agent sits the harness. A plain `Agent` only calls the model and loops over the tools you hand it; an agent harness is the scaffolding *around* that model — a ready-made autonomous pipeline with a function-calling loop, a persistent todo list, plan/execute modes, file and web-search tools, tool-approval heuristics, context compaction, and OpenTelemetry, all on by default and individually switchable. `create_harness_agent(client, ...)` assembles a fully wired `Agent` from your chat client; you configure only the parts you want to change.

```python
return create_harness_agent(
    client=client,
    name="research-agent",
    agent_instructions=(
        "You are a concise research assistant. Break work into a short todo "
        "list, use your tools, and report the final answer plainly."
    ),
    tools=get_stock_price,
    disable_web_search=True,  # no hosted web search for this offline demo
)
```

Task-specific prompt goes in `agent_instructions`; general operating rules go in `harness_instructions` (default `DEFAULT_HARNESS_INSTRUCTIONS`). Extra tools pass via `tools=`.

**The gotcha:** every default capability has a `disable_*` flag — `disable_todo`, `disable_mode`, `disable_web_search`, `disable_file_memory`, `disable_file_access`, `disable_tool_auto_approval`, `disable_compaction`. Compaction only turns on when you supply both `max_context_window_tokens` and `max_output_tokens` (or a custom strategy); otherwise it is auto-disabled. For looping, a `loop_should_continue` predicate (e.g. `todos_remaining()`) plus a `loop_max_iterations` cap re-invoke the agent until the predicate says stop. The harness returns a normal `Agent` but is stateful across a run, so drive it with a session: `session = agent.create_session()` then `await agent.run(prompt, session=session)`.

---

## Knowing it works: offline evaluation

None of the above matters if you can't tell when it breaks. The evaluation framework measures agent quality, safety, and correctness. `evaluate_agent()` runs your agent once per query, turns each interaction into an `EvalItem`, and scores it with one or more evaluators. A `LocalEvaluator` runs fast, offline checks — keywords, tool calls, custom functions — with no extra API calls, which makes it ideal for CI smoke tests and inner-loop iteration.

```python
@evaluator
def is_concise(response: str) -> bool:
    return len(response.split()) < 80

local = LocalEvaluator(keyword_check("weather"), is_concise, mentions_units)
results = await evaluate_agent(
    agent=agent,
    queries=["What's the weather in Seattle today?", "Give me the weather for Portland."],
    evaluators=local,
)
for r in results:
    print(f"{r.provider}: {r.passed}/{r.total} items passed")
```

The `@evaluator` decorator wraps a plain function; its *parameter names* decide what data it receives — supported names include `query`, `response`, `expected_output`, `expected_tool_calls`, `conversation`, `tools`, and `context`. A check may return a `bool`, a `float` (>= 0.5 passes), a dict with `score`/`passed`, or a `CheckResult`.

**The gotcha:** `evaluate_agent` returns one `EvalResults` per evaluator provider, each with `.provider`, `.passed`, `.total`, and `.raise_for_status()` (which raises `EvalNotPassedError`). Call `raise_for_status()` to turn evaluation into a hard gate in CI. `expected_output` is paired positionally with `queries`. Cloud LLM-as-judge scoring — FoundryEvals for relevance, coherence, groundedness, and safety — is available via `agent_framework.foundry`, but it needs a Foundry project client and a judge-model deployment; `LocalEvaluator` runs with zero extra setup, which is why it's the right first rung.

---

## Choosing what to reach for

| Need | Reach for | Key surface |
|---|---|---|
| Reason about an image | Multimodal `Message` | `Content.from_uri` / `Content.from_data` |
| Get typed data back | Structured outputs | `options={"response_format": Model}` → `response.value` |
| Run long work without blocking | Background responses | `options={"background": True}` + `continuation_token` |
| Ground answers in your docs | RAG-as-a-tool | search function + "retrieve, then cite" instructions |
| Define an agent without code | Declarative YAML | `AgentFactory.create_agent_from_yaml` |
| Full autonomous pipeline | Harness | `create_harness_agent(...)` + `disable_*` flags |
| Score outputs, gate CI | Evaluation | `evaluate_agent` + `LocalEvaluator` |

---

## Key takeaways

- **Input and output are both structured content.** A turn is a `Message` of `Content` parts, and a response can carry a typed `.value` alongside its `.text` — the string form is just the simplest case of a richer contract.
- **`.value` and `continuation_token` demand branching.** Structured parsing can fail (`.value is None`) and a background job may finish instantly (`token is None`); never assume, always branch.
- **RAG is a tool contract, not a technology.** Retrieve, ground, cite — the shape is identical whether the backend is an in-memory list or a live vector store; only the retrieval mechanism swaps.
- **Agents can be defined and operated at either extreme.** Declarative YAML moves construction out of code; the harness bundles a whole autonomous pipeline you dial down with `disable_*` flags. Both still return an ordinary `Agent`.
- **Evaluation is what makes the rest safe to change.** Start with a `LocalEvaluator` for offline, zero-setup checks, call `raise_for_status()` to gate CI, and graduate to Foundry LLM-as-judge when you need it.

Swap the `FoundryChatClient` for another chat client and most of these mechanics hold — the model reads richer input and emits richer output; your job is to shape the turn, branch on what comes back, ground it in the right facts, and prove it still works.

---

## Interactive diagrams

Explore the concepts in this guide as self-contained, pan/zoom interactive diagrams (light/dark, no dependencies):

- [Background Responses](/blog/diagrams/maf-py-18-background-responses.html)
- [Harness](/blog/diagrams/maf-py-23-harness.html)
