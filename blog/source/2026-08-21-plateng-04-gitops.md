# GitOps and Declarative Delivery

*GitOps takes one idea to its logical conclusion: if your infrastructure and deployments are declarative code, then git should be the single source of truth, and a machine — not a human running commands — should continuously make reality match git. It turns "deploy" from an action you perform into a state you declare, and it's how modern platforms run.*

Infrastructure as code made infrastructure declarative and version-controlled. **GitOps** takes the next step: make **git the single source of truth** for the desired state of your systems, and have an automated agent *continuously reconcile* the running system to match what's in git. Instead of pushing changes to production, you commit the desired state to git and the system pulls and applies it. This post covers the GitOps model, its principles, pull-based reconciliation, and why it's become the standard way platforms deploy — especially on Kubernetes.

## The core idea: git as the source of truth

GitOps rests on a simple, powerful premise: **the desired state of your entire system — infrastructure and applications — lives in git, declaratively, and git is the single source of truth.** Everything you want running is described in a git repository (as declarative IaC / Kubernetes manifests / config), and the *actual* running system is continuously made to match that repository. This means:

- **To change the system, you change git.** You don't run deploy commands against production; you commit the desired change to git (via a pull request), and the change flows automatically from there. A deploy is a git commit.
- **Git is the record of what should be running.** Want to know the exact desired state of production? Look at git. It's the authoritative, versioned, auditable description of the whole system.
- **The running system converges to git.** An automated agent continuously compares the actual state to git and reconciles any difference, so reality tracks the repository.

This reframes deployment fundamentally: from an *imperative action* ("push this out") to a *declarative state* ("git says the system should be this; make it so"). The system is defined by git, and keeping it that way is automated. This is the declarative model from the IaC post, extended to the *operational* running of the whole system.

## The GitOps principles

GitOps is often summarized by a few principles (as articulated by the OpenGitOps project):

- **Declarative** — the entire desired system state is expressed declaratively (what, not how) — the IaC-post foundation.
- **Versioned and immutable** — the desired state is stored in git, versioned and immutable, so you have a complete history and can roll back to any previous state by reverting.
- **Pulled automatically** — software agents automatically *pull* the desired state from git (rather than changes being pushed to the cluster — see below).
- **Continuously reconciled** — agents continuously observe the actual state and reconcile it to the desired state, correcting any divergence.

These principles combine into a system where git is authoritative, changes are versioned and revertible, and an automated agent keeps reality matching git — no manual deployment, no drift.

## Pull-based reconciliation

A distinctive GitOps mechanism is **pull-based** (vs push-based) deployment, and it matters for security and reliability:

```text
Push-based (traditional CI/CD deploy):
  pipeline → (has prod credentials) → pushes changes INTO the cluster

Pull-based (GitOps):
  agent INSIDE the cluster → pulls desired state FROM git → applies it locally
  → continuously reconciles actual vs desired
```

- **Push-based** — the CI/CD pipeline actively pushes deployments into the environment, which means the pipeline needs credentials *into* production (a security exposure) and deployment is a one-time action.
- **Pull-based (GitOps)** — an agent running *inside* the target environment (e.g. in the Kubernetes cluster) *pulls* the desired state from git and applies it, then keeps reconciling. The cluster reaches *out* to git; nothing external needs push credentials into the cluster.

Pull-based has real advantages: **better security** (no external system holds cluster-write credentials; the agent inside pulls), and **continuous reconciliation** (the agent constantly ensures actual matches desired, so it *corrects drift automatically* — if someone manually changes the cluster, the agent reverts it back to what git says). This continuous reconciliation is GitOps's superpower over plain IaC: IaC applies changes when you run it; GitOps *continuously* enforces the git state, so drift (from the IaC post) is not just detected but *automatically corrected*. Tools like Argo CD and Flux implement this pull-based reconciliation for Kubernetes.

## Why GitOps matters

GitOps delivers concrete benefits that make it the modern standard, especially for Kubernetes:

- **Auditability and history** — git *is* the record: every change to the system is a commit, so you have a complete, versioned, reviewable history of what changed, when, and by whom. Compliance and debugging both benefit.
- **Easy rollback** — because the desired state is versioned in git, rolling back is reverting a commit; the agent reconciles the system back to the previous state. Rollback is a git operation, not a scramble.
- **Drift correction** — continuous reconciliation means manual changes to the live system are automatically reverted to match git, so the system can't silently drift from its declared state (the IaC drift problem, solved).
- **Consistency across environments** — the same git-driven model applies to all environments, so promoting a change is a git change, and environments stay consistent.
- **Security** — pull-based means no external push credentials into production; the reconciliation agent's access is contained.
- **Developer workflow** — developers deploy by the same workflow they already know (a pull request to git), lowering cognitive load — which ties directly to the platform-engineering goal.

That last point connects GitOps to the platform: **GitOps gives developers a familiar, safe, self-service deployment model** — "change git, and the platform makes it real" — which is exactly the kind of paved-road capability an internal developer platform provides. Developers don't need to know the deployment mechanics; they commit config to git and the platform's GitOps reconciliation handles the rest.

## GitOps as declarative operations

The takeaway: GitOps makes git the single source of truth for the whole system's desired state (declaratively), with an automated agent pulling from git and continuously reconciling reality to match — turning deployment from an imperative action into a declared state. Its principles (declarative, versioned/immutable, pulled, continuously reconciled) deliver auditability, easy rollback, automatic drift correction, consistency, and security, via pull-based reconciliation (Argo CD, Flux on Kubernetes). It's the operational culmination of the declarative model IaC started, and it's how modern platforms deliver a safe, git-driven, self-service deployment experience to developers. With the DevOps foundation now covered (CI/CD, IaC, GitOps), the series turns to the platform-engineering discipline built on it — starting with the internal developer platform itself.

## Key takeaways

- GitOps makes git the single source of truth for the entire system's desired state (declaratively) and continuously reconciles the running system to match it — so you change the system by committing to git (a deploy is a commit), and git is the authoritative, versioned record of what should be running.
- Its principles: declarative (desired state as what-not-how), versioned and immutable (in git, with full history and revert-based rollback), pulled automatically (agents pull from git), and continuously reconciled (agents correct any divergence).
- GitOps is pull-based: an agent inside the target environment pulls desired state from git and applies it (vs push-based pipelines pushing in) — giving better security (no external push credentials into production) and continuous reconciliation that automatically corrects drift (not just detects it, as plain IaC does).
- Benefits: full auditability/history (every change is a commit), easy rollback (revert a commit), automatic drift correction, cross-environment consistency, and contained security — implemented by tools like Argo CD and Flux on Kubernetes.
- GitOps gives developers a familiar, safe, self-service deployment model (change git, the platform makes it real) — a paved-road capability that ties directly to platform engineering's cognitive-load-reduction goal, and the operational culmination of the declarative model IaC began.

## Further reading

- [Infrastructure as code (previous post)](/blog/posts/plateng-03-infrastructure-as-code.html)
- [OpenGitOps — GitOps principles](https://opengitops.dev/)
- [Distributed Systems: replication — reconciliation and desired-state thinking](/blog/posts/distsys-05-replication.html)
