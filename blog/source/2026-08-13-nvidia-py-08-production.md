# Production on the NVIDIA Stack

*Taking an NVIDIA-stack LLM system from a working prototype to something you trust in production — reliability, cost and throughput, observability, and security — all from Python, with the OpenAI-compatible surface keeping the code stable whether you burst to the API Catalog or run your own NIM.*

---

Every earlier post in this series built one capability and stopped at "it works." This one is about the gap between *works on my laptop* and *works at 2 a.m. under load with a dashboard someone is paging off of.* The good news, and the through-line of the whole series, is that going to production does **not** mean rewriting anything. The same `openai` client, the same `resp.usage` accounting, the same request shape you have used since post 2 are what you harden here. Production is mostly wrapping calls you already have in retries, health checks, metrics, and secrets.

We will walk the four production concerns — reliability, cost/throughput, observability, security — with Python where Python earns it, then finish with a checklist and a FastAPI endpoint that ties the series together.

---

## Hosted, self-hosted, and the hybrid in between

Post 7 self-hosted a NIM on Triton with TensorRT-LLM. The choice between that and the hosted API Catalog is the first production decision, and it is a genuine trade, not a default:

| Dimension | Hosted (API Catalog) | Self-hosted NIM/Triton |
|---|---|---|
| Cost model | Per-token / per-request | GPU-hours (you pay for the box, busy or idle) |
| Control | NVIDIA sets versions, limits | You pin versions, tune batching, own the SLA |
| Data path | Prompts leave your network | Prompts stay inside your VPC |
| Scaling | Elastic, someone else's problem | Your capacity planning |

The mature answer is usually **hybrid**: run steady-state traffic on a self-hosted NIM you have sized and optimized, and **burst** overflow to the hosted API Catalog when demand spikes past your GPU capacity. Because both speak the OpenAI wire protocol, "route to the other backend" is a change of `base_url` and key — not a change of code.

```python
from openai import OpenAI

SELF_HOSTED = OpenAI(base_url="http://nim.internal:8000/v1", api_key="not-used")
HOSTED = OpenAI(base_url="https://integrate.api.nvidia.com/v1",
                api_key=os.environ["NVIDIA_API_KEY"])  # nvapi-...

def pick_client(self_hosted_healthy: bool) -> OpenAI:
    return SELF_HOSTED if self_hosted_healthy else HOSTED
```

**The gotcha:** pin your model version and container tag. Deploying `:latest` — or leaving a hosted model id unversioned — means the model can change behavior *under you* between deploys, and your prompts and guardrails were tuned against the old one. Pin the NIM image tag and record the exact model id you tested; treat a version bump as a code change that goes through the same eval you would run for a prompt edit.

---

## Reliability: assume everything fails, briefly

Networks blip, GPUs restart, hosted endpoints rate-limit. Reliability is layering cheap defenses so a transient failure never reaches the user.

### Timeouts and the client's built-in retries

The `openai` client already retries — by default it retries certain failures (connection errors, `429`, `5xx`) with exponential backoff. Make the policy explicit rather than inheriting defaults, and always set a timeout so a stuck socket cannot hang a request forever.

```python
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
    max_retries=4,      # client retries 429/5xx/connection errors with backoff
    timeout=30.0,       # seconds; a hung call fails fast instead of hanging
)
```

That covers the SDK's own calls. For *your* orchestration code — a whole RAG turn, a reranker call, a guardrails pass — wrap the unit in `tenacity` so a flaky step retries with jittered backoff instead of failing the request:

```python
from tenacity import (retry, stop_after_attempt, wait_exponential_jitter,
                      retry_if_exception_type)
from openai import APIConnectionError, RateLimitError, InternalServerError

@retry(
    retry=retry_if_exception_type(
        (APIConnectionError, RateLimitError, InternalServerError)),
    wait=wait_exponential_jitter(initial=1, max=20),
    stop=stop_after_attempt(4),
    reraise=True,
)
def generate(client: OpenAI, model: str, messages: list[dict]) -> str:
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content
```

