# Google ADK Glossary: Every Core Concept in One Place
*The reference capstone for the 26-part series — every canonical ADK term, defined concisely.*

---

This post closes **"Google ADK, Concept by Concept."** Across 25 prior installments we built up Google's [Agent Development Kit](https://google.github.io/adk-docs/) one idea at a time — agents, tools, sessions, callbacks, streaming, evaluation, deployment. This finale collects the core vocabulary in a single reference: roughly ninety of the terms that matter most, grouped by subsystem, each with a one-line definition in plain language. The full API surface is larger, but if you know these, you can read any ADK codebase — Python (`google.adk`) or Go (`google.golang.org/adk/v2`) — and know what every moving part does.

Terms are grounded in the real ADK APIs. Where a concept has a distinct Python and Go form, both are noted.

## Agents & orchestration

| Term | Definition |
|---|---|
| **Agent** | A configured LLM given a name, model, instruction, and tools that decides, per message, whether to answer directly or call a tool. `Agent(...)` in Python; `llmagent.New(...)` in Go. |
| **LlmAgent** | The LLM-driven agent type, configured via `description`, `instruction`, generation params, and optional input/output schemas. `Agent` is an alias for it. |
| **Workflow agent** | An agent whose control flow is deterministic code, not a model decision. Three built-ins: Sequential, Parallel, Loop. |
| **SequentialAgent** | Runs its sub-agents one after another over shared state — a pipeline like draft → review → edit. |
| **ParallelAgent** | Runs sub-agents concurrently against the same starting state, then merges their state deltas at the join. |
| **LoopAgent** | Re-runs its sub-agents each pass, accumulating state, until `max_iterations` or a sub-agent signals `escalate`. |
| **Custom agent** | A hand-written agent that lazily yields a stream of events, for control flow the three workflow agents can't express. Python async generator; Go range-over-func iterator. |
| **Sub-agent** | An agent nested under a parent; the parent may route to it or invoke it as a tool. |
| **Delegation (transfer)** | A coordinator hands off the turn to a matching sub-agent, which then replies to the user directly (`transfer_to_agent`). |
| **Coordinator / dispatcher** | A root agent that reads each sub-agent's `description` and routes the request to the best match. |
| **Agent-as-tool (AgentTool)** | Invoking a sub-agent like a function tool: the parent gets its return value and keeps control. `agent_tool.AgentTool`. |
| **description** | A sub-agent's one-line summary — the routing signal a coordinator matches against. The single most important string in a multi-agent system. |
| **Escalate** | A flag a sub-agent sets on an event's actions to break out of an enclosing loop early. |

## Tools

| Term | Definition |
|---|---|
| **Function tool** | A plain function exposed to the model; ADK runs it and feeds the result back. Python: function + type hints + docstring. Go: `functiontool.New`. |
| **Built-in tool** | A ready-made, Google-provided tool (e.g. `google_search`, `url_context`) enabled without writing its body. |
| **Toolset** | A group of related tools mounted together, often backed by an external system. |
| **Long-running tool** | A tool that returns a "pending" marker and is completed/resumed later by an async backend or a human. |
| **Human-in-the-loop (HITL)** | The pause/resume pattern where a tool records a pending call, returns control, and resumes when the matching response arrives. |
| **Authenticated tool** | A tool that acts as the end user against a third-party API via an interactive OAuth2 consent flow (Python-only in v2.0.0). |
| **MCP tool / MCPToolset** | A toolset that connects to a Model Context Protocol server and mounts that server's tools onto the agent. |
| **Grounding-tool isolation** | Keeping a built-in grounding tool and custom function tools in separate sub-agents, because the Gemini API won't mix them in one agent. |

## Sessions, state & memory

