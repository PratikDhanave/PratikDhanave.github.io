# Chain of Thought: The Idea That Started It

*The observation that launched reasoning models was almost embarrassingly simple: if you ask a language model to "think step by step" before answering, it gets dramatically better at hard problems — with no change to the model at all. That a few words of prompting could unlock reasoning already latent in the model was a clue about something deep: the ability to reason was there, waiting to be elicited, and giving the model room to work was the key.*

Reasoning models generate an extended chain of thought before answering. That idea has a direct ancestor: **chain-of-thought (CoT) prompting**, the discovery that prompting a model to produce intermediate reasoning steps sharply improves its performance on complex tasks. This post traces the idea — what CoT is, why it works, its variants like self-consistency, and how it leads directly from a prompting trick to models *trained* to reason. Understanding CoT is understanding the foundation reasoning models are built on.

## The discovery: step by step helps

The core finding: prompting a model to reason step by step — rather than jump straight to an answer — substantially improves accuracy on problems that require multiple steps (arithmetic, commonsense, symbolic reasoning). Instead of asking "what's the answer?", you prompt the model to "show its work," and it produces a sequence of intermediate reasoning steps leading to the answer. The improvement on multi-step problems was large and surprising:

- **It required no retraining.** The same model, given the same problems, did far better *purely* because it was prompted to generate reasoning first. Nothing about the model changed — only the invitation to think before answering. This was striking: the reasoning capability was already *in* the model; the prompt just unlocked it.
- **It helped most on hard, multi-step problems.** On simple one-step questions CoT made little difference, but on problems needing several steps of reasoning it was transformative — exactly the pattern reasoning models show, and for the same underlying reason.
- **It scaled with model capability.** CoT's benefit emerged strongly in larger, more capable models — smaller models benefited less. This suggested reasoning was an ability that appeared with scale and could be *elicited* once present.

This is the seed of everything that follows: the realization that a model's reasoning ability is partly a matter of giving it *room to reason*, not just what it knows. "Let's think step by step" turned out to be one of the highest-leverage prompts ever found.

## Why generating reasoning helps

Why should writing out intermediate steps make a model *more accurate*? The mechanism connects to how LLMs compute:

- **It decomposes hard problems into easy steps.** Many problems are hard to solve in one leap but easy step by step — each step simple given the previous ones. By generating intermediate steps, the model tackles a sequence of easy sub-problems instead of one hard one, which is far more reliable. The chain of thought is a decomposition mechanism.
- **It gives the model more computation to work with.** Each generated token involves a forward pass through the model. When the model generates a *reasoning* before the answer, it performs many more forward passes — effectively spending *more computation* on the problem. Intermediate tokens are "scratch space" that lets the model do more work before committing. This is the direct link to test-time compute: more reasoning tokens = more compute = better answers on hard problems. (This is *why* CoT is the ancestor of test-time-compute scaling.)
- **It conditions the answer on explicit steps.** Because the model generates the answer *after* the reasoning, the answer is conditioned on those written-out steps — so if the steps are correct, the answer is more likely correct. The model isn't reasoning "in its head" and hoping; it's building the answer on visible, self-generated groundwork.

So CoT isn't cosmetic — it changes the computation. Writing out steps decomposes the problem, spends more compute, and conditions the answer on explicit reasoning. That's why a prompt with no model change can produce large accuracy gains, and it's the same mechanism reasoning models exploit at a much larger scale.

## Self-consistency and sampling many paths

A powerful extension of CoT, and an early form of spending test-time compute for accuracy, is **self-consistency**: instead of generating *one* chain of thought, generate *many* and take the most common answer.

- **The idea.** Sample multiple independent chains of thought for the same problem (using randomness so they differ), then aggregate — typically by *majority vote* over the final answers. Different reasoning paths may make different mistakes, but correct reasoning tends to converge on the same answer, so the most frequent answer across many paths is more likely right than any single path.
- **Why it works.** A single chain of thought can go wrong (a mistake early derails it). Sampling many paths and voting is a form of *ensembling*: errors are often idiosyncratic and cancel out, while correct reasoning agrees. It trades more compute (many samples) for higher accuracy — an explicit test-time-compute technique.

Self-consistency is important as a bridge idea: it shows that you can spend *more inference compute* (generate many reasoning paths) to get *better answers*, without touching the model. This is exactly the test-time-compute principle the next post develops — and self-consistency, best-of-N, and verifier-based selection (a later post) are all variations on "sample more, then choose well." CoT gave one reasoning path; self-consistency showed that many paths plus aggregation is better still.

## From prompting to trained reasoning

CoT prompting revealed reasoning was latent and elicitable — but prompting has limits, and closing them leads directly to reasoning models:

- **Prompting is shallow.** A prompted chain of thought from a standard model is limited: the model wasn't *trained* to reason well, so its steps can be superficial, and it doesn't reliably self-correct or explore alternatives. You're eliciting an ability, not optimizing it.
- **The next step: train the model to reason.** If reasoning helps and is elicitable, why not *train* the model to produce excellent reasoning natively — long, self-correcting, exploratory chains of thought — rather than hoping a prompt elicits them? This is exactly what reasoning models do: they use techniques (reinforcement learning, discussed in a later post — with early precursors like **STaR**, which bootstraps reasoning by training on the model's own successful chains of thought) to make the model *inherently* good at generating effective reasoning.
- **The result is deeper and more reliable.** A trained reasoning model produces far more capable thinking than a prompted standard model — longer, more likely to catch and fix mistakes, more willing to explore approaches. It's the difference between coaxing a latent skill and training that skill to expert level.

So the arc is clear: CoT prompting discovered that reasoning helps and is elicitable; self-consistency showed that spending inference compute on multiple reasoning paths helps more; and reasoning models take the logical next step of *training* the model to reason well and *natively* spend inference compute on thinking. Chain of thought is where it started — a prompt that unlocked reasoning — and the rest is scaling and internalizing that idea. Next: test-time compute, the principle that ties it all together.

## Key takeaways

- Chain-of-thought (CoT) prompting — asking a model to reason step by step before answering — sharply improves accuracy on multi-step problems with *no retraining*, revealing that reasoning ability was already latent in the model and just needed room to be elicited.
- CoT helps most on hard multi-step problems (little effect on simple ones) and emerges with model scale — the same pattern reasoning models show, for the same reason.
- Generating reasoning helps because it decomposes a hard problem into easy steps, spends more computation (each reasoning token is another forward pass — the direct link to test-time compute), and conditions the answer on explicit self-generated groundwork.
- Self-consistency extends CoT by sampling *many* reasoning paths and taking the majority-vote answer — an ensembling effect where idiosyncratic errors cancel and correct reasoning converges — an early, explicit form of spending test-time compute for accuracy.
- The arc runs from prompting to training: CoT prompting is shallow (the model wasn't trained to reason), so reasoning models take the next step and *train* the model (via RL, with precursors like STaR) to natively produce deep, self-correcting reasoning — turning an elicited skill into an optimized one.

## Further reading

- [Self-Consistency Improves Chain of Thought Reasoning (Wang et al., 2022)](https://arxiv.org/abs/2203.11171)
- [STaR: Bootstrapping Reasoning With Reasoning (Zelikman et al., 2022)](https://arxiv.org/abs/2203.14465)
- [What reasoning models are (previous post)](/blog/posts/reason-01-what-reasoning-models-are.html)
