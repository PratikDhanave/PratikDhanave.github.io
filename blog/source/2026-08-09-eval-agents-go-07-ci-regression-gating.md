# Agent Evaluation in CI: Regression Gating

*How to wire agent evaluations into continuous integration in Go — running a slow, model-calling eval harness under `go test`, setting per-metric thresholds that fail the build on a regression, and living honestly with the fact that these gates are softer than unit tests.*

---

A unit test is a contract: given this input, the function must return exactly that output, forever. Agent evaluations are not contracts — they are measurements. An eval run tells you *how well* an agent did on a dataset, expressed as a score between 0 and 1, and that score wobbles from run to run because a language model sits in the middle of it. The job of CI is to catch the moment a change makes the agent measurably *worse* — a regression — without drowning you in false alarms every time the model phrases an answer differently.

This post is about that wiring. We are building on the [Agent Development Kit for Go](https://adk.dev/) (`google.golang.org/adk/v2`), which gives us agents and runners but, unlike its Python sibling, ships **no evaluation package** — so we build the harness ourselves and run it under `go test`. The Python ADK docs describe [running evals in CI](https://adk.dev/evaluate/) with pytest and configurable thresholds; the shape of that idea ports cleanly to Go, and Go's build tags and testing tooling make some of it nicer.

---

## 1. Two kinds of tests, one command

The first design decision is separation. Your unit tests are fast, deterministic, and offline. Your eval tests are slow, non-deterministic, and call a real model over the network. You do **not** want `go test ./...` on every save to spend two minutes and real API credits scoring an agent. But you also want the eval harness to be *real Go tests* so they run under the same tooling, produce the same output, and gate the same pipeline.

Go's build tags give a clean split. Put eval tests behind a tag so they compile only when asked:

```go
//go:build eval

package eval

import (
	"os"
	"testing"
)

// requireLive skips unless the eval environment is actually configured,
// so `go test -tags eval` degrades gracefully on a machine without creds.
func requireLive(t *testing.T) {
	t.Helper()
	if os.Getenv("ADK_EVAL_LIVE") == "" {
		t.Skip("set ADK_EVAL_LIVE=1 and model credentials to run eval tests")
	}
}
```

Now the two worlds never collide:

```bash
go test ./...              # unit tests only — the //go:build eval files don't compile
go test -tags eval ./eval  # eval harness — slow, calls the model
```

I use a build tag *and* an env-var guard on purpose. The tag keeps eval code out of the normal compile so a missing model dependency never breaks `go test ./...`. The env flag lets the same tagged binary run in "collect but skip" mode on a laptop without credentials — the test is discovered, reported as skipped, and never charges you. This mirrors the ADK convention where live-model tests skip by default unless credentials and a flag are present.

---

## 2. A minimal eval harness

Since there is no ADK eval package, define the shapes you need. A **case** is an input plus whatever you assert about the agent's behavior; a **metric** turns one agent run into a score in `[0,1]`; a **result** carries the score back for gating.

```go
//go:build eval

package eval

import "context"

// Case is one row of the eval dataset.
type Case struct {
	Name          string
	Prompt        string
	ExpectedTools []string // trajectory: tools we expect to be invoked, in order
	Reference     string   // reference answer for response-quality scoring
}

// Trace is what one agent run produced, captured by the runner.
type Trace struct {
	FinalText  string
	ToolCalls  []string
}

// Metric scores a single trace against its case. 1.0 is perfect, 0.0 is failure.
type Metric interface {
	Name() string
	Score(ctx context.Context, c Case, tr Trace) (float64, error)
}
```

Two metrics carry most of the weight in practice. **Trajectory match** checks *which tools the agent called* — this is stable because it doesn't depend on prose. **Response quality** scores the final answer against a reference, which is inherently fuzzier.

```go
//go:build eval

package eval

import (
	"context"
	"strings"
)

// ToolTrajectory scores the fraction of expected tool calls that appear
// in the right order. Order-preserving, so a reversed call sequence scores low.
type ToolTrajectory struct{}

func (ToolTrajectory) Name() string { return "tool_trajectory" }

func (ToolTrajectory) Score(_ context.Context, c Case, tr Trace) (float64, error) {
	if len(c.ExpectedTools) == 0 {
		return 1.0, nil // nothing expected, nothing to miss
	}
	matched, j := 0, 0
	for _, want := range c.ExpectedTools {
		for j < len(tr.ToolCalls) {
			if tr.ToolCalls[j] == want {
				matched++
				j++
				break
			}
			j++
		}
	}
	return float64(matched) / float64(len(c.ExpectedTools)), nil
}

// ResponseContains is a cheap deterministic quality proxy: does the answer
// mention every required token? A stand-in for a heavier LLM-judge metric.
type ResponseContains struct{}

func (ResponseContains) Name() string { return "response_match" }

func (ResponseContains) Score(_ context.Context, c Case, tr Trace) (float64, error) {
	need := strings.Fields(strings.ToLower(c.Reference))
	if len(need) == 0 {
		return 1.0, nil
	}
	got := strings.ToLower(tr.FinalText)
	hit := 0
	for _, w := range need {
		if strings.Contains(got, w) {
			hit++
		}
	}
	return float64(hit) / float64(need), nil
}
```

A real deployment would swap `ResponseContains` for an LLM-as-judge metric. The interface is the point: the harness gates on numbers, and it does not care whether a number came from string matching or from a judge model.

---

## 3. The regression gate: thresholds that fail the build

A gate is just a table of per-metric floors and a test that fails when the *aggregate* score for a metric drops below its floor. Keeping thresholds in one place — not scattered across assertions — means you tune the strictness of the whole suite by editing one map.

```go
//go:build eval

package eval

// Thresholds are the per-metric floors the aggregate score must clear.
// Trajectory is held to a higher bar because it's more stable than prose.
var Thresholds = map[string]float64{
	"tool_trajectory": 0.90,
	"response_match":  0.70,
}
```

The gating test loads the dataset, runs every case through the agent, averages each metric across the dataset, and compares against the floor:

```go
//go:build eval

package eval

import (
	"context"
	"testing"
)

func TestEvalGate(t *testing.T) {
	requireLive(t)

	cases := LoadDataset(t) // reads testdata/*.json; sampled on PRs (see §5)
	metrics := []Metric{ToolTrajectory{}, ResponseContains{}}
	ctx := context.Background()

	// sums[metric] accumulates scores across the dataset.
	sums := map[string]float64{}

	for _, c := range cases {
		tr := RunAgent(ctx, t, c.Prompt) // one live agent invocation → Trace
		for _, m := range metrics {
			s, err := m.Score(ctx, c, tr)
			if err != nil {
				t.Fatalf("metric %s on case %q: %v", m.Name(), c.Name, err)
			}
			sums[m.Name()] += s
		}
	}

	n := float64(len(cases))
	for _, m := range metrics {
		avg := sums[m.Name()] / n
		floor := Thresholds[m.Name()]
		delta := avg - floor
		t.Logf("%-16s avg=%.3f floor=%.3f delta=%+.3f", m.Name(), avg, floor, delta)
		if avg < floor {
			t.Errorf("REGRESSION: %s scored %.3f, below floor %.3f", m.Name(), avg, floor)
		}
	}
}
```

That `t.Errorf` is the whole game: a non-zero exit code from `go test` fails the CI job. No special reporting infrastructure required — the same mechanism that fails a unit test fails an eval regression.

---

## 4. The non-determinism problem

Here is where agent evals stop resembling unit tests. Run the suite twice and the scores differ, because the model samples differently each time. If your floor sits right at the average score, a normal run-to-run wobble will flip the build red for no real reason. Flaky gates get ignored, and an ignored gate is worse than no gate. Four mitigations, roughly in order of how much I reach for them:

**Pin what you can.** Set temperature to 0 and a fixed seed if the provider honors one. This removes sampling variance for the parts of the pipeline that support it. It does not make the model fully deterministic — providers rarely guarantee bit-identical output — but it collapses most of the noise.

```go
// When constructing the model/agent for evals, kill sampling variance.
cfg := ModelConfig{Temperature: 0, Seed: 42}
```

**Run each case a few times and average.** Scoring a case three times and taking the mean shrinks the variance of the *reported* number, so the floor comparison is against a steadier signal. It costs 3× the calls, which is why you reserve it for the nightly full run, not PRs.

```go
func meanScore(runs int, score func() float64) float64 {
	total := 0.0
	for i := 0; i < runs; i++ {
		total += score()
	}
	return total / float64(runs)
}
```

**Gate with tolerance bands, not knife-edges.** Instead of failing the instant the average dips below the floor, fail only when it drops **more than a tolerance** below a stored *baseline* from the last known-good run. Small dips are noise; a drop past the band is a signal.

```go
// baseline["tool_trajectory"] = 0.94 from the last green main build.
const tolerance = 0.03
if avg < baseline[name]-tolerance {
	t.Errorf("REGRESSION: %s fell from baseline %.3f to %.3f (>%.2f band)",
		name, baseline[name], avg, tolerance)
}
```

**Prefer trajectory over prose for hard gates.** Trajectory metrics — did the agent call the right tools, in the right order — barely move between runs, because tool selection is far more stable than free-text wording. That is why the threshold table holds trajectory to `0.90` but response quality to `0.70`. When you want a gate strict enough to *block a merge*, gate on trajectory; treat response-quality scores as a trend you watch, not a wall you enforce.

Caching is the fifth lever and the sharpest double-edged one: record model responses for a fixed dataset and replay them, and the eval becomes deterministic and free. But a cached eval no longer tests the live model — it tests your recording. Use caching for the *plumbing* tests (does the harness parse tool calls correctly?) and keep at least one un-cached live run so a real model regression can't hide behind a stale cassette.

---

## 5. Cost and time: sample on PRs, full suite nightly

Live evals cost money and minutes. A 200-case dataset scored three times each is 600 model calls per run — fine once a night, painful on every push to a busy PR. Split the schedule by how much signal you need versus how fast you need it.

On a pull request, run a **deterministic sample** of the dataset — enough to catch an obvious regression quickly and cheaply. Nightly (or on merge to `main`), run the **full** dataset with multi-run averaging for a trustworthy baseline.

```go
//go:build eval

package eval

import (
	"os"
	"sort"
	"strconv"
	"testing"
)

// LoadDataset returns the full set, or a stable sample when ADK_EVAL_SAMPLE is set.
// Sampling is deterministic (sort then stride) so the same cases run every PR —
// a random sample would make PR scores jitter for a second, avoidable reason.
func LoadDataset(t *testing.T) []Case {
	all := readAllCases(t) // your testdata loader
	sample := os.Getenv("ADK_EVAL_SAMPLE")
	if sample == "" {
		return all
	}
	k, err := strconv.Atoi(sample)
	if err != nil || k <= 0 || k >= len(all) {
		return all
	}
	sort.Slice(all, func(i, j int) bool { return all[i].Name < all[j].Name })
	stride := len(all) / k
	out := make([]Case, 0, k)
	for i := 0; i < len(all) && len(out) < k; i += stride {
		out = append(out, all[i])
	}
	return out
}
```

The knob — `ADK_EVAL_SAMPLE=20` on PRs, unset nightly — keeps one code path for both schedules. Cheap, fast feedback on every PR; the expensive, authoritative measurement runs while you sleep.

---

## 6. Reporting: deltas and artifacts

A red build that just says "response_match scored 0.62" sends someone digging. Report the *delta against baseline* and save the per-case scores as a build artifact so the failure explains itself. The gating test already logs deltas via `t.Logf`; write the machine-readable version too:

```go
//go:build eval

package eval

import (
	"encoding/json"
	"os"
)

type Report struct {
	Metric   string  `json:"metric"`
	Average  float64 `json:"average"`
	Baseline float64 `json:"baseline"`
	Delta    float64 `json:"delta"`
	Floor    float64 `json:"floor"`
	Passed   bool    `json:"passed"`
}

func WriteReport(path string, rows []Report) error {
	b, err := json.MarshalIndent(rows, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o644)
}
```

Upload `eval-report.json` from the job and the reviewer sees exactly which metric moved, by how much, and against what baseline — without re-running anything.

---

## 7. Wiring it into GitHub Actions

Two triggers, one workflow. The PR job runs a sampled, fast gate; the nightly job runs the full suite and refreshes the baseline. Secrets carry the model credentials so `requireLive` doesn't skip.

```yaml
name: agent-eval

on:
  pull_request:
  schedule:
    - cron: "0 3 * * *"   # 03:00 UTC nightly, full suite

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.23"

      # Fast, sampled gate on PRs; full suite on the nightly schedule.
      - name: Run agent evals
        env:
          ADK_EVAL_LIVE: "1"
          MODEL_API_KEY: ${{ secrets.MODEL_API_KEY }}
          ADK_EVAL_SAMPLE: ${{ github.event_name == 'pull_request' && '20' || '' }}
        run: go test -tags eval -timeout 20m ./eval -run TestEvalGate

      - name: Upload eval report
        if: always()   # keep the artifact even when the gate fails
        uses: actions/upload-artifact@v4
        with:
          name: eval-report
          path: eval-report.json
```

`if: always()` on the upload matters: the artifact is most useful precisely when the gate failed. The `-timeout 20m` guards against a hung model call turning into a stuck runner.

---

## 8. The honest caveat

Agent eval gates are softer than unit tests, and pretending otherwise will burn you. A unit test that goes red means the code is wrong. An eval gate that goes red means the *measured behavior moved past a threshold you chose* — which might be a real regression, or a noisy sample, or a model provider quietly changing a checkpoint under you, or a reference answer that was always a little too strict. Treat a red eval as *a reason to look*, not proof of a bug.

That has practical consequences for how you run these gates:

- **Make eval failures reviewable, not merge-blocking on day one.** Start with the gate reporting a status and requiring a human glance; promote it to a hard block only for the metrics you trust — usually trajectory, rarely raw prose quality.
- **Version your baselines and thresholds in the repo.** When you deliberately change the agent and scores shift, you *update the baseline in the same PR*, so the diff records that the bar moved on purpose.
- **Watch trends, not single runs.** One dip is noise; three runs sliding the same direction is a regression. The nightly report is where you see the trend.

The payoff is real despite the softness: a change that drops tool-trajectory accuracy from 0.94 to 0.71 will light up the gate immediately, and that is exactly the class of regression that silently ships without one. You are not trying to freeze the agent's behavior — you are trying to notice when it gets worse before your users do.

---

## Key takeaways

- **Separate eval tests from unit tests** with a `//go:build eval` tag plus an env-flag guard, so `go test ./...` stays fast and free while `go test -tags eval` runs the live harness.
- **Build the harness yourself** — adk-go ships no eval package. A `Metric` interface scoring a `Trace` into `[0,1]` is enough to gate on.
- **Gate on aggregate scores against per-metric floors**; a `t.Errorf` fails the build like any other test.
- **Tame non-determinism** with temperature 0 / fixed seeds, multi-run averaging, tolerance bands against a baseline, and by holding hard gates to *trajectory* rather than prose.
- **Split the schedule:** a deterministic sample on PRs for speed, the full dataset nightly for an authoritative baseline — one env knob, one code path.
- **Report deltas and save artifacts** so a red build explains itself.
- **Accept that eval gates are softer than unit tests.** Start advisory, promote the metrics you trust to blocking, version baselines and thresholds in the repo, and watch trends over single runs.
