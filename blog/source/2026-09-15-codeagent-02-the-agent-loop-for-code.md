# The Agent Loop for Code — Read, Edit, Run, Observe

*Every coding agent, under the hood, runs the same loop: understand the situation, take an action, observe what happened, and decide the next action — repeating until the task is done. This read-edit-run-observe loop is the engine of a coding agent, and it works for code precisely because each action produces concrete, verifiable feedback. This post builds that loop and shows why closing it against real results is what separates an agent from a code generator.*

Post 1 said agency means acting and closing the loop. This post is the loop itself — the core execution model of a coding agent. Understanding it clarifies everything: why grounding (post 3) and tools (post 4) matter, why verification (post 6) is central, and why coding agents can self-correct. It's the beating heart of the series.

## The loop: observe, act, observe again

A coding agent operates as a cycle, the same shape as any agent (perceive → decide → act → perceive) specialized for software:

1. **Understand / observe the state** — read the relevant code, the task, the current situation (what files exist, what the error is, what the tests say). The agent builds a picture of where things stand.
2. **Decide the next action** — reason about what to do next given the goal and the current state: which file to read, what edit to make, what command to run.
3. **Act** — take a concrete action through a tool (post 4): read a file, edit code, run a command, execute tests, search the codebase.
4. **Observe the result** — see what the action produced: the file's contents, the edit's effect, the command's output, the test results, the error message.
5. **Repeat** — feed that observation back into understanding, and loop — deciding and taking the next action — until the task is complete (tests pass, the feature works) or the agent determines it's done or stuck.

The critical element is step 4→5: **the agent observes the concrete result of each action and uses it to decide the next one.** This is closing the loop, and it's what makes the agent *agentic* rather than a one-shot generator. A code generator produces code and stops; an agent makes a change, *runs it*, sees the error, and fixes it — iterating toward a working result. The loop is why a coding agent can start with a wrong first attempt and *converge* to a correct solution, which is how real engineering actually works (nobody writes correct code first try; they iterate against feedback).

## Why feedback makes the loop work for code

