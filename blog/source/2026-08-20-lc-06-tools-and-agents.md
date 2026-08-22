# Tools and Agents

*Chains follow a path you define; agents decide the path themselves. LangChain gives you both the tools an agent uses and — increasingly through LangGraph — the machinery to run agent loops reliably. Understanding where LangChain's tools end and LangGraph's orchestration begins is the key to building agents that work rather than agents that wander.*

The chains so far follow a fixed structure you compose. **Agents** break that: an agent uses an LLM to *decide* what to do — which tool to call, whether to call another, when it's done — following a dynamic path rather than a predetermined one. This post covers LangChain **tools** (the capabilities agents use) and how agents are built, including the important shift toward **LangGraph** for reliable agent orchestration. It's where LangChain meets the agent pattern the broader blog explores.

## Tools: giving the LLM capabilities

A **tool** is a function the LLM can call to act beyond generating text — search, query a database, call an API, compute. LangChain provides a standard tool abstraction and, like other components, a large catalog of pre-built tool integrations plus easy ways to define your own:

- **Define a tool from a function** — wrap a Python function (with a description and typed arguments) as a tool, and LangChain generates the schema the model needs to call it — the same "typed function becomes a tool" idea as the Pydantic AI tools post, with the description guiding when the model uses it.
- **Pre-built tool integrations** — LangChain's ecosystem includes ready-made tools (search, various APIs, utilities), so you often assemble an agent's capabilities from existing tools.
- **Standard tool interface** — tools are components with a consistent interface, so they plug into agents (and, being composable, into chains) uniformly.

The tool-design lessons from across the blog apply: a tool's *description* is what the model reasons over to decide when to call it, so clear descriptions and well-typed arguments matter; and give an agent *few, well-chosen* tools rather than many overlapping ones, so tool selection stays reliable. Tools are the agent's hands — its ability to affect and observe the world — and their quality bounds what the agent can reliably do.

## Tool calling: the foundation

Underneath agents is **tool calling** (function calling) — the model's ability to output a request to call a specific tool with specific arguments, which the framework then executes, feeding the result back. Modern LLMs support this natively, and LangChain exposes it through the standard model interface (the models post): you *bind* tools to a model, and the model can then choose to call them.

Tool calling is the primitive; an **agent** is the *loop* built on it:

```text
1. Model, given the query and available tools, decides: answer, or call a tool?
2. If a tool call → framework runs the tool → result goes back to the model
3. Model observes the result, decides again (another tool? done?)
4. Repeat until the model produces a final answer
```

This think-act-observe loop (the ReAct pattern from the Agentic RAG and agent series) is what makes an agent — the model drives its own path through the tools. LangChain provides tool calling as the foundation; the question is *how you run the loop reliably*, which is where the modern LangChain story shifts to LangGraph.

## Agents: the shift to LangGraph

Historically, LangChain had its own agent executors to run the agent loop. The modern LangChain approach is that **complex, reliable agents are built with LangGraph** (its own series) — LangChain provides the components (models, tools, the tool-calling interface), and LangGraph provides the *orchestration* to run agent loops with control and state. This reflects the LangChain-vs-LangGraph relationship from the first post:

- **LangChain** — the components an agent uses: the model (with tool calling bound), the tools, retrievers, prompts. The raw materials.
- **LangGraph** — the stateful, graph-based engine to *orchestrate* the agent loop: managing state across steps, handling the cyclic think-act-observe flow, adding control (bounded iterations, branching), persistence (checkpointing), and human-in-the-loop. The reliable agent runtime.

The reason for this division is exactly the chains-vs-graphs boundary: an agent loop is *cyclic and stateful* (it revisits the model repeatedly, carrying state), which is graph-shaped, not chain-shaped. LCEL chains handle pipelines; agent loops need LangGraph's stateful orchestration to be *reliable* — bounded, inspectable, controllable — rather than an opaque loop that might wander or spin. So the practical modern pattern is: **use LangChain's tools and models, and orchestrate agents with LangGraph.** If you're building anything beyond a trivial agent, that's the path, and it's why the two libraries are complementary rather than redundant.

## Keeping agents reliable

Whichever orchestration you use, the agent-reliability disciplines from across the blog apply — agents are powerful and prone to misbehaving, so the guardrails matter:

- **Few, well-described tools** — so the model chooses correctly; too many overlapping tools degrade selection.
- **Bound the loop** — a max-iterations limit so a confused agent fails fast instead of spinning (and burning tokens) — LangGraph makes this controllable.
- **Handle tool errors** — feed failures back so the agent can recover, and degrade gracefully when it can't.
- **Observe the loop** — trace which tools the agent called, in what order, with what results (LangSmith, the next post), because you can't debug or trust a reasoning loop you can't see.
- **Prefer structure where you can** — if a task can be a chain (fixed flow) rather than an open agent loop, the chain is more predictable; reserve open-ended agents for genuinely dynamic tasks. This is the recurring "structure where you need predictability, autonomy where you need flexibility" lesson.

The theme: agents trade predictability for flexibility, so add the guardrails (few tools, bounded loops, error handling, observability) that keep the flexibility from becoming unreliability — and use LangGraph's orchestration precisely because it makes those guardrails concrete.

## Tools and agents in the LangChain world

The mental model to carry: LangChain gives you **tools** (typed functions and a rich integration catalog) and **tool calling** (through the standard model interface), which are the raw materials of agents; and the **orchestration** of reliable agent loops is LangGraph's domain. So "building an agent with LangChain" today means composing LangChain's tools and models and running them with LangGraph's stateful engine. This keeps the pieces in their right places — LangChain for standardized components, LangGraph for stateful orchestration — and is the accurate picture of how agents are built in this ecosystem now. The final post covers observing and operating all of this in production with LangSmith.

## Key takeaways

- Chains follow a fixed path; agents use the LLM to decide the path (which tool to call, when to stop) — a dynamic think-act-observe loop built on tool calling.
- A tool is a function the LLM can call to act; LangChain provides a standard tool abstraction, a large catalog of pre-built tools, and easy function-to-tool definition (description guides when the model calls it) — apply the disciplines of clear descriptions and few, well-chosen tools.
- Tool calling (the model outputting a tool-call request that the framework executes and feeds back) is the primitive, exposed through the standard model interface by binding tools to a model; an agent is the loop built on that primitive.
- The modern approach builds reliable agents with LangGraph: LangChain provides the components (models with tool calling, tools), LangGraph provides the stateful, graph-based orchestration of the cyclic agent loop (state, bounded iterations, checkpointing, human-in-the-loop) — because agent loops are graph-shaped, not chain-shaped.
- Keep agents reliable with few well-described tools, bounded loops, tool-error handling, and observability, and prefer chains (fixed flow) where a task doesn't need open-ended autonomy — structure where you need predictability, autonomy where you need flexibility.

## Further reading

- [Retrieval and RAG (previous post)](/blog/posts/lc-05-retrieval-and-rag.html)
- [LangGraph, Concept by Concept — the agent orchestration engine](/blog/series/langgraph-concept-by-concept/)
- [Pydantic AI: tools and function calling — the typed-function-as-tool idea](/blog/posts/pydai-04-tools-and-function-calling.html)
