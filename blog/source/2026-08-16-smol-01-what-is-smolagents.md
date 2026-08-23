# What Is smolagents?

*Most agent frameworks have the model call tools by emitting JSON. smolagents, Hugging Face's deliberately tiny library, makes the model write Python code instead — "agents that think in code." That one design choice, plus a ruthless commitment to minimalism, is what the whole library is about, and it turns out to matter more than it sounds.*

smolagents is a minimal agent library from Hugging Face, and its tagline says it plainly: *a barebones library for agents that think in code.* Two things define it — an extreme commitment to **minimalism** (its core is only around a thousand lines), and a distinctive **code-first** approach where agents express their actions as executable Python rather than structured JSON tool calls. This series covers it concept by concept; this first post establishes what it is, the minimalism, and the code-agent idea that sets it apart.

## What smolagents is

smolagents is a small, open-source Python library for building agents. You give an agent a model and some tools, and it runs the agent loop — but its defining characteristic is *how* the agent takes actions: by **writing and executing code**. It's deliberately minimal (the core logic is tiny), model-agnostic (works with Hugging Face models, and others via integrations), and it emphasizes the **code agent** as its primary abstraction, while also supporting traditional tool-calling agents.

The two things to hold from the start: **minimalism** (it's small, simple, and easy to understand — you can read the whole core) and **code-first** (agents act by writing code, which is the library's signature idea and the reason it exists). Everything else follows from these.

## The minimalism

smolagents's first defining trait is how *small* it is. Where some agent frameworks are sprawling toolkits, smolagents's core is on the order of a thousand lines — small enough to read and understand in full. This minimalism is a deliberate philosophy, and it has real consequences:

- **Understandable** — you can read the whole library and know exactly what your agent does. There's no deep stack of abstractions hiding behavior; the loop is simple and legible.
- **Low overhead** — little conceptual and code overhead to get an agent running; the library gets out of your way.
- **Hackable** — because it's small and simple, it's easy to modify, extend, and understand — you're not fighting a large framework.
- **A learning tool** — its minimalism makes it excellent for *understanding* how agents work, since the core loop isn't buried under abstraction.

This is a different value proposition from the batteries-included frameworks (LangChain) or the philosophy-heavy ones — smolagents's pitch is "small, simple, readable, does the essential thing well." If you value understanding your tools and minimal overhead, the minimalism itself is a reason to reach for it. It reflects a real design stance: an agent doesn't need a huge framework; it needs a model, tools, and a loop — kept small.

## The code-agent idea

smolagents's second and more distinctive trait is the **code agent** — the idea that an agent should express its actions as *executable code* rather than as structured (JSON) tool calls. This is the library's signature, so it's worth stating clearly up front (the next posts go deep):

- **Traditional tool calling** — the model outputs a structured *JSON* description of a tool call (call this tool with these arguments), which the framework parses and executes. This is the standard approach across most providers and frameworks.
- **Code agents** (smolagents's default) — the model outputs *Python code* that calls tools (and does logic, control flow, variable handling) directly, which the framework executes. The model's "action" is a snippet of code, not a JSON blob.

"Agents that think in code" means exactly this: the agent reasons and acts by *writing code*. Instead of "I want to call the search tool with this query" as JSON, the agent writes `results = search("query")` as code — and can then loop over results, store them in variables, call another tool with them, and do real logic, all in one action. This turns out to be more powerful than it sounds, and the reasons (efficiency, expressiveness, composability) are the subject of the next posts. For now, the key point: smolagents's identity is that agents act by writing code, and that choice ripples through everything.

## Why code agents matter (the preview)

The code-agent approach isn't a quirk — Hugging Face's argument (with supporting evidence) is that it's genuinely *better* for many tasks, which the next post details. In brief:

- **More efficient** — a code action can do in one step what would take several JSON tool-call round-trips (call a tool, loop, call another, combine), reportedly reducing steps and LLM calls meaningfully.
- **More expressive** — code naturally handles logic, control flow, variables, and composing tool results, which JSON tool calls express awkwardly or not at all.
- **Plays to the model's strengths** — LLMs are trained on enormous amounts of code, so writing code is something they're often very good at — arguably more natural than emitting a specific JSON schema.

The trade-off, also covered ahead, is **security** — executing model-written code is dangerous and must be sandboxed (its own post). But the core claim is that letting agents act in code is a powerful default, and smolagents is built around it. This is why smolagents is more than "a small library" — it's a small library making a specific, evidence-backed bet about *how* agents should act.

## When to use smolagents

Like any framework, it fits some situations (the [agent-framework comparison](/blog/posts/ai-decisions-02-agent-frameworks.html) covers the broader choice):

- **Reach for smolagents when** you want a minimal, understandable, hackable agent library, when the code-agent approach fits your task (tasks involving logic, computation, composing tool results — where code actions shine), and when you value reading and understanding your framework over a large batteries-included one.
- **It's excellent for learning** how agents work, precisely because of its minimalism, and for tasks where code-as-action is a natural fit.
- **Consider alternatives when** you need a batteries-included ecosystem (LangChain), heavy stateful orchestration (LangGraph), type-safe structured outputs (Pydantic AI), or you can't safely execute model-written code in your environment (the security constraint). smolagents is the small, code-first choice.

The through-line: smolagents is Hugging Face's minimal, code-first agent library — small enough to understand fully, built on the powerful idea that agents should think and act in code. The next post goes deep on that code-agent idea, the heart of the library.

## Key takeaways

- smolagents is a minimal, open-source agent library from Hugging Face — "a barebones library for agents that think in code" — defined by two traits: extreme minimalism (core ~1,000 lines) and a code-first approach.
- The minimalism is deliberate: the library is small enough to read and understand fully, with low overhead, high hackability, and value as a learning tool — a different pitch from batteries-included frameworks, reflecting the stance that an agent needs just a model, tools, and a loop.
- The signature idea is the code agent: instead of the model emitting JSON tool calls (the standard approach), it writes executable Python that calls tools and does logic directly — "thinking in code," where an action is a code snippet, not a JSON blob.
- Code agents are argued to be genuinely better for many tasks — more efficient (one code action does what several JSON round-trips would), more expressive (natural logic/control-flow/variables/composition), and playing to LLMs' code-training strengths — with security (sandboxing model-written code) as the key trade-off.
- Reach for smolagents for a minimal, understandable, hackable library when the code-agent approach fits (logic/computation/composing results) and you can execute code safely; consider alternatives for batteries-included ecosystems, heavy orchestration, type safety, or environments where code execution is unsafe.

## Further reading

- [smolagents documentation (Hugging Face)](https://huggingface.co/docs/smolagents/index)
- [smolagents on GitHub](https://github.com/huggingface/smolagents)
- [AI Architecture Decisions: choosing an agent framework](/blog/posts/ai-decisions-02-agent-frameworks.html)
