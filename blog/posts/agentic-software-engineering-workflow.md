<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-workflow.html -->

# Agentic Software Engineering in Go: Developer Workflow

*From hand work to head work: the daily developer loop*

---

## The Problem: The Antagonist Loop

Most developers experience an antagonistic relationship with coding agents. You ask for a function, the agent generates something plausible, you point out the imports are wrong, it tries again, you explain the team's error-handling idiom, it tries again, and eventually you give up and write the thing yourself. The agent consumed twenty minutes and produced nothing you kept.

The root cause is not the model. It is that the interaction has no structure: no written success criteria, so "done" is whatever you fail to object to; no constraints, so the agent cannot know your organizational standards; no verification, so unproven code lands in your lap for manual inspection; and no artifact a colleague could pick up, because the whole exchange lives in a chat transcript.

The previous posts in this series built the machinery that fixes this — specifications ([post 3](/blog/posts/agentic-software-engineering-specs.html)), the verification pipeline ([post 4](/blog/posts/agentic-software-engineering-verification.html)), and the harness that ties them together ([post 5](/blog/posts/agentic-software-engineering-harness.html)). This post is about what your day actually looks like once that machinery exists. The short version: you stop typing implementations and start writing specs, reviewing artifacts, and directing the system — hand work becomes head work.

## The Daily Loop

The loop has four phases, and only one of them is new work:

```text
author spec  ──►  validate  ──►  agent generates  ──►  verify + review
    ▲                                                        │
    └────────── revise spec when the failure is yours ◄──────┘
```

The surprising part in practice is the feedback edge on the left. When verification fails repeatedly, the bug is often in the *specification* — a success criterion that cannot be checked, a constraint the steps contradict — and the fix is editing YAML, not code.

## Authoring a Spec

Everything starts from `asf spec template`, which scaffolds the machine-readable format the whole factory consumes:

```bash
./asf spec template specs/my-feature.yaml
$EDITOR specs/my-feature.yaml
./asf spec validate my-feature
```

A spec has five load-bearing sections — intent (goal, success criteria, anti-goals), constraints (`must` / `must_not`, each with a validator note), typed inputs and outputs, and a dependency-ordered step plan. Here is a condensed excerpt from the authentication spec the series [case study](/blog/posts/agentic-software-engineering-case-study.html) runs end to end:

```yaml
id: "auth-service-001"
title: "Authentication token package"
intent:
  goal: "Implement a Go package `auth` with password hashing (bcrypt),
         HS256 JWT access-token issue/validate, and single-use rotating
         refresh tokens"
  success_criteria:
    - "HashPassword/CheckPassword wrap bcrypt with a work factor of at least 12"
    - "ValidateAccessToken rejects expired tokens, bad signatures, and
       tokens signed with none/other algorithms"
  anti_goals:
    - "No hand-rolled crypto — stdlib crypto and golang.org/x/crypto/bcrypt
       only, plus github.com/golang-jwt/jwt/v5"
constraints:
  - id: "c2"
    type: "must"
    description: "JWTs use github.com/golang-jwt/jwt/v5 with
                  SigningMethodHS256, and validation pins the algorithm"
    validator: "jwt.Parse must use WithValidMethods or an explicit method check"
steps:
  - id: "s3"
    name: "Access tokens"
    depends_on: ["s1"]
    validation: "expired and tampered tokens rejected in tests"
```

What makes a spec good is checkability. "Make it fast" is not a criterion; "95th-percentile latency under 100ms" is. "Secure" is not a constraint; "refresh tokens stored only as SHA-256 digests, invalidated after one use" is. Every success criterion should name the test, grep, or command that would prove it — the `validator` field exists to force that discipline.

The validator catches structural problems before any model sees the spec — missing goals, and steps that depend on steps that don't exist:

```text
$ ./asf spec validate auth-service-001
Spec auth-service-001 is valid!
```

## From Spec to Prompt

