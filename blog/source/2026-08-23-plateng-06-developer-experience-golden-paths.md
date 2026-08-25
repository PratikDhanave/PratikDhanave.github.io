# Developer Experience and Golden Paths

*A golden path is the well-lit, paved road through your platform — the supported, opinionated way to build and ship a service, so a developer can go from idea to production without making a hundred infrastructure decisions. Developer experience is the measure of how good that road feels. Together they're what makes a platform actually reduce cognitive load rather than just relocate it.*

The IDP is the platform; **developer experience (DX)** is how good it is to use, and **golden paths** are the primary mechanism for delivering great DX. This post covers what golden paths (paved roads) are, why they beat both rigid mandates and total freedom, and how DX is the real measure of a platform's success. This is the heart of *why* platform engineering works — it's not about controlling developers, it's about making the good way the easy way.

## Golden paths: the paved road

A **golden path** (or *paved road*) is a supported, opinionated, well-documented way to accomplish a common task — most importantly, creating and shipping a service. Instead of a developer facing a blank slate and a hundred decisions (which language setup? which pipeline? how to deploy? how to add observability? how to handle secrets? which cloud resources?), the golden path gives them a *ready-made, best-practice route*:

```text
Without a golden path: developer assembles from scratch —
  pick a framework, write a Dockerfile, build a pipeline, configure Kubernetes,
  wire observability, set up secrets, provision a database... (huge cognitive load, hours/days, inconsistent)

With a golden path: developer runs a template / scaffold →
  gets a service with pipeline, deployment, observability, security, and a database
  wired up the right way, ready to code the actual feature (minutes, consistent, best-practice)
```

A golden path typically manifests as a **template or scaffold**: "create a new service" produces a working service pre-wired with the pipeline (CI/CD), deployment (GitOps), observability, security defaults, and common resources — all set up the *right* way. The developer starts from a production-ready foundation and writes their feature, rather than spending days assembling infrastructure. This is the concrete mechanism that reduces cognitive load: the golden path *makes the infrastructure decisions for you*, embedding best practices so you don't have to know them.

The paved-road metaphor is apt: it's the smooth, well-lit, supported route. You *can* go off-road (build something custom) if you truly need to, but the paved road is so much easier and safer that most journeys take it — by choice, because it's better.

## Opinionated but not mandatory

The key design principle of golden paths — and a subtle balance — is being **opinionated but not mandatory** (paved roads, not railroads):

- **Opinionated** — the golden path makes decisions *for* the developer (this framework setup, this pipeline, this deployment method, these defaults), so they don't have to. Opinions are the *point* — they're what removes the decisions and cognitive load. A golden path with no opinions ("here are 20 options, choose") doesn't reduce load at all.
- **Not mandatory** — but developers *can* deviate when they have a genuine need the golden path doesn't serve. It's a paved road (strongly preferred, easiest), not a railroad (the only option). Forcing everyone onto one rigid path breaks down for the legitimate edge cases and breeds resentment.

This balance matters because it avoids two failure modes:

- **Too rigid (railroad)** — if the only way is the mandated way, developers with legitimate special needs are stuck, forced to fight the platform or route around it entirely (shadow infrastructure). Mandates breed workarounds.
- **Too loose (no opinions)** — if the platform just offers options without a clear best-practice default, developers still face all the decisions and cognitive load; the platform didn't actually help. Total freedom is what caused the problem.

The golden-path sweet spot: **a strong, opinionated default that handles the common case beautifully, with the freedom to deviate for genuine exceptions.** Most developers take the paved road because it's clearly the easiest and best; the few with real special needs can go off-road. This is "make the right way the easy way" — you guide developers toward best practices not by *forcing* them but by making the best-practice path the *path of least resistance*. That's far more effective than mandates, because developers *want* to take it.

## Developer experience is the measure

**Developer experience (DX)** — how good it feels to build software with your platform and tools — is the real measure of a platform's success, and it's why golden paths matter. A platform succeeds not by existing but by being *genuinely pleasant and productive to use*. Good DX means:

- **Low friction** — common tasks are fast and easy (self-service, golden paths), not full of manual steps, waiting, or yak-shaving.
- **Low cognitive load** — developers focus on their product/feature, not on infrastructure decisions and tooling — the whole point of the discipline (post one).
- **Fast feedback and flow** — quick pipelines, quick environments, quick answers, so developers stay in flow rather than blocked and context-switching.
- **Good defaults and clear paths** — the right way is obvious and easy (golden paths), so developers aren't lost or making error-prone decisions.
- **Discoverability and documentation** — developers can find what they need (a developer portal, good docs) without hunting or asking around.

DX is the *product quality* of the platform (from the platform-as-a-product post). Just as a consumer product succeeds by being delightful to use, an IDP succeeds by giving developers a great experience — which is what earns the voluntary adoption that platform-as-a-product requires. Poor DX (friction, mandates, waiting, confusion) means developers resent and route around the platform, no matter how technically capable it is. **Great DX is what makes a platform actually adopted and actually cognitive-load-reducing** — it's the outcome the whole discipline aims at.

## Why this is the heart of it

Step back and see why DX and golden paths are the core of platform engineering:

- The *problem* (post one) was developer cognitive load from the vast stack.
- The *solution* (post five) was a self-service platform.
- But a platform only *solves* the problem if it's actually *pleasant and easy to use* — a self-service platform with terrible DX just relocates the cognitive load (now you have to learn the platform). Golden paths + great DX are what make the platform *genuinely* reduce cognitive load rather than add a new layer of it.

So golden paths (opinionated, easy best-practice routes) delivering great DX (low friction, low cognitive load, fast flow) are the mechanism by which platform engineering achieves its purpose. This is also why platform engineering is *developer-centric*, not control-centric: it wins by serving developers so well they *choose* the platform, not by mandating it. Get golden paths and DX right, and the platform succeeds; get them wrong, and even the best infrastructure goes unused. The next post covers keeping what the platform runs *reliable* — observability and SRE on the platform.

## Key takeaways

- A golden path (paved road) is a supported, opinionated, well-documented way to do a common task — especially creating a service — typically a template/scaffold that produces a production-ready service pre-wired with pipeline, deployment, observability, security, and resources, so developers start from a best-practice foundation instead of assembling infrastructure from scratch.
- Golden paths reduce cognitive load by *making the infrastructure decisions for you* (embedding best practices), which is the concrete mechanism behind the platform's purpose — a golden path with no opinions doesn't help.
- The design principle is opinionated but not mandatory (paved road, not railroad): a strong best-practice default for the common case, with freedom to deviate for genuine exceptions — avoiding both too-rigid mandates (which breed workarounds) and too-loose freedom (which leaves the cognitive load).
- "Make the right way the easy way": guide developers to best practices by making the best-practice path the path of least resistance, so they take it by choice — far more effective than mandates.
- Developer experience (DX) — low friction, low cognitive load, fast feedback/flow, good defaults, discoverability — is the real measure of a platform's success and its product quality; great DX earns voluntary adoption and genuinely reduces cognitive load, while poor DX means developers route around the platform no matter how capable it is. DX + golden paths are the heart of platform engineering.

## Further reading

- [The internal developer platform (previous post)](/blog/posts/plateng-05-internal-developer-platform.html)
- [Team Topologies — reducing cognitive load and enabling flow](https://teamtopologies.com/)
- [From DevOps to platform engineering — cognitive load, the problem DX solves](/blog/posts/plateng-01-devops-to-platform-engineering.html)
