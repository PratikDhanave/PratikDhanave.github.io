# Evaluating AI Systems

*How to know whether an LLM system actually works — building an eval dataset, the four metric families (deterministic checks, text overlap, embedding similarity, LLM-as-judge) in Go, task-specific eval for RAG and classification, and wiring a scored regression gate into CI so you measure instead of vibe.*

---

Every earlier post in this series ended with a program that ran. The chat client in post 4 returned a completion; the structured extractor in post 5 returned a typed struct; the RAG pipeline in posts 9 and 10 returned a grounded answer; the agent in posts 11 and 12 returned a result after a loop of tool calls. In each case we eyeballed the output, decided it looked right, and moved on. That works for a demo. It does not survive contact with a second prompt, a model upgrade, or a colleague asking "did your change make it better or worse?"

The reason ordinary tests don't answer that question is that LLM output is **non-deterministic and open-ended**. A unit test asserts `got == want`. But an LLM asked to summarize a paragraph can produce a hundred equally correct summaries that share almost no words, and running the same prompt twice can return different bytes. `assert.Equal` fails a correct answer for being phrased differently, and tells you nothing about the paraphrases you didn't hardcode. So instead of *testing* an LLM system, you **evaluate** it: you score its behavior across a set of representative cases and track that score over time. This post builds the machinery from scratch in Go.

> This is the broad primer for evaluating AI *systems*. For the agent-specific deep dive — trajectory scoring, tool-call correctness, multi-turn conversations — a companion series on this blog, [Evaluating Agents in Go](/blog/posts/eval-agents-go-01-why-evaluate-agents.html), goes much further. Here we stay at the level every LLM feature needs.

---

## Start with a dataset, not a metric

Evaluation begins with examples, not code. An **eval dataset** is a collection of cases, each pairing an input with either a reference answer or a rubric describing what a good answer looks like. In Go it is just a slice of structs:

```go
type EvalCase struct {
	ID        string   `json:"id"`
	Input     string   `json:"input"`
	Reference string   `json:"reference,omitempty"` // gold answer, if one exists
	Rubric    string   `json:"rubric,omitempty"`    // for open-ended cases
	MustHave  []string `json:"must_have,omitempty"` // required facts/terms
}
```

Where do cases come from? The worst source is your imagination — you'll write cases your system already passes. The best source is **real usage**. The chat client, RAG pipeline, and agent from earlier posts all pass through a request/response path you control, so log every interaction (input, output, retrieved context, latency, cost) as a trace. Then curate: sample real inputs, keep the ones that expose interesting behavior, and write down what the right answer should have been. A dataset grown this way stays honest because it reflects what users actually ask, not what you wish they asked.

**The gotcha:** a tiny or stale eval set gives false confidence. Twenty hand-written cases can all pass while your system quietly breaks on the long tail of real inputs. Treat the dataset as a living asset — every bug report is a missing test case, and the set should grow every week. A high score on ten cases means almost nothing; a high score on three hundred curated-from-production cases means something.

---

## Family 1: deterministic checks, the cheap wins

Some correctness *is* mechanical, and where it is, code it in plain Go — no model, no cost, no flakiness. A **scorer** is any function that maps a case and an output to a number in `[0,1]`:

```go
type Scorer func(c EvalCase, output string) float64

func exactMatch(c EvalCase, out string) float64 {
	if strings.TrimSpace(out) == strings.TrimSpace(c.Reference) {
		return 1
	}
	return 0
}

func containsAll(c EvalCase, out string) float64 {
	low := strings.ToLower(out)
	for _, want := range c.MustHave {
		if !strings.Contains(low, strings.ToLower(want)) {
			return 0
		}
	}
	return 1
}

func validJSON(_ EvalCase, out string) float64 {
	if json.Valid([]byte(out)) {
		return 1
	}
	return 0
}
```

