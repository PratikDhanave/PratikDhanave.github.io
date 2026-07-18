# Add Tools

*A tool is just a Python function the model may call: decorate it with @tool, annotate the arguments, and the framework wires the schema, the call, and the result back into the conversation.*

---

## What this lesson demonstrates

An agent with instructions can only talk. Give it tools and it can act. Here two functions — `get_weather` and `convert_currency` — become callable tools, and the agent picks the right one from the wording of each question. You never call the tools yourself; the model decides, the framework runs them and feeds the result back so the model can phrase a final answer.

## The code

Three things make a function usable as a tool: a docstring (WHAT it does), `Annotated` `Field` descriptions (what each argument means), and a human-readable return string:

```python
@tool(approval_mode="never_require")
def convert_currency(
    amount: Annotated[float, Field(description="The amount of money to convert.")],
    from_ccy: Annotated[str, Field(description="Source currency code, e.g. USD, EUR, GBP, INR.")],
    to_ccy: Annotated[str, Field(description="Target currency code, e.g. USD, EUR, GBP, INR.")],
) -> str:
    """Convert an amount between USD, EUR, GBP and INR using a fixed rate table."""
    ...
```

Attaching them to the agent is one argument:

```python
Agent(client=client, name="ToolAgent",
      instructions="Use your tools when they fit the question.",
      tools=[get_weather, convert_currency])
```

## What to notice

- **The docstring and Field descriptions are the API the model sees.** Vague descriptions produce bad tool choices — this is prompt engineering wearing a type annotation.
- **`approval_mode` gates side effects.** `"never_require"` runs the tool silently; a side-effecting production tool should use `"always_require"` so a human confirms first (a later lesson covers approval).
- **The gotcha:** the model, not your code, decides which tool fires. "How much is 250 US dollars in rupees?" routes to `convert_currency` purely because the wording matches its docstring — so write docstrings for the model to read.

## How it maps to Azure AI Foundry

The Foundry Responses API supports function calling: `@tool` turns your annotated function into the JSON schema Foundry advertises to the model, and the framework handles the call/return round-trip transparently. Same `FoundryChatClient` + `AzureCliCredential` as before.

## Run it

```bash
uv run tutorial/01-get-started/02_add_tools.py
```

Expected: a weather answer from one tool, a currency conversion from the other. Needs Foundry creds and `az login`.

---

Next: [Multi Turn](/blog/posts/maf-py-03-multi-turn.html)
