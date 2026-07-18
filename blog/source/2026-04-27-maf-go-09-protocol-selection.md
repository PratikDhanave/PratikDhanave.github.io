# A2A · Protocol Selection

*How to pin which transport a client uses when a remote A2A agent advertises several bindings at once.*

---

## What this lesson demonstrates

An A2A agent card can list *every* transport the agent speaks — JSON-RPC, HTTP+JSON, gRPC — all at once. Left alone, the client falls back to the card's default. This lesson shows how a client states an **explicit preferred transport** so the binding is chosen deterministically. Once wrapped, the remote agent is just an `agent.Agent`: you `RunText` it and `Collect()` the response exactly as with a local model-backed agent. The difference is entirely in *how* the client is constructed.

## The core: preferred transport is a client Config

```go
func newClientFromCard(ctx context.Context, card *a2a.AgentCard, transport a2a.TransportProtocol) (*a2aclient.Client, error) {
    return a2aclient.NewFromCard(
        ctx,
        card,
        a2aclient.WithConfig(a2aclient.Config{
            PreferredTransports: []a2a.TransportProtocol{transport},
        }),
    )
}
```

The program's `preferredTransport` defaults to `a2a.TransportProtocolHTTPJSON`; flip it to `a2a.TransportProtocolJSONRPC` to negotiate JSON-RPC instead. `PreferredTransports` reorders the card's advertised interfaces so the client tries your chosen binding first.

## What to notice

- **The card drives the identity.** `card.Name` and `card.Description` become the local agent's name/description, with `cmp.Or(card.Name, "RemoteA2AAgent")` supplying a fallback, so your handle mirrors the remote agent.
- **Construction is not connection.** `NewFromCard` selects a compatible interface and builds the matching HTTP transport *in memory* — it does **not** dial the server. The first network call happens at `Resolve` (fetching the card) and again at `RunText` (the actual request). That split is exactly why the offline test can build the whole client from a synthetic card.
- **A middleware, reimplemented locally.** A tiny `runLogger` satisfies `agent.Middleware` and announces each run — the same observability seam the Foundry lessons use, minus the SDK-internal dependency.

The gotcha: because `NewFromCard` defers dialing, an unreachable server or a transport the server doesn't actually honor won't surface at construction. You find out at the first `Resolve` or `RunText`, not when you pin the preference — so your preferred transport must be one the card genuinely advertises.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, transport selection is a client concern layered *below* the agent abstraction. The `a2aprovider` presents a uniform `*agent.Agent` regardless of whether bytes travel over JSON-RPC or HTTP+JSON, so your application code — and any Azure AI Foundry-backed host that composes this agent as a tool — is insulated from the wire format. Pinning a transport is how you make cross-service negotiation reproducible in environments where, say, gRPC is blocked by a proxy.

## Run it

```bash
A2A_AGENT_HOST=http://127.0.0.1:5000 go run ./tutorial/02-agents/a2a/protocol_selection
```

Expected: a pirate joke from the remote agent, preceded by a run banner. The program needs a reachable A2A server; the offline structural test builds a synthetic card advertising both transports and asserts the wiring, with the live path gated behind `AF_LIVE=1`.

---

Next: [a2a · Stream Reconnection](/blog/posts/maf-go-10-stream-reconnection.html)
