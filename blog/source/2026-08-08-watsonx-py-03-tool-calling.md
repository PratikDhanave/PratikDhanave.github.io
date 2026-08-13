# Tool Calling with watsonx

*Letting a Granite model on watsonx.ai invoke your Python functions — the full request-and-response loop with the first-party `ibm-watsonx-ai` chat API, plus the shorter LangChain path with `ChatWatsonx.bind_tools`.*

---

The last post got a Granite model on watsonx.ai talking to us through the `chat()` API — messages in, an assistant reply out. That reply is always *text*. A model, on its own, cannot check today's weather, query your database, or add two numbers reliably. **Tool calling** is how you close that gap: you describe the functions the model is allowed to invoke, and instead of guessing an answer the model asks *you* to run one and hand back the result.

watsonx.ai speaks the same tool-calling shape you may know from other chat APIs — an OpenAI-style `tools` array, `tool_choice`, and an assistant message that can carry `tool_calls`. IBM's Granite instruct models are explicitly trained for this: given a well-described tool, they will emit a structured call rather than hallucinate the answer. This post builds the whole round-trip in the first-party SDK, then shows the compressed LangChain version. Everything here assumes the credentials from the earlier posts: an IAM API key, a `project_id`, and a regional `url`.

---

## What "tool calling" actually is

It helps to be precise, because the name oversells the magic. The model never runs your code. The loop is entirely yours:

1. You send the conversation **plus a catalog of tools** (each a name, a description, and a JSON-schema description of its arguments).
2. The model replies. Either it answers in prose (done), **or** it returns one or more `tool_calls` — each naming a tool and supplying arguments.
3. **You** parse those arguments, call the real Python function, and append the result to the conversation as a `tool`-role message.
4. You call `chat()` again with the extended conversation. Now the model can use the results — to answer, or to call another tool.

That is a loop, and loops need a cap. The model can chain several tool calls before it is satisfied, so you iterate until it stops asking or until you hit a sane iteration ceiling.

---

## Step 1: describe a tool as a JSON schema

A tool declaration is a plain Python dict in the shape watsonx.ai expects. The `parameters` field is a standard JSON Schema object — the model reads it to decide *whether* to call the tool and *what* to pass.

```python
GET_WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current temperature for a city, in Celsius.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Pune' or 'Frankfurt'.",
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit to report in.",
                },
            },
            "required": ["city"],
        },
    },
}
```

The description fields are not decoration — they are the entire interface the model reasons over. A vague description ("gets weather") produces vague tool use; a specific one, with the units and an example city, produces reliable calls. Treat these strings the way you would treat a docstring another engineer depends on.

Behind each declared tool sits an ordinary Python function. Nothing about it is special — it takes normal arguments and returns a normal value:

```python
def get_weather(city: str, unit: str = "celsius") -> dict:
    """Look up the current temperature. Stubbed here with fixed data."""
    table = {"pune": 31, "frankfurt": 9, "dallas": 24}
    celsius = table.get(city.strip().lower(), 20)
    temp = celsius if unit == "celsius" else round(celsius * 9 / 5 + 32)
    return {"city": city, "temperature": temp, "unit": unit}
```

In a real system this would hit a weather API. The point of the loop is identical either way: the model asks, you execute, you report back.

---

## Step 2: run the round-trip loop by hand

Here is the complete loop against the first-party `chat()` API. Read it once, then we will pull apart the three fiddly bits.

```python
import json
import os
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

credentials = Credentials(
    url="https://us-south.ml.cloud.ibm.com",
    api_key=os.environ["WATSONX_API_KEY"],
)

model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",   # a tool-capable Granite instruct model; verify the id
    credentials=credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)

# Map the declared tool names to the real callables.
TOOLS = [GET_WEATHER_TOOL]
DISPATCH = {"get_weather": get_weather}


def run_conversation(user_prompt: str, max_iterations: int = 5) -> str:
    messages = [
        {"role": "system", "content": "You are a concise assistant. Use tools when they help."},
        {"role": "user", "content": user_prompt},
    ]

    for _ in range(max_iterations):
        response = model.chat(messages=messages, tools=TOOLS, tool_choice="auto")
        assistant_msg = response["choices"][0]["message"]
        messages.append(assistant_msg)   # keep the model's turn in the history

        tool_calls = assistant_msg.get("tool_calls")
        if not tool_calls:
            # No tool requested: this is the final natural-language answer.
            return assistant_msg.get("content", "")

        # The model asked for one or more tools. Run each and report back.
        for call in tool_calls:
            name = call["function"]["name"]
            result = execute_tool(name, call["function"]["arguments"])
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],       # must match the call exactly
                "content": json.dumps(result),
            })

    return "Stopped: reached the tool-call iteration cap without a final answer."
```

