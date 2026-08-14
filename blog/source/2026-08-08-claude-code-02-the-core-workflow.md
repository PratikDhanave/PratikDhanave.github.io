# The Core Workflow

*Getting great results from Claude Code is less about clever prompts and more about a disciplined loop: give context, specify clearly, let it work, review, and steer.*

Once you understand what Claude Code is (post 1), the question becomes how to actually work with it day to day. The engineers who get the most from it aren't writing magic incantations — they've internalized a workflow that plays to the tool's strengths and compensates for its blind spots. This post lays out that loop.

## Explore, plan, execute, review

The most reliable pattern for anything non-trivial is a four-beat loop:

1. **Explore.** Before changing code, have Claude Code *understand* the relevant part of the codebase — "read how sessions are handled and explain the flow." Grounding it in the real code prevents plausible-but-wrong changes.
2. **Plan.** For anything with more than one step, ask for a plan before edits ("outline the approach, don't write code yet"). Cheap to review, and it catches a wrong direction before any code is written. (There's a dedicated plan mode for exactly this.)
3. **Execute.** Let it make the changes, run the tests, and iterate on failures.
4. **Review.** Read the diff as you would a colleague's PR — it's your accountability, not the model's (post 1).

Skipping straight to "execute" on a fuzzy request is the most common way to get output you then have to unwind.

**The gotcha:** for multi-step or risky work, asking for a plan first is the single highest-leverage habit — reviewing a three-line plan is far cheaper than reviewing (and reverting) a 300-line wrong implementation.

## Specify like you'd brief a colleague

Claude Code is capable but doesn't share your context or taste. Good specification closes that gap:

- **State the goal and the "done" condition.** "Add pagination to the orders API — cursor-based, matching how the products API does it, with tests" beats "add pagination."
- **Point at the right context.** Name the files, the pattern to follow, the constraints. It can find things, but pointing it at the relevant code saves time and prevents wrong guesses.
- **Give constraints and non-goals.** "Don't change the public response shape," "keep it in this module," "no new dependencies." Constraints are as valuable as the goal.
- **Provide examples.** "Follow the pattern in `handlers/products.go`." Concrete beats abstract, for models as for juniors.

## Steer actively; don't monologue

Working with an agent is a conversation, not a one-shot prompt. If it's heading the wrong way, interrupt and correct — you don't have to let a wrong approach run to completion. Course-correct early and specifically ("stop — use the existing validator instead of writing a new one"). The tighter your steering loop, the less rework. Equally, when it asks a clarifying question, answer it precisely; a vague answer produces a vague result.

**The gotcha:** letting a visibly-wrong direction run "to see what it does" wastes the run and muddies the context. Interrupt and redirect the moment you see it going astray — early correction is cheap, late correction means unwinding work.

## Manage the context

Claude Code works within a context window, and long, sprawling sessions dilute focus (the model spends attention on stale history). Practical hygiene:

- **One coherent task per session/thread.** Start fresh for an unrelated task rather than dragging a long, mixed history along. (`/clear` resets context when you switch tasks.)
- **Keep durable context in files, not the chat.** Project conventions belong in CLAUDE.md (post 3), not re-typed each session.
- **Let it re-ground.** For a big task, having it re-read the key files beats relying on a fuzzy memory from 40 messages ago.

## Right-size the task

Match the size of what you delegate to how much you trust the setup. Big, well-specified, well-tested tasks are where the agent shines — but if the codebase has no tests and the requirements are fuzzy, break the work down and verify each step. A good rule: the larger the delegation, the more important that there's an objective check (a test suite, a type checker, a build) the agent can loop against. Tests aren't just quality insurance — they're the signal that lets the agent self-correct.

**The gotcha:** delegating a large change in a codebase with no automated checks means neither you nor the agent has a fast way to know it worked — the agent can't loop against a green/red signal, and you're left reviewing everything by eye. Add a test or a smaller scope first.

## Use the tools around the loop

Fluency with the surrounding features multiplies the core loop: plan mode for deliberate design, `/clear` for context hygiene, permission settings for the right autonomy (post 1), and — as the series continues — CLAUDE.md for durable context (post 3), subagents for parallel legwork (post 5), and slash commands for repeatable workflows (post 7). You don't need all of it on day one; the four-beat loop plus clear specification carries most work.

## A worked example

Say you're adding rate limiting to a login endpoint. The loop in practice:

```text
You:  "Read how the login handler and middleware are wired, then explain
       where a rate limiter would slot in. Don't write code yet."
CC:   <reads handler, middleware, config> "Login is handled in auth/login.go,
       middleware chains in server.go. A limiter fits as middleware keyed by
       IP+username. You already use go-redis, so a Redis token bucket fits."
You:  "Good. Plan the change — files, approach, tests."
CC:   <plan: new ratelimit middleware, wire it, config knobs, table tests>
You:  "Do it. Cap at the existing config style; add tests for allow + deny."
CC:   <edits, runs `go test ./...`, one test fails, fixes, re-runs, green>
You:  <review the diff> "The deny path should return 429 with Retry-After."
CC:   <adjusts, re-runs tests>
```

Notice the shape: explore grounds it in *your* code, the plan is reviewed before any edits, execution loops against the test suite (the objective signal), and you steer on specifics at review time. The same four beats scale from a one-file tweak to a multi-file feature — you just spend more time on the plan and review as the change grows.

**The gotcha:** the failure version of this is one message — "add rate limiting" — followed by accepting whatever comes back. Without the explore and plan beats it may pick the wrong layer, miss your Redis usage, or invent a config style; without reviewing the diff you ship the 429-vs-200 detail wrong. The loop is what turns a plausible change into a correct one.

## Key takeaways

- Use the **explore → plan → execute → review** loop; don't jump straight to execute on fuzzy requests.
- For multi-step/risky work, **get a plan first** — reviewing a plan is far cheaper than reverting a wrong implementation.
- **Specify like briefing a colleague**: goal, done-condition, the right context, constraints/non-goals, and examples to follow.
- **Steer actively** — interrupt and correct early; it's a conversation, not a one-shot prompt.
- **Manage context**: one task per session, durable conventions in files, re-ground for big tasks.
- **Right-size delegation to your checks** — the bigger the task, the more you need tests/types/build for the agent to loop against.

## Further reading

- [Claude Code — best practices](https://www.anthropic.com/engineering/claude-code-best-practices) — the explore/plan/execute workflow and specification tips.
- [Claude Code documentation — common workflows](https://docs.claude.com/en/docs/claude-code/common-workflows) — plan mode, context management, and steering.
- [Claude Code — CLI and interactive usage](https://docs.claude.com/en/docs/claude-code/overview) — the interactive loop and controls.
