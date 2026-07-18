# a2a · Stream Reconnection

*How to resume a long-running remote agent stream after it drops — using a continuation token to reconnect instead of re-sending the expensive query.*

---

## What this lesson demonstrates

A2A lets your program drive an agent behind an HTTP endpoint. Long tasks stream their progress back, but streams break — proxies time out, laptops sleep, mobile networks drop. This lesson shows the recovery pattern: while a remote task is still **working**, it hands you a **continuation token** on each `*ResponseUpdate`. Stash it, and when the connection dies you **reconnect** with that token to keep receiving updates — no need to re-run the query.

The program does this deliberately in two phases: stream until a token appears, break to simulate an interruption, then reconnect and resume to completion.

## The core: capture the token, then reconnect with no messages

```go
// Phase 1 — stream and break the moment we hold a continuation token.
for update, err := range remoteAgent.RunText(ctx, query, agent.WithSession(session), agent.Stream(true)) {
    if err != nil {
        fail("stream error: %v", err)
    }
    if update == nil {
        continue
    }
    fmt.Print(update)
    if update.ContinuationToken != "" {
        continuationToken = update.ContinuationToken
        break // connection "drops"
    }
}
```

Phase 2 then calls `remoteAgent.Run(ctx, nil, agent.WithSession(session), agent.WithContinuationToken(continuationToken), agent.Stream(true))`. The provider re-subscribes to the *same* task and resumes streaming the remaining updates.

## What to notice

- **The token appears mid-stream.** While the remote task is `submitted`/`working`, the provider sets `update.ContinuationToken` to the task ID. Phase 1 breaks the instant that field is non-empty — that is the "interruption."
- **Reconnect passes NO messages.** Phase 2 sends `nil` messages plus the token; the provider re-subscribes (`SubscribeToTask`, falling back to `GetTask` if the task already finished). The original heavy query is never re-sent.
- **No credential object here.** Unlike the Foundry lessons, A2A carries no `TokenCredential`. Auth (if any) rides on the underlying `*http.Client` the `a2aclient` was built with.
- **Construction is factored out of `main`.** `newRemoteAgent(client, card, mw)` builds the `*agent.Agent`, so the offline test constructs the identical agent from an in-memory card.

The gotcha to watch: a task can finish *before* you ever see a token. The program guards for this — if the run completes with `continuationToken == ""`, reconnection is simply not applicable, and blindly assuming a token exists would leave you re-subscribing to nothing.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, `agent.Stream(true)` plus `agent.WithContinuationToken(...)` is the resumable-streaming contract. The token is the server-side task handle; reconnecting is a `tasks/resubscribe` under the hood. For Azure AI Foundry-backed remote agents doing long analyses, this makes streamed runs durable across flaky links — the client can lose the socket and pick the stream back up without paying for the compute twice.

## Run it

```bash
A2A_AGENT_HOST=http://127.0.0.1:5000 go run ./tutorial/02-agents/a2a/stream_reconnection
```

Expected: streaming starts, prints `Captured continuation token …`, "interrupts," then prints `Reconnecting to task …` and resumes to completion. The program needs a live A2A server; the offline tests build a real client from an in-memory JSON-RPC card without dialing, and the end-to-end flow is gated behind `AF_LIVE=1`.

---

Next: [step01 · Running an Agent (with middleware)](/blog/posts/maf-go-11-running.html)
