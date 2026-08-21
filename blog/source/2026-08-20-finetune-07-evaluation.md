# Evaluating a Fine-Tuned Model

*A fine-tune that looks great on a handful of hand-picked prompts can be quietly broken — overfit to your training data, worse than the base model you started from, or catastrophically forgetful of skills it used to have. Without real evaluation you can't tell, and shipping a fine-tune you haven't measured is shipping a guess.*

Every previous post built toward a trained, possibly aligned model. This one answers the question that decides whether it's usable: **did it actually work?** Fine-tuning has failure modes that don't announce themselves — overfitting, regression against the base model, catastrophic forgetting — and eyeballing a few outputs won't catch them. This post covers how to evaluate a fine-tune honestly, which is the difference between a fine-tune you *hope* is good and one you *know* is.

## Why fine-tuning needs rigorous evaluation

Fine-tuning is uniquely easy to fool yourself about, for a specific reason: you optimized the model *on your data*, so of course it does well on things that look like your data. The whole risk is that it does well on your *training* examples while failing on real, unseen inputs — or while quietly losing capabilities you didn't test. Casual testing on a few prompts you happen to try will look fine and hide all of this.

So evaluation isn't a formality; it's how you detect the specific ways fine-tuning goes wrong. The non-negotiable foundation, from the data post: **evaluate on a held-out test set the model never trained on**, representative of real production inputs. Measuring on training data tells you nothing except that the model memorized — which it did. Real evaluation means real, unseen, representative data, and it's the only way to know.

## The failure modes to watch for

Fine-tuning has three signature failure modes, and good evaluation is designed to catch each:

- **Overfitting** — the model has memorized the training data rather than learning the general behavior. Signature: excellent on training examples, poor on the held-out test set. The gap between training and test performance *is* overfitting. It comes from too many training epochs, too little/too-narrow data, or too much adapter capacity — and it's why you watch validation performance and stop when it stops improving (even as training loss keeps dropping).
- **Regression against the base model** — the fine-tune is actually *worse* than the model you started from. This is more common than people expect: a mediocre fine-tune on weak data can degrade the base model's abilities. The essential check: **compare the fine-tuned model against the base model** on your evaluation, not just against nothing. If it doesn't beat the base model, the fine-tune failed, and you should not ship it.
- **Catastrophic forgetting** — in gaining your task, the model *loses* other capabilities it had. Fine-tuning hard on a narrow task can erode general abilities, instruction-following, or safety behaviors. Signature: great at the new task, noticeably worse at things it used to do. You catch it by evaluating *general* capabilities too, not only the target task — otherwise you ship a model that nails your task and fails at everything around it. (LoRA/QLoRA's frozen base helps limit this versus full fine-tuning, but it can still happen.)

Each of these is invisible to "try a few prompts and it looks good." They're only caught by structured evaluation against a held-out set, a base-model baseline, and a general-capability check.

## What and how to measure

Evaluation methods depend on the task, and you usually combine several:

- **Task-specific metrics** — for well-defined tasks, quantitative measures: accuracy/F1 for classification, exact-match or field accuracy for extraction, and so on. These give an objective number to compare fine-tuned vs. base vs. previous versions. Use them wherever the task allows a clear right answer.
- **LLM-as-judge** — for open-ended outputs where there's no single correct answer (style, helpfulness, quality), use a strong model to score or compare outputs against criteria, at scale. The same tool from the RAG/production series, with the same caveat: validate the judge against human judgment on a sample, since an unreliable judge gives confident-but-wrong scores.
- **Human evaluation** — the gold standard for quality and preference, especially for aligned models (does it actually feel better?). Expensive, so used on a sample or for the decisions that matter most — but nothing fully substitutes for humans on subjective quality.
- **Pairwise comparison** — rather than absolute scores, compare fine-tuned vs. base (or vs. a previous version) head-to-head ("which response is better?"). Often more reliable than absolute scoring for judging whether the fine-tune is an improvement, and it directly answers the base-model-regression question.

The through-line: pick metrics that match the task, always include a **comparison against the base model** (did fine-tuning help?), and don't rely on a single number — combine an automatic metric, a judge, and some human review for a rounded picture.

## The evaluation discipline

Putting it together into a workflow that catches the failure modes:

1. **Hold out a real test set** before training — representative of production, never seen in training. (From the data post; it starts here.)
2. **Establish the base-model baseline** — measure the un-fine-tuned model on the same test set first, so you can prove the fine-tune improved on it.
3. **Watch validation during training** — track performance on held-out data across epochs; stop when it plateaus or degrades (early stopping) to avoid overfitting, even if training loss keeps falling.
4. **Evaluate the target task** on the test set — with task-specific metrics and/or judge/human evaluation.
5. **Evaluate general capabilities too** — check the model hasn't catastrophically forgotten skills outside the target task.
6. **Compare against the base model** — fine-tuned vs. base, head-to-head. If it doesn't clearly win (task better, general abilities intact), don't ship it — iterate on data (usually) or method.
7. **Iterate on data first.** When evaluation shows problems, the highest-leverage fix is almost always the dataset (the data post) — more/cleaner/more-representative examples — not hyperparameters.

This discipline is what makes fine-tuning an engineering practice rather than a hopeful ritual. It's also the honest gate: a fine-tune that doesn't beat the base model on a real test set, or that forgets general skills, is a failure to catch *before* production, not after.

## Key takeaways

- Fine-tuning is uniquely easy to fool yourself about because you optimized on your own data — so evaluation must use a held-out test set the model never trained on, representative of real inputs; measuring on training data proves only memorization.
- Watch three signature failure modes: overfitting (great on training, poor on test — the train/test gap), regression (the fine-tune is worse than the base model), and catastrophic forgetting (gaining the task while losing other capabilities) — none visible from trying a few prompts.
- Always compare against the base model: if the fine-tune doesn't clearly beat the model you started from on a real test set, it failed and shouldn't ship.
- Measure with task-specific metrics (where there's a right answer), LLM-as-judge (open-ended, validate the judge), human evaluation (gold standard for quality), and pairwise comparison (reliable for "is it better?") — combine several, don't trust one number.
- Follow the discipline: hold out a real test set, baseline the base model, watch validation for early stopping, evaluate both the target task and general capabilities, compare head-to-head against base, and iterate on data first when problems appear.

## Further reading

- [Alignment: RLHF and DPO (previous post)](/blog/posts/finetune-06-alignment-rlhf-dpo.html)
- [Data: the real determinant — where evaluation problems are usually fixed](/blog/posts/finetune-05-data.html)
- [Evaluating Agents in Go series — evaluation harness patterns](/blog/series/evaluating-agents-in-go/)