The loop is powerful for coding *specifically because code gives concrete feedback at every step* (post 1's verifiability), and this is worth seeing in detail:

- **Every action has an observable result.** Read a file → see its contents. Make an edit → see the new code. Run the program → see output or a crash. Run tests → see pass/fail and error messages. Unlike fuzzy domains where an action's effect is unclear, code actions produce *clear, objective* observations the agent can reason over. The environment talks back precisely.
- **Errors are signals, not dead ends.** A compile error, a failing test, a stack trace — these are *rich feedback* telling the agent exactly what's wrong, which it uses to correct course. The agent's ability to *read an error and fix the cause* is the loop's superpower, and it's why coding agents handle the normal messiness of programming (things don't work the first time) gracefully. Errors drive the loop forward rather than stopping it.
- **Convergence through iteration.** Because each iteration gets concrete feedback, the agent can *converge*: attempt, observe failure, refine, re-attempt, until it works. This mirrors the debugging loop every engineer runs, and it's why a coding agent can solve tasks it couldn't produce correctly in one shot. The loop turns "generate correct code" (hard) into "generate, test, fix, repeat" (tractable).

The deep point: the agent loop *plus* code's concrete feedback equals reliable self-correction. The agent isn't expected to be right first try; it's expected to *iterate against real results toward being right*, which is both more achievable and more robust. This is why the loop, not the model's raw code-generation ability, is the essence of a coding agent — the model provides the reasoning at each step, but the *loop against feedback* is what gets to a working solution.

## What the loop needs, and where it struggles

The loop frames the rest of the series by revealing what it depends on and where it breaks:

- **It needs good observation (grounding, post 3).** The agent can only decide well if it *understands the state* — which means reading the right code, having the relevant context, and navigating the codebase effectively. Poor grounding (the agent doesn't understand the code it's changing) produces bad decisions, so grounding the agent in the codebase is essential to the loop's "observe" step.
- **It needs reliable actions (tools, post 4).** The "act" step happens through tools — editing, running, testing, searching — so the agent needs well-designed, reliable tools to act through. The loop is only as good as the tools it acts with.
- **It needs a clear success signal (verification, post 6).** The loop terminates when the task is "done," which requires *knowing* it's done — passing tests, a working result. Where verification is strong (good tests), the loop converges reliably; where it's weak (no tests, fuzzy success), the agent can't tell if it succeeded, and the loop struggles. This is the deepest limitation: **the loop is only as reliable as the feedback that drives it.**
- **It can get stuck or loop unproductively.** Without good feedback or when a task is beyond it, the agent can thrash — repeating failing attempts, going in circles, or confidently "finishing" something broken. Bounding the loop (iteration limits), detecting stuck states, and knowing when to escalate to the human are real engineering concerns (and connect to the agent-governance/bounded-execution ideas elsewhere).

The synthesis: the coding agent is, at its core, a **read-edit-run-observe loop** that closes against code's concrete feedback — observe the state, decide an action, act through a tool, observe the result, repeat — converging to a working solution by iterating the way a human engineer debugs. It works *because* code gives objective feedback at every step (verifiability from post 1), it *needs* good grounding (post 3), reliable tools (post 4), and a clear success signal (post 6), and it *struggles* exactly where that feedback is weak. Hold the loop as the engine of everything that follows: the model reasons, but the loop-against-feedback is what makes a coding agent reliably get to working code.

The throughline: every coding agent runs a **read-edit-run-observe loop** — observe the state (read code, the task, the error), decide the next action, act through a tool (read/edit/run/test/search), observe the concrete result, and repeat until done. The critical element is **observing each action's result and using it to decide the next** — *closing the loop*, which makes it an **agent** (iterates to a working solution) rather than a one-shot **generator** (produces code and stops). It works for code specifically because **code gives concrete feedback at every step**: every action has an observable result, **errors are rich signals not dead ends** (read the stack trace, fix the cause — the loop's superpower), enabling **convergence through iteration** (attempt → observe failure → refine, like human debugging — turning "write correct code" into the tractable "generate, test, fix, repeat"). The loop *needs* good **grounding** (post 3, to observe well), reliable **tools** (post 4, to act), and a clear **success signal/verification** (post 6, to know it's done) — and it **struggles or thrashes exactly where feedback is weak** (no tests, fuzzy success), so *the loop is only as reliable as the feedback that drives it.*

## Key takeaways

- A coding agent is, at its core, a **loop**: **observe the state** (read relevant code, the task, errors, test results) → **decide the next action** → **act** through a tool (read/edit/run/test/search) → **observe the result** → **repeat** until the task is done or the agent is stuck.
- The critical element is **observing each action's concrete result and using it to decide the next** — *closing the loop* — which is what makes it an **agent** (converges to a working solution) vs a one-shot **code generator** (produces and stops); the agent isn't expected to be right first try, but to **iterate against real results toward being right**.
- The loop works for code because **code gives concrete feedback at every step**: every action has an **observable result** (file contents, output, crash, pass/fail), **errors are rich signals** (a stack trace tells the agent exactly what to fix — the loop's superpower, handling programming's normal messiness), and this enables **convergence through iteration** (mirroring the human debug loop; turning "write correct code" into "generate, test, fix, repeat").
- The essence of a coding agent is **the loop, not the model's raw generation ability** — the model reasons at each step, but *the loop against feedback* is what gets to working code (reliable self-correction = agent loop + code's concrete feedback).
- The loop **depends on** good **grounding** (post 3 — observe/understand the state), reliable **tools** (post 4 — act), and a clear **success signal/verification** (post 6 — know when done), and it **struggles/thrashes where feedback is weak** (no tests, fuzzy success — the agent can't tell if it succeeded) — so *the loop is only as reliable as the feedback driving it*, and bounding it (iteration limits, stuck-detection, escalation) is a real concern.

## Further reading

- [Software agent — the perceive-decide-act loop specialized for code](https://en.wikipedia.org/wiki/Software_agent)
- [Debugging — the iterate-against-feedback process the loop mirrors](https://en.wikipedia.org/wiki/Debugging)
