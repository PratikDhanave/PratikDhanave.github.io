# Infrastructure as Code

*Clicking through a cloud console to set up infrastructure is fast, fun, and a disaster you'll regret — because nobody can reproduce it, review it, or remember what you did. Infrastructure as code turns your servers, networks, and databases into version-controlled, reviewable, reproducible code. It's the practice that makes infrastructure an engineering discipline instead of an artisanal craft.*

The CI/CD pipeline deploys to *infrastructure* — and how you manage that infrastructure is the next foundational practice: **Infrastructure as Code (IaC)**. Instead of manually configuring servers, networks, and cloud resources by clicking consoles or running ad-hoc commands, you *define* infrastructure in version-controlled code and apply it automatically. This makes infrastructure reproducible, reviewable, and automatable — and it's what a platform uses to provision environments for developers. This post covers what IaC is, declarative vs imperative, key concepts (idempotency, state, drift), and why it matters.

## The problem: manual infrastructure

The old way — **click-ops** — is setting up infrastructure by hand: clicking through a cloud console, SSHing into servers to configure them, running one-off commands. It works for a moment and fails as a practice, because manual infrastructure is:

- **Not reproducible** — you can't reliably recreate it. Setting up an identical staging environment means clicking through the same steps again and hoping you remember them all. Environments drift apart ("works in staging, breaks in prod").
- **Not reviewable or documented** — there's no record of *what* was configured or *why*; the knowledge lives in someone's head or a stale wiki. No code review, no audit trail.
- **Error-prone and slow** — manual steps get done inconsistently, forgotten, or fat-fingered, and doing them by hand is slow.
- **Not automatable** — a pipeline can't click a console; manual infra can't be part of an automated workflow.

**Infrastructure as Code** fixes all of this by making infrastructure *code*: you write the desired infrastructure in files, version-control them, and apply them with tooling. Infrastructure becomes reproducible (re-apply the code to get an identical environment), reviewable (it's code, in git, code-reviewed), documented (the code *is* the documentation of what exists), and automatable (the pipeline applies it). This is the shift from infrastructure as artisanal craft to infrastructure as engineering.

## Declarative vs imperative

There are two styles of IaC, and the declarative style dominates for good reason:

- **Imperative** — you specify the *steps* to create infrastructure ("create this server, then attach this disk, then configure this network"). You describe *how*. Scripts (shell, some tools) are imperative.
- **Declarative** — you specify the *desired end state* ("I want three servers of this type, this network, this database"), and the tool figures out *how* to get there from the current state. You describe *what*, not how.

**Declarative IaC** (the dominant approach, used by Terraform, and Kubernetes manifests, CloudFormation, and others) is preferred because you describe the *goal* and the tool computes the actions:

```text
Declarative (Terraform-style): "I want this VPC, these 3 instances, this database"
   → tool compares desired state to actual state → creates/updates/deletes to match
```

The advantage: you don't have to script the steps or handle "does it already exist?" logic — you declare what you want, and the tool reconciles reality to match. This makes the code simpler (state, not procedure), naturally idempotent (below), and safe to re-run. The declarative model — desired state, tool reconciles — is central to modern infrastructure (and to GitOps, the next post). Some tools are imperative or hybrid, but declarative is the mainstream because "describe the destination, let the tool find the path" scales far better than scripting every step.

## Key concepts: idempotency, state, drift

Three concepts define how IaC works in practice:

- **Idempotency** — applying the same IaC repeatedly produces the same result. Running your Terraform twice doesn't create duplicate resources; it sees the desired state already matches and does nothing (or fixes any difference). This is what makes IaC safe to run in automation — you can re-apply anytime, and it converges to the declared state rather than piling up changes. Declarative IaC is naturally idempotent.
- **State** — declarative tools track the *current state* of your infrastructure (what exists) so they can compute the difference from the *desired state* (your code) and make only the necessary changes. Terraform, for example, keeps a state file mapping your code to real resources. Managing this state (storing it safely, remotely, with locking so two people don't apply at once) is a real operational concern of IaC.
- **Drift** — when the real infrastructure diverges from the code, usually because someone made a manual change (click-ops) outside the IaC. Drift is dangerous: your code no longer reflects reality, so the next apply may undo the manual change or behave unexpectedly. The discipline is: **all changes go through the code** — no manual changes — so the code stays the single source of truth and drift doesn't accumulate. IaC tools can *detect* drift (compare actual vs declared), and GitOps (next post) actively *corrects* it.

These three — idempotency (safe re-apply), state (track reality to compute changes), drift (reality diverging from code, prevented by all-changes-through-code) — are the mechanics you must understand to use IaC well. The overarching rule: **the code is the source of truth; change infrastructure by changing the code, never by hand.**

## IaC in the pipeline and platform

IaC connects to the rest of the platform:

- **In the CI/CD pipeline** — infrastructure changes go through a pipeline like application code: propose a change (a pull request to the IaC), review it, see a *plan* of what will change (declarative tools preview the diff before applying — a crucial safety step), and apply it automatically on merge. Infrastructure changes become reviewed, planned, automated deployments — just like code.
- **In the platform** — the platform team uses IaC to define and provision the infrastructure developers get (environments, clusters, databases), so developers receive reproducible, standardized infrastructure without hand-building it. IaC is how the platform delivers infrastructure as a self-service, consistent capability.
- **With modules/reuse** — IaC is written in reusable modules, so common infrastructure patterns (a standard service setup, a standard database) are defined once and reused, which is exactly the "golden path" idea (a later post) applied to infrastructure.

Infrastructure as code turns infrastructure into a version-controlled, reviewable, reproducible, automatable engineering artifact — the foundation the platform provisions and the pipeline deploys to. The next post covers the modern evolution of applying IaC: GitOps, where git becomes the operational source of truth and the system continuously reconciles reality to match it.

## Key takeaways

- Manual "click-ops" infrastructure is not reproducible, reviewable, documented, or automatable, and drifts between environments; Infrastructure as Code fixes this by defining infrastructure in version-controlled code that's reproducible (re-apply for identical environments), reviewable (code-reviewed in git), self-documenting, and automatable.
- Declarative IaC (Terraform, Kubernetes manifests, CloudFormation) — describe the desired end state, and the tool reconciles reality to match — dominates over imperative (scripting the steps) because you declare *what* not *how*, giving simpler, idempotent, re-runnable code.
- Three key concepts: idempotency (re-applying converges to the declared state, safe in automation), state (tools track current reality to compute the minimal diff from desired state — and managing that state safely matters), and drift (reality diverging from code via manual changes — prevented by routing all changes through the code).
- The governing rule: the code is the single source of truth — change infrastructure by changing the code, never by hand — and declarative tools let you preview the plan (the diff) before applying, a crucial safety step.
- IaC flows through the pipeline (propose → review → plan → auto-apply, like application code), is how the platform provisions reproducible infrastructure for developers self-service, and is written in reusable modules (golden paths for infra) — the foundation the pipeline deploys to and GitOps (next) continuously reconciles.

## Further reading

- [CI/CD: the deployment pipeline (previous post)](/blog/posts/plateng-02-ci-cd.html)
- [Terraform documentation (HashiCorp)](https://developer.hashicorp.com/terraform)
- [Distributed Systems / cloud fundamentals — what IaC provisions](/blog/series/computer-networking-for-backend-engineers/)
