# Multi-Agent Orchestration in Microsoft Agent Framework (Python)

*A complete guide to coordinating many agents — from a fixed pipeline, to parallel fan-out, to a self-routing mesh, to a planner that decides who acts next, to publishing an agent as a network service other agents can call.*

---

One agent with a good set of tools takes you a long way. But some jobs are bigger than one agent: a draft that needs review, a launch plan that needs a researcher *and* a marketer *and* a lawyer weighing in at once, a support request that has to find the right specialist, an open-ended investigation with no fixed steps. **Orchestration** is how Microsoft Agent Framework (MAF) wires several agents into a single system — and the whole design problem is choosing the *shape* of that system.

MAF gives you a family of builders in `agent_framework.orchestrations`, one per topology: a pipeline, a fan-out/fan-in graph, a self-routing mesh, a coordinated conversation, and a dynamic planner. A sixth pattern, A2A, lives one level up — it turns an agent into a network service so orchestration can cross process and organization boundaries. Each builder is deliberately small: you hand it a list of participants, configure a few knobs, call `.build()`, and run the resulting workflow once with a prompt.

Every agent in every example below is a `FoundryChatClient` agent authenticated with `AzureCliCredential()` — so `az login` first, and set the project endpoint and model as usual. That detail is uniform across all six patterns and worth stating once: **the builders are client-agnostic.** Construction is offline; only `.run()` (or `.stream()`) actually calls the model. Swap the chat client for any other provider and the orchestration shapes hold unchanged. From here on the guide focuses on what makes each topology different.

---

## Pipelines: sequential orchestration

The simplest shape is a line. **Sequential orchestration** wires agents into a pipeline where each runs in turn and passes its output to the next. It fits any "each step builds on the last" job — draft then review, extract then summarize, translate then proof-read. The canonical example chains a copywriter that drafts a marketing sentence into a reviewer that critiques the draft.

You hand a list of participants to `SequentialBuilder` and the **order in the list *is* the execution order**:

```python
from agent_framework.orchestrations import SequentialBuilder

return SequentialBuilder(participants=[writer, reviewer]).build()

# ...
events = await workflow.run("Write a tagline for a budget-friendly eBike.")
final: AgentResponse = events.get_outputs()[0]   # ONLY the last agent's messages
for msg in final.messages:
    print(f"[{msg.author_name or 'assistant'}]\n{msg.text}\n")
```

**The gotcha:** by default each agent sees the **full prior conversation** — the original inputs plus every response so far. Pass `chain_only_agent_responses=True` when you want each agent to consume only the *previous* agent's reply instead; that is the right choice for translation or progressive-refinement chains where earlier context would only confuse the next step. And note what `events.get_outputs()[0]` actually is: an `AgentResponse` holding **only the last agent's messages**, not the whole transcript. Use `msg.author_name` to tell which agent produced each message.

---

## Parallelism: concurrent orchestration

Turn the line sideways and you get a fan. **Concurrent orchestration** runs several agents on the **same prompt in parallel**. Each works independently, then a built-in aggregator fans their answers back in. It fits ensemble reasoning, brainstorming, and voting — anywhere diverse perspectives on one input are the whole point. The key payoff is latency: because the agents overlap, total wall-clock time is `max(agent)`, not the sum. Run a researcher, a marketer, and a legal reviewer on one product-launch prompt and all three Foundry calls happen at once.

`ConcurrentBuilder` wires the fan-out/fan-in graph for you; you just hand it a list of agents (or custom `Executor`s). The default aggregator yields a single `AgentResponse` holding one assistant message per participant:

```python
from agent_framework.orchestrations import ConcurrentBuilder

return ConcurrentBuilder(participants=[researcher, marketer, legal]).build()

# ...
events = await workflow.run("We are launching a budget-friendly electric bike...")
final: AgentResponse = events.get_outputs()[0]
for msg in final.messages:                       # one message per expert
    print(f"[{msg.author_name or 'assistant'}]:\n{msg.text}")
```

**The gotcha:** participants run with **no ordering** — all in parallel — and the default aggregator's single `AgentResponse` does **not** include the original user prompt, only the experts' replies. Read them via `events.get_outputs()[0].messages`, with `msg.author_name` labelling each. Two knobs reshape the output: pass `intermediate_output_from=[...]` to also surface each listed participant's own output as `"intermediate"` events (handy under `stream=True`), or call `.with_aggregator(callback)` to replace fan-in entirely — for example a summarizer agent that consolidates every expert into one string instead of returning them side by side.

---

## Self-routing: handoff orchestration