Retry only *transient* exception types. Retrying a `400` (a malformed request) or a content-policy rejection just burns latency and money to fail the same way four times.

### Probe readiness before you route

Post 7 noted that a NIM exposes health endpoints. Use them: check readiness *before* sending a request to a self-hosted backend, so a container that is up but not yet serving does not eat real traffic.

```python
import httpx

def nim_ready(base: str = "http://nim.internal:8000", timeout: float = 2.0) -> bool:
    try:
        r = httpx.get(f"{base}/v1/health/ready", timeout=timeout)
        return r.status_code == 200
    except httpx.HTTPError:
        return False
```

### Graceful fallback

Now compose the pieces into a fallback chain: try the self-hosted NIM, fall back to the hosted API Catalog if it is unhealthy, and fall back to a cached or canned answer if *both* are unreachable. The user gets a degraded answer, never a stack trace.

```python
def answer(messages: list[dict], model: str) -> str:
    if nim_ready():
        try:
            return generate(SELF_HOSTED, model, messages)
        except Exception:
            log.warning("self-hosted NIM failed, falling back to hosted")
    try:
        return generate(HOSTED, model, messages)  # burst / disaster fallback
    except Exception:
        log.error("all live backends down, serving canned response")
        return "I can't reach the model right now. Please try again shortly."
```

**The gotcha:** an untested fallback path fails exactly when you need it. The `except` branch you never exercise is where the real outage happens — the hosted key expired, the fallback model id is wrong, the canned string got refactored away. Test the fallback deliberately: point the primary at a dead port in a staging run and confirm the chain degrades cleanly. A fallback you have never watched execute is a hope, not a safety net.

---

## Cost and throughput: two completely different meters

The most common production surprise is that **hosted and self-hosted bill on different axes**, so the optimization that helps one does nothing for the other.

### Hosted: count tokens

Hosted cost is a function of tokens, and every response tells you exactly how many it used. Log `resp.usage` (introduced in post 2) on every call so cost is observable, not a month-end shock.

```python
resp = client.chat.completions.create(model=model, messages=messages)
u = resp.usage  # prompt_tokens, completion_tokens, total_tokens
log.info("llm_call", extra={"model": model,
         "prompt_tokens": u.prompt_tokens,
         "completion_tokens": u.completion_tokens,
         "total_tokens": u.total_tokens})
```

