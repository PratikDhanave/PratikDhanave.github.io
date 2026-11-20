<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-intro.html -->

# Agentic Software Engineering in Go: Introduction

*Beyond unconstrained generation: building reliable AI-assisted development systems*

---

## The Problem: Vibe Coding Doesn't Scale

We've all seen it. An LLM generates impressive code in seconds. It compiles. It even runs. Three weeks later the "quick prototype" is in production, no tests exist for the generated paths, the original prompt is lost to a chat history, nobody can say why certain decisions were made, and the technical debt is compounding silently.

This is **vibe coding** — treating AI as a magic code generator rather than an engineering tool. It works for throwaway scripts. It fails for production systems, and it fails in a specific way: not at generation time, when everything looks great, but weeks later, when the absence of specs, verification, and auditability comes due.

The alternative this series builds is **agentic software engineering**: the same request flows through specification → context → generation → verification instead of prompt → code, every artifact is checked by machinery rather than vibes, and the whole process leaves an audit trail a teammate can pick up.

A disclosure up front, because this series will demand the same honesty from its own claims: every pattern here is implemented in a real companion codebase (a Go project with a CLI, an HTTP API, an MCP server, and a web dashboard), and the series' final post runs the whole stack end to end on a live local model and reports exactly what happened — including a judge-approved artifact that didn't compile. Where something in the codebase is scaffolding rather than production-ready, the post that covers it says so.

## The Five Disciplines

**Context engineering.** An unconstrained agent produces its statistical baseline — the most probable code given its training data, which is almost never *your* code. Context engineering makes architectural decision records, conventions, and specs the agent's operating environment, so output lands inside your standards instead of near them. [Post 2](/blog/posts/agentic-software-engineering-context.html) demonstrates this with a controlled experiment: the same prompt run with and without an ADR, on a real model, outputs compared.

**Specification engineering.** English prompts are ambiguous; specifications are checkable. A machine-readable spec defines intent, hard constraints (`must` / `must_not`), typed inputs and outputs, and a dependency-ordered plan — and is validated before any model runs. [Post 3](/blog/posts/agentic-software-engineering-specs.html).

**Verification loops (AI-TDD).** Every generated artifact passes build, test, and lint; failures come back as structured `file:line` findings that feed a bounded fix-retry loop. [Post 4](/blog/posts/agentic-software-engineering-verification.html) — including the real bugs found in the verification engine itself.

**Autonomy calibration.** Not every task deserves the same agent freedom. Risk, context quality, and track record should set how much runs unattended and where the human gates sit. [Post 6](/blog/posts/agentic-software-engineering-autonomy.html) presents the framework and is candid about how much of it is implemented versus design.

**Security by design.** An agent is an untrusted-input processor with execution privileges. Input validation, command allowlists, sandboxing, and API guarding belong in the harness, not in a hardening sprint afterward. [Post 7](/blog/posts/agentic-software-engineering-security.html).

## Why Go

The patterns are language-agnostic; the implementation benefits concretely from Go. The worker pool at the factory's core is a buffered channel and a `select` loop — orchestration maps directly onto goroutines without a framework. The whole system (CLI, API server, MCP server) deploys as static binaries. And the verification pipeline leans on the toolchain's uniformity: `go build ./...`, `go test ./...`, and `golangci-lint` behave identically everywhere, which matters when they're the arbiter of whether agent output is accepted.

## The Series

The twelve posts build the system in dependency order — each discipline, then their integration, then operating the result:

| # | Post | Grounded in |
|---|------|-------------|
| 1 | Introduction (this post) | — |
| 2 | [Context Engineering](/blog/posts/agentic-software-engineering-context.html) | `pkg/context` + a live A/B experiment |
| 3 | [Specification Engineering](/blog/posts/agentic-software-engineering-specs.html) | `pkg/spec` |
| 4 | [AI-TDD Verification Loops](/blog/posts/agentic-software-engineering-verification.html) | `pkg/verify` |
| 5 | [The Complete Harness](/blog/posts/agentic-software-engineering-harness.html) | `pkg/harness` |
| 6 | [Autonomy Calibration](/blog/posts/agentic-software-engineering-autonomy.html) | framework + the factory's real knobs |
| 7 | [Security & Safety](/blog/posts/agentic-software-engineering-security.html) | `pkg/security`, `pkg/webguard` |
| 8 | [Team Operating Model](/blog/posts/agentic-software-engineering-team.html) | git hooks, CI, `pkg/integration` |
| 9 | [Developer Workflow](/blog/posts/agentic-software-engineering-workflow.html) | the `asf` CLI |
| 10 | [Software Factory Orchestration](/blog/posts/agentic-software-engineering-factory.html) | `pkg/factory`, SQLite durability |
| 11 | [Production Operations](/blog/posts/agentic-software-engineering-ops.html) | `pkg/eval`, status API, benchmarks |
| 12 | [Case Study](/blog/posts/agentic-software-engineering-case-study.html) | one feature, end to end, live |

Start with post 2 — context engineering is the foundation the rest assumes — or jump straight to the [case study](/blog/posts/agentic-software-engineering-case-study.html) to see the whole machine run before reading how each part works.

---

*All code in this series is Go 1.23+ from the companion factory codebase; command output and timings in later posts come from real sessions against it.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-02
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-intro.html
Attribution: please link the canonical URL when citing or quoting this post.
