# State Management

*How a shared state snapshot rides along with every AG-UI turn, so client and server-hosted agent stay in sync on evolving structured data.*

---

## What this lesson demonstrates

The final AG-UI lesson (a client+server pair) shares **state** between the two halves. The client owns a state map; on each turn it attaches the current state as a JSON `DataContent`, and after each reply it looks for an updated snapshot the server sent back and adopts it. The demo is a recipe assistant: the server's model answers in JSON, and a middleware turns that JSON into a state snapshot the client can track and render.

## The server: a state-snapshot middleware

The agent's instructions ask the model to reply with a JSON recipe object. A middleware watches every update and, whenever a reply parses as a JSON object, emits an *extra* update whose content is a `DataContent` snapshot before passing the original through:

```go
var snapshot any
if json.Unmarshal([]byte(trimmed), &snapshot) == nil {
    encoded := base64.StdEncoding.EncodeToString([]byte(trimmed))
    if !yield(&agent.ResponseUpdate{
        Role:     update.Role,
        Contents: message.Contents{&message.DataContent{MediaType: "application/json", Data: encoded}},
    }, nil) {
        return
    }
}
```

The middleware is a pure function of the wrapped `RunFunc` — no network — so the offline test drives it with a fake `next` and asserts the snapshot it emits. It's wired into the agent via `agent.Config.Middlewares`, and the agent goes behind the usual AG-UI handler.

## The client: carry state in, adopt state out

Each message carries **two** contents — the user's text and the current state snapshot:

```go
msg := message.New(&message.TextContent{Text: input}, toStateContent(state))
resp, err := a.RunMessage(ctx, msg, agent.WithSession(session)).Collect()
if nextState, ok := extractState(resp); ok {
    state = nextState // server sent an updated snapshot — adopt it
    printState(state)
}
```

`toStateContent` marshals the state to JSON and base64-wraps it as an `application/json` `DataContent`; `extractState` scans the response for the first such `DataContent` and decodes it. If the response carries no snapshot, `extractState` returns `false` and the client keeps the state it already holds.

## What to notice / the gotcha

State travels as **content**, not as a side channel. It's just a `DataContent` with media type `application/json` attached to messages in both directions — the same envelope the framework uses for any binary/structured payload. Both sides agree on that media type; the client's `:state` command prints whatever snapshot it currently holds. Because `toStateContent`/`extractState` are pure round-trip helpers, they're unit-tested offline with no server.

## How it maps to the Microsoft Agent Framework

This is the AG-UI answer to "how does a UI keep a live view of the agent's structured output?" The model runs against Azure AI Foundry on the server, its JSON output is captured as state by middleware, and the client renders that state as it evolves — think a recipe card, a form, or a dashboard filling in as the conversation proceeds. Middleware plus `DataContent` gives you a typed, inspectable state channel without inventing a protocol of your own.

## Run it

```bash
go run ./tutorial/02-agents/agui/step05_state_management/server   # terminal 1 (needs az login + Foundry)
go run ./tutorial/02-agents/agui/step05_state_management/client   # terminal 2
```

The middleware and state helpers test offline; the live server run is gated behind `AF_LIVE=1`.

---

Next: [mcp · Agent with tools from an MCP Server](/blog/posts/maf-go-32-agent-mcp-server.html)
