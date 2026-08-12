# Bedrock in Production: IAM, Cost, and Observability

*Taking an Amazon Bedrock Go service from a working prototype to something you can run on-call — least-privilege IAM, credentials without static keys, tuning the SDK's built-in retryer, tracking token cost, and wiring up logging and metrics with aws-sdk-go-v2.*

---

Across this series we built up a Bedrock service in Go one capability at a time: a first [Converse call](/blog/posts/bedrock-go-02-converse-api.html), then [streaming and usage accounting](/blog/posts/bedrock-go-03-streaming-and-usage.html), [tool use](/blog/posts/bedrock-go-04-tool-use.html), retrieval with knowledge bases, agents, and guardrails. Every one of those posts answered "how do I make the model *do* this?" This finale answers a different question: **how do I run it in production without getting paged, over-billed, or breached?**

None of what follows is model behaviour — it is operational plumbing. But it is the difference between a demo and a service. We will cover the four things that decide whether a Bedrock deployment is boring in the good way: identity and access, reliability, cost, and observability. All of it uses `github.com/aws/aws-sdk-go-v2` and the wider AWS Go SDK — no third-party frameworks.

---

## Two gates, not one

Before any IAM, understand the access model, because it trips up nearly everyone once: **on Bedrock, calling a foundation model passes through two independent gates, and both must open.**

1. **Model access** is a per-account, per-region grant you request in the Bedrock console under *Model access*. Until a model shows as "Access granted," no principal in the account can invoke it, regardless of IAM.
2. **IAM permissions** are the usual policy grant: the specific principal (your role) must be allowed the specific action on the specific model resource.

**The gotcha:** these are two separate switches and failing either one looks different. A missing model-access grant surfaces as an `AccessDeniedException` mentioning the model isn't accessible; a missing IAM permission surfaces as an `AccessDeniedException` about the *action*. Developers commonly fix the IAM policy, redeploy, and stay blocked because the account never requested model access in that region in the first place. Check both, and check them in the region you actually call.

---

## A least-privilege IAM policy

The instinct to attach a broad `bedrock:*` policy "just to get it working" is how over-privileged roles metastasise. Bedrock's runtime actions are narrow and well-named, so scope to exactly what your service calls, on exactly the model ARNs it uses.

The core runtime actions:

- `bedrock:InvokeModel` — the raw invoke call.
- `bedrock:InvokeModelWithResponseStream` — its streaming twin.
- `bedrock:Converse` and `bedrock:ConverseStream` — the Converse API used throughout this series.

If your service uses agents and knowledge bases, those are *separate* actions on *separate* resources: `bedrock:InvokeAgent`, and for retrieval `bedrock:Retrieve` / `bedrock:RetrieveAndGenerate`.

Foundation-model ARNs have no account ID (the model is owned by AWS/the provider), while provisioned models and inference profiles live in your account. A policy for a Converse-based service calling one Claude model in `us-east-1` looks like this:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeOneClaudeModel",
      "Effect": "Allow",
      "Action": [
        "bedrock:Converse",
        "bedrock:ConverseStream",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
      ]
    }
  ]
}
```

If you route through a cross-region **inference profile** (common for Claude models today), the profile is a real resource in your account and you must list it *and* the underlying foundation models in every region it can reach:

```json
"Resource": [
  "arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-3-5-sonnet-20240620-v1:0",
  "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
  "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
]
```

**The gotcha:** an inference profile invocation is authorized against *both* the profile ARN and the foundation-model ARN in each region the profile fans out to. Scope your `Resource` to only the profile and you'll get denied at call time; list every region's model ARN the profile targets. Consult the profile's definition for its member regions rather than guessing.

---

## Credentials without static keys

Never bake access keys into a Bedrock service. Hard-coded keys leak, don't rotate, and can't be scoped per-task. Instead give the compute an **IAM role** and let the SDK find it.

`config.LoadDefaultConfig` walks the default credential provider chain — environment variables, shared config files, then the container/instance credential providers — and picks up whatever the runtime offers. On ECS it reads the task role from the container credentials endpoint; on EKS it uses IAM Roles for Service Accounts (IRSA) via the projected web-identity token; on Lambda it uses the function's execution role from the environment. In every case your code is identical and there are no keys in it:

```go
import (
	"context"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
)

