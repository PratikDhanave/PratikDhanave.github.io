# checkpoint · Human-in-the-Loop with Checkpoint & Restore

*How to pause a workflow to ask a human, checkpoint every super-step, then rewind the whole graph to a saved checkpoint and replay.*

---

## What this lesson demonstrates

This lesson combines two patterns from the earlier ones: a **human-in-the-loop pause** and **checkpoint/restore**. A number-guessing game is modelled as a two-node workflow wired in a cycle:

- **`GuessPort`** — a `workflow.RequestPort`. It *pauses* the run and emits an external request (`SignalWithNumber`) asking a human for a guess, then resumes when the human's `int` response arrives.
- **`Judge`** — an executor holding a secret `target` and a `tries` counter. It compares each guess and either **yields** the answer or **sends** a too-high / too-low signal back to the port for another round.

A `checkpoint.Manager` snapshots the graph after every super-step. Once the game is won, `main` picks a mid-run checkpoint, calls `RestoreCheckpoint`, and replays — the Judge's `tries` count comes back too. It's fully offline: no agent, no model, no credential — the "human" is just a responder function.

## The request port

The port is a first-class graph node with typed request/response, wired into the cycle:

```go
guessPort := workflow.RequestPort{
	ID:       "GuessPort",
	Request:  reflect.TypeFor[SignalWithNumber](),
	Response: reflect.TypeFor[int](),
}
ask := guessPort.Bind()
// … AddEdge(ask, judge); AddEdge(judge, ask); WithOutputFrom(judge)
```

In the event loop, a `RequestInfoEvent` is answered with `request.CreateResponse(guess)` and `run.SendResponse(...)`, where `PortableValueAs[SignalWithNumber]` decodes the request payload.

## What to notice

- **A `RequestPort` is the human-in-the-loop primitive.** Typed `SignalWithNumber → int`, it turns each pause into a `RequestInfoEvent`. The port is factored behind a `responder` function so the offline test can script guesses instead of reading stdin — the console path stays in `consoleResponder`.
- **State survives a rewind via three hooks.** `Extend(&workflow.Executor{...})` attaches `ResetFunc` (fresh run), `OnCheckpointFunc` (save `tries` with `QueueStateUpdate`), and `OnCheckpointRestoredFunc` (reload `tries` with `ReadState`). Without these, a restored replay would lose the try count.
- **Checkpoints ride on `SuperStepCompletedEvent`.** Its `CompletionInfo.CheckpointInfo` is the handle passed to `run.RestoreCheckpoint(ctx, saved)` — the same live-rewind mechanism as the previous lesson, now spanning a human-gated cycle.
- **The cycle terminates by yielding.** `AddEdge(ask, judge)` + `AddEdge(judge, ask)` form the loop; the Judge ends it by calling `YieldOutput` instead of sending.

## How it maps to the Agent Framework Go SDK

`workflow.RequestPort` + `RequestInfoEvent` / `SendResponse` is the SDK's external-request machinery — the same primitive behind tool-approval gates — here used for a raw human input. Layering `WithCheckpointing` on top means a paused, waiting-on-a-human workflow is fully durable and rewindable, which is exactly what long-running approval and review workflows need.

## Run it

```bash
# Guesses feed in on stdin; these converge on the secret target (42):
printf '50\n25\n42\n' | go run ./tutorial/03-workflows/checkpoint/checkpoint_with_human_in_the_loop
go test ./tutorial/03-workflows/checkpoint/checkpoint_with_human_in_the_loop   # offline, scripted responder
```

There's no live model here; `AF_LIVE=1` skips. The offline test plays the whole game — and the rewind — with scripted guesses.

---

Next: [concurrent · Fan-out / Fan-in Workflow](/blog/posts/maf-go-74-concurrent.html)

## Key takeaways

- This lesson fuses two earlier patterns: a human-in-the-loop pause and checkpoint/restore, over a cyclic guess-the-number graph.
- A `workflow.RequestPort` with typed `SignalWithNumber → int` is the human-in-the-loop primitive — each pause becomes a `RequestInfoEvent`, answered with `request.CreateResponse(guess)` and `run.SendResponse(...)`.
- The port is factored behind a `responder` function so the offline test scripts guesses while the console path stays in `consoleResponder`.
- State survives a rewind through three executor hooks — `ResetFunc`, `OnCheckpointFunc` (save `tries`), `OnCheckpointRestoredFunc` (reload `tries`); without them a restored replay loses the try count.
- Layering `WithCheckpointing` over a paused, waiting-on-a-human workflow makes it fully durable and rewindable — exactly what long-running approval and review workflows need.

## Further reading

- [checkpoint · Checkpoint and Resume](/blog/posts/maf-go-72-checkpoint-and-resume.html)
- [group_chat_tool_approval · Human-in-the-loop inside a group chat](/blog/posts/maf-go-69-group-chat-tool-approval.html)
- [Human in the Loop](/blog/posts/maf-go-30-human-in-loop.html)
- [Microsoft Agent Framework for Go](https://github.com/microsoft/agent-framework-go)
