# Response Evaluation: Match, ROUGE, and LLM-as-Judge

*How to score an agent's final answer against a reference — from exact string match, through ROUGE-1 unigram overlap, to an LLM judge — with original Go you can drop into a test suite. Part 5 of Evaluating Agents in Go.*

---

The earlier parts of this series measured how an agent *behaves* — which tools it called, in what order, whether it stayed on the rails. This one measures the thing users actually see: the **final response**. Given a question, a reference (gold) answer, and whatever the agent produced, how good was it?

The Go SDK for Google's Agent Development Kit — `google.golang.org/adk/v2` — gives you the runner, agents, and tools, but it ships **no evaluation package**. So we build one. The good news is that response scoring is a small, self-contained problem, and the ADK Python evaluators describe exactly the shape worth reproducing:

- **`response_match_score`** — ROUGE-1 similarity between candidate and reference, passing above a threshold (0.8 by default).
- **`final_response_match_v2`** — an LLM judge deciding whether the candidate is *semantically equivalent* to the reference.
- **`rubric_based_final_response_quality_v1`** — an LLM scoring the response against an explicit rubric.

Three metrics, three levels of leniency. We'll implement the first two from scratch in Go and sketch the third, then combine them into a single pass/fail gate.

---

## 1. Exact and normalized match: cheap, deterministic, and too strict

The simplest metric is string equality. It has one virtue — it never lies about *what* it measured — and one fatal flaw: natural language has many correct surfaces for one meaning. `"42"` and `"The answer is 42."` are the same answer and an exact comparison calls them different.

Normalizing before comparing recovers some of that. Lowercase, collapse whitespace, strip punctuation:

```go
package respeval

import (
	"regexp"
	"strings"
)

var punct = regexp.MustCompile(`[^\p{L}\p{N}\s]+`)
var spaces = regexp.MustCompile(`\s+`)

// Normalize lowercases, strips punctuation, and collapses whitespace.
func Normalize(s string) string {
	s = strings.ToLower(s)
	s = punct.ReplaceAllString(s, " ")
	s = spaces.ReplaceAllString(strings.TrimSpace(s), " ")
	return s
}

// ExactMatch is true only if the raw strings are identical.
func ExactMatch(candidate, reference string) bool {
	return candidate == reference
}

// NormalizedMatch compares after Normalize.
func NormalizedMatch(candidate, reference string) bool {
	return Normalize(candidate) == Normalize(reference)
}
```

`NormalizedMatch` now accepts `"The answer is 42"` and `"the answer is 42."` as equal. But it still fails the moment the wording drifts: `"forty-two"` vs `"42"`, or a correct answer that adds a clause the reference omitted. Exact match is a good gate for **closed-form** answers — a currency code, a boolean, an ID — and a bad one for prose. For prose you need a metric that rewards *overlap* rather than demanding identity. That is ROUGE.

---

## 2. ROUGE-1: scoring unigram overlap

ROUGE-1 measures how many individual words (unigrams) the candidate and reference share. It reports three numbers:

- **Precision** — of the words the candidate produced, what fraction appear in the reference? (Penalizes padding.)
- **Recall** — of the words the reference contains, what fraction did the candidate produce? (Penalizes omissions.)
- **F1** — the harmonic mean, which is what ADK's `response_match_score` thresholds on.

The one subtlety that separates a correct implementation from a naive one is **clipping**: if the reference says "the" twice and the candidate says "the" five times, the overlap for "the" is 2, not 5. You count the *minimum* of the two counts per word. Here is the whole thing:

```go
package respeval

// Rouge1Score holds unigram precision, recall, and F1.
type Rouge1Score struct {
	Precision float64
	Recall    float64
	F1        float64
}

func tokenize(s string) []string {
	n := Normalize(s)
	if n == "" {
		return nil
	}
	return strings.Fields(n)
}

func counts(tokens []string) map[string]int {
	m := make(map[string]int, len(tokens))
	for _, t := range tokens {
		m[t]++
	}
	return m
}

// Rouge1 computes clipped unigram overlap between candidate and reference.
func Rouge1(candidate, reference string) Rouge1Score {
	cand := tokenize(candidate)
	ref := tokenize(reference)
	if len(cand) == 0 || len(ref) == 0 {
		return Rouge1Score{} // no overlap is definable
	}

	candCounts := counts(cand)
	refCounts := counts(ref)

	overlap := 0
	for tok, c := range candCounts {
		if r, ok := refCounts[tok]; ok {
			overlap += min(c, r) // clip to the smaller count
		}
	}

	precision := float64(overlap) / float64(len(cand))
	recall := float64(overlap) / float64(len(ref))
	f1 := 0.0
	if precision+recall > 0 {
		f1 = 2 * precision * recall / (precision + recall)
	}
	return Rouge1Score{Precision: precision, Recall: recall, F1: f1}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
```

