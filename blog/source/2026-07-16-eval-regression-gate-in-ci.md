# An Eval Regression Gate in CI
*Treat agent output quality like a test. A baseline file plus a gate that fails the build on regression turns "the agents got worse" into a red X.*

Agent systems rot quietly. Nobody ships a commit titled "make the triage agent 12% worse at routing." It happens sideways: someone tightens a prompt to fix one edge case and breaks three others, a provider bumps a model version under you, a refactor reorders the tools a router sees and it starts picking the wrong one. None of that trips a unit test. The code still compiles, the endpoints still return `200`, the JSON still parses. You find out when a user does — when an incident gets routed to the wrong on-call, or the diagnosis is confidently wrong.

I hit exactly this on a governed multi-agent system I built for operational incident triage (Microsoft Agent Framework, Python). Multiple agents cooperate to classify an incoming incident, route it to the right responder, and propose a diagnosis. Every one of those is a *quality* judgment, not a boolean. So I gave quality the same standing as any other test: a committed baseline and a gate that fails the build when current behavior regresses against it.

## Quality is a measurement, not an assertion

The instinct is to write `assert route == "database-team"` and call it a test. That instinct is wrong for agent output, and pretending otherwise is how you end up with a flaky suite everyone learns to re-run until it's green.

An eval is a measurement against a baseline. You define a set of scenarios — a synthetic incident, the expected route, the expected diagnosis class — and you *score* the current system's output against expected outcomes. The score is a number: fraction of scenarios routed correctly, fraction diagnosed correctly, maybe a rubric score from an LLM judge for free-text quality. The gate isn't "did it match exactly." The gate is "is the current score at least as good as the committed baseline, within a threshold."

That distinction matters because it tells you what the gate protects against (regression) and what it deliberately doesn't do (freeze behavior forever). A unit test says *this is correct*. An eval gate says *this is not worse than what we agreed was good enough*.

## The baseline is a file you commit

The whole scheme hangs on one artifact: `baseline.json`, checked into the repo next to the eval scenarios. It records the scores the suite is expected to meet — the contract.

```json
{
  "suite": "triage-eval",
  "generated_at": "2026-07-10",
  "thresholds": {
    "routing_accuracy": 0.92,
    "diagnosis_accuracy": 0.85,
    "judge_score_min": 4.2
  },
  "scenarios": 40
}
```

Because it's a committed file, three good things follow. It's *reviewable* — a change to it shows up as a diff in the pull request. It's *versioned* — you can see when and why the bar moved via `git log`. And it's *shared* — CI and every developer's `make eval` read the same numbers, so "works on my machine" stops being a quality argument.

## The gate: run, score, compare, block

A single make target ties it together. It runs the eval suite, scores the run, compares against the baseline, and exits non-zero on regression. CI runs that same target alongside the coverage gate, so a pull request goes red for *either* a code-coverage drop *or* a quality drop — quality is now a first-class CI citizen, not a vibe someone checks manually.

```
        ┌──────────────┐
        │  scenarios   │  (committed: incident → expected
        │  (test set)  │   route + diagnosis)
        └──────┬───────┘
               │  make eval
               ▼
        ┌──────────────┐
        │   run agents │  offline path by default;
        │   score each │  live-model path only when needed
        └──────┬───────┘
               │  scores: {routing: 0.90, diagnosis: 0.86, ...}
               ▼
        ┌──────────────┐        current < baseline
        │  compare vs  │──────────────────────────► ✗ FAIL
        │ baseline.json│   (regression → exit 1, CI red)
        └──────┬───────┘
               │  current >= baseline
               ▼
             ✓ PASS ─────────► merge allowed
```

The comparison itself is boring on purpose — boring is what you want in a gate:

```python
for metric, floor in baseline["thresholds"].items():
    if scores[metric] < floor - TOLERANCE:
        fail(f"regression: {metric} {scores[metric]:.3f} < {floor:.3f}")
```

`TOLERANCE` absorbs the small nondeterminism you can't design away. It should be tight — a few points — not a barn door. If you need a wide tolerance to stay green, your eval is measuring noise, not quality.

## Keep it fast: offline by default, live when it counts

An eval gate that takes fifteen minutes and burns tokens on every push gets disabled within a week. The fix is to split the path.

Most of the suite runs *offline and deterministic*: stubbed or recorded model responses, fixed seeds, so the gate exercises your routing logic, tool selection, parsing, and scoring plumbing for free and in seconds. This is the part that catches the "refactor broke routing" and "prompt template regressed parsing" classes of bug, which are the common ones.

Reserve *live-model* eval runs for the scenarios that genuinely need a model in the loop — the free-text diagnosis quality a judge has to grade. Those are slower, cost money, and are gated behind an explicit flag and credentials, so they don't run on every trivial push but do run before a release. The offline path keeps the feedback loop tight; the live path keeps it honest. Skipped live evals in a normal CI run are expected, not a failure.

## Moving the bar on purpose

Here's the part people get wrong: they treat a failing eval as always-bad and reflexively widen the tolerance until green. Sometimes the system genuinely got *better* — you improved a prompt, added a tool, and routing accuracy climbed. The gate should still make you do something deliberate: update `baseline.json` in the same pull request, as a reviewed diff, so the improvement is recorded and becomes the new floor.

That's the whole discipline. You never edit the baseline to make red go away; you edit it to ratchet the bar *up* when you've earned it. "We improved the prompt" stops being a Slack message and becomes a line in a diff a reviewer approved. A regression and an improvement look different in the PR — one is an unexplained score drop, the other is an intentional baseline bump with a commit message.

## Why it matters

Testing determinism is easy — you assert and you're done. Testing quality is different: it needs a baseline you agree to move on purpose. Without that, agent quality degrades on a timescale slower than any single PR review, so no individual reviewer ever sees it happen, and it surfaces in production as trust erosion you can't easily attribute to any one change.

A committed baseline plus a gate collapses that whole failure mode into a single red X on a pull request. Regressions become build failures. Improvements become reviewable diffs. And "the agents got worse" stops being something a user tells you and becomes something CI told you first — before you shipped.
