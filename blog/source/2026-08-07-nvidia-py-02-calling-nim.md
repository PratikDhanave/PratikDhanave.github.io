# Calling NIM from Python

*Your first real NVIDIA NIM calls in Python, two idiomatic ways: the plain OpenAI SDK pointed at NVIDIA's endpoint, and the official LangChain integration — with error handling, streaming, and the one change that makes the same code run against a self-hosted model.*

---

NVIDIA NIM (NVIDIA Inference Microservices) exposes large language models behind an **OpenAI-compatible REST API**. That single design decision is the reason this post is short: you do not learn a bespoke SDK. You reuse the same request shape you already know from `chat.completions.create`, and you point it at NVIDIA's endpoint instead of OpenAI's.

There are two paths worth knowing, and this post walks both end to end:

1. **The `openai` SDK, pointed at NVIDIA.** Fewest dependencies, full control over the request, and typed exceptions you can catch precisely.
2. **The official `langchain-nvidia-ai-endpoints` package.** The `ChatNVIDIA` chat model, for when you want to drop NIM into a LangChain chain, retriever, or agent and keep the surrounding ecosystem.

Both talk to the same models. The deciding factor is what surrounds the call, not the call itself. We will finish on the property that makes NIM worth the trouble: **portability** — moving from NVIDIA's hosted catalog to a self-hosted NIM container is a one-line change.

---

## Getting a key and finding a model

Everything below assumes two things.

First, an API key. Create one at [build.nvidia.com](https://build.nvidia.com) — keys are prefixed `nvapi-`. Put it in an environment variable rather than a source file:

```bash
export NVIDIA_API_KEY="nvapi-..."
```

Second, a model id. NIM model ids are **catalog strings** like `meta/llama-3.1-8b-instruct`, not friendly aliases. The exact set of available ids and their spelling changes over time, so treat any id in this post as an example and confirm the current one in the model catalog on [build.nvidia.com](https://build.nvidia.com) before you run.

```bash
pip install openai langchain-nvidia-ai-endpoints
```

---

## 1. The OpenAI SDK, pointed at NVIDIA

The `openai` Python package does not hardcode OpenAI's URL. Construct the client with `base_url` set to NVIDIA's integration endpoint and `api_key` set to your `nvapi-` key, and every method on the client now talks to NIM.

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)

resp = client.chat.completions.create(
    model="meta/llama-3.1-8b-instruct",  # confirm the id in the catalog
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Explain what an inference microservice is in two sentences."},
    ],
    temperature=0.2,
    max_tokens=256,
    stream=False,
)

print(resp.choices[0].message.content)
```

The response object is the standard chat-completion shape. The generated text lives at `resp.choices[0].message.content`. There can be more than one choice if you ask for several completions, but with the default you read index `0`.

**The gotcha:** `base_url` must end in `/v1`. The path segment is part of the OpenAI-compatible contract, and leaving it off (`https://integrate.api.nvidia.com`) sends your request to a route that does not exist — you get a 404 that looks like an outage but is really a URL typo.

### Reading token usage

Every non-streaming response carries a `usage` object. Read it to track cost and to catch prompts that are quietly ballooning.

```python
usage = resp.usage
print("prompt tokens:    ", usage.prompt_tokens)
print("completion tokens:", usage.completion_tokens)
print("total tokens:     ", usage.total_tokens)
```

Those three fields — `prompt_tokens`, `completion_tokens`, `total_tokens` — are the whole story for a single call. Sum `total_tokens` across a session and you have a running meter.

### Error handling with typed exceptions

The `openai` package raises a **hierarchy of typed exceptions**, all subclasses of `openai.APIError`. Catching them by type lets you react differently to a rate limit than to a bad request. The ones you will meet most often:

- `openai.APIConnectionError` — the request never reached the server (DNS, TLS, network). It has a `.__cause__` with the underlying error.
- `openai.APITimeoutError` — a subclass of the connection error, raised when the request exceeds the configured timeout.
- `openai.RateLimitError` — HTTP 429; you are sending too fast. Back off and retry.
- `openai.AuthenticationError` — HTTP 401; a missing or wrong `nvapi-` key.
- `openai.BadRequestError` — HTTP 400; a malformed request, e.g. an unknown model id or an oversized prompt.
- `openai.APIStatusError` — the base class for any non-2xx response, carrying `.status_code` and `.response`. Catch it last as a fallback.

```python
import openai

def ask(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        return resp.choices[0].message.content
    except openai.AuthenticationError:
        raise SystemExit("Check NVIDIA_API_KEY — the server rejected the credential.")
    except openai.RateLimitError:
        raise RuntimeError("Rate limited (429). Slow down or add backoff.")
    except openai.BadRequestError as e:
        raise RuntimeError(f"Bad request (400): {e}")
    except openai.APIStatusError as e:
        raise RuntimeError(f"Server returned {e.status_code}: {e.response}")
    except openai.APIConnectionError as e:
        raise RuntimeError(f"Could not reach the endpoint: {e.__cause__}")
```

