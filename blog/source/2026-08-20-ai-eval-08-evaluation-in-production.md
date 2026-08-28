# Evaluation in Production

*Offline evaluation tells you whether a change is promising; production tells you whether it actually works. Once your system is serving real users, evaluation becomes continuous: online experiments, guardrail metrics, drift monitoring, and gating deploys on eval scores. This closing post moves evaluation from the lab into the running system and ties the whole series into a working loop.*

Everything so far has been mostly offline: fixed datasets, controlled runs, scores you compare before shipping. But a fixed dataset is a snapshot, and reality moves. Real inputs drift, models get updated, and the only place you learn what *actually* happens is production. This final post covers evaluating a live system — and how offline and online evaluation combine into one continuous discipline.

## Why offline isn't enough

Offline evaluation has an unavoidable gap: your eval set is a *model* of reality, and models drift out of date. Users ask things you never anticipated; the input distribution shifts as your product and audience change; an underlying model you call gets silently updated by the provider. A system that scored beautifully on last quarter's eval set can quietly degrade on this quarter's traffic without a single line of your code changing.

Production evaluation closes this gap by measuring the real thing: actual outputs, on actual inputs, judged by actual outcomes. It's the other half of the loop introduced in post 1 — offline to *develop* cheaply and safely, online to *confirm* against reality.

## Online experiments

The core tool for validating a change in production is the controlled experiment. Instead of trusting an offline win, you ship the change to a fraction of traffic and measure:

- **A/B testing.** Route some users to the new variant (B) and some to the current one (A), and compare outcomes on real metrics. This is the highest-fidelity evaluation there is — real users, real behavior — and the only way to know a change's true effect. It requires enough traffic and time for statistical significance, and discipline to change one thing at a time.
- **Canary / gradual rollout.** Release to 1%, then 5%, then more, watching metrics at each step and halting if anything degrades. This bounds the blast radius of a bad change — a poor variant reaches few users before you catch it.
- **Shadow evaluation.** Run the new variant *alongside* production on the same live inputs without showing users its output, then compare. You get real-input behavior with zero user risk — useful for scoring a candidate before you dare route real traffic to it.

The through-line: production is where you validate, but you validate *carefully*, limiting exposure until the evidence is in.

## What to measure in production

Production metrics are broader than offline quality scores because you can observe consequences you can't simulate:

- **Implicit user signals.** Real behavior reveals quality: did the user accept the suggestion, copy the answer, thumbs-up, retry, rephrase, or abandon? A high retry or abandonment rate is a quality alarm no offline metric would show. These signals are noisy but abundant and unfakeable.
- **Explicit feedback.** Thumbs up/down, ratings, reports. Sparse (most users don't rate) but high-signal, and a source of new eval cases.
- **Guardrail metrics.** Things that must *not* regress even if your target metric improves: latency, cost per request, error rate, safety violations, refusal rate. A change that improves answer quality but doubles latency or cost may be a net loss; guardrails catch the trade-offs a single quality score hides.
- **Online LLM-as-a-judge.** Sample a slice of live traffic and run a judge (post 3) over it continuously, producing an ongoing quality score on *real* inputs — the offline judge, pointed at production.

## Monitoring for drift

Beyond experiments, a production system needs *continuous* monitoring, because degradation often arrives without any deploy of yours:

- **Input drift.** The distribution of what users send shifts over time. Track it, because a system tuned for one distribution silently degrades as inputs move away from it.
- **Output drift.** Watch aggregate properties of your outputs — average length, refusal rate, sentiment, format-validity rate. A sudden shift often signals an upstream change (a provider updated the model behind their API) before users complain.
- **Feedback trends.** A slow decline in thumbs-up or a rise in retries is an early-warning system.

Monitoring turns evaluation from a pre-ship event into an always-on sensor, so you learn about degradation from your dashboards rather than from angry users.

## Gating deploys with evals

The bridge back to offline is **CI gating**: run your eval harness (post 4) automatically on every change to prompts, models, or system code, and *block* the deploy if the score drops below a threshold or regresses against baseline. This treats evals exactly like tests — a failing eval stops the release. It's what makes fast iteration safe: you can change prompts and swap models freely because the gate catches regressions before they reach anyone. Pair it with the online tools above and you get defense in depth: CI gating stops known regressions pre-merge, canary rollouts limit unknown ones, and monitoring catches the drift that no deploy caused.

## The complete loop

Assembled, the whole series describes one continuous cycle:

1. **Develop offline** — define "good" (post 1), pick metrics (post 2), maybe an LLM judge (post 3), against a real dataset in a harness (post 4), aware of what benchmarks do and don't tell you (post 5) and how contamination and Goodhart's law corrupt scores (post 6).
2. **Gate on the way out** — CI runs the harness and blocks regressions.
3. **Validate online** — canary or A/B the change on real traffic, watching quality and guardrail metrics.
4. **Monitor continuously** — drift, feedback, and a live judge keep watch.
5. **Feed production back into offline** — every real failure, every drifted input, every low-rated output becomes a new eval case, so your dataset keeps pace with reality and your golden set (validated by humans, post 7) stays honest.

That last arrow is what makes the loop a loop: production is not just where you deploy, it's your richest source of eval data. The systems that stay good are the ones where this cycle spins continuously — offline speed and online truth feeding each other — rather than teams that evaluate once, ship, and hope. Evaluation isn't a phase you finish. It's the discipline that, run forever, keeps an AI system trustworthy as the model, the users, and the world all keep changing.

## Key takeaways

- **Offline evaluation is a snapshot that drifts** — input distributions shift, providers update models, and a system can degrade in production with no code change — so online evaluation is required to measure the real thing.
- Validate changes with **controlled online experiments**: A/B tests (highest fidelity), canary/gradual rollouts (bounded blast radius), and shadow evaluation (real inputs, zero user risk).
- Measure more in production than offline: **implicit signals** (retries, abandonment, acceptance), explicit feedback, **guardrail metrics** (latency, cost, safety, error rate) that must not regress, and an **online LLM-judge** on sampled traffic.
- **Monitor continuously for drift** — input, output (length/refusal/format), and feedback trends — so you catch degradation (often from silent upstream model changes) from dashboards, not from users.
- **Gate deploys on eval scores in CI** (treat a failing eval like a failing test) for defense in depth with canaries and monitoring, and **feed every production failure back into the offline eval set** — that feedback arrow is what keeps the whole loop honest as reality changes.

## Further reading

- [Holistic Evaluation of Language Models (HELM) — Liang et al., arXiv:2211.09110](https://arxiv.org/abs/2211.09110)
- [EleutherAI — lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