| Term | Definition |
|---|---|
| **Session** | One conversation: an ordered list of Events plus a key-value State bag. All of an agent's memory within a single conversation. |
| **SessionService** | The pluggable backend that stores sessions and exposes create/get/append. In-memory, database, or Vertex-managed — swappable without touching agent code. |
| **State** | The mutable key-value bag on a session, changed only through event deltas, never in-place. |
| **Session-scoped state** | Unprefixed keys; live only across the current conversation's turns. |
| **User-scoped state** | `user:`-prefixed keys; persist across all sessions of the same user. |
| **App-scoped state** | `app:`-prefixed keys; shared across all users of the application. |
| **Temporary state** | `temp:`-prefixed keys; honored only during the current turn and stripped when the event commits — never persisted. |
| **Delta discipline** | The rule that every state change rides on an event's delta, keeping the whole history auditable and replayable. |
| **MemoryService** | The long-term memory abstraction with exactly two operations — `ingest` and `search` — over past conversations. |
| **Artifact** | A named, auto-versioned binary blob (bytes + MIME type): a generated image, uploaded PDF, CSV report, audio clip. |
| **ArtifactService** | The service that stores, versions, loads, lists, and deletes artifacts, auto-incrementing the version on each save (in-memory or GCS-backed). |

## Context & callbacks

| Term | Definition |
|---|---|
| **Context object** | The single handle ADK passes to callbacks, tools, and agents for session state, artifacts, memory, and control actions. |
| **ReadonlyContext** | The minimal, read-only context (invocation id, agent name, read-only state) passed to instruction providers. |
| **CallbackContext** | Extends ReadonlyContext with mutable state and artifact load/save; passed to agent and model callbacks. |
| **ToolContext** | The richest context: adds tool actions (escalate/transfer), memory search, credential requests, and artifact listing; passed to tool functions. |
| **InvocationContext** | The context for a custom agent's run method — session and state, but no `actions`, so escalate must ride on an emitted event. |
| **Callback** | A hook ADK fires at a fixed lifecycle point to observe (log, trace) or intervene (block, rewrite, cache). |
| **before/after agent** | Callbacks around an agent's run; `before_agent` can short-circuit it, `after_agent` can replace its output. |
| **before/after model** | Callbacks around each LLM call; `before_model` returning a response skips the model (guardrails, caches), `after_model` can rewrite the reply (e.g. append citations). |
| **before/after tool** | Callbacks around each tool call; `before_tool` returning a result skips the tool, `after_tool` can rewrite its result. |
| **Plugin** | An app-global callback bundle registered once on the App/Runner, firing across all agents — the home for cross-cutting concerns like logging and metrics. |

## Runtime, events & streaming

| Term | Definition |
|---|---|
| **Runner** | The orchestrator that drives the loop: prompt the model, run tool calls, feed results back, stream events until a final response. What real apps embed. |
| **Invocation** | The full unit of work triggered by one user message; may span many agents and LLM calls, ending at the final-response event. |
| **Event** | One entry in a session's ordered log — user message, model reply, tool call/result — carrying any state change as a delta in its actions. `Event(author=, actions=)`. |
| **Event loop / event stream** | A run returns an iterable of events, not a single value; the caller loops and consumes each as it arrives. |
| **EventActions** | The side-effects carried by an event: `state_delta`, `artifact_delta`, `escalate`, `transfer_to_agent`. |
| **Event log as checkpoint** | The append-only event stream is itself the run's checkpoint; resumption just replays the log to rebuild state. |
| **Partial event** | An incremental chunk emitted while a response streams in; the final event confirms the whole message. |
| **Bidi (live) streaming** | Full-duplex mode over one persistent socket to a Live-API model, running input and output simultaneously for real-time audio/video/text. `StreamingMode.BIDI`. |
| **Barge-in** | The user speaking over the model mid-turn to interrupt it; the server signals it on the event stream (`event.interrupted`). |

## Models & reasoning

| Term | Definition |
|---|---|
| **Gemini** | Google's model family ADK is optimized for; a bare model string like `"gemini-2.5-flash"` resolves directly in Python. |
| **LiteLLM** | The adapter that plugs 100+ non-Google providers (OpenAI, Claude, Ollama, and more) behind ADK's uniform model interface. |
| **BaseLlm** | The abstract model interface every backend implements, giving an agent one uniform way to call any provider. |
| **Model registry (LLMRegistry)** | The Python registry mapping a model string to a `BaseLlm` class so non-Gemini specs resolve to their provider. |
| **Fake model** | A minimal model returning a canned response, letting a real agent run end-to-end offline with no network or key — the key to deterministic tests. |
| **Planner** | A component that makes an agent lay out a plan and reason through steps before answering, buying better multi-step reasoning and an inspectable trace. |
| **PlanReActPlanner** | A model-agnostic planner that injects a plan→act→reason→answer instruction and parses the tagged reply into private reasoning and a visible answer. |
| **BuiltInPlanner** | Delegates reasoning to a thinking model's native thinking budget via `ThinkingConfig` instead of rewriting the reply. |
| **Thinking budget** | A cap on tokens a thinking model may spend reasoning, plus a flag to expose those thoughts, supplied as native model config. |
| **Code executor** | A component that pulls model-written code from the reply, runs it in some sandbox, and feeds the real output back. Model-side (`BuiltInCodeExecutor`) or client-side (local/container/GKE/Vertex). |
| **Context caching** | Storing a prompt's stable prefix (long system instruction, reference doc, tool schema) model-side so later turns re-bill only the new tokens. Set once on the App via `ContextCacheConfig`. |

