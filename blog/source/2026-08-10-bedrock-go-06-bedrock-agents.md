# Bedrock Agents

*How to invoke a managed Agent for Amazon Bedrock from Go — where the server owns the reason-act loop, and your job is to call InvokeAgent, range the event stream, accumulate the answer chunks, and read the trace for observability.*

---

In an earlier post we built tool use by hand: you declared tools, caught the `ToolUse` stop reason, ran the real Go function, fed the result back, and called Converse again — a `for` loop you owned end to end. That loop is powerful precisely because *you* drive it. But it is also code you have to write, test, and cap against runaway iterations, every single time.

**Agents for Amazon Bedrock** move that loop server-side. You author an agent once — a model, a set of instructions, one or more **action groups** (tools backed by a Lambda function or a plain function schema), and optionally a **knowledge base** for retrieval — and Bedrock runs the reason-act cycle *for* you. From Go you make a single call, `InvokeAgent`, and stream back the result. The model deciding to call a tool, the tool running, the model reading the result and deciding what's next: all of that happens inside the service. You watch it through a **trace**, but you do not orchestrate it.

This post is about *invoking* a prepared agent from Go with `github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime`. The contrast to hold onto: post 4 was "you own the loop with Converse tool use"; this post is "Bedrock owns the loop, you invoke the agent and stream its trace."

---

## Two ways to run an agent loop

The distinction matters enough to make it concrete before any code:

| | DIY tool use (Converse) | Managed agent (InvokeAgent) |
|---|---|---|
| Who runs the reason-act loop | You, in a Go `for` loop | Bedrock, server-side |
| Where tools execute | Your process (the Go function) | Lambda or a returned function-call contract |
| Where instructions live | Your `System` prompt each call | Baked into the agent at author time |
| What you call | `bedrockruntime.Converse` (repeatedly) | `bedrockagentruntime.InvokeAgent` (once per user turn) |
| Package | `service/bedrockruntime` | `service/bedrockagentruntime` |
| Retrieval / knowledge base | You wire it up | Attached to the agent, invoked automatically |
| Observability | You log each turn yourself | A structured **trace** streamed to you |

Neither is strictly better. The DIY loop gives you total control and keeps tools in-process; the managed agent trades that control for a runtime you don't maintain, plus first-class knowledge bases and a step-by-step trace. Reach for a managed agent when the orchestration itself is undifferentiated work you'd rather not own.

---

## What you author in the control plane (briefly)

There are **two** SDK surfaces, and mixing them up is the first stumbling block. The *control plane* — `github.com/aws/aws-sdk-go-v2/service/bedrockagent` — is where you build and version an agent. The *runtime* — `bedrockagentruntime` — is where you invoke it. This post lives almost entirely in the runtime, but you need a mental model of the control-plane lifecycle because the runtime call depends on it.

Conceptually, authoring an agent looks like this (via the console, IaC such as CloudFormation/Terraform, or the `bedrockagent` client):

1. **`CreateAgent`** — name the agent, pick the foundation model, and write the natural-language **instructions** that define its job.
2. **Attach action groups** (`CreateAgentActionGroup`) — each is a set of tools the agent may call, described either by an OpenAPI/function schema and backed by a **Lambda** function, or configured to hand control back to your application. Optionally attach a **knowledge base** for retrieval-augmented answers.
3. **`PrepareAgent`** — compile the current draft into an invocable version. Edits to instructions or action groups don't take effect until you prepare again.
4. **`CreateAgentAlias`** — publish a named, versioned pointer (an *alias*) that the runtime targets. The alias is what production traffic uses.

I'm deliberately not inventing the full field-by-field shape of these calls — consult the `bedrockagent` docs for the exact request structures, which differ by whether you use Lambda-backed or return-control action groups. The one fact that shapes your Go runtime code is the output of this process: an **agent id** and an **alias id**.

**The gotcha:** you invoke an *alias*, never the draft. A freshly created agent is not callable until you've run `PrepareAgent` and created at least one alias — until then `InvokeAgent` has nothing to point at. During development AWS provides a built-in test alias (`TSTALIASID`) that always tracks the latest prepared draft, which is convenient locally but should never be your production target; cut a real alias and pin to it so a mid-edit draft can't leak into live traffic.