Sequential and concurrent both decide the routing at build time. **Handoff orchestration** hands that decision to the agents themselves. It wires specialists into a **mesh** where any agent can transfer ("hand off") the whole conversation to a better-suited peer. There is no central orchestrator: control passes agent-to-agent via an auto-injected handoff tool call, and the receiving agent takes full ownership with the complete conversation context. Think customer-support triage routing to refund / order / return specialists — a "damaged order, want a refund" request routes itself through the mesh.

`with_start_agent` picks who receives the first message; `add_handoff(src, [dst, ...])` restricts which transfers are legal:

```python
from agent_framework.orchestrations import HandoffBuilder

workflow = (
    HandoffBuilder(name="customer_support_handoff",
                   participants=[triage_agent, order_agent, return_agent, refund_agent])
    .with_start_agent(triage_agent)
    .add_handoff(triage_agent, [order_agent, return_agent])
    .add_handoff(return_agent, [refund_agent])
    .with_autonomous_mode(turn_limits={triage_agent.name: 3})   # run unattended
    .build()
)
```

Each specialist owns a plain `@tool` function (order lookup, return, refund); the handoff tool itself is injected by the builder — you don't write it.

**The gotcha:** handoff is **inherently interactive**. A handoff is a special tool call, so if an agent answers the user instead of handing off, the workflow can't know what comes next — it emits a `request_info` event (a `HandoffAgentUserRequest`) and waits for human input. To run unattended, call `.with_autonomous_mode()`, an experimental feature that auto-replies to those requests; `turn_limits` caps autonomous turns so it can't loop forever. Each specialist needs `require_per_service_call_history_persistence=True` so local context survives the handoff short-circuits. Only user/agent messages are broadcast for context — handoff tool calls and results are filtered out. And import `HandoffBuilder` from `agent_framework.orchestrations`, not the top-level package.

---

## Coordinated conversation: group chat

Where handoff has no coordinator, **group chat** puts one back at the center. It models a collaborative conversation among several agents, coordinated by an orchestrator that decides who speaks next. Agents share the full conversation history and refine each other's work over multiple rounds — a Researcher gathers facts, then a Writer synthesizes them. The orchestrator sits at the center of a **star topology** and can select speakers via a simple function, an agent-based orchestrator, or fully custom logic. The example below pairs a Researcher and a Writer, cycles between them with round-robin selection, and caps the run at four messages so it always terminates.

Speaker selection and termination are both chosen at construction time:

```python
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

def round_robin_selector(state: GroupChatState) -> str:
    names = list(state.participants.keys())
    return names[state.current_round % len(names)]

return GroupChatBuilder(
    participants=[researcher, writer],
    termination_condition=lambda conversation: len(conversation) >= 4,
    selection_func=round_robin_selector,
    intermediate_output_from=[researcher, writer],
).build()
```

**The gotcha:** speaker selection is set once via **one of** `selection_func` (a function over `GroupChatState`), `orchestrator_agent` (an intelligent `Agent`), or a custom orchestrator — not a mix. `termination_condition` is a callable over the messages list; set a hard cap so the run always ends, though an agent orchestrator may decide to stop earlier on its own. Without `intermediate_output_from=[...]`, only the orchestrator's terminal `"output"` event is emitted and you won't see individual turns. Note the agents do **not** share one `AgentSession` — the orchestrator broadcasts each response so every agent has the full history before its next turn. Run with `stream=True`, then `await stream.get_final_response()` for the terminal `AgentResponse`; streaming yields `AgentResponseUpdate` chunks per turn, so you watch each Foundry-backed agent write live.

---

## Dynamic planning: magentic orchestration

