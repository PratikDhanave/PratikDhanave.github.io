# a2a · Remote Skills as Function Tools

*How to discover a remote A2A agent's advertised skills and hand each one to a local host agent as an ordinary function tool.*

---

## What this lesson demonstrates

A remote agent publishes an **agent card** over HTTP — a JSON document describing the skills it offers. This lesson resolves that card, wraps the remote agent behind the `a2aprovider`, and turns each advertised `a2a.AgentSkill` into a **function tool**. A local Foundry host agent (a travel planner) is given those tools. When the host model decides it needs a skill, calling the tool round-trips a prompt to the *remote* agent and returns its answer. One agent's skills become another agent's tools.

## The core: a skill becomes a tool

`createSkillTools` builds one `functool.MustNew` per advertised skill. Each tool's handler is a closure that forwards the caller's query to the remote agent:

```go
tools = append(tools, functool.MustNew(functool.Config{
    Name:        sanitizeToolName(cmp.Or(skill.Name, skill.ID, "a2a_skill")),
    Description: formatSkillDescription(skill),
}, func(ctx context.Context, query string) (string, error) {
    resp, err := remoteAgent.RunText(ctx, skillPrompt(skill, query)).Collect()
    if err != nil {
        return "", err
    }
    return resp.String(), nil
}))
```

From the host model's point of view, "calling a skill" is just an ordinary function-tool call. The fact that it fans out to a network call is invisible.

## What to notice

- **Names and descriptions are derived, not hand-written.** `sanitizeToolName` lower-cases and collapses non-alphanumeric runs to underscores, falling back to the skill's `ID` and then to `a2a_skill`. `formatSkillDescription` flattens the skill's `Description`, `ID`, `Tags`, `Examples`, and I/O modes into a multi-line tool description so the host model has enough context to choose it. Both are pure functions — the offline test hammers them directly.
- **Two providers, composed.** `a2aprovider.NewAgent(client, …)` wraps the remote agent; `foundryprovider.NewAgent(…, Tools: …)` builds the local host. The host never knows a tool is backed by a network call.
- **Construction is separated from `main`.** `buildHostAgent(...)` and `createSkillTools(...)` are factored out so the test can build the identical wiring offline — fake credential, fake remote agent, no server, no model.

The gotcha worth internalizing: the skill's human-readable `Name` (e.g. `"Route Planner"`) is *not* a valid tool identifier. If you skip sanitizing, tool registration fails or two skills silently collide on the same name.

## How it maps to the Agent Framework

This is Agent-to-Agent (A2A) composition in the Microsoft Agent Framework Go SDK. The `a2aprovider` package makes a remote agent look like a local `*agent.Agent`, so it slots into the same `agent.Config{Tools: …}` seam that any function tool uses. On Azure AI Foundry, the host agent runs against your deployed model while its tool calls reach out over A2A — you compose specialized remote agents into one planner without the model ever leaving the standard tool-calling contract.

## Run it

```bash
export A2A_AGENT_HOST=http://127.0.0.1:5000
export FOUNDRY_PROJECT_ENDPOINT=...   # + az login
go run ./tutorial/02-agents/a2a/as_function_tools
```

Most of the lesson builds and tests offline — the structural tests wire a fake credential and fake remote agent with no network — and the live end-to-end run is gated behind `AF_LIVE=1` (it needs a running A2A server *and* `az login`).

---

Next: [A2A · Polling for Task Completion](/blog/posts/maf-go-08-polling-for-task-completion.html)
