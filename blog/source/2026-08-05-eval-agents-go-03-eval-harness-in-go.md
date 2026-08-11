# Building an Evaluation Harness in Go

*The core of the series: a minimal, original evaluation harness in Go. Run an agent under test through adk-go's runner, capture the tool-call trajectory and the final response behind an adapter you own, and score them with `go test`.*

---

The first two posts in this series set up the *why* and the *what*. Post one argued that an agent's answer is a measurement, not an assertion — a plausible final response can hide a completely wrong sequence of actions, so you score two axes: the **trajectory** (did it call the right tools, in the right order?) and the **final response** (is the answer close enough to a reference?). Post two turned that into data structures — an `EvalCase` that pins a query to its expected tool path and reference answer.

This post builds the machine that runs those cases. Google's [ADK](https://adk.dev/) ships a full evaluation package for Python; the Go SDK, `google.golang.org/adk/v2`, does **not** — there is `agent`, `runner`, `tool`, `session`, and `telemetry`, but no `eval`. That gap is the whole reason this post exists. We are going to build the harness ourselves, and the interesting engineering is not the scoring math (that's a dozen lines) — it's the **seam** that keeps our scoring code from ever importing an adk-go type. Get that seam right and the harness outlives any SDK churn.

## The one design decision that matters

An agent run, mechanically, is a stream of events. adk-go's runner executes an agent and yields those events — tool calls the model requested, tool results, intermediate messages, and eventually a final response. To score a run we need exactly two things out of that stream: the **ordered list of tool names** the agent called, and the **text of its final answer**. Nothing else.

So the design writes itself. Define a tiny value type holding those two things, define an interface that produces it, and make the scorer depend only on the value type. Everything that knows about adk-go's event shapes lives behind the interface. The scorer never sees a `runner`, an `Event`, or a `Session`.

```go
// Capture is everything the scorer needs from a single run: the ordered tool
// names the agent called, and the text of its final response. Deliberately
// tiny — it is the contract between "run the agent" and "score the run".
type Capture struct {
	ToolCalls []string // tool names, in call order
	FinalText string   // the agent's final response text
}

// AgentUnderTest is the seam. The harness drives this interface and nothing
// else. Any implementation — a real adk-go agent, a recorded fixture, an
// in-memory stub — is interchangeable because the harness only ever sees a
// Capture coming back.
type AgentUnderTest interface {
	Run(ctx context.Context, query string) (Capture, error)
}
```

Read that `AgentUnderTest` interface as a promise: *give me a query, hand me back what happened, in terms I already understand.* The moment your metrics code depends on `Capture` instead of on adk-go, three things become true at once. You can unit-test the scorer with hand-written captures and no network. You can swap the model provider without touching a line of scoring. And when adk-go renames an event field — SDKs do — the blast radius is one file.

## Recap: the EvalCase from post two

The harness consumes the `EvalCase` we defined earlier. Reproduced here so this post stands alone:

```go
// EvalCase pins a single scenario: the input, the tool path we expect the
// agent to take, and a reference answer to compare the final text against.
type EvalCase struct {
	Name          string   // human label, used as the subtest name
	Query         string   // the user input handed to the agent
	ExpectedTools []string // expected tool-call trajectory, by name and order
	Reference     string   // reference final answer for response matching
}
```

Cases are just data. Define them as a Go slice for a small suite, or unmarshal them from JSON when the set grows and non-engineers start contributing scenarios — the harness doesn't care which, because it only ever receives `[]EvalCase`.

## Wiring adk-go behind the seam

Here is the concrete adapter that satisfies `AgentUnderTest` by driving adk-go's runner. This is the *only* code in the project that knows adk-go's event model exists.

