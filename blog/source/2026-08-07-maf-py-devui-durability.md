# DevUI & Durable Agents in Microsoft Agent Framework (Python)

*A guide to the two hosting concerns every agent eventually hits — seeing it run in a local chat window with a live call inspector, and keeping its state alive across crashes on Durable Task infrastructure.*

---

An agent you can't watch is an agent you can't debug, and an agent that forgets everything when the process dies is an agent you can't ship. Microsoft Agent Framework (MAF) answers both from its hosting layer. **DevUI** gives any agent a local chat window plus an inspector that renders every model call, tool call, and OpenTelemetry span as it happens — the fastest way to actually *see* an agent behave, with no curl and no print statements. The **Durable Extension** goes the other direction: it checkpoints threads, orchestration progress, and workflow steps onto Durable Task infrastructure so a session survives a process crash, resumes on any worker, and can pause for hours or days without burning compute.

Both are transport, not intelligence. Every entity below is a plain `Agent` over a `FoundryChatClient` — `project_endpoint` + `model` + `AzureCliCredential()`, so `az login` first — with a local `get_weather` tool as the thing to inspect. DevUI and the Durable Extension render or persist the exact same model and tool calls the Foundry client already makes; they never change how the agent thinks. That shared foundation means the boilerplate is explained once here and assumed everywhere after.

---

## 1. DevUI: a chat window and inspector around any agent

DevUI is a local web app that wraps any agent — or any workflow — in a chat window plus an inspector panel that shows each model call and tool call the moment it happens. You build a normal Foundry agent, hand it to `serve()`, and a local web server boots and blocks until Ctrl-C. Ask about the weather in the chat, watch the tool call surface in the inspector.

```python
from agent_framework.devui import serve

agent = build_agent()  # a normal Foundry-backed Agent with a get_weather tool
print("Starting DevUI — open the printed URL, ask about the weather, watch the tool call.")
serve(entities=[agent])  # blocks; add more agents/workflows to switch between them
```

The signature detail is `entities` — a *list*. One DevUI process can front several agents and even workflows side by side, and the UI lets you switch between them. Because it accepts anything MAF can run, DevUI is a single pane over your whole local fleet.

**The gotcha:** DevUI ships as a *separate* package — `agent-framework-devui` — so `from agent_framework.devui import serve` raises `ModuleNotFoundError` on a bare install. Fix it with `uv sync --extra hosting` (or `uv add agent-framework-devui`). And `serve()` owns the event loop: it is a blocking call, so there is no `asyncio.run()` around it and no `await`. You call it directly from a synchronous `main()`. When your agent construction is itself async, build the finished agent first — `await build_agent()` inside `main()` — and only then hand the completed object to the blocking `serve()`.

---

## 2. Serving a whole directory: discovery by convention

Passing entities by hand is fine for one or two agents. Once you have a fleet on disk, DevUI can auto-discover them and serve them all with one command. Discovery is directory-driven: each entity lives in its own folder, and that folder's `__init__.py` exports a module-level variable named *literally* `agent` (or `workflow`). Point the `devui` CLI at the parent folder and it finds every entity underneath.

```python
# The only hard requirement for discovery: a module-level `agent` export in __init__.py.
ENTITY_TEMPLATE = '''\
agent = Agent(
    client=FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["FOUNDRY_MODEL"],
        credential=AzureCliCredential(),
    ),
    name="{name}",
    tools=[get_weather],
    instructions="{instructions}",
)
'''
# Then: devui ./entities --port 9000 --reload   → discovers weather_agent, concierge_agent
```

This is the one place the standard boilerplate reappears verbatim, because discovery keys on it: the `.env.example` documents exactly those Foundry vars, and each scaffolded package is the same Foundry-backed agent you'd otherwise build by hand. Discovery is pure packaging convention — nothing about the agent changes, only how DevUI finds it.

**The gotcha:** the folder name becomes the entity name, but the variable name is what discovery keys on — it must be *literally* `agent` or `workflow`. Implementation can live in `agent.py`/`workflow.py`, but the folder's `__init__.py` has to re-export the symbol. The entity directory must sit **directly** under the path passed to `devui`; nesting it deeper hides it. Environment scoping follows the tree: a parent-level `.env` loads for all entities, an entity-level `.env` only for that one. And if discovery finds nothing, DevUI doesn't error — it shows a curated sample gallery instead, which is a useful tell that your layout is wrong.

---

## 3. Turning on the trace timeline

The inspector shows calls; tracing shows the *shape* of a run. DevUI can capture and display the OpenTelemetry (OTel) traces Agent Framework already emits during execution. The key word is *already*: DevUI does not create its own spans. It collects the GenAI spans the framework produces — LLM calls, tool calls, agent runs — and renders them as a timeline in its debug panel. Launch DevUI with tracing on, run the agent in the browser, then open the debug panel to see the full span hierarchy.

```python
from agent_framework.devui import serve

agent = await build_agent()  # a Foundry agent with a get_weather tool (a nice span to inspect)

print("Starting DevUI with tracing enabled at http://localhost:8080")
serve(
    entities=[agent],
    tracing_enabled=True,  # wires OTel span capture into the debug panel
)
```

