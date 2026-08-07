# Memory, Context & Session State in Microsoft Agent Framework (Python)

*A complete guide to what an agent remembers — from a single conversation held in a session, to durable facts injected on every run, to the per-request values that reach a tool without ever touching the model's schema.*

---

A language model call is stateless: send messages, get a reply, forget everything. Turning that into an *assistant* — one that recalls your name across turns, remembers your bank across conversations, stays under a token budget as the chat grows, and threads a user id into a tool without exposing it to the model — is entirely a question of **what state lives where**. Microsoft Agent Framework gives you a small set of explicit places to put that state, and picking the right one is most of the design work:

1. **Sessions** — conversation history and scratch state carried across `agent.run()` calls.
2. **Storage** — where that history actually lives: local session state vs. service-managed.
3. **Compaction** — shrinking a growing transcript to fit a token budget.
4. **Context providers** — durable, cross-conversation memory and per-run shaping, via two hooks.
5. **Runtime context** — per-request values delivered straight to tools, hidden from the model.
6. **Shared state** — passing data between middleware in a chain.

Every example below drives a plain `Agent` over a `FoundryChatClient` on Azure AI Foundry (`project_endpoint` + `model` + `AzureCliCredential()`, so `az login` first). That client is the same throughout; the interesting part is the state plumbing around it, which is provider-agnostic in shape.

---

## 1. Sessions: memory within one conversation

A bare `agent.run()` starts cold every time — the agent has no memory of the previous call. An `AgentSession` is the state container that fixes this. It holds the conversation history plus a scratch `state` dict, and passing the **same** session into every `run()` is what makes turn 2 remember turn 1.

```python
# One session shared across turns == the agent's working memory.
session = agent.create_session()

first = await agent.run("My name is Alice.", session=session)
second = await agent.run("What is my name?", session=session)  # recalls "Alice"

# Serialize the live session, then restore it into a fresh AgentSession.
serialized = session.to_dict()
resumed = AgentSession.from_dict(serialized)
third = await agent.run("And what did I just ask you?", session=resumed)
```

Because a session is serializable, a conversation can be paused, persisted, and resumed later — even across a process restart.

**The gotcha:** `agent.create_session()` is synchronous in Python — no `await`. Threading is entirely manual: forget to pass `session=session` into a `run()` and that turn starts cold, breaking the memory chain. A session exposes both a local `session_id` and a `service_session_id` (the remote conversation id), plus that mutable `state` dict shared with context and history providers. Sessions are agent- and service-specific — reusing one across a different agent configuration or provider can produce invalid context.

---

## 2. Storage: where the history actually lives

A session's history has to be stored *somewhere*, and Microsoft Agent Framework gives you two modes. In **local session state**, the full transcript is kept in the session and re-sent on each run — you opt in with an `InMemoryHistoryProvider` (or a DB/Redis-backed equivalent). In **service-managed** mode, the service holds the conversation and the session only carries a remote id. Either way, to survive a process restart you persist the *whole* `AgentSession`, not just the message text.

```python
return Agent(
    client=client,
    name="StorageAgent",
    instructions="You are a helpful assistant with a good memory.",
    context_providers=[InMemoryHistoryProvider("memory", load_messages=True)],
)
```

The provider replays the stored transcript on each run because `load_messages=True`. Swap `InMemoryHistoryProvider` for a database-backed provider and the rest of the flow is identical — that provider seam is the whole point.

History providers are themselves just context providers (more on those below) that persist the transcript. The default `InMemoryHistoryProvider()` is lost on exit; `FileHistoryProvider("./sessions")` writes one JSON-Lines file per session and survives restarts.

**The gotcha:** only **one** history provider per agent may set `load_messages=True`, otherwise the transcript double-loads. Persist with `session.to_dict()` and restore with `AgentSession.from_dict()`, treating the payload as opaque — then rebuild the **same** agent/provider configuration to resume it. `require_per_service_call_history_persistence=True` keeps local history around each model call (handy with tool-calling), but it errors if the run is already bound to a service-managed conversation. Don't mix the two persistence models.

**How this maps to Foundry:** a chat-completions client like `FoundryChatClient` uses local history (the provider above); a responses-style service that persists conversations exposes `session.service_session_id` instead, which you rehydrate with `agent.get_session(service_session_id=...)`. Don't hand-write that id — read it off the session.

---

## 3. Compaction: keeping the transcript under a token budget

Because every model call resends the whole transcript, a long chat eventually blows the context window, costs more, and slows down. **Compaction** shrinks older history while keeping what matters. You attach a `CompactionProvider` next to a history provider; its `before_strategy` runs before each model call and rewrites the in-memory message list using one or more `CompactionStrategy` objects — truncate, sliding window, collapse tool results, LLM-summarize, or a token-budget pipeline of all of them.

