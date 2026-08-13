# Calling watsonx.ai from Python

*Your first real inference calls with the ibm-watsonx-ai SDK — credentials, ModelInference, the generate and chat APIs, streaming, token usage, error handling, and the langchain-ibm path.*

---

Once you have a watsonx.ai project provisioned, the interesting part starts: sending a prompt to a foundation model from Python and getting text back. IBM ships a first-party SDK, `ibm-watsonx-ai`, that wraps the REST inference endpoints so you never assemble a raw HTTP request or juggle bearer tokens yourself. This post walks through making real calls — from the three pieces of authentication every request needs, through the two families of generation APIs, to streaming, usage accounting, and the LangChain integration when you want a portable interface.

Everything below is ordinary Python you can run against your own project once your credentials are in the environment.

---

## Install and authenticate

Install the SDK. If you plan to use the LangChain path later, add `langchain-ibm` too.

```bash
pip install ibm-watsonx-ai
pip install langchain-ibm   # only if you want the LangChain wrapper
```

Every call to watsonx.ai carries three things: an IAM **API key** that proves who you are, a **regional service URL** that says which data center hosts the models, and a **project_id** (or a **space_id**) that scopes billing and asset access. Read all three from the environment — never paste an API key into source that lands in git.

```python
import os
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

credentials = Credentials(
    url=os.environ["WATSONX_URL"],          # e.g. https://us-south.ml.cloud.ibm.com
    api_key=os.environ["WATSONX_APIKEY"],
)

model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",
    credentials=credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)
```

The regional URL is not cosmetic — `us-south`, `eu-de`, `eu-gb`, `jp-tok`, `au-syd`, and the others are distinct endpoints, and a project created in one region is not reachable through another region's URL. Set `WATSONX_URL` to match the region where you created your project.

**The gotcha:** you need **both** an API key **and** a project_id (or space_id) — a perfectly valid API key with no project attached still fails. The API key authenticates *you*; the project_id tells watsonx.ai *which workspace* the request runs against, and that is where model access and token consumption are tracked. If you are deploying assets rather than developing, pass `space_id=...` instead of `project_id=...`; you supply one or the other, not both.

---

## The generate family: text in, text out

The oldest and simplest surface is text generation. `ModelInference` gives you two closely related methods.

`generate_text()` returns just the generated string — nothing else. It is the right choice when all you want is the completion.

```python
prompt = "Write one sentence explaining what a vector database is."
answer = model.generate_text(prompt=prompt)
print(answer)
```

`generate()` returns the full response dictionary. That includes the generated text plus the metadata watsonx.ai reports for the call — most usefully the token counts. Reach for it whenever you need to know how many tokens the request consumed.

```python
response = model.generate(prompt=prompt)

results = response["results"][0]
print("text:", results["generated_text"])
print("input tokens:", results["input_token_count"])
print("output tokens:", results["generated_token_count"])
print("stop reason:", results["stop_reason"])
```

The shape is a dict with a `results` list; each entry carries `generated_text`, `input_token_count`, `generated_token_count`, and `stop_reason`. Token counts matter for cost — watsonx.ai bills on tokens processed — and for staying inside a model's context window, so a habit of reading them early pays off.

**The gotcha:** `generate_text` returns a plain string while `generate` returns the full dict with usage. Pick based on whether you need the numbers. If you call `generate_text` and later wish you had the token counts, you have to make the request again — there is no usage hiding on the string. When in doubt during development, use `generate` and read `results["generated_text"]`.

---

## The chat API: the forward path

The generate family sends a single flat prompt. Modern instruction-tuned models are trained on **conversations** — sequences of messages with roles — and watsonx.ai exposes a chat surface built for exactly that. This is the API to prefer for new work.

```python
messages = [
    {"role": "system", "content": "You are a concise assistant for software engineers."},
    {"role": "user", "content": "What is idempotency in an HTTP API?"},
]

response = model.chat(messages=messages)
print(response["choices"][0]["message"]["content"])
```

The message list uses `system`, `user`, and `assistant` roles, and the response follows the familiar chat-completion shape: a `choices` list whose entries hold a `message` with `role` and `content`. Usage rides along under a `usage` object.

```python
usage = response["usage"]
print("prompt tokens:", usage["prompt_tokens"])
print("completion tokens:", usage["completion_tokens"])
print("total tokens:", usage["total_tokens"])
```

To hold a multi-turn conversation, append the assistant's reply and the next user turn to `messages` and call `chat()` again — the model sees the whole history each time. The system message is where you put durable instructions about tone, format, and role.