func newClient(ctx context.Context) (*bedrockruntime.Client, error) {
	cfg, err := config.LoadDefaultConfig(ctx,
		config.WithRegion("us-east-1"),
	)
	if err != nil {
		return nil, err
	}
	return bedrockruntime.NewFromConfig(cfg), nil
}
```

The credential chain also handles refresh: role credentials are temporary and the SDK re-fetches them before expiry, so a long-running service keeps working without restarts. Locally, the same chain reads your `aws configure` profile or `AWS_PROFILE`, so the code you run on your laptop is the code that runs in the cluster.

**The gotcha:** if you find yourself reaching for `config.WithCredentialsProvider` and a static-key provider, stop — that's almost always the wrong tool outside a short-lived test. The right move is to attach the correct role to the task/pod/function and let `LoadDefaultConfig` discover it. Static keys are the thing security review will flag first.

---

## Reliability: tune the retryer, don't wrap it

Here is the single most important reliability fact about aws-sdk-go-v2: **it already retries for you.** Every Bedrock client is built with a standard retryer that catches transient and throttling errors and retries them with exponential backoff *and jitter*, up to a maximum attempt count. You do not need to write a retry loop, and if you do, you will make things worse.

You configure the built-in retryer at construction. To raise the attempt ceiling, `config.WithRetryMaxAttempts` is the one-liner; for finer control, install a `retry.NewStandard` retryer (or the adaptive mode, which additionally rate-limits client-side under sustained throttling):

```go
import (
	"time"

	awshttp "github.com/aws/aws-sdk-go-v2/aws/transport/http"
	"github.com/aws/aws-sdk-go-v2/aws/retry"
	"github.com/aws/aws-sdk-go-v2/config"
)

cfg, err := config.LoadDefaultConfig(ctx,
	config.WithRegion("us-east-1"),

	// Raise the built-in retryer's attempt cap (default is 3).
	config.WithRetryMaxAttempts(5),

	// Or take full control of the standard retryer.
	config.WithRetryer(func() aws.Retryer {
		return retry.NewStandard(func(o *retry.StandardOptions) {
			o.MaxAttempts = 5
			o.MaxBackoff = 10 * time.Second
		})
	}),

	// A hard per-attempt transport timeout so no single call hangs.
	config.WithHTTPClient(awshttp.NewBuildableClient().WithTimeout(60*time.Second)),
)
```

Pass either `WithRetryMaxAttempts` *or* a custom `WithRetryer` — not both, since the custom retryer defines its own attempt count. Backoff and jitter come for free inside the standard retryer; you tune the ceilings, not the algorithm.

Layer timeouts on top with `context`. The retryer governs *how many times*; the context governs *how long total*. A deadline on the call bounds the whole retry sequence:

```go
ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
defer cancel()
out, err := client.Converse(ctx, input)
```

Because Converse and InvokeModel are effectively read-style, request-response calls (they don't mutate durable state on the Bedrock side), retrying them is safe — a retried call just produces another completion. That's what makes the built-in retryer sound here.

**The gotcha:** the SDK already retries with backoff, so a naive `for i := 0; i < 5; i++` around your call *multiplies* attempts — 5 of your iterations times 3 SDK attempts is up to 15 requests, and under a throttling event that turns a hiccup into a self-inflicted request storm. If you need more resilience, raise `MaxAttempts` on the built-in retryer; don't stack your own loop on top of it. When you do want to react to throttling explicitly, detect it by type rather than string matching:

```go
import (
	"errors"

	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
)

var thr *types.ThrottlingException
if errors.As(err, &thr) {
	// The retryer has already exhausted its attempts; shed load,
	// enqueue for later, or return a 429 to your caller.
}
```

On-demand throughput has **per-account, per-model quotas** (requests and tokens per minute) that the service enforces by throttling. If your steady-state load is high enough to hit them, no amount of client retry fixes it — you either request a quota increase or buy **provisioned throughput**, which reserves capacity as model units for predictable, high-volume workloads. Invoking a provisioned model just means passing its provisioned-model ARN as the `ModelId`; the code doesn't otherwise change.

---

## Cost control starts with token accounting

Bedrock bills on-demand usage by tokens — input and output priced separately, and the rates differ by **model and region**. I won't print numbers here because they change and vary; the authoritative source is the [Amazon Bedrock pricing page](https://aws.amazon.com/bedrock/pricing/), and your cost model should read from it, not from a blog.

What you *can* do in code is measure. Every Converse response carries a `Usage` field (`types.TokenUsage`) with `InputTokens`, `OutputTokens`, and `TotalTokens` — the same accounting we used back in the [streaming and usage](/blog/posts/bedrock-go-03-streaming-and-usage.html) post, now put to work for cost. Aggregate it per model with the per-token rates as configuration you fill in from the pricing page:

```go
import (
	"sync"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
)