---

## Invoking a prepared agent

With an agent id and alias id in hand, the runtime call is refreshingly small. Build a `bedrockagentruntime.Client` from your AWS config, then call `InvokeAgent` with four things: the agent id, the alias id, a **session id** you choose, and the user's `InputText`.

```go
import (
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime"
)

client := bedrockagentruntime.NewFromConfig(cfg)

out, err := client.InvokeAgent(ctx, &bedrockagentruntime.InvokeAgentInput{
	AgentId:      aws.String(agentID),      // from CreateAgent
	AgentAliasId: aws.String(agentAliasID), // from CreateAgentAlias (not the draft)
	SessionId:    aws.String(sessionID),    // YOU pick this; reuse it for memory
	InputText:    aws.String("What's the status of order 4021?"),
	EnableTrace:  aws.Bool(true),           // stream the reasoning/tool steps too
})
if err != nil {
	log.Fatalf("InvokeAgent request failed: %v", err)
}
```

As with `ConverseStream`, the `err` here is the error from *starting* the invocation — bad ids, throttling, missing credentials, an agent that isn't prepared. A nil error means the stream opened, **not** that the agent finished. Anything that goes wrong mid-run surfaces on the stream, which is the next section.

`EnableTrace` defaults to off. Set it to `true` and Bedrock interleaves trace events describing each reasoning and tool step; leave it off and you get only the final answer chunks. Turn it on in development and for debugging, and weigh leaving it on in production against the extra payload — the trace can be verbose.

---

## The response is an event stream

`InvokeAgentOutput` doesn't hand you a finished string. Like `ConverseStream`, it exposes an **event stream**: `out.GetStream()` returns the stream handle, and its `.Events()` method gives you a channel of `types.ResponseStream` — a union interface. You `range` the channel until Bedrock closes it and type-switch on each concrete event.

The two events you care about:

- **`*types.ResponseStreamMemberChunk`** — a piece of the final answer. Its `.Value` is a `types.PayloadPart`, whose `.Bytes` field is a `[]byte` slice of answer text. Append these across the stream to assemble the reply.
- **`*types.ResponseStreamMemberTrace`** — a step in the agent's reasoning: which tool it decided to call, what a knowledge base returned, how it framed the final response. Present only when you set `EnableTrace: true`.