Order matters: the specific exceptions come first, `APIStatusError` and `APIConnectionError` last, because the specific ones are subclasses and Python matches the first `except` that fits.

**The gotcha:** the client's retry and timeout behavior is **configurable — so configure it** rather than assuming the defaults suit your workload. The SDK retries certain errors (connection errors, 429s, 5xx) a small number of times with backoff. You can raise or lower that with `max_retries`, and set a request deadline with `timeout`, either on the whole client or per call.

```python
from openai import OpenAI

# Client-wide defaults.
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    max_retries=4,
    timeout=30.0,  # seconds
)

# Or override for one call that you know is slow.
resp = client.with_options(timeout=120.0).chat.completions.create(
    model="meta/llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Write a long essay on caching."}],
    max_tokens=2048,
)
```

### Streaming: guard the None deltas

For an interactive UI you want tokens as they arrive, not one block at the end. Pass `stream=True` and iterate. Each chunk carries a partial message on `chunk.choices[0].delta`, and the new text (if any) is at `.delta.content`.

```python
stream = client.chat.completions.create(
    model="meta/llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Count slowly from one to five."}],
    max_tokens=128,
    stream=True,
)

pieces = []
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:                     # may be None on some chunks — skip those
        pieces.append(delta)
        print(delta, end="", flush=True)
print()

full_text = "".join(pieces)
```

**The gotcha:** `chunk.choices[0].delta.content` is often `None`, not just an empty string. The first chunk may carry only the assistant role, and the final chunk (the one that signals completion) carries no text at all. A bare `pieces.append(delta)` without the `if delta:` guard appends `None` and blows up your `"".join(...)`. Always check truthiness before using the delta.

One more streaming note: when you stream over the OpenAI-compatible endpoint, the usage totals are not attached to the intermediate content chunks the way they are on a non-streaming response. If you need exact token accounting, prefer a non-streaming call, or count locally — do not assume `usage` is populated mid-stream.

---

## 2. The official LangChain integration: ChatNVIDIA

NVIDIA maintains `langchain-nvidia-ai-endpoints`, which exposes NIM as a first-class LangChain chat model called `ChatNVIDIA`. If your application is already built on LangChain — chains, retrievers, output parsers, agents — this is the path that fits, because `ChatNVIDIA` behaves like any other LangChain chat model.

It reads `NVIDIA_API_KEY` from the environment automatically, so construction is just the model id.

```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA

llm = ChatNVIDIA(
    model="meta/llama-3.1-8b-instruct",  # confirm the id in the catalog
    temperature=0.2,
    max_tokens=256,
)

result = llm.invoke("Explain what an inference microservice is in two sentences.")
print(result.content)
```

`invoke` returns an `AIMessage`; the text is on `.content`. That is the same return type you get from any LangChain chat model, which is the whole point — swap `ChatNVIDIA` in wherever a chat model is expected and the rest of the chain does not change.

### Passing structured messages

Instead of a bare string you can pass a list of messages, either as LangChain message objects or as role/content tuples. Both are accepted.

```python
from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content="You are a concise assistant."),
    HumanMessage(content="Name three benefits of an OpenAI-compatible API."),
]
print(llm.invoke(messages).content)

# Equivalent, using tuples:
print(llm.invoke([
    ("system", "You are a concise assistant."),
    ("human", "Name three benefits of an OpenAI-compatible API."),
]).content)
```

### Streaming with ChatNVIDIA

Streaming uses the standard LangChain `.stream(...)` method, which yields message chunks. Concatenate `.content` as they arrive.

```python
pieces = []
for chunk in llm.stream("Count slowly from one to five."):
    if chunk.content:            # guard here too — chunks can be empty
        pieces.append(chunk.content)
        print(chunk.content, end="", flush=True)
print()

full_text = "".join(pieces)
```

The LangChain layer already smooths over empty chunks better than the raw client, but keeping the `if chunk.content:` guard costs nothing and keeps the two code paths symmetric.

### When to reach for which

| You want | Use | Why |
|---|---|---|
| Fewest dependencies, full request control | `openai` client | One package, typed exceptions, raw `usage` |
| Precise error handling by HTTP status | `openai` client | `RateLimitError`, `APIStatusError`, etc. |
| Drop NIM into an existing LangChain app | `ChatNVIDIA` | Behaves like any LangChain chat model |
| Chains, retrievers, agents, output parsers | `ChatNVIDIA` | Composes with the LangChain ecosystem |
| A thin script or microservice | `openai` client | Nothing to learn, nothing extra to ship |