The levers that lower this bill are prompt size (retrieval that fetches *fewer, better* passages — post 4's reranking directly reduces context tokens) and output length (`max_tokens`). Token accounting is what lets you attribute cost to a feature and decide whether that feature is worth it.

### Self-hosted: fill the GPU

Self-hosted cost is **GPU-hours**, flat, whether the GPU serves a thousand requests an hour or zero. There is no per-token meter — the box costs the same idling as it does saturated. That inverts the goal: instead of minimizing tokens, you **maximize utilization**. Triton's dynamic batching (post 7) groups concurrent requests into one GPU pass; higher throughput per GPU-hour is lower cost per request. Your capacity-planning job is to keep the GPU busy but not so saturated that latency spikes — and the only way to know where that line is is the metrics in the next section.

### Rate-limit yourself before the provider does

The hosted API Catalog enforces rate limits. Fire a burst of naive concurrent requests and you get `429`s — which your retries then dutifully re-send, making it worse. Cap concurrency on your side with an `asyncio.Semaphore` (or a token-bucket limiter for a strict rate ceiling):

```python
import asyncio
from openai import AsyncOpenAI

aclient = AsyncOpenAI(base_url="https://integrate.api.nvidia.com/v1",
                      api_key=os.environ["NVIDIA_API_KEY"])
sem = asyncio.Semaphore(8)  # at most 8 in-flight calls

async def bounded_generate(model: str, messages: list[dict]) -> str:
    async with sem:
        resp = await aclient.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content
```

**The gotcha:** hosted rate limits mean naive concurrency turns into a `429` storm, and self-hosted has the opposite failure — an idle GPU is pure sunk cost while a saturated one drops latency off a cliff. Capacity-plan with real Prometheus numbers (below), not intuition: size self-hosted GPU count to your steady-state utilization target, and cap client-side concurrency to stay under hosted limits.

---

## Observability: see the whole request

A production request on this stack is a *pipeline* — retrieve, rerank, guardrails, generate — and when it is slow or wrong you need to know *which stage*. Two feeds give you that: the server's own metrics and the ones you emit.

### Server-side Prometheus metrics

Both Triton and NIM expose **Prometheus** metrics out of the box. Triton publishes them on its metrics port (`8002`) at `/metrics` — GPU utilization, inference latency, and queue depth (how long requests wait before the GPU picks them up). Queue depth is your saturation signal: rising queue depth with flat GPU utilization means you need more replicas, not a bigger batch. Scrape these into Prometheus and alert on them.

### Your own structured logs and metrics

Server metrics tell you about the GPU; they cannot tell you that *your reranker* is the slow stage. Emit that yourself with the standard `logging` module and `prometheus_client`.

```python
import logging, time
from prometheus_client import Counter, Histogram, start_http_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ragapp")

STAGE_LATENCY = Histogram("rag_stage_seconds", "Per-stage latency", ["stage"])
REQUESTS = Counter("rag_requests_total", "Requests", ["outcome"])
TOKENS = Counter("rag_tokens_total", "Tokens billed", ["kind"])

start_http_server(9100)  # exposes /metrics for Prometheus to scrape
```

Now instrument each stage and carry a request id through so a single turn is traceable end to end across retrieve → rerank → guardrails → generate:

```python
import uuid

def handle(question: str) -> str:
    req_id = uuid.uuid4().hex[:8]
    try:
        for stage, fn in (("retrieve", retrieve), ("rerank", rerank),
                          ("guardrails", check_input), ("generate", run_llm)):
            t0 = time.perf_counter()
            result = fn(question)
            dt = time.perf_counter() - t0
            STAGE_LATENCY.labels(stage=stage).observe(dt)
            log.info("stage done", extra={"req_id": req_id, "stage": stage,
                                          "seconds": round(dt, 3)})
        REQUESTS.labels(outcome="ok").inc()
        return result
    except Exception:
        REQUESTS.labels(outcome="error").inc()
        log.exception("request failed", extra={"req_id": req_id})
        raise
```

With this in place a slow request is no longer a mystery: the histogram shows *which* stage's latency moved, and the `req_id` in the logs lets you replay that exact turn. Feed the same token counts from `resp.usage` into the `TOKENS` counter and your cost graph lives on the same dashboard as your latency graph.

---

## Security: keys, injection, and network scope

Three surfaces matter more in production than in a prototype.

**Keys belong in a secret manager, never in code.** You now hold two kinds: `nvapi-` keys for the hosted API Catalog, and NGC keys used to *pull* NIM container images. Neither goes in source, a Docker image layer, or a committed `.env`. Read them at runtime from a secret manager (AWS Secrets Manager, GCP Secret Manager, Vault, or your orchestrator's secret mount) and inject as environment variables the process reads once at startup.

```python
import os
api_key = os.environ["NVIDIA_API_KEY"]  # injected from the secret store, not baked in
if not api_key:
    raise RuntimeError("NVIDIA_API_KEY missing — refusing to start")
```

**Your injection surface grew.** Every capability the series added widened it: RAG (post 5) feeds retrieved documents into the prompt, tools (post 3) let the model trigger actions, and both can carry adversarial instructions from untrusted sources. This is exactly why the NeMo Guardrails pass from post 6 runs *in production, on every request* — not just in demos. Guardrails check both input (jailbreak and topic control) and output (leakage, unsafe content); they are a control you keep on, and one of the stages you trace above.

**Network-scope self-hosted endpoints.** A self-hosted NIM exposing an unauthenticated OpenAI-compatible API is an open model to anyone who can reach it. Bind it to a private subnet, put it behind an authenticated gateway, and never expose the raw inference or Triton metrics port (`8002`) to the public internet. The whole point of self-hosting was to keep data in your network — do not undo that with an open port.

---

## The production checklist

| Area | Ship-blocker check |
|---|---|
| Versions | Model id + NIM container tag pinned; no `:latest` |
| Timeouts | Every client call has an explicit `timeout` |
| Retries | `max_retries` set; `tenacity` on your own orchestration, transient errors only |
| Health | Readiness probe (`/v1/health/ready`) checked before routing |
| Fallback | Hosted-burst and canned-answer paths tested, not just written |
| Cost | `resp.usage` logged (hosted); GPU utilization tracked (self-hosted) |
| Concurrency | Client-side limiter/`Semaphore` under the hosted rate limit |
| Metrics | Triton/NIM Prometheus scraped; per-stage latency + tokens emitted |
| Tracing | Request id carried across retrieve → rerank → guardrails → generate |
| Secrets | `nvapi-`/NGC keys in a secret manager; startup fails if missing |
| Guardrails | NeMo Guardrails on every request, input and output |
| Network | Self-hosted endpoints private/authenticated; metrics port not public |

---

## Wrapping it in a FastAPI endpoint

Everything above composes into a single service. FastAPI exposes the pipeline over HTTP with a health route for your load balancer to probe.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="nvidia-stack-rag")

class Query(BaseModel):
    question: str

@app.get("/healthz")
def healthz() -> dict:
    return {"ready": nim_ready()}

@app.post("/ask")
def ask(q: Query) -> dict:
    try:
        return {"answer": handle(q.question)}   # traced + guarded pipeline
    except Exception:
        raise HTTPException(status_code=503, detail="service temporarily unavailable")
```

Run it with `uvicorn app:app`, put the `prometheus_client` metrics server on its own port, and you have a service with health checks, tracing, metrics, retries, fallback, and guardrails — every piece the checklist demands.

---

## The series arc, in one line of client code

Step back and look at the path this series walked: a **hosted call** (post 2) → letting the model **use tools** (post 3) → **embeddings and reranking** (post 4) → full **RAG** (post 5) → **guardrails** around it (post 6) → **self-hosting and optimizing** the model (post 7) → **production** (here). That is a complete applied-LLM system, built up one capability at a time.

The remarkable part is what *didn't* change. From the first hosted `chat.completions.create` to a self-hosted NIM behind a FastAPI service with a fallback to the API Catalog, it was the same `openai` client and the same request shape the whole way. The OpenAI-compatible surface and the `pip`-installable NeMo packages meant every new capability layered on without a rewrite, and moving between hosted and self-hosted stayed a change of `base_url` — not a change of architecture. That portability is the reason to build on this stack: you prototype fast on someone else's GPUs and graduate to your own without throwing the code away.

---

## Key takeaways

- **Production is hardening, not rewriting.** Retries, health checks, metrics, and secrets wrap the calls you already have.
- **Pin versions.** `:latest` and unversioned model ids change behavior under you; treat a bump as a tested code change.
- **The two cost meters are opposite.** Hosted = tokens (log `resp.usage`); self-hosted = GPU-hours (maximize utilization, watch queue depth).
- **Rate-limit yourself.** Cap concurrency client-side so bursts don't become `429` storms; the provider's limiter is not your friend.
- **Trace the pipeline.** Server-side Prometheus plus your own per-stage metrics and a request id tell you *which* stage failed.
- **Test the fallback.** An unexercised degraded path fails exactly when the outage hits.
- **Keep keys out of code and endpoints off the public internet** — and keep guardrails on for every request.

---

## Further reading

- [NVIDIA NIM for LLMs — observability and metrics](https://docs.nvidia.com/nim/large-language-models/latest/observability.html)
- [Triton Inference Server — metrics and Prometheus](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/metrics.html)
- [NVIDIA API Catalog / build.nvidia.com](https://build.nvidia.com)
- [NGC private registry and API keys](https://docs.nvidia.com/ngc/gpu-cloud/ngc-user-guide/index.html)
- [tenacity — retrying library for Python](https://tenacity.readthedocs.io/)
- [prometheus_client — Python metrics library](https://prometheus.github.io/client_python/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [OpenAI Python SDK — timeouts and retries](https://github.com/openai/openai-python#retries)
