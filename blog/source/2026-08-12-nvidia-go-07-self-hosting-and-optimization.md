# Self-Hosting and Optimizing Inference

*When to graduate from the hosted API Catalog to inference you run yourself — deploying a NIM container, understanding Triton and TensorRT-LLM, the optimization levers that raise throughput and cut latency, and the one Go base-URL switch that makes the move free.*

---

Earlier in this series the Go client talked to `https://integrate.api.nvidia.com/v1` — NVIDIA's hosted API Catalog. That endpoint is the right way to start: no GPUs, no drivers, no ops, just a Bearer token and a model id. But it is not the only way to run, and past a certain point it stops being the *cheapest* or most *controllable* way. This post is about the other end of the spectrum — inference you host and operate yourself — and how to decide where on that spectrum you belong.

A caution up front, so the framing is honest: **NVIDIA ships no Go SDK, and this is not a Go-heavy post.** Deploying and tuning inference is an operations job — containers, GPUs, and server config — that happens mostly outside your Go program. Go's role here is narrow but real: it *calls* the endpoint you stand up, and it *operates* it (health checks, readiness gating). The payoff established in post 2 pays off again here — because your client speaks the OpenAI-compatible dialect, moving from hosted to self-hosted is a one-line change. Everything else in this post is the ops context around that one line.

---

## Why self-host at all

The hosted catalog is a managed convenience: NVIDIA owns the hardware, the scaling, and the uptime, and you pay per token. Self-hosting inverts every one of those. You take on GPUs and operations, and in exchange you get control. The reasons that justify the trade tend to be some mix of:

- **Data control and residency.** When prompts or documents can't leave your network — regulated data, customer PII, contractual residency requirements — sending them to a third-party API is a non-starter. A NIM running inside your VPC keeps every token on infrastructure you control.
- **Predictable cost at scale.** Per-token pricing is wonderful at low volume and brutal at high volume. Once you're serving a steady, heavy request stream, the fixed cost of a GPU you own can undercut a metered bill — *if* your utilization is high enough to amortize it.
- **Latency and locality.** A model co-located with your application — same region, same network, no public-internet round trip — can shave the tail latency that a remote API adds.
- **No per-token vendor pricing.** Self-hosting converts a variable, usage-coupled cost into a fixed capacity cost. That changes the economics of features that would be reckless to ship on a metered API (bulk reprocessing, aggressive retries, speculative calls).
- **Air-gapped operation.** Some environments have no outbound internet at all. A container you pull once and run offline is the only option that works.

**The gotcha:** self-hosting trades vendor cost for **GPU + ops cost** — and the ops cost is the one teams underestimate. You now own driver upgrades, capacity planning, autoscaling, monitoring, and on-call. It is only worth it past a volume (or compliance) threshold, and that threshold is specific to your workload. Don't reason about it in the abstract — **measure** your actual request volume and compare the fully-loaded cost of owned hardware against your metered bill before you commit.

---

## Deploying a NIM: a container that self-optimizes

A NIM (NVIDIA Inference Microservice) is distributed as a **container image**. You pull it from NVIDIA's NGC registry, run it on a host with a compatible NVIDIA GPU, and it comes up serving the *same* OpenAI-compatible endpoint you've been calling in the hosted catalog — typically on a local port. The clever part is what happens between pull and serve: the NIM inspects the GPU it landed on and configures itself with an optimized inference profile for that hardware. You don't hand-tune the engine; the container does that work for you.

