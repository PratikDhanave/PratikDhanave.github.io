# Pydantic AI in Production

*A framework earns its place not in the demo but in production — under real traffic, real failures, and the need to observe, control cost, and evolve. Pydantic AI's typed, testable design carries into production well, and paired with observability and the model-agnosticism it's had all along, it makes agents you can actually operate. This closing post covers taking a Pydantic AI agent live.*

The series built a typed, tooled, tested agent. This final post covers running it in production: observability, the model-agnosticism that becomes a cost and reliability lever at scale, error handling, and an honest summary of when Pydantic AI is the right choice. The through-line is that the same properties that made development pleasant — typing, DI, testability, model-agnosticism — are what make production manageable, because production is where unobservable, untestable, locked-in agents fail.

## Observability

In production you can't see inside an agent's reasoning without instrumentation, and (from the observability series) LLM applications especially need it — the model is a black box, tool calls can fail, and costs accrue per token. Pydantic AI integrates observability, notably with **Logfire** (from the Pydantic team) and, being built on open standards, with **OpenTelemetry**-based tracing:

- **Trace agent runs** — see the full flow of a run: the prompts sent, the model's responses, which tools were called with what arguments, and the final output. This is the distributed-tracing idea (from the observability series) applied to an agent's internal steps, making a run's behavior inspectable rather than opaque.
- **Track token usage and cost** — agent runs consume tokens (and money); observing usage per run is how you monitor and control cost (the AI cost series), catching expensive patterns.
- **Diagnose failures** — when an agent misbehaves (wrong tool, bad output, a loop), traces show *where* it went wrong, turning "the agent did something weird" into a specific, diagnosable step.

The practical guidance from the observability series holds: instrument before you launch, not after the first incident. Pydantic AI's built-in observability support (Logfire/OTel) makes this straightforward, and it's essential — an agent you can't observe is an agent you can't operate or improve.

## Model-agnosticism as a production lever

Model-agnosticism (from the first post) is a nice development convenience, but in production it becomes a genuine strategic lever, echoing the keep-the-model-swappable and cost themes across this blog:

- **Cost control via model choice** — because swapping models is configuration, you can route to the cheapest model that meets each task's quality bar, or move to a cheaper model as options improve, without rewriting your agent. This is the biggest cost lever, and model-agnosticism is what makes it cheap to pull.
- **Reliability via fallback** — you can fall back to an alternative provider if one has an outage or rate-limits you, improving resilience — the network/distributed-systems resilience mindset applied to model providers.
- **No lock-in** — your typed agent logic, tools, and outputs are independent of the provider, so you're never trapped by one vendor's pricing or availability. As the model landscape shifts, you adapt by configuration.

So the property that felt like a minor convenience during development pays off as a cost, reliability, and flexibility advantage in production. Design to exploit it: keep the model a configured choice, and revisit that choice as costs and capabilities change.

## Error handling and reliability

Production agents fail — models error or rate-limit, tools throw, outputs occasionally can't be validated even after retries — and handling this is part of operating them (the resilience lessons from the distributed-systems and networking series apply directly):

- **Model/API failures** — wrap model calls with the network-resilience practices: timeouts, retries with backoff for transient errors, and fallback (to another provider, via model-agnosticism) or graceful degradation when a model is unavailable.
- **Validation failures** — structured outputs retry automatically on validation errors (the structured-outputs post), but a persistent failure to produce valid output needs handling — surface a clear error or fallback rather than crashing.
- **Tool failures** — tools call real systems that fail; handle tool errors so the agent can recover or degrade gracefully, and bound the agent's loop so a confused agent fails fast rather than spinning (and burning tokens).
- **Cost/latency bounds** — set limits (max tokens, max tool iterations) so a runaway run can't consume unbounded budget or time — the load-shedding mindset for agents.

Pydantic AI's typing helps here: typed tool contracts and validated outputs mean many failure modes surface as clear, catchable errors rather than silent bad data. But you still build the resilience around the agent — treat model and tool calls as the unreliable network calls they are.

## When Pydantic AI is the right choice

Pulling the series together into an honest verdict (complementing the [agent-framework comparison](/blog/posts/ai-decisions-02-agent-frameworks.html)):

- **Choose Pydantic AI when** you're building in Python, value type safety and testability, and need reliable **structured outputs** — its sweet spot is applications where the agent produces typed data your program consumes (extraction, classification, typed tool-driven workflows, structured APIs), and where you want production reliability through testing and observability. It's especially natural if you already use Pydantic/FastAPI.
- **Its standout strengths** are typed/validated outputs (turning the most brittle part of LLM apps into the most reliable), genuine testability (deterministic tests via test models + DI — rare among agent frameworks), and model-agnosticism (cost/reliability/no-lock-in).
- **Consider alternatives when** your shape is different: heavy graph-based stateful orchestration with complex control flow (LangGraph), a multi-agent-team metaphor (CrewAI), a declarative prompt-optimization approach (DSPy), or a non-Python stack. Pydantic AI is a Python, type-first, agent framework — excellent when that's what you want, not a universal answer.

## The series in one arc

Pydantic AI, end to end: it brings **type safety** to agents (post one), centered on the **Agent** as a type-parameterized reusable unit (post two), whose flagship feature is **structured outputs** — validated typed data instead of parsed strings (post three). Agents act through **tools** that are just typed Python functions (post four), receive their context via typed **dependency injection** (post five), hold conversation through explicit **messages** and stay responsive via **streaming** (post six), and — crucially — are genuinely **testable** with test models plus injected fakes (post seven), then run reliably in **production** with observability, model-agnosticism, and resilience (this post). The unifying idea is that Pydantic AI applies the typed, validated, tested, injected discipline of good modern Python to LLM agents — so you build agents the way you build the rest of your robust Python, and get agents you can actually trust and operate. That's its distinctive contribution to the agent-framework landscape.

## Key takeaways

- Production needs observability: Pydantic AI integrates with Logfire and OpenTelemetry to trace agent runs (prompts, tool calls, outputs), track token usage/cost, and diagnose failures — instrument before launch, because an unobservable agent can't be operated.
- Model-agnosticism becomes a production lever: swap models by configuration to control cost (route to the cheapest model meeting the quality bar), add reliability (fallback across providers), and avoid lock-in — the convenience from development pays off as strategy at scale.
- Handle failure like the unreliable calls it is: timeouts/retries/fallback for model and tool calls, handling for persistent validation failures, and bounds (max tokens, max iterations) so runaway runs can't burn unbounded budget — typing surfaces many failures as catchable errors.
- Choose Pydantic AI for Python apps valuing type safety, testability, and reliable structured outputs (extraction, classification, typed workflows), especially with a Pydantic/FastAPI background; its standout strengths are typed outputs, genuine testability, and model-agnosticism.
- Consider alternatives for graph-based orchestration (LangGraph), multi-agent-team metaphors (CrewAI), declarative optimization (DSPy), or non-Python stacks — Pydantic AI is a type-first Python agent framework, excellent for that shape, not a universal answer.

## Further reading

- [Testing and evals (previous post)](/blog/posts/pydai-07-testing-and-evals.html)
- [What is Pydantic AI? — start of the series](/blog/posts/pydai-01-what-is-pydantic-ai.html)
- [AI Architecture Decisions: choosing an agent framework](/blog/posts/ai-decisions-02-agent-frameworks.html)
