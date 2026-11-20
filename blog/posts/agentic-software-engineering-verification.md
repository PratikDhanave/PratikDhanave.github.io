<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-verification.html -->

# Agentic Software Engineering in Go: AI-TDD Verification Loops

*Automated verification of agent-generated code*

---

## The Problem: Unverified Agent Output

When an agent generates code, the default human posture is "looks right, probably works." The [case study](/blog/posts/agentic-software-engineering-case-study.html) at the end of this series provides the canonical counterexample from a real run: an artifact that an LLM judge scored 0.91 — with specific praise for its security design — failed `go build` on an API the model had hallucinated. Plausibility and correctness are different properties, and only a toolchain can tell them apart.

**AI-TDD** is the discipline of putting every agent artifact through the same gate human code faces — build, test, lint — and feeding failures back as structured input for revision, automatically, up to a bounded retry limit.

## The Pipeline Is a State Machine

The verification pipeline in `pkg/verify` advances phase by phase and stops at the first failure. Rather than scattering phase names through string comparisons, the lifecycle is a declared state machine — the same pattern every lifecycle in the factory uses:

```go
// Verification pipeline phases. The pipeline advances phase by phase and
// stops at the first failing phase.
const (
	PhaseBuild       state.State = "build"
	PhaseTest        state.State = "test"
	PhaseLint        state.State = "lint"
	PhaseConstraints state.State = "constraints"
	PhasePassed      state.State = "passed"
	PhaseFailed      state.State = "failed"
)

var PhaseMachine = state.NewMachine("verification", PhaseBuild, map[state.State][]state.State{
	PhaseBuild:       {PhaseTest, PhaseFailed},
	PhaseTest:        {PhaseLint, PhaseFailed},
	PhaseLint:        {PhaseConstraints, PhasePassed, PhaseFailed},
	PhaseConstraints: {PhasePassed, PhaseFailed},
})
```

The phases run `go build ./...`, `go test -v ./...`, and `golangci-lint run ./...` with per-phase timeouts, each parsing its tool's output into a shared finding type:

```go
type VerificationError struct {
	Type       string // "build", "test", "lint", "constraint"
	File       string
	Line       int
	Message    string
	Suggestion string
	Severity   string
}
```

That struct is the whole point of the pipeline. Raw tool output is for humans; `[]VerificationError` is for machines — it can be counted, trended, and above all *rendered back into a prompt*.

Honest inventory before going further: the `constraints` phase is currently a stub — spec constraints are enforced by the LLM judge and human review today, not mechanically ([post 3](/blog/posts/agentic-software-engineering-specs.html) discusses this gap). Build, test, and lint are real and are the gate everything below runs through.

## What Dogfooding the Engine Taught

Running this engine for real — against the factory's own repository, preparing the case study — surfaced three bugs *in the verification machinery itself*, and each one teaches a design principle.

**Your pipeline has its own dependencies, and they skew.** The first real run died inside golangci-lint: the installed linter was built with an older Go than the toolchain compiling the repo, and failed with `cannot decode "internal/goarch", export data version 5 is greater than maximum supported version 2`. A verification pipeline is software with a supply chain; version-pin the linter alongside the toolchain.

**Parse structure, not keywords.** With the linter fixed, the next run printed the most dangerous output a verifier can produce:

```text
✗ Verification failed with 0 errors:
```

The lint parser recognized findings by searching for the lowercase words "error" or "warning" — and golangci-lint v2 findings (`Error return value of 'json.Unmarshal' is not checked (errcheck)`) contain neither. Fifty real findings, zero parsed. The fix matches the structural shape every finding shares instead of sniffing vocabulary:

```go
// lintFindingRe matches a golangci-lint finding line: path/file.go:line:col: message (linter).
// Findings are identified by shape, not by keywords — golangci-lint v2 findings
// ("Error return value ... (errcheck)") contain neither "error" nor "warning"
// in lowercase, and source-echo/caret lines never match the shape.
var lintFindingRe = regexp.MustCompile(`^(\S+\.go):(\d+):(\d+):\s+(.+)$`)
```

After which the same run reports honestly:

