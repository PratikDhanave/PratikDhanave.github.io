---
title: "Building Production Multi-Agent Systems: Real-World Lessons from Genie"
description: "I shipped a 15-agent financial assistant processing 40M requests/month. Here's what broke, what scaled, and the patterns that actually work."
tags: "architecture, python, ai, beginners"
canonical_url: "https://pratikdhanave.github.io/articles/27-multi-agent-systems/"
---

# Building Production Multi-Agent Systems: Real-World Lessons from Genie

I shipped a **15-agent financial assistant** on Microsoft's Agent Framework (MAF). It processes 40M requests per month, orchestrates complex workflows, and costs 40% less than alternatives.

This isn't a "how to build agents" tutorial. This is what I learned when agents *broke* in production.

## The Problem With Single-Agent Systems

You start with one agent: "Give me a financial recommendation."

It works. Then users ask for:
- Account analysis + fraud detection + investment advice *in the same request*
- Real-time responses (P99 latency < 2 seconds)
- Cost control (don't spend more on LLM calls than we make in profit)

A single agent trying to do all three becomes a bottleneck. Enter: **multi-agent orchestration**.

## The Architecture That Worked

```
Customer Request
    ↓
Supervisor Agent ← (routes intelligently)
    ├→ Analyst Agent ← (account data)
    ├→ Risk Agent ← (fraud detection)
    ├→ Recommender Agent ← (investment logic)
    └→ Compliance Agent ← (regulatory checks)
    ↓
Aggregator (merge results)
    ↓
Response to customer (< 2 seconds)
```

**Key insight:** Each agent is independent. If Risk Agent is slow, it doesn't block Analyst Agent.

## Pattern 1: Hierarchical Routing

The Supervisor agent doesn't run LLM logic. It's dumb and fast:

```python
class SupervisorAgent:
    def __init__(self, specialists: list[Agent], budget: float):
        self.specialists = specialists
        self.budget = budget
        self.spent = 0.0
    
    async def route(self, request: dict) -> dict:
        # Determine which agents to call based on request type
        required_agents = self.classify_request(request)
        
        # Call them in parallel
        tasks = [
            agent.process(request) 
            for agent in required_agents
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        return self.aggregate(results)
```

**Why this works:**
- Supervisor is lightweight (no LLM call)
- Specialists run in parallel (fast)
- Each specialist is reusable (easy to test, modify, scale)

## Pattern 2: Cost-Aware Routing

This is where the 40% savings came from. Route by **value**, not by capability.

```python
class CostGuardian:
    """Enforce budget limits on every agent call."""
    
    async def execute_with_budget(self, agent: Agent, request: dict):
        cost = agent.estimated_cost(request)
        
        # High-value decision (customer asking about $50K portfolio)?
        # Use expensive model (GPT-4)
        if request.value > 10000:
            return await agent.execute_with_model("gpt-4")
        
        # Low-value decision (quick lookup)?
        # Use cheap model (Ollama)
        if request.value < 100:
            return await agent.execute_with_model("ollama:3b")
        
        # Medium value? Tradeoff model
        return await agent.execute_with_model("gpt-3.5-turbo")
```

**Result:** 30-40% cost reduction without sacrificing quality.

## Pattern 3: Structured Message Passing

Don't let agents communicate via free-form strings. Use schemas:

```python
from dataclasses import dataclass

@dataclass
class AnalystResult:
    account_id: str
    balance: float
    monthly_income: float
    recent_transactions: list[dict]
    confidence: float  # 0-1, how confident in this data?

# Supervisor validates before passing to next agent
def validate_and_forward(result: AnalystResult) -> dict:
    if result.confidence < 0.8:
        return {"error": "low confidence, retry"}
    
    return result.dict()
```

**Why:** Catch errors early. Agents can validate input before processing.

## Pattern 4: Timeout & Fallback Chains

In production, agents timeout. Have a plan:

```python
async def call_with_fallback(primary_agent, fallback_agents, request, timeout=2.0):
    """Try primary. If timeout, try fallback 1. If timeout, try fallback 2."""
    
    for agent in [primary_agent] + fallback_agents:
        try:
            result = await asyncio.wait_for(
                agent.process(request),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            continue  # Try next agent
    
    # All failed
    return {"error": "all agents timed out"}
```

Real example: Risk Agent is slow (database query backlog). Fallback to Risk Agent cached result. User gets a response instead of timeout.

## Observability: The Game Changer

You need to see **every** agent call:

```python
import opentelemetry.trace as trace

tracer = trace.get_tracer(__name__)

async def agent_execute(agent_id: str, request: dict):
    with tracer.start_as_current_span(f"agent.{agent_id}") as span:
        span.set_attribute("request.type", request["type"])
        span.set_attribute("request.value", request["value"])
        
        result = await agent.process(request)
        
        span.set_attribute("latency_ms", time.time() - start)
        span.set_attribute("cost", agent.last_cost)
        span.set_attribute("success", result.get("error") is None)
        
        return result
```

In production, I can see:
- Which agent is slow (latency heatmap)
- Which agent is expensive (cost per call)
- Which agent fails most (error rate by agent)

This data drove our optimization decisions.

## The Real Numbers

**Before multi-agent:**
- P99 latency: 5 seconds (single agent doing everything)
- Cost per request: $0.032
- Error rate: 2.1%

**After multi-agent + patterns above:**
- P99 latency: 1.2 seconds (40% reduction)
- Cost per request: $0.018 (40% savings)
- Error rate: 0.3% (better due to fallbacks)

**Scale:** 40M requests/month × $0.014 savings = **$560K/month saved**.

## The Trap: Premature Multi-Agent

Don't build this until you need it. Signals you need multi-agent:

- Single agent request handling time > 1 second
- One request needs >3 different LLM calls
- Cost per request > $0.01
- Error rate > 0.5%

Before that? Single agent is simpler and faster to build.

## What I'd Do Differently

1. **Start with one agent, add observability immediately** — then you'll see where multi-agent helps
2. **Cost budgets from day 1** — not an afterthought
3. **Test with mocks first** — multi-agent systems are hard to test with real LLM calls
4. **Document processor agreements** — especially important if agents share data

## The Hardest Part

Not the architecture. The hardest part is **testing**. You can't mock everything. You need:

- Unit tests (mock all LLM calls)
- Integration tests (real agents, fake data)
- Load tests (does it handle 30K RPS?)
- Cost audits (are we actually saving money?)

---

## Next Steps

Multi-agent systems aren't magic. They're **cost-aware, observable, fault-tolerant orchestration**.

If you're building agents:
1. Start with one
2. Add observability (OpenTelemetry)
3. Scale to multiple agents only when you hit limits
4. Enforce budgets from the start

**Questions?** I detail implementation patterns for compliance-driven multi-agent systems (GDPR, PSD2) on my [portfolio](https://pratikdhanave.github.io/articles/27-multi-agent-systems/).

---

**Tags:** #architecture #python #ai #production #observability

