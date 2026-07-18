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

---

Next: [loop · A Cyclic Workflow (guess-the-number)](/blog/posts/maf-go-80-loop.html)
