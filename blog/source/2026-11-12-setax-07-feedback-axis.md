# The Feedback Axis: Every Self-Evolution Failure Is a Feedback Failure

*Walk back through the first six posts and a pattern repeats with suspicious regularity: the artifact loop is only as good as its evaluator, consensus training launders whatever bias the vote shares, self-play drifts without an anchor, test-time adaptation mis-fires when its proxy objective lies. Different loci, same lesson. This post makes the lesson the subject: feedback is the taxonomy's second axis, failure modes sort by feedback type rather than by locus — and the engineering discipline of self-evolving systems is mostly the engineering of feedback.*

## The five feedback types

Orthogonal to *what evolves* is *what signal drives the evolving* — and the five types form a strength ladder that posts 2–6 have been climbing up and down all series:

- **Formal verification** — a checker that cannot be fooled, only mis-aimed. The residual risk relocates entirely into the *specification*: optimize a correct proof of the wrong theorem and the feedback was perfect while the question was wrong.
- **Mechanical measurement** — execution, timing, tests. Honest about a narrow world; fails by noise (lucky candidates win) and by narrowness (benchmark-true, production-false).
- **Environment outcome** — the task actually succeeded, the user actually accepted, the system actually stayed up. The most *meaningful* signal and the worst-behaved: delayed, noisy, confounded, and expensive, with an attribution problem (which of the forty steps caused the outcome?) that grows with agent complexity.
- **Learned/judged evaluation** — an LLM judge, a reward model, a learned scorer. Infinitely available and always slightly wrong; its biases (length, confidence, format, sycophancy toward the generator's style) are *stable*, so optimization pressure finds and exploits them with certainty, not chance.
- **Self-consistency** — agreement with oneself: majority vote, internal confidence, round-trip checks. The cheapest signal and the only one with *no external referent at all* — it detects incoherence, never shared error, which is why post 5 called consensus training a sharpener rather than a teacher.

Two properties decide everything about using them. **Exploitability under pressure**: [Goodhart's law](https://en.wikipedia.org/wiki/Goodhart%27s_law) — a measure under optimization stops measuring — binds each type at a different pressure threshold, highest for formal verification, lowest for self-consistency; post 3's "pressure budget" is this axis applied to artifact search, and post 5's anchor discipline is the same budget applied to weights. **Cost and latency**: the strong signals are scarce or slow, the weak ones instant and free — so every real system faces a feedback *economics* problem, not just a feedback *quality* problem.

## The universal architecture: feedback cascades

Every mature self-evolving system converges on the same answer to that economics problem: a **cascade** — cheap, weak, exploitable signals filter a large candidate flow; expensive, strong, trustworthy signals gate what survives. Self-consistency prunes thousands of samples; a judge ranks hundreds; tests verify dozens; the environment (or a human) blesses the few that matter. The design rules of a sound cascade are exactly the series' accumulated lessons restated: *strength must be monotone* — each stage's verdict is checked by a stronger stage, never a weaker one, and anything consequential (a weight update, a deployed artifact, a persistent memory) must trace to the strongest affordable signal, not to a judge's opinion laundered through volume. *Pressure concentrates on the cheap stages* — that's their job; they're disposable filters, and their gaming is contained so long as a stronger stage stands behind them. *The cascade is itself a measured system* — stage-to-stage agreement rates are the drift alarm: when judge scores rise but test pass-rates don't, when self-consistency tightens but environment outcomes flatten, the divergence between adjacent signals is the earliest observable symptom that some stage is being optimized against. A cascade that doesn't monitor its own inter-stage agreement is a cascade that will silently rot.

And one signal type deserves its explicit seat rather than an afterthought: **human feedback** enters the cascade not as another scalar but as the *calibrator* — the periodic spot-check that re-anchors judges, re-validates test suites, and audits environment attributions. The design question for humans-in-the-loop is placement: at the top of the cascade (gating what ships) they're a bottleneck; as random auditors of every stage's agreement they're a multiplier.

The takeaway: feedback is the taxonomy's second axis, with five types on a strength ladder — **formal, mechanical, environmental, judged, self-consistent** — each failing in its own signature way, all governed by Goodhart at type-specific pressure thresholds. Real systems run **cascades**: weak cheap signals filter volume, strong scarce signals gate consequences, inter-stage agreement is monitored as the drift alarm, and humans calibrate rather than bottleneck. Design the cascade before the loop — because every failure story in this series, from gamed judges to private self-play languages, is a cascade that was missing a stage or wasn't watching its seams.

## Key takeaways

- The strength ladder: **formal → mechanical → environmental → judged → self-consistent**, ordered by exploitability under optimization pressure — and inversely by cost and availability.
- Signature failures per type: mis-specification, benchmark narrowness, attribution confusion, stable exploitable bias, shared-error blindness — recognize the feedback type and you can predict the failure before running the loop.
- The **cascade** is the universal architecture: cheap filters → strong gates, with consequence-bearing changes always traced to the strongest affordable signal.
- **Inter-stage agreement is the drift alarm** — adjacent signals diverging (judge up, tests flat) is the earliest sign a stage is being gamed; humans serve best as cascade calibrators, not cascade bottlenecks.

## Further reading

- [Goodhart's law — why measures die under optimization](https://en.wikipedia.org/wiki/Goodhart%27s_law)
- [Feedback — the control-theoretic root of the whole axis](https://en.wikipedia.org/wiki/Feedback)