(On Go 1.21+ the built-in `min` exists and you can drop the helper.)

### A worked example

Take a reference and a near-miss candidate:

- **reference:** `"the cat sat on the mat"` → tokens `[the, cat, sat, on, the, mat]`, counts `{the:2, cat:1, sat:1, on:1, mat:1}`, length 6.
- **candidate:** `"the cat sat on a mat"` → tokens `[the, cat, sat, on, a, mat]`, counts `{the:1, cat:1, sat:1, on:1, a:1, mat:1}`, length 6.

Clipped overlap, word by word: `the` = min(1, 2) = 1, `cat` = 1, `sat` = 1, `on` = 1, `mat` = 1, `a` = 0 (not in reference). Total overlap = **5**.

- precision = 5 / 6 ≈ **0.833**
- recall = 5 / 6 ≈ **0.833**
- F1 ≈ **0.833**

At an F1 threshold of 0.8 this candidate **passes** — a one-word substitution barely dents the score, which is exactly the leniency we wanted over exact match. The clipping mattered: without it, the double-counted `"the"` in the reference could have inflated the overlap and pushed the score past 1.0.

### Where ROUGE-1 breaks

ROUGE only sees surface words. Two failure modes follow directly:

1. **Paraphrase looks wrong.** Reference `"The capital of France is Paris."` vs candidate `"Paris is the capital city of France."` share most words and score well — but reference `"You should restart the service."` vs candidate `"Try rebooting the daemon."` mean the same thing and share almost nothing. ROUGE-1 F1 ≈ 0.
2. **Word-salad looks right.** A candidate that lists the reference's keywords in a meaningless order can post a high unigram overlap while saying nothing coherent, because ROUGE-1 ignores order entirely.

When meaning and wording diverge, lexical overlap is the wrong tool. You need something that reads for *meaning*.

---

## 3. LLM-as-judge: scoring meaning, not words

The idea behind ADK's `final_response_match_v2` is to hand the question, the reference, and the candidate to a language model and ask it: *are these two answers equivalent?* The model reads past the wording and judges the semantics — catching the paraphrase ROUGE missed, and rejecting the word-salad ROUGE accepted.

We keep the model call **generic**. The adk-go model clients evolve, and this series is about the evaluation logic, not a particular client signature. So we depend on a tiny interface any client (an adk-go model, a raw HTTP call, a fake for tests) can satisfy:

```go
package respeval

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

// Model is the minimal surface a judge needs: text in, text out.
// Back it with an adk-go model client, a direct API call, or a fake.
type Model interface {
	Generate(ctx context.Context, prompt string, temperature float64) (string, error)
}

// Verdict is the structured result we ask the judge to return.
type Verdict struct {
	Score     float64 `json:"score"`     // 0.0–1.0
	Pass      bool    `json:"pass"`      // judge's own call
	Reasoning string  `json:"reasoning"` // one sentence
}
```

The prompt is where reliability is won or lost. A good judge prompt (a) states the task narrowly, (b) supplies an explicit rubric so "equivalent" isn't left to the model's mood, (c) demands structured output, and (d) tells the model to ignore style, length, and phrasing:

```go
const judgeTemplate = `You are a strict evaluator. Decide whether the CANDIDATE
answer is semantically equivalent to the REFERENCE answer for the given QUESTION.

Rubric:
- Score 1.0: candidate conveys the same key facts as the reference; wording may differ.
- Score 0.5: candidate is partially correct or omits a material fact.
- Score 0.0: candidate is wrong, contradicts the reference, or is off-topic.
Ignore differences in style, length, and phrasing. Judge only meaning.
Do not reward a candidate for merely repeating words from the reference.

QUESTION: %s
REFERENCE: %s
CANDIDATE: %s