## Grounding & evaluation

| Term | Definition |
|---|---|
| **Grounding** | Tying answers to an external source of truth so they're current, verifiable, and citable rather than confidently generated from frozen training data. |
| **Grounding metadata** | The structured record on a grounded response listing the web sources the model actually used — what makes citations possible. |
| **Citations** | The human-visible list of sources appended to a grounded answer so readers can verify each claim. |
| **RAG (retrieval-augmented generation)** | Retrieve relevant passages, augment the prompt with them, then generate an answer grounded in that context rather than in training memory. |
| **Eval set** | A JSON file of eval cases — each a query, expected final response, and expected tool trajectory — serving as a growing regression suite. |
| **Trajectory evaluation** | Checking whether the agent called the right tools, with the right args, in the right order — not just judging the final answer. |
| **Response evaluation** | Scoring the final answer against a reference, either lexically (`response_match_score`, ROUGE-1) or via an LLM judge (`final_response_match_v2`). |
| **adk eval** | The CLI that scores an agent against an eval set using a criteria config file (Python-only in v2.0.0). |
| **CI gate** | A build check that fails the merge when eval scores drop below their thresholds, turning behavior regressions into red builds. |

## Protocols & deployment

| Term | Definition |
|---|---|
| **MCP (Model Context Protocol)** | The open "USB for tools" protocol: an agent connects as a client to an external server and uses its capabilities as native tools. An ADK agent can also *be* an MCP server. |
| **A2A (Agent-to-Agent)** | The open "HTTP for agents" protocol: one agent discovers and calls another as a peer over HTTP, across languages and frameworks. |
| **Agent Card** | A JSON manifest advertising an A2A agent's name, URL, and skills; discovery is fetching the card, invocation is calling a named skill. |
| **adk deploy** | The CLI that wraps container build/push/deploy into one command, with `cloud_run` and `agent_engine` subcommands. |
| **Cloud Run** | Google's serverless container platform — scales to zero, the default low-ops deploy target reachable via `adk deploy cloud_run`. |
| **Vertex Agent Engine** | The fully-managed Vertex AI agent runtime — provisions managed sessions, memory, autoscaling, and tracing. Deploy via `adk deploy agent_engine`. |
| **GKE** | Google Kubernetes Engine, the deploy target when you already run k8s or need sidecars/GPUs/fine networking. |
| **Observability / OpenTelemetry** | Both SDKs ship built-in OTEL instrumentation, emitting spans automatically that export to backends like Cloud Trace — no hand-rolled tracing. |
| **Safety settings** | Per-category content-filter thresholds attached to the generation config; on Vertex, mutually exclusive with Model Armor screening. |
| **Agent Config (from_config)** | ADK's declarative feature: define an agent in a YAML file that the loader validates and constructs at load time, keeping prompt/model/wiring in editable data while tools and callbacks stay in code. |

---

That is the core vocabulary of the Agent Development Kit — enough to read any ADK project and recognize every primitive at play. From a single `LlmAgent` with one function tool, up through workflow orchestration, persistent sessions, grounded and evaluated behavior, and a managed deployment, every concept in this series composes from the terms above.

Thanks for reading all 26 parts of *Google ADK, Concept by Concept.* Start anywhere: the official [ADK docs](https://google.github.io/adk-docs/), the [Python SDK](https://github.com/google/adk-python), and the [Go SDK](https://github.com/google/adk-go) are the canonical next stops.
