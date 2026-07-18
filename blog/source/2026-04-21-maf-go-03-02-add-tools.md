# 02 · Add Tools

*Hand the agent a plain Go function it can decide to call mid-conversation — the model requests it, the framework runs it, the result flows back.*

---

## What this lesson demonstrates

An agent that can only talk is limited. Give it a *tool* — an ordinary Go function — and it can fetch data or hit an API without you scripting when. Here we register a `weather` function. Ask "What is the weather in Amsterdam?" and the model emits a tool call, the framework runs `weather("Amsterdam")`, and the model turns the returned string into its answer. The model decides *when* to call; your Go code decides *what* the call does.

## The code

The tool is just a named function wrapped so the model can see it:

```go
func weather(_ context.Context, location string) (string, error) {
    return fmt.Sprintf("The weather in %s is cloudy with a high of 15°C.", location), nil
}

var weatherTool = functool.MustNew(functool.Config{
    Name:        "weather",
    Description: "Get the current weather for a given location",
}, weather)
```

Wiring it into the agent is a single field — the same `agent.Config` as lesson 01, now with `Tools` populated:

```go
Config: agent.Config{
    Name:  "WeatherAgent",
    Tools: []tool.Tool{weatherTool},
},
```

## What to notice

- **A tool is just a function.** `weather(ctx, location) (string, error)` is ordinary Go. It's a *named* func, not an inline closure, precisely so the offline test can call it directly and assert the exact string — no model needed.
- **`functool.MustNew` derives the JSON schema.** From the handler's parameter type (a `string`) it builds the input schema the model sees, so the model knows it must supply a `location`. The `Name` and `Description` are the agent's documentation for *when* to reach for the tool — vague descriptions are the usual gotcha when a model won't call a tool.
- **Tool calling works identically under streaming.** The same question run with `agent.Stream(true)` behaves the same; the tool round-trip is transparent to whether you collect or stream.

## How it maps to Azure AI Foundry

When you attach a tool, the framework advertises its JSON schema to the Foundry model alongside your message. Foundry returns a tool call rather than a final answer; the SDK executes your Go handler locally, sends the result back as a tool result, and the model produces the final reply. This is standard function-calling — the framework just handles the request/execute/return loop for you.

## Run it

```bash
go run ./tutorial/01-get-started/02_add_tools
```

Expected: an answer describing Amsterdam's weather built from the tool's string, collected then streamed. Offline, `TestWeather` asserts the exact returned string and `TestNewAgent_Wiring` checks the agent name — both run anywhere. The real model-issued tool call lives in `TestAddTools_Live`, gated behind `AF_LIVE=1`.

---

Next: [03 · Multi-Turn Conversation](/blog/posts/maf-go-04-03-multi-turn.html)