Respond with ONLY a JSON object, no prose, no code fences:
{"score": <number 0.0-1.0>, "pass": <true|false>, "reasoning": "<one sentence>"}`

// LLMJudge asks the model whether candidate matches reference.
func LLMJudge(ctx context.Context, m Model, question, reference, candidate string) (Verdict, error) {
	prompt := fmt.Sprintf(judgeTemplate, question, reference, candidate)

	// Low temperature: we want a repeatable verdict, not creativity.
	raw, err := m.Generate(ctx, prompt, 0.0)
	if err != nil {
		return Verdict{}, fmt.Errorf("judge generate: %w", err)
	}

	v, err := parseVerdict(raw)
	if err != nil {
		return Verdict{}, fmt.Errorf("judge parse: %w", err)
	}
	return v, nil
}

// parseVerdict extracts the JSON object even if the model wraps it in prose.
func parseVerdict(raw string) (Verdict, error) {
	s := strings.TrimSpace(raw)
	// Trim a stray ```json ... ``` fence if the model added one.
	s = strings.TrimPrefix(s, "```json")
	s = strings.TrimPrefix(s, "```")
	s = strings.TrimSuffix(s, "```")
	// Slice to the outermost braces to survive leading/trailing chatter.
	if i, j := strings.Index(s, "{"), strings.LastIndex(s, "}"); i >= 0 && j > i {
		s = s[i : j+1]
	}
	var v Verdict
	if err := json.Unmarshal([]byte(strings.TrimSpace(s)), &v); err != nil {
		return Verdict{}, fmt.Errorf("not valid JSON: %q: %w", raw, err)
	}
	if v.Score < 0 || v.Score > 1 {
		return Verdict{}, fmt.Errorf("score out of range: %v", v.Score)
	}
	return v, nil
}
```

### Making the judge reliable

An LLM judge is itself a nondeterministic system, so treat it like one you're trying to control:

- **Temperature 0.** You want the same input to yield the same verdict run to run. Creativity is a liability here.
- **A written rubric, not a vibe.** "Equivalent" is underspecified; the three-band rubric above turns a fuzzy question into a near-classification. Tighten the bands to your domain.
- **Structured output.** Parsing free-form prose for a verdict is brittle. Ask for JSON and parse it — and make the parser defensive, because models still occasionally wrap JSON in a code fence or a sentence, which `parseVerdict` strips.
- **Guard against judge bias.** Models tend to reward longer, more confident, or more familiar-sounding answers, and can favor a candidate that echoes the reference's words (the very thing we told it to ignore). Keep the reference and candidate clearly labeled and symmetric, tell the judge to ignore length and phrasing, and — for anything high-stakes — spot-check a sample of verdicts against human judgment before trusting the metric at scale.
- **Fail loud on unparseable output.** A judge that can't be parsed is a *test infrastructure* failure, not a passing grade. Return an error; never silently score it as a pass.

The `rubric_based_final_response_quality_v1` metric is the same machinery with a different question — instead of "is this equivalent to the reference?" you ask "does this satisfy each criterion in this rubric?" and average the per-criterion scores. Swap the template, keep the client, keep the parser.

---

## 4. Combining metrics into a pass/fail gate

No single metric is right for every case, so combine them with a cheap-to-expensive strategy: try lexical match first (free, deterministic), and only spend an LLM call when overlap is inconclusive.

```go
// Thresholds configures the gate.
type Thresholds struct {
	RougeF1  float64 // e.g. 0.8, matching ADK's response_match_score default
	Judge    float64 // e.g. 0.8, minimum acceptable judge score
	UseJudge bool    // fall back to the LLM judge when ROUGE is low
}

// Result is the combined outcome for one (question, reference, candidate).
type Result struct {
	Pass    bool
	Rouge   Rouge1Score
	Verdict *Verdict // nil if the judge was not consulted
	Method  string   // "exact", "rouge", or "judge"
}

// Grade runs the escalation: exact/normalized → ROUGE → judge.
func Grade(ctx context.Context, m Model, t Thresholds, question, reference, candidate string) (Result, error) {
	if NormalizedMatch(candidate, reference) {
		return Result{Pass: true, Method: "exact"}, nil
	}

	r := Rouge1(candidate, reference)
	if r.F1 >= t.RougeF1 {
		return Result{Pass: true, Rouge: r, Method: "rouge"}, nil
	}

	// Lexical overlap was low. That is either a real miss or a paraphrase.
	if !t.UseJudge {
		return Result{Pass: false, Rouge: r, Method: "rouge"}, nil
	}
	v, err := LLMJudge(ctx, m, question, reference, candidate)
	if err != nil {
		return Result{Rouge: r, Method: "judge"}, err
	}
	return Result{Pass: v.Pass && v.Score >= t.Judge, Rouge: r, Verdict: &v, Method: "judge"}, nil
}
```

This ordering is deliberate. Exact match is free and unambiguous; ROUGE is free and catches near-misses; the judge is the only step that costs a model call and introduces nondeterminism, so it runs **last and only when needed** — when lexical overlap is low, which is precisely the paraphrase case ROUGE can't resolve. In a large eval suite this keeps the bill and the flakiness proportional to the number of genuinely ambiguous answers.

---

## 5. Tests

Response scoring is math and prompt-plumbing, both testable without a live model. Use a fake `Model` for the judge path:

```go
package respeval