When should you use which? Use **chat** for anything conversational, anything multi-turn, and anything where a system message helps — it is the direction IBM and the wider ecosystem are moving. The **generate** family still fits single-shot completion tasks and older prompt templates, and it is a touch simpler when you genuinely have one prompt and want one string back. For new code, default to chat.

---

## Setting parameters

Left alone, a model uses its defaults. To control output length, randomness, and the decoding strategy, pass parameters. For the generate family, the SDK gives you named constants so you do not have to memorize raw key strings.

```python
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

params = {
    GenParams.DECODING_METHOD: "greedy",
    GenParams.MAX_NEW_TOKENS: 200,
    GenParams.MIN_NEW_TOKENS: 1,
}

model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",
    credentials=credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
    params=params,
)
```

Two decoding methods matter. **Greedy** decoding always takes the highest-probability next token, so it is deterministic — the same prompt yields the same output. **Sampling** introduces randomness, and only then do `TEMPERATURE`, `TOP_P`, and `TOP_K` have any effect.

```python
sampling_params = {
    GenParams.DECODING_METHOD: "sample",
    GenParams.MAX_NEW_TOKENS: 300,
    GenParams.TEMPERATURE: 0.7,
    GenParams.TOP_P: 0.9,
}
```

You can attach `params` at construction time as above, or pass them per call: `model.generate_text(prompt=prompt, params=sampling_params)`. A per-call `params` overrides the constructor default for that request.

For the chat API, use `TextChatParameters` rather than `GenParams` — the chat surface has its own parameter model (covering things like `max_tokens`, `temperature`, and `top_p`), passed via the `params` argument on `chat()`.

```python
from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

chat_params = TextChatParameters(max_tokens=300, temperature=0.5, top_p=0.9)
response = model.chat(messages=messages, params=chat_params)
```

**The gotcha:** the decoding method decides which other parameters do anything. Set `TEMPERATURE` while `DECODING_METHOD` is `"greedy"` and it is silently ignored — greedy has no randomness to tune. If you want reproducible output, use greedy; if you want varied or creative output, switch to sampling and *then* tune temperature and top-p. Mixing the two mental models is the most common reason "my temperature setting does nothing."

---

## Streaming

For anything a human reads as it arrives — a chat UI, a long generation — stream the tokens instead of waiting for the whole response. Both API families have a streaming variant that returns a generator you iterate.

For the generate family, `generate_text_stream` yields text chunks:

```python
for chunk in model.generate_text_stream(prompt="List three benefits of unit testing."):
    print(chunk, end="", flush=True)
print()
```

For the chat API, `chat_stream` yields incremental response objects; pull the partial content out of each delta:

```python
for chunk in model.chat_stream(messages=messages):
    choices = chunk.get("choices", [])
    if choices:
        delta = choices[0].get("delta", {})
        piece = delta.get("content")
        if piece:
            print(piece, end="", flush=True)
print()
```

Streaming does not change what the model produces — the same prompt and parameters give the same result — it only changes *when* the bytes reach you. Each chat stream event carries a `delta` rather than a full `message`, and you accumulate the `content` pieces yourself to rebuild the whole reply.

---

## Error handling

Real calls fail: a wrong region URL, an expired or malformed API key, a project the key cannot access, a model_id that is not deployed where you are calling. The SDK surfaces these as exceptions from its own error hierarchy rather than leaving you to parse HTTP status codes.

```python
from ibm_watsonx_ai.wml_client_error import WMLClientError, ApiRequestFailure

try:
    answer = model.generate_text(prompt=prompt)
    print(answer)
except ApiRequestFailure as exc:
    # the service accepted the request but returned an error status
    print("watsonx.ai request failed:", exc)
except WMLClientError as exc:
    # client-side / configuration problems, including auth setup
    print("client error:", exc)
```

`WMLClientError` is the base for the SDK's client errors, and `ApiRequestFailure` (a subclass) is raised when the service returns a non-success response — its message includes the status and the server's error payload, which usually names the exact problem (invalid model, missing project access, bad parameters). Catch `ApiRequestFailure` for service-side rejections and fall back to `WMLClientError` for broader configuration issues.

One thing you do **not** have to handle: IAM token lifecycle. Your API key is exchanged for a short-lived bearer token behind the scenes, and the SDK refreshes it when it nears expiry. You supply the long-lived API key once; token rotation is the SDK's job, not yours.

