# A2A · Polling for Task Completion

*How to drive a slow remote agent that answers with a continuation token, then poll that token to completion instead of blocking on one long call.*

---

## What this lesson demonstrates

Everything before this ran a model *in-process*. A2A (Agent-to-Agent) is different: the agent lives on another machine behind an HTTP endpoint, advertising itself with an **agent card**. You resolve the card, build an A2A client from it, wrap that client in a local `agent.Agent` via `a2aprovider`, and then drive it with the exact same `RunText` / `Run` API as any other agent.

The new idea is **background responses**. Some remote tasks take a while. Ask with `agent.AllowBackgroundResponses(true)` and the server may return *immediately* with a **continuation token** instead of a finished answer. You then poll — handing the token back — until a response comes back with an *empty* token, which means "done."

## The core: poll until the token clears

```go
resp, err := a.RunText(ctx, prompt,
    agent.WithSession(session),
    agent.AllowBackgroundResponses(true),
).Collect()
if err != nil {
    return nil, err
}

for resp.ContinuationToken != "" {
    time.Sleep(2 * time.Second)
    // Continuing a background response: no new messages, just the token.
    resp, err = a.Run(ctx, nil,
        agent.WithSession(session),
        agent.WithContinuationToken(resp.ContinuationToken),
    ).Collect()
    if err != nil {
        return nil, err
    }
}
return resp, nil
```

## What to notice

- **A remote agent looks like a local one.** After `a2aprovider.NewAgent` wraps the A2A client, you call `RunText` / `Run` / `CreateSession` exactly as with a Foundry agent. The provider is the only thing that changed.
- **The agent card drives the wiring.** `agentConfigFromCard` reads the card's `Name` (with `cmp.Or(card.Name, "RemoteA2AAgent")` as the fallback) and `Description`, and attaches the middleware. That pure function is what the offline test checks.
- **Background and poll are two distinct option sets.** The *first* call carries `AllowBackgroundResponses(true)`. Each *poll* carries `WithContinuationToken(token)` and **no messages** — `Run(ctx, nil, ...)`.

The gotcha: a poll must pass `nil` messages. The runtime rejects a run that supplies *both* a continuation token and messages ("messages are not allowed when continuing a background response"). The continuation *is* the request; there is nothing new to say.

## How it maps to the Agent Framework

This is the Microsoft Agent Framework Go SDK's answer to long-running remote work. The continuation token is the server-side task handle: the first response acknowledges the task, and subsequent polls fetch its state. Against Azure AI Foundry-backed remote agents, this keeps a client responsive over slow tool-heavy analyses without holding one HTTP request open for the whole duration.

## Run it

```bash
A2A_AGENT_HOST=http://127.0.0.1:5000 AF_LIVE=1 \
  go run ./tutorial/02-agents/a2a/polling_for_task_completion
```

The program exits early unless `AF_LIVE=1` is set, because it needs a reachable A2A server. The offline structural test builds the same `a2aprovider.AgentConfig` from a fake card and asserts its wiring — no network, no server.

---

Next: [A2A · Protocol Selection](/blog/posts/maf-go-09-protocol-selection.html)
