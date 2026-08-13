# The NVIDIA AI Stack

*A Python engineer's map of NVIDIA's AI platform — NIM inference, NeMo Retriever, NeMo Guardrails, and Triton with TensorRT-LLM — and why the same code runs against the hosted API Catalog or your own self-hosted microservice.*

---

Say "NVIDIA" to most engineers and they picture GPUs and CUDA — silicon and drivers. But over the last few years NVIDIA has grown a full application layer on top of that silicon, and the striking thing for someone who writes Python for a living is how little new API surface you have to learn. The inference endpoints speak the OpenAI wire protocol. The retrieval and safety pieces ship as ordinary `pip`-installable packages. You can prototype against a hosted endpoint today and move the exact same code onto a container in your own cluster next quarter without rewriting your client.

This post is the opener for a short series on building LLM and agent applications on NVIDIA's stack **from Python**. Here I'll map the pieces, explain how they fit together, show the one snippet that proves "it's just the `openai` SDK pointed somewhere new," and lay out where the series goes. No CUDA required to follow along.

---

## The four layers you actually touch

NVIDIA's AI stack is large, but from an application engineer's seat it collapses to four concerns: **serve a model, retrieve context, keep it safe, and optimize for scale.** Each has a concrete product.

1. **NIM (NVIDIA Inference Microservices)** — containerized model microservices. Each NIM packages a model plus an optimized runtime and exposes an **OpenAI-compatible REST API**. This is your inference layer.
2. **NeMo Retriever** — a family of embedding and reranking NIMs. These are the retrieval building blocks for RAG: turn text into vectors, then reorder candidate passages by relevance.
3. **NeMo Guardrails** — an open-source Python package (`nemoguardrails`) for putting programmable safety and topic controls around a conversational app.
4. **Triton Inference Server + TensorRT-LLM** — the serving and optimization substrate underneath a self-hosted NIM. Triton is the inference server; TensorRT-LLM compiles models into optimized engines. You reach for these when you run models yourself and care about latency and throughput.

The mental model: **NIM is the front door for inference, NeMo pieces bolt on retrieval and safety, and Triton/TensorRT-LLM is the engine room** you only walk into when you host models.

---

## Why the Python story is different here

NVIDIA's inference layer made one decision that changes everything for a Python developer: **NIM exposes the OpenAI-compatible API.** A NIM's chat endpoint accepts the same request shape as `chat.completions.create` and returns the same response shape. That single choice means you do not need an NVIDIA-specific SDK to call an NVIDIA model. You have two clean options, and both are first-class:

- The **standard `openai` client**, pointed at an NVIDIA base URL.
- NVIDIA's official LangChain integration, **`langchain-nvidia-ai-endpoints`**, which gives you `ChatNVIDIA`, `NVIDIAEmbeddings`, and `NVIDIARerank`.

Compare that to platforms where you inherit a bespoke SDK, a bespoke auth scheme, and a bespoke response object — and where moving providers means a rewrite. Here, the skills you already have transfer directly.

---

## Hosted vs. self-hosted: the same code, two homes

There are two places a NIM can live, and the portability between them is the whole pitch.

**Hosted — the API Catalog at build.nvidia.com.** NVIDIA runs the models for you. You browse the catalog, grab an API key (it starts with `nvapi-`), and call the models over the internet at the base URL `https://integrate.api.nvidia.com/v1`. Zero infrastructure. Ideal for prototyping, evaluation, and low-to-moderate volume.

**Self-hosted — a NIM container in your environment.** You pull the NIM container and run it on your own GPUs, on-prem or in your cloud account. Now inference happens inside your security boundary — no prompt or document ever leaves your network — and you control capacity, versioning, and cost at scale.

The reason this matters: because both speak the OpenAI-compatible API, **the only thing that changes between them is the `base_url` and the key.** Your application logic, your prompts, your parsing — untouched.

| Dimension | Hosted (API Catalog) | Self-hosted (NIM container) |
|---|---|---|
| Infrastructure | None — NVIDIA runs it | Your GPUs, your ops |
| Where data goes | To NVIDIA's endpoint | Stays in your network |
| Base URL | `https://integrate.api.nvidia.com/v1` | Your service address, e.g. `http://localhost:8000/v1` |
| Auth | `nvapi-...` key | Typically none on a private endpoint (you secure the network) |
| Best for | Prototyping, evaluation, low volume | Data control, scale, latency tuning |
| Client code | `openai` / `ChatNVIDIA` | **Identical** — swap `base_url` |

**The gotcha:** "OpenAI-compatible" means the *protocol* matches, not that every model supports every option. Features like tool calling, structured outputs, or vision depend on the specific model behind the endpoint. Treat the OpenAI API as the contract for *how* you call, and always check the model's page in the catalog for *what* it supports.

---

## The proof: it's just the `openai` SDK, pointed at NVIDIA

Here is the whole idea in one file. Install the standard client, point it at NVIDIA, make one chat call. There is nothing NVIDIA-specific in the code except the base URL.

```bash
pip install openai
export NVIDIA_API_KEY="nvapi-..."   # from build.nvidia.com
```

```python
import os
from openai import OpenAI

# The ONLY NVIDIA-specific lines: the base_url and the key.
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)

response = client.chat.completions.create(
    model="meta/llama-3.1-8b-instruct",  # pick any model id from the catalog
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "In one sentence, what is an NVIDIA NIM?"},
    ],
    temperature=0.2,
)

print(response.choices[0].message.content)
```

That's it. The `model` string is the model's id as listed on build.nvidia.com; everything else is the ordinary OpenAI Python SDK you may already use daily. Streaming (`stream=True`), temperature, max tokens — all the familiar parameters carry over because the wire format is the same.