```text
✗ Verification failed with 50 errors:
  [LINT] pkg/conversation/store.go:334 - Error return value of
         `json.Unmarshal` is not checked (errcheck)
  [LINT] pkg/integration/teams.go:26 - type teamsSigVerifier is unused (unused)
  ...
```

**A failed verdict is not an error.** The subtlest bug: phases originally returned a Go `error` when their tool found problems, so callers treated "lint found 50 issues" the same as "lint isn't installed" — and aborted. The retry loop that makes AI-TDD a *loop* was unreachable code. The fix is one distinction, now explicit in `RunVerification`:

```go
if err := step.run(ctx, result); err != nil {
	result.FailedPhase = step.phase
	result.Phase = PhaseFailed
	if len(result.Errors) == 0 {
		// Nothing parseable came back: the phase could not run at
		// all (missing tool, exec failure). That is an
		// infrastructure error, not a verification verdict.
		return result, fmt.Errorf("%s verification failed: %w", step.phase, err)
	}
	// The phase ran and found failures — a verdict, not an error.
	// Callers feed result.Errors into the fix-prompt retry loop.
	return result, nil
}
```

If your own pipeline conflates "the check failed" with "the check couldn't run," every downstream consumer inherits the confusion.

## Closing the Loop: The Fix Prompt

When verification fails, the findings render into the prompt for the next generation attempt — this is the actual production code, not a sketch:

```go
func GenerateFixPrompt(result *VerificationResult, specContent string) string {
	var sb strings.Builder

	sb.WriteString("# Verification Failed - Please Fix\n\n")
	sb.WriteString("The following verification errors were found:\n\n")

	for _, err := range result.Errors {
		sb.WriteString(fmt.Sprintf("## %s: %s\n", strings.ToUpper(err.Type), err.Message))
		if err.File != "" {
			sb.WriteString(fmt.Sprintf("**File**: %s", err.File))
			if err.Line > 0 {
				sb.WriteString(fmt.Sprintf(":%d", err.Line))
			}
			sb.WriteString("\n")
		}
		...
	}

	sb.WriteString("## Original Specification\n\n")
	sb.WriteString(specContent)
	sb.WriteString("\n\nPlease fix the code and ensure all verification passes.\n")
	return sb.String()
}
```

With the verdict fix in place, the harness runs the real bounded loop. Against a repo with 50 standing lint findings and no agent wired to fix them, it does exactly what it should — four verification rounds, then an honest failure:

```text
$ ./asf harness run auth-service-001
✗ Harness failed for auth-service-001
  Duration: 19.46s
  Retries: 3
  Final: Verification failed after 3 retries
```

One finding from the case study belongs in this post's conclusions, because it's about feedback quality rather than feedback plumbing: the fix loop converges only as fast as its feedback is precise. `undefined: jwt.WithAlgorithms` was a true statement that let the model guess a *second* wrong name for the same imaginary API; the loop converged the round the feedback contained the actual correct call. When a retry oscillates, the move is to enrich the feedback (or the context), not to raise the retry limit.

## Where the Loop's Edges Are

Worth stating plainly, because verification is where overclaiming hurts most:

- **Green tests from the generating model are weak evidence.** In the case study's converged round, all 7 generated tests passed — and none exercised an expired token or a reused refresh token. The same blind spots that shape the code shape its tests. Verification bounds *regressions*; it doesn't certify *coverage*.
- **Retry limits are a cost control, not a quality strategy.** The default is 3. If artifacts routinely need more, the spec or context is underspecified — fix the input, not the loop count.
- **Lint findings are a backlog signal.** The 50 findings above are real debt in the factory's own repo (22 `unused`, 21 `errcheck`, 7 `staticcheck`), surfaced the first time the pipeline's parser worked. A verifier that has never embarrassed its own codebase hasn't been run honestly yet.

The [next post](/blog/posts/agentic-software-engineering-harness.html) wires this engine together with context loading and spec rendering into the single entry point the rest of the series builds on: the complete harness.

---

*All code and command output in this post is from the companion factory codebase (Go 1.23+) and real sessions against it; the three bugs described are fixed there as of this writing.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-05
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-verification.html
Attribution: please link the canonical URL when citing or quoting this post.