```python
pipeline = TokenBudgetComposedStrategy(
    token_budget=2_000,
    tokenizer=tokenizer,
    strategies=[
        ToolResultCompactionStrategy(keep_last_tool_call_groups=1),
        SummarizationStrategy(client=summarizer_client, target_count=4, threshold=2),
        SlidingWindowStrategy(keep_last_groups=8),
    ],
)
history = InMemoryHistoryProvider()
compaction = CompactionProvider(before_strategy=pipeline, history_source_id=history.source_id)
```

The composed strategy runs its children gentlest-first and stops as soon as the budget is met.

**The gotcha:** compaction **only** affects agents that keep history in memory — pair `CompactionProvider` with an `InMemoryHistoryProvider` and wire `history_source_id=history.source_id`. Order matters in `context_providers=[history, compaction]`: the history provider stores the transcript, then compaction trims it before each model call. `SummarizationStrategy` fires only when the non-system message count exceeds `target_count + threshold`, and it needs its **own** chat client (a smaller/cheaper model is recommended). `CharacterEstimatorTokenizer` is just a ~4-chars/token heuristic. These types are experimental.

Because compaction operates on in-memory history, a server-managed Foundry Agent with persistent service-side history would ignore it entirely — another reason the local-vs-service distinction from Section 2 matters.

---

## 4. Context providers: durable memory and per-run shaping

A session remembers *within* one conversation. A `ContextProvider` remembers *across* all of them — and it does more besides. It is an object the agent consults on every run, with two keyword-only hooks:

- `before_run(*, agent, session, context, state)` — inject instructions, messages, or tools before the model sees anything.
- `after_run(*, agent, session, context, state)` — observe the response and update memory.

On the `context` (a `SessionContext`) you inject with `context.extend_instructions(source_id, text)`, `context.extend_messages(...)`, and `context.extend_tools(source_id, tools)`.

### Durable memory that outlives sessions

Real assistants remember across conversations — "you told me last week you bank with HDFC." Because a provider *instance* persists between runs, facts stored on it survive even a brand-new session, which is exactly what a session cannot do.

```python
class ProfileMemory(ContextProvider):
    def __init__(self) -> None:
        super().__init__(source_id="profile_memory")  # source_id is required
        self.facts: list[str] = []

    async def before_run(self, *, agent, session, context, state) -> None:
        if self.facts:
            note = "Known facts about the user: " + "; ".join(self.facts) + "."
            context.extend_instructions(self.source_id, note)
```

Attach it with `context_providers=[memory]`, and two *different* sessions both know the user. The facts live on `self`, so they carry across conversations; `extend_instructions` injects the note into the system prompt for one run only, and the persistence comes from the instance holding the facts. A production `after_run` would extract new facts with an LLM call or tool; the pattern keeps it deterministic.

### Per-session state that travels with the session

When state should follow the *session* rather than the provider, write it into the `state` dict the framework threads through — not an instance attribute:

```python
class ToneAndTally(ContextProvider):
    def __init__(self) -> None:
        super().__init__(source_id="tone_and_tally")

    async def before_run(self, *, agent, session, context, state) -> None:
        context.extend_instructions(self.source_id, "Always answer in British English, one sentence.")

    async def after_run(self, *, agent, session, context, state) -> None:
        state["turns"] = state.get("turns", 0) + 1
        print(f"[provider] turns so far this session: {state['turns']}")
```

Providers **stack**. A `FileHistoryProvider("./sessions")` and a `ToneAndTally()` can go into the same `context_providers=[...]` list — the file history persists the transcript while `ToneAndTally` shapes style and counts turns. This is the unifying idea: history, durable memory, compaction, and custom context all live in one `context_providers` list, independent of the chat client.

**The gotcha:** `source_id` is required in `super().__init__()`, and both hooks are keyword-only (`*, agent, session, context, state`) — miss the leading `*` and the framework won't call them as expected. And choose your storage deliberately: put a counter on `self` and it follows the *provider*; put it in `state` and it follows the *session*. Storing session-scoped data on `self` means it won't travel with the session across reuse.

---

## 5. Runtime context: per-request values that skip the schema

Sometimes a tool needs a value that came from *this* request — a user id, a tenant — but that value has no business in the tool's JSON schema, where the model would try to fill it in. Microsoft Agent Framework splits per-run state into three explicit buckets on `agent.run(...)`:

- `session=` — conversation state and history (read via `ctx.session`).
- `function_invocation_kwargs=` — values only tools and function middleware see (`ctx.kwargs`).
- `client_kwargs=` — chat-client-specific config (for custom clients).

A tool reaches these through a `FunctionInvocationContext` parameter, and can stash state on the session for later runs:

```python
@tool(approval_mode="never_require")
def send_email(address, ctx: FunctionInvocationContext) -> str:
    user_id = ctx.kwargs["user_id"]          # per-run, not a tool argument
    tenant = ctx.kwargs.get("tenant", "default")
    if ctx.session is not None:
        ctx.session.state["last_email_to"] = address  # persists across runs
    return f"Queued email for {address} from {user_id} ({tenant})"
```

