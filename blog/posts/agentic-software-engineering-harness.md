<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-harness.html -->

# Agentic Software Engineering in Go: The Complete Harness

*Integrating context, specifications, and verification loops*

---

## The Problem: Three Disciplines, Three Silos

The last three posts built three engines: context loading ([post 2](/blog/posts/agentic-software-engineering-context.html)), spec parsing and prompt rendering ([post 3](/blog/posts/agentic-software-engineering-specs.html)), and the build/test/lint verification pipeline ([post 4](/blog/posts/agentic-software-engineering-verification.html)). Used separately, they leak at the seams: a developer assembles context by hand and forgets the ADRs; a prompt goes out without the spec's constraints; generated code lands unverified because running the pipeline was a separate manual step.

The **harness** is the component that makes the composition mandatory. One call takes a spec ID and does everything in the right order; there is no path through it that skips a discipline.

## One Entry Point

The harness is deliberately thin — it owns no intelligence of its own, just the composition:

```go
// CompleteHarness integrates context, specs, and verification
type CompleteHarness struct {
	contextEngine *asfContext.ContextEngine
	specEngine    *spec.SpecEngine
	verifier      *verify.VerificationEngine
	workingDir    string
	maxRetries    int
}
```

`Execute(ctx, specID)` runs the sequence: load and structurally validate the spec (an invalid spec aborts before any model is involved), load the prioritized context items, render spec + context into the full prompt, then drive the verification loop with bounded retries, generating a fix prompt from the findings on each failure. The prompt assembly is one line, and it's worth seeing because it *is* the integration everyone hand-waves:

```go
specPrompt := h.specEngine.GeneratePrompt(s)
contextStr := asfContext.FormatForAgent(contextItems)
fullPrompt := fmt.Sprintf("%s\n\n## Project Context\n%s", specPrompt, contextStr)
```

Everything the agent will ever know about the task is in `fullPrompt`, built the same way every time. When output is wrong, there are exactly three inspectable inputs to debug — the spec, the context, or the verification feedback — instead of a chat history.

The result type records the whole run, which is what makes harness executions comparable across time:

```go
type HarnessResult struct {
	SpecID        string
	Success       bool
	ContextItems  []asfContext.ContextItem
	SpecPrompt    string
	Verification  *verify.VerificationResult
	TotalDuration time.Duration
	RetryCount    int
	AgentFeedback string
	FinalOutput   string
}
```

## A Real Run

From the session behind the [case study](/blog/posts/agentic-software-engineering-case-study.html), against the factory's own repository — which carries 50 standing lint findings, so this is the honest failure path:

```text
$ ./asf harness run auth-service-001
✗ Harness failed for auth-service-001
  Duration: 19.46s
  Retries: 3
  Final: Verification failed after 3 retries
```

Four verification rounds in under twenty seconds, each producing a structured fix prompt. The run *should* fail here — there's no agent wired into the CLI path to act on the feedback (next section), and the repository genuinely doesn't pass lint. A harness that said anything else would be lying, and this series has had enough of pipelines that report "0 errors" while failing ([post 4](/blog/posts/agentic-software-engineering-verification.html) tells that story).

For the same reason, treasure the `SpecPrompt` field: during this session, reading assembled prompts is how the spec renderer's step-numbering bug was found. The harness making the prompt a first-class output is what made the bug findable.

## Where the Agent Actually Plugs In — Honest Wiring Diagram

This is the part earlier drafts of this series glossed over, so here it is precisely.

The harness defines the agent seam as a one-method interface:

```go
// AgentClient defines the interface for agent code generation
type AgentClient interface {
	Generate(ctx context.Context, prompt string) (string, error)
}
```

Any provider in `pkg/llm` (Anthropic, OpenAI, Ollama, any Chat-Completions server) satisfies it. But the two execution paths differ in what they do with it:

- **`asf harness run` (the CLI path)** assembles the prompt and runs the verification loop against the *working tree*. It does not call a model. It's the right tool for "does this repo pass, and what exactly would an agent be told?"
- **The factory path** ([post 10](/blog/posts/agentic-software-engineering-factory.html)) is where `Generate` is actually called: workers build the same spec+context prompt, invoke the LLM through a concurrency gate, and hand the output to an LLM judge with its own retry loop ([post 11](/blog/posts/agentic-software-engineering-ops.html)).

And the gap between them, stated plainly because the case study paid for the lesson: **the factory's generated artifacts are returned as task results, not written into a workspace and compiled**. The judge loop is wired; the compiler loop for artifacts is not — in the case study, extracting the artifact and running `go build` by hand is what caught a hallucinated API that the judge had praised. Wiring artifact extraction into this harness's verification loop is the system's single highest-leverage missing piece. The harness is where that belongs, which is exactly why the `ExecuteWithAgent` variant exists in the code today as a stub awaiting that plumbing.

## Configuration

The knobs are few and boring, which is a feature:

```go
func DefaultHarnessConfig() HarnessConfig {
	return HarnessConfig{
		WorkingDir:          ".",
		MaxRetries:          3,
		VerificationTimeout: 5 * time.Minute,
		ContextDirs:         []string{"docs", "specs", "internal", "pkg", "cmd"},
	}
}
```

`ContextDirs` deserves respect disproportionate to its size: it is the curation boundary from [post 2](/blog/posts/agentic-software-engineering-context.html). Every directory listed is a directory whose contents become instructions. Adding a path here is a context-engineering decision, not a config tweak.

## Why the Harness Earns Its Place

Without it, the three disciplines are advice; with it, they're enforced. The practical differences, from using it daily: context can't be forgotten, because loading isn't a step a human performs; specs can't drift from prompts, because the prompt is rendered from the spec at execution time; verification can't be skipped, because it's the harness's exit criterion; and every run leaves a `HarnessResult` that says what was known, what was asked, and what the toolchain concluded.

The next question is scale: one developer invoking `Execute` is a workflow, but a team needs this running continuously, surviving restarts, with queued work and observable state. That's the [factory orchestrator](/blog/posts/agentic-software-engineering-factory.html) — after a necessary detour through how much freedom the agent behind the harness should get: [autonomy calibration](/blog/posts/agentic-software-engineering-autonomy.html).

---

*All code and command output in this post is from the companion factory codebase (Go 1.23+) and real sessions against it.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-06
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-harness.html
Attribution: please link the canonical URL when citing or quoting this post.
