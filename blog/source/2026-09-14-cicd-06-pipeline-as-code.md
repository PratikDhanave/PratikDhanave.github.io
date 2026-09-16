# Pipeline as Code

*A pipeline is only trustworthy if it's defined the same way your application is: as version-controlled code, reviewed and reproducible. "Pipeline as code" turns the path to production from clicked-together settings in a web UI into a file in your repository — and that shift, from configuration to code, brings the whole discipline of software engineering to bear on how you ship software.*

We've covered what flows through a pipeline; this post is about how the pipeline itself is defined. Modern CI/CD systems — GitHub Actions, GitLab CI, and others — express pipelines as declarative files committed alongside your code. Understanding this model, and the principles for doing it well, is what separates a maintainable delivery system from a fragile one.

## From clicked config to committed code

Early CI servers were configured by clicking through a web UI — defining build steps in forms, storing them in the server's database. That worked until it didn't: the configuration wasn't versioned, wasn't reviewable, wasn't reproducible, and lived only in one server's state. Nobody could see *why* the pipeline changed, or restore a previous version, or stand up an identical pipeline elsewhere.

**Pipeline as code** fixes this by defining the pipeline in a file *in the repository* — `.github/workflows/*.yml`, `.gitlab-ci.yml`, a `Jenkinsfile`. The consequences are the same benefits version control brings to any code:
- **Versioned** — the pipeline's history is in git; you can see every change and who made it, and roll back a bad pipeline change like any other.
- **Reviewed** — pipeline changes go through pull requests and code review, just like application changes.
- **Reproducible** — the pipeline is fully described by a file, so it's identical everywhere and can be recreated from scratch.
- **Co-located and co-evolving** — the pipeline lives beside the code it builds and changes *with* it in the same commit, so a change that needs a new build step ships its pipeline update atomically.

This is the same "as code" shift that Infrastructure as Code brought to servers: replace clicked-together, un-auditable state with declarative, version-controlled definitions. It's foundational to everything else.

## The declarative model: workflows, jobs, steps

Most pipeline systems share a structure worth knowing generically (names vary by tool):

- A **workflow/pipeline** is triggered by an **event** — a push, a pull request, a tag, a schedule, a manual dispatch.
- It contains **jobs** — units of work that can run in parallel and on different machines. Jobs can depend on each other, forming the stage graph (test job → build job → deploy job).
- Each job runs **steps** in sequence — individual commands or reusable actions (check out code, set up a language, run tests, build an image).

A minimal GitHub Actions example shows the shape:

```yaml
name: CI
on: [push, pull_request]        # event triggers
jobs:
  test:                          # a job
    runs-on: ubuntu-latest
    steps:                       # sequential steps
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: npm test
```

The model is **declarative**: you describe *what* the pipeline consists of (triggers, jobs, steps, dependencies) and the system figures out *how* to schedule and run it — parallelizing independent jobs, ordering dependent ones. You declare the graph; the runner executes it. This declarative nature is what makes pipelines readable and reproducible.

## Principles for maintainable pipelines

A pipeline is code, so treat it like code — the same practices that keep applications maintainable apply:

- **DRY: don't repeat pipeline logic.** As pipelines grow, duplication creeps in (the same deploy steps copied across environments). Factor shared logic into reusable units — reusable workflows, composite actions, templates, anchors — so a change is made once. Copy-pasted pipeline logic rots exactly like copy-pasted code.
- **Keep steps small and named.** A step should do one clear thing with a readable name, so a failed run points precisely at what broke. A giant shell script step is a black box when it fails.
- **Fail fast, cheap first** (post 3) — order jobs so quick checks gate expensive ones, and use job dependencies to stop the graph early on failure.
- **Pin versions.** Pin the versions of the actions/images your pipeline uses (and ideally to a digest), so a pipeline that passes today passes tomorrow — an unpinned dependency can change under you and break or, worse, be compromised (a supply-chain risk we cover next post).
- **Make it fast** (post 3) — caching and parallelism apply to the pipeline definition directly (cache steps, parallel jobs).
- **Keep it readable** — the pipeline is documentation of your path to production; a newcomer should be able to read the file and understand how the software ships.

The meta-principle: everything you'd do to keep application code healthy — DRY, small units, reviews, versioning, readability — applies to pipeline code, because it *is* code now.

## Runners, environments, and matrix builds

Two more concepts round out the model:

- **Runners** are the machines that execute jobs — hosted (the provider's, e.g. GitHub-hosted ubuntu runners) or self-hosted (yours, for special hardware, private-network access, or cost at scale). The pipeline file selects which.
- **Matrix builds** run the same job across combinations of parameters — test against Node 18/20/22, or Linux/macOS/Windows, in parallel — declared compactly and expanded by the runner. This is how you get broad compatibility coverage without copy-pasting the job, and a clean example of the declarative model's leverage: one small spec, many parallel executions.

Together, the pipeline-as-code model gives you a versioned, reviewed, reproducible definition of your entire path to production — declarative, maintainable, and evolving in lockstep with your application. It's the substrate the security and operations concerns of the next posts build on: you can't secure or reliably operate a pipeline that only exists as clicks in a web UI.

## Key takeaways

- **Pipeline as code** defines the pipeline in a version-controlled file in the repo (`.github/workflows`, `.gitlab-ci.yml`) instead of clicked-together UI config — making it **versioned, reviewed, reproducible, and co-evolving** with the application (the same shift as Infrastructure as Code).
- Pipelines share a **declarative model**: an *event* triggers a *workflow* of *jobs* (parallel, with dependencies forming the stage graph) each running sequential *steps* — you declare *what*, the runner figures out *how* (scheduling, parallelizing).
- Treat pipeline definitions like the code they are: **DRY** (factor shared logic into reusable workflows/actions — copy-pasted pipeline logic rots), small named steps, fail-fast ordering, **pinned versions** (reproducibility + supply-chain safety), caching/parallelism, and readability.
- **Runners** (hosted vs self-hosted) execute jobs; **matrix builds** run one job across parameter combinations (languages/OSes) in parallel — one small spec, many executions, the declarative model's leverage.
- A pipeline-as-code definition is the versioned, reproducible substrate that securing and operating the pipeline (next posts) depends on — you can't secure or reliably operate clicks in a web UI.

## Further reading

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [Martin Fowler — Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html)
