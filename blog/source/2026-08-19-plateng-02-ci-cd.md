# CI/CD: The Deployment Pipeline

*CI/CD is the assembly line of modern software — the automated path from a developer's commit to running production code. It's the practice that turned releases from rare, terrifying events into routine, boring ones, and "boring releases" is one of the highest compliments in software. It's also the first capability any platform provides.*

The foundational DevOps practice — and the first thing an internal developer platform automates — is **CI/CD**: the automated pipeline that takes code from commit to production. It's what makes frequent, reliable releases possible, replacing manual, error-prone deployment with an automated assembly line. This post covers the three C's (continuous integration, delivery, and deployment — which are distinct), what a pipeline actually does, and the practices that make it work. It's the backbone of shipping software, and everything else in the platform builds on it.

## The three C's (they're different)

"CI/CD" bundles three related-but-distinct practices, and knowing the difference matters:

- **Continuous Integration (CI)** — developers *integrate* their code into a shared main branch frequently (many times a day), and each integration is automatically *built and tested*. The point is to catch integration problems and bugs *immediately*, while they're small, rather than in a painful "merge hell" at the end. CI answers: "does the code build and pass tests on every change?"
- **Continuous Delivery (CD)** — every change that passes CI is automatically prepared for release — built, tested, and packaged so it's *ready to deploy* to production at any time, with the actual deploy being a *manual* decision (a button press). CD answers: "is every change always in a deployable state?"
- **Continuous Deployment (also CD)** — goes one step further: every change that passes the pipeline is *automatically deployed* to production, no manual gate. CD (deployment) answers: "does every passing change ship to production automatically?"

The distinction between the two CDs matters: **continuous delivery** keeps you always *ready* to deploy (human decides when); **continuous deployment** actually deploys *automatically*. Most organizations do continuous *delivery* (automated up to a manual production gate) and adopt continuous *deployment* (fully automatic) as their testing and confidence mature. The progression CI → continuous delivery → continuous deployment is a maturity ladder, each step requiring more automated confidence than the last.

## What the pipeline does

A **CI/CD pipeline** is the automated sequence a code change flows through from commit to production. A typical pipeline:

```text
commit → build → test → (security/quality scans) → package → deploy to staging
       → integration tests → [gate] → deploy to production → verify
```

- **Trigger** — a commit/push (or merge/PR) automatically starts the pipeline. No manual kickoff.
- **Build** — compile the code and produce an artifact (a binary, a container image).
- **Test** — run the automated tests (unit, then integration), *failing the pipeline* if any fail. This is CI's core: no change proceeds without passing tests.
- **Scan** — quality and security checks (linting, vulnerability scanning, the DevSecOps concerns) run in the pipeline.
- **Package** — produce the deployable artifact (typically a versioned container image pushed to a registry).
- **Deploy** — release to environments (often staging first, then production), possibly with a manual gate before production (delivery) or automatically (deployment).
- **Verify** — confirm the deployment is healthy (smoke tests, health checks), and be ready to roll back if not.

The pipeline is *automated* end to end — that's the whole point. A change flows from commit to (at least) staging without human steps, so releasing is fast, consistent, and repeatable rather than a manual ritual someone might get wrong. The pipeline is codified (as configuration in the repo — pipeline-as-code), so it's version-controlled and reviewable like any code.

## Why CI/CD matters: boring releases

The transformation CI/CD delivers is making releases *boring* — and in software, boring is the highest praise. Before CI/CD, deployments were rare, manual, high-stakes events: batched-up changes, a nervous release night, a runbook of manual steps, and a real chance of failure. CI/CD inverts this:

- **Frequent, small releases.** Because deploying is automated and cheap, you release *often* in *small* increments. Small changes are less risky (less to go wrong, easier to diagnose) than big batched ones — a counterintuitive but well-established truth: deploying more often is *safer*, not riskier, because each deploy carries less change.
- **Fast feedback.** CI catches bugs on every commit, so problems surface immediately while the context is fresh and the fix is cheap — versus discovering them weeks later in a big integration.
- **Consistency and repeatability.** The automated pipeline does the same steps every time, eliminating the human error of manual deployment. A release is a routine, reproducible process, not a bespoke event.
- **Fast recovery.** With automated pipelines, rolling back or shipping a fix is fast (just another pipeline run), so when something does break, you recover quickly — which matters more than never breaking.

This is why the DORA research (the metrics post) found that elite teams deploy *frequently* with *low* failure rates and *fast* recovery — CI/CD is what enables all of that. "Boring releases" — frequent, small, automated, low-drama — is the goal, and CI/CD is how you get there.

## Practices that make it work

CI/CD done well relies on a few disciplines:

- **Trunk-based development / frequent integration** — integrate to main frequently in small changes (CI's premise), rather than long-lived branches that cause painful merges. Small, frequent integrations are the foundation.
- **Comprehensive automated tests** — the pipeline's confidence *is* your test suite; you can only automate deployment as far as your tests let you trust it. Good tests are the prerequisite for CD.
- **Fast pipelines** — a slow pipeline discourages frequent integration and delays feedback; keep it fast (parallelize, cache, `cargo check`-style quick checks) so developers get results quickly.
- **Deploy the same artifact through environments** — build once, promote the *same* artifact through staging to production (rather than rebuilding per environment), so what you tested is what you ship.
- **Automated rollback / progressive delivery** — be able to roll back fast, and use techniques like canary or blue-green deploys to release gradually and safely (reducing blast radius).
- **Pipeline as code** — define the pipeline in version-controlled config, reviewed and evolved like application code.

CI/CD is the deployment pipeline at the heart of DevOps and the first capability a platform provides to developers — turning shipping from a risky manual event into a fast, automated, boring routine. The next post covers automating the *infrastructure* the pipeline deploys to: infrastructure as code.

## Key takeaways

- CI/CD bundles three distinct practices: continuous integration (integrate frequently to main, auto build+test every change, catch problems immediately), continuous delivery (every passing change is kept deployable, human decides when to ship), and continuous deployment (every passing change ships to production automatically) — a maturity ladder needing more automated confidence at each step.
- A CI/CD pipeline is the automated sequence from commit to production — trigger → build → test (fail on failure) → scan → package → deploy (staging, then production, gated or automatic) → verify — codified as pipeline-as-code, run end to end without manual steps.
- CI/CD's value is making releases boring: frequent small releases (safer than big batched ones because each carries less change), fast feedback (bugs caught per commit), consistency/repeatability (no manual-deploy human error), and fast recovery (rollback/fix is just another pipeline run).
- This is why DORA's elite teams deploy frequently with low failure rates and fast recovery — CI/CD enables all of it; deploying more often is safer, not riskier.
- Do it well with trunk-based/frequent integration, comprehensive automated tests (the pipeline's confidence is your test suite), fast pipelines, build-once-promote-the-same-artifact, automated rollback/progressive delivery, and pipeline-as-code — it's the first capability a platform provides.

## Further reading

- [From DevOps to platform engineering (previous post)](/blog/posts/plateng-01-devops-to-platform-engineering.html)
- [DORA — DevOps research and metrics](https://dora.dev/)
- [DevSecOps series — security in the pipeline](/blog/series/devsecops/)
