# Why Evaluating AI Agents Is Hard

*The opener to a series on evaluating agents in Go: why an agent isn't a function you can unit-test, why "it worked in the demo" doesn't survive contact with production, and the two things actually worth measuring — the steps it took and the answer it gave.*

---

A function is a contract. Give it the same inputs and it returns the same output, forever, until someone edits the code. That property is the quiet foundation of every test you have ever written: assert that `Add(2, 3)` returns `5`, and if it ever doesn't, something changed and the test tells you where.

An agent breaks that contract on purpose. It wraps a language model in a loop — the model reads a request, decides whether to call a tool, reads the tool's result, decides again, and eventually answers. The same request can produce a different tool sequence and a different sentence on two consecutive runs, and *both can be correct*. This is not a bug you can fix; it is the mechanism you are paying for. The whole reason you reached for an agent instead of a switch statement is that you wanted it to handle inputs you didn't enumerate.

So the first honest thing to say about evaluating agents is that your existing testing instincts will fight you. `assert output == expected` is the wrong shape. This series is about the right shape — and because Google's Agent Development Kit ships its evaluation tooling only in Python, doing it in Go means building the harness yourself. That's the work. Let's start with why it's necessary.

---

## An agent is not a function

Here is the smallest agent that still behaves like one — a model, a loop, a tool. The Go type is deliberately vague about what happens inside `Run`, because that vagueness is the point.

```go
// Agent runs a model-driven loop and returns a final answer plus the
// trajectory it took to get there. Two calls with the same query may
// return different Trajectory and different Answer — both may be valid.
type Agent interface {
	Run(ctx context.Context, query string) (Result, error)
}

type Result struct {
	Answer     string     // the final natural-language response
	Trajectory []ToolCall // the ordered tool calls made along the way
}

type ToolCall struct {
	Name string            // e.g. "search_flights"
	Args map[string]any    // the arguments the model chose
}
```

Now try to test it the way you'd test `Add`:

```go
func TestBookFlight(t *testing.T) {
	got, _ := agent.Run(ctx, "cheapest flight BLR to SFO next Friday")
	if got.Answer != "The cheapest flight is UA 869 at $612." {
		t.Fatalf("unexpected answer: %q", got.Answer)
	}
}
```

This test is worse than useless — it is *confidently* useless. It fails when the price changes, when the model rephrases the same fact ("Your cheapest option is United 869, $612"), when the flight number updates, or when the model helpfully adds a caveat about baggage fees. None of those are regressions. Yet it *passes* if the agent invents a flight that doesn't exist, as long as it happens to print that exact string. You are asserting on the one thing that is allowed to vary while ignoring the thing that actually matters: whether the agent did the right work and told the truth.

**The gotcha:** string equality on an agent's answer measures phrasing, not correctness. It produces false failures on valid rewordings and false passes on confident hallucinations — the exact inversion of what a test is for. Every instinct that served you on pure functions has to be re-derived here.

---

## Why "it worked in the demo" isn't enough

Demos are single draws from a distribution. You typed a query, the stars aligned, the agent nailed it, and you shipped. Production is thousands of draws from a *shifting* distribution, and three forces conspire against the version that impressed you in the demo.

**Non-determinism within a fixed setup.** Even with the same model, same prompt, and temperature pinned low, decoding is sampled and tool results arrive in varying order. The agent that took three clean tool calls in the demo might take a redundant fifth one at 2 a.m., or skip a lookup and guess. You cannot see this from one run; you see it from the *rate* across many runs.

**Prompt and model drift.** You will edit the system prompt to fix one awkward reply, and silently change behavior on twenty inputs you didn't retest. Worse, the model itself moves underneath you: a provider ships a new checkpoint behind the same version string, deprecates the one you validated on, or nudges tool-calling behavior in a minor update. Your code didn't change; your agent did.

**Silent regressions.** This is the dangerous one. When a function regresses, it throws or returns the wrong type and something downstream crashes loudly. When an agent regresses, it keeps producing fluent, confident, well-formatted prose — that is now subtly wrong. There is no stack trace for "started hallucinating refund policies." The output looks exactly as trustworthy as it did yesterday. Without measurement, the failure mode of an agent is not a crash; it is a lie delivered in a calm voice.

The takeaway isn't "demos are bad." It's that a demo answers "can it work?" and production requires "how often does it work, and will I notice when that changes?" Those are statistical questions, and statistical questions need a harness that runs many cases and reports rates — not a green checkmark from one lucky run.

---

## The two things worth measuring

Google's ADK documentation frames agent evaluation around two axes, and they map cleanly onto the two ways an agent can disappoint you. Keep them separate; they fail independently and you debug them differently.

### 1. Trajectory — did it take the right steps?

The trajectory is the ordered sequence of tool calls the agent made. Evaluating it asks: given this query, did the agent reach for the right tools, with sane arguments, in a reasonable order? An agent can produce a correct-sounding final answer while having taken a reckless path to get there — skipping a required authorization check, calling a write tool before the read that should gate it, or hitting a paid API five times where one would do. Trajectory evaluation is what catches that.

The relevant idea from ADK's model is `tool_trajectory_avg_score`: compare the actual tool sequence against an expected one and score how well they match. In Go you build the comparison yourself. A first, deliberately simple version:

```go
// TrajectoryScore returns the fraction of steps where the actual tool
// call matches the expected one, position by position. 1.0 is a perfect
// match; 0.0 is no overlap. This is exact-match — a real harness layers
// in argument tolerance and order-insensitivity where the task allows.
func TrajectoryScore(expected, actual []ToolCall) float64 {
	if len(expected) == 0 {
		return 1.0
	}
	matches := 0
	for i := range expected {
		if i < len(actual) && sameCall(expected[i], actual[i]) {
			matches++
		}
	}
	return float64(matches) / float64(len(expected))
}

func sameCall(a, b ToolCall) bool {
	return a.Name == b.Name && argsEqual(a.Args, b.Args)
}
```

This is intentionally strict, and later posts loosen it — because "took the right steps" is rarely a single canonical path. Sometimes order doesn't matter, sometimes an extra tool call is fine, sometimes the argument just has to be *close enough*. Encoding that judgment is most of the real work, and we'll build it up honestly rather than pretend one score fits every task.

### 2. Final response — did it give the right answer?

The second axis judges the answer itself, independent of how it was reached. ADK's model offers a ladder of increasingly capable metrics, and the honest framing is that each one buys more nuance at a higher cost:

- **`response_match_score`** — lexical overlap against a reference answer (ROUGE-1 style, n-gram overlap). Cheap, deterministic, and blind to meaning: it rewards shared words and can't tell that "United 869" and "UA869" are the same flight, or that a fluent paraphrase is correct.
- **`final_response_match_v2`** — an LLM-as-judge scores the answer against the reference for *semantic* correctness, tolerating rewording. More faithful to how a human would grade, but now your evaluator is itself a non-deterministic model with its own cost and biases.
- **`rubric_based_*`** — score against an explicit checklist of criteria you write ("cites a real flight number", "states the price", "mentions baggage caveats") rather than one golden string.
- **`hallucinations_v1`** — check whether claims in the answer are grounded in the tool results and context, rather than invented.
- **`safety_v1`** and **`multi_turn_*`** — safety of the response, and the harder case of quality sustained across a whole conversation rather than a single turn.

**The gotcha:** there is no free lunch on the response axis. Lexical scores are cheap, reproducible, and semantically blind; LLM-judge scores are semantically aware but slower, costlier, and non-deterministic — you are now evaluating a model *with* a model, so you have to validate the judge too. The right choice depends on how much a wrong answer costs you, not on which metric sounds most sophisticated. A blog code sample can live with ROUGE; a refund agent cannot.

---

## Where Go stands, and what this series builds

Here is the part the Go ecosystem doesn't advertise. The `google.golang.org/adk/v2` module gives you real, first-class packages for *building* agents — `agent`, `runner`, `tool`, `session`, `model`, `memory`, `workflow`, `artifact`, `telemetry`. What it does **not** give you is an evaluation package. The `AgentEvaluator`, the `adk eval` command-line runner, and the evalset file format all live in ADK's Python distribution. There is no drop-in Go equivalent, and inventing an API that looks like one would just mislead you.

So the Go position is: the *conceptual* model is language-agnostic and well-documented — two axes, the metric families above — but the *tooling* to apply it is yours to build. That is not a gap to apologize for; it's the premise of this series. We'll build a small, honest evaluation harness in Go, piece by piece, grounded in ADK's documented model rather than in any one course's code.

The rough map from here:

| Post | What we build |
|---|---|
| 1 — this one | Why agents resist unit testing; the two axes to measure |
| 2 | An evalset format in Go — cases with a query, expected trajectory, and reference answer |
| 3 | A `runner` that executes cases and captures the real trajectory + answer |
| 4 | Trajectory scoring: exact match, then order- and argument-tolerant variants |
| 5 | Response scoring: ROUGE-style overlap, then an LLM-as-judge with a validated rubric |
| 6 | Grounding and hallucination checks against tool outputs |
| 7 | Wiring evaluation into CI so regressions fail the build, not production |

Each post ships runnable Go and is upfront about what the metric can and cannot tell you. No metric here is a verdict on its own; together they turn "it felt fine in the demo" into a number you can watch move.

---

## Key takeaways

- **An agent is not a function.** Same input, different valid output — string equality on the answer gives you false failures on rewordings and false passes on confident hallucinations.
- **Demos answer the wrong question.** "Can it work?" is one lucky draw; production needs "how often, and will I notice when it drifts?" Those are statistical questions that need a harness, not a checkmark.
- **Measure two things separately.** Trajectory (did it take the right steps?) and final response (did it give the right answer?) fail independently and are debugged differently.
- **Response metrics trade cost for nuance.** Lexical overlap is cheap and semantically blind; LLM-judge is faithful but non-deterministic and needs validating itself. Pick by what a wrong answer costs.
- **In Go, you build the harness.** ADK defines a solid, language-agnostic eval model but ships the tooling only in Python. `adk-go` has no evaluation package — so this series builds one, grounded in the docs.

The goal of everything that follows isn't a perfect grade. It's the ability to catch a silent regression before your users do — to replace a calm, confident, wrong answer with a red number in CI.

---

## Further reading

- [Google ADK — Evaluate agents](https://adk.dev/evaluate/) — the primary conceptual source for the two-axis model and the metric families (`tool_trajectory_avg_score`, `response_match_score`, `final_response_match_v2`, rubric-based, hallucination, and safety metrics) referenced throughout this post.
- The topic of evaluating ADK agents is also covered by a LinkedIn Learning course, which inspired this series' subject; the code and framing here are original and derived from Google's public ADK documentation rather than that course.