import (
	"context"
	"math"
	"testing"
)

func TestRouge1WorkedExample(t *testing.T) {
	got := Rouge1("the cat sat on a mat", "the cat sat on the mat")
	if math.Abs(got.F1-0.8333) > 0.001 {
		t.Fatalf("F1 = %.4f, want ~0.8333", got.F1)
	}
}

func TestRouge1Clipping(t *testing.T) {
	// Reference has "the" once; a candidate spamming "the" must not
	// score overlap above the reference's count.
	got := Rouge1("the the the the", "the mat")
	if got.Precision > 0.26 { // 1 clipped overlap / 4 candidate tokens
		t.Fatalf("precision = %.4f, clipping failed", got.Precision)
	}
}

func TestNormalizedMatch(t *testing.T) {
	if !NormalizedMatch("The answer is 42.", "the answer is 42") {
		t.Fatal("normalized match should ignore case and punctuation")
	}
	if NormalizedMatch("forty-two", "42") {
		t.Fatal("normalized match is lexical; it cannot equate these")
	}
}

// fakeModel returns a canned response and records the prompt it saw.
type fakeModel struct {
	reply      string
	lastPrompt string
	lastTemp   float64
}

func (f *fakeModel) Generate(_ context.Context, prompt string, temp float64) (string, error) {
	f.lastPrompt, f.lastTemp = prompt, temp
	return f.reply, nil
}

func TestLLMJudgeParsesFencedJSON(t *testing.T) {
	m := &fakeModel{reply: "```json\n{\"score\":1.0,\"pass\":true,\"reasoning\":\"same fact\"}\n```"}
	v, err := LLMJudge(context.Background(), m, "capital of France?", "Paris", "The capital is Paris.")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !v.Pass || v.Score != 1.0 {
		t.Fatalf("verdict = %+v, want pass with score 1.0", v)
	}
	if f := m.lastTemp; f != 0.0 {
		t.Fatalf("judge temperature = %v, want 0.0", f)
	}
}

func TestGradeEscalatesToJudge(t *testing.T) {
	// A paraphrase with near-zero lexical overlap must reach the judge.
	m := &fakeModel{reply: `{"score":1.0,"pass":true,"reasoning":"equivalent"}`}
	res, err := Grade(context.Background(), m,
		Thresholds{RougeF1: 0.8, Judge: 0.8, UseJudge: true},
		"How do I fix it?", "You should restart the service.", "Try rebooting the daemon.")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !res.Pass || res.Method != "judge" {
		t.Fatalf("result = %+v, want pass via judge", res)
	}
}
```

`go test ./...` runs the whole thing offline. The judge path is exercised with a fake, so it's deterministic in CI; you only reach for a real adk-go model client when you deliberately run the live evaluation.

---

## Key takeaways

- **Exact/normalized match** is right for closed-form answers and too strict for prose — one paraphrase and it fails a correct answer.
- **ROUGE-1** scores clipped unigram overlap (precision, recall, F1); it's free and deterministic, and F1 ≥ 0.8 mirrors ADK's `response_match_score`. It rewards near-misses but is blind to paraphrase and to word order.
- **LLM-as-judge** reads for meaning, catching the paraphrases ROUGE misses — but it's nondeterministic, so pin temperature to 0, give it a written rubric, demand structured JSON, and guard against length and echo bias.
- **Combine them cheap-to-expensive:** exact → ROUGE → judge, so the model call only fires on genuinely ambiguous answers.
- **adk-go has no eval package** — but response scoring is small enough to own, test offline with a fake model, and wire to a real client only for live runs.

---

## Further reading

- [ADK evaluation guide](https://adk.dev/evaluate/) — the response and rubric metrics this post reimplements in Go.
- [google/adk-go](https://github.com/google/adk-go) — the Go SDK (`google.golang.org/adk/v2`) whose model clients back the judge.
