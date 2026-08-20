# Signatures: Declaring What, Not How

*A DSPy signature is the contract that says what goes in and what comes out of a step — and by declaring the transformation instead of writing the prompt, it becomes something the optimizer can improve.*

The first primitive of DSPy is the **signature**, and it is where the framework's whole philosophy is concentrated. A signature declares the *what* of a transformation — its inputs, its outputs, and their meaning — without specifying the *how* of the prompt. This second post in the DSPy series covers signatures in both their forms, why typed fields matter, and how the signature becomes the thing DSPy compiles.

## What a signature is

A signature is a specification of a language-model transformation: what fields it takes and what fields it produces. It is deliberately *not* a prompt. Where a prompt says "You are an expert assistant. Read the following question carefully and provide a concise, accurate answer...", a signature says `question -> answer`. The signature captures the intent; DSPy is responsible for turning it into an actual prompt, and the optimizer is responsible for making that prompt good.

That separation is the point. Because the signature declares intent rather than wording, the wording is free to be generated, tuned, and re-tuned. You commit to *what* the step does and leave *how to ask* to the framework.

## Inline signatures

The quickest form is a string. An inline signature names input and output fields separated by `->`:

```python
import dspy
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

summarize = dspy.Predict("document -> summary")
classify  = dspy.Predict("ticket -> urgency")
translate = dspy.Predict("english_text -> french_text")
```

Multiple fields on either side are comma-separated, and the field names are meaningful — DSPy uses them to construct the prompt, so `question, context -> answer` reads and prompts better than `input1, input2 -> output`:

```python
answer = dspy.Predict("context, question -> answer")
```

Inline signatures are perfect for quick work and prototyping. The field names carry the semantics, so choose them to describe the data honestly.

## Class-based signatures

When you need more control — descriptions, types, or a task-level instruction — use a class-based signature. It is a `dspy.Signature` subclass whose docstring is the task description and whose fields are declared with `InputField` and `OutputField`:

```python
class ClassifyUrgency(dspy.Signature):
    """Classify a support ticket's urgency for triage."""

    ticket: str = dspy.InputField(desc="the customer's message")
    urgency: str = dspy.OutputField(desc="one of: low, medium, high, critical")

classify = dspy.Predict(ClassifyUrgency)
```

Several things are happening here, all of which help the model and the optimizer:

- **The docstring** is the task-level instruction — a concise statement of what the step is for. Crucially, this instruction is one of the things the optimizer can *rewrite* to improve the metric; you provide a sensible starting point, not the final wording.
- **Field descriptions** (`desc`) give the model per-field guidance — what the input contains, what shape the output should take. `"one of: low, medium, high, critical"` steers the output far better than a bare field name.
- **Types** annotate what each field is. A `str` is the default, but signatures support richer types.

Class-based signatures are what you reach for in real systems, because the descriptions and constraints materially improve results and give the optimizer more to work with.

## Typed fields and structure

Signatures are not limited to strings. Output fields can be typed — booleans, numbers, lists, or structured types — and DSPy uses the type to enforce and parse the output. Declaring `is_spam: bool` or `scores: list[float]` tells DSPy to produce and validate that shape, which is far more reliable than asking for JSON in a prompt and hoping. This connects DSPy to the constrained-output discipline: the signature's types are a validation boundary, not a suggestion. When your downstream code needs structured data, encode that in the signature's output types and let DSPy handle the extraction.

## The signature is what gets compiled

Here is why the signature matters beyond convenience. When you later attach an optimizer, what it tunes is anchored to the signature: it proposes better *instructions* (rewrites of that docstring) and selects few-shot *demonstrations* that fit the signature's fields. The signature is the stable contract — inputs, outputs, intent — around which the optimizer searches for the best prompt. A vague signature gives the optimizer little to anchor on; a precise one, with honest field names and clear descriptions, gives it a strong starting point and a clear target. Writing good signatures is therefore not busywork — it is the highest-leverage authoring you do in DSPy, because everything downstream compiles against them.

## Signatures compose

Because each signature is a self-contained contract, signatures compose cleanly into pipelines. A RAG program might use `question -> search_query` to rewrite the query, then `context, question -> answer` to generate — two signatures, each declaring one transformation, wired together in a program (the subject of a later post). Each can be understood, tested, and optimized on its own terms. This composability is what lets DSPy scale from a single call to a multi-step system without the pipeline collapsing into one giant unmaintainable prompt.

## Key takeaways

- A signature declares a transformation's inputs and outputs (the *what*), never the prompt (the *how*) — which is exactly what lets the prompt be generated and optimized.
- Inline signatures (`"context, question -> answer"`) are quick; field names are meaningful, so name them to describe the data honestly.
- Class-based signatures add a docstring task-instruction (which the optimizer can rewrite), per-field `desc` guidance, and types — reach for them in real systems.
- Typed output fields (bool, numbers, lists, structured types) make DSPy enforce and parse structure, a reliable validation boundary rather than "ask for JSON and hope."
- The signature is the stable contract the optimizer compiles against; precise signatures with honest names and clear descriptions are the highest-leverage authoring in DSPy, and they compose cleanly into pipelines.

## Further reading

- [DSPy — official documentation](https://dspy.ai)
- [stanfordnlp/dspy on GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy paper — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
