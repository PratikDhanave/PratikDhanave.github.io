# Production on watsonx

*Taking a watsonx.ai system from a notebook to production in Python — deployment spaces, reliability with retries and fallbacks, cost and throughput control, observability wired to watsonx.governance, and a hardening checklist.*

---

Everything in this series so far has run against a **development project**: a `project_id`, an API key in your shell, and a `ModelInference` call in a script. That is exactly right for building. It is not what you run in production. This finale is about the gap between the two — the choices, the failure modes, and the Python patterns that keep a watsonx.ai system dependable, affordable, observable, and secure once real traffic hits it.

We will lean on everything the earlier posts built: calling models (post 2), tool calling with Granite (post 3), embeddings and reranking (post 4), RAG with Docling (post 5), guardrails and Granite Guardian (post 6), and watsonx.governance (post 7). Production is where those pieces stop being separate demos and become one traced, monitored request path.

---

## From project to space: how prod differs from dev

In development you scope work to a **project** and pass `project_id`. In production you promote the asset — a deployed prompt template, a deployed model, or an AI service — into a **deployment space** and address it by `space_id`. A space is watsonx.ai's production container: it holds deployed assets, controls who can invoke them, and separates a running service from the experimentation that produced it.

The SDK addresses one or the other on the same `APIClient`.

```python
from ibm_watsonx_ai import APIClient, Credentials

credentials = Credentials(
    url=os.environ["WATSONX_URL"],
    api_key=os.environ["WATSONX_APIKEY"],
)
client = APIClient(credentials)

# development
client.set.default_project(os.environ["WATSONX_PROJECT_ID"])

# production — the same client, a different scope
client.set.default_space(os.environ["WATSONX_SPACE_ID"])
```

Once a prompt template or model is deployed into a space, you invoke it through the deployment rather than naming a raw `model_id`, which lets the platform version and govern what actually runs.

```python
# invoke a deployed asset by its deployment id, not a bare model_id
resp = client.deployments.generate(
    deployment_id=os.environ["WATSONX_DEPLOYMENT_ID"],
    params={"prompt_variables": {"question": user_question}},
)
```

Beyond deployed prompt templates, watsonx.ai lets you deploy an **AI service** — your own Python function, packaged and run inside the space — so orchestration like "retrieve, rerank, guard, generate" lives behind one governed endpoint instead of in a client script. Check the `ibm-watsonx-ai` deployment docs for the exact packaging call in your SDK version, since the AI-service surface is still evolving.

**The gotcha:** promoting from dev to prod is **not** swapping `project_id` for `space_id` in a string. The asset itself has to be *moved* — promoted or deployed into the space — before a `space_id` can reach it. A space with no deployed asset returns nothing no matter how correct your credentials are. Treat "promote the asset into the space" as a real deployment step, not a config edit.

---

## SaaS or Cloud Pak for Data: where watsonx runs

Where your production endpoint physically lives is a first-class decision, and it changes only the `url` and the operational model — the SDK calls stay the same.

- **IBM Cloud (SaaS).** watsonx.ai as a managed service, addressed by a regional URL like `https://us-south.ml.cloud.ibm.com`. IBM runs the infrastructure; you pick the region, which fixes where inference happens and where data is processed.
- **Cloud Pak for Data (CPD).** watsonx.ai running on OpenShift in your own environment — on-premises or in your cloud tenancy — for hybrid deployments and stricter **data residency** or isolation requirements. Here the `url` points at your CPD cluster, and authentication uses your CPD credentials rather than an IBM Cloud IAM key.

Region and deployment flavor together decide data residency. If a workload must keep data inside a jurisdiction, choosing the right region (SaaS) or hosting on CPD is the control — not anything you can patch later in code. Decide it before you build the endpoint, because moving a production space across regions or platforms is a migration, not a setting.

---

## Reliability: timeouts, retries, and fallback

Networks are unreliable, services rate-limit, and models occasionally return errors. A production caller assumes every request can fail and decides in advance what happens next.

