# AG-UI Human-in-the-Loop: The Server

*The server hosts an agent with one approval-gated tool — the model may propose calling it, but the framework refuses to run it until a human on the other end says yes.*

---

## What this lesson demonstrates

Human-in-the-loop is a pause enforced by the server. The Foundry agent hosts a single tool, `approve_expense_report`, that is marked *approval-required*. When the model wants to call it, the agent does not run it — it emits an approval request over AG-UI instead. A separate client program collects the human's decision and sends it back, and only then does the call proceed.

The server's job is to enforce the pause. Everything hinges on one wrapper.

## The real code

`newHandler` builds the agent and wraps the plain tool with `tool.ApprovalRequiredFunc`:

```go
a := foundryprovider.NewAgent(
	endpoint,
	cred,
	foundryprovider.ModelDeployment(model),
	foundryprovider.AgentConfig{
		Instructions: "You are a helpful assistant in charge of approving expenses.",
		Config: agent.Config{
			Name:  "AGUIAssistant",
			Tools: []tool.Tool{tool.ApprovalRequiredFunc(newExpenseTool())}, // gate this tool behind human approval
		},
	},
)
```

`newExpenseTool` is an ordinary `functool.MustNew` tool around `approveExpenseReport`. On its own it would auto-run. `tool.ApprovalRequiredFunc(...)` wraps it so the framework marks it "needs approval" — that is the load-bearing line. The rest is the familiar `aguiprovider.NewJSONHTTPHandler` mounted at `/`.

## What to notice

- **Approval is a wrapper, not a config flag.** Unlike frontend tools (which flipped `DisableFuncAutoCall`), the gate here is applied per-tool by wrapping it. You can host approval-gated and freely-running tools side by side in the same `Tools` slice.
- **The pure function stays plain.** `approveExpenseReport(ctx, id string)` returns `"Expense report <id> approved"` — no framework, no network. Keeping it a named function lets the offline test call it directly with a plain string, independent of the tool's JSON encoding.
- **The test asserts the gate is applied.** `main_test.go` builds the tool, agent, and handler with a fake credential and checks the tool is approval-required, the agent carries it, and the handler is non-nil. No model is called; the live bind needs `AF_LIVE`.

## How it maps to the Microsoft Agent Framework Go SDK

`tool.ApprovalRequiredFunc` decorates any `tool.FuncTool` so the runtime emits an approval request rather than executing it. Over AG-UI, that request becomes an event the client answers, and the answer flows back as the approval the framework was waiting on. It is the SDK's built-in way to put a human in the middle of an autonomous run.

## Run it

`go run ./tutorial/02-agents/agui/step04_human_in_loop/server`, then point the matching AG-UI client at it. Needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` (+ `FOUNDRY_MODEL`). Offline tests run with `go test ./...`; the live bind skips without `AF_LIVE=1`.

---

Next: [AG-UI State Management — The Server](/blog/posts/maf-go-91-state-management-server.html)

## Key takeaways

- Human-in-the-loop is a pause enforced by the server: an approval-required tool makes the agent emit an approval request over AG-UI instead of running the call, and it proceeds only after a human's decision comes back.
- The load-bearing line is `tool.ApprovalRequiredFunc(newExpenseTool())`: approval is a per-tool *wrapper*, not a config flag, so you can host approval-gated and freely-running tools side by side in the same `Tools` slice — unlike frontend tools, which flip `DisableFuncAutoCall`.
- Keep the underlying function plain (`approveExpenseReport(ctx, id string)` returns a string, no framework/network) so the offline test can call it directly, independent of the tool's JSON encoding.
- The test builds tool, agent, and handler with a fake credential and checks the tool is approval-required, the agent carries it, and the handler is non-nil — no model call; the live bind needs `AF_LIVE`.

## Further reading

- [AG-UI Frontend Tools — The Server](/blog/posts/maf-go-89-frontend-tools-server.html)
- [AG-UI State Management — The Server](/blog/posts/maf-go-91-state-management-server.html)
- [agent-framework-go on GitHub](https://github.com/microsoft/agent-framework-go)