To pull from NGC you need an **NGC API key**, and to give the container access to the GPU you need the NVIDIA driver plus the **NVIDIA Container Toolkit** installed on the host (that's what wires the GPU through to the container runtime). The shape of a run looks roughly like this — treat the exact flags as **illustrative**, and confirm the current image name, tag, port, and environment variables against the NIM documentation for your chosen model, because they vary by model and change over time:

```bash
# ILLUSTRATIVE — verify image, tag, port, and env against the NIM docs.
# 1) Authenticate to NGC so docker can pull the image.
docker login nvcr.io   # username: $oauthtoken, password: your NGC API key

# 2) Run the NIM with GPU access exposed through the container toolkit.
docker run --rm --gpus all \
  -e NGC_API_KEY="$NGC_API_KEY" \
  -p 8000:8000 \
  nvcr.io/nim/<publisher>/<model>:<tag>
```

Once it reports ready, it is answering `POST /v1/chat/completions` on `localhost:8000` — byte-for-byte the contract your Go client already speaks.

**The gotcha:** a NIM has **real GPU and driver requirements** — a supported CUDA/driver version, the NVIDIA Container Toolkit, and a GPU with enough memory for the model. When those don't line up, the container fails *at start*, not at request time. A missing toolkit, a too-old driver, or a GPU that can't fit the weights surfaces as a container that never becomes ready — so read the container logs on startup rather than waiting for a request to error.

---

## The portability payoff, realized

Here is the part that makes all of the above cheap from Go's side. The client we built in post 2 took its endpoint as a constructor argument. Pointing it at the NIM you just deployed is one line:

```go
// Before — hosted API Catalog (needs an nvapi-... key):
client, _ := nim.New()

// After — your self-hosted NIM (no key if it's network-scoped):
client := nim.NewWithBaseURL("http://localhost:8000/v1", "")
```

Nothing else in the Go code changes. The request structs, the SSE streaming parser, the status-error handling, the token accounting — all identical, because both endpoints implement the same OpenAI-compatible surface. That is the quiet dividend of NIM having *no* bespoke Go SDK: there is no vendor abstraction to unlearn when you move from a hosted trial to production on your own hardware.

**The gotcha:** the *wire protocol* is portable, but the *catalog* is not. Model ids differ between the hosted catalog and what you self-host, and a self-hosted model may not have exactly the same capabilities — tool/function calling, structured output, and context window can all differ by model and version. So the base-URL switch is free, but **re-verify capabilities after you flip it**: run your tool-calling and streaming paths against the self-hosted endpoint before you assume they behave identically. Portable transport does not guarantee portable behavior.

---

## Triton Inference Server: when you need more than a NIM

A NIM is a curated, single-purpose microservice: one model, pre-packaged, self-optimizing. **Triton Inference Server** is the general-purpose serving layer underneath that convenience. You reach for Triton directly when a NIM's one-model, one-endpoint shape is too narrow — when you need to:

- **Serve multiple models** (or multiple versions of one) from a single server, with its model-repository layout and version management.
- **Serve custom or non-LLM models** — your own fine-tunes, classical ML, vision models — across multiple backends, not just the LLMs a NIM wraps.
- **Talk gRPC as well as HTTP.** Triton exposes both, following the KServe-compatible inference protocol, which matters for high-throughput, low-overhead internal services.
- **Control batching yourself** through Triton's dynamic batching — coalescing requests that arrive close together into one GPU pass.

Triton also exposes a **Prometheus metrics endpoint**, which is what makes it operable in production. You scrape it for the signals that tell you whether the server is healthy and how hard it's working — request counts, queue and compute latencies, and GPU utilization — and wire those into dashboards and alerts. A NIM gives you a turnkey model; Triton gives you a serving *platform* you assemble and operate. The rule of thumb: use a NIM when one exists for your model and its packaging fits; drop to Triton when you're serving a fleet of models or something a NIM doesn't cover.

---

## TensorRT-LLM: the optimization layer underneath

Both NIM and Triton can serve LLMs through **TensorRT-LLM** — NVIDIA's optimization library and inference backend for large language models. This is where raw throughput and latency actually get won or lost. You mostly don't touch it directly when you run a NIM (the NIM applies it for you), but understanding *what* it does explains *why* self-hosted inference can be fast. The core techniques, at an intuition level:

- **Quantization (e.g. FP8, INT8).** Model weights and activations are stored and computed in lower numerical precision instead of full 16- or 32-bit floats. Smaller numbers mean less memory moved per token and faster arithmetic on hardware built for low precision — so you fit bigger models or more concurrent requests on the same GPU, and each step runs quicker. The trade is a small, usually acceptable accuracy cost that the quantization method works to minimize.
- **In-flight (continuous) batching.** Naive batching waits for a whole batch of requests to finish before starting the next — the fast requests idle while the slow ones drag. Continuous batching instead swaps finished sequences out and new ones in *while the batch is running*, keeping the GPU saturated. Higher utilization means higher total throughput without punishing latency for short requests.
- **Paged KV cache.** As a model generates, it caches the attention keys and values for tokens already seen (the "KV cache"). Reserving one big contiguous block per request wastes memory to fragmentation. Paging it — allocating the cache in small reusable pages, like virtual memory — packs many more concurrent sequences into the same GPU memory, which raises the concurrency ceiling and thus throughput.
- **Tensor parallelism.** A model too large for one GPU is split *across* several, with each GPU holding a slice of every layer and the GPUs exchanging partial results. That's what lets you serve models that no single GPU could hold, and it can cut latency by putting more compute on each token.

Each lever pushes on the same two dials — memory pressure and GPU occupancy — because those are what bound LLM serving. The practical takeaway: a NIM already applies an appropriate combination of these for the GPU it detects, so you get most of the benefit without hand-tuning. You'd configure TensorRT-LLM yourself only when you're building a custom Triton deployment and need to control the engine directly.

**The gotcha:** these are legitimately powerful, and it is tempting to reach for the numbers. Resist quoting throughput or latency figures you didn't measure on *your* hardware with *your* model and *your* traffic — the gains are real but entirely dependent on GPU, model, quantization, and request mix. The only honest benchmark is the one you run against your own deployment.

---

## A decision framework: three tiers of control

These three options form a ladder of increasing control and increasing effort. Climb only as far as your requirements force you:

| Tier | What it is | You control | You operate | Reach for it when |
|---|---|---|---|---|
| 1. Hosted API Catalog | NVIDIA-run endpoint, per-token billing | Almost nothing | Nothing | Prototyping, low/spiky volume, no data-residency constraint |
| 2. Self-hosted NIM | Container you pull and run; self-optimizing | Placement, scaling, data path | GPUs + ops | Data must stay in your network; steady high volume; predictable cost matters |
| 3. Custom Triton + TensorRT-LLM | Server you assemble and tune | The whole serving stack | Everything | Multiple/custom models, gRPC, or engine-level tuning a NIM can't give |

The discipline is to **stop at the lowest tier that meets your constraints**. Tier 1 costs the least engineering and is where every project should start. Tier 2 is the common landing spot for production once compliance or volume forces the move — you get most of the optimization for the price of running a container. Tier 3 is for teams that genuinely need a serving platform, and it carries the most operational weight. Jumping to tier 3 because it sounds powerful is how you end up owning a Kubernetes-plus-GPU platform to serve one model that a NIM would have handled.

---

## Go's job: gate traffic on a readiness probe

Here is where Go re-enters. A model server — NIM or Triton — takes real time to become ready after the container starts: it loads weights, builds or loads the optimized engine, and warms up. Routing traffic before it's ready gives your users errors. So before a new instance joins your pool, your Go orchestration should **poll a health/readiness endpoint until it passes**, then route. The exact path depends on the server (NIM and Triton expose their own health/ready endpoints — check the docs); the pattern is the same:

```go
package health

import (
	"context"
	"fmt"
	"net/http"
	"time"
)

// WaitReady polls the server's readiness endpoint until it returns 200 OK
// or the context deadline is hit. Nothing should route to the endpoint
// until this returns nil.
func WaitReady(ctx context.Context, httpClient *http.Client, readyURL string) error {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		if ok := probe(ctx, httpClient, readyURL); ok {
			return nil
		}
		select {
		case <-ctx.Done():
			return fmt.Errorf("endpoint %s not ready before deadline: %w", readyURL, ctx.Err())
		case <-ticker.C:
			// try again on the next tick
		}
	}
}

// probe issues a single readiness check. A 200 means "route traffic here";
// anything else (including a connection error while the model still loads)
// means "not yet".
func probe(ctx context.Context, httpClient *http.Client, readyURL string) bool {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, readyURL, nil)
	if err != nil {
		return false
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		return false // server not up yet — expected during startup
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}
```

Driving it before the first real request:

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
defer cancel()

readyURL := "http://localhost:8000/v1/health/ready" // illustrative path — confirm in the docs
if err := health.WaitReady(ctx, &http.Client{Timeout: 5 * time.Second}, readyURL); err != nil {
	log.Fatalf("NIM never became ready: %v", err)
}

// Only now is it safe to construct the client and send traffic.
client := nim.NewWithBaseURL("http://localhost:8000/v1", "")
```

**The gotcha:** **don't route traffic before the readiness probe passes.** Model load is not instant — a large model can take minutes to come up, and during that window the endpoint may refuse connections or return errors that look like failures but are just "not ready yet." Treat a connection error during startup as *keep polling*, give the probe a generous deadline (a coarse per-request timeout plus an overall budget), and only flip an instance into rotation once it answers 200. A liveness/readiness gate like this is exactly what a Kubernetes readiness probe automates in production — the Go loop above is the same idea when you're orchestrating it yourself.

---

## Key takeaways

- **Start hosted; self-host only when a constraint forces it.** Data residency, air-gapping, predictable cost at high volume, and latency are the reasons that justify taking on GPUs and ops — and the ops cost is the one to measure, not guess.
- **A NIM is a container that optimizes itself.** Pull it from NGC with your NGC API key, run it with GPU access via the NVIDIA Container Toolkit, and it serves the same OpenAI-compatible endpoint the hosted catalog does. Requirement mismatches fail at container start, so watch the startup logs.
- **The base-URL switch is free; behavior parity is not.** Your Go client moves from hosted to self-hosted in one line, but model ids and capabilities differ — re-verify tool calling and streaming against the new endpoint.
- **Triton is the platform; TensorRT-LLM is the engine.** Drop to Triton for multiple/custom models, gRPC, and Prometheus metrics; TensorRT-LLM's quantization, continuous batching, paged KV cache, and tensor parallelism are the levers that raise throughput and cut latency — and a NIM applies them for you.
- **Gate traffic on readiness.** Model load takes time; poll a health endpoint until it returns 200 before routing, and never quote performance numbers you didn't measure on your own hardware.

---

## Further reading

- [NVIDIA NIM documentation](https://docs.nvidia.com/nim/) — deploying NIM microservices: container prerequisites, NGC authentication, GPU requirements, and the served endpoints.
- [NVIDIA NIM for LLMs — deployment guide](https://docs.nvidia.com/nim/large-language-models/latest/getting-started.html) — pulling and running an LLM NIM, and confirming its current image names, ports, and environment variables.
- [Triton Inference Server documentation](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/index.html) — model repositories, HTTP/gRPC (KServe) protocol, dynamic batching, and the Prometheus metrics endpoint.
- [TensorRT-LLM (GitHub)](https://github.com/NVIDIA/TensorRT-LLM) — the optimization backend: quantization, in-flight batching, paged KV cache, and tensor parallelism.
- [NVIDIA Container Toolkit documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/index.html) — installing the toolkit and driver so containers can access the GPU.
