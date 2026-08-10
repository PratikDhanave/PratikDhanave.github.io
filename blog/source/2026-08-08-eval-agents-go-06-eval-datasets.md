# Building Eval Datasets from Real Traces

*Where good eval cases actually come from — seeding by hand, harvesting from production telemetry, and curating a golden dataset in Go that doesn't rot the moment your prompt changes.*

---

Earlier posts in this series built the machinery: a metric that scores the **trajectory** (did the agent call the right tools, in the right order, with the right arguments?) alongside one that scores the **final response**, and a Go harness that loads cases, runs them, and gates a merge on the aggregate. The machinery is the easy half. The hard half is the thing it consumes — the **dataset**. A perfect scorer over three toy cases tells you nothing; a mediocre scorer over a hundred *representative* cases tells you plenty.

Google's [ADK](https://adk.dev/evaluate/) frames an eval case the way we will: an **input**, an **expected tool trajectory**, and a **reference response** — grouped into *test files* (a single session) or *evalsets* (multiple, multi-turn sessions). ADK has no Go evaluation package, so we built our own schema in post 2. This post is about *filling it* — turning intent and real traffic into cases that are worth scoring.

---

## 1. Two sources: seeds you write, traces you harvest

Eval cases come from exactly two places, and a healthy dataset draws from both.

**Hand-written seed cases** come first, before the agent has ever seen a real user. You write them from the spec: for each thing the agent is *supposed* to do, one case that exercises it. Seeds are deliberate — you control the intent, you know the correct trajectory, and you can cover edge cases users haven't hit yet (the empty result, the ambiguous request, the input that should trigger a refusal). Their weakness is imagination: you only write cases for behavior you *thought of*.

**Harvested cases** come from production. Once the agent is live and instrumented, every real run is a candidate case — real phrasing, real ambiguity, the long tail you'd never have invented. You capture runs via telemetry, then **curate**: most traces are noise, a few are gold. Harvesting fixes the imagination problem but introduces a labelling problem — a captured run shows what the agent *did*, not what it *should* have done.

The two are complementary. Seeds give you coverage of intent; traces give you coverage of reality. Skip seeds and you're blind until launch; skip traces and your dataset slowly drifts away from how people actually use the thing.

---

## 2. The schema, restated

Post 2 defined the on-disk shape. Recapped here because everything below reads and writes it:

```go
package eval

// ToolCall is one step in a trajectory: a tool name plus the
// arguments it was invoked with. Args is decoded JSON so the
// scorer can compare structurally, not as raw text.
type ToolCall struct {
	Name string         `json:"name"`
	Args map[string]any `json:"args"`
}

// EvalCase is one scoreable unit: an input, the tool path we
// expect, and a reference answer. Metadata rides alongside so
// the dataset stays curatable — not just runnable.
type EvalCase struct {
	ID                 string     `json:"id"`
	Intent             string     `json:"intent"`             // coarse bucket, e.g. "refund_lookup"
	Input             string     `json:"input"`              // the user turn
	ExpectedTrajectory []ToolCall `json:"expected_trajectory"`
	ReferenceResponse  string     `json:"reference_response"`
	Tags               []string   `json:"tags,omitempty"`     // "edge-case", "harvested", ...
	Source             string     `json:"source"`             // "seed" | "trace:<run-id>"
	Reviewed           bool       `json:"reviewed"`           // a human signed off on the ground truth
}

// Dataset is the versioned collection the harness loads.
type Dataset struct {
	Name    string     `json:"name"`
	Version string     `json:"version"` // bump when cases change meaningfully
	Cases   []EvalCase `json:"cases"`
}
```

The fields beyond input/trajectory/response are what make a dataset *maintainable* rather than merely *runnable*. `Source` tells you where a case came from; `Reviewed` records whether a human has vouched for its ground truth; `Version` lets you say "these numbers were produced against dataset v4" and mean it.

---

## 3. Load and save

Nothing exotic — JSON on disk, one file per dataset. The only opinions worth encoding are **fail loudly on a malformed dataset** (a silently-skipped case is a silently-missing test) and **stable, sorted output** so a re-save produces a clean git diff.

