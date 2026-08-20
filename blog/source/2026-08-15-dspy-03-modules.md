# Modules: Strategies for Calling a Model

*If a signature says what a step does, a module says how to get the model to do it — and because modules are parameterized, swapping one for another changes the reasoning strategy without touching your intent.*

A signature declares a transformation; a **module** actually performs it by prompting the model in a particular way. Modules are DSPy's second primitive, and they are where you choose a *strategy* — a plain prediction, a chain of reasoning, a tool-using loop — independently of what the step is for. This third post in the DSPy series covers the core modules, why they are interchangeable, and what "parameterized" really means.

## A module wraps a signature with a strategy

Every module takes a signature and knows how to call the model to satisfy it. The simplest is `dspy.Predict`, which asks the model directly:

```python
import dspy
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

qa = dspy.Predict("question -> answer")
qa(question="What is the capital of France?").answer   # "Paris"
```

`Predict` builds a prompt from the signature, calls the model, and parses the output fields. That is the baseline. The interesting part is that other modules take the *same signature* and apply a different strategy to it.

## Chain of Thought

`dspy.ChainOfThought` is `Predict` plus reasoning. It takes the identical signature but instructs the model to reason step by step before producing the output fields, and it exposes that reasoning:

```python
qa = dspy.ChainOfThought("question -> answer")
result = qa(question="If a train travels 60 km in 45 minutes, what is its speed in km/h?")
print(result.reasoning)   # the step-by-step working
print(result.answer)      # "80 km/h"
```

Notice you changed one thing — `Predict` to `ChainOfThought` — and the step now reasons, with no change to the signature or the calling code. That interchangeability is the design: the *what* (signature) stays fixed while you experiment with the *how* (module). For tasks involving math, logic, or multi-step inference, chain-of-thought usually improves accuracy; for simple lookups it adds tokens for little gain, and choosing between them is exactly the kind of decision you can make empirically with the metric from a later post.

## ReAct: modules that use tools

`dspy.ReAct` implements the reason-and-act loop: given a signature and a set of tools, the model reasons about what it needs, calls a tool, observes the result, and iterates until it can produce the output. You hand it Python functions as tools:

```python
def search(query: str) -> str:
    """Search the knowledge base and return matching passages."""
    ...

agent = dspy.ReAct("question -> answer", tools=[search])
agent(question="What did our Q3 revenue guidance say?").answer
```

The same signature `question -> answer` is now satisfied by an agent that can call `search` as many times as it needs. This is how DSPy expresses agents — as a module — and it composes with everything else in the framework, including optimization. We build a fuller agent in a later post; the point here is that "agentic" is just another module strategy over the same declarative signature.

## Other strategies

DSPy ships additional module strategies for particular shapes of problem — for example a program-of-thought style that has the model produce and execute code for computational tasks. The catalog grows, but the principle is constant: each module is a reusable strategy for turning a signature into a model call, and you pick the one whose approach fits the task. You can also write your own module by composing existing ones, which is exactly what a *program* is (the next post).

## What "parameterized" means

The most important property of a module is subtle: modules are **parameterized**, and their parameters are the prompt itself — the instruction wording and the few-shot demonstrations. When you first use a module, those parameters are at sensible defaults (a prompt derived from the signature, no demonstrations). When you *optimize* (a later post), the optimizer adjusts these parameters — rewriting the instruction, selecting demonstrations — to maximize your metric.

This is why the compiler analogy holds. A module is like a function whose behavior can be tuned by learned parameters, except the parameters are not weights, they are the prompt. An un-optimized module works; an optimized one works better, on your task, with your model — and the code you wrote did not change, only the compiled prompt behind it did. Holding this in mind reframes everything: you are not writing prompts, you are declaring parameterized modules that DSPy will later fill in.

## Choosing and combining modules

In practice you start simple and let evidence guide escalation. Use `Predict` for straightforward transformations; reach for `ChainOfThought` when reasoning helps and you can measure that it does; use `ReAct` when the task genuinely needs tools and iteration. Because modules are interchangeable over a signature and cheap to swap, "which strategy" becomes an empirical question you answer with the metric, not a guess you bake into a prompt. And because modules compose, a real system is many modules wired together — each a small, tunable strategy — rather than one monolithic call. That composition is the subject of the next post.

## Key takeaways

- A module performs a signature by prompting the model with a particular strategy; `dspy.Predict` is the direct baseline.
- `dspy.ChainOfThought` takes the same signature but adds step-by-step reasoning (and exposes it); swapping it in changes the strategy without touching intent or calling code.
- `dspy.ReAct` implements the reason-act tool loop over a signature — this is how DSPy expresses agents, and it composes with optimization like any other module.
- Modules are *parameterized*: their parameters are the prompt (instruction wording + few-shot demonstrations), which the optimizer later tunes — a module is a function whose "weights" are its prompt.
- Start with `Predict`, escalate to `ChainOfThought`/`ReAct` based on measured need, and compose modules into programs — "which strategy" is an empirical question the metric answers.

## Further reading

- [DSPy — official documentation](https://dspy.ai)
- [DSPy modules — docs](https://dspy.ai)
- [DSPy paper — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
