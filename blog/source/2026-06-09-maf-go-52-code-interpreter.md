# step14 · Code Interpreter (hosted tool)

*This lesson teaches the hosted tool: a marker that lets the Foundry service run code the model writes, instead of a Go function you implement.*

---

## What this lesson demonstrates

A language model is unreliable at arithmetic and can't actually *execute* anything. The **code interpreter** fixes that. You attach `hostedtool.CodeInterpreter{}` to the agent, and when the model decides it needs to compute something it writes Python, the Foundry service runs it in a sandbox, and the result flows back into the answer. Here the agent is asked to solve `sin(x) + x^2 = 42` — a root-finding problem no LLM should attempt in its head.

## A hosted tool is a marker, not a function

Unlike a function tool (step03), a hosted tool carries no Go implementation. It's a zero-value marker you add to `Config.Tools`:

```go
func newCodeInterpreterAgent(endpoint, model string, cred azcore.TokenCredential) *agent.Agent {
	return foundryprovider.NewAgent(endpoint, cred,
		foundryprovider.ModelDeployment(model),
		foundryprovider.AgentConfig{
			Instructions: "You are a helpful assistant that can solve problems with code.",
			Config: agent.Config{
				Name:  "CodeInterpreterAgent",
				Tools: []tool.Tool{&hostedtool.CodeInterpreter{}}, // the hosted tool
			},
		})
}
```

## What to notice / the gotcha

- **The marker has no `Run` method** — only `Name() == "code_interpreter"`. Adding it to `Config.Tools` is what flips the service's "may execute generated code" switch; the SDK forwards that exact name to Foundry. Nothing runs in your process.
- **Hosted vs. function tools: same interface, opposite execution site.** A function tool ships Go code the SDK calls locally; a hosted tool ships *nothing* — the capability lives in the service. Both satisfy `tool.Tool`, so `Config.Tools` treats them identically.
- **The offline test can only pin the identity.** Because the marker does nothing locally, the structural test asserts `Name() == "code_interpreter"` and that the tool-wired agent constructs — it cannot exercise execution without the live service.

## How it maps to the Agent Framework

`hostedtool.CodeInterpreter` is the Go SDK's declaration of an Azure AI Foundry server-side capability. It's the same pattern as web search (step21): the agent declares what the service is allowed to do, and Foundry does the heavy lifting — sandboxed Python execution here — returning the computed answer inline.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step14_code_interpreter
```

The live run needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`. The offline tests assert wiring and the `"code_interpreter"` tool identity with no network; the live model-plus-sandbox call is gated behind `AF_LIVE=1`.

---

Next: [step21 · Foundry Web Search (hosted tool + citations)](/blog/posts/maf-go-53-web-search.html)