Three things in that loop carry all the weight.

**Arguments arrive as a JSON string, not a dict.** The `arguments` field on each tool call is a string of JSON — the model serialized them for transport. You must decode before use, and you must decode *defensively*, because a model can occasionally emit malformed or empty JSON:

```python
def execute_tool(name: str, raw_arguments: str) -> dict:
    fn = DISPATCH.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        kwargs = json.loads(raw_arguments) if raw_arguments else {}
    except (json.JSONDecodeError, TypeError):
        return {"error": "could not parse tool arguments", "raw": raw_arguments}
    try:
        return fn(**kwargs)
    except TypeError as exc:
        # Wrong or missing arguments — hand the error back so the model can retry.
        return {"error": f"bad arguments for {name}: {exc}"}
```

Notice that failures are *returned as data*, not raised. Feeding the error back into the conversation lets the model correct itself on the next turn — often it will re-call the tool with fixed arguments. Raising would just crash your loop.

**Every tool result must echo the exact `tool_call_id`.** When the model requests several tools in one turn, it disambiguates the results purely by id. A `tool` message with a wrong or missing `tool_call_id` breaks the pairing and confuses the model on the next call. Copy `call["id"]` straight through — never regenerate it.

**You append the assistant turn *and* the tool turns.** The history you send back must contain the assistant message that made the calls, followed by one `tool` message per call. Skip the assistant turn and the tool results dangle with nothing to attach to.

**The gotcha:** `tool_choice` controls *whether* the model is allowed, or forced, to call a tool. `"auto"` lets the model decide (the usual choice); you can also force a specific function when your flow demands one first. But the important half is the branch in the loop: **you must check whether `tool_calls` is present at all.** A non-tool-trained model — or a tool-trained one that judges no tool is needed — simply answers in prose, and `assistant_msg.get("tool_calls")` is empty. Code that assumes a tool call always comes back will crash on the most common, healthy case: a direct answer.

---

## Multiple tool calls in one turn

The loop above already handles it, but it is worth seeing why the inner `for` matters. Ask *"Compare the temperature in Pune and Frankfurt"* and a capable Granite model will return **two** `tool_calls` in a single assistant message — one `get_weather` for each city — rather than taking two round-trips. Your job is to run both and append **both** results (each with its own `tool_call_id`) before calling `chat()` again:

```json
{
  "role": "assistant",
  "tool_calls": [
    {"id": "call_a1", "type": "function",
     "function": {"name": "get_weather", "arguments": "{\"city\": \"Pune\"}"}},
    {"id": "call_b2", "type": "function",
     "function": {"name": "get_weather", "arguments": "{\"city\": \"Frankfurt\"}"}}
  ]
}
```

The two `tool` messages you append carry `tool_call_id` `"call_a1"` and `"call_b2"` respectively. Get one id wrong and the model may attribute Frankfurt's weather to Pune. This is exactly why you copy the id verbatim rather than counting on order.

**The gotcha:** the response shape shown here — `response["choices"][0]["message"]`, and each call's `id` / `function.name` / `function.arguments` — follows watsonx.ai's OpenAI-compatible chat contract. Field names and nesting can shift between SDK versions, so before you ship, print one raw `chat()` response and confirm the exact keys against the version of `ibm-watsonx-ai` you installed. Keep your extraction in one small helper (like `execute_tool`) so there is a single place to adjust if a key moves.

---

## Not every model calls tools

Tool calling is a *model capability*, not a universal feature of the endpoint. Passing `tools=[...]` to a model that was not trained for function calling does not error — the model just ignores the catalog and answers in prose, and your `tool_calls` branch never fires. IBM's **Granite instruct** models are trained for tool and function calling, which is why they are the natural pick here. Other tool-capable models hosted on watsonx.ai work too.

The practical rule: check the model card for the specific id you are using before you rely on tool calls, and always write the loop so a prose-only answer is a valid, expected outcome rather than a bug. Your `if not tool_calls: return ...` line is that safety valve.

---

## The LangChain path: `bind_tools`

If your application already lives in LangChain, `ChatWatsonx` from `langchain-ibm` wraps the same machinery and hides the JSON plumbing. You declare a tool with the `@tool` decorator (LangChain reads the type hints and docstring to build the schema for you), bind it, and let LangChain marshal the calls.