The SDK exposes its failures through the hierarchy post 2 introduced: `WMLClientError` for client-side and configuration problems, and its subclass `ApiRequestFailure` when the service returns a non-success status (the message carries the HTTP status and the server's error payload). Retry the transient ones — timeouts, 429 rate limits, 5xx — and fail fast on the permanent ones like a bad `model_id` or missing access.

`tenacity` handles the retry loop cleanly. Use **exponential backoff with jitter** so many clients backing off at once do not synchronize into a thundering herd.

```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception, before_sleep_log,
)
from ibm_watsonx_ai.wml_client_error import ApiRequestFailure
import logging

log = logging.getLogger("watsonx")

def is_transient(exc: BaseException) -> bool:
    # retry rate limits and server errors; give up on client mistakes
    if isinstance(exc, ApiRequestFailure):
        status = getattr(exc, "response", None) and getattr(exc.response, "status_code", None)
        return status in (429, 500, 502, 503, 504)
    return isinstance(exc, (TimeoutError, ConnectionError))

@retry(
    retry=retry_if_exception(is_transient),
    wait=wait_exponential_jitter(initial=1, max=30),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def generate_with_retry(model, prompt: str) -> dict:
    return model.generate(prompt=prompt)
```

Two more reliability habits. First, **bound every call with a timeout** — the SDK accepts request timeouts, and an unbounded call is a hung worker waiting to happen. Second, **have a fallback**: when the primary path is exhausted, degrade gracefully rather than 500 the user. A smaller Granite model, a cached previous answer, or a plain "try again shortly" is almost always better than an error page.

```python
from ibm_watsonx_ai.foundation_models import ModelInference

def answer(prompt: str) -> str:
    try:
        return generate_with_retry(primary_model, prompt)["results"][0]["generated_text"]
    except ApiRequestFailure:
        log.warning("primary model failed after retries; falling back")
        cached = cache.get(prompt)
        if cached:
            return cached
        # a smaller, cheaper model as a last resort
        return fallback_model.generate_text(prompt=prompt)
```

**The gotcha:** the IAM bearer token behind your API key is short-lived, and the SDK refreshes it for you — you never write token-refresh code (post 2). What you *do* own is the long-lived **API key** itself, which expires or gets rotated on your organization's schedule. Store it in a secret manager, not in code or a baked image, and read it at startup so a rotation is a secret update and a restart, not a redeploy. Do not try to "help" the SDK by caching tokens yourself; you will only reintroduce the expiry bug it already solved.

---

## Cost and throughput

watsonx.ai bills on **tokens processed**, so cost control starts with token accounting. As post 2 showed, `generate()` returns per-call counts and `chat()` returns a `usage` object — read them on every production call and record them.

```python
resp = model.generate(prompt=prompt)
r = resp["results"][0]
input_tokens = r["input_token_count"]
output_tokens = r["generated_token_count"]
# chat(): resp["usage"]["prompt_tokens"] / ["completion_tokens"] / ["total_tokens"]
```

From there, four levers move the bill and the latency:

- **Right-size the model.** A `granite-3-8b-instruct` answers most tasks; reserve a larger model for the queries that genuinely need it. Routing simple traffic to the smaller model is usually the biggest single saving.
- **Trim the input.** In a RAG path (post 5), fewer, better-reranked chunks (post 4) mean fewer input tokens per call — reranking pays for itself in prompt size.
- **Batch where the API allows it** instead of firing one request per item in a Python loop.
- **Cap concurrency client-side.** Do not let a burst of users translate into an unbounded fan-out at the service; a semaphore keeps you inside your plan's limits and turns 429s into short waits.

```python
import asyncio

sem = asyncio.Semaphore(8)  # at most 8 in-flight calls

async def bounded_generate(model, prompt: str) -> str:
    async with sem:
        # ModelInference calls are synchronous; run them off the event loop
        resp = await asyncio.to_thread(generate_with_retry, model, prompt)
        return resp["results"][0]["generated_text"]
```

On actual prices: watsonx.ai pricing is **plan- and region-specific** and changes over time, so this post cites the pricing page rather than quoting a number — check it for your plan and region and compute your own per-request cost from the token counts above.

**The gotcha:** pin your **model version and prompt-template version**. Foundation models are updated and eventually deprecated on a published schedule (post 2), and a prompt template evolves as you tune it. If production silently floats to a new model build or an edited template, your outputs — and your token usage — shift underneath you with no code change. Pin the versions you validated, and treat a model or template upgrade as a change you test and roll out deliberately, not a surprise.

---

## Observability and governance

You cannot operate what you cannot see. Two layers matter: your own telemetry, and watsonx.governance.

**Structured logging and metrics.** Give every request a correlation id and log each stage of the pipeline with it, so one line of `grep` reconstructs a full RAG → rerank → guardrail → generate trace. Record latency, token counts, and outcome as structured fields, and derive your operational metrics — p95 latency, tokens per request, error rate — from them.

```python
import logging, time, uuid

log = logging.getLogger("watsonx")

def handle(question: str) -> str:
    rid = uuid.uuid4().hex[:12]
    t0 = time.monotonic()
    log.info("request start", extra={"rid": rid, "stage": "start"})

    chunks = retrieve(question)                       # post 5: RAG
    log.info("retrieved", extra={"rid": rid, "stage": "retrieve", "n": len(chunks)})

    top = rerank(question, chunks)                    # post 4: rerank
    if not guardrails_ok(question, top):              # post 6: Granite Guardian
        log.warning("blocked by guardrail", extra={"rid": rid, "stage": "guard"})
        return "I can't help with that request."

    resp = model.generate(prompt=build_prompt(question, top))
    r = resp["results"][0]
    log.info("generated", extra={
        "rid": rid, "stage": "generate",
        "input_tokens": r["input_token_count"],
        "output_tokens": r["generated_token_count"],
        "latency_ms": round((time.monotonic() - t0) * 1000),
    })
    return r["generated_text"]
```

**watsonx.governance.** Post 7 covered factsheets and monitors; production is where they earn their keep. A **factsheet** records the model, prompt template, and evaluation lineage of what you deployed — auditable evidence of *what* is running. **Monitors** (via watsonx.governance / OpenScale) watch the live endpoint for quality, drift, and generative-AI risks like toxicity or hallucination, so a regression shows up as an alert instead of a customer complaint. The `ibm-aigov-facts-client` package (`AIGovFactsClient`) is the Python entry point for wiring factsheets to a deployment; consult the watsonx.governance docs for the monitor configuration that matches your evaluation setup.

**The gotcha:** shipping without governance monitors wired to the production endpoint means you are **blind to drift and hallucination in prod**. Local guardrails (post 6) block bad inputs and outputs request-by-request, but only continuous monitoring tells you the *aggregate* quality is sliding — a model update degrading answers, inputs drifting away from what you evaluated on. In a governance-first platform, connecting monitors is not an optional nicety; it is the difference between knowing your system's health and hoping.

---

## Security

The threats in production are credential leaks and injection, and both have concrete Python-side defenses.

- **Secrets belong in a secret manager, never in code.** The IAM API key and the project/space id should be read from IBM Cloud Secrets Manager, a Kubernetes secret, HashiCorp Vault, or the platform's equivalent — injected as environment variables or fetched at startup. No key in git, no key in a container image, no key in a log line.
- **Least privilege.** Provision the production API key (or service id) with only the access the endpoint needs — invoke a specific space and its deployments, nothing more. A key scoped to one space cannot be used to wander the account if it leaks.
- **Injection is a live surface.** RAG (post 5) puts retrieved document text into the prompt, and tool calling (post 3) lets model output trigger actions — both are paths for prompt injection and untrusted content. Keep the guardrails from post 6 on the input *and* the output, treat tool arguments as untrusted (validate before executing, gate side effects), and never let retrieved text silently override your system instructions.

Least privilege plus a secret manager plus guardrails on both ends is the baseline; none of the three substitutes for the others.

---

## Wrapping it in a FastAPI endpoint

Putting the pieces together, a minimal production endpoint reads config from the environment at startup, applies the retry/fallback logic, and returns a clean response.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ibm_watsonx_ai.wml_client_error import WMLClientError

app = FastAPI()

class Query(BaseModel):
    question: str

@app.post("/ask")
async def ask(q: Query):
    try:
        return {"answer": await bounded_generate(primary_model, q.question)}
    except WMLClientError as exc:
        log.error("request failed", exc_info=exc)
        raise HTTPException(status_code=502, detail="Model service unavailable")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
```

The health check lets your orchestrator restart a stuck worker; the `WMLClientError` catch turns SDK failures into a proper HTTP status instead of a stack trace on the wire.

---

## Production checklist

| Area | Do this before you ship |
|---|---|
| Scope | Deploy the asset into a **space**; call by `space_id` / deployment id, not `project_id` |
| Placement | Choose SaaS region or Cloud Pak for Data to satisfy data residency |
| Versions | Pin model and prompt-template versions you validated |
| Reliability | Timeouts on every call; retry transient errors with backoff + jitter |
| Fallback | Smaller model or cached answer when the primary path is exhausted |
| Secrets | API key + space id in a secret manager; SDK refreshes IAM tokens |
| Access | Least-privilege key scoped to the one space it needs |
| Cost | Record token counts; right-size the model; cap concurrency |
| Guardrails | Input and output guardrails on; validate tool arguments |
| Governance | Factsheets recorded; quality/drift monitors wired to the live endpoint |
| Observability | Correlation id per request; log latency, tokens, error rate |

---

## Key takeaways

- **Dev is a project; prod is a space.** Promote the asset into a deployment space and invoke it by `space_id` / deployment id — moving the asset is a real step, not a string swap.
- **Placement is a design decision.** SaaS region or Cloud Pak for Data fixes data residency, and only the `url` and auth model change in code.
- **Assume every call fails.** Timeouts, `tenacity` retries with backoff and jitter for transient errors, and a smaller-model or cached fallback keep the endpoint up.
- **The SDK refreshes IAM tokens; you protect the API key.** Store it in a secret manager, scoped least-privilege, and rotate it out of band.
- **Cost tracks tokens.** Read `input_token_count` / `generated_token_count`, right-size the model, cap concurrency, and compute price from the region-specific pricing page — never a guessed number.
- **Governance is not optional in production.** Wire factsheets and drift/quality monitors, or you are blind to regressions that request-level guardrails cannot see.

This is the last post in the series, so here is the whole arc: we started with the **watsonx platform** (post 1), made real inference calls with `ModelInference` and `ChatWatsonx` (post 2), gave Granite **tools** (post 3), added **embeddings and reranking** (post 4), built **RAG with Docling** (post 5), put **guardrails and Granite Guardian** around it (post 6), brought it under **watsonx.governance** (post 7), and now run it in **production**. The through-line is watsonx's enterprise, governance-first posture: the platform is built so the same system you demo can be deployed, secured, monitored, and audited — which is exactly what production asks of it.

---

## Further reading

- [Deploying assets and deployment spaces in watsonx.ai](https://www.ibm.com/docs/en/watsonx/saas?topic=deployments-deploying-assets) — spaces, deployed prompt templates, and AI services.
- [IBM Cloud Pak for Data documentation](https://www.ibm.com/docs/en/cloud-paks/cp-data) — on-premises and hybrid watsonx deployment.
- [watsonx.ai pricing](https://www.ibm.com/products/watsonx-ai/pricing) — plan- and region-specific rates; compute your own per-request cost.
- [ibm-watsonx-ai SDK documentation](https://ibm.github.io/watsonx-ai-python-sdk/) — `APIClient`, `set.default_space`, deployments, and error classes.
- [IBM watsonx.governance documentation](https://www.ibm.com/docs/en/watsonx/watsonxgov) — factsheets and production model monitors.
- [tenacity documentation](https://tenacity.readthedocs.io/) — retry, `wait_exponential_jitter`, and stop conditions.
- [FastAPI documentation](https://fastapi.tiangolo.com/) — building and serving the endpoint.