There is no wrong choice here — they hit the same models. Pick the raw client when the LLM call is the whole program, and `ChatNVIDIA` when the call is one node in a larger LangChain graph.

---

## 3. Portability: the same code, a self-hosted NIM

The reason NIM's OpenAI compatibility matters is that it decouples your code from *where* the model runs. NVIDIA ships NIM as a container you can run on your own GPU. That container serves the **same OpenAI-compatible API** on its own host and port. To move your application from the hosted catalog to your own hardware, you change one thing: the `base_url`.

```python
import os
from openai import OpenAI

# Hosted NVIDIA catalog:
# base_url = "https://integrate.api.nvidia.com/v1"

# Self-hosted NIM container on your network:
base_url = os.environ.get("NIM_BASE_URL", "http://localhost:8000/v1")

client = OpenAI(
    base_url=base_url,
    api_key=os.environ.get("NVIDIA_API_KEY", "not-needed-for-local"),
)

resp = client.chat.completions.create(
    model="meta/llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Ping."}],
    max_tokens=32,
)
print(resp.choices[0].message.content)
```

`ChatNVIDIA` supports the same move through its `base_url` parameter:

```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA

llm = ChatNVIDIA(
    base_url="http://localhost:8000/v1",
    model="meta/llama-3.1-8b-instruct",
)
```

**The gotcha:** a self-hosted NIM may not need an API key at all — access is often controlled by the network (a private VPC, a Kubernetes service, a firewall) rather than a per-request credential. The `openai` client still insists on *some* `api_key` value being present, so pass a harmless placeholder. Never do the reverse: do not hardcode your real `nvapi-` key to reach a local endpoint, and never commit any key. Keep it in an environment variable or a secret store, and let the local URL fall back to no real credential.

---

## A complete, runnable example

Putting the OpenAI-client pieces together: non-streaming with usage, error handling, then streaming — one self-contained script.

```python
import os
import openai
from openai import OpenAI

MODEL = "meta/llama-3.1-8b-instruct"  # confirm in the catalog

client = OpenAI(
    base_url=os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=os.environ.get("NVIDIA_API_KEY", "not-needed-for-local"),
    max_retries=3,
    timeout=30.0,
)


def complete(prompt: str) -> None:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
    except openai.RateLimitError:
        print("Rate limited (429) — back off and retry.")
        return
    except openai.APIStatusError as e:
        print(f"Server error {e.status_code}: {e.response}")
        return
    except openai.APIConnectionError as e:
        print(f"Connection failed: {e.__cause__}")
        return

    print(resp.choices[0].message.content)
    u = resp.usage
    print(f"[tokens] prompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens}")


def stream(prompt: str) -> None:
    events = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        stream=True,
    )
    for chunk in events:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()


if __name__ == "__main__":
    complete("Give one reason OpenAI-compatible APIs simplify vendor migration.")
    stream("Now say the same thing as a haiku.")
```

Run it against the hosted catalog by setting `NVIDIA_API_KEY`, or against a local container by setting `NIM_BASE_URL` to your NIM's `/v1` URL. The code does not change.

---

## Key takeaways

- **NIM is OpenAI-compatible**, so the plain `openai` client works — set `base_url` to `https://integrate.api.nvidia.com/v1` and `api_key` to your `nvapi-` key.
- **Read `resp.choices[0].message.content` for text and `resp.usage` for `prompt_tokens` / `completion_tokens` / `total_tokens`.** Usage is reliable on non-streaming calls.
- **Streaming deltas can be `None`.** Guard `if chunk.choices[0].delta.content:` before using them, or the final/role-only chunks will break your accumulator.
- **Catch typed exceptions** — `RateLimitError`, `AuthenticationError`, `BadRequestError`, and the `APIStatusError` / `APIConnectionError` base classes — and set `max_retries` and `timeout` deliberately instead of trusting defaults.
- **`ChatNVIDIA` is the LangChain-native path** — `invoke` and `stream` behave like any LangChain chat model. Prefer it inside chains and agents; prefer the raw client for thin scripts.
- **Portability is a one-line change.** Point `base_url` at a self-hosted NIM to run the identical code on your own GPU — and remember a local NIM may need no key, only network access.

---

## Further reading

- [NVIDIA NIM for LLMs — API reference](https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html)
- [build.nvidia.com — model catalog and API keys](https://build.nvidia.com)
- [openai-python — the official OpenAI Python SDK](https://github.com/openai/openai-python)
- [langchain-nvidia-ai-endpoints on PyPI](https://pypi.org/project/langchain-nvidia-ai-endpoints/)
- [ChatNVIDIA integration docs (LangChain)](https://python.langchain.com/docs/integrations/chat/nvidia_ai_endpoints/)
