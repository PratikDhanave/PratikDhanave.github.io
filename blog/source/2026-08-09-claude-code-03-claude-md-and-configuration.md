# CLAUDE.md and Project Configuration

*The single highest-leverage setup step for Claude Code is a good CLAUDE.md — the file where you write down, once, the context and conventions you'd otherwise repeat every session.*

Claude Code is a capable collaborator that doesn't share your context (post 1). CLAUDE.md is how you give it that context durably. Instead of re-explaining your build commands, conventions, and gotchas in every conversation, you write them down once and Claude Code loads them automatically. Getting this file right is the difference between an agent that constantly guesses your conventions and one that follows them from the first message. This post is about CLAUDE.md and the configuration around it.

## What CLAUDE.md is

CLAUDE.md is a Markdown file that Claude Code reads automatically at the start of a session and treats as standing instructions for working in that project. Think of it as the onboarding doc you'd hand a new engineer — except it's read every time, so it's always applied. It typically lives at your repo root and is checked into version control so the whole team benefits.

There's a small hierarchy worth knowing:

- **Project CLAUDE.md** (repo root, committed) — shared team conventions for this codebase.
- **Nested CLAUDE.md** (in subdirectories) — context specific to a module, applied when working there.
- **User-level memory** (in your home config) — your personal preferences across all projects.

They layer, so project rules cover the repo while personal preferences follow you everywhere.

## What to put in it

The best CLAUDE.md is *specific and useful*, not a wall of generic advice. High-value contents:

- **How to build, test, and run.** The exact commands — `make test`, `npm run build`, how to run a single test. This is the most-used section; it lets the agent verify its own work (post 2's loop).
- **Project structure and where things live.** A short map so it doesn't have to rediscover the layout every time.
- **Conventions the code follows.** Naming, error handling, the patterns you want matched, libraries to prefer or avoid.
- **Gotchas and non-obvious rules.** "Don't edit generated files in `/dist`," "this service has no tests, be careful," "we use X not Y." The things that would trip up a new engineer.
- **What NOT to do.** Constraints are as valuable as instructions — "never commit to main," "don't add dependencies without asking."

**The gotcha:** a CLAUDE.md stuffed with generic best-practices ("write clean code," "add tests") wastes context and teaches the model nothing it doesn't know — every line competes for attention. Keep it specific to *this* project: the commands, the conventions, the gotchas that are actually true here.

## Keep it tight and current

CLAUDE.md is loaded into context every session, so it has a real cost — bloat dilutes everything else. Treat it like code you maintain:

- **Prune ruthlessly.** If a line isn't earning its place, cut it. Shorter and accurate beats long and aspirational.
- **Keep it true.** An out-of-date CLAUDE.md (wrong build command, renamed module) is worse than none — it actively misleads the agent. Update it when the project changes.
- **Iterate from real sessions.** When Claude Code makes a mistake a rule would have prevented, add the rule. When a rule never fires, remove it. The file gets better by observation.

## Configuration beyond CLAUDE.md

CLAUDE.md handles *context and conventions*; separate configuration handles *behavior and permissions*:

- **Settings files** control things like permission rules (which tools/commands are allowed without asking), environment, and defaults — at user, project, and local (uncommitted) levels. This is where you tune autonomy (post 1) safely and shareably.
- **Permission allowlists** let you pre-approve safe, frequent actions (e.g. running your test command) so you're not clicking approve constantly, while keeping consequential actions gated.
- **`.gitignore`-style scoping and ignore rules** keep the agent out of files it shouldn't touch or read.
- **Slash commands, subagents, hooks, and skills** (later posts) are also configured in the project, turning repeated setup into shared, versioned assets.

The principle: **make the good setup shareable and version-controlled.** A well-configured repo means every teammate's Claude Code starts with the same context, conventions, and guardrails.

**The gotcha:** putting secrets or machine-specific paths in a committed config or CLAUDE.md leaks them to the whole team and to anyone who clones the repo — keep those in local (uncommitted) settings or environment, and commit only what's genuinely shared.

## A realistic CLAUDE.md, annotated

Here's the shape of a useful project CLAUDE.md — specific, not generic:

```markdown
# Project: payments-api (Go)

## Build & test
- `make test` — full suite; `go test ./path -run TestName` for one test
- `make lint` — golangci-lint; CI fails on any lint error
- Run locally: `make run` (needs Postgres via `docker compose up db`)

## Layout
- `cmd/` entrypoints · `internal/` private pkgs · `internal/ledger/` the core

## Conventions
- Money is integer minor units + currency code — NEVER floats
- Errors: wrap with `fmt.Errorf("...: %w", err)`; no naked returns
- New endpoints: add a table-driven test and an authz check

## Do not
- Don't edit `internal/pb/` (generated protobuf)
- Don't add dependencies without asking
- Never commit to main; branch first
```

Every line earns its place: the commands let the agent verify its own work, the money rule prevents a whole class of bug, and the "do not" list heads off the mistakes a newcomer (human or agent) actually makes. Notice what's *absent* — no "write clean code," no "follow best practices." Those cost context and teach nothing.

**The gotcha:** the money-units and generated-code rules above are exactly the kind of thing the model can't infer from the code alone in one glance — it might see a `float64` elsewhere and follow it, or "helpfully" regenerate a file you hand-edited. The highest-value CLAUDE.md lines are the project-specific invariants and traps, not the universal advice.

## The payoff

The upfront investment in CLAUDE.md and config compounds. Every session starts with the agent already knowing how to build and test, which conventions to follow, and what not to touch — so you spend your specification effort (post 2) on the task, not on re-explaining the project. On a team, it means consistent agent behavior across everyone who works in the repo. It's the closest thing Claude Code has to a "set it up once" lever, and it's worth doing early.

## Key takeaways

- **CLAUDE.md is auto-loaded standing context** — write your project's conventions once instead of repeating them every session; commit it so the team shares it.
- It **layers**: project (committed) + nested (per-module) + user-level (personal preferences).
- Fill it with **specifics** — build/test/run commands, structure, conventions, gotchas, and what NOT to do — not generic advice.
- **Keep it tight, true, and iterated** — it costs context every session, and a stale file actively misleads.
- Use **settings/permission files** for behavior and autonomy, and keep secrets/machine-specific paths in local (uncommitted) config.
- Well-configured repos give **every teammate the same context and guardrails** — the highest-leverage one-time setup.

## Further reading

- [Claude Code — memory and CLAUDE.md](https://docs.claude.com/en/docs/claude-code/memory) — how the file is loaded and layered.
- [Claude Code — settings and permissions](https://docs.claude.com/en/docs/claude-code/settings) — configuring behavior, permissions, and scope.
- [Claude Code — best practices](https://www.anthropic.com/engineering/claude-code-best-practices) — what makes a CLAUDE.md effective.
