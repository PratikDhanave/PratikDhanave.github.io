# Why We Migrated from Google ADK to Microsoft MARA

*The philosophy, trade-offs, and what we learned converting 18+ agents in 3 months.*

---

## The Story

In early 2025, our multi-agent platform (Genie: a financial advisor, Bodh: a medical AI) lived on Google's Application Development Kit (ADK). It worked. The agents were fast, the orchestration patterns were clear, and Gemini was powerful.

But we hit a fork in the road:

1. **ADK's vision**: Tightly coupled to Google Cloud. Vertex AI, Gemini models, Google's tool ecosystem.
2. **Our vision**: Platform-agnostic multi-agent systems. Swap LLM providers (OpenAI, Azure, local Ollama). Run on any cloud (GCP, Azure, on-prem). Keep agent logic pure; LLM choice should be a config knob.

So we chose Microsoft's Agent Framework (MAF) — the reference architecture, not the vendor lock-in.

## What Changed (The Mapping)

### Agents: Minimal friction
- ADK's `LlmAgent(model="gemini-2.5-flash", instruction=, tools=)` → MAF's `Agent(client=build_chat_client(), instructions=, tools=)`
- The `model=` parameter is gone. Instead, `build_chat_client()` reads `PROVIDER=ollama|openai|foundry` from `.env`. **One code path, any LLM.**

### Orchestration: New builders
- ADK's `SequentialAgent([agent1, agent2])` → MAF's `SequentialBuilder(participants=[...]).build()`
- We ported all 5 orchestration patterns: Sequential, Concurrent, Handoff, GroupChat, Magentic.
- Result: Same control flow, cleaner abstractions.

### Tools: Decorator pattern
- ADK: `tools=[fn]` (pass functions directly)
- MAF: `@tool` decorator + same signature/docstring
- We now have governed wrappers (policy-as-code, OPA sidecar) built on top. Better composability.

### Memory & State
- ADK: `session_service.state[key]`
- MAF: `AgentThread` for conversation history + `MemoryFileStore` for long-term memory
- The semantic mapping is 1:1. We kept the same keys; execution is more explicit.

## Why It Matters

**Provider portability**: On day 90, we swapped `PROVIDER=openai` (cost reason) without touching agent code. Try that with ADK.

**Clarity**: MAF separates concerns. An agent is logic. A builder is orchestration. A client is provider. Test each independently.

**Open source credibility**: MAF isn't a Google project. It's Microsoft's reference architecture. We can talk about it, teach it, share examples without vendor politics.

## The Cost

- **3 months** to port 18 agents (engineers working part-time on this; not full-time migration)
- **~500 lines of code changes** per average agent
- **Zero behavioral loss**: Every agent still solves the same problem the same way

## The Thesis

If your agents are truly portable (they should be), your orchestration is declarative (it should be), and your tools are pure functions (they should be), then the LLM framework is plumbing. Pick the one that lets you swap plumbing without rewriting your house.

That's why we chose MAF.

---

Next: [The Executor Pattern](/blog/2026/06/02/adk-to-maf-executor-pattern.html)
