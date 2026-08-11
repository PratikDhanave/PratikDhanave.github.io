# The ADK Evaluation Model

*Before you can evaluate an agent in Go, you need a mental model of what "evaluating an agent" even means. This post unpacks the conceptual core of Google's Agent Development Kit eval framework — cases, trajectories, metrics, thresholds — the parts that are language-agnostic, so the rest of this series can implement them as plain Go types and functions.*

---

Testing a deterministic function is easy: feed it an input, assert on the output. Agents break that comfort in two ways. First, the same prompt can yield different wording every run, so exact string equality is the wrong assertion. Second, an agent doesn't just *answer* — it *acts*: it decides which tools to call, in what order, with what arguments. A reply that reads perfectly can still be wrong if the agent reached it by calling the wrong tool, or right by luck after calling nothing at all.

Google's Agent Development Kit (ADK) answers this with an evaluation model that scores two different things: **what the agent did** (its trajectory of tool calls) and **what the agent said** (its final response). Everything else — file formats, metrics, thresholds — hangs off that split.

A note on the terrain. ADK's *eval tooling* is Python-only today: the `AgentEvaluator` class, the `adk eval` CLI, and the `.test.json` / `.evalset.json` file formats all live in the Python SDK. The Go module (`google.golang.org/adk/v2`) ships `agent`, `runner`, `tool`, `session`, `telemetry`, and friends — but **no eval package**. That's fine. The eval *model* is conceptual and portable; only its Python *implementation* is missing from Go. This post teaches the model. The rest of the series builds it in Go from scratch.

---

## 1. The unit of evaluation: an eval case

The atom of ADK evaluation is a single **eval case** — one interaction you want to hold the agent accountable for. Conceptually it bundles three things:

1. **The input** — what the user said (and, for multi-turn cases, the conversation leading up to it).
2. **The expected tool trajectory** — the sequence of tool calls you believe a correct agent would make, each with a name and arguments.
3. **The reference final response** — a known-good answer to compare the agent's actual reply against.

That triple is the whole idea. You're asserting *both* on the path and on the destination. An eval case with an empty expected trajectory says "a correct agent should answer this without calling any tools" — which is itself a meaningful assertion, since a chatty agent that gratuitously calls a search tool for `2 + 2` is misbehaving.

Here's that concept as an original Go schema — not a translation of ADK's Python types, but a Go-native modeling of the same idea:

```go
package eval

// ToolCall is one expected (or observed) invocation in a trajectory.
type ToolCall struct {
	Name string         `json:"name"`
	Args map[string]any `json:"args,omitempty"`
}

// Turn is a single user input paired with what a correct agent should do.
type Turn struct {
	UserInput    string     `json:"user_input"`
	WantTools    []ToolCall `json:"want_tools,omitempty"`    // expected trajectory
	WantResponse string     `json:"want_response,omitempty"` // reference answer
}

// EvalCase is one scenario: one or more turns that belong to a single session.
type EvalCase struct {
	ID    string `json:"id"`
	Turns []Turn `json:"turns"`
}
```

Note the deliberate choices: `Args` is `map[string]any` because tool arguments are arbitrary JSON; `WantTools` is a slice because trajectory is *ordered*; and a `Turn` carries both the expected path and the expected answer, keeping the two assertions side by side.

**The gotcha:** an eval case is *not* a unit test with one assertion — it's two assertions with independent pass/fail. An agent can nail the trajectory and botch the wording, or produce a beautiful answer via the wrong path. Keeping them separate is the point; collapsing them into a single "did it pass" boolean throws away exactly the diagnostic signal you built the case to capture.

---

## 2. Test files vs. evalsets: single-turn vs. multi-turn

ADK stores cases in two file shapes, and the distinction is a **data-modeling decision** worth understanding before you invent Go equivalents.

- A **test file** (`.test.json` in Python) holds a *single session* — one conversation, often one turn. It's the lightweight format for quick, focused checks: "given this input, did the agent call the weather tool and report the temperature?" You keep these next to your code and run them like unit tests.
- An **evalset** (`.evalset.json` in Python) holds *multiple sessions*, each potentially multi-turn, under one file. It's the format for realistic, stateful scenarios — a booking flow where turn 3 depends on what the agent remembered from turn 1. Evalsets are what you graduate to for regression suites and integration-style coverage.

