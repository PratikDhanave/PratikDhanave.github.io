# Tools and Structured Context

*Tool definitions and structured data quietly consume a large share of the context budget, and how you select, describe, and format them shapes both what fits and how well the model uses it.*

When people think about context, they picture prompts and documents. But two other claimants often consume more of the budget than expected: the definitions of the tools a model can call, and the structured data you feed it. Both are context, both cost tokens, and both strongly affect the model's behavior. This sixth post in the context engineering series covers tools and structured context — the parts of the window that are easy to overlook and expensive to get wrong.

## Tool definitions are context too

Every tool you give a model comes with a definition — a name, a description, and an input schema — and all of it goes into the context window on calls where the tools are available. Give the model twenty richly-described tools and you may spend thousands of tokens on tool definitions before the task begins. That has two consequences: it eats budget that could go to the task, and — more subtly — it makes the model's job harder. Choosing among twenty tools is a harder decision than choosing among five, and a crowded toolset invites wrong selections.

So tools are subject to the same budget discipline as everything else. The questions are which tools to expose, how to describe them, and whether the model needs all of them for this task.

## Select the tools the task needs

The most effective move is often to *not* present every tool on every call. If you know the task at hand only needs a subset — a query-and-report task does not need the file-deletion tools — expose only that subset. Fewer, well-chosen tools mean a smaller budget footprint and a cleaner decision for the model. When the full set is large, consider selecting tools per task (by category, by the current step, or by retrieving relevant tools much as you retrieve documents) rather than dumping the entire catalog into every window. The goal parallels retrieval: the model should see the tools relevant to now, not the maximum available.

## Describe tools for the model that reads them

A tool's description and schema are the model's entire basis for using it correctly — they are, effectively, part of the prompt. The same principles as tool design apply: a specific name that signals intent, a description that says what the tool does *and when to use it*, and a schema that names each parameter, types it, marks required fields, and constrains values. Vague or overlapping tool descriptions produce wrong calls and force the model to guess arguments. Precise ones make selection and invocation nearly deterministic. The tokens spent on a good description are among the best-spent in the whole context, because they prevent a whole class of failed tool calls.

## Formatting structured data

Beyond tools, agents frequently need structured data in context — records, tables, configuration, API results. How you format it affects both how many tokens it costs and how well the model reads it.

- **Choose a format the model parses well.** Models handle common structured formats (JSON, and simple tables or key-value layouts) reliably. Favor clarity over cleverness; a clean, consistent structure beats a dense custom encoding the model has to decode.
- **Mind the token cost of the format.** Verbose formats carry overhead — deeply nested JSON repeats keys and punctuation on every record. For large, uniform datasets, a compact tabular or key-value layout can convey the same information in far fewer tokens than repetitive JSON. The right format balances readability against budget.
- **Include only the fields that matter.** An API might return fifty fields when the task needs three. Project down to the relevant fields before placing data in the context; the rest is pure budget waste that also dilutes attention.
- **Label and delimit.** Give structured blocks clear headers and boundaries so the model knows what it is looking at and does not confuse data with instructions.

## Tool results are context that accumulates

A tool call's *result* re-enters the context so the model can use it — and in an agent loop, these results pile up turn after turn. A single verbose result (a full document, a large JSON payload) can dominate the window, and several of them across a long run can crowd out everything else. Treat tool results with the same discipline as history: keep the distilled information the model needed, not the raw dump, once it has been consumed. This is where the tools topic meets the memory topic — an agent that faithfully retains every raw tool output will overflow far faster than one that summarizes results down to what matters.

## The overlooked budget

The theme of this post is that tools and structured data are a large, frequently-ignored slice of the context budget. Teams optimize their prompts and their retrieval and then wonder why the window is full — and the answer is often a bloated toolset, verbose data formatting, and accumulating raw tool output. Auditing these three is one of the highest-return things you can do for an agent's cost, latency, and reliability. Expose the tools the task needs, describe them precisely, format data compactly and relevantly, and distill tool results — and a surprising amount of budget, and a surprising number of errors, disappear.

## Key takeaways

- Tool definitions (name, description, schema) are context that consumes the budget on every call where tools are available; a crowded toolset both costs tokens and makes the model's selection harder.
- Expose only the tools a task needs — select per task rather than dumping the whole catalog — to shrink the footprint and sharpen the model's decision.
- Tool descriptions and schemas are effectively part of the prompt: specific names, when-to-use descriptions, and precise schemas prevent a whole class of failed calls.
- Format structured data for both parseability and token cost: pick a format the model reads well, project to relevant fields, use compact layouts for large uniform data, and label/delimit blocks.
- Tool results re-enter and accumulate in context; distill them to what matters rather than retaining raw dumps — auditing tools, data formatting, and result bloat is a high-return optimization.

## Further reading

- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
