# Workflow Agents: Deterministic Orchestration in ADK
*When you want fixed control flow, don't ask the model — wire it yourself.*

---

An LLM agent *reasons*: it decides, at runtime, what to do next. A **workflow agent** does the opposite — it runs sub-agents in a fixed, predetermined pattern that you specify in code. The key mental shift is this: **a workflow agent contains no model**. It is plain control flow, and the intelligence lives entirely in the LLM sub-agents it coordinates.

This is the second concept in the series. Google's [Agent Development Kit](https://google.github.io/adk-docs/) ships three workflow shapes — sequential, parallel, and loop — plus a custom escape hatch for anything they can't express. This post covers all four and, crucially, how sub-agents pass data to each other.

## Three shapes (plus one)

| Agent | Runs sub-agents… | Use for |
|-------|-----------------|---------|
| **Sequential** | one after another, sharing state | pipelines: draft → review → edit |
| **Parallel** | concurrently, independent branches | fan-out: research 3 sources at once |
| **Loop** | repeatedly until `max_iterations` or *escalate* | iterative refinement, retry-until-good |
| **Custom** | whatever code you write | anything the three above can't express |

Because these agents make no model calls, their behavior is deterministic and unit-testable. That is the whole point: you get repeatable orchestration for free and spend your token budget only where judgment is actually needed.

## Sequential: a pipeline sharing state

The canonical shape is a pipeline where each stage feeds the next. An `LlmAgent` writes its result to session state via `output_key` (covered in the previous post); the next stage reads it by name.

```python
from google.adk.agents import LlmAgent, SequentialAgent

writer = LlmAgent(
    name="writer",
    model="gemini-flash-latest",
    instruction="Write a vivid 3-sentence story about {topic}.",
    output_key="story",           # result lands in state['story']
)
critic = LlmAgent(
    name="critic",
    model="gemini-flash-latest",
    instruction="Give one sentence of critique of this story:\n{story}",
    output_key="critique",
)

pipeline = SequentialAgent(
    name="story_pipeline",
    sub_agents=[writer, critic],  # writer runs, THEN critic sees state['story']
)
```

The `{story}` placeholder in the critic's instruction is resolved from state at call time. Stage *N+1* sees everything stage *N* wrote — that is how the two stages communicate. There are **no return values** between sub-agents; the shared session state is the only channel.

## How state actually flows

This is the part that trips people up, so it's worth being precise. Sub-agents never call each other and never return values. Instead:

- An **LLM sub-agent** writes its answer to state via `output_key`.
- A **custom sub-agent** writes via a `state_delta` attached to the event it emits — you don't mutate the state dict directly.

Writing through an event delta (rather than mutating a map) keeps every state change on the event log, so the whole run is replayable and auditable. Here is a custom (non-LLM) stage that does the same draft-then-review dance deterministically:

```python
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions

class DraftAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        topic = ctx.session.state.get("topic", "something")
        draft = f"A short note about {topic}."
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"draft": draft}),  # write
        )
```

The next stage reads it back with `ctx.session.state.get("draft")`. In Go the same idea uses the native streaming construct — a Go 1.23 range-over-func iterator instead of an async generator, and the error travels *in* the stream rather than being raised:

```go
func draftRun(ctx agent.InvocationContext) iter.Seq2[*session.Event, error] {
    return func(yield func(*session.Event, error) bool) {
        topic := stateString(ctx, "topic", "something")
        draft := fmt.Sprintf("A short note about %s.", topic)
        yield(&session.Event{
            Author:  "draft",
            Actions: session.EventActions{StateDelta: map[string]any{"draft": draft}},
        }, nil)
    }
}
```

Reading state in Go returns a value-and-error pair: `ctx.Session().State().Get("draft")` gives `(any, error)`.

## Parallel: fan-out without collisions

`ParallelAgent` runs its sub-agents at the same time — on `asyncio` tasks in Python, on goroutines in Go. Because branches run against the *same* starting state but write independently, the one rule that matters is: **give each branch a distinct `output_key`**, or concurrent writes clobber each other. The framework merges the branch deltas when they join.

```python
from google.adk.agents import ParallelAgent

research = ParallelAgent(
    name="research_fanout",
    sub_agents=[
        LlmAgent(name="tech", model="gemini-flash-latest",
                 instruction="Technical angle on {topic}, 2 sentences.",
                 output_key="tech_view"),   # distinct key
        LlmAgent(name="econ", model="gemini-flash-latest",
                 instruction="Economic angle on {topic}, 2 sentences.",
                 output_key="econ_view"),   # distinct key
    ],
)
```

## Loop: iterate until good enough

`LoopAgent` re-runs its children, accumulating state each pass, until it hits `max_iterations` **or** a sub-agent signals *escalate*. That escalate flag is how a "quality checker" stage says "we're done, stop looping" instead of always burning every iteration:

- Python, in a tool or callback: `tool_context.actions.escalate = True`.
- Python, in a custom agent: `yield Event(actions=EventActions(escalate=True))` — a custom agent's context has no `.actions`, so you attach it to the emitted event.
- Go: yield an event whose `Actions.Escalate` is true.

```python
from google.adk.agents import LoopAgent

refine = LoopAgent(
    name="refine_loop",
    max_iterations=3,
    sub_agents=[LlmAgent(name="refiner", model="gemini-flash-latest",
                         instruction="Improve this, or say DONE:\n{paragraph?}",
                         output_key="paragraph")],
)
```

## Constructing them in Go

Go nests the shared fields (name, description, sub-agents) inside an embedded `agent.Config` and puts workflow-specific fields on the outer struct. Python passes everything as flat keyword args:

```go
loopagent.New(loopagent.Config{
    MaxIterations: 3,                     // workflow-specific, outer struct
    AgentConfig: agent.Config{           // shared fields, embedded
        Name:      "refine_loop",
        SubAgents: []agent.Agent{refiner},
    },
})
```

Sequential and parallel follow the same `New(Config{AgentConfig: ...})` shape.

## Mental model: fixed wiring vs. dynamic delegation

Reach for a workflow agent when *you* already know the control flow: the order of stages, the branches to fan out, the loop bound. The graph is fixed and the model never decides it. That contrasts sharply with the next concept in the series — **multi-agent delegation**, where an LLM coordinator decides at runtime which sub-agent handles a request. Same building blocks, opposite locus of control: here the shape is compiled into your code; there it emerges from the model's reasoning. Use a workflow agent whenever determinism, testability, or a strict SLA matters more than flexibility.

> **API note:** ADK's `SequentialAgent`, `ParallelAgent`, and `LoopAgent` are the clearest way to *learn* these ideas and still run today, but current releases point toward a more general graph-based orchestrator that folds sequential, parallel, loop, and branching into one graph. The concepts — ordering, fan-out, iteration, shared state — carry over unchanged. Check the [official docs](https://google.github.io/adk-docs/) for the version you're on.

*Next in the series: multi-agent systems — dynamic, LLM-driven delegation, the mirror image of this post's fixed orchestration.*