`asf spec generate` renders the YAML into the prompt the agent receives, so you can read exactly what the model will be told — no hidden prompt assembly:

```text
$ ./asf spec generate auth-service-001

# Specification: Authentication token package
...
## Constraints (MUST FOLLOW)
MUST: Passwords are hashed with golang.org/x/crypto/bcrypt at cost >= 12
MUST: JWTs use github.com/golang-jwt/jwt/v5 with SigningMethodHS256, and
      validation pins the algorithm
...
## Execution Plan
1. **Define types and errors**
2. **Password hashing** [depends on: s1]
3. **Access tokens** [depends on: s1]
...
```

Reading this output regularly is worth the habit. While writing this series I noticed the execution plan printed every step with the same number — the renderer was using `len(spec.Steps)` where it meant the loop index. A one-line fix, but it had been silently mis-numbering every prompt. Inspectable prompts get debugged; invisible ones don't.

When a harness run is wired to an LLM, this prompt goes out with curated project context appended — the ADRs and conventions from [post 2](/blog/posts/agentic-software-engineering-context.html) — and the verification loop from post 4 gates what comes back.

## Verification Is the Inner Loop

`asf verify` runs the pipeline — build, test, lint — against the working tree, and you run it the way you run tests: constantly.

```text
$ ./asf verify
Running verification...
✗ Verification failed with 50 errors:
  [LINT] pkg/conversation/store.go:334 - Error return value of
         `json.Unmarshal` is not checked (errcheck)
  [LINT] pkg/integration/teams.go:26 - type teamsSigVerifier is unused (unused)
  ...
```

That output is from a real run against the factory's own codebase, and the 50 findings are real backlog. The point of the workflow is not that verification always passes — it is that failure arrives as a structured list of file:line findings that can be handed back to an agent as a fix prompt, instead of as a vague feeling that the code is untrustworthy.

`asf harness run <spec-id>` composes the whole thing: load spec, assemble context, generate the prompt, then run the verification loop with bounded retries, emitting a fix prompt on each failure. The [case study](/blog/posts/agentic-software-engineering-case-study.html) walks through a complete run, including the failures.

## The Real Command Surface

These are the commands that exist today, from the CLI's own help text — this list is deliberately boring, because the workflow should be:

```text
asf init                       scaffold project structure
asf context                    show what context the agent would receive
asf spec template [path]       scaffold a spec
asf spec validate <spec-id>    structural validation
asf spec generate <spec-id>    render the agent prompt
asf verify                     build + test + lint on the working tree
asf harness run <spec-id>      spec + context + verification loop
asf factory start|status|submit|states
asf mcp start [addr]           headless API for other tools
asf integration list|status    adapter status (Slack/Teams/GitHub/Linear)
```

Two honest caveats. First, `asf factory submit` from the CLI constructs a fresh orchestrator per invocation — the durable, always-on mode runs through the API server, which the [next post](/blog/posts/agentic-software-engineering-factory.html) covers. Second, the "overnight batch" workflow this post's first draft promised is aspirational until you deploy that server somewhere that stays up overnight.

## Why This Beats the Antagonist Loop

The spec is the artifact, and that changes four things concretely. Disagreements about what to build become diffs on a YAML file instead of competing recollections of a chat. Success criteria are checked by the pipeline, not re-litigated per review. A new teammate reads `specs/` to learn what the system is supposed to do — the specs are documentation that cannot drift, because the harness executes them. And when the agent produces garbage, you debug one of three inspectable inputs — spec, context, or verification feedback — instead of rewording a prompt and hoping.

The next post scales this from one developer's loop to an always-on system: the [factory orchestrator](/blog/posts/agentic-software-engineering-factory.html), with durable task state, worker pools, and crash recovery.

---

*Command output in this post is from real sessions against the companion factory codebase (Go 1.23+); nothing is mocked up.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-10
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-workflow.html
Attribution: please link the canonical URL when citing or quoting this post.
