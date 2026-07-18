# Human In Loop

*How an approval-required tool makes the server pause a run and wait for a human on the client to say yes or no.*

---

## What this lesson demonstrates

This client+server pair puts a human in the middle of a tool call. The server hosts a Foundry agent with one tool — `approve_expense_report` — that is marked **approval-required**. The model may *propose* calling it, but the framework will not run it until a human on the other end approves. The server enforces the pause; the client collects the y/n decision and sends it back.

## The server: gate the tool behind approval

The pure business logic is an ordinary function. What makes it human-gated is one wrapper:

```go
Config: agent.Config{
    Name:  "AGUIAssistant",
    Tools: []tool.Tool{tool.ApprovalRequiredFunc(newExpenseTool())}, // gate behind human approval
},
```

`tool.ApprovalRequiredFunc(...)` wraps the plain function tool so the framework marks it "needs approval". When the model wants to call it, the agent emits an approval *request* instead of executing — that is the human-in-the-loop pause. Everything else is the same `aguiprovider.NewJSONHTTPHandler` wiring from the earlier lessons.

## The client: an approval loop

The client can't just stream text and stop — it has to answer the approval and re-run. That is what `runWithApprovals` does:

```go
resp, err := a.RunMessage(ctx, current, agent.WithSession(session)).Collect()
if err != nil {
    return err
}
responses := collectApprovalResponses(resp.Contents(), decide)
if len(responses) == 0 {
    return nil // nothing left to approve — the run is finished
}
current = message.New(responses...) // feed decisions back in, loop again
```

`collectApprovalResponses` walks the run's contents and, for each `*message.ToolApprovalRequestContent`, asks the `decide` function (interactively: `stdinApprover` reading y/n from the terminal) and produces a response via `v.CreateResponse(approved, "")`. Those responses become the *next* input message, and the loop repeats until a run comes back with nothing pending.

## What to notice / the gotcha

The approval isn't a callback — it's a **message round-trip**. The run returns, surfaces its pending approvals, and you re-run with the decisions as new contents. The client also handles two shapes: a `ToolApprovalRequestContent` (the framework's gate) and a manual `request_approval` `FunctionCallContent`. The decision logic (`parseApproval`, `collectApprovalResponses`) is kept free of stdin and network so the offline test can drive the whole loop with a scripted approver.

## How it maps to the Microsoft Agent Framework

Approval-required tools are the framework's built-in mechanism for high-stakes actions — refunds, deployments, expense sign-off — where an autonomous model shouldn't act alone. Over AG-UI, the model runs against Azure AI Foundry on the server, but the *authority* stays with the human at the client. The server can't complete the tool call until a decision comes back, which is exactly the guarantee you want for irreversible operations.

## Run it

```bash
go run ./tutorial/02-agents/agui/step04_human_in_loop/server   # terminal 1 (needs az login + Foundry)
go run ./tutorial/02-agents/agui/step04_human_in_loop/client   # terminal 2
```

The tool wiring and approval helpers test offline; the end-to-end round-trip is gated behind `AF_LIVE=1`.

---

Next: [State Management](/blog/posts/maf-go-31-state-management.html)
