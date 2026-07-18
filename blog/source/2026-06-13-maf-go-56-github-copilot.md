# github-copilot · A Local-CLI Provider

*A provider whose "credential" is a local process, gated by a human-in-the-loop permission handler for every action the model wants to take.*

---

## What this lesson demonstrates

Every other provider in this module talks to an HTTP endpoint with a bearer token. This one is different: `copilotprovider` drives the **`copilot` binary running on your machine**. There is no Azure credential and no URL — the SDK spawns (or connects to) the CLI, which is already signed in to your GitHub account. And because Copilot can *act* — run shell commands, read files, fetch URLs — every action is gated by a **permission handler** you supply.

## The wiring

The agent takes a `*copilot.Client` plus a `copilotprovider.AgentConfig`, and the permission handler goes on the `SessionConfig`:

```go
return copilotprovider.NewAgent(
	client,
	copilotprovider.AgentConfig{
		SessionConfig: &copilot.SessionConfig{
			OnPermissionRequest: onPermission,
		},
		Config: agent.Config{
			Name:        "GitHub Copilot Agent",
			Middlewares: []agent.Middleware{mw},
		},
	},
)
```

`OnPermissionRequest` fires whenever the model wants to take an action. The decision logic is factored into a pure `decide(answer)` helper that maps a raw y/n string to a `rpc.PermissionDecisionApproveOnce{}` (proceed once) or `rpc.PermissionDecisionReject{}` (block) — so it can be unit-tested without stdin.

## What to notice

- **The "credential" is a local process.** `copilot.NewClient(nil)` only *constructs* the client; `client.Start(ctx)` is what launches the CLI. Compare this to the Foundry lessons, which pass an `azcore.TokenCredential` and an endpoint — Copilot has neither. Without the CLI installed and authenticated (or `COPILOT_CLI_PATH` set), `Start` fails fast with a clear error.
- **Permission handler = human in the loop.** In `main`, the prompt "List all files in the current directory" makes the model request a `shell` action; `promptPermission` prints `[Permission Request: shell]` and asks `Approve? (y/n):` before anything runs.
- **Construction is separated from `main`.** `newCopilotAgent(client, onPermission, mw)` lets the offline test build the identical agent from a client that was *never started* — nothing spawns, nothing dials out — and assert `a.Name() == "GitHub Copilot Agent"`.

## How it maps to the Microsoft Agent Framework

This lesson stretches the provider abstraction in an instructive direction: a provider need not be a remote HTTP service at all. The same `agent.Agent` contract — `RunText`, `agent.Stream(true)`, middleware — works over a *local* model host. The novel piece is the permission model: for providers that can execute side effects, the Agent Framework Go SDK routes each action through a `SessionConfig.OnPermissionRequest` callback, giving you a single, testable choke point for human approval.

## Run it

`go run ./tutorial/02-agents/providers/github-copilot` (needs the Copilot CLI installed and authenticated). The offline tests — wiring, the pure `decide` table, and middleware pass-through — run with no CLI; the live call is gated behind `AF_LIVE=1`.

---

Next: [02 · Providers · OpenAI](/blog/posts/maf-go-57-openai.html)