The same family covers regex matching, JSON-schema validity (reuse the `validateInvoice`-style check from post 5), and **budgets**: latency and cost are deterministic numbers you can assert against a ceiling. Wrap them the same way — record the elapsed time and the token usage from the `Usage` field post 4 already parsed, and score `1` if under budget, `0` if over. A running harness over these scorers is a dozen lines:

```go
func run(cases []EvalCase, generate func(string) string, score Scorer) float64 {
	var total float64
	for _, c := range cases {
		total += score(c, generate(c.Input))
	}
	return total / float64(len(cases))
}
```

**The gotcha:** exact match massively *under*-counts correct answers. "Paris is the capital of France" and "The capital of France is Paris" are both right and score `0` against each other. Exact match is only honest for closed-form outputs — a classification label, an extracted ID, a number. For anything free-form it is a lower bound so pessimistic it's misleading. Use `containsAll` for required facts, and reach for the semantic and judge scorers below for the phrasing itself.

---

## Family 2: reference-based text overlap (and why it's weak)

Before embeddings, the standard way to compare a generated string to a reference was **n-gram overlap**. Two names dominate: **BLEU**, which measures precision (how many of the output's word-sequences appear in the reference), and **ROUGE**, which measures recall (how many of the reference's word-sequences appear in the output). At their core both count shared runs of tokens. A minimal unigram-recall version — the intuition behind ROUGE — is a handful of lines:

```go
func unigramRecall(reference, output string) float64 {
	refWords := strings.Fields(strings.ToLower(reference))
	outSet := map[string]bool{}
	for _, w := range strings.Fields(strings.ToLower(output)) {
		outSet[w] = true
	}
	var hit int
	for _, w := range refWords {
		if outSet[w] {
			hit++
		}
	}
	return float64(hit) / float64(len(refWords))
}
```

These metrics were built for machine translation and summarization, where a reference is available and outputs stay close to it. They are fast and reproducible, which is why they persist.

**The gotcha:** overlap metrics are weak for open-ended text. They reward surface word choice, not meaning — a perfect paraphrase using synonyms scores low, and a fluent-but-wrong answer that reuses the reference's vocabulary scores high. Report them if you already have references and want a cheap trend line, but never treat a BLEU/ROUGE number as a verdict on whether an answer is *correct*.

---

## Family 3: semantic similarity with embeddings

The fix for paraphrase-blindness is the tool we already built. Post 7 turned text into a `[]float32` where meaning lives in geometry, and implemented `cosine` by hand. Reuse it directly: embed the output and the reference, and score their cosine similarity. Synonyms and reordered clauses land close together even when they share no exact tokens.

```go
// embed calls the /embeddings endpoint from post 7; cosine is post 7's function.
func semanticScore(c EvalCase, out string) float64 {
	refVec := embed(c.Reference)
	outVec := embed(out)
	sim := cosine(refVec, outVec) // roughly [-1, 1]
	if sim < 0 {
		return 0
	}
	return sim // clamp to [0,1] for a usable score
}
```

This is the single biggest upgrade over exact match for free-form answers, and it stays cheap and deterministic (pin the embedding model). Its limit is that it rewards *topical* closeness, not *factual* correctness: "The dose is 5mg" and "The dose is 50mg" are nearly identical vectors but one is dangerously wrong. Use semantic similarity as a phrasing-tolerant filter, and when factual precision matters, escalate to a judge.

---

## Family 4: LLM-as-judge

When there's no clean reference and correctness is subjective — is this summary faithful? is this answer helpful and on-topic? — hand the grading to a strong model. **LLM-as-judge** prompts a capable model with the input, the output, and an explicit rubric, and asks for a score plus a reason. Post 5 already gave us structured output, so we get a typed, parseable verdict instead of prose:

```go
type Verdict struct {
	Score     int    `json:"score"`     // 1-5 against the rubric
	Reasoning string `json:"reasoning"` // why — forces the model to justify
}

func judge(ctx context.Context, c *Client, input, output, rubric string) (Verdict, error) {
	sys := "You are a strict grader. Apply the rubric exactly. " +
		"Score 1-5. Reason first, then score. Return only JSON."
	user := fmt.Sprintf("RUBRIC:\n%s\n\nINPUT:\n%s\n\nANSWER:\n%s", rubric, input, output)

	resp, err := c.Complete(ctx, ChatRequest{
		Messages:       []Message{{Role: "system", Content: sys}, {Role: "user", Content: user}},
		ResponseFormat: jsonSchema(reflectSchema(Verdict{})), // response_format from post 5
		Temperature:    0,
	})
	if err != nil {
		return Verdict{}, err
	}
	var v Verdict
	if err := json.Unmarshal([]byte(resp.Choices[0].Message.Content), &v); err != nil {
		return Verdict{}, err
	}
	return v, nil
}
```

Asking for the reasoning *before* the score isn't decoration — a model that must justify its grade grades more consistently, and the reasoning is your audit trail when a score looks wrong.

**The gotcha:** judges are biased, and the biases are systematic. Models favor **longer** answers over concise correct ones, favor whichever answer comes **first** when comparing two, and rate their **own** outputs higher than a rival model's. Three mitigations: (1) **anchor with a concrete rubric** — replace "rate the quality" with "5 = every claim supported by the input; 3 = mostly supported, one unsupported claim; 1 = fabricated" so the score has fixed meaning; (2) prefer **pairwise comparison** ("is A or B better?") over absolute scoring, since relative judgments are more stable — and swap the order across runs to cancel position bias; (3) use a **different model** to judge than the one that generated, to avoid self-preference. A judge is a useful, scalable approximation of a human rater, not an oracle.

---

## Task-specific eval

The four families are your toolkit; different tasks assemble them differently.

**RAG** (posts 9–10) has three failure surfaces, each with its own metric. **Retrieval recall@k** — is the answer-bearing chunk in the top *k*? — is the ceiling on everything downstream, exactly as post 10 argued; it's a deterministic set check against known-relevant chunk IDs. **Faithfulness / groundedness** asks whether every claim in the answer is supported by the retrieved context — a perfect job for an LLM-as-judge that sees the context and flags any unsupported sentence. **Answer relevance** asks whether the answer actually addresses the question — semantic similarity between the answer and the question, or another judge pass. Together they separate "we retrieved the wrong thing" from "we retrieved the right thing and then ignored or contradicted it."

**Classification** — routing, intent detection, the retrieval gate from post 10 — is the one place where references are crisp and the old metrics shine. Count outcomes per label and compute precision, recall, and F1 directly:

```go
func prf1(tp, fp, fn int) (precision, recall, f1 float64) {
	if tp+fp > 0 {
		precision = float64(tp) / float64(tp+fp)
	}
	if tp+fn > 0 {
		recall = float64(tp) / float64(tp+fn)
	}
	if precision+recall > 0 {
		f1 = 2 * precision * recall / (precision + recall)
	}
	return
}
```

Precision asks "when it said yes, was it right?"; recall asks "of all the real yeses, how many did it catch?"; F1 balances the two. Which you optimize depends on the cost of each error — a spam filter guards precision, a fraud flag guards recall.

| Task | Primary metric | Family |
|---|---|---|
| Extraction / labels / IDs | exact match, JSON validity | deterministic |
| Free-form Q&A | semantic similarity + judge | embeddings + judge |
| Summarization | faithfulness (judge), ROUGE trend | judge + overlap |
| RAG retrieval | recall@k | deterministic |
| RAG answer | groundedness + relevance | judge + embeddings |
| Classification / routing | precision / recall / F1 | deterministic |

---

## Make eval part of the loop

A score you compute once and forget is a vanity metric. The point of all this machinery is to run it *automatically* and *repeatedly*. Combine the pieces into a runner that scores a whole dataset and fails when quality drops:

```go
func gate(cases []EvalCase, generate func(string) string, score Scorer, floor float64) error {
	got := run(cases, generate, score)
	fmt.Printf("eval score: %.3f (floor %.3f)\n", got, floor)
	if got < floor {
		return fmt.Errorf("regression: %.3f < %.3f", got, floor)
	}
	return nil
}
```

Call it from a Go test so `go test ./...` runs it, wire that into CI, and every pull request now proves it didn't make the system worse before it merges. Commit the floor alongside the code; ratchet it up as you improve. (The companion [Evaluating Agents in Go](/blog/posts/eval-agents-go-07-ci-regression-gating.html) series covers this CI gating pattern in depth for agents.)

This is **offline eval** — a fixed dataset scored before shipping, the fast feedback that guides development. It is necessary but not sufficient, because a curated set never fully mirrors live traffic. **Online eval** closes the gap: sample real production responses, score them with the same judges and checks, and watch the trend. Ship changes behind an **A/B test** — route a fraction of traffic to the new version and compare scores on identical distributions — and collect **human feedback** (thumbs up/down, corrections), the ground truth you calibrate your automated judges against and the richest source of new eval cases.

**The gotcha:** non-determinism will corrupt your scores if you ignore it. The same input can yield different outputs, so a single sample per case makes your metric jittery — a "regression" might be noise. Two defenses: pin **temperature 0** for the model under test so scoring is reproducible, and for anything still stochastic (judges included), **run several samples and average**. Fix the eval-set order, fix model versions, and record them with the score, so a number from today is comparable to a number from last month.

---

## Key takeaways

- **You evaluate LLM systems, you don't unit-test them.** Output is non-deterministic and open-ended, so `assert.Equal` fails correct answers and proves nothing about the ones you didn't hardcode. Score behavior across a dataset instead.
- **The dataset is the product.** Curate cases from real traces, turn every failure into a case, and keep it growing. A tiny or stale set is false confidence.
- **Match the metric to the task.** Deterministic checks for closed-form outputs and budgets; embedding cosine (post 7) for paraphrase-tolerant free-form comparison; LLM-as-judge for subjective quality; precision/recall/F1 for classification.
- **Exact match and n-gram overlap under-count correctness** on open-ended text — treat them as cheap lower bounds, not verdicts.
- **LLM-as-judge is scalable but biased** toward longer, first, and self-authored answers. Anchor with a concrete rubric, prefer order-swapped pairwise comparison, and judge with a different model.
- **RAG splits into recall@k, groundedness, and relevance** — measure them separately so you know *which* stage failed.
- **Eval belongs in CI as a scored regression gate**, backed by online scoring, A/B tests, and human feedback. Pin temperature 0 and average multiple samples so your scores are reproducible.
- **Measure before you tweak.** Set a baseline first; every prompt change is a hypothesis you verify against the score, not a vibe you ship.

---

## Further reading

- [Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (arXiv:2306.05685)](https://arxiv.org/abs/2306.05685) — the foundational study of LLM-as-judge, including the position, verbosity, and self-enhancement biases and the pairwise-comparison mitigation.
- [Lin, "ROUGE: A Package for Automatic Evaluation of Summaries" (ACL 2004)](https://aclanthology.org/W04-1013/) — the original ROUGE paper defining n-gram recall for summarization.
- [Papineni et al., "BLEU: a Method for Automatic Evaluation of Machine Translation" (ACL 2002)](https://aclanthology.org/P02-1040/) — the original BLEU precision-based overlap metric.
- [Es et al., "RAGAS: Automated Evaluation of Retrieval Augmented Generation" (arXiv:2309.15217)](https://arxiv.org/abs/2309.15217) — reference-free RAG metrics for faithfulness and answer relevance.
- [Evaluating Agents in Go](/blog/posts/eval-agents-go-01-why-evaluate-agents.html) — the companion series on this blog for agent-specific trajectory and multi-turn evaluation.
