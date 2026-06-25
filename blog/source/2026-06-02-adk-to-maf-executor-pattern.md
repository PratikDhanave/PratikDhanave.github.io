# The Executor Pattern: ADK→Microsoft Agent Framework Conversion for Agentic Control Flow

*How to port ADK's orchestration callbacks to Microsoft Agent Framework builders without losing control.*

---

## The Problem: Where Does Control Live?

In ADK, a `SequentialAgent` manages sub-agents internally:

```python
orchestrator = SequentialAgent(
    sub_agents=[planner, executor, reviewer],
    model="gemini-2.5-flash"
)
result = await orchestrator.run(prompt)  # Returns final AgentResponse
```

The orchestrator owns the loop. You don't see intermediate states. Callbacks let you hook into them, but you're an observer, not the driver.

In Microsoft Agent Framework (MAF), builders are different:

```python
workflow = SequentialBuilder(participants=[planner, executor, reviewer])
built = await workflow.build()  # Returns the compiled workflow

result = await built.run(prompt)  # AgentResponse
```

The builder compiles into a workflow. You call `run()`. But **you can also iterate the participants yourself** — that's the executor pattern.

## The Executor Pattern

Instead of relying on the builder's loop, you become the loop:

```python
from agent_framework import Agent, AgentThread

# Create a thread (conversation state)
thread = AgentThread()

# Define agents
planner = Agent(
    client=build_chat_client(),
    name="Planner",
    instructions="Break down the request into steps."
)

executor = Agent(
    client=build_chat_client(),
    name="Executor",
    instructions="Execute the plan one step at a time."
)

reviewer = Agent(
    client=build_chat_client(),
    name="Reviewer",
    instructions="Review the executed plan."
)

# Manual orchestration loop
agents = [planner, executor, reviewer]
for agent in agents:
    result = await agent.run(prompt, thread=thread)
    print(f"{agent.name}: {result.message.content}")
    
    # YOU control escalation, retry, etc.
    if should_escalate(result):
        break
```

**This is the executor pattern.** You're the orchestrator. The agents are pure. The thread carries state.

## Why It Matters for ADK→Microsoft Agent Framework Porting

In ADK, if you had a custom callback:

```python
def before_agent_callback(context):
    print(f"Agent {context.agent_name} is running")
    # Custom logic: log, meter, validate

# ADK listens via internal hooks
seq_agent = SequentialAgent(
    sub_agents=[...],
    before_agent_callback=before_agent_callback
)
```

In Microsoft Agent Framework, **you own the loop**, so you just add the logic:

```python
for agent in agents:
    print(f"Agent {agent.name} is running")  # Same observability
    result = await agent.run(prompt, thread=thread)
    # Custom logic: log, meter, validate, etc.
```

It's more explicit. You see every handoff. You control every decision.

## Real Example: Financial Supervisor

Our Genie agent (financial advisor) has a supervisor that delegates to specialists:

**ADK version**: Supervisor is an `LlmAgent` that routes to sub-agents via callbacks.

**Microsoft Agent Framework version**: Supervisor is an `Agent` with tools. Each tool wraps a specialist agent:

```python
@tool
async def ask_analyzer(question: str) -> str:
    """Ask the analyzer agent a question."""
    analyzer = Agent(..., name="Analyzer")
    thread = AgentThread()
    result = await analyzer.run(question, thread=thread)
    return result.message.content

supervisor = Agent(
    client=build_chat_client(),
    name="Supervisor",
    instructions="Route financial questions to specialists",
    tools=[ask_analyzer, ask_forecaster, ask_anomaly_detector]
)

result = await supervisor.run(user_prompt)
```

**Cleaner, more testable.** Each agent is a black box. The supervisor decides when to call them. Tools are the interface.

## The Conversion Checklist

When porting ADK agents to Microsoft Agent Framework:

- [ ] Identify orchestration pattern (Sequential? Router? Loop?)
- [ ] If Sequential: port as SequentialBuilder or manual loop
- [ ] If Router (manager → specialists): use Agent + tools pattern
- [ ] If Loop (refine until converged): manual loop with `max_iterations` check
- [ ] Extract all callbacks → invert to executor-pattern logic
- [ ] Test each agent independently; test orchestration separately

## The Lesson

ADK hides orchestration. Microsoft Agent Framework exposes it. The executor pattern isn't "less convenient" — it's more honest. You see every step. You can meter, log, audit, and decide at every point.

That's what 18 agents taught us.

---

Next: [Token Exchange Patterns](/blog/posts/adk-to-maf-token-exchange.html)