**The gotcha:** a `model_id` string is region- and version-specific. A model available in `us-south` may not be available in `eu-de`, and IBM deprecates and retires model versions on a published schedule, so a hard-coded id that worked last quarter can start returning errors. Before assuming your code is broken, confirm the model is actually available in *your* region and project — list what your setup can reach:

```python
from ibm_watsonx_ai.foundation_models import ModelInference

# APIClient.foundation_models.get_model_specs() enumerates available models;
# check the SDK docs for the exact call in your version, then pick a live model_id.
```

---

## The langchain-ibm path

If your application is built on LangChain — chains, agents, retrievers — you probably want a chat model object that speaks LangChain's interface instead of watsonx.ai's native dicts. The `langchain-ibm` package provides `ChatWatsonx`, a drop-in `BaseChatModel`.

```python
import os
from langchain_ibm import ChatWatsonx

chat = ChatWatsonx(
    model_id="ibm/granite-3-8b-instruct",
    url=os.environ["WATSONX_URL"],
    project_id=os.environ["WATSONX_PROJECT_ID"],
    apikey=os.environ["WATSONX_APIKEY"],
)

result = chat.invoke("Explain the CAP theorem in two sentences.")
print(result.content)
```

`ChatWatsonx` takes the same four pieces of configuration — `model_id`, `url`, `project_id`, `apikey` — and gives you the standard LangChain methods. `.invoke()` returns an `AIMessage` whose `.content` is the text; `.stream()` yields message chunks the same way LangChain streams every chat model.

```python
for chunk in chat.stream("Name three sorting algorithms."):
    print(chunk.content, end="", flush=True)
print()
```

You can pass LangChain message objects too:

```python
from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content="You answer as briefly as possible."),
    HumanMessage(content="What port does HTTPS use by default?"),
]
print(chat.invoke(messages).content)
```

When would you prefer `ChatWatsonx` over the native `ModelInference`? When watsonx.ai is one interchangeable piece of a larger LangChain application — you want to compose it into chains, swap it for another provider by changing one constructor, or reuse LangChain tooling for prompts, output parsing, and agents. When you are writing a small, direct integration or need watsonx.ai features not surfaced through the LangChain abstraction, the native SDK is the more transparent choice.

---

## Native SDK vs. LangChain at a glance

| Concern | `ModelInference` (native) | `ChatWatsonx` (langchain-ibm) |
|---|---|---|
| Interface | watsonx.ai dict responses | LangChain `BaseChatModel` |
| Text call | `generate_text` / `generate` / `chat` | `.invoke()` |
| Streaming | `generate_text_stream` / `chat_stream` | `.stream()` |
| Parameters | `GenParams` / `TextChatParameters` | constructor + `params` kwargs |
| Best when | direct integration, full feature access | part of a larger LangChain app |

---

## Key takeaways

- **Every request needs three things:** an IAM API key, a regional URL that matches your project's region, and a project_id (or space_id). Read them from the environment; a valid key with no project still fails.
- **`generate_text` returns a string, `generate` returns the dict with token counts.** Use `generate` when you need usage; you cannot recover it from a bare string after the fact.
- **Prefer the chat API for new work.** Messages with `system`/`user`/`assistant` roles match how modern models are trained, and usage arrives under `usage` in the response.
- **Decoding method gates the other parameters.** Greedy is deterministic; sampling is where temperature and top-p do anything.
- **Stream for human-facing output** with `generate_text_stream` or `chat_stream`; the content is identical, only the timing changes.
- **Errors come through `WMLClientError` / `ApiRequestFailure`,** and the SDK refreshes IAM tokens for you — you never manage bearer-token expiry.
- **Reach for `ChatWatsonx`** when watsonx.ai is one swappable component inside a LangChain application.

---

## Further reading

- [ibm-watsonx-ai SDK documentation](https://ibm.github.io/watsonx-ai-python-sdk/) — full reference for `Credentials`, `ModelInference`, and parameter metanames.
- [ModelInference API reference](https://ibm.github.io/watsonx-ai-python-sdk/fm_model_inference.html) — `generate_text`, `generate`, `chat`, and the streaming variants.
- [IBM watsonx.ai product documentation](https://www.ibm.com/products/watsonx-ai) — foundation models, regions, and platform concepts.
- [langchain-ibm ChatWatsonx reference](https://python.langchain.com/docs/integrations/chat/ibm_watsonx/) — the LangChain chat integration, invoke and stream usage.
