# Structured Outputs

*Making a Microsoft Agent Framework agent return typed data instead of prose.*

---

## What this lesson demonstrates

By default an agent returns free-form text. Structured outputs make it return data that conforms to a schema you define, so you can consume a typed object instead of regex-ing prose. The whole feature rides on one key: `response_format` inside the `options` dict on `agent.run(...)`.

The schema can be either a Pydantic `BaseModel` (then `response.value` is an instance of that model) or a JSON-schema dict (then `response.value` is the parsed JSON, usually a dict). The lesson walks through both plus a streaming variant.

## The core call

```python
class PersonInfo(BaseModel):
    name: str | None = None
    age: int | None = None
    occupation: str | None = None

response = await agent.run(PROMPT, options={"response_format": PersonInfo})
if response.value:
    p = response.value  # a typed PersonInfo instance
    print(f"name={p.name}  age={p.age}  occupation={p.occupation}")
```

Streaming works the same way: iterate the stream for live tokens, then call `await stream.get_final_response()` and read `.value` off the finalized response.

## The gotcha

The parsed object lives on `response.value`, not `response.text`. `.text` is still the raw JSON string; `.value` is `None` when parsing fails, so always branch on it. Primitives and bare lists are not supported directly, so wrap them in a model or object.

## The Azure / MAF mapping

The agent is a plain `Agent` over a `FoundryChatClient` authenticated with `AzureCliCredential`. `response_format` maps to the underlying model's structured-output capability; the framework handles schema translation and parses the result back into `.value` for you.

## Run it

`uv run tutorial/02-agents/09_structured_outputs.py` — needs Azure AI Foundry credentials (`az login` plus `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_MODEL`).

---

Next: [Background Responses](/blog/posts/maf-py-18-background-responses.html)