The difference isn't cosmetic. A single-turn check can be stateless; a multi-turn evalset must preserve **session state** between turns, because the agent's behavior on turn *N* legitimately depends on turns *1..N-1*. That's why the `EvalCase` above nests `Turns` inside a case: one case *is* one session, and a session can have many turns.

Modeling the two shapes in Go is just two container types over the same `EvalCase`:

```go
// TestFile is the lightweight shape: a handful of quick, mostly single-turn cases.
type TestFile struct {
	Cases []EvalCase `json:"cases"`
}

// EvalSet is the heavyweight shape: many named, multi-turn sessions plus
// shared setup the whole suite runs against.
type EvalSet struct {
	Name         string         `json:"name"`
	Cases        []EvalCase     `json:"cases"`
	InitialState map[string]any `json:"initial_state,omitempty"` // seed session state
}
```

**The gotcha:** don't reach for the evalset shape first. Multi-turn cases are dramatically harder to author correctly — every turn's expected trajectory has to account for state the previous turns established, and a single wrong assumption early cascades into false failures downstream. Start with single-turn test files, prove the metrics work, and only build evalsets once you actually need stateful coverage.

---

## 3. The metric families

A metric is a function that takes (expected, actual) and returns a score, usually in `[0, 1]`. ADK groups them into families, and each answers a different question. Understanding *what each measures* is what lets you pick the right one instead of scoring everything the same blunt way.

### Trajectory: did the agent call the right tools?

The trajectory metric — ADK names it **`tool_trajectory_avg_score`** — compares the agent's actual sequence of tool calls against the expected one. In its strict form it's an **exact match**: same tools, same order, same arguments, scored per step and averaged. A perfect trajectory scores `1.0`; one wrong call in a four-step plan drags the average down proportionally.

```go
// TrajectoryScore returns the fraction of steps where the actual tool call
// exactly matches the expected one (name + args), position by position.
func TrajectoryScore(want, got []ToolCall) float64 {
	if len(want) == 0 && len(got) == 0 {
		return 1.0 // correctly called nothing
	}
	n := len(want)
	if len(got) > n {
		n = len(got) // length mismatch is itself a penalty
	}
	matches := 0
	for i := 0; i < len(want) && i < len(got); i++ {
		if want[i].Name == got[i].Name && sameArgs(want[i].Args, got[i].Args) {
			matches++
		}
	}
	return float64(matches) / float64(n)
}
```

Exact match is strict on purpose — it catches an agent that calls tools out of order or fabricates arguments. Its weakness is rigidity: if two orderings are equally valid, exact match unfairly fails one. That's a signal to relax the metric deliberately (say, order-insensitive matching), not to abandon trajectory scoring.

### Response, lexical: does the wording overlap the reference?

**`response_match_score`** compares the final response to the reference using **ROUGE-1** — the overlap of individual words (unigrams) between the two texts, expressed as an F-measure. It's cheap, deterministic, and needs no model to compute. It rewards answers that reuse the reference's key terms.

Its blind spot is meaning: ROUGE-1 can't tell that "the capital is Paris" and "Paris is the capital" say the same thing with different overlap, nor that two paraphrases with low word overlap are equally correct. Use it as a fast, free first pass, not a verdict on correctness.

### Response, semantic: does an LLM judge think it matches?

**`final_response_match_v2`** hands the (reference, actual) pair to an **LLM judge** and asks whether the actual response is correct given the reference. This catches paraphrase and semantic equivalence that ROUGE-1 misses. The cost is that the judge is itself a probabilistic model — non-deterministic, priced per call, and only as reliable as its prompt.

### Rubric-based: does it satisfy explicit criteria?

The **`rubric_based_*`** metrics score a response (or a whole trajectory) against a written **rubric** — a list of criteria like "cites a source," "declines politely if out of scope," "gives the number to two decimals." An LLM judge checks each criterion and you get a per-criterion breakdown. This is how you evaluate qualities that no single reference answer captures.

### Safety and hallucination: is it grounded and harmless?

- **`hallucinations_v1`** checks whether the response is *grounded* — supported by the tool outputs and context the agent actually had — rather than confidently invented.
- **`safety_v1`** checks whether the response is harmless per a safety policy.

Both are judged, both are about the *content's trustworthiness* rather than its match to a reference, and both matter most for agents that surface information to real users.

### Multi-turn: does it hold up across a conversation?

The **`multi_turn_*`** family applies the above ideas across an entire session rather than a single exchange — scoring the agent's coherence, memory, and task completion over multiple turns. These are the metrics you run against evalsets, and they're where stateful bugs (forgetting an earlier answer, contradicting itself) show up.

