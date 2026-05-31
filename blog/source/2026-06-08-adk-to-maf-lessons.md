# Lessons from Converting 18 Agents in 90 Days

*The patterns that worked, the traps we fell into, and what we'd do differently.*

---

## What Worked

### 1. Provider Abstraction (The Win)

We swapped `PROVIDER=openai` mid-project to reduce costs. Zero code changes. That's the golden rule: **if your agents are portable, your provider choice is a dial, not a decision.**

### 2. Executor Pattern Over Implicit Orchestration

ADK's implicit callbacks felt convenient until we needed to audit tool calls or add approval gates. MAF's executor pattern (you own the loop) was more verbose upfront but 10x more powerful downstream.

### 3. Tools as Pure Functions

Wrapping tools in governance (audit, approval, policy) became trivial because tools were @decorated functions, not opaque instances.

### 4. AgentThread for Conversation State

Explicit thread management meant we could serialize conversations, replay them in tests, and audit every turn. No more "where did this session state come from?"

## What Was Hard

### 1. Token Budgeting in Multi-Agent Runs

We built 3 versions:
- V1: Per-agent counters (failed; didn't track cross-agent costs)
- V2: Global counter + coordinator middleware (worked but was clunky)
- V3: Thread-scoped token tracker (clean; final solution)

**Lesson**: Token budgeting is non-trivial in multi-agent systems. Plan for it early.

### 2. Approval Workflows

ADK agents don't really have a pattern for "wait for human approval." We built it:
```python
@governed_write(approval=True)
def execute_trade(...):
    # Automatically queues for approval if conditions met
    # Coordinator checks approval_status() before proceeding
```

Took 2 iterations to get right.

### 3. Cross-Agent Handoff Semantics

When Agent A calls Agent B, what should Agent B see?
- Option 1: The raw request from Agent A (minimal context)
- Option 2: The full conversation so far (max context, but can bias Agent B)
- Option 3: A filtered view (tricky to define correctly)

We landed on Option 3 (filtered) after realizing Option 2 caused "hallucination contagion" (Agent B inherited Agent A's mistakes).

**Lesson**: Handoff context is a design choice. Don't inherit context blindly.

### 4. Error Handling in Tool Chains

When a tool fails, do you:
- Stop the agent?
- Retry silently?
- Ask the agent to handle the error?

We ended up with a 3-tier strategy:
1. Tool has internal retry logic (exponential backoff)
2. Agent middleware catches exceptions, logs, and lets the agent decide
3. Supervisor (human or another agent) handles escalation

## What We'd Do Differently

### 1. Test Agents Earlier

We wrote agents, then tested them. Better approach:
- Write the agent interface (expected input/output)
- Mock the tools
- Test the agent against mocked tool responses
- Only then connect real tools

### 2. Version Your Prompts

Prompts evolve. We should have:
```
agents/analyzer/prompts/
  v1.txt (original)
  v2.txt (added context)
  v3.txt (better formatting)
```

With A/B testing to measure which version performed better.

### 3. Budget Token Spend From Day 1

We tried to retrofit token budgeting late. It's easier to build in from day 1:
```python
async def run_agent(agent, prompt, budget=5000):
    # Enforce budget throughout
    return await agent.run(prompt, max_tokens=budget)
```

### 4. Use Observability From Day 1

We added tracing after the fact. Every agent should emit traces from day 1:
```python
@with_telemetry
async def run_agent(...):
    return await agent.run(...)
```

## The Numbers

| Metric | Result |
|--------|--------|
| Agents converted | 18 |
| Timeline | 90 days (part-time) |
| Code changed per agent | ~500 lines avg |
| Bugs found during port | 3 (porting caught edge cases!) |
| Zero-code provider swaps | 4 (dev → staging → prod, then back to dev) |
| Approval workflows built | 2 |
| Governance policies written | 5 |

## The Thesis

You don't port to MAF because you love MAF. You port because **portable agents are powerful agents.** Once your orchestration, tools, and state management are separate from your LLM choice, everything else becomes composable.

Provider abstraction isn't just "swap models." It's architectural clarity. It's the difference between agents as black boxes and agents as components.

---

## Next Steps

Now that you've ported your agents:
1. Wire in observability (Laminar or self-hosted Jaeger)
2. Add governance (approval gates, audit logs, policy enforcement)
3. Build dashboards (token spend, latency, error rates)
4. A/B test prompt versions
5. Deploy to production with confidence

The hardest part is behind you. The rest is engineering.

---

## Links

- [18 Agent Migration Case Study](https://github.com/PratikDhanave/genesisofaienginering/tree/main/microsoft)
- [CONVERSION_GUIDE.md](https://github.com/PratikDhanave/genesisofaienginering/blob/main/microsoft/CONVERSION_GUIDE.md)
- [MAF Reference Architecture](https://github.com/microsoft/agent-framework)
- [Agent Governance Toolkit (AGT)](https://github.com/microsoft/agent-governance-toolkit)
