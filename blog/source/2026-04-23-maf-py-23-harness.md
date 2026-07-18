# Harness

*The batteries-included autonomous agent pipeline from create_harness_agent.*

---

## What this lesson demonstrates

A plain `Agent` only calls the model and loops over the tools you hand it. An agent harness is the batteries-included scaffolding around that model: a ready-made autonomous pipeline with a function-calling loop, a persistent todo list, plan/execute modes, file and web-search tools, tool-approval heuristics, context compaction, and OpenTelemetry — all on by default and individually switchable. `create_harness_agent(client, ...)` assembles a fully wired `Agent` from your chat client; you just configure the parts you want to change.

## The core call

```python
return create_harness_agent(
    client=client,
    name="research-agent",
    agent_instructions=(
        "You are a concise research assistant. Break work into a short todo "
        "list, use your tools, and report the final answer plainly."
    ),
    tools=get_stock_price,
    disable_web_search=True,  # no hosted web search for this offline demo
)
```

Task-specific prompt goes in `agent_instructions`; general operating rules go in `harness_instructions` (default `DEFAULT_HARNESS_INSTRUCTIONS`). Extra tools pass via `tools=`.

## The gotcha

Every default capability has a `disable_*` flag: `disable_todo`, `disable_mode`, `disable_web_search`, `disable_file_memory`, `disable_file_access`, `disable_tool_auto_approval`, `disable_compaction`. Compaction only turns on when you supply both `max_context_window_tokens` and `max_output_tokens` (or a custom strategy); otherwise it is auto-disabled. For looping, a `loop_should_continue` predicate (e.g. `todos_remaining()`) plus a `loop_max_iterations` cap re-invoke the agent until the predicate says stop.

## The Azure / MAF mapping

`create_harness_agent` wraps a `FoundryChatClient` (with `AzureCliCredential`) in the full agentic pipeline and returns a normal `Agent`. It is stateful across a run, so drive it with a session: `session = agent.create_session()` then `await agent.run(prompt, session=session)`.

## Run it

`uv run tutorial/02-agents/15_harness.py` — needs Foundry credentials via `az login`.

---

Next: [Code Act](/blog/posts/maf-py-24-code-act.html)