```go
// adkAgent adapts an adk-go runner+agent to the AgentUnderTest interface.
// It is the single point of contact with the SDK.
type adkAgent struct {
	run runFunc // injected: executes one turn and returns the event stream
}

// runFunc is a thin alias over adk-go's runner call. Following adk-go's
// runner API, a runner executes an agent for an input and yields a sequence
// of events; we collect them for one turn. Keeping this a function value
// makes adkAgent trivial to construct in tests.
type runFunc func(ctx context.Context, query string) ([]event, error)

func (a *adkAgent) Run(ctx context.Context, query string) (Capture, error) {
	events, err := a.run(ctx, query)
	if err != nil {
		return Capture{}, fmt.Errorf("agent run: %w", err)
	}
	var capture Capture
	for _, ev := range events {
		if name, ok := toolCallName(ev); ok {
			capture.ToolCalls = append(capture.ToolCalls, name)
		}
		if text, ok := finalText(ev); ok {
			capture.FinalText = text // last final-response event wins
		}
	}
	return capture, nil
}
```

Two helpers, `toolCallName` and `finalText`, do the actual translation from an adk-go event to our terms. They are the entire coupling to the SDK's event shapes:

```go
// toolCallName reports whether ev represents a tool call and, if so, its name.
// finalText reports whether ev carries final-response text.
//
// These two functions are the boundary. Their bodies inspect adk-go's concrete
// event types (a tool-call event vs. a final-response event); the exact field
// access follows adk-go's runner/event API and is the only thing you rewrite
// if that API moves. Everything upstream speaks Capture, not adk-go.
func toolCallName(ev event) (string, bool) {
	if ev.kind == kindToolCall {
		return ev.tool, true
	}
	return "", false
}

func finalText(ev event) (string, bool) {
	if ev.kind == kindFinalResponse {
		return ev.text, true
	}
	return "", false
}
```

I am deliberately not asserting the precise names of adk-go's event fields here — `event`, `kind`, `tool`, and `text` above stand in for whatever the SDK exposes, and this is the file where you bind them to the real types. That is the point of the seam: this illustrative shape is quarantined in one place, and the scorer below has no idea it exists. If you're unsure of an exact signature while wiring the real SDK, keep this adapter minimal and let the compiler guide the field access — the rest of the harness compiles and tests independently of it.

## The scorer, in terms of Capture only

Now the metrics. These are pure functions over strings and slices — no context, no SDK, no I/O — which is exactly why they're trivial to test. Two axes, two functions.

```go
// trajectoryScore is the fraction of positions where the actual tool call
// matches the expected one, dividing by the longer sequence so that spurious
// extra calls are penalized too. A perfect path scores 1.0.
func trajectoryScore(expected, actual []string) float64 {
	if len(expected) == 0 && len(actual) == 0 {
		return 1.0 // "no tools" is the correct trajectory for a plain Q&A
	}
	if len(expected) == 0 {
		return 0.0 // we expected silence; the agent acted anyway
	}
	matches := 0
	for i, want := range expected {
		if i < len(actual) && actual[i] == want {
			matches++
		}
	}
	denom := len(expected)
	if len(actual) > denom {
		denom = len(actual) // an extra unnecessary call drags the score down
	}
	return float64(matches) / float64(denom)
}

// responseMatchScore is unigram recall: the fraction of the reference's tokens
// that appear anywhere in the actual answer. Lenient on purpose — wording
// varies, so we measure overlap, not equality.
func responseMatchScore(reference, actual string) float64 {
	ref := tokenize(reference)
	if len(ref) == 0 {
		return 1.0 // nothing to match against
	}
	got := make(map[string]struct{})
	for _, t := range tokenize(actual) {
		got[t] = struct{}{}
	}
	hits := 0
	for _, t := range ref {
		if _, ok := got[t]; ok {
			hits++
		}
	}
	return float64(hits) / float64(len(ref))
}

// tokenize lowercases and splits on any non-alphanumeric run.
func tokenize(s string) []string {
	return strings.FieldsFunc(strings.ToLower(s), func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsNumber(r)
	})
}
```

