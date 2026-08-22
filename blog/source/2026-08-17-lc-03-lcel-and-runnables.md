# LCEL and Runnables

*The pipe operator that lets you write `prompt | model | parser` is not syntactic sugar — it's LangChain's core composition model, and everything you pipe together shares one standard interface that gives you streaming, batching, and async for free. Understanding Runnables and LCEL is understanding how LangChain applications are actually built.*

The last post ended with `prompt | model | parser`. That pipe is **LCEL (LangChain Expression Language)**, and the components it connects are **Runnables** — LangChain's unifying composition abstraction. This post explains what a Runnable is, how LCEL composes them, and the capabilities you get automatically from the shared interface. This is the concept that ties LangChain together: nearly everything is a Runnable, and Runnables compose.

## The Runnable: one interface for everything

The key abstraction is the **Runnable** — a standard interface that LangChain components implement. Models, prompts, output parsers, retrievers, and even whole chains are all Runnables, meaning they share a common set of methods:

- **`invoke`** — run it on a single input, get a single output.
- **`batch`** — run it on many inputs efficiently.
- **`stream`** — run it and stream the output progressively.
- Plus async versions of each (`ainvoke`, etc.).

This uniformity is the point. Because *every* component implements the same Runnable interface, they're interchangeable in composition and they all get the same capabilities. A prompt, a model, and a parser are different things, but as Runnables they present the same `invoke`/`batch`/`stream` surface — so you can pipe them together and treat the result the same way. The Runnable is to LangChain what a common interface is to any well-designed system: the thing that makes disparate parts compose. Once you see that "it's all Runnables," LangChain's structure clicks.

## LCEL: composing Runnables with a pipe

**LCEL (LangChain Expression Language)** is the declarative way to compose Runnables, using the `|` (pipe) operator to chain them so the output of one becomes the input of the next:

```python
# Illustrative shape — see the LangChain docs for exact API.
chain = prompt | model | output_parser

# because the chain is itself a Runnable, it has the full interface:
chain.invoke({"question": "..."})          # single
chain.batch([{"question": "..."}, ...])    # many
for chunk in chain.stream({"question": "..."}):   # streamed
    print(chunk, end="")
```

Read `prompt | model | output_parser` as "pipe the input through the prompt, then the model, then the parser." It's function composition for LLM components, expressed declaratively. The elegant consequence: **a composed chain is itself a Runnable**, so it has the same `invoke`/`batch`/`stream` interface as its parts, and can be composed further into bigger chains. Composition is closed — Runnables make Runnables — which is what lets you build complex applications from small piped pieces without special glue at each level.

## The capabilities you get for free

Here's why LCEL is more than nice syntax: because everything is a Runnable with the standard interface, composing with LCEL gives you significant capabilities *automatically*, without writing them:

- **Streaming** — an LCEL chain can stream its output end to end, so you get responsive, progressive output through the whole pipeline for free. You don't implement streaming; the Runnable interface provides it.
- **Batching** — run the chain over many inputs efficiently (with parallelism where possible) via `batch`, without writing batching logic.
- **Async** — every chain has async methods, so it fits async applications (like web servers) without extra work.
- **Parallelism** — LCEL can run independent components concurrently (a parallel Runnable that runs several branches at once and combines results), so you compose parallel steps declaratively.
- **Consistent configuration and inspection** — chains built with LCEL can be configured, inspected, and traced uniformly (feeding into LangSmith observability, a later post).

This is the real payoff of the Runnable/LCEL design: the cross-cutting concerns you'd otherwise implement per application — streaming, batching, async, parallelism — come from the shared interface. Compose your logic once with LCEL, and you get all of these behaviors automatically, everywhere. That's a substantial amount of engineering handed to you by the abstraction.

## Beyond linear pipes

LCEL isn't limited to straight-line pipes; it provides Runnables for the common shapes of composition:

- **Sequential** — the basic pipe (`a | b | c`), output flowing forward.
- **Parallel** — run multiple Runnables on the same input concurrently and collect their outputs into a structure (e.g. fetch context *and* pass through the question at once) — common in RAG, where you retrieve *and* forward the query in parallel.
- **Passthrough and assignment** — pass inputs along or add computed values into the data flowing through, so you can shape the data between steps without breaking the pipe.
- **Branching / routing** — choose which Runnable to run based on the input (route different inputs to different sub-chains).
- **Custom functions as Runnables** — wrap an ordinary function so your own logic composes into a chain like any other component.

These let LCEL express real application flows — retrieve-then-generate, parallel-fetch-then-combine, route-by-input — declaratively, while still being *chains* (LCEL's sweet spot). The important boundary: LCEL is for *composition of components into pipelines*, including modest branching and parallelism. When you need genuinely *stateful, cyclic, complex* orchestration (loops, evolving state, human-in-the-loop), that's LangGraph's job (its own series) — LCEL handles the chain-shaped compositions, LangGraph the graph-shaped ones. Knowing that line keeps you using the right tool.

## Why LCEL matters

Stepping back, LCEL and Runnables are what make LangChain a *composition framework* rather than a bag of components:

- **Uniformity** — everything is a Runnable, so everything composes and everything has the same interface. This is the conceptual backbone.
- **Declarative composition** — you describe the pipeline with pipes, and the framework runs it, rather than writing imperative call-and-pass-along code.
- **Free capabilities** — streaming, batching, async, parallelism from the shared interface, not from your effort.
- **Composability all the way up** — chains are Runnables, so you build big applications from small composed pieces, closed under composition.

If the last post's atoms (model, prompt, parser) are the *what*, LCEL and Runnables are the *how* — the mechanism that turns those atoms into applications. The rest of the series (retrieval, tools, memory) is largely about *more Runnables* to compose into your chains. The next post looks at chains and composition patterns in more depth.

## Key takeaways

- The Runnable is LangChain's unifying abstraction: models, prompts, parsers, retrievers, and whole chains all implement one standard interface (`invoke`/`batch`/`stream` plus async), which is what makes disparate components interchangeable and composable.
- LCEL composes Runnables with the `|` pipe operator (`prompt | model | parser`), function composition for LLM components — and a composed chain is itself a Runnable, so composition is closed (Runnables make Runnables) and chains nest into bigger chains.
- The big payoff is free capabilities: because everything shares the Runnable interface, LCEL chains get streaming, batching, async, and parallelism automatically, without you implementing them — a substantial amount of engineering from the abstraction.
- LCEL handles more than linear pipes — parallel, passthrough/assignment, branching/routing, and custom functions as Runnables — expressing real flows (retrieve-then-generate, parallel-fetch-combine) declaratively, while staying chain-shaped.
- The boundary: LCEL is for composing components into pipelines (including modest branching/parallelism); genuinely stateful, cyclic, complex orchestration is LangGraph's job — LCEL/Runnables are the how that turns LangChain's atoms into applications.

## Further reading

- [Models, prompts, and output parsers (previous post)](/blog/posts/lc-02-models-prompts-parsers.html)
- [LangChain documentation — LCEL and Runnables](https://python.langchain.com/)
- [LangGraph, Concept by Concept — for stateful graph orchestration](/blog/series/langgraph-concept-by-concept/)
