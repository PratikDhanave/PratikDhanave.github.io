# Guardrails and Safety

*How to put Amazon Bedrock Guardrails in front of a model from Go — attaching one to a Converse call, screening raw text with ApplyGuardrail, and reading whether the guardrail actually intervened.*

---

A model that answers anything is a liability. The moment you expose a Bedrock-backed feature to real users, someone will try to make it produce hate speech, coax out a system prompt, ask it to draft self-harm instructions, or paste in a customer's credit-card number that you never wanted stored. You can try to prompt your way out of this — "never discuss X" in the system prompt — but instructions are suggestions, and a determined user will talk the model around them.

**Guardrails for Amazon Bedrock** are the managed answer. A guardrail is a policy object you configure once and then apply to model traffic. It evaluates text against a fixed set of policy types, and when something crosses a threshold it *intervenes* — blocking the message, masking the offending span, or returning a canned refusal you chose. Crucially it evaluates **both** directions: the user's input prompt on the way in, and the model's output on the way out. This post is about wiring that into Go with `aws-sdk-go-v2` — attaching a guardrail to a `Converse` call, and calling `ApplyGuardrail` to screen arbitrary text on its own.

I'll assume you've already got the earlier posts' setup: `config.LoadDefaultConfig` for credentials and region, and a `bedrockruntime.Client`. If a field name here doesn't match what your editor autocompletes, trust the compiler and pkg.go.dev over me — the SDK types move, and I'd rather you verify than copy a stale signature.

---

## What a guardrail actually evaluates

A guardrail is not one filter — it's a bundle of independently configured policies. When you apply it, Bedrock runs the text through every policy you enabled and aggregates the verdicts. The policy types are worth knowing by name, because the assessment result you get back in Go is broken down along exactly these lines:

- **Content filters.** Six harm categories — hate, insults, sexual, violence, misconduct, and a separate prompt-attack (jailbreak) detector. Each has a configurable *strength* (`NONE`, `LOW`, `MEDIUM`, `HIGH`) set independently for the input side and the output side. Higher strength catches more but also flags more borderline text.
- **Denied topics.** Named topics you define with a natural-language description and sample phrases — "investment advice", "competitor pricing", "medical diagnosis". The guardrail classifies whether the text falls into one and blocks it if so. This is how you enforce "the support bot does not give legal advice" without depending on the model's goodwill.
- **Sensitive information filters (PII).** A catalog of built-in PII types (email, phone, SSN, credit-card, name, address, and more) plus your own regex patterns. Each entry is set to either `BLOCK` (refuse the whole message) or `ANONYMIZE` (mask the span, e.g. replace it with `{EMAIL}`) so the rest of the text flows through redacted.
- **Word filters.** A managed profanity list plus a custom deny-list of exact words and phrases — brand names you never want uttered, slurs, a competitor you won't name.
- **Contextual grounding and relevance.** Two scored checks aimed at hallucination. *Grounding* measures whether the model's answer is supported by a source you supply; *relevance* measures whether it actually addresses the user's query. You set a threshold from 0 to 1, and responses that score below it are blocked.

A guardrail also has an **identifier** and **versions**. You create it through the control plane and Bedrock assigns it an ID; every time you publish, you get a new numbered version (`1`, `2`, …). There's also a mutable `DRAFT` version that reflects your latest un-published edits. Both the identifier and a version are required whenever you apply the guardrail — which brings us to the first thing people get wrong.

**The gotcha:** the `DRAFT` version is not stable — anyone editing the guardrail in the console changes what `DRAFT` does, live, under your running service. Pin a **published numeric version** in production (`GuardrailVersion: aws.String("3")`), and treat bumping it as a deliberate deploy, not something that drifts on its own.

---

## Creating a guardrail (conceptually)