Here's how the families slot together as a Go interface — one contract, many implementations:

```go
// Metric scores an agent's behavior on a turn. Score is normalized to [0, 1].
type Metric interface {
	Name() string
	Evaluate(want Turn, gotTools []ToolCall, gotResponse string) (score float64, err error)
}
```

The interface deliberately hands each metric *both* the trajectory and the response, so a trajectory metric ignores the text, a ROUGE metric ignores the tools, and a rubric or multi-turn metric can use whatever it needs.

---

## 4. Thresholds and pass/fail

A raw score isn't a verdict. `0.82` means nothing until you decide what's good enough — and "good enough" differs per metric. Exact trajectory match might demand `1.0` (any deviation is a bug), while a ROUGE response match might pass at `0.5` (partial overlap is acceptable), and an LLM-judged match at `0.8`.

ADK externalizes this: thresholds live in a **`test_config.json`** so you can tune the bar without touching cases or code. The pattern is worth keeping in Go — a config of per-metric thresholds, evaluated against the scores:

```go
// Config maps a metric name to the minimum score that counts as a pass.
type Config struct {
	Thresholds map[string]float64 `json:"thresholds"`
}

// Passes reports whether every scored metric met its configured threshold.
// A metric with no configured threshold is treated as informational (not gating).
func (c Config) Passes(scores map[string]float64) bool {
	for name, min := range c.Thresholds {
		got, ok := scores[name]
		if !ok || got < min {
			return false
		}
	}
	return true
}
```

**The gotcha:** thresholds are policy, not truth — set them too high and every noisy run fails the suite until the team stops trusting it; too low and real regressions sail through green. Judge-based metrics especially need headroom, because the judge itself varies run to run. Externalizing thresholds (rather than hard-coding `>= 0.9` in an assertion) is what lets you tune that bar as you learn how noisy each metric really is.

---

## 5. The honest gap between Python and Go

To be direct about what exists where:

| Capability | Python ADK | Go ADK (`google.golang.org/adk/v2`) |
|---|---|---|
| Build and run agents | Yes | Yes (`agent`, `runner`, `tool`, `session`) |
| Observe tool calls | Yes | Yes (via `telemetry` / session events) |
| `.test.json` / `.evalset.json` formats | Yes | No — you define your own schema |
| `AgentEvaluator` + `adk eval` CLI | Yes | No equivalent |
| Built-in metrics (`response_match_score`, …) | Yes | No — you implement them |

The good news is that the two capabilities Go *does* have — running the agent and observing its tool calls through the `telemetry` and `session` packages — are exactly the raw material an evaluator needs. You run a case, capture the trajectory and final response from the session, and score them with functions you write. The eval "framework" that's missing is, in the end, a loop over cases, a set of metric functions, and a threshold check — all of which the structs above already sketch.

So the plan for this series is not to wait for a Go eval package. It's to *build the model directly*: `EvalCase` and `EvalSet` as our data schema, `Metric` implementations for the families that matter (trajectory exact-match first, then ROUGE, then an LLM judge), and a `Config` of thresholds to turn scores into pass/fail. The concepts port cleanly; only the code is ours to write.

---

## Key takeaways

- **An eval case asserts on two things independently:** the tool *trajectory* (what the agent did) and the *final response* (what it said). Never collapse them into one boolean — the split is the diagnostic value.
- **Test files vs. evalsets is single-turn vs. multi-turn.** Start with lightweight single-session cases; graduate to stateful, multi-turn evalsets only when you need them, because they're far harder to author correctly.
- **Metrics answer different questions.** Exact trajectory match is strict and deterministic; ROUGE response match is cheap but blind to meaning; LLM-judged match catches paraphrase at the cost of non-determinism; rubric, safety, and hallucination metrics score qualities no single reference captures.
- **Thresholds are tunable policy, not truth.** Externalize them so you can raise or lower the bar per metric as you learn each one's noise floor.
- **The eval model is portable; only Python's tooling is not.** Go can run agents and observe trajectories today — the missing evaluator is a loop over cases, a handful of metric functions, and a threshold check, which the rest of this series builds in Go.

---

## Further reading

- [ADK evaluation documentation](https://adk.dev/evaluate/) — the primary reference for the concepts modeled here (eval cases, trajectory vs. final response, metrics, and thresholds).