**The gotcha:** the programmatic flag is `tracing_enabled`, not `tracing` — the CLI equivalent *is* `devui ./agents --tracing`, so the names deliberately differ between the two entry points. Without an OTLP collector, traces are captured locally and shown only in the DevUI debug panel. To export them elsewhere — Jaeger, Zipkin, Azure Monitor, Datadog — set the `OTLP_ENDPOINT` env var, e.g. `OTLP_ENDPOINT=http://localhost:4317`. The same blocking-`serve()` rule from earlier applies: build the agent asynchronously in `main()`, then hand the finished object to the synchronous `serve()`. Tracing is observability layered on top — it changes what you can see, never how the agent runs.

---

## 4. Durability: agents that survive a crash

DevUI is about the inner loop; the Durable Extension is about the outer one. It makes agents and multi-agent orchestrations *durable*: threads, orchestration progress, and workflow steps are checkpointed on Durable Task infrastructure. Sessions survive process crashes, resume on any worker, and can pause for hours or days — a human-in-the-loop approval that arrives tomorrow — without holding a process open. You wrap normal agents in `AgentFunctionApp(agents=[...])`, which auto-generates HTTP endpoints (`POST /api/agents/<Name>/run`) and persists conversation state per `x-ms-thread-id`. There are no manual thread objects to manage.

```python
from agent_framework.azure import AgentFunctionApp

app = AgentFunctionApp(agents=agents)  # registering makes each thread durable

@app.orchestration_trigger(context_name="context")
def triage_orchestration(context):          # a generator (def + yield), NOT async
    email_text = context.get_input()
    spam_agent = app.get_agent(context, "SpamDetector")   # the DURABLE wrapper
    session = spam_agent.create_session()
    detection = yield spam_agent.run(messages=f"...{email_text}", session=session,
                                     options={"response_format": SpamDetectionResult})
```

Each registered agent is the same plain `Agent` over `FoundryChatClient` you'd build for DevUI — identical whether or not it is later made durable. In practice the lesson runs that agent in plain, non-durable mode first as a smoke test, then shows the durable wiring. Durability is a wrapper around an unchanged agent, not a different kind of agent.

**The gotcha:** inside an `@app.orchestration_trigger` you must **not** call the raw agent — fetch the durable wrapper with `app.get_agent(context, "Name")`, or the step won't be checkpointed. The trigger is a *generator* (`def` + `yield`), not `async def`, because Durable Functions replays it after a failure and every `yield`ed step must be a resumable point — this is the mental model that makes durability work, and violating it silently breaks recovery. Structured output goes through `options={"response_format": MyModel}` and comes back under `.get("structured_response")`. Finally, this can't run under plain `uv run`: durable hosting needs the Azure Functions host (`func start`), Azurite, the Durable Task Scheduler emulator, and the `agent-framework-azurefunctions` package.

---

## 5. Which hosting tool for which job

| Need | Use | Runs where |
|---|---|---|
| Watch one agent's calls interactively | `serve(entities=[agent])` | Local web server |
| Front several agents/workflows at once | `serve(entities=[...])` or `devui <dir>` | Local web server |
| Serve a directory of agents on disk | `devui <dir>` + `agent` export convention | Local web server |
| See the span timeline for a run | `serve(..., tracing_enabled=True)` / `--tracing` | Local (or OTLP export) |
| Survive process crashes, resume anywhere | `AgentFunctionApp(agents=[...])` | Durable Task infra |
| Pause for hours/days (human-in-the-loop) | Durable orchestration generator | Durable Task infra |

The split is clean: DevUI is a **development-time** window you open and close; the Durable Extension is a **runtime** guarantee baked into how the agent is hosted. Neither touches the model, so you can wrap the same Foundry-backed `Agent` in either — or, over its lifecycle, both.

---

## Key takeaways

- **DevUI is transport, not intelligence.** It renders the model and tool calls a `FoundryChatClient` already makes; `serve(entities=[...])` takes a list so one process can front a whole fleet.
- **`serve()` is blocking and owns the event loop.** No `asyncio.run()`, no `await` around it — build any async agent first in `main()`, then hand the finished object over. The hosting extra (`uv sync --extra hosting`) is required or the import fails.
- **Discovery keys on a literal `agent`/`workflow` export.** The folder name becomes the entity name, the exported variable is what DevUI finds, and the directory must sit directly under the path you pass in.
- **Tracing shows spans the framework already emits.** Flip `tracing_enabled=True` (or `--tracing`); point `OTLP_ENDPOINT` at a collector to export beyond the local debug panel.
- **Durability is a wrapper around an unchanged agent.** `AgentFunctionApp` checkpoints threads per `x-ms-thread-id`; inside an orchestration always fetch the durable wrapper with `app.get_agent(context, ...)`, keep the trigger a generator so it can replay, and expect to run it under `func start`, not `uv run`.

DevUI and the Durable Extension bracket an agent's life: you build and debug it in the local chat-and-timeline window, then host it durably so a crash costs you nothing. Both hold the same Foundry-backed agent at their center — swap the client and the mechanics carry straight over.