```python
import os
from langchain_core.tools import tool
from langchain_ibm import ChatWatsonx


@tool
def get_weather(city: str, unit: str = "celsius") -> dict:
    """Get the current temperature for a city, in Celsius or Fahrenheit."""
    table = {"pune": 31, "frankfurt": 9, "dallas": 24}
    celsius = table.get(city.strip().lower(), 20)
    temp = celsius if unit == "celsius" else round(celsius * 9 / 5 + 32)
    return {"city": city, "temperature": temp, "unit": unit}


chat = ChatWatsonx(
    model_id="ibm/granite-3-8b-instruct",   # verify the id in the docs
    url="https://us-south.ml.cloud.ibm.com",
    project_id=os.environ["WATSONX_PROJECT_ID"],
)

llm_with_tools = chat.bind_tools([get_weather])
```

The response is a LangChain `AIMessage`. Its `.tool_calls` attribute is a list of dicts with the arguments **already parsed into a Python dict** — LangChain does the `json.loads` for you. The manual loop becomes a handful of lines:

```python
from langchain_core.messages import HumanMessage, ToolMessage

messages = [HumanMessage("What's the temperature in Pune?")]
ai_msg = llm_with_tools.invoke(messages)
messages.append(ai_msg)

for call in ai_msg.tool_calls:                 # args already decoded to a dict
    result = get_weather.invoke(call["args"])
    messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

final = llm_with_tools.invoke(messages)
print(final.content)
```

Same four steps — ask, execute, report, ask again — but LangChain absorbs the JSON decoding and message formatting. The `tool_call_id` discipline is still yours: `ToolMessage` requires it, and it must match `call["id"]`.

**The gotcha:** the two paths differ in exactly one place that bites people. In the raw SDK, `call["function"]["arguments"]` is a **JSON string you must `json.loads` yourself**; in LangChain, `call["args"]` is **already a dict**. Mix them up — calling `json.loads` on the LangChain dict, or `**` a string from the raw SDK — and you get an immediate `TypeError`. Know which layer you are in.

---

## Raw SDK vs. LangChain at a glance

| Concern | Raw `ibm-watsonx-ai` | `ChatWatsonx.bind_tools` |
|---|---|---|
| Declare a tool | Hand-written JSON-schema dict | `@tool` on a Python function |
| Attach tools | `chat(messages=..., tools=[...])` | `chat.bind_tools([...])` |
| Where the call sits | `response["choices"][0]["message"]["tool_calls"]` | `ai_msg.tool_calls` |
| Arguments format | JSON **string** — `json.loads` it | Python **dict** — already parsed |
| Report a result | `{"role": "tool", "tool_call_id": ..., "content": ...}` | `ToolMessage(content=..., tool_call_id=...)` |
| Control choice | `tool_choice="auto"` / forced | `bind_tools(..., tool_choice=...)` |

Reach for the raw SDK when you want full control of the message stream or are not otherwise on LangChain; reach for `bind_tools` when your app is already a LangChain application and you would rather not hand-marshal JSON.

---

## Key takeaways

- **The model asks, you execute.** watsonx.ai never runs your code — it returns `tool_calls`, and your loop parses them, calls the real function, appends a `tool` message, and calls `chat()` again until a prose answer comes back.
- **Arguments are a JSON string in the raw SDK.** `json.loads` them defensively and return errors as data so the model can retry; LangChain hands you an already-parsed dict instead.
- **Echo the exact `tool_call_id`.** Multiple tools can be requested in one turn, and the model pairs results to calls by id alone — copy it verbatim, never regenerate or rely on order.
- **Always branch on whether `tool_calls` is present.** A prose-only reply is the normal, healthy case; tool calling is a *model* capability, so pick a tool-trained Granite instruct model and let a direct answer be a valid outcome.
- **Cap the loop.** The model can chain several tool calls; iterate to a ceiling so a confused model can never spin forever.
- **Verify field names against your SDK version.** The response shape here follows watsonx.ai's OpenAI-compatible contract; print one raw response and confirm the keys before you ship.

---

## Further reading

- [Adding tools to a chat request (watsonx.ai docs)](https://www.ibm.com/docs/en/watsonx/saas?topic=lab-chat-function-calling) — official guidance on function calling with the chat API.
- [`ibm-watsonx-ai` SDK reference](https://ibm.github.io/watsonx-ai-python-sdk/) — API reference for `ModelInference`, including the `chat()` method and its parameters.
- [`ibm-watsonx-ai` on PyPI](https://pypi.org/project/ibm-watsonx-ai/) — the first-party Python SDK and its release notes.
- [IBM Granite documentation](https://www.ibm.com/granite/docs/) — model cards and capability details, including tool/function calling support per model.
- [`ChatWatsonx` in the LangChain docs](https://python.langchain.com/docs/integrations/chat/ibm_watsonx/) — the `langchain-ibm` chat model, including `bind_tools`.
- [`langchain-ibm` on GitHub](https://github.com/langchain-ai/langchain-ibm) — source and examples for `ChatWatsonx` and the rest of the integration.