// Rates are per 1,000 tokens, model- and region-specific.
// Fill these from the official Bedrock pricing page — do not hard-code
// a number you can't cite.
type Rate struct {
	InputPer1K  float64
	OutputPer1K float64
}

type CostTracker struct {
	mu     sync.Mutex
	rates  map[string]Rate // modelID -> rate
	inTok  map[string]int64
	outTok map[string]int64
}

func NewCostTracker(rates map[string]Rate) *CostTracker {
	return &CostTracker{
		rates:  rates,
		inTok:  map[string]int64{},
		outTok: map[string]int64{},
	}
}

// Record folds one response's Usage into the running totals.
func (c *CostTracker) Record(modelID string, u *types.TokenUsage) {
	if u == nil {
		return
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	c.inTok[modelID] += int64(aws.ToInt32(u.InputTokens))
	c.outTok[modelID] += int64(aws.ToInt32(u.OutputTokens))
}

// EstimatedCost applies the configured rates to the accumulated tokens.
func (c *CostTracker) EstimatedCost() float64 {
	c.mu.Lock()
	defer c.mu.Unlock()
	var total float64
	for model, r := range c.rates {
		total += float64(c.inTok[model]) / 1000 * r.InputPer1K
		total += float64(c.outTok[model]) / 1000 * r.OutputPer1K
	}
	return total
}
```

This is an *estimate* for dashboards and alerts, not a billing system of record — reconcile against Cost Explorer and your AWS invoice. But having live token counts per model lets you catch a runaway prompt or a retry storm long before the bill does.

Beyond measurement, the levers that actually move cost:

- **Right-size the model.** The most capable model is rarely the cheapest, and many tasks (classification, extraction, short summaries) run fine on a smaller, faster model. Route by task.
- **Trim the context.** Input tokens are billed too. Retrieval that stuffs ten documents into the prompt when three would do is pure waste — tighten what RAG injects.
- **Cache and batch where the shape allows.** Deduplicate identical requests, and if the model family supports prompt caching for a large stable system prompt, reuse it rather than resending it every call.

**The gotcha:** never invent or hard-code a price. Rates differ by model and region and change over time; a number baked into your code silently goes wrong. Keep rates in configuration sourced from the pricing page, and treat the in-process estimate as a leading indicator that you reconcile against the actual bill.

---

## Observability: logs you own and logs Bedrock keeps

Two layers of observability matter, and they're configured in different places.

**Bedrock model-invocation logging** is an account-and-region setting, *not* a per-call flag. You enable it once (in the Bedrock console under *Settings*, or via the `PutModelInvocationLoggingConfiguration` control-plane API) and Bedrock delivers full request/response records — optionally including prompt and completion data — to CloudWatch Logs and/or S3. This is your audit trail and your source of truth for what was actually sent to the model. Because it's platform-side, your Go code doesn't touch it; you just make sure it's turned on and pointed at a log group or bucket you retain.

**Your own structured logs and metrics** are what you emit from Go for latency, token counts, and error rate — the signals your dashboards and alerts run on. The key detail that ties your logs back to AWS support and to Bedrock's own logs is the **request ID**, which every SDK response exposes through its result metadata. Pull it with `awsmiddleware.GetRequestIDMetadata` and log it on every call:

```go
import (
	"context"
	"log/slog"
	"time"

	awsmiddleware "github.com/aws/aws-sdk-go-v2/aws/middleware"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
)

// instrumentedConverse wraps a Converse call with timing, token accounting,
// request-ID capture, and structured logging.
func instrumentedConverse(
	ctx context.Context,
	client *bedrockruntime.Client,
	log *slog.Logger,
	cost *CostTracker,
	in *bedrockruntime.ConverseInput,
) (*bedrockruntime.ConverseOutput, error) {

	start := time.Now()
	out, err := client.Converse(ctx, in)
	elapsed := time.Since(start)

	modelID := aws.ToString(in.ModelId)

	if err != nil {
		log.ErrorContext(ctx, "bedrock converse failed",
			slog.String("model", modelID),
			slog.Duration("latency", elapsed),
			slog.String("error", err.Error()),
		)
		return nil, err
	}

	// Request ID lives in the response's result metadata.
	reqID, _ := awsmiddleware.GetRequestIDMetadata(out.ResultMetadata)

	var inTok, outTok int32
	if out.Usage != nil {
		inTok = aws.ToInt32(out.Usage.InputTokens)
		outTok = aws.ToInt32(out.Usage.OutputTokens)
		cost.Record(modelID, out.Usage)
	}

	log.InfoContext(ctx, "bedrock converse ok",
		slog.String("model", modelID),
		slog.String("request_id", reqID),
		slog.Duration("latency", elapsed),
		slog.Int("input_tokens", int(inTok)),
		slog.Int("output_tokens", int(outTok)),
		slog.String("stop_reason", string(out.StopReason)),
	)
	return out, nil
}

var _ = types.TokenUsage{} // Usage type reference
```

Emit those same three numbers — latency, tokens, error/throttle counts — as metrics (CloudWatch, Prometheus, whatever you run) so you can alert on p99 latency creeping up, a spike in `ThrottlingException`, or tokens-per-request drifting. And if your service uses Bedrock **agents**, remember the agent already produces a trace of its reasoning and tool steps: capture that trace alongside these metrics for end-to-end visibility into multi-step runs.

**The gotcha:** log the `request_id` on *every* call, success or failure. When you open an AWS support case or cross-reference Bedrock's model-invocation logs, that ID is the join key. A latency spike with no request ID in your logs is a spike you can't investigate; one with the ID is a five-minute lookup.

---

## A production checklist

Before you route real traffic at a Bedrock Go service:

| Area | Check |
|---|---|
| Access | Model access granted in the target region; IAM policy scoped to specific actions and model/profile ARNs |
| Credentials | Running under an IAM role (ECS task / EKS IRSA / Lambda execution role); zero static keys in code or config |
| Reliability | Built-in retryer tuned via `WithRetryMaxAttempts` or a custom `retry.NewStandard`; **no** hand-rolled retry loop on top |
| Timeouts | `context` deadline per request; transport timeout on the HTTP client |
| Throughput | On-demand quotas understood; provisioned throughput or quota increase planned for steady high volume |
| Cost | Token usage recorded per model; rates sourced from the pricing page, reconciled against Cost Explorer |
| Observability | Model-invocation logging enabled to CloudWatch/S3; structured logs + metrics for latency, tokens, errors; request IDs logged |
| Errors | `ThrottlingException` and `AccessDeniedException` handled by type; agent traces captured where used |

---

## Key takeaways

- **Access is two gates.** Model access (per account/region, in the console) and IAM permissions are independent — both must open, and they fail differently.
- **Scope IAM narrowly.** Grant `bedrock:Converse*` / `bedrock:InvokeModel*` (and agent/KB actions only if used) on specific model, inference-profile, and provisioned ARNs — not `bedrock:*`.
- **Use roles, never keys.** `config.LoadDefaultConfig` picks up the ECS/EKS/Lambda role automatically and refreshes it; static credentials are a smell.
- **Let the SDK retry.** aws-sdk-go-v2 has exponential backoff with jitter built in — tune `MaxAttempts`, don't wrap it in your own loop, and bound the whole thing with a context deadline.
- **Measure tokens, cite prices.** Aggregate `Usage` per model in code; keep rates in config from the official pricing page; reconcile against the real bill.
- **Own your observability.** Turn on model-invocation logging platform-side, emit structured latency/token/error signals from Go, and log the SDK **request ID** on every call as your join key.

That closes the arc: from a single Converse call, through tools, retrieval, agents, and guardrails, to a service you can put on-call. The model was never the hard part — running it safely, cheaply, and observably is the engineering. Now you have both halves.

---

## Further reading

- [Security in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/security.html) and [Identity and access management](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html) — the authoritative IAM actions, resources, and policy examples.
- [Monitor Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html) and [Model invocation logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) — CloudWatch/S3 delivery and the logging configuration.
- [Amazon Bedrock quotas](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html) and [Provisioned Throughput](https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html) — on-demand limits and reserved capacity.
- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) — the current, model- and region-specific token rates.
- [`config`](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/config) and [`aws/retry`](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/aws/retry) on pkg.go.dev — `LoadDefaultConfig`, `WithRetryMaxAttempts`, `WithRetryer`, and `retry.NewStandard`.
- [`aws/middleware`](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/aws/middleware) — `GetRequestIDMetadata` for pulling the request ID out of response metadata.