```go
package eval

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

// Load reads a dataset and validates every case. A dataset that
// won't fully parse is a broken test suite, so we return the
// first structural problem rather than a partial set of cases.
func Load(path string) (*Dataset, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read dataset: %w", err)
	}
	var ds Dataset
	dec := json.NewDecoder(bytesReader(raw))
	dec.DisallowUnknownFields() // a typo'd field is a bug, not a shrug
	if err := dec.Decode(&ds); err != nil {
		return nil, fmt.Errorf("decode dataset: %w", err)
	}
	seen := map[string]bool{}
	for i, c := range ds.Cases {
		switch {
		case c.ID == "":
			return nil, fmt.Errorf("case %d: empty id", i)
		case seen[c.ID]:
			return nil, fmt.Errorf("case %q: duplicate id", c.ID)
		case c.Input == "":
			return nil, fmt.Errorf("case %q: empty input", c.ID)
		}
		seen[c.ID] = true
	}
	return &ds, nil
}

// Save writes the dataset with cases sorted by ID and indented,
// so re-saving after a curation edit yields a reviewable diff.
func Save(path string, ds *Dataset) error {
	sort.Slice(ds.Cases, func(i, j int) bool {
		return ds.Cases[i].ID < ds.Cases[j].ID
	})
	out, err := json.MarshalIndent(ds, "", "  ")
	if err != nil {
		return fmt.Errorf("encode dataset: %w", err)
	}
	return os.WriteFile(path, append(out, '\n'), 0o644)
}
```

`DisallowUnknownFields` earns its place: eval datasets are edited by hand, and a mistyped `refernce_response` that silently deserializes to an empty string would quietly weaken a test. Better to refuse to load.

---

## 4. From a captured trace to an EvalCase

This is the piece that makes harvesting practical. Your agent, when instrumented, emits a trace per run — the input it received, the sequence of tool calls it made, and the final text it returned. (In our harness those come off the same event stream the runner already exposes; the shape below is deliberately generic so it maps onto whatever telemetry you have — OpenTelemetry spans, a structured log, an ADK-style session record.)

```go
package eval

import (
	"fmt"
	"strings"
	"time"
)

// CapturedRun is the raw material: what the agent actually did on
// one real request. This is telemetry, not ground truth — the
// trajectory here is observed behavior, which may be wrong.
type CapturedRun struct {
	RunID     string     `json:"run_id"`
	Timestamp time.Time  `json:"timestamp"`
	Input     string     `json:"input"`
	ToolCalls []ToolCall `json:"tool_calls"`   // what it did
	Response  string     `json:"response"`     // what it said
}

// FromTrace converts an observed run into a *candidate* EvalCase.
// It pre-fills the expected trajectory and reference response with
// what the agent actually produced — a starting point a human then
// corrects. Reviewed is false by design: nothing here is ground
// truth until a person says so.
func FromTrace(run CapturedRun, intent string) EvalCase {
	return EvalCase{
		ID:                 slugify(intent) + "-" + shortID(run.RunID),
		Intent:             intent,
		Input:              run.Input,
		ExpectedTrajectory: run.ToolCalls, // observed != expected, yet
		ReferenceResponse:  run.Response,  // draft answer to be edited
		Tags:               []string{"harvested"},
		Source:             "trace:" + run.RunID,
		Reviewed:           false,
	}
}
```

The critical line is the comment on `Reviewed`. `FromTrace` seeds the expected trajectory and reference response with **what the agent did** — but that is exactly the thing under test, so it cannot double as the answer key. The converter's job is to save a human the transcription, not the judgement. A curator then does three things:

1. **Confirms or edits the trajectory.** Did the agent call the right tools? Delete the spurious call it made; add the one it skipped. This edited trajectory becomes the ground truth the scorer measures future runs against.
2. **Rewrites the reference response** into what a *good* answer looks like — not necessarily the exact words the agent produced.
3. **Flips `Reviewed` to true**, which is the gate that lets the case into the scored set.

Wiring that into the harness is a filter:

```go
// ReviewedOnly returns the subset a human has vouched for. The
// harness scores these; unreviewed harvested candidates sit in the
// dataset as a to-do queue, never affecting the gate.
func (ds *Dataset) ReviewedOnly() []EvalCase {
	out := make([]EvalCase, 0, len(ds.Cases))
	for _, c := range ds.Cases {
		if c.Reviewed {
			out = append(out, c)
		}
	}
	return out
}
```

Unreviewed candidates aren't discarded — they live in the dataset as a backlog. You harvest in bulk, then curate at leisure; only reviewed cases move the number that gates the build.

---

## 5. Dataset hygiene

A pile of cases is not a dataset. Five habits separate a suite you trust from one you tolerate.

**Cover intents, not just volume.** Group cases by `Intent` and make sure every intent the agent supports has cases — and that at least one is an edge case: the empty result, the malformed input, the request that *should* be refused. A quick coverage report catches the gap:

```go
// IntentCoverage counts reviewed cases per intent so you can see
// which behaviors are under-tested at a glance.
func (ds *Dataset) IntentCoverage() map[string]int {
	cov := map[string]int{}
	for _, c := range ds.ReviewedOnly() {
		cov[c.Intent]++
	}
	return cov
}
```

An intent sitting at zero (or one) is a blind spot, and this is how you find it before production does.

**Small but representative beats large but redundant.** Two hundred near-identical "look up order #N" cases inflate runtime and confidence equally falsely. Deduplicate aggressively — one canonical case per behavior, plus its edge variants. A tight dataset that runs in seconds gets run on every commit; a bloated one that takes ten minutes gets skipped.

**Avoid leakage.** If your prompt engineering starts *targeting* specific eval inputs — tweaking instructions until case #37 passes — the dataset stops measuring generalization and starts measuring memorization. Keep a slice of cases as a hold-out you don't look at while iterating, and check it only occasionally. When hold-out and working scores diverge, you've been overfitting.

**Version the dataset.** Bump `Dataset.Version` whenever cases change meaningfully, and record which version produced a given score. "We went from 0.82 to 0.91" is meaningless if the dataset also changed underneath; "0.82 → 0.91 on dataset v4" is a real result.

**Keep provenance.** `Source` and `Reviewed` are what let you audit the suite a year later — which cases are hand-written spec coverage, which are harvested from real incidents, and who vouched for each. A dataset you can't audit is one you'll eventually stop trusting.

---

## 6. The golden-dataset maintenance problem

Here's the trap that catches teams late. You build a good dataset, it gates your builds, everyone's happy — and then the agent changes. You add a tool, split one into two, reword the system prompt so the model now (correctly) takes a different path. Suddenly cases start failing not because the agent got *worse* but because the *ground truth is stale*.

The wrong reaction is to freeze the dataset and treat every failure as a regression. The right reaction is to treat the golden dataset as **living**: when the agent's correct behavior legitimately changes, the expected trajectories must change with it. That's a curation task, not a rubber stamp — for each newly-failing case, a human decides "the agent is wrong, this is a real regression" or "the agent is right, the answer key is out of date," and updates the trajectory in the second case.

The tooling that makes this bearable is a **diff against the current dataset**: run the agent, compare each observed trajectory to the stored expectation, and surface only the mismatches for review.

```go
// Drift is one case whose observed behavior no longer matches the
// stored ground truth — the review queue for dataset maintenance.
type Drift struct {
	CaseID   string
	Expected []ToolCall
	Observed []ToolCall
}

// FindDrift re-runs each reviewed case and reports where observed
// trajectories diverge from the answer key. A human triages each:
// real regression, or stale ground truth to refresh via FromTrace.
func FindDrift(ds *Dataset, run func(input string) CapturedRun) []Drift {
	var drifts []Drift
	for _, c := range ds.ReviewedOnly() {
		got := run(c.Input)
		if !trajectoryEqual(c.ExpectedTrajectory, got.ToolCalls) {
			drifts = append(drifts, Drift{
				CaseID:   c.ID,
				Expected: c.ExpectedTrajectory,
				Observed: got.ToolCalls,
			})
		}
	}
	return drifts
}
```

Note the symmetry: `FindDrift` surfaces the mismatch, and `FromTrace` is exactly the tool for refreshing the ones that turn out to be stale — the same converter that harvests new cases also re-baselines old ones. Curate, don't freeze. A frozen golden dataset gives you a green build and a false sense of safety; a curated one keeps measuring the thing you actually care about as that thing evolves.

---

## Key takeaways

- **Two sources, both needed.** Hand-written seeds cover the intents you designed for; harvested traces cover the reality you didn't imagine. A dataset from only one is half-blind.
- **A trace is a candidate, not a case.** `FromTrace` transcribes what the agent *did* to save typing — but observed behavior is the thing under test, so a human must set the expected trajectory and reference answer before it becomes ground truth. `Reviewed` is that gate.
- **Hygiene is coverage + restraint.** Cover every intent (especially edge cases), keep it small and non-redundant, hold out a slice to catch leakage, and version the whole thing so scores are comparable.
- **Golden datasets are living.** When the agent's correct behavior changes, the answer key must change with it. Diff observed against expected, triage the drift, and re-baseline the stale cases — don't freeze the dataset and mistake staleness for regression.

The scorer is arithmetic; the dataset is judgement. Invest there.

---

## Further reading

- [ADK — Evaluate agents](https://adk.dev/evaluate/) — the test-file vs. evalset model and the input / expected-trajectory / reference-response case shape this post's Go schema mirrors.