The trajectory metric is the strict one — a single wrong tool call is a real defect even when the answer reads fine, so in practice you gate it at an exact `1.0`. The response metric is deliberately forgiving; unigram recall around `0.7` catches "the answer drifted off-topic" without failing on paraphrase. Note that `responseMatchScore` here is a deliberately simplified recall-only stand-in for ADK's `response_match_score`, which is ROUGE-1 F1 (balancing precision and recall) — post 5 implements that fully. Both are simple enough to reason about at a glance, which matters: a scoring function nobody understands is a scoring function nobody trusts.

## A Result type and the evaluate step

One case in, one `Result` out. The `Result` carries both raw scores plus a pass/fail verdict against thresholds, and it never throws away the numbers — you want the scores in the report even when a case passes, so you can watch a metric erode *before* it crosses the line.

```go
// Thresholds is the bar each axis must clear for a case to pass.
type Thresholds struct {
	Trajectory float64 // typically 1.0 — exact tool path
	Response   float64 // typically 0.7 — unigram overlap
}

// Result is the outcome of scoring one EvalCase.
type Result struct {
	Case            string
	TrajectoryScore float64
	ResponseScore   float64
	Passed          bool
	Err             error // non-nil if the run itself failed
}

// Evaluate runs one case through the agent and scores it. A run error is
// captured on the Result (Passed stays false) rather than panicking, so one
// flaky case can't sink the whole suite report.
func Evaluate(ctx context.Context, agent AgentUnderTest, c EvalCase, th Thresholds) Result {
	capture, err := agent.Run(ctx, c.Query)
	if err != nil {
		return Result{Case: c.Name, Err: err}
	}
	ts := trajectoryScore(c.ExpectedTools, capture.ToolCalls)
	rs := responseMatchScore(c.Reference, capture.FinalText)
	return Result{
		Case:            c.Name,
		TrajectoryScore: ts,
		ResponseScore:   rs,
		Passed:          ts >= th.Trajectory && rs >= th.Response,
	}
}
```

## Go's testing package *is* the runner

There is a temptation to build a bespoke suite runner — a loop, a progress bar, colored output. Resist it. Go already ships a parallel, filterable, reportable test runner, and an eval suite is a table-driven test in every respect. Wiring the harness into `testing` means `go test ./eval/...` gives you per-case pass/fail, `-run` filtering to a single scenario, `-v` for detail, and CI integration for free.

```go
func TestAgentEval(t *testing.T) {
	th := Thresholds{Trajectory: 1.0, Response: 0.7}
	agent := newAgentUnderTest(t) // constructs the adk-go adapter (or a stub)
	cases := loadCases(t)         // slice literal or JSON — harness is agnostic

	for _, c := range cases {
		c := c // capture range var (pre-1.22 safety; harmless after)
		t.Run(c.Name, func(t *testing.T) {
			t.Parallel()
			r := Evaluate(context.Background(), agent, c, th)
			if r.Err != nil {
				t.Fatalf("run failed: %v", r.Err)
			}
			if !r.Passed {
				t.Errorf("regressed: trajectory=%.2f (need >=%.2f), response=%.2f (need >=%.2f)",
					r.TrajectoryScore, th.Trajectory, r.ResponseScore, th.Response)
			}
		})
	}
}
```

Because the harness depends on the `AgentUnderTest` interface, `newAgentUnderTest` can return a real adk-go adapter when credentials are present and a recorded stub otherwise. That's what keeps the suite runnable offline in CI — a stub that replays a fixed `Capture` per query needs no model, no network, no keys:

```go
// stubAgent replays canned captures — the entire adk-go dependency vanishes.
type stubAgent struct{ byQuery map[string]Capture }

func (s *stubAgent) Run(_ context.Context, query string) (Capture, error) {
	c, ok := s.byQuery[query]
	if !ok {
		return Capture{}, fmt.Errorf("no fixture for query %q", query)
	}
	return c, nil
}
```

That eight-line stub is the seam paying rent. The scoring functions, the `Evaluate` step, the whole table-driven driver — every part of that runs against `stubAgent` with zero SDK involvement.

## A summary report

