# 02 · step04 — Function Tools With Approvals

*How to pause a run for human approval before the framework is allowed to execute a tool.*

---

## What this lesson demonstrates

In step03 the framework ran the `weather` tool the instant the model asked for it. That's fine for reads, but dangerous for a tool that spends money or mutates state. Wrap the same tool with `tool.ApprovalRequiredFunc` and the flow changes: the run **pauses** and hands you a `*message.ToolApprovalRequestContent` instead of an answer. You inspect the pending call, decide, and feed a response back with a second run. **Only an approved call executes** — the standard human-in-the-loop guardrail.

## The core code

One wrapper flips the behaviour; the tool body is unchanged:

```go
Config: agent.Config{
	Name:        "WeatherAgent",
	Middlewares: []agent.Middleware{mw},
	// Wrapping the tool is what turns "run it" into "ask first".
	Tools: []tool.Tool{tool.ApprovalRequiredFunc(weatherTool)},
},
```

The pause is *data*, not a callback — you find it by ranging the response, then resume:

```go
approved := askApproval(request, reply)
userResponses = append(userResponses, request.CreateResponse(approved, ""))
// second run: feed responses back in with RunMessage on the same session
resp, err = a.RunMessage(ctx, message.New(userResponses...), agent.WithSession(session)).Collect()
```

## What to notice

- **The pause is data, not control flow.** A paused run returns normally; the "we need approval" signal is a `*message.ToolApprovalRequestContent` you find by ranging `resp.Contents()`.
- **A session threads the two runs.** `CreateSession` + `agent.WithSession(session)` on both `RunText` and `RunMessage` is what lets the second run answer the *specific* paused call. Drop the session and the framework can't correlate the approval with its request — the gotcha here.
- **Request → response is explicit.** `request.CreateResponse(approved, reason)` builds the answer; `message.New(responses...)` bundles them; `RunMessage` resumes. An `approved==false` response *declines* the call rather than silently dropping it.

## How it maps to Azure AI Foundry

The Foundry model still drives the decision to call the tool, but `ApprovalRequiredFunc` intercepts before execution, so the SDK returns the pending call to you instead of invoking it. Because the pause/approve/resume dance depends on the live model, the full loop only runs live; the offline tests pin the pure pieces — `TestAskApproval` proves only `Y`/`y` approves, and `TestApprovalDetails` checks the name/argument extraction shown to the human. This is how you build spend-money or mutate-state tools safely on top of the Microsoft Agent Framework.

## Run it

```bash
go run ./tutorial/02-agents/agents/step04_using_function_tools_with_approvals
```

Type `Y` to approve (anything else declines). The program needs Foundry; the offline tests run without a network, and the live pause/approve/resume loop is gated behind `AF_LIVE=1`.

---

Next: [step05 · Structured Output](/blog/posts/maf-go-15-structured-output.html)
