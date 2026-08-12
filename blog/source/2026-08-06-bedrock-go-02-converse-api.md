# Calling a Model with the Converse API

*Your first real inference call in Go against Amazon Bedrock — using the unified, model-agnostic Converse API and the AWS SDK for Go v2, from client construction to reading tokens back off the response.*

---

In the last post we got credentials sorted and confirmed the account could see Bedrock. Now comes the part that actually earns its keep: sending a prompt to a model and getting text back, in Go, with types you can trust the compiler to check.

Bedrock gives you two doors into a model. The older one is `InvokeModel`, where you hand the service a raw JSON body shaped exactly the way that specific model family expects, and parse an equally model-specific JSON blob out of the response. It works, but the shape of that body changes from vendor to vendor — Anthropic's messages format is not Meta's is not Amazon's own. The newer door is **Converse**, a single request/response shape that Bedrock normalizes across every chat-capable model on the platform. You write your messages, roles, and inference parameters *once*, and switching models becomes a one-line change to the model id. This post lives entirely on the Converse side, and for new code you should too. We will note where `InvokeModel` still matters, but Converse is the default you want.

The catch — and the reason newcomers stall on their first call — is that the Go SDK models Bedrock's flexible content shapes as **union interfaces** implemented by `MemberXxx` structs. That is idiomatic aws-sdk-go-v2, but it looks alien if you've only ever unmarshaled JSON into a plain struct. We'll unpack it carefully, because getting it wrong is the number-one source of "why won't this compile / why is my text empty" questions.

---

## The two packages you need

Everything for runtime inference lives in `github.com/aws/aws-sdk-go-v2/service/bedrockruntime`. There is a separate `bedrock` service package, but that one is for control-plane work — listing foundation models, managing provisioned throughput, custom model jobs. For *calling* a model you want `bedrockruntime` and its companion `bedrockruntime/types` package, which holds the message, content-block, and configuration types.

```bash
go get github.com/aws/aws-sdk-go-v2/config
go get github.com/aws/aws-sdk-go-v2/aws
go get github.com/aws/aws-sdk-go-v2/service/bedrockruntime
```

The `config` package loads your credentials and region the standard way (env vars, shared config file, SSO, IAM roles). The `aws` package gives you the pointer helpers — `aws.String`, `aws.Float32`, `aws.Int32` — that you'll need because many optional fields on the request are pointers, so the SDK can tell "unset" apart from "set to zero."

---

## Constructing the client

The client is built from a loaded `aws.Config`. Nothing Bedrock-specific happens here — it's the same two-step you'd use for S3 or DynamoDB.

```go
cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion("us-east-1"))
if err != nil {
    log.Fatalf("load AWS config: %v", err)
}

client := bedrockruntime.NewFromConfig(cfg)
```

`LoadDefaultConfig` walks the standard credential chain, so if `aws configure` or your environment is already set up, this just works. I pass the region explicitly because Bedrock model availability differs by region, and being explicit saves a confusing failure later when a model id that exists in `us-east-1` isn't offered in the region your default profile happens to point at.

---

## Building the request

`client.Converse` takes a `*bedrockruntime.ConverseInput`. The three fields you'll touch on almost every call are `ModelId`, `Messages`, and — usually — `InferenceConfig`. A `System` prompt is common too.

```go
input := &bedrockruntime.ConverseInput{
    ModelId: aws.String("anthropic.claude-3-5-sonnet-20240620-v1:0"),
    System: []types.SystemContentBlock{
        &types.SystemContentBlockMemberText{
            Value: "You are a terse assistant. Answer in one sentence.",
        },
    },
    Messages: []types.Message{
        {
            Role: types.ConversationRoleUser,
            Content: []types.ContentBlock{
                &types.ContentBlockMemberText{
                    Value: "In one sentence, what is Amazon Bedrock?",
                },
            },
        },
    },
    InferenceConfig: &types.InferenceConfiguration{
        Temperature: aws.Float32(0.2),
        TopP:        aws.Float32(0.9),
        MaxTokens:   aws.Int32(300),
    },
}
```

