# Agents and Tools

*The moment you expose a query engine as a tool, RAG stops being a fixed pipeline and becomes a decision: the agent decides whether to retrieve, from which source, and whether one search was enough. That is agentic RAG, and it's built into LlamaIndex.*

So far the pipeline has been fixed: every question flows through retrieve-then-synthesize. An **agent** breaks that rigidity. An agent is an LLM that, given the conversation and the latest message, *decides which action to take* — often, which **tool** to call. And LlamaIndex's key move is that a query engine can *be* a tool. This sixth post in the LlamaIndex series covers agents, tools, and the agentic-RAG pattern they enable.

## What an agent adds: decisions

A fixed RAG pipeline always retrieves, always from the same index, always once. That's wasteful for "hi there" and inadequate for "compare our Q1 and Q2 refund rates and explain the change," which needs multiple retrievals and some reasoning. An **agent** replaces the fixed flow with a reasoning loop: look at the request, decide what to do (answer directly, call a tool, call another tool), observe the result, and repeat until done. The agent supplies the *judgment* a static pipeline lacks — a loop of think → act → observe (the ReAct pattern from the [Agentic RAG](/blog/series/agentic-rag/) series).

## Tools: what an agent can do

A **tool** is a capability the agent can invoke — a Python function, an API call, or a query engine — described well enough (name, purpose, parameters) that the LLM knows when to use it. In LlamaIndex you wrap a function as a `FunctionTool`, and the agent chooses among the tools you give it:

```python
from llama_index.core.tools import FunctionTool

def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

multiply_tool = FunctionTool.from_defaults(fn=multiply)
```

The quality of a tool's **description** is what determines whether the agent uses it correctly — a vague description leads to misuse or neglect. Tool design is prompt design: name and describe tools for the model that has to choose among them.

## The key idea: a query engine as a tool

Here's where LlamaIndex's data foundation and agents combine. A query engine — your entire RAG pipeline over a corpus — can be wrapped as a `QueryEngineTool` and handed to an agent:

```python
from llama_index.core.tools import QueryEngineTool

policy_tool = QueryEngineTool.from_defaults(
    query_engine=policy_index.as_query_engine(),
    name="refund_policy",
    description="Answers questions about the company refund and returns policy.",
)
```

Now the agent *decides* when to retrieve. This is **agentic RAG**, and it unlocks the patterns a fixed pipeline can't:

- **Skip retrieval when it's not needed** — chit-chat and simple arithmetic don't hit the index, saving cost and latency.
- **Route across multiple sources** — give the agent one query-engine tool per corpus (policies, engineering docs, HR) plus its descriptions, and it picks the right one for each question.
- **Multi-step retrieval** — decompose a complex question, retrieve for each part, and combine — several tool calls in one turn.
- **Mix retrieval with other tools** — retrieve a policy *and* call a calculator or an API in the same reasoning loop.

Retrieval becomes one capability among many that the agent orchestrates, rather than the whole program.

## Keeping agents reliable

Agentic flexibility has a cost: an agent can loop, call the wrong tool, or wander. The disciplines from the broader agent series apply directly. Give the agent *few, well-described* tools rather than many overlapping ones — choice overload degrades tool selection. Bound the reasoning loop with a max-iterations limit so a confused agent fails fast instead of spinning. Handle tool errors gracefully and feed them back so the agent can recover. And observe what the agent actually did — which tools it called, in what order — because you can't debug or trust a reasoning loop you can't see (the next posts on workflows and production go deeper here). Agentic RAG is more capable than a fixed pipeline, but capability without guardrails is unreliability; the guardrails are what make it production-worthy.

## Key takeaways

- An agent is an LLM that decides which action/tool to take in a think→act→observe loop, supplying the judgment a fixed retrieve-then-synthesize pipeline lacks.
- A tool is a capability (function, API, or query engine) the agent can invoke; the quality of its description determines whether the agent uses it correctly — tool design is prompt design.
- LlamaIndex's key move: wrap a query engine as a `QueryEngineTool` so the agent *decides* when to retrieve — this is agentic RAG.
- Agentic RAG enables skipping retrieval when unneeded, routing across multiple corpora, multi-step retrieval for complex questions, and mixing retrieval with other tools.
- Keep agents reliable with few well-described tools, a bounded reasoning loop, graceful tool-error handling, and observability — flexibility without guardrails is unreliability.

## Further reading

- [LlamaIndex documentation](https://docs.llamaindex.ai)
- [Agentic RAG series](/blog/series/agentic-rag/)
- [LlamaIndex, Concept by Concept — start of the series](/blog/posts/llamaindex-01-what-is-llamaindex.html)
