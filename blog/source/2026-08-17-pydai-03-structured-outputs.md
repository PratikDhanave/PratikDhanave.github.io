# Structured Outputs

*This is the feature Pydantic AI is named for and built around: you declare a Pydantic model as your agent's output type, and you get back a validated instance of it — not a string to parse, not JSON to hope about, but a real typed object. It turns the single most brittle part of LLM applications into the most reliable.*

The Agent post noted that a Pydantic AI agent is parameterized by an output type. This post is about that output type — **structured outputs**, the framework's flagship capability. If you take one thing from this series, it's this: Pydantic AI makes "get validated, typed data out of an LLM" a solved, first-class operation. This post covers how it works, why it's more than convenience, and what it means for building reliable applications.

## The problem: LLMs return text, apps need data

An LLM produces text. But your application almost never wants text — it wants *data*: an `Order` with items and a total, a `Classification` with a label and confidence, a list of extracted `Contact` records. The traditional path from text to data is painful and fragile:

1. Prompt the model to return JSON in a specific shape.
2. Parse the returned string as JSON (which may be malformed, wrapped in prose, or subtly wrong).
3. Validate the parsed data has the right fields and types (which it may not).
4. Handle all the ways steps 2 and 3 fail.

This "prompt-parse-validate-handle" dance is everywhere in LLM code, and it's brittle: the model returns *almost*-valid JSON, or the right shape with a wrong type, or extra commentary around it, and your parsing breaks — often silently, propagating bad data downstream. Structured outputs replace this entire dance with a declaration.

## The solution: declare the type

With Pydantic AI, you define the output you want as a **Pydantic model** and tell the agent that's its output type. The framework then ensures the model's output conforms to it, validated, and hands you back a typed instance:

```python
# Illustrative shape — see the Pydantic AI docs for exact API.
from pydantic import BaseModel
from pydantic_ai import Agent

class Order(BaseModel):
    item: str
    quantity: int
    total: float

agent = Agent("openai:gpt-...", output_type=Order)

result = agent.run_sync("Two coffees at $3.50 each")
order = result.output          # this is a validated Order instance
print(order.quantity, order.total)   # typed fields, IDE autocomplete, no parsing
```

`result.output` is an `Order` — a real, validated Python object with typed fields — not a string you parsed. The prompt-parse-validate-handle dance is gone, replaced by "declare the model, get the model." This is the core value: **the most brittle part of LLM applications becomes a type declaration.**

## How it works: schema plus validation plus retry

Understanding the mechanism explains why it's reliable, not magic. Pydantic AI does three things:

- **Generates a schema from your model.** From your Pydantic model's types, it derives a JSON schema describing the required structure, and uses the model provider's structured-output/function-calling capability to tell the LLM exactly what shape to produce. The model isn't just asked nicely for JSON; it's constrained toward the declared schema.
- **Validates the output with Pydantic.** The model's output is validated against your Pydantic model — the same battle-tested validation that guards data across the Python ecosystem. If it doesn't conform (wrong type, missing field), validation catches it.
- **Retries on validation failure.** If the output fails validation, Pydantic AI can feed the validation error back to the model and ask it to correct — automatically getting the model to fix its own malformed output. This self-correction loop is why structured outputs are reliable in practice: transient malformed outputs get repaired rather than crashing your app.

This schema → validate → retry pipeline is the machinery that turns "the model usually returns the right shape" into "I get a validated object or a clear error." It's Pydantic's validation rigor applied at the LLM-output boundary, with automatic correction — exactly where LLM applications are most fragile.

## Why this is more than convenience

Structured outputs aren't just less code — they change the reliability profile of your application:

- **Errors are caught at the boundary.** Malformed output is caught and (often) corrected *right where it's produced*, instead of propagating as bad data that breaks something three steps later. This is the type-safety-catches-errors-early philosophy from the first post, realized.
- **Validation can encode business rules.** Because it's a full Pydantic model, you get all of Pydantic's validation — constraints (a quantity must be positive), custom validators, nested models — enforced on the LLM's output. The model must return not just the right *shape* but data satisfying your *rules*, or it's rejected and retried.
- **The rest of your program is typed.** Downstream code receives a real typed object, so your IDE, type checker, and refactoring tools all work — the LLM's output is now just typed data flowing through typed code.
- **It makes agents composable and testable.** A typed output is a clean interface; an agent that returns an `Order` composes with anything expecting an `Order`, and can be tested by asserting on typed fields.

The shift is from "hope the string is right" to "the output is a validated object satisfying my model's rules, or I get a clear error" — a fundamentally more robust foundation for anything that consumes LLM output.

## The range of output types

Pydantic AI's output typing is flexible, covering the real cases:

- **A Pydantic model** — the common case: structured data with typed, validated fields.
- **Plain types** — simpler outputs (a string, a number, a list) when you don't need a full model.
- **Unions of types** — the output can be one of several models (e.g. a `Success` result *or* a `NeedMoreInfo` result), letting the agent signal different structured outcomes — powerful for modeling branching results type-safely.
- **Validation with custom logic** — output validators that run your own checks (including ones needing dependencies), rejecting and retrying outputs that fail domain rules.

This range means structured outputs aren't limited to "fill in this form" — you can model rich, branching, rule-constrained results, all type-safe. It's the feature that most distinguishes Pydantic AI, and the one that makes it especially strong for the extraction, classification, and typed-workflow applications the first post highlighted. With reliable typed output established, the next post covers how the agent *acts* on the world to produce those outputs: tools.

## Key takeaways

- Structured outputs are Pydantic AI's flagship feature: declare a Pydantic model as the agent's output type and get back a validated instance (`result.output`), replacing the brittle prompt-parse-validate-handle dance with a type declaration.
- The mechanism is schema → validate → retry: the framework derives a schema from your model to constrain the LLM, validates the output with Pydantic, and automatically feeds validation errors back to the model to self-correct malformed output.
- It's more than convenience — it changes reliability: errors are caught (and often corrected) at the output boundary instead of propagating, and Pydantic validation lets you enforce business rules (constraints, custom validators) on the model's output, not just its shape.
- Downstream code receives a real typed object, so IDE/type-checker/refactoring tools all work, and typed outputs make agents composable and testable via clean interfaces.
- Output types are flexible: Pydantic models (the common case), plain types, unions (one of several result models for branching outcomes), and custom output validators — enabling rich, rule-constrained, branching results, all type-safe.

## Further reading

- [Agents (previous post)](/blog/posts/pydai-02-agents.html)
- [Pydantic AI documentation — results and output types](https://ai.pydantic.dev/)
- [Pydantic — data validation](https://docs.pydantic.dev/)