Guardrails live on the **control plane**, not the runtime one. You create and version them with the `service/bedrock` client (`CreateGuardrail`, `CreateGuardrailVersion`, `UpdateGuardrail`), or — more sanely — through the console, CloudFormation, or Terraform, so the policy is reviewed and version-controlled like any other infra. Building the full policy definition in Go is a large, fiddly struct, and it belongs in your provisioning code, not your request path.

For this post the guardrail already exists. What matters at request time is two strings: the **guardrail ID** (something like `abcd1234efgh`) and the **version** you want to pin. Everything below assumes you've pulled those from config or environment.

```go
guardrailID := os.Getenv("BEDROCK_GUARDRAIL_ID")
guardrailVersion := os.Getenv("BEDROCK_GUARDRAIL_VERSION") // e.g. "3", not "DRAFT" in prod
```

---

## Way 1: attach the guardrail to a Converse call

The common case is: you're already calling `Converse` (from the earlier post), and you just want the guardrail to police that conversation. You do it by setting `GuardrailConfig` on the `ConverseInput`. Bedrock then screens the input messages before the model sees them and screens the model's reply before it reaches you.

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
)

func main() {
	ctx := context.Background()

	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		log.Fatalf("load config: %v", err)
	}
	client := bedrockruntime.NewFromConfig(cfg)

	userText := "I want to invest my savings. What stock should I buy today?"

	out, err := client.Converse(ctx, &bedrockruntime.ConverseInput{
		ModelId: aws.String("anthropic.claude-3-5-sonnet-20240620-v1:0"),
		Messages: []types.Message{
			{
				Role: types.ConversationRoleUser,
				Content: []types.ContentBlock{
					&types.ContentBlockMemberText{Value: userText},
				},
			},
		},
		GuardrailConfig: &types.GuardrailConfiguration{
			GuardrailIdentifier: aws.String(os.Getenv("BEDROCK_GUARDRAIL_ID")),
			GuardrailVersion:    aws.String(os.Getenv("BEDROCK_GUARDRAIL_VERSION")),
			Trace:               types.GuardrailTraceEnabled,
		},
	})
	if err != nil {
		log.Fatalf("converse: %v", err)
	}

	fmt.Println("stop reason:", out.StopReason)
	if resp, ok := out.Output.(*types.ConverseOutputMemberMessage); ok {
		for _, block := range resp.Value.Content {
			if txt, ok := block.(*types.ContentBlockMemberText); ok {
				fmt.Println("reply:", txt.Value)
			}
		}
	}
}
```

Two details do the work here. `GuardrailConfiguration` carries the ID and version. `Trace: types.GuardrailTraceEnabled` asks Bedrock to return *why* it did what it did — the per-policy assessment — in `out.Trace`. Without the trace you still get filtering, you just can't see the reasoning, which makes debugging a blocked message miserable.

### Reading whether it intervened

This is the part people skip, and it's the part that matters. When a guardrail blocks a message, `Converse` does **not** return an error. It returns a normal, successful response whose content is the guardrail's *blocked-message* text — the canned string you configured, like "I can't help with that." The signal that something was filtered is the **stop reason**:

```go
if out.StopReason == types.StopReasonGuardrailIntervened {
	log.Println("guardrail intervened — response was filtered")
}
```

So the flow is: check `StopReason` first. If it's `StopReasonGuardrailIntervened`, the "reply" you'd otherwise print is a refusal, and you should treat it as one — log it, maybe surface a friendlier message, don't feed it back into the model as if the user got a real answer. If you enabled the trace, `out.Trace.Guardrail` holds the assessment that explains which policy fired.

**The gotcha:** a guardrail intervention is a *successful* API call. If your code only checks `err != nil` and otherwise prints `out.Output`, a blocked response sails through looking like a normal answer — you'll happily show the user the guardrail's refusal string and never know a policy fired. Always branch on `StopReason == types.StopReasonGuardrailIntervened` before trusting the content.

---

## Way 2: screen text on its own with ApplyGuardrail

Attaching to `Converse` is convenient but coupled — the guardrail only runs when you call the model. Sometimes you want to evaluate text *without* a model call at all: screen a user's message before it ever reaches Bedrock (and skip the model call entirely if it's abusive), or check some content your app generated from another source. That's `ApplyGuardrail`.

`ApplyGuardrail` takes the guardrail ID and version, a `Source` telling it whether this text is an `INPUT` (a user prompt) or `OUTPUT` (a model response) — the distinction matters because content filters can be tuned differently per direction — and the `Content` to evaluate. It returns an `Action`, the possibly-modified `Outputs`, and the `Assessments` breakdown.

```go
func screenUserInput(ctx context.Context, client *bedrockruntime.Client, text string) (bool, string, error) {
	out, err := client.ApplyGuardrail(ctx, &bedrockruntime.ApplyGuardrailInput{
		GuardrailIdentifier: aws.String(os.Getenv("BEDROCK_GUARDRAIL_ID")),
		GuardrailVersion:    aws.String(os.Getenv("BEDROCK_GUARDRAIL_VERSION")),
		Source:              types.GuardrailContentSourceInput,
		Content: []types.GuardrailContentBlock{
			&types.GuardrailContentBlockMemberText{
				Text: &types.GuardrailTextBlock{
					Text: aws.String(text),
				},
			},
		},
	})
	if err != nil {
		return false, "", fmt.Errorf("apply guardrail: %w", err)
	}

	// Action tells you the verdict for the whole request.
	if out.Action == types.GuardrailActionGuardrailIntervened {
		// Outputs holds the message the guardrail wants shown instead.
		safe := ""
		if len(out.Outputs) > 0 && out.Outputs[0].Text != nil {
			safe = *out.Outputs[0].Text
		}
		return true, safe, nil // blocked == true
	}
	return false, text, nil // Action == NONE: text is clean, pass it through
}
```

`out.Action` is the top-level verdict: `GuardrailActionGuardrailIntervened` means a policy fired, `GuardrailActionNone` means the text passed clean. When it intervenes, `out.Outputs` carries the safe replacement text — for a PII policy set to `ANONYMIZE`, that's your original text with the sensitive spans masked (`{EMAIL}`, `{PHONE_NUMBER}`); for a hard block, it's the configured refusal string. And `out.Assessments` is the same per-policy breakdown the Converse trace gives you, so you can log *which* filter tripped.

Wired into a request handler, it's a cheap front gate:

```go
blocked, safeText, err := screenUserInput(ctx, client, userMessage)
if err != nil {
	http.Error(w, "screening failed", http.StatusInternalServerError)
	return
}
if blocked {
	// Never call the model. Return the guardrail's message.
	writeJSON(w, map[string]string{"reply": safeText})
	return
}
// safeText is the original (or PII-redacted) message — now call the model.
```

The payoff: an abusive or PII-laden prompt is caught before it costs you a model invocation, and if you use `ANONYMIZE` you can forward the *redacted* text to the model so it never ingests the raw credit-card number in the first place.

**The gotcha:** `Source` is not cosmetic. `INPUT` and `OUTPUT` can be configured with different content-filter strengths, and grounding checks only make sense for `OUTPUT`. Screen a user's prompt as `INPUT` and a model's answer as `OUTPUT` — mislabel them and you're applying the wrong half of your policy, silently.

---

## Converse trace vs. ApplyGuardrail: which to use

| You want to… | Use | Notes |
|---|---|---|
| Police a model conversation you're already having | `GuardrailConfig` on `Converse` | One call; check `StopReason` |
| Reject a user prompt before spending a model call | `ApplyGuardrail` with `Source: INPUT` | Standalone; check `Action` |
| Redact PII out of text before storing/forwarding it | `ApplyGuardrail` | Read the masked `Outputs` |
| Check output your app produced from another path | `ApplyGuardrail` with `Source: OUTPUT` | No model needed |
| See exactly which policy fired | `Trace` (Converse) or `Assessments` (ApplyGuardrail) | Enable trace to debug |

There's cost and latency to know about, too: applying a guardrail is a separate evaluation with its own per-text-unit pricing, and `ApplyGuardrail` adds a network round-trip. Don't screen the same text twice — if you already `ApplyGuardrail` on the input and redact it, you don't also need the input side of a Converse guardrail for that same text.

---

## Contextual grounding is not free hallucination detection

Grounding is the most over-hoped policy. People read "reduces hallucination" and expect the guardrail to somehow *know* when the model made something up. It can't — it has no oracle for truth. What contextual grounding actually does is compare the model's answer against a **grounding source you supply** and score how well the answer is supported by it. No source, no grounding check.

That means grounding only helps in a RAG-style flow where you're already passing retrieved documents as context — you provide those documents as the grounding source, and the guardrail flags answers that wander off them. If you're doing open-ended chat with no source material, the grounding policy has nothing to compare against.

**The gotcha:** contextual grounding needs the source text handed to it — it does not fact-check against the open world. Enable it only where you actually have grounding material to supply, and treat it as "is this answer consistent with what I gave the model", not "is this answer true".

---

## Defense in depth: guardrails complement your own checks

A guardrail is a strong layer, not the whole wall. It's an ML classifier making judgment calls, and like any classifier it has false negatives — a novel jailbreak phrasing, a PII format its detector doesn't recognize, an on-topic-but-harmful request. Lean on it as your *managed* safety layer, but keep your own controls around it:

- **Validate structurally** before the guardrail: length limits, rate limits, auth, and schema checks on anything a user submits. A guardrail won't stop someone from hammering your endpoint.
- **Screen input independently** with `ApplyGuardrail` so garbage never reaches the model and never appears in your logs unredacted.
- **Screen output**, whether via the Converse trace or a second `ApplyGuardrail`, and fail closed — if the guardrail call itself errors, don't ship the unscreened model text; return a safe fallback.
- **Keep application-level policy** in your own code for rules a guardrail can't express — per-user entitlements, business logic, "this account can't ask about that dataset".

Guardrails move the heavy, model-shaped safety work — harm classification, PII detection, topic policing — off your plate and onto a managed service you can version and audit. They don't move the *responsibility*. That still lives in your handler.

---

## Key takeaways

- **A guardrail evaluates both directions.** Input prompt on the way in, model output on the way out — one policy object, applied to both.
- **Attach it to `Converse` via `GuardrailConfig`**, and read `StopReason == types.StopReasonGuardrailIntervened` — an intervention is a *successful* call whose content is a refusal, not an error.
- **Use `ApplyGuardrail` to screen text standalone**, with `Source` set to `INPUT` or `OUTPUT`; branch on `Action` and read the (possibly redacted) `Outputs`.
- **Pin a published numeric version** in production — `DRAFT` mutates under you.
- **Grounding needs a source** you supply; it checks support against that source, not truth against the world.
- **Guardrails complement your validation**, they don't replace it — validate, screen, fail closed, and keep business rules in your own code.

When a field name doesn't match your autocomplete, believe the compiler: the exact `types` shapes are the authority, and pkg.go.dev is where I'd confirm anything here before shipping it.

---

## Further reading

- [Stop harmful content in models using Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) — the official user-guide overview of policy types, versions, and how evaluation works.
- [Components of a guardrail](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html) — content filters, denied topics, sensitive-information filters, word filters, and contextual grounding in detail.
- [`bedrockruntime` package — pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime) — the `ApplyGuardrail` and `Converse` operations and their inputs.
- [`bedrockruntime/types` — pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types) — `GuardrailConfiguration`, `GuardrailContentBlock`, `GuardrailAction`, and `StopReason` constants.
- [`bedrock` (control plane) — pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrock) — `CreateGuardrail` and `CreateGuardrailVersion` for provisioning guardrails from Go.
