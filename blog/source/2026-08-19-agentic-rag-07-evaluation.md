# Evaluating Agentic RAG

*Every agentic technique in this series adds cost and complexity, so the only way to know any of it is worth it is to measure — and RAG needs measurement on two fronts at once: did it retrieve the right things, and did it answer faithfully from them?*

Agentic RAG is a stack of decisions — transform, route, grade, iterate — each of which adds cost and could help or hurt. Without evaluation you are guessing that the machinery improves answers, and guessing wrong means paying more for worse. RAG is also uniquely hard to evaluate because a good answer requires two independent things to go right: good retrieval and faithful generation. This seventh post in the Agentic RAG series covers how to evaluate RAG systems and the agentic loops on top of them.

## Two failure surfaces, two sets of metrics

A RAG answer can be wrong for two fundamentally different reasons, and conflating them makes debugging impossible:

- **Retrieval failed** — the right information was never fetched, so no amount of good generation could produce a correct answer.
- **Generation failed** — the right information *was* retrieved, but the model ignored it, contradicted it, or hallucinated beyond it.

These need separate metrics, because the fixes are opposite (improve retrieval vs. improve grounding). The widely-used framing splits into:

- **Context relevance / precision** — of what was retrieved, how much is actually relevant to the question? Low means the retriever is pulling noise.
- **Context recall** — of the information needed to answer, how much was retrieved? Low means the retriever is missing the answer.
- **Faithfulness / groundedness** — are the answer's claims actually supported by the retrieved context? Low means the model is hallucinating or contradicting its sources.
- **Answer relevance** — does the answer actually address the question asked? Low means the model wandered even if grounded.

The first two grade retrieval; the last two grade generation. Tracking all four localizes any failure to the stage that caused it — the single most useful thing an evaluation gives you.

## LLM-as-judge and evaluation tooling

Several of these metrics — faithfulness, answer relevance, context relevance — are hard to compute with string matching but well-suited to an LLM judge: a model scores whether each answer claim is supported by the context, whether retrieved chunks are relevant, whether the answer addresses the question. Frameworks in this space (RAGAS-style evaluation among them) operationalize exactly these RAG-specific metrics so you can score a system systematically rather than eyeballing outputs. The judge must be used carefully — it has the biases and limits covered in the self-critique discussion of the self-evolving-agents series — but for RAG's fuzzy, semantic metrics it is far more practical than exact matching, provided you validate the judge against some human-labeled cases.

## Build an evaluation set

Metrics need data to run on. The foundation is an evaluation set: representative questions paired with the information needed to answer them and, ideally, reference answers. Cover the range you actually serve — simple lookups, multi-part questions, multi-hop chains, and crucially *questions your knowledge base cannot answer* (to test that the system says "I don't know" rather than fabricating). This last category is where naive RAG silently fails and where agentic self-correction is supposed to help, so it must be in the eval or you cannot measure the improvement. Build the set once, and it becomes the ground truth against which every change — a new query transformation, a router tweak, an added correction step — is judged.

## Evaluate the agentic behavior, not just the answer

Beyond answer quality, agentic RAG has *behaviors* worth measuring because they drive cost and are where the agentic logic can go wrong:

- **Routing accuracy** — did queries go to the right source, and (critically) did the system correctly decide *whether* to retrieve at all?
- **Retrieval-correction effectiveness** — when retrieval was poor, did grading catch it and did the correction help?
- **Hop count and termination** — for multi-hop, did the loop use an appropriate number of hops and stop at the right time?
- **Cost and latency per query** — the resource side of every agentic decision.

These turn "the answer was good" into "the system behaved efficiently and correctly," which is what you need to tune the loop rather than just the prompt.

## Measure the trade you are actually making

The reason evaluation is non-negotiable for agentic RAG specifically: every step up the spectrum costs more, so each must justify itself against a baseline. Run naive RAG on the eval set, then add each agentic capability and measure both the quality gain *and* the cost increase. Query transformation might lift answer relevance substantially for little added cost — clearly worth it. Full multi-hop self-correction might lift quality modestly at several times the cost — worth it only for the hard questions, which tells you to apply it selectively. Without this measured comparison you cannot make the central agentic-RAG decision: how much reasoning to add. The evaluation is what converts "agentic RAG is more sophisticated" into "for our questions, these specific capabilities are worth their cost and these are not."

## Key takeaways

- Agentic RAG stacks costly decisions, so evaluation is the only way to know the machinery improves answers rather than just raising the bill.
- A RAG answer fails for two separable reasons — retrieval failed or generation failed — so measure both: context relevance and recall (retrieval) plus faithfulness/groundedness and answer relevance (generation).
- LLM-as-judge (via RAGAS-style tooling) is practical for RAG's semantic metrics, provided you validate the judge against human-labeled cases and mind its biases.
- Build an evaluation set covering simple, multi-part, and multi-hop questions — and especially questions the knowledge base cannot answer, to test honest "I don't know" over fabrication.
- Also evaluate agentic behaviors (routing/whether-to-retrieve accuracy, correction effectiveness, hop count, cost/latency), and measure each capability's quality gain against its added cost versus a naive baseline to decide how much reasoning to add.

## Further reading

- [Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection — Asai et al., 2023](https://arxiv.org/abs/2310.11511)
- [Corrective Retrieval Augmented Generation — Yan et al., 2024](https://arxiv.org/abs/2401.15884)
- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
