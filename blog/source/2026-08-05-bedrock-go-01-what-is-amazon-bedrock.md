# What Amazon Bedrock Is

*The opener for a Go series on building LLM and agent applications with Amazon Bedrock — what the service actually is, why it sits between your Go code and a dozen foundation models, and which aws-sdk-go-v2 packages you will lean on for the rest of the way.*

---

In earlier posts I called model providers the blunt way: build a JSON body, `POST` it with `net/http`, set a bearer token in a header, parse the response. That works, and it teaches you what a completion request really looks like on the wire. But the moment you want a second model, a second region, an audit trail, or a security team that signs off, the hand-rolled client starts to hurt. **Amazon Bedrock** is AWS's answer to that friction: one managed service that puts many foundation models behind a single API, authenticated and governed the way the rest of your AWS account already is.

This series builds real Go applications on Bedrock — the Converse API, streaming, tool use, retrieval over your own documents, agents, guardrails, and the production concerns that decide whether any of it survives contact with a bill and an on-call rotation. This first post is the map. No feature deep-dive yet; just what Bedrock is, what it adds over a raw provider call, what it costs you in exchange, and which SDK packages back each piece.

---

## One API in front of many models

The core idea is small and worth stating plainly. Bedrock is a fully-managed service that exposes foundation models from several providers — Anthropic's Claude family, Amazon's own Nova and Titan models, Meta's Llama, Mistral, and others — through a shared request surface. You pick a model by its **model ID** (a string like `anthropic.claude-3-5-sonnet-20241022-v2:0`), and for most chat-style work you call the same operation regardless of which vendor built the model.

That last part is the leverage. With a direct provider integration, switching from one vendor to another means a new endpoint, a new auth scheme, a new request schema, and a new response shape — a rewrite. On Bedrock, the **Converse API** normalizes messages, system prompts, tool definitions, and token usage across providers, so swapping models is often a one-line change to the model ID. You still tune per-model behavior where it matters, but the plumbing stays put.

The models are not automatically available. Each one must be **enabled for your account in a given region** through the Bedrock console's model-access page, and availability varies by region. That is the first thing to internalize: Bedrock is regional, and a model that answers in `us-east-1` may simply not exist in `eu-central-1` yet.

---

## What Bedrock adds over a raw provider call

If you already have a working `net/http` client against a provider, it is fair to ask what a managed layer buys you. Here is the honest accounting.

**AWS-native auth instead of bearer keys.** A direct provider call carries a long-lived API key in a header — a secret you have to store, rotate, and hope never leaks into a log or a git history. Bedrock uses **IAM and SigV4 request signing**. The SDK signs each request with credentials resolved from your environment — an IAM role on an EC2 instance or a Lambda, an SSO session, a named profile — and you scope access with IAM policies (allow `bedrock:InvokeModel` on this model ARN, deny everything else). There is no model API key to manage.

**Data stays in your AWS account and region.** Requests and responses flow through your chosen region, and you can keep traffic on the AWS network with **VPC endpoints and PrivateLink** so nothing traverses the public internet. For teams with data-residency obligations, choosing the region *is* the compliance control.

**Operational plumbing you would otherwise build.** CloudWatch metrics and logs, per-model and per-account quotas, and **provisioned throughput** for workloads that need reserved, predictable capacity rather than on-demand rates.

**Higher-level building blocks.** Beyond raw inference, Bedrock offers **guardrails** (content and topic policies applied to inputs and outputs), **knowledge bases** (managed retrieval-augmented generation over your documents), and **agents** (multi-step tool-using workflows the service orchestrates). These are later posts, but they are the reason to be on Bedrock rather than gluing models together yourself.

The trade-offs are real and you should name them up front:

- **AWS lock-in.** Your auth, networking, and higher-level features are AWS-shaped. Portability drops.
- **Region-dependent model availability.** The newest model may land in one region months before another.
- **You must request model access.** A fresh account cannot call any model until you enable it in the console — a step that surprises people on day one.

---

## The pieces you will use, and the packages behind them

Bedrock splits into a **control plane** (managing models, guardrails, and configuration) and a **runtime** (actually running inference and invoking agents). The Go SDK, `aws-sdk-go-v2`, mirrors that split across four service packages. Knowing which is which saves you a lot of confused importing.

| Package | Plane | What you do with it |
|---|---|---|
| `github.com/aws/aws-sdk-go-v2/service/bedrock` | Control | List available foundation models, manage guardrails and model customization |
| `github.com/aws/aws-sdk-go-v2/service/bedrockruntime` | Runtime | Run inference: `Converse`, `ConverseStream`, `InvokeModel` |
| `github.com/aws/aws-sdk-go-v2/service/bedrockagent` | Control | Author agents and knowledge bases (design-time) |
| `github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime` | Runtime | Invoke agents at run-time: `InvokeAgent`, `RetrieveAndGenerate` |

The pairing is the thing to remember: `bedrock` and `bedrockagent` are where you *configure*; `bedrockruntime` and `bedrockagentruntime` are where you *call*. Most of this series lives in `bedrockruntime` — the Converse API is the workhorse — with `bedrockagent` and `bedrockagentruntime` arriving when we build agents and RAG.

**The gotcha:** the package that runs a chat completion is `bedrockruntime`, not `bedrock`. The plain `bedrock` package has no `Converse` method — it is the control plane. If your editor cannot find `Converse`, you have almost certainly imported the wrong one. This trips up nearly everyone on their first client.

