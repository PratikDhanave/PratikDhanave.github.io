# step23 · Local MCP (wrapping remote tools)

*This lesson teaches how to connect to a remote MCP server and decorate the tools it exposes with your own local behavior before an agent uses them.*

---

## What this lesson demonstrates

"Local MCP" is about *where the tool objects live*, not where the server lives. You open a session to a remote MCP server (Microsoft Learn's public endpoint), list the tools it publishes, and get them back as ordinary `tool.Tool` values **in your process**. Because they're just Go values, you can wrap each one. Here a decorator prints a line every time a tool is invoked, then delegates to the real MCP tool — proving that MCP tools compose like any other `tool.FuncTool`.

## A decorator is embedding plus one override

`loggingFuncTool` embeds a `tool.FuncTool`, inheriting `Name`, `Description`, `Schema` and `ReturnSchema` unchanged; only `Call` is overridden to print, then delegate:

```go
type loggingFuncTool struct {
	tool.FuncTool
}

func (t loggingFuncTool) Call(ctx context.Context, args string) (any, error) {
	fmt.Printf("  >> [LOCAL MCP] Invoking tool %q locally...\n", t.Name())
	return t.FuncTool.Call(ctx, args)
}
```

`wrapTools` applies it to every `FuncTool` in the slice and passes non-`FuncTool`s through untouched.

## What to notice / the gotcha

- **Delegation is what makes it transparent.** Because `Call` ends in `t.FuncTool.Call(...)`, the agent gets the same result the underlying tool would have returned — the decorator adds behavior without changing outcomes. Swap the print for metrics, caching, or argument validation and nothing else moves.
- **Type-assert to `tool.FuncTool` before wrapping.** `mcptool.ListTools` returns `[]tool.Tool`; only the ones that assert to `tool.FuncTool` are callable and decoratable. `wrapTools` skips the rest, preserving order.
- **`wrapTools` is pure and returns a fresh slice**, leaving its input untouched — which is exactly why the offline test can feed it fakes and assert the decoration without any session or model.

## How it maps to the Agent Framework

This is the natural extension of step09 (MCP client as tools). There you handed the remote tools straight to the agent; here you interpose a local decorator first. The Go SDK's `mcptool` returns tools as first-class `tool.Tool` values, so the same composition tricks you'd use on any function tool — wrapping, timing, guarding — apply unchanged to tools resolved over the wire.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step23_local_mcp
```

The live run needs `az login`, `FOUNDRY_PROJECT_ENDPOINT`, and outbound network to learn.microsoft.com. Offline tests wrap a fake tool and assert the decorator forwards args, returns the inner result, propagates errors, and wraps only `FuncTool`s — no session, no model; the end-to-end run is gated behind `AF_LIVE=1`.

---

Next: [providers/gemini · The Same Agent, Backed by Google Gemini](/blog/posts/maf-go-55-gemini.html)
