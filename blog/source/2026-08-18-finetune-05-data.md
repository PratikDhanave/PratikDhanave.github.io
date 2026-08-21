# Data: The Real Determinant

*You can pick the perfect technique, tune every hyperparameter, and rent the best GPU — and still get a worse model than you started with, because your dataset was mediocre. Fine-tuning quality is decided overwhelmingly by data quality, and a few hundred excellent examples beat tens of thousands of sloppy ones. This is the post that actually determines whether your fine-tune works.*

The last posts made fine-tuning cheap and accessible with LoRA and QLoRA. But the technique is not what makes a fine-tune succeed or fail — **the data is**. The most common reason a fine-tuning project disappoints isn't the method or the hyperparameters; it's a dataset that's too small, inconsistent, poorly formatted, or unrepresentative. This post is about the thing that matters most and gets the least glamour: building the dataset.

## Why data dominates

Fine-tuning teaches the model by example — it learns the patterns in your training data, faithfully, including the bad ones. This has a blunt consequence: **the model becomes your data.** If your examples are inconsistent, the model learns inconsistency. If they contain errors, it learns errors. If they're formatted three different ways, it learns to produce all three. Fine-tuning is a mirror, and it reflects the quality of what you show it.

This is why data quality dominates every other factor. A brilliant technique on a bad dataset produces a bad model; a basic technique (plain LoRA SFT) on an *excellent* dataset produces a great one. The leverage is enormously lopsided toward data — which is exactly backwards from where most people spend their attention (tweaking hyperparameters and methods). If you take one thing from this series about *doing* fine-tuning well, it's: **invest in the dataset first, most, and last.**

## Quality over quantity

The single most important and counterintuitive lesson: **a small number of high-quality examples beats a large number of mediocre ones.** People assume fine-tuning needs huge datasets; for SFT (from the spectrum post), the opposite is often true — a few hundred to a few thousand *carefully crafted* examples frequently outperform tens of thousands of scraped, noisy ones.

Why? Because the model learns behavior from patterns, and clean, consistent examples teach a clean, consistent pattern, while noisy examples teach noise. Adding more mediocre data doesn't average out — it actively teaches the model the flaws. So the priorities:

- **Curate ruthlessly.** A smaller, hand-checked, high-quality dataset beats a larger, unfiltered one. Removing bad examples improves the model more than adding mediocre ones.
- **Every example is a lesson.** Each training pair teaches the model something; a wrong or inconsistent one teaches it something wrong. Treat examples as instruction, not bulk.
- **Consistency is a feature.** If you want a specific format or style, *every* example must exemplify it. Inconsistency in the data becomes inconsistency in the model.

This is liberating: you don't need a massive data operation to fine-tune well — you need a *disciplined* one.

## What makes a good dataset

Concretely, a fine-tuning dataset should be:

- **Representative of real inputs.** The examples must match the distribution of inputs the model will actually see in production. If you train on clean, well-formed inputs but production sends messy ones, the model won't generalize. Include the variety, edge cases, and messiness of real usage.
- **Consistently formatted.** Every example follows the same structure and conventions (especially the output format you want). The model learns the format from the consistency.
- **Correct.** Outputs are actually right — verified, not assumed. Errors in training data are lessons in error.
- **Diverse within the task.** Cover the range of cases the task includes, so the model learns the *task*, not a narrow slice. But diversity *within* the task's real distribution — not random noise.
- **Properly split.** Hold out a **validation/test set** the model never trains on, so you can measure real performance and detect overfitting (the evaluation post). Never evaluate on training data.

The recurring theme is that the dataset should be a faithful, clean, consistent representation of *exactly the behavior you want, on exactly the inputs you'll see*. That's a craftsmanship problem, not a scale problem.

## Getting the data

Where do good examples come from? Several sources, each with caveats:

- **Real production data** — the gold standard, because it's exactly representative. Requires collecting, cleaning, and (critically) respecting privacy and consent for using user data in training. Often the best examples are your real interactions, corrected.
- **Human-created/curated examples** — experts writing ideal input→output pairs. Expensive but high-quality, and often the right investment for a narrow, high-value task.
- **Synthetic data** — using a strong model to *generate* training examples. Increasingly common and powerful for bootstrapping a dataset, but with a crucial caveat: synthetic data must be **checked**, because a generating model can produce plausible-but-wrong examples that would teach the fine-tuned model those errors. Synthetic data is a starting point to curate, not a finished dataset to trust blindly.
- **Existing datasets** — public datasets for common tasks, useful as a base but rarely matching your specific behavior and distribution.

Whatever the source, the *curation* step — reviewing, correcting, filtering, ensuring consistency — is where the quality is made. Raw data of any origin becomes a good dataset only through disciplined curation.

## Practical dataset discipline

- **Start small and clean, then grow deliberately.** Begin with a modest, excellent dataset; expand only with examples that maintain the quality bar. Don't dump in data to hit a number.
- **Enforce format consistency mechanically.** Validate that every example matches the expected structure before training — one malformed batch teaches malformed output.
- **Hold out a real test set** from the start, representative of production, never touched in training.
- **Check synthetic and scraped data by hand** (at least a sample) before trusting it — plausible errors are the dangerous kind.
- **Iterate data, not just hyperparameters.** When a fine-tune underperforms, the first place to look is usually the data — missing cases, inconsistencies, errors — not the learning rate. Improving the dataset is almost always higher-leverage than tuning the method.
- **Respect privacy and consent** when using real user data — a legal and ethical requirement, especially for the sensitive-data apps this blog often discusses.

Data is where fine-tuning projects are won or lost. With a clean, representative, consistent dataset and the efficient techniques from the earlier posts, you can produce a genuinely good fine-tune. The next posts cover pushing quality further with alignment, and — essential — how to *know* whether your fine-tune actually worked.

## Key takeaways

- Fine-tuning quality is dominated by data quality: the model learns your examples faithfully, flaws included, so it *becomes* your data — a great dataset with a basic technique beats a great technique on a bad dataset.
- Quality beats quantity: a few hundred to a few thousand carefully curated, consistent examples typically outperform tens of thousands of noisy ones, because noise is learned as noise, not averaged away.
- A good dataset is representative of real (including messy) inputs, consistently formatted, correct/verified, diverse within the task's true distribution, and split with a held-out test set never used in training.
- Sources — real production data (best but needs privacy/consent), human-curated (expensive, high-quality), synthetic (powerful for bootstrapping but must be checked for plausible errors), public datasets (a base) — all become good only through disciplined curation.
- Practical discipline: start small and clean, enforce format consistency mechanically, hold out a real test set, hand-check synthetic/scraped data, iterate on data before hyperparameters, and respect privacy/consent for user data.

## Further reading

- [QLoRA and quantized fine-tuning (previous post)](/blog/posts/finetune-04-qlora.html)
- [Hugging Face — preparing a dataset](https://huggingface.co/docs/transformers/en/training)
- [AI Cost Optimization series — right-sizing before fine-tuning](/blog/series/ai-cost-optimization/)