**The gotcha:** the base URL includes the `/v1` suffix and is `integrate.api.nvidia.com` — not the `build.nvidia.com` web catalog, which is the browsing UI, not the inference endpoint. Keep your `nvapi-...` key in an environment variable, never in source, and rotate it if it leaks. When you later move to a self-hosted NIM, you change only the `base_url` (and usually drop the key) — this exact call keeps working.

---

## The same call through LangChain

If your app lives in the LangChain ecosystem, NVIDIA's official integration gives you the identical capability as a chat model object. Same endpoint underneath, same portability between hosted and self-hosted.

```bash
pip install langchain-nvidia-ai-endpoints
```

```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# Reads NVIDIA_API_KEY from the environment; defaults to the hosted catalog.
llm = ChatNVIDIA(model="meta/llama-3.1-8b-instruct", temperature=0.2)
print(llm.invoke("In one sentence, what is an NVIDIA NIM?").content)
```

To target a self-hosted NIM, pass `base_url="http://localhost:8000/v1"` to `ChatNVIDIA` instead — same pattern as the raw client. The same package also ships `NVIDIAEmbeddings` and `NVIDIARerank`, which is exactly what we'll use when we get to retrieval.

**The gotcha:** `ChatNVIDIA` is a real, maintained integration, but LangChain's surface shifts between releases. Pin the package version in your project and confirm constructor kwargs against the current `langchain-nvidia-ai-endpoints` docs rather than trusting a snippet's exact argument names — the *shape* here is stable, individual kwargs less so.

---

## How the layers connect in a real app

Put the pieces in motion and a production application threads them together like this:

- A user message arrives. **NeMo Guardrails** inspects it first — is it on-topic, is it safe? — before any model runs.
- If the app is retrieval-augmented, **NeMo Retriever** embeds the query, a vector store returns candidate passages, and a reranker NIM reorders them so the most relevant context lands in the prompt.
- The grounded prompt goes to a **chat NIM** — hosted or self-hosted — for generation.
- Guardrails checks the *output* too, before it reaches the user.
- Under heavy load, that chat NIM is a container backed by **Triton + TensorRT-LLM**, tuned for your latency and throughput targets.

Every one of those interactions, from your Python code's point of view, is either an OpenAI-style HTTP call or a method on a `pip`-installed package. That uniformity is the reason the stack is pleasant to build on.

---

## Where this series goes

Eight stops, each building on the last. This post is the map; the rest are the territory.

1. **The NVIDIA AI Stack** (this post) — the layers, hosted vs. self-hosted, and the one snippet that proves it's the `openai` SDK.
2. **Calling a NIM** — chat completions in depth: streaming, parameters, error handling, and the `ChatNVIDIA` equivalent.
3. **Tool calling** — letting a NIM model invoke your Python functions through the OpenAI tool-calling protocol.
4. **Embeddings and reranking with NeMo Retriever** — `NVIDIAEmbeddings` and `NVIDIARerank`, and why a reranker sharply improves retrieval quality.
5. **Building RAG** — wiring retrieval, reranking, and generation into a grounded question-answering app.
6. **Safety with NeMo Guardrails** — `RailsConfig`, `LLMRails`, and Colang to constrain topics and block unsafe input and output.
7. **Self-hosting and optimization** — running a NIM container, and what Triton and TensorRT-LLM do underneath to serve models fast.
8. **Production** — observability, cost, versioning, and the switch from hosted to self-hosted without touching application code.

---

## Key takeaways

- **NIM is the inference front door**, and it speaks the OpenAI-compatible API — so you call NVIDIA models with the standard `openai` client or `ChatNVIDIA`, no bespoke SDK required.
- **Hosted and self-hosted are the same code.** The API Catalog at `https://integrate.api.nvidia.com/v1` and a self-hosted NIM differ only in `base_url` and key; your app logic is portable between them.
- **The stack maps to four concerns**: NIM (serve), NeMo Retriever (retrieve), NeMo Guardrails (keep safe), Triton + TensorRT-LLM (optimize) — and each meets you as HTTP or a `pip` package.
- **"OpenAI-compatible" is about the protocol, not the feature set** — confirm tool calling, structured output, or vision support on each model's catalog page.
- **Self-hosting buys data control and scale** without a rewrite, which is the whole reason the portability guarantee matters.

Next in the series: calling a NIM in depth — streaming, parameters, and turning that one-shot snippet into something you'd ship.

---

## Further reading

- [NVIDIA NIM documentation](https://docs.nvidia.com/nim/) — the microservices reference: containers, the OpenAI-compatible API, deployment.
- [NVIDIA API Catalog (build.nvidia.com)](https://build.nvidia.com/) — browse models, grab an `nvapi-...` key, and try endpoints in the browser.
- [`langchain-nvidia-ai-endpoints` on PyPI](https://pypi.org/project/langchain-nvidia-ai-endpoints/) — the official LangChain integration (`ChatNVIDIA`, `NVIDIAEmbeddings`, `NVIDIARerank`).
- [`langchain-nvidia-ai-endpoints` source (GitHub)](https://github.com/langchain-ai/langchain-nvidia) — code, examples, and issue tracker.
- [NVIDIA NeMo documentation](https://docs.nvidia.com/nemo/) — Retriever, Guardrails, and the broader NeMo platform.
- [NeMo Guardrails (GitHub)](https://github.com/NVIDIA/NeMo-Guardrails) — the open-source `nemoguardrails` package, Colang, and configuration guides.
- [Triton Inference Server](https://docs.nvidia.com/deeplearning/triton-inference-server/) and [TensorRT-LLM](https://docs.nvidia.com/tensorrt-llm/) — the serving and optimization layers underneath self-hosted NIMs.
