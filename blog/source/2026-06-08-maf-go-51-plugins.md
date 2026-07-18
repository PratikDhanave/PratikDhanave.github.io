# step13 · Plugins (grouping tools)

*This lesson teaches how to bundle related function tools onto a Go type and attach the whole group to an agent as one slice.*

---

## What this lesson demonstrates

A "plugin" isn't a framework construct — it's an organizing idea. You put related tools on one type (here `assistantPlugin`), expose them as `[]tool.Tool`, and hand the whole group to the agent. That keeps a domain's tools together and lets a real plugin close over shared dependencies (a DB handle, an HTTP client). This example bundles two tools: `GetWeather` (takes a location) and `GetCurrentTime` (takes nothing), then asks one prompt that needs both.

## A plugin is a type with a `tools()` method

There's nothing magic here — the plugin is a plain struct whose method returns a slice of `functool.MustNew` tools:

```go
func (assistantPlugin) tools() []tool.Tool {
	weather := functool.MustNew(functool.Config{
		Name:        "GetWeather",
		Description: "Gets the current weather for a location.",
	}, func(_ context.Context, location string) (string, error) {
		return fmt.Sprintf("The weather in %s is cloudy with a high of 15°C.", location), nil
	})
	now := functool.MustNew(functool.Config{
		Name:        "GetCurrentTime",
		Description: "Gets the current time.",
	}, func(context.Context, struct{}) (string, error) {
		return time.Now().Format(time.RFC1123), nil
	})
	return []tool.Tool{weather, now}
}
```

`newAssistant` just drops `assistantPlugin{}.tools()` into `agent.Config{Tools: ...}`.

## What to notice / the gotcha

- **Handlers are typed; schemas are automatic.** The handler's input type drives the JSON schema the model sees — `string` for `GetWeather` (a `location`), an empty `struct{}` for `GetCurrentTime` (no args). Get the input type right and the model knows exactly what each tool accepts.
- **The plugin is stateless here, but doesn't have to be.** The pattern's real payoff is a plugin type that holds dependencies its handler closures capture — the tools travel with their collaborators.
- **One prompt, multiple tool calls.** The model reads both schemas and calls `GetCurrentTime()` and `GetWeather("Seattle")` in one turn; the framework runs the handlers in between and the model weaves both results into a single answer.

## How it maps to the Agent Framework

The Go SDK has no `Plugin` type — and that's the point. `functool.MustNew` gives you tools, `agent.Config.Tools` accepts any slice of them, and "plugin" is simply the convention of grouping a domain's tools behind one Go type. It scales to as many tools as you like without new framework machinery.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step13_plugins
```

The live run needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`. Offline tests assert the plugin surfaces exactly `GetWeather` and `GetCurrentTime` and invoke each handler with JSON args directly — no network; the live call is gated behind `AF_LIVE=1`.

---

Next: [step14 · Code Interpreter (hosted tool)](/blog/posts/maf-go-52-code-interpreter.html)
