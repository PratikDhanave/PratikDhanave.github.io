# 01 · Hello Agent

*The smallest useful agent: give a model instructions and a name, hand it a message, get a response — collected or streamed.*

---

## What this lesson demonstrates

This is the Agent primitive stripped to its essence. You build an agent from instructions plus a model, call it with a message, and it returns a response. That single loop is what everything later — tools, memory, workflows — builds on. The lesson runs the same call two ways: once collected all at once, once streamed token-by-token.

## The code

Construction is factored out of `main` so the offline test can rebuild the identical agent with a fake credential:

```go
func newJoker(endpoint, model string, cred azcore.TokenCredential) *agent.Agent {
    return foundryprovider.NewAgent(
        endpoint,
        cred,
        foundryprovider.ModelDeployment(model),
        foundryprovider.AgentConfig{
            Instructions: "You are good at telling jokes.",
            Config:       agent.Config{Name: "Joker"},
        },
    )
}
```

Then `main` runs it two ways off the same method:

```go
resp, err := a.RunText(ctx, "Tell me a joke about a pirate.").Collect()

for update, err := range a.RunText(ctx, "Now tell one about a robot.", agent.Stream(true)) {
    demo.Print(update, err)
}
```

## What to notice

- **Two call styles, one method.** `RunText` returns a `ResponseStream`. Call `.Collect()` to drain it into a finished `*Response`, or `range` over it with `agent.Stream(true)` to consume `*ResponseUpdate`s as they arrive. Both types implement `fmt.Stringer`, so one `demo.Print` handles both.
- **Streaming is a Go iterator, not a channel.** The `for update, err := range a.RunText(...)` loop is a Go 1.23+ range-over-function iterator (`iter.Seq2`). There are no channels to close and no goroutines to manage — the gotcha here is that you don't need the machinery you might expect.
- **Construction is separated from `main`.** `newJoker(...)` exists purely so the test can build the same agent offline and assert `a.Name() == "Joker"` without a network.

## How it maps to Azure AI Foundry

`foundryprovider.NewAgent` binds the agent to your Foundry project's Responses API, keyed by the model deployment name via `ModelDeployment(model)`. Under the hood each `RunText` becomes a `POST /responses` with a bearer token from your Azure credential. The `AgentConfig.Instructions` field is the system prompt; `agent.Config.Name` is how the agent identifies itself.

## Run it

```bash
go run ./tutorial/01-get-started/01_hello_agent
```

Expected: two jokes — the first collected, the second streamed. The offline structural test runs anywhere; the live model call is a second test gated behind `AF_LIVE=1` (needs `az login`).

---

Next: [02 · Add Tools](/blog/posts/maf-go-03-02-add-tools.html)
