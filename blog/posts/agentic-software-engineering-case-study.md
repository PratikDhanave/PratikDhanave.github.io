<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-case-study.html -->

# Agentic Software Engineering in Go: Case Study

*End-to-end, nothing mocked: one feature through the whole factory*

---

## The Setup

This series has made a lot of claims: that machine-readable specs beat prompts, that verification loops beat vibes, that an LLM judge is useful but not sufficient, that the whole thing composes into a factory. This closing post cashes those claims by running one feature through the entire stack and reporting what actually happened — including the parts that failed.

The ground rules: everything below is from one real session. The model is `qwen3.6` running locally through Ollama — deliberately not a frontier cloud model, because a local model's failures exercise the verification machinery harder, and the machinery is what this series is about. Timings are wall-clock. Nothing is cleaned up after the fact.

The feature is an authentication token package: bcrypt password hashing, HS256 JWT access tokens, single-use rotating refresh tokens. Scoped honestly — a Go library package with tests, not a deployed service. One spec, one reviewable artifact.

## Phase 1: The Specification

The spec follows the format from [post 3](/blog/posts/agentic-software-engineering-specs.html). The parts that end up mattering most are the constraints:

```yaml
id: "auth-service-001"
title: "Authentication token package"
intent:
  goal: "Implement a Go package `auth` with password hashing (bcrypt),
         HS256 JWT access-token issue/validate, and single-use rotating
         refresh tokens"
  anti_goals:
    - "No plaintext storage of passwords or refresh tokens"
    - "No hand-rolled crypto — stdlib crypto and golang.org/x/crypto/bcrypt
       only, plus github.com/golang-jwt/jwt/v5"
constraints:
  - id: "c1"
    type: "must"
    description: "Passwords are hashed with golang.org/x/crypto/bcrypt at cost >= 12"
  - id: "c2"
    type: "must"
    description: "JWTs use github.com/golang-jwt/jwt/v5 with SigningMethodHS256,
                  and validation pins the algorithm"
    validator: "jwt.Parse must use WithValidMethods or an explicit method check"
  - id: "c4"
    type: "must_not"
    description: "Refresh tokens must never be stored in plaintext and must be
                  invalidated after a single use"
steps:
  # s1 types/errors → s2 hashing, s3 access tokens, s4 rotation → s5 tests
```

```text
$ ./asf spec validate auth-service-001
Spec auth-service-001 is valid!
```

## Phase 2: The Tooling Shakeout Nobody Writes About

Before any model ran, `./asf verify` — the build/test/lint pipeline from [post 4](/blog/posts/agentic-software-engineering-verification.html) — had to work. It didn't, three times, and each failure is more instructive than a clean run would have been.

**Failure 1: toolchain skew.** The lint phase hard-failed because the installed golangci-lint (2.11.3, built with go1.26) couldn't read export data from the Go 1.27 toolchain compiling the repo:

```text
could not load export data: internal error in importing "internal/goarch"
(cannot decode "internal/goarch", export data version 5 is greater than
maximum supported version 2)
```

Your verification pipeline has its own dependencies, and they skew. Fix: upgrade the linter.

**Failure 2: the parser lied.** With the linter current, verify produced the most suspicious output of the session:

```text
✗ Verification failed with 0 errors:
```

The engine's lint parser recognized findings by searching lines for the lowercase words "error" or "warning". golangci-lint v2 findings — `Error return value of 'json.Unmarshal' is not checked (errcheck)` — contain neither. Fifty real findings, zero parsed. The fix was to match the structural shape (`file.go:line:col: message`) instead of keyword-sniffing. After it, the pipeline reported honestly:

```text
✗ Verification failed with 50 errors:
  [LINT] pkg/conversation/store.go:334 - Error return value of
         `json.Unmarshal` is not checked (errcheck)
  ...
```

**Failure 3: findings treated as crashes.** `./asf harness run auth-service-001` then *aborted* at the lint phase instead of entering its fix-prompt retry loop, because the verification engine returned findings as a Go `error` rather than as a failed result. The retry loop — the heart of AI-TDD — was unreachable code. One distinction fixed it: a phase that *ran and found problems* produces a verdict; only a phase that *could not run* produces an error. With that, the harness did its real job:

```text
$ ./asf harness run auth-service-001
✗ Harness failed for auth-service-001
  Duration: 19.46s
  Retries: 3
  Final: Verification failed after 3 retries
```

(A fourth bug, found by reading prompts: the spec renderer numbered every execution-plan step as `len(spec.Steps)` instead of its index. Every prompt the factory had ever assembled listed steps "6, 6, 6, 6, 6, 6".)

The lesson of this phase: **the verification harness is itself software and fails like software.** None of these four bugs were visible until the system ran against real work. If your agentic pipeline has never surprised you with its own defects, it probably hasn't run for real yet.

## Phase 3: The Live Run

Factory up ([post 10](/blog/posts/agentic-software-engineering-factory.html)), with the orchestrator restoring six historical tasks from SQLite on boot:

```text
2026/11/20 11:00:28 factory: LLM enabled (provider ollama, model qwen3.6:latest,
    max 2 concurrent calls, judge threshold 0.75, context budget 24000 chars)
```

Launch, then follow the SSE stream to the terminal state:

```text
$ curl -s -X POST localhost:8080/api/factory/launch/feature \
    -H 'Content-Type: application/json' -d '{"spec_id":"auth-service-001"}'
{"action":"feature","status":"running","task_id":"8f3d0c9e-...","type":"generate"}
```

Four minutes and 59 seconds later the task completed: one generation attempt, 37 context items in the prompt, and an LLM-as-judge verdict ([post 11](/blog/posts/agentic-software-engineering-ops.html)) well above the 0.75 threshold:

```json
"evaluation": {
  "score": 0.91, "passed": true,
  "criteria": { "correctness": 0.90, "code_quality": 0.95,
                "spec_compliance": 0.85, "security": 0.95,
                "documentation": 0.90 }
}
```

And the judge earned partial credit. Its improvement list caught two real problems: the artifact shipped **no tests** (spec step s5 — hence the lowest score landing on spec compliance), and a doc comment on the `RefreshTokenStore` interface promised an `ErrAlreadyExists` that exists nowhere in the code. The generated code itself read well — algorithm-pinned JWT validation, SHA-256-digested refresh tokens, sentinel errors, no global state.

## Phase 4: The Compiler Disagrees

Then I extracted the artifact into a module and ran the gate the judge isn't:

```text
$ go build ./...
./auth.go:90:2:  declared and not used: token
./auth.go:99:7:  undefined: jwt.WithAlgorithms
```

**The 0.91-scored artifact did not compile.** `jwt.WithAlgorithms` does not exist in `golang-jwt/jwt/v5` — the model hallucinated the API. Worse, and this is the sentence to remember from this whole series: *the judge praised the hallucination*. Its feedback specifically commended "algorithm pinning via `jwt.WithAlgorithms`". The judge is the same model that wrote the code; they share blind spots by construction. An LLM judge measures whether code *looks* right. Only the toolchain knows whether it *is*.

## Phase 5: The Fix Loop, Round by Round

I replayed the harness's fix prompt by hand against the same model — same system prompt, compiler output formatted exactly as the verification engine formats it — so each round below is one iteration of the AI-TDD loop with real feedback:

| Round | Feedback given | Result | Time |
|-------|----------------|--------|------|
| 1 (factory) | spec + context | Judge 0.91, but 2 compile errors, no tests | 4m 59s |
| 2 | both compiler errors + "tests required" | Errors fixed, tests added — new typo: `crypto/sha256"` missing its opening quote | 3m 36s |
| 3 | the exact malformed line | Quote fixed — but re-hallucinated the same API as `jwt.Algorithm` | 1m 23s |
| 4 | the exact correct call: `jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()})` | **Builds. Vets clean. All 7 tests pass.** | 1m 55s |

```text
--- PASS: TestAuthService (1.05s)
    --- PASS: TestAuthService/HashPassword_succeeds (0.52s)
    --- PASS: TestAuthService/CheckPassword_mismatch_returns_error (0.52s)
    --- PASS: TestAuthService/IssueAccessToken_creates_valid_token (0.00s)
    --- PASS: TestAuthService/ValidateAccessToken_rejects_invalid_token (0.00s)
    --- PASS: TestAuthService/IssueRefreshToken_generates_and_stores_digest (0.00s)
    --- PASS: TestAuthService/RotateRefreshToken_successfully_validates... (0.00s)
    --- PASS: TestAuthService/RotateRefreshToken_rejects_invalid_base64... (0.00s)
ok   authdemo  1.515s
```

Look at what rounds 3 and 4 demonstrate together. "undefined: jwt.WithAlgorithms" was true but insufficient — told only that the name was wrong, the model guessed another wrong name for the same imaginary API. The loop converged the moment the feedback contained the *actual* API. **Convergence of the fix loop is bounded by the precision of the feedback**, which is the deepest argument for context engineering ([post 2](/blog/posts/agentic-software-engineering-context.html)): had the spec's context included a two-line cheat sheet of the `jwt/v5` parser options, round 1 would likely have been right — the 24K-char local context budget means the model was working from training memory of an API that changed between major versions.

And one more honest finding: the passing tests are *partial*. Nothing exercises an actually-expired token, and no test reuses a rotated refresh token to assert `ErrRefreshReused`. Green tests written by the same model that wrote the code inherit the same blind spots. The human review gate ([post 6](/blog/posts/agentic-software-engineering-autonomy.html) put it at the autonomy boundary) stays.

## The Scorecard

Measured, not estimated:

| What | Value |
|------|-------|
| Spec authoring + validation | ~20 minutes, one `validate` pass |
| Verification-harness bugs found & fixed before any LLM ran | 4 |
| Factory generate task (gen + judge, local qwen3.6) | 4m 59s, 1 attempt |
| Judge score vs. compiler verdict on round 1 | 0.91 "passed" vs. 2 build errors |
| Rounds to a building, tested artifact | 4 (~12m of model time) |
| Generated tests passing / criteria actually covered | 7/7 passing; coverage incomplete |
| Lint findings surfaced in the factory's own repo | 50 (real backlog) |

## What This Proves, and What It Doesn't

The pipeline earned its keep in both directions: the judge caught real spec violations the compiler can't see (missing tests, lying doc comments), and the compiler caught a confident hallucination the judge blessed. Every claim in this series about layered verification came down to that one pair of facts.

The biggest gap is now precisely locatable: the factory's judge loop is wired, but its *compiler* loop is not — generate tasks return artifacts as task results, and nothing inside the loop yet writes them to a workspace and runs `go build` before the judge opines. Phase 5 was me doing that step by hand. Wiring artifact extraction into the verification engine is the single highest-leverage next change, and it's an orchestration change, not an AI one.

That is the closing thought of the series. Nothing in the hard parts of this case study was about prompting. The failures were toolchain skew, a parser bug, an error-vs-verdict design mistake, and a feedback loop that needed better data — software engineering, all the way down. The agentic part works exactly as well as the engineering discipline wrapped around it.

---

*Every command, timing, score, and failure in this post is from a single real session against the companion factory codebase (Go 1.23+), model qwen3.6 via Ollama. The four harness bugs described are fixed in the codebase as of this writing.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-13
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-case-study.html
Attribution: please link the canonical URL when citing or quoting this post.