---

## Why Go for this

The Go SDK is not a second-class binding here — `aws-sdk-go-v2` is a first-class, AWS-maintained SDK, and the Bedrock service packages are generated and updated alongside the rest of AWS. Three properties make Go a genuinely good fit for Bedrock services:

- **Single static binary.** A Bedrock-backed API ships as one artifact with no runtime to install — trivial to drop into a container, a Lambda, or a bare host.
- **First-class SDK.** Context-aware operations, structured error types, pluggable credential providers, and typed request/response shapes generated straight from the AWS API models.
- **Concurrency that fits the workload.** LLM calls are I/O-bound and often fan out — score ten candidates, summarize twenty documents, race two models. Goroutines and a bounded worker pool make that natural, and `context.Context` gives you clean per-request timeouts and cancellation on calls that can run for many seconds.

---

## Config and auth: from credentials to a client

Every Bedrock call needs an `aws.Config` — the resolved bundle of region, credentials, and HTTP settings. You build it once with the `config` package's `LoadDefaultConfig`, which walks the standard AWS credential chain (environment variables, shared config files, SSO, and IAM roles) so your code never hardcodes a secret. Then you construct a runtime client from that config.

```go
package main

import (
	"context"
	"log"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
)

func main() {
	ctx := context.Background()

	// Resolve region + credentials from the standard AWS chain.
	cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion("us-east-1"))
	if err != nil {
		log.Fatalf("load AWS config: %v", err)
	}

	// A runtime client is all you need to run inference later.
	client := bedrockruntime.NewFromConfig(cfg)

	log.Printf("bedrock runtime client ready in region %s", cfg.Region)
	_ = client // next post: client.Converse(ctx, ...)
}
```

Before this compiles into something that actually talks to AWS, install the packages:

```bash
go get github.com/aws/aws-sdk-go-v2/config
go get github.com/aws/aws-sdk-go-v2/service/bedrockruntime
```

To confirm your credentials and region resolve *and* that a model is enabled, you can list foundation models from the control-plane client — a read-only call that touches no inference budget:

```go
import "github.com/aws/aws-sdk-go-v2/service/bedrock"

// cfg from LoadDefaultConfig above
ctrl := bedrock.NewFromConfig(cfg)
out, err := ctrl.ListFoundationModels(ctx, &bedrock.ListFoundationModelsInput{})
if err != nil {
	log.Fatalf("list models: %v", err)
}
log.Printf("region %s exposes %d foundation models", cfg.Region, len(out.ModelSummaries))
```

**The gotcha:** a clean compile and valid credentials still are not enough to *invoke* a model. `ListFoundationModels` shows what exists in the region; it does not mean you have access. Until you enable a specific model on the Bedrock console's model-access page for that region, an inference call returns an `AccessDeniedException`. And because access is granted per region, enabling Claude in `us-east-1` does nothing for a client configured against `eu-west-1`. Enable the model, in the region, before you expect an answer.

---

## The road ahead

With the map in hand, here is where the series goes. Each post is standalone Go you can run, building toward a production-shaped Bedrock service.

1. **What Amazon Bedrock is** — this post: the service, the trade-offs, the packages, the client.
2. **The Converse API** — the unified chat call: messages, system prompts, inference parameters, and swapping models by ID.
3. **Streaming and usage** — `ConverseStream` for token-by-token output, and reading token counts to track cost.
4. **Tool use** — letting a model call your Go functions through Converse's tool-calling loop.
5. **Knowledge-base RAG** — grounding answers in your own documents with `RetrieveAndGenerate`.
6. **Bedrock Agents** — multi-step, tool-using workflows invoked with `InvokeAgent`.
7. **Guardrails** — content and topic policies on inputs and outputs.
8. **Production** — IAM scoping, cost control, retries and timeouts, and CloudWatch observability.

---

## Key takeaways

- **Bedrock is one API in front of many models.** Pick a model by ID; the Converse API keeps the request and response shape stable across Anthropic, Amazon, Meta, Mistral, and more.
- **Auth is IAM, not bearer keys.** The SDK signs every request with SigV4 using credentials from the standard chain — nothing to store or rotate by hand.
- **It is regional, and access is opt-in.** Model availability varies by region, and each model must be enabled in the console for that region before you can invoke it.
- **Four packages, split into two planes.** `bedrock` / `bedrockagent` configure; `bedrockruntime` / `bedrockagentruntime` run. Inference lives in `bedrockruntime` — not `bedrock`.
- **Go fits the shape of the work.** Single-binary services, a first-class SDK, and cheap concurrency for I/O-bound, fan-out model calls.
- **The price is lock-in and setup.** You trade portability for AWS-native auth, networking, data residency, and higher-level features like guardrails, knowledge bases, and agents.

---

## Further reading

- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/) — the primary source for models, regions, model access, guardrails, knowledge bases, and agents.
- [`bedrockruntime` on pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime) — the inference client (`Converse`, `ConverseStream`, `InvokeModel`).
- [`bedrock` on pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrock) — the control-plane client (list models, manage guardrails).
- [`bedrockagent` on pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockagent) — authoring agents and knowledge bases.
- [`bedrockagentruntime` on pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime) — invoking agents (`InvokeAgent`, `RetrieveAndGenerate`).
- [`config` on pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/config) — `LoadDefaultConfig` and the credential chain.
