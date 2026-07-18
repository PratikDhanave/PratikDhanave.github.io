# 12 · Agent as a Function Tool

*How wrapping one agent as a tool.Tool lets an orchestrator agent delegate to a specialist — composition all the way down, with no routing code.*

---

## What this lesson demonstrates

You already know function tools: a typed Go function the model may call mid-run. This lesson swaps the function for a whole **agent**. `agenttool.New` adapts an `*agent.Agent` into an ordinary `tool.Tool`, so a top-level *orchestrator* agent can delegate to a *specialist* agent exactly as it would call any other tool — no hand-written routing.

Here the orchestrator (an "Assistant" instructed to answer in French) owns a `WeatherAgent` as a tool, and that weather agent in turn owns a leaf `weather` function. Ask about Amsterdam's weather and the call cascades two levels deep, then returns in French.

## The core: an agent becomes a tool

```go
foundryprovider.AgentConfig{
    Instructions: "You are a helpful assistant who responds in French.",
    Config: agent.Config{
        Name: "Assistant",
        // agenttool.New adapts an *agent.Agent to a tool.Tool: its Call runs the
        // inner agent with the model's {"query": ...} argument and returns the text.
        Tools: []tool.Tool{agenttool.New(weatherAgent, agenttool.Config{})},
    },
}
```

When the outer model decides it needs weather, it calls the `WeatherAgent` tool; the wrapper runs the inner agent with `{"query": ...}`, which may itself call the leaf `weather` function, and the answer bubbles back up.

## What to notice

- **The inner agent's name and description become the tool's contract.** `agenttool.New` reuses `WeatherAgent`'s `Name()` and `Description()` — that's the schema the *outer* model sees when deciding to delegate, so give the specialist a clear identity.
- **Two levels of tool-calling, zero routing logic.** The orchestrator calls the `WeatherAgent` tool; the weather agent calls its `weather` function. You wrote no dispatch code.
- **Different input shape.** A plain function tool wraps a single argument as `Arg0`; the agent-as-tool takes a `{"query": "..."}` object instead — its `Call` feeds `query` to the inner agent. The offline test asserts each shape.
- **Construction is factored out.** `newWeatherAgent` and `newAssistant` exist so the test builds both agents offline with a fake credential and asserts that wrapping the weather agent yields a tool named `WeatherAgent` exposing a `query` property.

## How it maps to the SDK

`functool.MustNew` builds the leaf `weather` tool by inferring its JSON schema from a plain typed Go function; `agenttool.New` builds the higher-order tool from an agent. Both produce a `tool.Tool`, so the orchestrator treats specialist agents and plain functions uniformly. This is how you assemble specialists into a hierarchy of Foundry-backed agents without a bespoke orchestration layer.

## Run it

```bash
go run ./tutorial/02-agents/agents/step12_as_function_tool
```

The offline structural test runs anywhere; the live end-to-end run needs `az login` + `FOUNDRY_PROJECT_ENDPOINT` and is gated behind `AF_LIVE=1`.

---

Next: [17 · Additional AI Context](/blog/posts/maf-go-23-additional-ai-context.html)
