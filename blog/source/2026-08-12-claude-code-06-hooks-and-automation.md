# Hooks and Automation

*Hooks turn "please always run the formatter" from a hope into a guarantee — deterministic shell commands that fire on Claude Code's lifecycle events, no matter what the model decides.*

Prompting and CLAUDE.md shape what Claude Code *tends* to do, but they're probabilistic — the model usually follows them. For things that must happen *every time*, you want determinism. Hooks provide it: user-defined shell commands that Claude Code runs automatically at specific points in its lifecycle. They're how you enforce policy, automate the boring, and wire the agent into your existing tooling with certainty rather than hope. This post is about using them.

## What hooks are

A hook is a command you register to run on a lifecycle **event**. Instead of asking the model to remember to do something, the hook *always* does it. The events cover the key moments in an agent's loop — notably:

- **Before a tool runs** (e.g. before an edit or a shell command) — inspect or gate the action.
- **After a tool runs** (e.g. after a file is edited) — react to what just happened.
- **On other lifecycle moments** — when a session starts, when the agent finishes/stops, when a prompt is submitted, and so on.

Because hooks are just shell commands, they can do anything your shell can: run a formatter, run tests, lint, log, send a notification, or block an action.

## What hooks are great for

The canonical uses cluster around *guarantees* and *automation*:

- **Auto-format after edits.** A PostToolUse hook that runs your formatter on files Claude Code just edited means formatting is never something you review — it's always done. (This is the classic first hook everyone adds.)
- **Enforce policy / block bad actions.** A PreToolUse hook can inspect a pending command or edit and *block* it — e.g. refuse edits to a protected path, or refuse a dangerous command. This is deterministic guardrail enforcement, stronger than a CLAUDE.md rule the model might overlook.
- **Run checks automatically.** Kick off tests or a linter after changes so failures surface immediately in the loop.
- **Notify and log.** Send a desktop/Slack notification when the agent needs input or finishes; keep an audit log of what actions ran.
- **Inject context.** A session-start hook can add project state the agent should always know.

**The gotcha:** the power of hooks is that they run deterministically with your permissions — which is also the risk. A hook is arbitrary code that executes automatically; a careless or malicious hook can do real damage without a prompt. Only add hooks you understand, keep them simple, and be cautious with hooks from untrusted sources.

## Hooks vs. prompting vs. permissions

These three controls do different jobs, and using the right one matters:

- **Prompting / CLAUDE.md** — *influences* behavior (probabilistic). Good for conventions and preferences.
- **Permissions** — *gates* actions for your approval (interactive). Good for "ask me before doing X."
- **Hooks** — *guarantee* an action or block (deterministic, automatic). Good for "this must always happen / never happen."

The pattern: use CLAUDE.md for "please prefer," permissions for "ask me first," and hooks for "always/never, no exceptions." Reaching for a hook when a CLAUDE.md line would do adds brittle machinery; relying on a CLAUDE.md line when you need a guarantee (a compliance rule, a protected path) leaves a gap the model can slip through.

**The gotcha:** trying to enforce a hard rule ("never touch the migrations folder") through CLAUDE.md wording alone is unreliable — the model *usually* complies, but "usually" isn't a guarantee. If it must never happen, a PreToolUse hook that blocks it is the right tool.

## Keeping hooks maintainable

Hooks are configuration that lives with the project (committed, like the rest of post 3's setup), so treat them as code:

- **Keep them fast and quiet.** A hook runs on every matching event; a slow hook taxes every action. Format the changed file, don't rebuild the world.
- **Make them idempotent and safe to re-run.** They'll fire often; they shouldn't have surprising cumulative effects.
- **Fail informatively.** If a hook blocks an action, it should say why, so you (and the agent) understand what happened.
- **Scope them.** Match hooks to the relevant tools/paths rather than firing on everything.

Committing hooks to the repo means the whole team gets the same automatic formatting, the same guardrails, and the same checks — turning individual discipline into enforced team policy.

## A realistic starter set

Most teams converge on a small, high-value set: auto-format on edit, run the linter/tests after changes to catch breakage in the loop, block edits to generated or protected paths, and a notification when the agent needs attention. That handful removes a whole category of "did it remember to…" review and makes the agent's behavior consistent and safe. Add more only when a real, repeated need appears — hook sprawl is its own maintenance burden.

## Key takeaways

- **Hooks are shell commands that fire deterministically on lifecycle events** (before/after tools, session start, stop, etc.) — guarantees, not hopes.
- Great for **auto-formatting, enforcing/blocking policy, running checks, notifications, logging, and context injection**.
- Use the **right control**: CLAUDE.md to *influence*, permissions to *gate interactively*, hooks to *guarantee or block automatically*.
- Hooks run **arbitrary code with your permissions** — keep them simple, understood, and be wary of untrusted ones.
- Keep them **fast, idempotent, informative, and scoped**; commit them so the whole team shares the same guardrails.
- A small starter set (format, test/lint, block protected paths, notify) removes a whole class of review overhead.

## Further reading

- [Claude Code — hooks](https://docs.claude.com/en/docs/claude-code/hooks) — the lifecycle events and how to configure hooks.
- [Claude Code — hooks guide / examples](https://docs.claude.com/en/docs/claude-code/hooks-guide) — practical hook patterns.
- [Claude Code — settings and permissions](https://docs.claude.com/en/docs/claude-code/settings) — how hooks relate to permissions and config scope.
