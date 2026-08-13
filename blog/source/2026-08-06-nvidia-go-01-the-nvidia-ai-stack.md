# The NVIDIA AI Stack

*A field map of NVIDIA's AI platform for a Go engineer — where NIM, the API Catalog, NeMo Retriever, NeMo Guardrails, Triton, and TensorRT-LLM each fit, and why a Go app talks to all of it over plain OpenAI-compatible HTTP.*

---

NVIDIA does not ship a Go SDK. When I first went looking for one, that felt like a wall. It turned out to be the opposite — a door. NVIDIA's inference layer speaks an **OpenAI-compatible REST API**, so a Go program reaches it with nothing but `net/http` and a bearer token. No vendor SDK to vendor, no generated client to babysit, no waiting for someone to port a Python library. You write the HTTP calls yourself, and you own every byte on the wire.

This post opens a series on building LLM and agent applications on NVIDIA's stack **from Go**. Before we write a real client (next post), it is worth drawing the map: NVIDIA ships a lot of named products, and most of the confusion I see comes from not knowing which piece an application engineer actually calls versus which piece an ops or ML team stands up. Let's separate those cleanly.

---

## The one idea that makes this a Go story

NVIDIA's inference offering is delivered as **NIM** — NVIDIA Inference Microservices. A NIM is a containerized model packaged as a microservice, and the interface it exposes is the important part: OpenAI-compatible REST endpoints like `/v1/chat/completions` and `/v1/embeddings`.

"OpenAI-compatible" is a wire-format contract, not a company relationship. It means the request body, the response shape, the streaming format (server-sent events), and the auth header all match the shape the broader ecosystem already standardized on. For a Go developer that translates to a very short list of things you have to do:

- POST JSON to a base URL.
- Send `Authorization: Bearer <key>`.
- Decode the JSON response (or read an SSE stream).

That is the entire integration surface. Here is the proof-of-concept — just an `http.Client` pointed at the hosted catalog with the key pulled from the environment. It doesn't call anything yet; it establishes the shape everything else in the series builds on:

```go
package nvidia

import (
	"fmt"
	"net/http"
	"os"
	"time"
)

// Client is a thin wrapper over net/http. There is no NVIDIA Go SDK —
// this is all you need, because NIM endpoints are OpenAI-compatible REST.
type Client struct {
	baseURL string
	apiKey  string
	http    *http.Client
}

func NewClient() (*Client, error) {
	key := os.Getenv("NVIDIA_API_KEY") // keys look like "nvapi-..."
	if key == "" {
		return nil, fmt.Errorf("NVIDIA_API_KEY is not set")
	}
	return &Client{
		baseURL: "https://integrate.api.nvidia.com/v1", // hosted API Catalog
		apiKey:  key,
		http:    &http.Client{Timeout: 60 * time.Second},
	}, nil
}
```

**The gotcha:** the key never belongs in source. Read it from the environment (or a secret manager) as above, and keep the `nvapi-` value out of logs, error strings, and request dumps. The base URL is the only thing you will swap when you move from the hosted catalog to a NIM running on your own GPUs — the code that builds requests and parses responses stays byte-for-byte identical. That portability is the whole pitch, and we'll come back to it.

---

## The API Catalog: try before you host

