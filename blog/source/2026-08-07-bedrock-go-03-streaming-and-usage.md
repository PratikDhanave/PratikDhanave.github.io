# Streaming and Token Usage

*How to stream Amazon Bedrock responses token-by-token with the aws-sdk-go-v2 Converse API, decode the event stream with a double type-switch, and account for tokens and cost from the metadata event — accurately, in Go.*

---

In the previous post we called `client.Converse(...)` and got the whole reply back in one `ConverseOutput`. That is fine for short answers, but a model generating a few hundred tokens keeps the user staring at a spinner for seconds. **Streaming** fixes the perceived latency: you print each fragment as the model produces it, so text appears to type itself onto the screen.

Bedrock exposes this through `ConverseStream`, a near-twin of `Converse` that returns an **event stream** instead of a single response. The trade-off is that you now have to decode a sequence of union events rather than read one struct — and Go's type system makes that decode explicit. This post walks the whole loop: firing the request, ranging the event channel, unwrapping the nested delta unions, and reading token usage off the final metadata event so you can price a request.

Everything below uses `github.com/aws/aws-sdk-go-v2/service/bedrockruntime` and its `types` package. I assume you already have a `*bedrockruntime.Client` and a model id from the Converse basics post.

---

## ConverseStream: same input, streaming output

`ConverseStreamInput` takes the **same fields** as `ConverseInput` — `ModelId`, `Messages`, `System`, `InferenceConfig`, `ToolConfig`. If you can build a Converse request, you can build a ConverseStream request; only the call and the response handling change.

```go
out, err := client.ConverseStream(ctx, &bedrockruntime.ConverseStreamInput{
	ModelId: aws.String(modelID),
	Messages: []types.Message{
		{
			Role: types.ConversationRoleUser,
			Content: []types.ContentBlock{
				&types.ContentBlockMemberText{Value: "Explain goroutine leaks in three sentences."},
			},
		},
	},
	InferenceConfig: &types.InferenceConfiguration{
		MaxTokens:   aws.Int32(512),
		Temperature: aws.Float32(0.3),
	},
})
if err != nil {
	log.Fatalf("ConverseStream request failed: %v", err)
}
```

Note what `err` covers here: it is the error from *starting* the stream — bad model id, throttling, a malformed request, missing credentials. A successful return means the connection opened, **not** that generation finished cleanly. Errors that happen mid-generation surface elsewhere, and that distinction is the source of the most common streaming bug (more on that below).

---

## Ranging the event stream

`out.GetStream()` returns the stream handle. Its `.Events()` method gives you a channel of `types.ConverseStreamOutput` — a union interface. You `range` the channel until Bedrock closes it, and inside the loop you type-switch on which concrete event arrived.

```go
stream := out.GetStream()
defer stream.Close()

for event := range stream.Events() {
	switch e := event.(type) {
	case *types.ConverseStreamOutputMemberMessageStart:
		// The assistant turn is beginning; e.Value.Role is the role.

	case *types.ConverseStreamOutputMemberContentBlockDelta:
		// An incremental chunk — decoded in the next section.

	case *types.ConverseStreamOutputMemberContentBlockStop:
		// One content block finished.

	case *types.ConverseStreamOutputMemberMessageStop:
		fmt.Printf("\n[stop reason: %s]\n", e.Value.StopReason)

	case *types.ConverseStreamOutputMemberMetadata:
		// Token usage and latency land here — see the usage section.
	}
}

if err := stream.Err(); err != nil {
	log.Fatalf("stream error: %v", err)
}
```

The lifecycle is predictable: one `MessageStart`, then for each content block a `ContentBlockStart` (omitted above — it carries no text for plain replies), a run of `ContentBlockDelta` events, and a `ContentBlockStop`; finally a `MessageStop` with the stop reason and a `Metadata` event with usage. Tool-use replies interleave more block types, but text generation is this simple shape.

**The gotcha:** you **must** check `stream.Err()` after the range loop ends. The `range` terminates when the channel closes — and the channel closes on *both* a clean finish and a mid-stream failure (a dropped connection, a timeout, a server-side error after generation started). Without the `stream.Err()` check, a truncated response is indistinguishable from a complete one: your loop just ends and you print whatever you got as if it were the full answer. Always pair the range with a trailing `stream.Err()` and a `defer stream.Close()`.

---

## Decoding a delta: the second type-switch

