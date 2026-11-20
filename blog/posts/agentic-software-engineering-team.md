<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-team.html -->

# Agentic Software Engineering in Go: Team Operating Model

*Integrating agent workflows into team software development lifecycles*

---

## The Problem: The Private Superpower

In most organizations, agentic development arrives as a personal tool: one developer gets dramatically faster, their prompts and hard-won context live in a private chat history, and when they go on holiday the capability goes with them. Nothing about the previous seven posts' machinery — specs, context, verification, the factory — automatically makes any of it a *team* asset.

The team operating model is the set of decisions that turn it into one. Most of them are not new infrastructure; they're about where existing artifacts live and which existing chokepoints run the machinery. This post is concrete about which parts the companion codebase implements today and which parts are team practice you build with ordinary git and CI.

## The Shared Context Is the Repository

The single most consequential decision is also the simplest: **the agent's context lives in the repo, not in anyone's head.** The context engine ([post 2](/blog/posts/agentic-software-engineering-context.html)) walks `docs/` and `specs/` in the working tree — which means the "shared context repository" isn't a new system to stand up. It's a convention about the one you have:

```text
docs/        ADR-001-Example.md, ...     # constraints, priority 100
specs/       auth-service.yaml, ...      # machine-readable intent, priority 90
pkg/, cmd/   source code                 # patterns, priority 50
```

This has a compounding property that private prompting can't match: when one developer writes an ADR to fix an agent failure (the case study's jwt/v5 hallucination is the canonical example — two lines of dependency notes would have prevented it), *every teammate's* future generations inherit the fix. Context improvements are commits; they're reviewed, versioned, and they never leave with an employee. The practical rule that follows: **ADRs and specs go through pull requests like code**, because they now *are* code — they program the agents.

The same logic makes spec review the team's highest-leverage review activity. A flawed function fails once; a flawed spec generates flawed artifacts for everyone until someone notices.

## Verification at the Chokepoints

The verification pipeline ([post 4](/blog/posts/agentic-software-engineering-verification.html)) becomes a team property the moment it runs where the team already converges: commits and PRs. The pre-commit hook is three honest lines — `asf verify` is a single static binary, so there's no toolchain ceremony:

```bash
#!/bin/sh
# .git/hooks/pre-commit
exec ./asf verify
```

And CI runs the same gate on every PR with a perfectly ordinary workflow:

```yaml
# .github/workflows/verify.yml
name: verify
on: [pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: "1.23" }
      - run: go build -o asf ./cmd/asf
      - run: ./asf verify
```

Nothing clever — deliberately. The point is *which* check runs at the chokepoint, not the plumbing around it. One field note from dogfooding: the first time a team wires this up, expect the gate to fail on the existing codebase (the factory's own repo surfaced 50 standing lint findings when its parser started working). Budget for that cleanup; a gate the team routinely bypasses is worse than no gate.

## Agent-Assisted Review: What Exists

The factory implements a `review` task type today. It assembles the same spec + context prompt as generation, with a review instruction whose design is worth copying — it explicitly tells the model *not* to self-censor:

```go
instruction := "## Task: Code Review\nReview the project context below against " +
	"the specification. Report every issue you find, including ones you are " +
	"uncertain about or consider low-severity — a downstream step filters by " +
	"importance. For each finding include file, severity, and a concrete fix.\n\n"
```

That one sentence encodes a real lesson about LLM reviewers: models filter aggressively toward confident findings unless told otherwise, and you want the filtering to happen downstream where a human sets the threshold, not inside the model where nobody sees what was dropped.

Review tasks launch like any factory task (`POST /api/factory/launch/review`, or the dashboard) and their findings land on the task record. What does **not** exist yet: automatic posting of findings as PR comments. Today the wiring from "review task result" to "comment on GitHub PR" is a human or a script you write; the `pkg/integration` adapters for GitHub, Slack, Teams, and Linear model webhooks and connection state and compile, but are not wired to live credentials — the honest status (`asf integration list` currently prints an empty registry). Treat agent review as a *pre-reviewer* that drafts findings for the human reviewer, which — given the case study's judge-approved-but-uncompilable artifact — is where it belongs on the autonomy ladder ([post 6](/blog/posts/agentic-software-engineering-autonomy.html)) anyway.

## Onboarding: The Spec Directory Is the Curriculum

A side effect of spec-driven work: the onboarding path writes itself, out of artifacts that are maintained *because the factory needs them*, not as documentation homework.

1. **Read `docs/` and `specs/`** — the ADRs say how we build and why; the specs say what the system is supposed to do. Unlike a wiki, these can't rot silently: the machinery executes them daily.
2. **Run `./asf verify`** — see the team's quality gate pass on a fresh clone (and learn the project builds green on day one).
3. **Run `./asf spec generate <some-spec>`** — read exactly what an agent gets told; this teaches the house style of constraints faster than any style guide.
4. **Author a small spec, run it through the factory, review the artifact** — the full loop, supervised, on something low-risk.

A new developer who has done those four things understands the team's actual operating model — not a stale onboarding doc's description of it.

## What to Measure (From Data You Already Have)

Skip the KPI wall. The factory's task store ([post 11](/blog/posts/agentic-software-engineering-ops.html)) already records per task: type, attempts, judge score, verification outcome, duration. Three questions it can answer honestly, team-wide:

- **Is quality drifting?** Judge-score trend per spec family.
- **Where does the loop thrash?** Attempt counts by spec — persistent 2+-attempt specs are context or spec problems with a name attached, which converts "the agent is flaky" arguments into "this spec needs work" tickets.
- **Is the gate holding?** Verification pass rate at the PR chokepoint over time.

Resist inventing targets for these on day one; collect a month of baseline first. (The temptation to publish a dashboard of invented targets is exactly the failure mode this series keeps warning about — numbers nobody measured, driving decisions nobody can defend.)

## The Operating Model in One Paragraph

Context and specs live in the repo and go through PR review, because they program the agents. Verification runs at the chokepoints the team already has. Agent review drafts findings; humans decide. Onboarding is reading and running the artifacts the system already maintains. And the factory's task history — not anecdotes — is the evidence base for tuning any of it. None of this requires new infrastructure beyond the factory itself; it requires the team agreeing that these artifacts are now load-bearing.

The [next post](/blog/posts/agentic-software-engineering-workflow.html) zooms back in to the individual: what the daily developer loop looks like when this model is in place.

---

*All code, command output, and prompts in this post are from the companion factory codebase (Go 1.23+); the CI workflow and pre-commit hook are the straightforward wiring shown, not product features.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-09
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-team.html
Attribution: please link the canonical URL when citing or quoting this post.