Read that top to bottom, because every field is teaching you something about the shape.

`ModelId` is a `*string`. The value above is an example — a specific version of one Anthropic model. **Model ids are not universal constants.** They vary by region, they carry a version suffix that changes when the vendor ships a new revision, and some models are only reachable through an *inference profile* id (often prefixed with a region shorthand like `us.`) rather than the bare model id. Don't hardcode one from a blog post and expect it to be right forever — open the Bedrock console for your region, or list models via the control-plane API, and copy the id you're actually entitled to use.

`System` is a slice of `types.SystemContentBlock`. That's a union interface too, and its text implementation is `types.SystemContentBlockMemberText`. System content is optional — drop the field entirely and the model runs without a system prompt.

`Messages` is a `[]types.Message`, and this is the heart of the request. Each `types.Message` has exactly two fields you set: `Role` and `Content`.

- `Role` is a `types.ConversationRole` — an enum with two values, `types.ConversationRoleUser` and `types.ConversationRoleAssistant`. A single-turn call is one user message. A multi-turn conversation is the full alternating history you replay on each request; Bedrock is stateless, so *you* own the transcript.
- `Content` is `[]types.ContentBlock`, and content blocks are where the union interface bites.

`InferenceConfig` is a `*types.InferenceConfiguration`. `Temperature` and `TopP` are `*float32`; `MaxTokens` is an `*int32`. They're pointers so the SDK distinguishes "leave it at the model default" (nil) from "set it to zero," which is why you wrap literals in `aws.Float32` / `aws.Int32`. The whole struct is optional — omit it and the model uses its defaults.

---

## The content-block union, explained

This is the concept to slow down on. `types.ContentBlock` is not a struct. It's an **interface**, and Bedrock uses it because a content block can be many things — text, an image, a document, a tool-use request, a tool result. Rather than one fat struct with a dozen mostly-nil fields, the SDK defines one concrete type per variant, each named `ContentBlockMemberX`, and each one satisfies the `ContentBlock` interface.

For plain text, the variant is `types.ContentBlockMemberText`, which has a single exported field, `Value string`. You construct it as a pointer and append it to the slice:

```go
Content: []types.ContentBlock{
    &types.ContentBlockMemberText{Value: "Hello"},
}
```

The payoff is on the response side, and it's the trap. When you read the model's reply, you get back a `[]types.ContentBlock` — the interface, not the concrete type. You **cannot** index into a string or read a `.Value` off the interface directly. You have to *type-assert* (or type-switch) each block back to its concrete variant before you can touch its data. Newcomers who expect `content[0].Value` get a compile error and assume they've misconfigured something; in fact the SDK is forcing them to acknowledge that a block might not be text at all.

**The gotcha:** content is a union interface, not a string and not a struct — you must type-assert (or type-switch) each block to `*types.ContentBlockMemberText` before you can read `.Value`. Indexing it like a string, or reaching for a `.Value` field on the interface, won't compile. And treat "this block is text" as a runtime question, not a given: a tool-calling model can return a `ContentBlockMemberToolUse` block instead, and blindly asserting text on that yields the zero value.

---

## Reading the response

