# step04 · Function Tools with Approvals

*How to gate a sensitive tool behind human consent: the run pauses, hands you an approval request, and only calls the tool once you approve.*

---

## What this lesson demonstrates

The previous lesson let the model call the weather tool silently. This one puts a **human in the loop**. You wrap the tool with `tool.ApprovalRequiredFunc`, and now instead of invoking it, the run pauses and hands you a `message.ToolApprovalRequestContent`. You approve or deny, feed your decision back with a *new* run on the same session, and the agent either invokes the tool or skips it. This is the pattern for gating side-effecting or sensitive tools behind consent.

## Marking a tool approval-required

The only change to the tool wiring is one wrapper:

```go
Config: agent.Config{
	Name: "WeatherAssistant",
	// ApprovalRequiredFunc marks the tool as needing approval: the run will
	// yield a ToolApprovalRequestContent instead of invoking it directly.
	Tools: []tool.Tool{tool.ApprovalRequiredFunc(weatherTool)},
},
```

The `weatherTool` itself is an ordinary `functool.MustNew` function; `ApprovalRequiredFunc` decorates it so the model can't fire it without your say-so.

## The approval loop

In `main`, the first `RunText` comes back carrying approval **requests**, not an answer. A loop then drives consent to completion:

```go
for {
	userResponses := collectApprovals(resp, os.Stdin, os.Stdout)
	if len(userResponses) == 0 {
		return
	}
	resp, err = a.RunMessage(ctx, message.New(userResponses...),
		agent.WithSession(session)).Collect()
	demo.Print(resp, err)
}
```

`collectApprovals` scans the response's contents for each `*message.ToolApprovalRequestContent`, prompts the user, and calls `request.CreateResponse(approved, "")` — which pairs your decision with the original request's `RequestID` so the agent knows which pending call it answers. When a run yields no more requests, you're done.

## What to notice

The **session is what makes this work**. It ties the successive runs together so the agent remembers the pending tool call while it waits for your answer; drop `agent.WithSession` and the second run wouldn't know what it's approving. Note the second run uses `RunMessage(message.New(userResponses...))`, not `RunText` — you're feeding structured approval content back in, not a text prompt.

The design is testable precisely because `collectApprovals` takes explicit `in`/`out` streams: a test can drive it with a scripted `"y\n"` and no real terminal, and the pure approval plumbing (approve → `CreateResponse`) is exercised offline.

## How it maps to the Agent Framework

`tool.ApprovalRequiredFunc` and `ToolApprovalRequestContent` are the SDK's human-in-the-loop primitives. The provider transports the approval request and response like any other message; the consent logic is yours. This is the same interruption model that later powers approvals inside group chats and workflows.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step04_function_tools_with_approvals
```

The offline test drives the approval plumbing with a fake credential; the live run is gated behind `AF_LIVE=1` with `az login` and `FOUNDRY_PROJECT_ENDPOINT`.

---

Next: [step05 · Structured Output](/blog/posts/maf-go-44-structured-output.html)
