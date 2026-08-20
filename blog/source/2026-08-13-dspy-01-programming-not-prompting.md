# DSPy: Programming, Not Prompting

*Hand-tuned prompt strings are brittle, model-specific, and impossible to systematically improve — DSPy replaces them with declarative modules and an optimizer that writes the prompts for you.*

Most LLM code is held together by prompt strings: long templates discovered by trial and error, fragile to the smallest wording change, and quietly broken the moment you swap models. DSPy, the framework from the Stanford NLP group, is a bet that this is the wrong abstraction. Its thesis is simple and radical: **you should program language models, not prompt them** — declare *what* each step does, and let an optimizer figure out *how* to prompt for it. This series builds DSPy up concept by concept; this first post covers the problem it solves, its core idea, and the five primitives everything else is made of.

## The problem with prompt strings

Consider a typical LLM feature. Someone writes a prompt: a few paragraphs of instructions, a couple of hand-picked examples, some formatting rules. It works, mostly. Then the requirements shift, or a better model ships, or the examples turn out to be unrepresentative — and the prompt has to be re-tuned by hand, with no principled way to know whether a change helped. Chain three such steps into a pipeline and you have three brittle strings whose interactions no one fully understands. This is the state of most production LLM code, and it does not scale: every improvement is manual, every model change is a rewrite, and quality is a matter of intuition rather than measurement.

The deeper issue is that the prompt conflates *what* you want with *how* to ask for it. "Classify this ticket's urgency" is the what; the specific wording, the examples, the phrasing that happens to work for this model is the how. Baking the how into a hand-written string freezes it, couples it to one model, and makes it un-optimizable.

## The DSPy idea: separate what from how

DSPy separates the two. You write your program as **modules** that declare the transformation each step performs — its inputs and outputs — in a **signature**. You do *not* write the prompt. Instead, you define a **metric** that scores whether the program did well, provide some examples, and run an **optimizer** that searches for the prompts (instructions and few-shot demonstrations) that maximize the metric.

The mental model to carry: DSPy is to prompting what a compiler is to assembly. You write the high-level intent; the optimizer "compiles" it down to the actual prompts, tuned to your task, your metric, and your model. Change the model, and you recompile rather than rewrite. Change the task, and you update the metric and recompile. The prompt stops being a hand-crafted artifact and becomes a *learned parameter* of your program.

## The five primitives

Everything in DSPy is built from five concepts, each of which gets its own post in this series:

- **Signature** — a declarative spec of a transformation's inputs and outputs, like `"question -> answer"`. It says what goes in and what comes out, not how to prompt for it.
- **Module** — a strategy for actually calling the model to satisfy a signature. `dspy.Predict` is the plain one; `dspy.ChainOfThought` adds reasoning; `dspy.ReAct` adds tool use. Modules are *parameterized* — their prompts are what the optimizer tunes.
- **Program** — modules composed into a pipeline (a `dspy.Module` subclass with a `forward` method), for anything multi-step like RAG or an agent.
- **Metric** — a function that scores a prediction against what you wanted. This is the objective the optimizer maximizes, so it defines "good."
- **Optimizer** — the algorithm that compiles your program: it searches over instructions and few-shot examples to improve the metric. (Older DSPy called these "teleprompters.")

You write signatures, modules, programs, and a metric. The optimizer writes the prompts. That division of labor is the whole framework.

## A first taste

The smallest DSPy program shows the shape. You configure a language model, declare a signature inline, and call a module:

```python
import dspy

dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

classify = dspy.Predict("ticket -> urgency")
result = classify(ticket="The whole site is down and customers can't check out.")
print(result.urgency)
```

Notice what is *absent*: there is no prompt. The signature `"ticket -> urgency"` declares the transformation; DSPy constructs a reasonable prompt from it. This already works untuned — and when you later attach a metric and an optimizer, DSPy will improve that prompt against your data without you editing a string.

## When DSPy fits — and when it doesn't

DSPy earns its keep when you have a task you can *measure* and want to improve systematically: a pipeline you will run at scale, tune over time, and possibly move across models. Its optimizers turn "tweak the prompt and hope" into "define the metric and compile," which is a large win for anything where quality matters and you have (or can build) an evaluation set.

It is less compelling for a one-off, throwaway prompt, or a task with no measurable notion of success, where the ceremony of signatures, metrics, and optimizers outweighs the benefit of a single well-worded string. And it asks for a mindset shift — you stop crafting prompts and start defining programs and metrics — which is exactly the shift this series is about. DSPy also does not remove the need to *think*: you still design the pipeline, choose the modules, and — most importantly — write a metric that genuinely captures quality, because the optimizer will maximize exactly what you measure.

## Where the series goes

From here we go primitive by primitive: signatures (declaring what), modules (strategies for how), composing programs, metrics and evaluation (defining and measuring good), and optimizers (letting DSPy write the prompts). Then we build a real RAG pipeline and an agent in DSPy, and finish with running DSPy in production. By the end you will be able to replace brittle prompt strings with programs that improve themselves against a metric.

## Key takeaways

- Prompt strings conflate *what* you want with *how* to ask, making them brittle, model-specific, and impossible to improve systematically.
- DSPy separates the two: you declare programs and a metric; an optimizer compiles the actual prompts (instructions + few-shot demos) to maximize that metric — like a compiler for prompting.
- The five primitives are Signature (what), Module (how — Predict/ChainOfThought/ReAct), Program (composed modules), Metric (the objective), and Optimizer (the compile algorithm).
- You write signatures, modules, programs, and metrics; the optimizer writes the prompts — and swapping models means recompiling, not rewriting.
- DSPy fits measurable, scaled, evolving pipelines; it's overkill for one-off prompts, and it still requires you to design the pipeline and write a metric that truly captures quality.

## Further reading

- [DSPy — official documentation](https://dspy.ai)
- [stanfordnlp/dspy on GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
