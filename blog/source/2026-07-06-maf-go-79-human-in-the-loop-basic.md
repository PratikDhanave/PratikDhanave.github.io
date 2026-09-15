# human_in_the_loop_basic · A Workflow That Asks a Human

*How a RequestPort pauses a workflow, emits a request to a human, and feeds their answer back into the graph.*

---

## What this lesson demonstrates

This is the first *workflow* lesson to show human-in-the-loop. The graph has two nodes and a cycle between them: a **RequestPort** ("GuessNumber") that emits an `ExternalRequest` to a human and feeds their answer back in, and a **Judge** executor that compares the guess to a secret target. The Judge either yields the final output ("42 found in N tries!") or sends a `Below`/`Above` signal back to the port to ask again. It is the number-guessing game.

## The real code

A `RequestPort` is a typed door to the outside world. `Request` is what you ask the human; `Response` is what they hand back:

```go
guessPort := workflow.RequestPort{
    ID:       "GuessNumber",
    Request:  reflect.TypeFor[NumberSignal](), // what we ask the human (the signal)
    Response: reflect.TypeFor[int](),          // what the human hands back (a guess)
}
ask := guessPort.Bind()
judge := workflow.NewExecutor("Judge", &judgeExecutor{target: target}).Bind()

wf, err := workflow.NewBuilder(ask).
    AddEdge(ask, judge).   // human's guess flows to the Judge
    AddEdge(judge, ask).   // Judge's Above/Below signal flows back to ask again
    WithOutputFrom(judge). // the Judge's YieldOutput is the workflow's result
    Build()
```

The driver runs the workflow with `inproc.Default.RunStreaming`, then ranges over `run.WatchStream`. On each `workflow.RequestInfoEvent` it prompts the console and calls `run.SendResponse`; on `workflow.OutputEvent` it stops.

## What to notice

- **The pause is an event, not a blocking call.** The workflow doesn't call into your code — it *emits* a `RequestInfoEvent` and suspends. You answer with `SendResponse` at your leisure, which is exactly what makes this durable across process boundaries.
- **The Judge declares its protocol as struct fields.** `judgeExecutor` embeds `workflow.AttrSendsMessage[NumberSignal]` and `workflow.AttrYieldsOutput[string]`. These compile-time declarations let the builder type-check the graph's edges and outputs.
- **State survives the round-trip.** The Judge bumps a `"tries"` counter via `ctx.ReadOrInitState` / `ctx.QueueStateUpdate`, so the win message can report how many turns it took even though each guess is a separate resumption.
- **`request.CreateResponse(guess)`** packages the human's answer as the port's typed `ExternalResponse` — it won't let you send the wrong type back.

## How it maps to the Agent Framework

In the Microsoft Agent Framework Go SDK, `RequestPort` + `RequestInfoEvent` is the general primitive for any external approval or input step — a human approving a tool call, a reviewer signing off on a draft, a service supplying data the graph can't compute. Because the port emits an event and resumes on a response, it pairs naturally with the checkpoint lessons: pause, persist, and rehydrate days later. No model is involved here, so you learn the mechanism cleanly before wiring it to an Azure AI Foundry agent.

## Run it

```bash
go run ./tutorial/03-workflows/human-in-the-loop/human_in_the_loop_basic
```

No model or network — but it is interactive: run it in a terminal and it reads your guesses from stdin. The offline test asserts the port↔judge cycle without touching stdin.

## Key takeaways

- A `RequestPort` is a typed door to the outside world: its `Request` type is what you ask the human, its `Response` type is what they hand back, and `CreateResponse` refuses to send the wrong type.
- The pause is an **event, not a blocking call** — the workflow emits a `RequestInfoEvent` and suspends, and you answer at your leisure with `SendResponse`, which is what makes it durable across process boundaries.
- Executors declare their protocol as struct fields (`AttrSendsMessage`/`AttrYieldsOutput`), letting the builder type-check edges and outputs at compile time.
- State survives each round-trip via `ctx.ReadOrInitState`/`ctx.QueueStateUpdate`, so the "tries" counter is intact even though every guess is a separate resumption.
- Because the port emits an event and resumes on a response, it pairs naturally with the checkpoint lessons — pause, persist, and rehydrate later — and generalises to any external approval or input step.

## Further reading

- [loop · A Cyclic Workflow (guess-the-number)](/blog/posts/maf-go-80-loop.html)
- [Checkpoint with human in the loop — Microsoft Agent Framework in Go](/blog/posts/maf-go-73-checkpoint-with-human-in-the-loop.html)
- [Human in the loop — Microsoft Agent Framework in Go](/blog/posts/maf-go-30-human-in-loop.html)
- [microsoft/agent-framework-go on GitHub](https://github.com/microsoft/agent-framework-go)

---

Next: [loop · A Cyclic Workflow (guess-the-number)](/blog/posts/maf-go-80-loop.html)
