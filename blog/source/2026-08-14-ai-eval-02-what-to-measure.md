# What to Measure: A Taxonomy of Metrics

*Before you can score an LLM, you have to decide what "good" even means for your task — and that choice determines everything downstream. Metrics fall into a few families, from exact string matching to reference overlap to semantic similarity to task-specific checks, each measuring something different and each with blind spots. Picking the wrong metric is worse than no metric: it gives you a confident number that points the wrong way.*

The previous post argued that measurement is the bottleneck. This one is about the measurement itself: the kinds of metrics available, what each actually captures, and where each fails. There is no universal "quality score" for language, so the real skill is matching a metric to what you care about — and knowing what it silently ignores.

## Start from the task, not the metric

The first mistake is reaching for a metric because it's popular. The right order is reversed: **define what a good output looks like for your specific task, then find a metric that captures it.** "Summarize this ticket" and "extract the order ID" and "answer this support question" have completely different notions of correct, and no single metric serves all three. Ask: is there one right answer or many? Does format matter? Does faithfulness to a source matter more than fluency? Are some errors catastrophic and others cosmetic? Your answers select the metric family.

## Exact and structural matching

The simplest metrics check whether the output *is* a specific value, and they're the strongest when they apply.

- **Exact match** — the output must equal the reference string (often after normalizing whitespace and case). Perfect for closed tasks: a classification label, a yes/no, a canonical short answer. When there genuinely is one right string, exact match is unambiguous and cheap. When there isn't, it's uselessly harsh — a correct summary phrased differently scores zero.
- **Structural / format checks** — does the output parse as valid JSON? Does it match the required schema? Does it contain the required fields? These are boolean and cheap, and they matter enormously for LLM systems that feed downstream code. A response can be *content-perfect* and still break your pipeline because it wrapped the JSON in prose. Format validity is often the first metric worth adding, because format failures are common and catastrophic.
- **Rule-based assertions** — regex matches, "contains this substring," "is under N tokens," "doesn't mention competitors." Narrow but precise; excellent as guardrails and for verifiable sub-properties.

These share a virtue — they're deterministic and unarguable — and a limit: they only work when correctness reduces to a checkable pattern.

## Reference-based overlap metrics

For open-ended text with reference answers, older NLP metrics score *overlap* between the output and one or more references.

- **BLEU** (from machine translation) measures n-gram precision: how many of the output's word sequences appear in the reference. **ROUGE** (from summarization) emphasizes recall: how much of the reference's content the output captured.
- **Token-level F1** balances precision and recall over shared tokens — common in question answering.

Their appeal is that they're automatic, fast, and reproducible. Their weakness is fundamental: **they measure surface word overlap, not meaning.** A paraphrase that's perfectly correct but uses different words scores low; a fluent answer that overlaps the reference but is subtly wrong scores high. They also depend heavily on having good references, and on how many. Treat these as *cheap proxies* — useful for tracking relative change on tasks with references, misleading if trusted as absolute quality.

## Semantic similarity

To get past surface overlap, semantic metrics compare *meaning* using embeddings. You embed the output and the reference into vectors and measure their distance (typically cosine similarity); approaches like BERTScore align tokens by embedding similarity rather than exact match.

This fixes the paraphrase problem — two ways of saying the same thing land near each other in vector space, so a correct rephrasing scores high. The cost is that "semantically similar" is not "correct": an answer can be on-topic and close in embedding space while being factually wrong, because embeddings capture aboutness, not truth. Semantic similarity is a better proxy than n-gram overlap for "did it say roughly the right thing," but it still can't catch a confident, on-topic falsehood.

## Task-specific and functional metrics

Often the best metric isn't about the text at all — it's about whether the output *does its job*. These tend to be the most meaningful because they measure the outcome you actually care about:

- **Functional correctness** — for code generation, does the generated code *pass the tests*? This sidesteps text comparison entirely: run it and see. It's the gold standard where it's available.
- **Downstream success** — did the extracted order ID retrieve the right order? Did the SQL the model wrote return the correct rows? Ground the metric in the real effect.
- **Faithfulness / groundedness** — for RAG and summarization, is every claim supported by the source? This targets hallucination directly and is often more important than fluency.
- **Task-completion rate** — for agents, did it accomplish the goal? (The subject of dedicated agent-eval work.)

Functional metrics require more setup — you need tests, ground-truth outcomes, or a way to check grounding — but they measure what matters instead of a proxy for it.

## No single number: use a suite

The deepest lesson is that **one metric is never enough.** Quality is multidimensional, and any single score hides trade-offs. A model can be more accurate but slower, more fluent but less faithful, better on average but worse on the edge cases that matter. Serious evaluation reports a *suite*: correctness *and* format-validity *and* faithfulness *and* latency *and* cost *and* safety — whichever dimensions your task cares about — and looks at the whole vector, not a weighted average that hides the tensions.

This also guards against the failure mode of optimizing a proxy into meaninglessness. If you crush a single metric, you'll often find you've gamed it rather than improved quality — a preview of the contamination and Goodhart's-law problems later in this series. A suite of complementary metrics, each with different blind spots, is far harder to fool than any one of them. Choose metrics that measure genuinely different things, know what each ignores, and read them together.

## Key takeaways

- **Choose the metric from the task, not the other way around** — closed vs. open-ended, format-sensitive, faithfulness-critical, and catastrophic-vs-cosmetic errors all select different metric families.
- **Exact match and structural/format checks** are deterministic and unarguable — ideal for labels, schemas, and verifiable properties — but useless when many answers are acceptable.
- **Reference-overlap metrics (BLEU/ROUGE/F1)** are cheap and automatic but measure *word overlap, not meaning*, so they punish correct paraphrases and reward on-topic-but-wrong text.
- **Semantic similarity** (embeddings/BERTScore) fixes the paraphrase problem but still can't distinguish "about the right thing" from "actually correct" — it can't catch a confident falsehood.
- **Task-specific/functional metrics** — code passing tests, downstream success, faithfulness to sources, task-completion — measure the outcome you care about rather than a text proxy, and are usually the most meaningful when you can set them up.
- **Never rely on one number**: report a *suite* of complementary metrics (correctness, format, faithfulness, latency, cost, safety) and read the whole vector — it's more informative and much harder to game.

## Further reading

- [MMLU: Measuring Massive Multitask Language Understanding — Hendrycks et al., arXiv:2009.03300](https://arxiv.org/abs/2009.03300)
- [RAGAS: Automated Evaluation of RAG — Es et al., arXiv:2309.15217](https://arxiv.org/abs/2309.15217)
