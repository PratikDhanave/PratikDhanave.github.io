# A2A Client

*This lesson builds a Foundry host agent that discovers remote A2A agents by their cards and calls each one as a tool.*

---

## What this lesson demonstrates

This is one half of the end-to-end A2A pair. The `a2a_client` is a local Foundry "HostClient" agent that owns the orchestrating model. On startup it walks a list of remote agent URLs — the three `a2a_server` processes on ports 5000/5001/5002 by default — resolves each one's agent card, and turns each remote agent into a callable tool. When you type a question, the host model decides *which* specialist (invoice, policy, logistics) to call, exactly the way it picks any function tool, and the call round-trips over the network to that server.

The whole point is that the client never hard-codes what the remotes can do. The card is the contract: it carries the remote agent's name and description, and the client reads those back to name the tool and dial the endpoint.

## The real code

`resolveRemoteTools` is where discovery happens — resolve the card, build an A2A client from it, wrap the remote agent, and hand back one `agenttool` per remote:

```go
card, err := agentcard.DefaultResolver.Resolve(ctx, url)
if err != nil {
    return nil, fmt.Errorf("failed to resolve card from %s: %w", url, err)
}
client, err := a2aclient.NewFromCard(ctx, card)
if err != nil {
    return nil, fmt.Errorf("failed to create A2A client for %s: %w", url, err)
}
remoteAgent := a2aprovider.NewAgent(client, a2aprovider.AgentConfig{
    Config: agent.Config{Name: card.Name, Description: card.Description},
})
tools = append(tools, agenttool.New(remoteAgent, agenttool.Config{}))
```

The host agent itself is built with `foundryprovider.NewAgent`, given those tools under a `Config{Name: "HostClient", Tools: tools}`.

## What to notice

- **Two providers, two roles.** `foundryprovider` backs the host agent (it owns the model); `a2aprovider` backs each remote reached over HTTP/JSON-RPC. Both the client and the servers need a Foundry credential — the client for its own orchestrator, each server for its hosted agent.
- **`agenttool.New` collapses a whole remote agent into one tool.** The model doesn't know it's talking across a network; it just sees a tool named after the card.
- **`splitURLs` is the one piece of pure logic** — it parses the semicolon-separated `A2A_AGENT_URLS`, trims blanks, and falls back to the default trio. That's why the offline test pins it and builds the host agent from a fake remote agent plus a fake credential — no network, no model call. The interactive loop is gated behind `AF_LIVE=1`.

## How it maps to the Microsoft Agent Framework Go SDK

This is the payoff of the earlier `02-agents/a2a` lessons, which showed one side at a time. Here the SDK's `a2aclient`/`agentcard` resolver (from `a2a-go`) does discovery, `a2aprovider.NewAgent` adapts a remote card into an `agent.Agent`, and `agenttool.New` makes it a tool — the same interface Azure AI Foundry function tools use, so specialist agents compose into a host with no orchestration code of your own.

## Run it

Start the three servers first, then `go run ./tutorial/05-end-to-end/a2a_client_server/a2a_client`. Both halves need `az login` + `FOUNDRY_PROJECT_ENDPOINT`. Offline tests run with `go test ./...`; the live conversation is gated behind `AF_LIVE=1`.

---

Next: [A2A Server](/blog/posts/maf-go-85-a2a-server.html)