Per-case red/green from `go test` is enough to *gate* a merge, but you also want the shape of the run at a glance — how many passed, and where the averages sit. Aggregate `[]Result` into a `Summary` and render it with `text/tabwriter`.

```go
type Summary struct {
	Total, Passed           int
	AvgTrajectory, AvgResp  float64
}

func Summarize(results []Result) Summary {
	s := Summary{Total: len(results)}
	for _, r := range results {
		if r.Passed {
			s.Passed++
		}
		s.AvgTrajectory += r.TrajectoryScore
		s.AvgResp += r.ResponseScore
	}
	if n := float64(len(results)); n > 0 {
		s.AvgTrajectory /= n
		s.AvgResp /= n
	}
	return s
}

// Report writes a per-case table plus a summary line.
func Report(w io.Writer, results []Result) {
	tw := tabwriter.NewWriter(w, 0, 4, 2, ' ', 0)
	fmt.Fprintln(tw, "CASE\tTRAJECTORY\tRESPONSE\tVERDICT")
	for _, r := range results {
		verdict := "PASS"
		if !r.Passed {
			verdict = "FAIL"
		}
		fmt.Fprintf(tw, "%s\t%.2f\t%.2f\t%s\n",
			r.Case, r.TrajectoryScore, r.ResponseScore, verdict)
	}
	tw.Flush()
	s := Summarize(results)
	fmt.Fprintf(w, "\n%d/%d passed  avg-trajectory=%.2f  avg-response=%.2f\n",
		s.Passed, s.Total, s.AvgTrajectory, s.AvgResp)
}
```

Call `Report` from a `TestMain` that collects results across cases, or from a small `cmd/eval` binary for a standalone run outside `go test`. Either way the output is a stable, diffable table — and a diffable table is exactly what a baseline gate (a later post) wants to compare against.

## Why the seam is the whole point

Step back and look at the dependency arrows. `Capture`, `EvalCase`, `Result`, the scorer, the driver, the report — none of them import adk-go. Exactly one type, `adkAgent`, does, and it implements a four-line interface. That inversion is what makes the harness durable:

- **The scorer is unit-testable in isolation.** Feed `trajectoryScore` two slices and assert a float. No mocks, no context, no SDK.
- **The suite runs offline.** A stub `AgentUnderTest` replays fixtures, so CI never needs a live model to catch a scoring regression.
- **SDK churn is contained.** When adk-go's event model shifts, you edit `toolCallName` and `finalText` and recompile. The metrics don't move.
- **The model is swappable.** Point the adapter at a different provider or agent and every case still scores identically, because scoring never knew which agent produced the `Capture`.

adk-go giving you no `eval` package is, oddly, a gift — it forces you to own the boundary instead of coupling to someone else's event types. The harness here is maybe 150 lines, and it's *yours*: small enough to read in one sitting, decoupled enough to survive the SDK it runs on.

## Key takeaways

- **Score two axes, capture two things.** Everything the scorer needs is an ordered list of tool names and the final text — model the run as a `Capture` and stop there.
- **The interface is the architecture.** `AgentUnderTest` is a four-line seam; put every adk-go type behind it and the rest of the harness never imports the SDK.
- **`testing` is your suite runner.** Table-driven subtests give you filtering, parallelism, and CI integration for free — don't rebuild them.
- **Keep the metrics dumb and pure.** Trajectory is strict (exact path), response is lenient (unigram overlap); both are pure functions you can test without a model.
- **A stub agent makes the suite run offline.** The same seam that decouples you from adk-go lets CI score regressions with zero credentials.

The next post takes these `Result`s and turns them into a committed baseline plus a gate that fails the build on regression — quality as a first-class CI citizen.

## Further reading

- [ADK evaluation documentation](https://adk.dev/evaluate/) — the two-metric model this harness reimplements in Go.
- [adk-go on GitHub](https://github.com/google/adk-go) — the `agent`, `runner`, `tool`, `session`, and `telemetry` packages the adapter wraps.