Every pattern so far fixes *something* up front — the order, the fan, the legal transfers, the selection rule. **Magentic orchestration** (from AutoGen's Magentic-One) fixes none of it. It is for complex, open-ended tasks where the solution path isn't known in advance. A dedicated **manager** agent plans the work, keeps a shared task ledger, and — round by round — decides which specialist should act next based on evolving progress. Here a Researcher gathers information and a Coder writes and runs code, collaborating under a Manager until the task is synthesized into a final answer. Unlike a fixed graph, ordering is chosen dynamically.

`participants`, `manager_agent`, and the inner-loop safety limits are all constructor kwargs:

```python
from agent_framework.orchestrations import MagenticBuilder

return MagenticBuilder(
    participants=[researcher_agent, coder_agent],
    intermediate_output_from=[researcher_agent, coder_agent],
    manager_agent=manager_agent,
    max_round_count=10,   # hard cap on coordination rounds
    max_stall_count=3,    # consecutive non-progress rounds before an auto-replan
    max_reset_count=2,    # times the manager may discard the plan and restart
).build()
```

The Coder additionally gets `client.get_code_interpreter_tool()`, so it can actually run analysis code inside the Foundry-hosted interpreter while the manager coordinates.

**The gotcha:** the manager reads each participant's **`description`** to decide who acts next, so make each capability distinct and specific — a vague description means bad delegation. The three limits guard the inner loop: `max_round_count` caps total coordination rounds, `max_stall_count` triggers an auto-replan after consecutive non-progress rounds, and `max_reset_count` caps full plan restarts. `intermediate_output_from=[...]` promotes participant outputs to `"intermediate"` events while the manager's synthesized answer stays the `"output"`. Planning milestones arrive as `event.type == "magentic_orchestrator"` with `event_type` of `PLAN_CREATED` / `REPLANNED` / `PROGRESS_LEDGER_UPDATED`. Plan review is **off** by default in Python (`enable_plan_review=False`), so it runs end-to-end without interaction; the final answer comes from `await stream.get_final_response().get_outputs()[-1]`.

---

## Crossing boundaries: A2A

The five builders above all coordinate agents living in *your* process. **A2A (Agent-to-Agent)** breaks that boundary: it lets *another* agent — in a different process, team, or company — call yours over a standard protocol, and it works both directions. You can **consume** a remote agent as if it were local with `A2AAgent(name=..., url=...)`, or **expose** your local agent by wrapping it in `A2AExecutor(agent)` and mounting that on an ASGI server. Your agent becomes a network service speaking a common language — the same Foundry-backed agent that serves a human through a UI can serve another agent through A2A, unchanged.

```python
from agent_framework.a2a import A2AAgent, A2AExecutor

# CONSUME: talk to someone else's agent as though it were local.
remote = A2AAgent(name="remote-weather", url="http://localhost:9000")
# result = await remote.run("What is the weather in Pune?")

# EXPOSE: wrap your local Agent so an ASGI server can publish it over A2A.
executor = A2AExecutor(build_agent())
```

**The gotcha:** A2A ships separately as `agent-framework-a2a`, so `import agent_framework.a2a` fails on a bare install — run `uv sync --extra hosting`. Constructing an `A2AAgent(url=...)` does **not** make a network call; nothing round-trips unless a server is actually listening at that URL. And exposing an agent is only half the job: `A2AExecutor(agent)` is the server-side adapter, but you still have to mount it on an ASGI server (uvicorn) to get a callable A2A URL. The A2A wrapper never touches the agent's "brain" — the underlying `Agent` over `FoundryChatClient` is exactly the same object either way.

---

## Choosing the right pattern

The patterns are not competitors so much as answers to different questions: *Is the order known? Do agents work on the same input or different parts? Who decides routing — you, the agents, or a planner? Does coordination stay in one process?*

| Pattern | Topology | Who decides flow | Use when |
|---|---|---|---|
| **Sequential** | Pipeline (line) | Fixed list order | Each step builds on the last — draft→review, extract→summarize, translate→proof |
| **Concurrent** | Fan-out / fan-in | All at once, no order | Diverse perspectives on one prompt — ensembles, brainstorming, voting; want `max` latency not sum |
| **Handoff** | Mesh, no center | The agents themselves | Route a request to the right specialist — support triage, tiered escalation |
| **Group chat** | Star (orchestrator-led) | A central orchestrator | Agents collaborate and refine over rounds with shared history |
| **Magentic** | Dynamic (manager-planned) | A planning manager, per round | Open-ended tasks with no known solution path; needs replanning |
| **A2A** | Cross-process service | The calling agent (remote) | Expose or consume an agent across process, team, or company boundaries |

---

## Key takeaways

- **The builders are uniform; the topology is the decision.** Each lives in `agent_framework.orchestrations` (A2A in `agent_framework.a2a`), takes a `participants` list, and builds with `.build()`. All are client-agnostic — the `FoundryChatClient` + `AzureCliCredential` setup is identical everywhere, and only `.run()`/`.stream()` calls the model.
- **Order lives in different places.** Sequential fixes it in the list; concurrent throws it away; handoff lets agents choose it; group chat delegates it to an orchestrator; magentic re-decides it every round.
- **`get_outputs()[0]` rarely means "the whole conversation."** In sequential it's the last agent's messages; in concurrent it's one message per expert with no user prompt. Use `msg.author_name` to attribute turns, and `intermediate_output_from=[...]` to see individual steps under streaming.
- **Autonomy is opt-in and capped.** Handoff blocks on `request_info` unless you enable `with_autonomous_mode()`; magentic guards its loop with `max_round_count` / `max_stall_count` / `max_reset_count`. Set hard caps so runs always terminate.
- **A2A is the boundary layer, not a topology.** It wraps an unchanged agent as a network service so any of the in-process patterns can extend across teams and companies.

Pick the smallest shape that matches your flow of control: a line when steps are ordered, a fan when they're independent, a mesh when routing depends on content, an orchestrator when agents must converse, a planner when the path is unknown — and A2A when the boundary is the network itself.