Middleware sees the *same* `FunctionInvocationContext`, so it can enrich kwargs before the tool runs — `context.kwargs.setdefault("tenant", "contoso")`, then `await call_next()`.

**The gotcha:** any parameter annotated `FunctionInvocationContext` is injected regardless of its name and is **hidden from the tool's schema**. Read per-run values with `ctx.kwargs["..."]` — do **not** add a blanket `**kwargs` to tools, because unexpected runtime kwargs are rejected; consume them through the context object instead. `function_invocation_kwargs` never reach the model, and `session.state` written inside a tool survives across runs on the same session — the same `state` dict from Section 4, now written from a tool.

---

## 6. Shared state: passing data between middleware

Middleware in a chain often needs to hand data forward — a request id, timing, accumulated metrics. Microsoft Agent Framework's Python function-middleware signature is deliberately minimal — `async def mw(context, call_next)` — with no shared bag baked in. The idiomatic trick is to put both middleware **on the same object** and let them read and write instance attributes. That instance *is* the shared state.

```python
class MiddlewareContainer:
    def __init__(self) -> None:
        self.call_count: int = 0  # the shared state both methods touch

    async def call_counter_middleware(self, context, call_next):
        self.call_count += 1
        await call_next()

    async def result_enhancer_middleware(self, context, call_next):
        await call_next()  # tool runs first — result only exists after
        if context.result:
            context.result = f"[Call #{self.call_count}] {context.result}"
```

You wire them in by passing **bound methods of one instance**: `middleware=[container.call_counter_middleware, container.result_enhancer_middleware]`.

**The gotcha:** order matters, and so does *when* you read `context.result`. You must `await call_next()` to continue the chain, and the tool's output only exists *after* that inner call runs — so read or mutate `context.result` after the await, not before. The counter middleware also has to run before the enhancer, or the enhancer stamps a stale count. Mutate the tool output by assigning to `context.result`. There is no framework API for shared state here — the container pattern is pure Python; the framework contract is just `FunctionInvocationContext` plus a zero-argument `call_next`.

---

## 7. Choosing where state lives

| You need to remember… | Put it in | Lifetime |
|---|---|---|
| The current conversation across `run()` calls | `AgentSession` | One conversation (serializable) |
| The full transcript, re-sent each call | `InMemoryHistoryProvider` (or DB-backed) | Session-local |
| The transcript, on disk across restarts | `FileHistoryProvider("./sessions")` | Survives process exit |
| The transcript, held by the service | Service-managed (`service_session_id`) | Server-side |
| A transcript kept under a token budget | `CompactionProvider` + in-memory history | Recomputed each call |
| Facts about the user across all conversations | `ContextProvider` (facts on `self`) | Outlives every session |
| Per-session scratch that follows the session | `state` dict in a context provider | The session |
| A per-request value a tool needs, hidden from the model | `function_invocation_kwargs` → `ctx.kwargs` | One run |
| A value written by a tool that must persist | `ctx.session.state[...]` | The session |
| Data passed between middleware in a chain | Shared instance (bound methods) | The instance's lifetime |

---

## Key takeaways

- **A session is working memory.** Pass the *same* `AgentSession` into every `run()` or the chain breaks; `create_session()` is synchronous, and `to_dict()`/`from_dict()` make a conversation resumable.
- **Storage is a provider seam.** Local history (`InMemoryHistoryProvider`, `FileHistoryProvider`, or DB-backed) re-sends the transcript; service-managed history keeps only a remote id. Never mix the two persistence models, and only one provider may `load_messages=True`.
- **Compaction only touches in-memory history.** Pair `CompactionProvider` with an `InMemoryHistoryProvider`, order it *after* the history provider, and remember summarization needs its own cheaper client. It's experimental.
- **Context providers unify everything.** History, durable cross-conversation memory, compaction, and per-run shaping all stack in one `context_providers` list. Facts on `self` outlive sessions; the `state` dict travels *with* a session. Hooks are keyword-only — mind the leading `*`.
- **Runtime context skips the schema.** `function_invocation_kwargs` reach tools via `ctx.kwargs` and never reach the model; `ctx.session.state` written in a tool persists across runs. Don't use blanket `**kwargs`.
- **Shared middleware state is plain Python.** Put both middleware on one object; read `context.result` only after `await call_next()`.

The pattern that holds across all of it: Microsoft Agent Framework doesn't hide state in one magic bag. It gives you named places — the session, the provider list, the kwargs buckets, the shared instance — and asks you to decide *what lives where* and *how long it should last*. Swap the `FoundryChatClient` for another chat client and every one of these mechanics still holds.

---

## Interactive diagrams

Explore the concepts in this guide as self-contained, pan/zoom interactive diagrams (light/dark, no dependencies):

- [Compaction](/blog/diagrams/maf-py-27-compaction.html)