The fastest way to start is the **hosted API Catalog** at [build.nvidia.com](https://build.nvidia.com). NVIDIA runs a large menu of models — open-weight LLMs, embedding models, rerankers, vision and speech models — behind a single hosted endpoint. You sign in, generate an API key of the form `nvapi-...`, and point your client at:

```
https://integrate.api.nvidia.com/v1
```

Every model on the catalog is addressed by a string `model` field in the request body, and the endpoints are the same OpenAI-compatible routes a self-hosted NIM exposes. So the catalog is not a separate API you have to learn — it is a **managed, multi-tenant host for the exact same interface** you'd get by running the container yourself. That is what makes it perfect for prototyping: you write your Go client once against the catalog, confirm the app works, and later decide where the inference should actually run.

I treat the catalog as the development and evaluation surface. It removes every ops question so you can focus on the application: prompt design, tool schemas, retrieval quality. When those are right, hosting becomes a deployment decision rather than a rewrite.

---

## Self-hosted NIM: same interface, your GPUs

The other end of the spectrum is running a NIM yourself. NVIDIA distributes NIMs as containers you pull and run on your own NVIDIA-GPU infrastructure — a workstation, a server, or a Kubernetes cluster. Once a NIM is running, it exposes the *same* OpenAI-compatible endpoints locally, e.g. `http://localhost:8000/v1/chat/completions` (check the current NIM docs for the exact port and container arguments, which vary by model).

Because the interface matches, moving your Go app from hosted to self-hosted is a **one-line change** — swap the `baseURL`. Everything about request building, streaming, and response parsing carries over unchanged. This is the payoff of building against a standard wire format instead of a proprietary SDK.

So when do you choose which? Here is how I weigh it:

| Dimension | Hosted API Catalog | Self-hosted NIM |
|---|---|---|
| Ops burden | Zero — NVIDIA runs it | You run the GPUs and the container |
| Data residency | Requests leave your network | Data stays inside your boundary |
| Latency | Network round-trip to NVIDIA | Local / same-VPC, tunable |
| Cost model | Pay per use / catalog terms | Your hardware + running cost |
| Best for | Prototyping, spiky or low volume | Steady volume, privacy, control |

Neither is "better." The catalog wins on speed-to-first-call and zero operations; self-hosting wins on data control, predictable latency, and cost at scale. Because your Go code doesn't care which one it's talking to, you get to defer and revisit this decision without touching the application.

**The gotcha:** OpenAI-compatible means *shape*-compatible, not *feature*-identical. Different models expose different capabilities — some support tool calling or JSON-structured output, some don't; parameter ranges and defaults differ; and a self-hosted NIM's exact routes and options depend on its version. Don't assume a body that worked against one model works verbatim against another. Confirm each model's supported parameters in the model card and the NIM docs rather than porting a request blindly.

---

## NeMo Retriever: the RAG building blocks

Once you want your app grounded in your own documents, you need two things beyond a chat model: **embeddings** (to turn text into vectors for similarity search) and **reranking** (to reorder candidate passages by true relevance to the query). NVIDIA packages both as part of **NeMo Retriever**, delivered — like everything else here — as NIMs.

For a Go developer that means two more OpenAI-compatible calls:

- An **embedding NIM** exposes `/v1/embeddings`; you send text and get back vectors to store in your vector database of choice.
- A **reranking NIM** takes a query plus candidate passages and returns relevance scores, so you can keep only the best few before sending them to the LLM.

NeMo is NVIDIA's broader platform for customizing and deploying models; Retriever is the slice of it aimed squarely at retrieval-augmented generation. The mental model to carry forward: RAG on this stack is **three HTTP calls from Go** — embed, (optionally) rerank, then chat with the retrieved context stitched into the prompt. We'll build exactly that later in the series, so I'll keep the details for those posts. The point here is that retrieval is not a different kind of integration — it's the same REST pattern with different endpoints.

---

## NeMo Guardrails: safety that lives outside Go

**NeMo Guardrails** is NVIDIA's open-source toolkit for putting programmable guardrails around an LLM application — input/output filtering, topic boundaries, blocking unsafe or off-policy responses, and shaping dialog flow. It is honest to say up front: it is a **Python library**, not a Go one.

That doesn't put it out of reach; it changes *where it sits*. There are two sane ways a Go app benefits from it:

1. Run Guardrails as a **service** in front of or beside your model, and have your Go app call that service's endpoint — the guardrail logic lives in Python, your app just makes an HTTP call.
2. Treat guardrails as an **ops/platform concern** owned by a Python service in your architecture, while your Go code focuses on the application logic.

I'll cover guardrails at the conceptual and integration level in this series — how to reason about where safety enforcement belongs — rather than pretending there's a native Go path. When in doubt about capabilities or configuration, the NeMo Guardrails docs are the source of truth.

**The gotcha:** don't confuse "no Go SDK" with "can't use it from Go." The pattern for every Python-side piece in this stack is the same — stand it up as a service, then call its endpoint over HTTP. Your Go application stays a thin, fast client; the heavier Python and ops machinery lives behind an endpoint.

---

## Triton and TensorRT-LLM: the serving and speed layer

Two more names round out the stack, and both live firmly on the ops/ML side:

- **Triton Inference Server** is NVIDIA's general-purpose model server. It serves models over HTTP and gRPC and handles concerns like batching, multiple model backends, and concurrent execution. NIMs build on this serving foundation; you configure Triton on the ops side, and from Go you simply call the resulting endpoint.
- **TensorRT-LLM** is an optimization library for LLM inference. It applies techniques like quantization (smaller, faster weights), in-flight (continuous) batching, and paged KV-cache management to raise throughput and lower latency on NVIDIA GPUs. It is a build/serving-time concern — it shapes *how fast and how cheap* your self-hosted inference runs, not how your Go client calls it.

For an application engineer, the key framing is: **these two determine the performance of the endpoint, not its interface.** Whether a model is served through a heavily TensorRT-LLM–optimized Triton deployment or the hosted catalog, your Go code sends the same request. When we reach self-hosting and optimization in the series, I'll treat these at the conceptual and ops level — enough to make good deployment decisions and to talk fluently with the team running the GPUs — because the Go side genuinely doesn't change.

---

## How the layers stack up

Reading the stack from the application down:

- **Your Go app** — plain `net/http`, holds the `nvapi-` key, builds requests, parses responses.
- **The endpoint** — hosted API Catalog (`integrate.api.nvidia.com`) *or* a self-hosted NIM, same OpenAI-compatible routes.
- **NeMo Retriever** — embedding and reranking NIMs for RAG, same REST pattern.
- **NeMo Guardrails** — Python/open-source safety, reached as a service.
- **Triton + TensorRT-LLM** — the serving and optimization layer beneath a self-hosted NIM; ops-side, invisible to your client code.

Everything the Go application touches is the top two rows. Everything below is a deployment and platform concern that changes performance and control, never the wire format.

---

## What the series will build

Here's the road ahead. Each post is a working Go program against real NVIDIA endpoints:

1. **The NVIDIA AI stack** (this post) — the map and the "it's just OpenAI-compatible HTTP" thesis.
2. **Calling NIM from Go** — a real, robust chat client: request/response types, streaming over SSE, errors, timeouts, retries.
3. **Tool calling** — letting the model call your Go functions via the tool-calling fields in the chat API.
4. **Embeddings and reranking** — using NeMo Retriever's endpoints from Go.
5. **RAG end to end** — embed, rerank, retrieve, and ground a chat response, wired to a vector store.
6. **Guardrails** — where safety enforcement belongs and how a Go app integrates NeMo Guardrails as a service.
7. **Self-hosting and optimization** — running a NIM on your own GPUs, and the ops-level story of Triton and TensorRT-LLM.
8. **Production** — configuration, observability, cost and latency management, and the portability payoff in practice.

---

## Key takeaways

- **There is no NVIDIA Go SDK — and you don't need one.** NIM endpoints are OpenAI-compatible REST, so `net/http` plus a bearer token is the whole integration surface.
- **One interface, two hosting choices.** The hosted API Catalog (`integrate.api.nvidia.com/v1`) and a self-hosted NIM expose the same routes; moving between them is a base-URL change, not a rewrite.
- **Hosted vs self-hosted is a real trade-off.** Zero-ops and speed-to-first-call versus data residency, latency control, and cost at scale — and your Go code stays identical either way.
- **RAG is the same pattern with new endpoints.** NeMo Retriever's embedding and reranking NIMs are more OpenAI-style HTTP calls, not a different integration model.
- **Some pieces are Python/ops-side — reach them as services.** NeMo Guardrails is open-source Python; Triton and TensorRT-LLM shape endpoint performance, not its interface. Call the resulting endpoint from Go and keep the heavy machinery behind it.

The mindset for the rest of this series: your Go app is a thin, fast, portable client. NVIDIA's stack does the heavy lifting behind a standard wire format — and because that format is open, you're never locked into a single host or a single vendor's SDK.

---

## Further reading

- [NVIDIA NIM documentation](https://docs.nvidia.com/nim/) — reference for the inference microservices, endpoints, and deployment.
- [NVIDIA API Catalog (build.nvidia.com)](https://build.nvidia.com) — try models and generate an `nvapi-` API key.
- [NVIDIA NeMo documentation](https://docs.nvidia.com/nemo/) — the platform for customizing and deploying models, including NeMo Retriever.
- [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) — the open-source Python toolkit for programmable guardrails.
- [Triton Inference Server](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/) — serving models over HTTP/gRPC.
- [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) — LLM inference optimization for NVIDIA GPUs.