The interesting event is `ConverseStreamOutputMemberContentBlockDelta`. Its `.Value` is a `types.ContentBlockDeltaEvent`, and inside that, `.Value.Delta` is **itself a union** — `types.ContentBlockDelta`. That second union is why decoding text takes two type-switches, not one: the outer switch tells you "this is a delta event," and the inner switch tells you "this delta is text" (versus a tool-use argument fragment, a reasoning chunk, and so on).

The text variant is `*types.ContentBlockDeltaMemberText`, whose `.Value` is the incremental `string`.

```go
case *types.ConverseStreamOutputMemberContentBlockDelta:
	switch d := e.Value.Delta.(type) {
	case *types.ContentBlockDeltaMemberText:
		fmt.Print(d.Value) // the incremental piece of text
		builder.WriteString(d.Value)
	}
```

Printing `d.Value` as it arrives is what produces the live "typing" effect. The `builder` is a `strings.Builder` you keep around if you also want the assembled full message at the end — Bedrock never hands you the complete text in one place during streaming, so if you need it you concatenate the deltas yourself.

**The gotcha:** the delta is a **nested union**, so a single type-switch is not enough — `e.Value.Delta` is an interface you must switch on again. If you only match the outer `ContentBlockDelta` event and try to read text off it directly, it won't compile, because the event doesn't carry a string; the string lives one union deeper. Two events, two switches.

---

## A complete streaming example

Putting the pieces together — fire the request, stream text to stdout, accumulate the full reply, and capture usage from the metadata event:

```go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
)

func main() {
	ctx := context.Background()

	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		log.Fatalf("load AWS config: %v", err)
	}
	client := bedrockruntime.NewFromConfig(cfg)

	modelID := "anthropic.claude-3-5-sonnet-20240620-v1:0"

	out, err := client.ConverseStream(ctx, &bedrockruntime.ConverseStreamInput{
		ModelId: aws.String(modelID),
		Messages: []types.Message{
			{
				Role: types.ConversationRoleUser,
				Content: []types.ContentBlock{
					&types.ContentBlockMemberText{
						Value: "Explain goroutine leaks in three sentences.",
					},
				},
			},
		},
		InferenceConfig: &types.InferenceConfiguration{
			MaxTokens: aws.Int32(512),
		},
	})
	if err != nil {
		log.Fatalf("ConverseStream request failed: %v", err)
	}

	stream := out.GetStream()
	defer stream.Close()

	var builder strings.Builder
	var usage *types.TokenUsage

	for event := range stream.Events() {
		switch e := event.(type) {
		case *types.ConverseStreamOutputMemberContentBlockDelta:
			if d, ok := e.Value.Delta.(*types.ContentBlockDeltaMemberText); ok {
				fmt.Print(d.Value)
				builder.WriteString(d.Value)
			}

		case *types.ConverseStreamOutputMemberMessageStop:
			fmt.Printf("\n\n[stop reason: %s]\n", e.Value.StopReason)

		case *types.ConverseStreamOutputMemberMetadata:
			usage = e.Value.Usage
		}
	}

	if err := stream.Err(); err != nil {
		log.Fatalf("stream error: %v", err)
	}

	if usage != nil {
		fmt.Printf("tokens: input=%d output=%d total=%d\n",
			aws.ToInt32(usage.InputTokens),
			aws.ToInt32(usage.OutputTokens),
			aws.ToInt32(usage.TotalTokens),
		)
	}

	_ = builder.String() // the full assembled reply, if you need it
}
```

The `aws.ToInt32` helper safely dereferences the `*int32` pointers the SDK uses (returning `0` for a nil pointer), which keeps the print statement free of nil checks.

---

## Token usage and cost

Every Bedrock request reports how many tokens it consumed, and that is the number your bill is built from. Where you read it depends on the call:

- **Non-streaming** (`Converse`): `out.Usage`, a `*types.TokenUsage`, is on the response struct directly.
- **Streaming** (`ConverseStream`): usage rides on the `ConverseStreamOutputMemberMetadata` event as `e.Value.Usage` — the same `*types.TokenUsage` type. The metadata event also typically carries latency in `e.Value.Metrics`.

`TokenUsage` has three fields worth knowing:

| Field | Meaning |
|---|---|
| `InputTokens` | Tokens in your prompt — system prompt, message history, tool schemas, the current user turn |
| `OutputTokens` | Tokens the model generated in its reply |
| `TotalTokens` | `InputTokens + OutputTokens` |

