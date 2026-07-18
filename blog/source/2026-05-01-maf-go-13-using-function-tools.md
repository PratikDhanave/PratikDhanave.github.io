# 02 · step03 — Using Function Tools

*How to wrap a plain typed Go function as a tool the model can call mid-run.*

---

## What this lesson demonstrates

An agent with only instructions can talk. An agent with **tools** can *act*. Here the model gets one function — `weather(location string) string` — and decides on its own when to call it. The framework marshals the model's JSON arguments into your parameter, runs your function, feeds the return value back, and lets the model answer in prose.

The whole tool is a typed Go function wrapped with `functool.MustNew`, which infers the JSON schema from the handler's signature — no hand-written schema.

## The core code

```go
var weatherTool = functool.MustNew(functool.Config{
	Name:        "weather",
	Description: "Get the current weather for a given location",
}, func(_ context.Context, location string) (string, error) {
	return fmt.Sprintf("The weather in %s is cloudy with a high of 15°C.", location), nil
})
```

The tool attaches via `agent.Config.Tools` as `[]tool.Tool{weatherTool}`; the SDK's automatic function-calling middleware handles the call/return loop for you.

## What to notice

- **A tool is just a typed Go function.** The model sees a `weather` tool taking one string. No reflection you have to manage, no separate schema file.
- **Single non-struct params are wrapped.** Because the parameter is a bare `string` (not a struct), the SDK wraps it, so the arguments arrive as `{"Arg0":"Amsterdam"}`. This is the gotcha the offline test pins down — it invokes `weatherTool.Call(ctx, ` + "`" + `{"Arg0":"Amsterdam"}` + "`" + `)` directly. Give the handler a struct with named fields and you get named JSON keys instead.
- **The handler is pure.** No network in the tool body — which is exactly why the offline test can exercise it directly, with no model and no Foundry call.

## How it maps to Azure AI Foundry

The agent is a Foundry agent (`foundryprovider.NewAgent` + `ModelDeployment`). When the Foundry model returns a `tool_call`, the SDK's function-calling loop unmarshals the arguments, runs your Go function, appends the result, and continues the run — all transparently. The tool *schema* the model reads to decide whether to call is derived from your Go signature, so the Go type system is your contract with the model. This is the same mechanism later lessons extend with approvals (step04) and structured output (step05).

## Run it

```bash
go run ./tutorial/02-agents/agents/step03_using_function_tools
```

For both the one-shot and streaming questions the model calls `weather` for "Amsterdam". The program needs Foundry; the four offline tests (wiring, tool metadata, a direct tool call, and a live test gated behind `AF_LIVE=1`) cover everything without a network by default.

---

Next: [02 · step04 — Function Tools With Approvals](/blog/posts/maf-go-14-using-function-tools-with-approvals.html)
