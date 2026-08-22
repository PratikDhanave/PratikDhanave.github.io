# Chains and Composition

*A "chain" is just Runnables composed with LCEL — but the word names the central idea of LangChain: build applications by wiring small, standard components into pipelines rather than writing monolithic prompt-and-parse code. Thinking in chains is thinking in composable steps, which is what makes LangChain applications modular, testable, and maintainable.*

The last post covered LCEL and Runnables — the mechanism. This post covers what you build with them: **chains**. A chain is a composition of components into an application pipeline, and "chaining" is the concept LangChain is named for. This post looks at composition patterns — sequential steps, parallel branches, routing, passing data through — and the design mindset of building LLM applications as composed steps. It's about turning the mechanism into real application structure.

## What a chain is

A **chain** is simply a sequence (or graph) of components composed together so data flows through them — built with LCEL from Runnables (the last post). The simplest chain is `prompt | model | parser`; a real application chain adds more steps: retrieve context, format it into a prompt, call the model, parse the output, maybe post-process. The essence is the same: **an application built as a pipeline of composable steps** rather than one big function that does everything.

This chaining mindset is LangChain's core contribution to *how you structure* LLM code. Instead of a monolithic block that builds a prompt, calls the model, and parses the result all tangled together, you compose named, standard components — each doing one thing — into a pipeline. The benefits are the usual benefits of good decomposition, applied to LLM apps:

- **Modularity** — each step is a focused, swappable component.
- **Reusability** — components and sub-chains are reused across applications.
- **Testability** — steps can be tested and reasoned about individually.
- **Readability** — the pipeline expresses the application's flow declaratively.

Thinking in chains is thinking in composable steps, and that's the shift that makes LangChain applications maintainable rather than a pile of prompt-wrangling code.

## The RAG chain: the canonical example

The most illustrative chain is retrieval-augmented generation (the [Agentic RAG](/blog/series/agentic-rag/) series covers RAG deeply; here it's the exemplar chain). A RAG chain composes retrieval and generation:

```text
question
   │
   ├─(parallel)→ retriever → relevant documents ┐
   │                                            ├→ prompt (context + question) → model → parser → answer
   └──────────── pass through the question ─────┘
```

```python
# Illustrative shape — see the LangChain docs for exact API.
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}   # parallel: retrieve AND forward
    | prompt                                                    # format context + question
    | model
    | output_parser
)
answer = rag_chain.invoke("What is our refund policy?")
```

This one example shows several composition patterns at once:

- **Parallel step** — retrieve the context *and* pass the question through simultaneously (the parallel Runnable from the LCEL post), collecting both into a structure.
- **Sequential flow** — that structure flows into the prompt, then the model, then the parser.
- **Data shaping** — passthrough forwards the question unchanged while the retriever transforms it into documents.

The RAG chain is the canonical LangChain composition because it exercises the real patterns — parallel, sequential, passthrough — in a genuinely useful application, and it shows how a substantial capability (retrieval-grounded answering) is *composed* from standard components rather than hand-built. Most LangChain applications are variations and extensions of this shape.

## Composition patterns

Beyond the linear pipe, a few patterns recur in building real chains (all from the Runnables/LCEL toolkit):

- **Sequential composition** — steps in order, output to input. The backbone of most chains.
- **Parallel composition** — run independent steps concurrently and combine results (retrieve context while forwarding the query; call multiple models or tools at once). Improves latency and enables fan-out.
- **Routing / branching** — choose the next step based on the input: route a classification question to one sub-chain and a generation question to another. This is how a single chain handles heterogeneous inputs.
- **Passthrough and assignment** — carry data forward unchanged, or add computed fields into the flowing data, so later steps have what they need without breaking the pipe.
- **Sub-chains as components** — because a chain is a Runnable, you compose chains *into* larger chains — building complex applications from tested sub-chains, closed under composition (the LCEL post's key property).

These patterns are the vocabulary of chain-building. Real applications combine them: a chain that routes by input type, retrieves in parallel where relevant, runs sub-chains, and shapes data between steps — all declaratively composed. The skill is decomposing your application into these composable steps.

## When chains are the right shape (and when they aren't)

Chains (LCEL composition) are LangChain's sweet spot, but they have a boundary worth respecting, reiterating the LangChain-vs-LangGraph line:

- **Chains fit** applications that are fundamentally *pipelines* — even with parallelism and modest branching — where data flows forward through steps: RAG, extraction, classification, multi-step transformations, most "call the model with the right context and parse the result" applications. If your app is a directed flow of steps, chains are ideal.
- **Chains strain** when you need *stateful, cyclic* orchestration: loops where the flow revisits steps, evolving state carried across many turns, complex agent decision loops, human-in-the-loop pauses. Expressing genuine cycles and rich state in linear-ish chains gets awkward.
- **That's where LangGraph takes over** (its own series) — graph-based, stateful orchestration for exactly those cyclic, stateful, complex flows. The modern LangChain guidance is: chains/LCEL for pipeline-shaped work, LangGraph for graph-shaped work.

So chains are the right tool for the large class of pipeline-shaped LLM applications, and recognizing when your application has outgrown that shape — into genuine statefulness and cycles — is when you graduate to LangGraph. Using chains for what they're good at, and not forcing cyclic orchestration into them, is the practical wisdom.

## The composition mindset

The deeper takeaway of this post is a *way of thinking*: build LLM applications as **compositions of small, standard, testable components** rather than monolithic code. Chains make this concrete — you decompose the application into steps (retrieve, format, generate, parse, route), implement or reuse each as a Runnable, and compose them with LCEL. This is ordinary good software design (decomposition, reuse, testability) applied to LLM applications, and it's LangChain's most durable contribution regardless of the specific API. The next posts add more components to compose — retrieval, tools, memory — but the mindset stays: everything is a component, and you build by composing them into chains.

## Key takeaways

- A chain is a composition of components (Runnables via LCEL) into an application pipeline — the concept LangChain is named for — and "thinking in chains" means building apps as pipelines of small composable steps rather than monolithic prompt-and-parse code.
- Chaining brings the benefits of good decomposition to LLM apps: modularity (focused swappable steps), reusability, testability (steps reasoned about individually), and readability (the pipeline expresses the flow).
- The RAG chain is the canonical example, exercising the real patterns at once — parallel (retrieve context while forwarding the question), sequential (into prompt→model→parser), and passthrough — showing a capability composed from standard components.
- The composition vocabulary is sequential, parallel, routing/branching, passthrough/assignment, and sub-chains-as-components (closed under composition) — real apps combine them declaratively, and the skill is decomposing your app into these steps.
- Chains fit pipeline-shaped applications (RAG, extraction, transformations, modest branching); they strain on stateful/cyclic orchestration, which is LangGraph's job — use chains for what they're good at, and the composition mindset is LangChain's most durable contribution.

## Further reading

- [LCEL and Runnables (previous post)](/blog/posts/lc-03-lcel-and-runnables.html)
- [Agentic RAG series — the RAG the canonical chain implements](/blog/series/agentic-rag/)
- [LangGraph, Concept by Concept — for stateful, cyclic orchestration](/blog/series/langgraph-concept-by-concept/)