`out.Output` is itself a union — a `types.ConverseOutput` interface. For a normal chat completion the concrete variant is `*types.ConverseOutputMemberMessage`, whose `.Value` is a `types.Message` (same shape as the ones you sent, but with the assistant's role). You assert your way down to it, then walk its content blocks.

```go
out, err := client.Converse(ctx, input)
if err != nil {
    log.Fatalf("Converse call failed: %v", err)
}

msg, ok := out.Output.(*types.ConverseOutputMemberMessage)
if !ok {
    log.Fatalf("unexpected output type: %T", out.Output)
}

var reply strings.Builder
for _, block := range msg.Value.Content {
    if text, ok := block.(*types.ContentBlockMemberText); ok {
        reply.WriteString(text.Value)
    }
}
fmt.Println("Assistant:", reply.String())
```

Two unions, two assertions: one to get from `out.Output` to the message, one per content block to get from `ContentBlock` to text. Concatenating every text block (rather than grabbing `Content[0]`) is the robust habit — a response can legitimately arrive as several blocks.

Alongside the message, two fields tell you *how* the turn ended and *what it cost*:

- `out.StopReason` is a `types.StopReason` enum. Common values are `end_turn` (the model finished naturally), `max_tokens` (it hit your `MaxTokens` ceiling and was cut off — a signal to raise the limit or expect truncation), and `stop_sequence`. Check it before trusting the text is complete.
- `out.Usage` is a `*types.TokenUsage` with `InputTokens`, `OutputTokens`, and `TotalTokens`, each an `*int32`. This is your billing and budgeting signal — log it.

```go
fmt.Printf("stop reason: %s\n", out.StopReason)
if u := out.Usage; u != nil {
    fmt.Printf("tokens in=%d out=%d total=%d\n",
        aws.ToInt32(u.InputTokens),
        aws.ToInt32(u.OutputTokens),
        aws.ToInt32(u.TotalTokens))
}
```

`aws.ToInt32` is the mirror of `aws.Int32` — it safely dereferences a `*int32`, returning zero for nil, so you don't hand-write nil checks on every pointer.

---

## The complete program

Putting it together: load config, build the client, construct the request, call, extract text, report usage. Note the context with a deadline — a network call to a model should never hang forever.

```go
package main

import (
    "context"
    "fmt"
    "log"
    "strings"
    "time"

    "github.com/aws/aws-sdk-go-v2/aws"
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/bedrockruntime"
    "github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
)

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
    defer cancel()

    cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion("us-east-1"))
    if err != nil {
        log.Fatalf("load AWS config: %v", err)
    }
    client := bedrockruntime.NewFromConfig(cfg)

    input := &bedrockruntime.ConverseInput{
        ModelId: aws.String("anthropic.claude-3-5-sonnet-20240620-v1:0"),
        System: []types.SystemContentBlock{
            &types.SystemContentBlockMemberText{
                Value: "You are a terse assistant. Answer in one sentence.",
            },
        },
        Messages: []types.Message{
            {
                Role: types.ConversationRoleUser,
                Content: []types.ContentBlock{
                    &types.ContentBlockMemberText{
                        Value: "In one sentence, what is Amazon Bedrock?",
                    },
                },
            },
        },
        InferenceConfig: &types.InferenceConfiguration{
            Temperature: aws.Float32(0.2),
            MaxTokens:   aws.Int32(300),
        },
    }

    out, err := client.Converse(ctx, input)
    if err != nil {
        log.Fatalf("Converse call failed: %v", err)
    }

    msg, ok := out.Output.(*types.ConverseOutputMemberMessage)
    if !ok {
        log.Fatalf("unexpected output type: %T", out.Output)
    }

    var reply strings.Builder
    for _, block := range msg.Value.Content {
        if text, ok := block.(*types.ContentBlockMemberText); ok {
            reply.WriteString(text.Value)
        }
    }

    fmt.Println("Assistant:", reply.String())
    fmt.Printf("stop reason: %s\n", out.StopReason)
    if u := out.Usage; u != nil {
        fmt.Printf("tokens in=%d out=%d total=%d\n",
            aws.ToInt32(u.InputTokens),
            aws.ToInt32(u.OutputTokens),
            aws.ToInt32(u.TotalTokens))
    }
}
```

That compiles and runs against a real account with model access. If a field name here doesn't match what your SDK version exposes — the `types` package does evolve — don't guess. Open the exact version on pkg.go.dev, look at the `types` package, and match the `MemberXxx` names it lists; they're all there and named consistently.

---

## Handling the errors that actually happen

The three failures you'll meet first are worth naming, because their error messages don't always point at the real cause.

**Model access not granted.** Before an account can call a model, someone has to request access to it in the Bedrock console. If that hasn't happened, the call fails — and it comes back as an **access-denied** error, *not* a "not found." That surprises people who expect a missing resource to 404. If you see access-denied on a model id you're sure is spelled right, check the model-access page in the console before touching your code.

**The wrong id, or an id that needs a profile.** A model id valid in one region may not exist in another, and some models are only callable through an inference-profile id rather than the bare foundation-model id. A validation error about the model identifier usually means one of these, not a typo.

**A blown deadline.** Because we wrapped the call in a `context.WithTimeout`, a slow or hung request surfaces as a context-deadline-exceeded error rather than hanging your program. Treat that as "retry or raise the timeout," not "the model is broken."

```go
out, err := client.Converse(ctx, input)
if err != nil {
    if errors.Is(err, context.DeadlineExceeded) {
        log.Fatalf("request timed out: %v", err)
    }
    // Otherwise inspect err — AccessDenied, ValidationException, etc.
    log.Fatalf("Converse failed: %v", err)
}
```

For structured handling you can assert the error against the modeled types in the `types` package (for example the access-denied and validation exception types) instead of matching on strings — the SDK returns them as concrete error types you can `errors.As` into.

**The gotcha:** an empty or surprising reply is often a stop-reason problem, not an API problem. If `out.StopReason` is `max_tokens`, the model was cut mid-sentence and your `MaxTokens` is too low — the call "succeeded" and the text is simply truncated. Always read `StopReason` before concluding the model gave a bad answer.

---

## Converse vs. InvokeModel, briefly

| | Converse | InvokeModel |
|---|---|---|
| Request shape | One unified schema for all models | Per-model raw JSON body |
| Switching models | Change `ModelId` | Rewrite body + parsing |
| Messages & roles | Normalized (`types.Message`) | Model-specific fields |
| Best for | New multi-model code | Model-specific features not yet in Converse |

`InvokeModel` still exists and still has its place — occasionally a brand-new model parameter shows up in the raw API before it's surfaced through Converse. But for the everyday job of "send messages, get a reply," Converse removes an entire class of per-vendor JSON wrangling. Start there.

---

## Key takeaways

- **Prefer Converse.** One request/response shape across models means switching a model is a one-line `ModelId` change, not a rewrite of your JSON marshaling.
- **Content is a union interface.** Build text with `&types.ContentBlockMemberText{Value: ...}`, and on the way back *type-assert* each `types.ContentBlock` to `*types.ContentBlockMemberText` before reading `.Value`. You cannot index it like a string.
- **The output is a union too.** Assert `out.Output` to `*types.ConverseOutputMemberMessage`, then walk `msg.Value.Content`.
- **Pointers everywhere optional.** Use `aws.String`, `aws.Float32`, `aws.Int32` to set fields and `aws.ToInt32` to read them, so nil means "unset."
- **Read `StopReason` and `Usage`.** They tell you whether the answer is complete and what the turn cost — a `max_tokens` stop reason is truncation, not a bad model.
- **Model ids aren't constants,** and a missing access grant returns access-denied, not not-found. Check the console for the id and the grant.

When the exact field names matter, the `bedrockruntime` and `bedrockruntime/types` docs on pkg.go.dev are the authority — pin to your SDK version and match the `MemberXxx` names there rather than guessing.

---

## Further reading

- [Amazon Bedrock — Converse API documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)
- [Amazon Bedrock Runtime API reference — Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [pkg.go.dev — service/bedrockruntime](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime)
- [pkg.go.dev — service/bedrockruntime/types](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types)
- [pkg.go.dev — aws pointer helpers (aws.String / aws.Float32 / aws.Int32)](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/aws)
