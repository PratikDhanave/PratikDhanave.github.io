<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-specs.html -->

# Agentic Software Engineering in Go: Specification Engineering

*Replacing vague English prompts with precise, machine-readable specifications*

---

## The Problem: The English Prompt Trap

Most agentic workflows start with something like: *"Build a REST API for user management with authentication, validation, and error handling."*

That one sentence hides at least seven open decisions — auth format, validation approach, error shape, storage, API style, test expectations, documentation — and the agent will make all seven for you, differently each time. The deeper problem isn't that the agent chooses badly; it's that the choices are *invisible*. Nothing records what was asked, so nothing can check what was delivered, and a teammate picking up the work has to reverse-engineer intent from the code.

## Specs Are the Checkable Form of Intent

**Specification engineering** moves the request from prose to a machine-readable document with six load-bearing parts: intent (goal, success criteria, anti-goals), constraints, typed inputs, typed outputs, a dependency-ordered step plan, and — through the `validator` notes on constraints — a pointer to how each promise gets checked.

Here is the real spec format, from the authentication spec the [case study](/blog/posts/agentic-software-engineering-case-study.html) later executes:

```yaml
id: "auth-service-001"
version: "1.0"
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
    - "No plaintext storage of passwords or refresh tokens"
    - "No global mutable state"
constraints:
  - id: "c2"
    type: "must"
    description: "JWTs use github.com/golang-jwt/jwt/v5 with
                  SigningMethodHS256, and validation pins the algorithm"
    validator: "jwt.Parse must use WithValidMethods or an explicit method check"
inputs:
  secret:
    type: "[]byte"
    description: "HMAC signing key for access tokens"
    required: true
steps:
  - id: "s3"
    name: "Access tokens"
    depends_on: ["s1"]
    validation: "expired and tampered tokens rejected in tests"
```

Notice what the format forces. Success criteria must be phrased so something could check them. Anti-goals make the implicit explicit — "no global mutable state" is exactly the kind of standard an agent violates when it's merely unstated. And each constraint's `validator` names the proof, which keeps you from writing constraints that *sound* rigorous but can't be tested.

## The Engine

`pkg/spec` is deliberately small: parse YAML into typed structs, validate structure, render a prompt. The structural validation catches real authoring mistakes before any model runs — a missing goal, or a step graph referencing steps that don't exist:

```go
func (e *SpecEngine) ValidateSpec(spec *Specification) []string {
	var errors []string

	if spec.ID == "" {
		errors = append(errors, "spec ID is required")
	}
	if spec.Intent.Goal == "" {
		errors = append(errors, "intent.goal is required")
	}
	// ... plus: every steps[].depends_on entry must name an existing step
	return errors
}
```

```text
$ ./asf spec validate auth-service-001
Spec auth-service-001 is valid!
```

`GeneratePrompt` then renders the spec into exactly what the agent will read — constraints in MUST/MUST_NOT form, the numbered execution plan, the success criteria:

```text
## Constraints (MUST FOLLOW)
MUST: Passwords are hashed with golang.org/x/crypto/bcrypt at cost >= 12
MUST: JWTs use github.com/golang-jwt/jwt/v5 with SigningMethodHS256, and
      validation pins the algorithm
...
## Execution Plan
1. **Define types and errors**
2. **Password hashing** [depends on: s1]
3. **Access tokens** [depends on: s1]
```

The renderer is worth your attention because **prompts are code**. While dogfooding this engine I found that it printed every step with the same number — `len(spec.Steps)` where the loop index belonged — so every prompt it had ever produced listed the plan as "6. 6. 6. 6. 6. 6." A trivial bug, invisible forever, because nobody reads assembled prompts unless the system makes them inspectable. (`asf spec generate <id>` exists precisely for that; so does the factory's prompt-only mode, which completes tasks by returning the fully assembled prompt instead of calling a model.)

## What Specs Buy — Stated Honestly

Earlier drafts of this post claimed "same spec → same code every time." That's false, and the case study proves it: the same spec through the same model produced meaningfully different artifacts across retry rounds. LLMs are stochastic; a spec doesn't make generation deterministic.

What a spec actually buys is narrower and more valuable:

- **It narrows the distribution.** Constraints eliminate whole families of wrong output (plaintext passwords, unpinned JWT algorithms) regardless of sampling.
- **It makes output checkable.** "Did the agent comply?" becomes a question the verification pipeline ([next post](/blog/posts/agentic-software-engineering-verification.html)) and the LLM judge can answer per criterion — in the case study's real run, the judge scored spec-compliance lowest (0.85) and named the violated step.
- **It's the handoff artifact.** The spec is version-controlled next to the code. Disagreements about what to build become diffs, not recollections.
- **It survives the agent.** When a better model ships, you re-run specs; prompts trapped in chat histories die with them.

One claim the format does *not* yet cash: the `validator` fields on constraints are prose notes, not executable checks — the pipeline's constraint-verification phase is a stub as of this writing ([post 4](/blog/posts/agentic-software-engineering-verification.html) covers what is real). The honest status is: constraints are enforced today by the judge reading them and the human reviewing; mechanical enforcement is the designed next step.

## Authoring Workflow

```bash
./asf spec template specs/my-feature.yaml   # scaffold the format
$EDITOR specs/my-feature.yaml               # fill in intent, constraints, steps
./asf spec validate my-feature              # structural check
./asf spec generate my-feature              # read what the agent will read
```

Two field notes from using this daily. First, when generation goes wrong repeatedly, the fix is usually in the spec — a criterion that can't be checked, or a constraint the steps contradict. Treat spec revision as the normal response to agent failure, not an admission of defeat. Second, keep specs scoped to one reviewable artifact; the case-study spec deliberately asks for a single Go package with tests, not a deployed service, because a spec whose output you can't review in one sitting is a spec you can't verify.

The [next post](/blog/posts/agentic-software-engineering-verification.html) builds the machinery that holds generated code to what the spec promised: the AI-TDD verification pipeline.

---

*All code and command output in this post is from the companion factory codebase (Go 1.23+) and real sessions against it.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-04
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-specs.html
Attribution: please link the canonical URL when citing or quoting this post.
