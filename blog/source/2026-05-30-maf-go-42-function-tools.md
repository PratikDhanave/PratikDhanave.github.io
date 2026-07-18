# step03 · Function Tools (Foundry)

*How to wrap an ordinary Go function as a tool the model can call, with the schema derived automatically from its types.*

---

## What this lesson demonstrates

This lesson gives the Foundry agent a **function tool**: a plain Go function the model can invoke mid-run. You wrap the func with `functool.MustNew`, the framework derives a JSON input/output schema from its types and hands that schema to the model, and when the model decides it needs the tool it emits a tool call — the framework unmarshals the arguments, runs your func, and feeds the result back, all inside a single `RunText`.

## Wrapping a Go func as a tool

The whole tool is one declaration:

```go
var weatherTool = functool.MustNew(functool.Config{
	Name:        "weather",
	Description: "Get the current weather for a given location",
}, func(_ context.Context, location string) (string, error) {
	return fmt.Sprintf("The weather in %s is cloudy with a high of 15°C.", location), nil
})
```

`functool.MustNew` inspects the handler's argument and return types — here `string → string` — and builds the schema the model reads. The tool is then attached through `agent.Config.Tools` in the `newAgent` helper, so it's added to every run and the model *may* call it.

## What to notice

Two subtleties in that signature. First, the single non-struct argument is exposed to the model as a field named **`Arg0`** — if you want named parameters, take a struct instead of a bare `string`. Second, the **`Description` is load-bearing**: it's the text the model reads to decide *when* to call the tool, so a vague description means the tool fires at the wrong times or not at all.

The other thing worth seeing: in `main`, one `RunText("What is the weather like in Amsterdam?")` triggers **two model round-trips** under the hood. The model asks for the `weather` tool, the framework runs `weatherTool` and returns its output, and the model produces a final answer incorporating it. `Collect` drains that entire multi-hop exchange into one `Response` — you never orchestrate the round-trips yourself.

Because the tool is a pure function, the offline test exercises it directly — asserting its name, description, schema, and `Call` output — with no network, alongside the usual wiring assertions on the agent.

## How it maps to the Agent Framework

`functool` is the Go SDK's bridge from idiomatic Go to the model's tool-calling protocol. The provider (Foundry, here) is responsible only for transporting the tool schema and the tool-call/tool-result messages; the `functool` + `agent.Config.Tools` mechanism is identical across providers. Tools are the primitive the next lessons extend — approvals gate them behind consent, and later hosted tools (code interpreter, web search) plug into the same `Tools` slot.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step03_function_tools
```

Tests (including the direct tool exercise) run offline; the live tool-calling run is gated behind `AF_LIVE=1` with `az login` and `FOUNDRY_PROJECT_ENDPOINT`.

---

Next: [step04 · Function Tools with Approvals](/blog/posts/maf-go-43-function-tools-with-approvals.html)
