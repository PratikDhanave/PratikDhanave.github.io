<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-autonomy.html -->

# Agentic Software Engineering in Go: Autonomy Calibration

*Calibrating agent freedom with the AEMM maturity model and Elastic Loop framework*

---

## The Problem: Fixed Autonomy Levels

Discussions of coding agents usually assume a fixed autonomy ladder:

- **Level 0** — developer writes all code
- **Level 1** — agent suggests, developer approves each piece
- **Level 2** — agent generates functions, developer reviews
- **Level 3** — agent implements features, developer validates the result
- **Level 4** — agent owns work end-to-end, human on exception

Teams pick a rung and stay there. That's wrong in both directions at once: level 2 everywhere means a senior team hand-reviews logging utilities forever, and level 4 everywhere means the payment path gets the same oversight as the README generator. The autonomy a task deserves depends on variables that differ *per task* — how risky it is, how good the context is, and what the track record says — so the level should be computed, not configured.

Before the framework, a transparency note: this post is the series' most design-forward. The factory implements autonomy as a handful of concrete gates (shown below with real values); the full scoring model is a framework for reasoning and a roadmap, not shipped code. The post is explicit about which is which.

## AEMM: Autonomy as a Computed Property

The **Autonomous Engineering Maturity Model** scores four dimensions per task, each 0–100:

| Dimension | What it measures | What moves it |
|-----------|------------------|---------------|
| **Risk** | Blast radius if the agent is wrong | Auth/payment surfaces, data sensitivity, novelty of the stack |
| **Context quality** | How well-specified the operating environment is | ADR coverage, spec completeness, established code patterns |
| **Agent confidence** | How reliable generation is for this kind of task | Historical judge scores, verification pass rates for similar specs |
| **History** | The track record of this team + factory configuration | Verified-success rate over recent tasks |

The **Elastic Loop** collapses them into a score and a level — elastic because the inputs are re-measured as evidence accumulates, so autonomy drifts up as context and track record improve, and snaps down when failures arrive:

```go
// Design sketch — the scoring model as code. The factory does not ship
// this function yet; its current gates are the concrete knobs below.
func CalculateAutonomy(risk, contextQuality, confidence, history float64) (float64, int) {
	score := (contextQuality + confidence + history - risk) / 3
	score = math.Max(0, math.Min(100, score))

	switch {
	case score >= 80:
		return score, 4 // autonomous, monitored
	case score >= 60:
		return score, 3 // managed: human validates results
	case score >= 40:
		return score, 2 // supervised: human reviews code
	case score >= 20:
		return score, 1 // assisted: human approves each step
	default:
		return score, 0 // manual
	}
}
```

The formula's exact weights matter less than its structure: **context quality and track record buy autonomy; risk spends it.** A high-risk task on a well-specified, well-tracked codebase can earn more freedom than a trivial task in an undocumented one — which matches engineering intuition and is exactly what fixed levels can't express.

## The Autonomy Knobs That Exist Today

The factory's implemented autonomy surface is small, concrete, and real — these are the actual defaults from the running system:

- **Judge threshold (0.75).** Every LLM generate task is scored by an LLM judge ([post 11](/blog/posts/agentic-software-engineering-ops.html)); output below threshold is regenerated with the judge's feedback. Raising the threshold is reducing autonomy: more output gets sent back before a human ever sees it.
- **Judged attempts (`ASF_EVAL_MAX_ATTEMPTS`, default 2)** and **harness retries (default 3).** Bounded loops are an autonomy decision: how long the system may thrash unattended before a human must look.
- **Per-agent capabilities in `factory.yaml`.** The factories-as-code definition ([post 10](/blog/posts/agentic-software-engineering-factory.html)) assigns each agent a role, a model, and a capability list (`["generate", "refactor"]` vs `["verify"]`) — coarse-grained autonomy by construction: an agent can't do what it was never wired to do.
- **RBAC tool allowlists.** `pkg/security` ([next post](/blog/posts/agentic-software-engineering-security.html)) gives the `agent` role `write_file` but not `spawn_agent`; the `validator` role gets neither. Tool access *is* autonomy, enforced at the lowest level.

Mapping these onto AEMM: today's factory runs a fixed policy equivalent to level 3 for generation (agent produces, judge validates, human reviews the artifact) with level-controlling knobs set globally rather than per task. The designed next step — computing risk from spec metadata and feeding judge-score history into per-task gating — has an obvious home: the task record already persists attempts, scores, and outcomes to SQLite, so the `history` input is being collected every run.

## What the Case Study Says About Where Gates Belong

The framework is theory; the series' [case study](/blog/posts/agentic-software-engineering-case-study.html) produced data, and it bears directly on calibration:

- The LLM judge passed an artifact at 0.91 that failed `go build` — the generating model and the judging model shared the same blind spot (a hallucinated API, specifically *praised* by the judge). **Judge approval alone cannot anchor high autonomy**; the toolchain gate is non-negotiable at every level above 0.
- The converged artifact's tests all passed — and omitted the expired-token and reuse cases, the two highest-value scenarios in an auth package. Tests written by the generating model inherit its blind spots, so **"tests pass" earns less autonomy credit than it appears to.**
- Convergence took four rounds, and only landed when a human put the exact correct API into the feedback. On a task where the model's training knowledge was stale, **effective autonomy was level 2 regardless of policy** — the system's real autonomy is capped by the weakest of its feedback loops, not by its configuration.

That last point is the practical heart of calibration: autonomy settings don't *create* capability, they *acknowledge* it. The way to raise a task's sustainable autonomy level is to improve the inputs AEMM scores — better context (the jwt/v5 cheat-sheet that would have prevented the hallucination), better specs, accumulated verified history — and let the score follow.

## Calibration as Operating Practice

Until per-task scoring is wired, AEMM still earns its keep as the team's shared vocabulary for three recurring decisions:

1. **Which specs may run unattended in the factory?** Score them mentally on the four dimensions; anything touching auth, money, or data deletion stays human-validated (risk dominates) no matter how good the track record.
2. **When does a knob move?** Change autonomy settings on evidence, not sentiment: a month of ≥0.85 judge scores on a spec family justifies raising `ASF_EVAL_MAX_ATTEMPTS`; a hallucination incident justifies a context fix *and* a temporary gate tightening on that dependency's surface.
3. **Where does review attention go?** Reviewer minutes are the scarce resource autonomy allocates. Spend them where risk is high and history is thin; stop spending them where the pipeline has been green for months on low-risk surfaces.

The [next post](/blog/posts/agentic-software-engineering-security.html) covers the floor under all of this — the security layer that holds whatever the autonomy level says, because an agent with `write_file` and a shell is an attack surface regardless of how well-calibrated its freedom is.

---

*Factory defaults and case-study data in this post are from real sessions with the companion codebase (Go 1.23+); the AEMM scoring function is presented explicitly as design, not shipped code.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-07
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-autonomy.html
Attribution: please link the canonical URL when citing or quoting this post.