The stream also carries typed exception events (throttling, validation, an internal error, a model that isn't ready) as their own union members, plus return-control and file members for advanced action-group patterns — but chunk and trace are the backbone of a normal invocation.

```go
stream := out.GetStream()
defer stream.Close()

var answer strings.Builder

for event := range stream.Events() {
	switch e := event.(type) {
	case *types.ResponseStreamMemberChunk:
		// A slice of the final answer text.
		answer.Write(e.Value.Bytes)

	case *types.ResponseStreamMemberTrace:
		// A reasoning/tool step — see the trace section below.
		logTrace(e.Value)
	}
}

if err := stream.Err(); err != nil {
	log.Fatalf("agent stream error: %v", err)
}
```

The `types` here come from `github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime/types` — a *different* `types` package from the `bedrockruntime` one you used for Converse. The names rhyme (`GetStream`, `Events`, `Err`, `Close`) because both are Smithy event streams, but they are distinct types; import the runtime-agent package, not the plain runtime one.

**The gotcha:** the stream **mixes** chunk and trace events, so you must type-switch and cannot assume every event is answer text. A common bug is to grab `.Value.Bytes` off whatever event arrives — but a trace event has no such field, and treating every event as a chunk either won't compile or silently drops the reasoning steps. Match `*types.ResponseStreamMemberChunk` for answer bytes and `*types.ResponseStreamMemberTrace` for observability, and ignore the rest unless you need them.

---

## Always check Err and Close the stream

The same discipline that streaming Converse demanded applies here, for the same reason. The `range` over `stream.Events()` ends when the channel closes — and the channel closes on **both** a clean finish and a mid-run failure (a dropped connection, a timeout, a server-side error after the agent started working). Without a trailing `stream.Err()` check, a truncated answer is indistinguishable from a complete one: your loop just ends and you return whatever you accumulated as if it were the whole reply.

**The gotcha:** `defer stream.Close()` and a post-loop `if err := stream.Err(); err != nil` are not optional. `Close()` releases the underlying connection; `Err()` is the *only* place a mid-stream error surfaces, because `InvokeAgent` itself already returned nil. Skip the `Err()` check and you will ship silently truncated agent answers that look fine in a demo and fail in production under flaky networks.

---

## Reading the trace for observability

When you set `EnableTrace: true`, each `*types.ResponseStreamMemberTrace` carries a `types.TracePart`. That struct includes routing metadata — the `AgentId`, `AgentAliasId`, and `SessionId` the step belongs to — and a `Trace` field that is *itself a union* describing what kind of step it was: pre-processing, orchestration (the core reason-act step, including tool invocations and knowledge-base lookups), post-processing, guardrail evaluation, or a failure.

Because that inner `Trace` is a union with several member types whose exact names vary by SDK version, keep your first pass minimal and verify the concrete member names on pkg.go.dev before switching on them. A pragmatic starting point is to log the whole trace part and drill in later:

```go
func logTrace(tp types.TracePart) {
	// The orchestration/pre/post-processing detail lives in tp.Trace,
	// a union — inspect its concrete member types on pkg.go.dev and
	// type-switch on the ones you care about (orchestration is the core one).
	log.Printf("trace step for session %s: %+v",
		aws.ToString(tp.SessionId), tp.Trace)
}
```

The trace is how you answer "*why* did the agent say that?" without owning the loop. It shows the rationale the model produced before acting, which action group or knowledge base it reached for, the inputs it passed, and what came back — the same visibility your hand-written Converse loop gave you by logging each turn, except Bedrock produces it for you. Treat it as your debugging and audit surface: capture it in development, and consider sampling it in production for a durable record of agent decisions.

---

## Sessions and multi-turn memory

The `SessionId` is a string **you** choose, and it is how the agent remembers a conversation. Send the same session id across successive `InvokeAgent` calls and Bedrock threads them into one continuous exchange — the agent's earlier turns, the tools it called, and the context it built all carry forward. Start a new session id and the agent begins with a clean slate.

```go
sessionID := uuid.NewString() // one per conversation

// Turn 1
invoke(ctx, client, sessionID, "Look up order 4021.")
// Turn 2 — same sessionID, so the agent still knows which order you mean
invoke(ctx, client, sessionID, "When will it ship?")
```

You are not resending the transcript the way you appended messages in the Converse loop — with a managed agent, the session id *is* the handle to the server-side conversation state. That's a real convenience: no growing `[]types.Message` to marshal each turn. It also means the session's lifetime and privacy are Bedrock's concern, governed by the agent's configuration.

**The gotcha:** reuse the session id for continuity, and mint a fresh one to start over — this is the single most common source of confusing agent behavior. Accidentally generate a new id every request (for example, calling `uuid.NewString()` inside your per-request handler) and every turn looks like a brand-new user to the agent, so "when will it ship?" answers with "which order?". Conversely, share one hard-coded session id across different end users and you cross-contaminate their conversations. Scope the session id to exactly one logical conversation: one user, one thread.

---

## A complete example

Putting it together — build the client, invoke the alias with a session id, stream the answer to stdout, and surface any mid-stream error:

```go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime"
	"github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime/types"
	"github.com/google/uuid"
)

func main() {
	ctx := context.Background()

	cfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		log.Fatalf("load AWS config: %v", err)
	}
	client := bedrockagentruntime.NewFromConfig(cfg)

	const (
		agentID      = "ABCDEFGHIJ"  // from CreateAgent
		agentAliasID = "KLMNOPQRST"  // from CreateAgentAlias — an ALIAS, not the draft
	)
	sessionID := uuid.NewString() // reuse across turns of ONE conversation

	answer, err := invoke(ctx, client, agentID, agentAliasID, sessionID,
		"What's the status of order 4021?")
	if err != nil {
		log.Fatalf("invoke agent: %v", err)
	}
	fmt.Printf("\n\nFinal answer:\n%s\n", answer)
}

func invoke(ctx context.Context, client *bedrockagentruntime.Client,
	agentID, aliasID, sessionID, question string) (string, error) {

	out, err := client.InvokeAgent(ctx, &bedrockagentruntime.InvokeAgentInput{
		AgentId:      aws.String(agentID),
		AgentAliasId: aws.String(aliasID),
		SessionId:    aws.String(sessionID),
		InputText:    aws.String(question),
		EnableTrace:  aws.Bool(true),
	})
	if err != nil {
		return "", fmt.Errorf("start invocation: %w", err)
	}

	stream := out.GetStream()
	defer stream.Close()

	var answer strings.Builder
	for event := range stream.Events() {
		switch e := event.(type) {
		case *types.ResponseStreamMemberChunk:
			text := string(e.Value.Bytes)
			fmt.Print(text) // live output as the agent produces it
			answer.WriteString(text)

		case *types.ResponseStreamMemberTrace:
			// Observability only — the reasoning/tool steps. See notes above.
			log.Printf("[trace] session=%s", aws.ToString(e.Value.SessionId))
		}
	}

	if err := stream.Err(); err != nil {
		return "", fmt.Errorf("agent stream: %w", err) // the ONLY place mid-run errors show
	}
	return answer.String(), nil
}
```

Ask *"What's the status of order 4021?"* against an agent whose action group is wired to an order-lookup Lambda, and the shape of the run is: Bedrock reasons about the request, decides to call the order-lookup tool, runs it (in Lambda, not your process), reads the result, and streams back prose like *"Order 4021 shipped yesterday and is due to arrive Thursday."* You see the answer arrive as chunk events; if `EnableTrace` is on, you also see the intermediate reasoning and the tool call as trace events — but you never wrote the loop that connected them.

---

## Key takeaways

- **The agent owns the loop.** With Converse tool use you drive a `for` loop in Go; with a Bedrock agent you call `InvokeAgent` once per user turn and the reason-act cycle — tool calls, knowledge-base lookups, re-reasoning — runs server-side.
- **Author in the control plane, invoke in the runtime.** `bedrockagent` (CreateAgent / action groups / PrepareAgent / CreateAgentAlias) builds and versions the agent; `bedrockagentruntime.InvokeAgent` runs it. They are two different SDK packages.
- **You invoke an alias, not the draft.** An agent isn't callable until it's prepared and has an alias. Pin production to a real alias; the built-in test alias is for local iteration only.
- **The response is a mixed event stream.** Type-switch: `*types.ResponseStreamMemberChunk` carries answer bytes in `.Value.Bytes`; `*types.ResponseStreamMemberTrace` carries reasoning steps for observability (only when `EnableTrace` is true).
- **Always `defer stream.Close()` and check `stream.Err()`.** `InvokeAgent` returned nil already — mid-run failures surface only on `Err()`, so skipping it ships silently truncated answers.
- **The session id is your memory handle.** Reuse it across turns of one conversation for continuity; mint a fresh one to start clean; never share it across users. Verify exact trace member names on pkg.go.dev before switching on them.

A managed agent is the right call when the orchestration is plumbing you'd rather not maintain and you want knowledge bases and a trace out of the box. When you need every tool in your own process and total control of the loop, the DIY Converse approach from the tool-use post still wins — the two are complementary tools, not rivals.

---

## Further reading

- [Agents for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html) — the official overview of agents, action groups, knowledge bases, and the prepare/alias lifecycle.
- [InvokeAgent API reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_InvokeAgent.html) — the runtime request/response contract, including sessions, trace, and the response event stream.
- [`bedrockagentruntime` package](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime) and its [`types`](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime/types) — `InvokeAgentInput`, the `ResponseStream` union, `ResponseStreamMemberChunk`, `ResponseStreamMemberTrace`, `PayloadPart`, and `TracePart`.
- [`bedrockagent` package](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockagent) — the control-plane client for `CreateAgent`, `CreateAgentActionGroup`, `PrepareAgent`, and `CreateAgentAlias`.
