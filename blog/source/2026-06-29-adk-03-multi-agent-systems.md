# Multi-Agent Systems in ADK: Coordinators, sub_agents, and LLM-Driven Delegation

*How one agent routes work to specialists — and why the description field is the most important string you write.*

---

Module 02 of this series covered **workflow agents** — `SequentialAgent`, `ParallelAgent`, `LoopAgent` — where *you* hard-code the orchestration. The order is fixed; the LLM never decides who runs next. This post is about the opposite: **dynamic composition**, where the *model* chooses how work flows between agents at runtime. In Google's Agent Development Kit (ADK), the simplest and most common form of this is **delegation** — a coordinator agent that transfers control to the right specialist based on what the user asked.

## The mechanism: `sub_agents` + `description`

You give an `LlmAgent` a list of `sub_agents`. ADK exposes those children to the coordinator's model and lets it call an implicit `transfer_to_agent(...)` function. The model decides *which* child to transfer to by reading each child's **`description`** — a one-line summary of what that agent is for. That single string is the routing table. Write it vaguely and you get bad routing; there is no separate config that overrides it.

Here is a two-specialist coordinator in Python:

```python
from google.adk.agents import LlmAgent

MODEL = "gemini-flash-latest"

weather_specialist = LlmAgent(
    name="weather_specialist",
    model=MODEL,
    description="Answers questions about the weather in a city.",
    instruction="You answer weather questions. If asked anything else, say you only do weather.",
)

joke_specialist = LlmAgent(
    name="joke_specialist",
    model=MODEL,
    description="Tells one short, family-friendly joke on request.",
    instruction="Tell exactly one short, family-friendly joke.",
)

coordinator = LlmAgent(
    name="coordinator",
    model=MODEL,
    description="Routes the user to the correct specialist.",
    instruction=(
        "You are a router. If the user asks about weather, transfer to weather_specialist. "
        "If the user wants a joke, transfer to joke_specialist. Do not answer yourself."
    ),
    sub_agents=[weather_specialist, joke_specialist],
)
```

Ask `"what's the weather in Paris?"` and the coordinator transfers to `weather_specialist`; ask `"tell me a joke"` and it transfers to `joke_specialist`. The `instruction` nudges the coordinator's *behaviour* ("don't answer yourself"), but the actual matching is driven by the sub-agents' `description` fields. This is why Module 01 insisted on writing a crisp one-liner for every agent — in a multi-agent system that line is load-bearing.

## The Go form

ADK is dual-language, and the Go SDK mirrors the shape exactly — a config struct with a `SubAgents` slice instead of a keyword argument:

```go
import (
    "google.golang.org/adk/v2/agent"
    "google.golang.org/adk/v2/agent/llmagent"
)

weather, _ := llmagent.New(llmagent.Config{
    Name: "weather_specialist", Model: m,
    Description: "Answers questions about the weather in a city.",
    Instruction: "You answer weather questions only.",
})
joke, _ := llmagent.New(llmagent.Config{
    Name: "joke_specialist", Model: m,
    Description: "Tells one short, family-friendly joke.",
    Instruction: "Tell exactly one short, family-friendly joke.",
})

coordinator, _ := llmagent.New(llmagent.Config{
    Name: "coordinator", Model: m,
    Description: "Routes the user to the correct specialist.",
    Instruction: "Transfer weather questions to weather_specialist and joke requests " +
        "to joke_specialist. Do not answer yourself.",
    SubAgents: []agent.Agent{weather, joke},
})
```

Same three ingredients — name, description, sub-agents — same routing behaviour. In both languages, attaching a child as a sub-agent sets its parent link automatically (`sub.parent_agent` in Python; the equivalent internal parent in Go).

## Delegation is a *transfer*, not a call

The key thing to internalise: when the coordinator delegates, it **hands over the turn**. The specialist responds to the user directly and owns the rest of the conversation. Control does not automatically bounce back to the coordinator after each reply.

That behaviour is tunable. By default a sub-agent can transfer *back up* to its parent or *sideways* to a peer. You can lock those doors:

```python
weather_specialist = LlmAgent(
    name="weather_specialist",
    model=MODEL,
    description="Answers questions about the weather in a city.",
    disallow_transfer_to_parent=True,   # can't hand control back up
    disallow_transfer_to_peers=True,    # can't jump to a sibling
)
```

The Go equivalents are `Config{DisallowTransferToParent: true}` and `DisallowTransferToPeers: true`. Use these when you want a specialist to fully own a task once it's engaged, rather than ping-ponging control around the hierarchy.

## Mental model: delegation vs. agent-as-tool

Delegation is one of two ways to compose agents, and it's worth contrasting with the other — **agent-as-tool** — because they feel similar but differ on one axis: *who keeps control.*

- **Delegation (transfer):** the coordinator hands off, the specialist finishes the turn. Use it for *"route this to the right expert."*
- **Agent-as-tool:** the parent *calls* the child like a function, gets a return value, and **keeps** control to continue reasoning. Use it for *"summarize this text, then use the summary in my next step."*

Agent-as-tool wraps the child so the parent can invoke it:

```python
from google.adk.tools import agent_tool

summarizer = LlmAgent(
    name="summarizer", model=MODEL,
    description="Summarizes provided text into exactly one sentence.",
    instruction="Summarize the user's text into exactly one concise sentence.",
)

assistant = LlmAgent(
    name="assistant", model=MODEL,
    instruction="When the user gives long text and asks for a summary, call the "
                "summarizer tool, then present the result.",
    tools=[agent_tool.AgentTool(agent=summarizer)],
)
```

In Go that's `agenttool.New(summarizer, nil)` passed in `Tools: []tool.Tool{...}`.

**One reuse rule for both languages:** an agent can have only **one** parent. If you want to both delegate to an agent *and* wrap it as a tool, create **two distinct instances** — reusing a single object makes the second parent assignment conflict. That's why the summarizer above is a separate agent, not the weather or joke specialist reused.

## When to reach for delegation

Use a coordinator/dispatcher when you have several **specialist** agents with clearly separable jobs — a support triage that routes to billing vs. technical vs. account agents, or an assistant that fans out to domain experts. Keep each specialist's `description` sharp and non-overlapping, because overlap is exactly where the model's routing goes wrong. And remember the contrast with Module 02: reach for a **workflow agent** when the sequence is known and fixed, and a **coordinator with `sub_agents`** when the *right next step depends on the input* and you want the LLM to decide.

*Next in the series: Module 04 — Tools, the full ecosystem of built-in, OpenAPI, MCP, and third-party tools, plus tool-level human-in-the-loop.*
