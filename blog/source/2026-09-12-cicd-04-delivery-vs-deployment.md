# Continuous Delivery vs. Continuous Deployment

*The two D's in CD/CD get used interchangeably, but they name genuinely different practices with different risk profiles and different prerequisites. Getting the distinction right — and knowing which one your system is actually ready for — is the difference between a mature delivery pipeline and a dangerous one. This post draws the line clearly and covers what it takes to cross it.*

The first post defined the difference in one sentence: Continuous Delivery keeps a human approval before production; Continuous Deployment removes it. This post goes deeper — what each really requires, how environments and promotion work, and how to decide which is right for your system. The distinction is small in words and large in consequences.

## The releasable artifact and environment promotion

Both practices rest on the same foundation from post 3: **one artifact, built once, promoted unchanged** through a sequence of environments. A typical promotion path:

**build → test environment → staging → production**

The same immutable artifact moves rightward, gated at each step, with environment-specific *configuration* injected at deploy time. Each environment is progressively more production-like: test environments verify functionality, staging mirrors production closely (same infrastructure shape, similar data) to catch environment-specific issues before they reach users.

The word **promotion** captures the mental model: the artifact is *promoted* from one environment to the next only after proving itself in the current one. Nothing is rebuilt; the thing that passed staging is byte-identical to the thing that goes to production. This promotion chain is the spine both delivery models share — they differ only in what happens at the final gate.

## Continuous Delivery: always releasable, human decides when

**Continuous Delivery** means your software is *always in a releasable state* — every change that passes the pipeline is automatically built, tested, and deployed up to a production-ready staging environment, so that **releasing to production is a single-click business decision.**

The key properties:
- The pipeline is fully automated *up to* production.
- Production release requires a **human approval** — a click, not an engineering effort.
- Because the software is always releasable, that human decision is about *timing and business*, not technical readiness: release now, or during a maintenance window, or after marketing is ready, or hold for a coordinated launch.

Continuous Delivery is the right default for most organizations. It captures nearly all the benefit — small changes, always-releasable software, fast reliable path to production — while keeping a human judgment at the production boundary. That human gate matters when releases have business timing constraints, regulatory sign-off, or coordination needs. The discipline is that the gate is about *when*, never about *whether it works* — the pipeline already proved that.

## Continuous Deployment: no gate, every change ships

**Continuous Deployment** removes the final human gate: every change that passes the entire pipeline is *automatically deployed to production*. Commit, pass, live — no click.

This sounds reckless and can be, but for teams that are ready it's the logical endpoint: if the pipeline is trustworthy enough that a human always clicks "approve" anyway, the click is just latency. Removing it deploys changes to users in minutes, tightens the feedback loop to its maximum, and forces the pipeline's quality to be genuinely excellent (because nothing else stands between a commit and production).

But Continuous Deployment demands far more of everything around it:
- **Exceptional automated testing** — the pipeline is the *only* safety net; there's no human to catch what tests miss.
- **Strong deployment strategies** — canary/progressive rollout (next post) so a bad change hits few users before automated checks catch it.
- **Robust monitoring and automated rollback** — production problems must be detected and reverted automatically and fast, because a human isn't gating releases.
- **Feature flags** — to decouple *deploying* code from *releasing* features, so incomplete work can ship dark.

Continuous Deployment isn't "less careful" than Delivery — it's *more* automated care, moving the rigor a human approver provided into the pipeline and observability. You don't remove the gate by being cavalier; you remove it by making everything around it strong enough that the gate was redundant.

## Choosing between them

The decision isn't about ambition or maturity signaling — it's about fit:

- **Choose Continuous Delivery** when releases have business-timing needs, regulatory or compliance sign-off, coordination across teams, or when your testing/monitoring isn't yet strong enough to trust unattended production releases. This is most teams, and it's not a compromise — it's a sound choice.
- **Choose Continuous Deployment** when your test suite and observability are genuinely excellent, changes are small and independent, and the value of maximum-speed feedback outweighs the human check — often internal tools, web services with strong rollout/rollback, and mature teams.

It's also not all-or-nothing per organization: you might run Continuous Deployment for a low-risk internal service and Continuous Delivery for a customer-facing payment system. Match the model to the *risk and constraints of each system*, not to a company-wide badge.

The honest guidance: **most teams should aim for Continuous Delivery first** — always-releasable software with a human production gate captures the overwhelming majority of the value at a fraction of the risk. Continuous Deployment is a further step to take *deliberately*, once the testing, rollout, and monitoring foundations genuinely support removing the human. Reaching "always releasable" is the milestone that matters; removing the final click is an optimization on top of it.

## Key takeaways

- Both models share one foundation: **one immutable artifact, built once, promoted unchanged** through progressively production-like environments (test → staging → production), with config injected at deploy time.
- **Continuous Delivery** = automated pipeline up to production + a **human approval** at the production gate, where the decision is about *timing/business* (the pipeline already proved it works), so software is *always releasable* with a single click.
- **Continuous Deployment** = *no* human gate; every passing change auto-ships — which demands *more* automated care: exceptional tests, progressive rollout, automated monitoring/rollback, and feature flags (the rigor a human provided, moved into the pipeline).
- Choose by **fit, not ambition**: Delivery when there are business/regulatory/coordination constraints or testing isn't yet bulletproof (most teams); Deployment when tests + observability are excellent and max-speed feedback is worth it — and it can be per-system, not company-wide.
- **Aim for Continuous Delivery first** — "always releasable" is the milestone that captures most of the value; removing the final click is a deliberate optimization once the foundations support it.

## Further reading

- [Martin Fowler — Continuous Delivery](https://martinfowler.com/bliki/ContinuousDelivery.html)
- [DORA — DevOps Research and Assessment](https://dora.dev/)
