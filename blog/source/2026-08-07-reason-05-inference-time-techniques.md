# Inference-Time Techniques: Spending Compute for Accuracy

*A reasoning model thinks harder on its own — but you can spend test-time compute on top of any model, reasoning or not, to squeeze out more accuracy. Generate many answers and vote. Generate many and pick the best with a verifier. Search a tree of reasoning steps, pruning the bad branches. These techniques share one shape — do more work at inference, then choose well — and understanding them turns test-time compute from a model property into a toolkit you control.*

The test-time-compute post named the family of techniques for spending inference compute; this post details the main ones you can apply *at inference*, on top of a model: **best-of-N sampling**, **self-consistency**, **verifiers and reward models**, and **search**. These are how you turn extra compute into extra accuracy explicitly, whether the underlying model reasons natively or not. Knowing them lets you build systems that spend compute deliberately where accuracy matters.

## Best-of-N and self-consistency: sample, then select

The simplest inference-time techniques generate *multiple* candidate answers and select among them — trading N× the compute for better accuracy:

- **Self-consistency (majority vote).** Generate N independent chains of thought (with sampling randomness so they differ), then take the *most common final answer*. Correct reasoning tends to converge on the same answer while errors are idiosyncratic and scattered, so the majority answer is more reliable than any single one. This needs no extra machinery — just sampling and counting — and works well when answers are discrete and comparable (a number, a multiple-choice letter).
- **Best-of-N (with a scorer).** Generate N candidate answers and *pick the best one* according to some scoring function — often a **verifier** or **reward model** (below) that estimates which candidate is most likely correct. Unlike majority vote, best-of-N can select a *correct minority* answer if the scorer recognizes its quality, and it works for open-ended outputs where "majority vote" doesn't apply (you can't vote on essays, but you can score them).

```text
Sample-then-select:
   problem → generate N candidates (sampling) → [c1, c2, ... cN]
   self-consistency: return the most frequent answer
   best-of-N:        return argmax(scorer(ci))  ← needs a good scorer
```

Both spend compute (generate N instead of 1) to raise accuracy, and both illustrate the core pattern: **generation is cheap and imperfect; selecting among many generations is where the gain is.** The quality of best-of-N hinges entirely on the scorer — a good verifier makes best-of-N powerful; a bad one wastes the samples. Which is why verifiers matter.

## Verifiers and reward models

A **verifier** (or reward model) is a model that *scores* candidate solutions — estimating how likely a solution is correct, or how good the reasoning is. Verifiers are the key to spending compute well, because *generating* candidates is easier than *knowing which is right*, and a verifier supplies that judgment:

- **Why verification is easier than generation.** For many problems, *checking* a candidate answer is easier than *producing* the right one — the classic asymmetry (it's easier to verify a proof than to find it). A verifier exploits this: let the (imperfect) generator produce many candidates, and use a verifier to identify the good ones. You get generator throughput plus verifier judgment.
- **Outcome vs process verifiers.** An **outcome reward model (ORM)** scores the *final answer*; a **process reward model (PRM)** scores the *reasoning steps* (the training post's distinction). A PRM can catch a solution that reaches a right answer via flawed steps, or identify where reasoning went wrong, giving finer selection. "Let's Verify Step by Step" showed process verifiers can select correct solutions more reliably than outcome verifiers in best-of-N settings.
- **How they're used at inference.** Verifiers power best-of-N (pick the highest-scored candidate) and guide search (below — score partial solutions to decide which branches to expand). A strong verifier is often the difference between test-time compute that pays off and compute wasted on candidates you can't rank.

Verifiers embody a deep idea: **decouple generating from judging.** A system that generates many candidates and verifies well can be much more accurate than one that must get it right in a single generation — because it converts the hard problem of "produce the correct answer" into the easier problem of "produce many candidates and recognize the correct one." This generate-and-verify decomposition recurs throughout inference-time scaling.

## Search: exploring the space of reasoning

The most structured way to spend inference compute is **search** — treating reasoning as exploring a *tree* of possibilities rather than committing to one path:

- **Reasoning as a tree.** Instead of generating one linear chain of thought, consider reasoning as a tree: at each step there are multiple possible next steps (branches), forming a tree of partial solutions. A single chain of thought is just one path through this tree; search explores *many* paths.
- **Tree of Thoughts.** The **Tree of Thoughts** approach generalizes chain-of-thought into deliberate tree search: generate multiple candidate next steps, *evaluate* partial solutions (often with the model or a verifier), *expand* promising branches, and *backtrack* from dead ends — exploring and pruning the space of reasoning. This lets the model deliberate, look ahead, and abandon bad approaches, rather than being stuck on one linear chain that might go wrong early.
- **Guided by evaluation.** Effective search needs a way to evaluate partial progress (a verifier or the model's own judgment) to decide which branches are worth expanding — otherwise the tree explodes. So search combines generation (candidate steps), evaluation (scoring partial states), and a search strategy (which branches to pursue, how deep). More compute = a broader/deeper search = better solutions on hard problems.

Search is the richest form of test-time compute: it spends compute *exploring* the solution space with lookahead and backtracking, which can solve problems that no single chain of thought reaches. It's more complex and expensive than sampling-and-voting, but for hard problems with a large solution space (planning, complex proofs, puzzles), structured search can be far more effective than linear reasoning. It's also computationally intensive — a genuine "spend a lot of compute" technique.

## Choosing and combining techniques

These techniques form a toolkit, and using test-time compute well means choosing and combining them for the problem:

- **Native reasoning first.** A trained reasoning model already does a lot of this internally (long chains, self-correction, some implicit exploration). Often the simplest "inference-time technique" is just using a reasoning model with appropriate reasoning effort. The explicit techniques below add *more* on top.
- **Self-consistency for discrete answers.** When the answer is a discrete value you can vote on (math answer, classification), majority vote over N samples is simple and effective — no verifier needed.
- **Best-of-N when you have a verifier.** When you can score candidates (a verifier/reward model, test cases for code, a checker), generate N and pick the best — especially for open-ended outputs where voting doesn't apply. As good as your verifier.
- **Search for large solution spaces.** When the problem benefits from exploration, lookahead, and backtracking (complex planning, puzzles), tree search spends compute most effectively — at higher complexity and cost.
- **Combine them.** These compose: a reasoning model with best-of-N sampling and a process verifier; search guided by a reward model; verify-and-revise loops. Real systems mix techniques, spending more compute (and money and latency) as accuracy demands rise.

The unifying principle across all of them: **generate more, and choose well** — spend inference compute to produce and then select (or search over) candidates, converting compute into accuracy. Generation is imperfect but cheap; the leverage is in verification, voting, and search. Next: the economics — because all this compute has a cost, and knowing when the accuracy is worth the money and latency is the practical crux.

## Key takeaways

- Inference-time techniques spend test-time compute on top of *any* model via one shared shape — "generate more, then choose well": self-consistency (sample N chains, majority-vote the answer) and best-of-N (sample N, pick the best by a scorer) trade N× compute for accuracy.
- Self-consistency needs no extra machinery and suits discrete, votable answers; best-of-N works for open-ended outputs and can select a correct *minority* answer — but is only as good as its scorer.
- Verifiers/reward models score candidates and are the key to spending compute well, exploiting that verifying is often easier than generating; outcome reward models score final answers while process reward models score reasoning steps (finer, can catch right-answer-wrong-reasoning) — they power best-of-N and guide search.
- The deep idea is decoupling generation from judging: a system that generates many candidates and verifies well beats one that must get it right in a single shot, converting "produce the correct answer" into the easier "produce many and recognize the correct one."
- Search (Tree of Thoughts) is the richest form — treat reasoning as a tree, generate candidate steps, evaluate partial solutions, expand promising branches, backtrack from dead ends — solving problems no single chain reaches, at higher cost; choose techniques by problem (native reasoning, self-consistency, best-of-N, search) and combine them, spending more compute as accuracy demands.

## Further reading

- [Tree of Thoughts: Deliberate Problem Solving with LLMs (Yao et al., 2023)](https://arxiv.org/abs/2305.10601)
- [Self-Consistency Improves Chain of Thought Reasoning (Wang et al., 2022)](https://arxiv.org/abs/2203.11171)
- [How reasoning models are trained (previous post)](/blog/posts/reason-04-training-reasoning-models.html)