The split matters because **input and output tokens are priced differently** — output tokens almost always cost more per token than input tokens. That is why a chatbot with a long system prompt and short replies has a very different cost profile from a summarizer that reads a little and writes a lot.

**The gotcha:** in a stream, usage arrives **only** on the final `Metadata` event — never on the per-delta events. If you try to read a token count while ranging the deltas, there is nothing there yet. Capture usage in a variable inside the `Metadata` case (as above) and read it *after* the loop, once you have also confirmed `stream.Err() == nil`. A stream that errors out before the metadata event gives you no usage at all.

### Computing cost in Go

Bedrock pricing is **per-token, and both model-specific and region-specific** — a Claude model in `us-east-1` is priced differently from a Llama model, or the same model in another region. Rates are commonly published per 1,000 tokens or per 1,000,000 tokens depending on the page. I am deliberately **not** putting dollar figures here, because they change and would go stale: look up the current numbers on the Bedrock pricing page for your exact model and region, then plug them into a formula like this.

```go
// Fill these in from the current Bedrock pricing page for YOUR model + region.
// Example units: USD per 1,000 tokens. Match the units to whatever the page quotes.
const (
	inputPricePer1K  = 0.0 // e.g. price of 1,000 input tokens
	outputPricePer1K = 0.0 // e.g. price of 1,000 output tokens
)

func requestCostUSD(u *types.TokenUsage) float64 {
	if u == nil {
		return 0
	}
	in := float64(aws.ToInt32(u.InputTokens)) / 1000.0 * inputPricePer1K
	out := float64(aws.ToInt32(u.OutputTokens)) / 1000.0 * outputPricePer1K
	return in + out
}
```

Keeping the rates as named constants (or, better, config values loaded per model) means the formula never hard-codes a price you would have to hunt down and update later. When AWS changes pricing or you switch models, you edit one place.

### Practical accounting tips

- **Accumulate deltas yourself if you need the full text.** The stream never replays the complete message; the `strings.Builder` pattern above is the only way to get it. You need this for logging, for storing the assistant turn back into your message history, or for post-processing.
- **Measure usage per request, not per session estimate.** The metadata event gives you exact counts — log `InputTokens`/`OutputTokens` per call so budgeting is based on real numbers rather than a token estimate from counting characters.
- **Watch input tokens grow in conversations.** Every turn resends the full history as input, so input tokens climb with conversation length. If cost creeps up, that growing prompt is usually why — trim or summarize old turns.
- **Usage is reported even on a truncated reply.** If `StopReason` is `max_tokens`, you still pay for the output generated up to the cutoff, and the metadata event reflects it. Check the stop reason when a reply looks cut off.

---

## Key takeaways

- **`ConverseStream` takes the same input as `Converse`** — the only real work is decoding the event stream it returns instead of reading one struct.
- **Range `out.GetStream().Events()` and type-switch** on `ConverseStreamOutput` variants: `MessageStart`, `ContentBlockDelta`, `ContentBlockStop`, `MessageStop`, `Metadata`.
- **Text lives two unions deep.** Match `*ContentBlockDelta`, then switch again on `.Value.Delta` for `*ContentBlockDeltaMemberText` to reach the incremental string.
- **Always check `stream.Err()` after the loop** and `defer stream.Close()` — a mid-stream failure otherwise looks exactly like a clean finish.
- **Usage comes from the `Metadata` event when streaming** (`out.Usage` when not). Input and output tokens are priced separately; compute cost with rates you read from the current pricing page, not from hard-coded numbers.

Streaming turns a slow-feeling call into a responsive one, and the metadata event turns every request into a measurable, budgetable unit. Next in the series we build on this to handle tool use over Converse, where the delta stream carries function-call arguments instead of plain text.

---

## Further reading

- [Amazon Bedrock ConverseStream API reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseStream.html) — the event types and request/response shape from the source.
- [Use the Converse API — Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/converse-api.html) — how Converse and ConverseStream fit together, including tokens and stop reasons.
- [`bedrockruntime` package on pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime) — the client, `ConverseStreamInput`, and `GetStream()`.
- [`bedrockruntime/types` on pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types) — the `ConverseStreamOutput`, `ContentBlockDelta`, and `TokenUsage` union and struct definitions.
- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) — current per-token rates by model and region (look up your exact numbers here).
