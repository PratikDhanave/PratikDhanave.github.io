# A2A Server

*This lesson hosts one specialized Foundry agent over the A2A protocol, publishing an agent card the client can discover.*

---

## What this lesson demonstrates

The `a2a_server` is the other half of the pair. A2A lets one agent expose itself to *other* agents over HTTP/JSON-RPC. This server wraps a single Foundry agent — invoice, policy, or logistics, chosen with `--agentType` — behind an `a2aprovider` executor and publishes an **agent card** at the well-known path. A client resolves that card and calls this agent as a tool. Because each server hosts exactly one agent type on one port, the full end-to-end scenario is three server processes plus the client.

Each server exposes two routes: `/.well-known/agent-card.json` for discovery (a static card handler), and `/` for the JSON-RPC endpoint the client actually calls.

## The real code

`newMux` is the wiring heart: it pins the card's interface URL, builds the A2A request handler around the executor, and mounts both routes:

```go
card.SupportedInterfaces = []*a2a.AgentInterface{
    a2a.NewAgentInterface(url, a2a.TransportProtocolJSONRPC),
}
requestHandler := a2asrv.NewHandler(
    a2aprovider.NewExecutor(hostAgent, a2aprovider.ExecutorConfig{}),
    a2asrv.WithExtendedAgentCard(card),
)
mux := http.NewServeMux()
mux.Handle("/", a2asrv.NewJSONRPCHandler(requestHandler))
mux.Handle(a2asrv.WellKnownAgentCardPath, a2asrv.NewStaticAgentCardHandler(card))
```

The agent behind it comes from `buildAgent(agentType)`, which returns a `foundryprovider.AgentConfig` plus the `*a2a.AgentCard` — including the card's `Name`, `Description`, and `Skills`.

## What to notice

- **The card is the contract.** The `Name`, `Skills`, and `SupportedInterfaces` URL that `buildAgent` and `newMux` set are exactly the fields the client reads back. Break the agreement — hand `newMux` a URL the client doesn't expect — and discovery fails. That agreement is why this is a *pair*, not two unrelated programs.
- **The invoice agent carries real tools.** Its `buildAgent` case wires three `functool.MustNew` tools (`query_invoices`, `query_by_transaction_id`, `query_by_invoice_id`) over a seeded in-memory dataset; policy and logistics are instruction-only agents that reply with fixed text.
- **`buildAgent` returns an error for an unknown type** instead of exiting, so the offline test can build every agent type's card + tools, drive `newMux`'s two routes with `httptest` (card served, bare GET on `/` rejected), and exercise the invoice queries — with a fake credential, no port, no network. The live bind is gated behind `AF_LIVE=1`.

## How it maps to the Microsoft Agent Framework Go SDK

`a2aprovider.NewExecutor` adapts an `agent.Agent` into an A2A executor; `a2asrv`'s `NewHandler`, `NewJSONRPCHandler`, and `NewStaticAgentCardHandler` (from `a2a-go`) turn it into a standard HTTP surface. The Foundry model lives entirely server-side, so a specialist agent becomes a network service any A2A-aware client — including an Azure AI Foundry host agent — can call as a tool.

## Run it

`go run ./tutorial/05-end-to-end/a2a_client_server/a2a_server --agentType invoice --port 5000` (repeat for policy/logistics on 5001/5002), then start the client. Needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`. Offline tests run with `go test ./...`; live paths skip without `AF_LIVE=1`.

---

Next: [Capstone · DocQA — answer questions about your own documents](/blog/posts/maf-go-86-docqa.html)
