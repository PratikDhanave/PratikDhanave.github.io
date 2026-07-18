# Function Tools

*How a plain Python function becomes a JSON schema the model can call.*

---

## What it demonstrates

A "function tool" is ordinary Python code the agent is allowed to call. Microsoft Agent Framework reads the function's signature and docstring, turns it into a JSON schema the model sees, invokes your function when the model asks, then feeds the return value back so the model can phrase its answer.

This lesson is about how that **schema** gets built: the docstring becomes the tool description, and `Annotated[..., Field(description=...)]` describes each parameter so the model chooses tools and arguments accurately.

## The code

```python
@tool(
    name="currency_convert",
    description="Convert an amount between INR, USD, EUR and GBP using a fixed rate table.",
    approval_mode="never_require",
)
def convert_currency(
    amount: Annotated[float, Field(description="The amount of money to convert.")],
    from_ccy: Annotated[str, Field(description="Source currency code: INR, USD, EUR or GBP.")],
    to_ccy: Annotated[str, Field(description="Target currency code: INR, USD, EUR or GBP.")],
) -> str:
    """Fallback description — ignored because @tool sets an explicit description."""
    ...
```

Tools attach at agent creation via `tools=[get_weather, convert_currency]`. The lesson mixes a plain function and a `@tool`-decorated one to show both register the same way.

## The gotcha

The `@tool` decorator is **optional** — you can pass a plain function straight to `tools=[...]` and the framework falls back to the function name and docstring. Where it earns its keep is overriding those defaults: `@tool(name=..., description=...)` decouples what the model sees from your Python identifier (note above, the docstring is ignored once an explicit description is set). Per-parameter descriptions come from `Annotated[type, Field(description=...)]`; a bare `Annotated[int, "..."]` string also works as a short description.

## Azure / MAF mapping

Not every agent type supports caller-provided function tools, but chat-client agents do — here a `FoundryChatClient` against Azure AI Foundry with `AzureCliCredential()`. The model reads the generated schemas and picks `get_weather` or `currency_convert` from the wording of the question.

## Run it

`uv run tutorial/02-agents/tools/01_function_tools.py` — needs Foundry creds. You get a weather answer, then a currency conversion like `250 USD = ... INR`.

---

Next: [Controlling Tool Availability](/blog/posts/maf-py-38-controlling-tool-availability.html)
