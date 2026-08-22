# Model Selection and Prompt Audits

*Model selection is the most commonly botched cost decision, because the intuitive answer — pick the cheaper model — is measured by the wrong number. The right number is cost per completed task, and by that measure the more capable model often wins. Paired with it is the least-known lever of all: auditing prompts written for an older model against your current one.*

Two levers here, closely related. **Model selection** — choosing which model runs a task — is the decision teams get wrong most often. And **prompt auditing** — re-checking prompts written for older models — is the lever almost no one knows about, yet it's the one most likely to apply to an existing codebase. Both hinge on measuring cost correctly. Figures throughout are vendors' own directional numbers; verify on your workload.

## Model selection: the median-vs-tail trap

Every vendor now says the same thing in different words. AWS's GENCOST01-BP01 is "right-size model selection to optimize inference costs." Google points to Model Garden's 160+ models so you can match model to use case, and suggests using a lightweight model (like a small Flash model) to summarize context *before* an expensive call. Anthropic puts the core insight most sharply: **a more capable model finishes a task with fewer turns, less searching, and less backtracking — "the per-token premium is routinely overwhelmed by doing less of everything."**

That last point is the crux, and it's why cheap-per-token is the wrong lens. The intuitive move — pick the model with the lowest per-token price — measures the wrong thing. What matters is **cost per *completed task***, not cost per token, and a pricier model that solves the task in fewer steps can cost *less* per task despite a higher per-token rate. Anthropic's measured example: on a research benchmark, the frontier model at *low* effort was both *more accurate* and ~10% *cheaper per task* than the mid-tier model. The expensive model did less of everything (fewer turns, less searching) and netted cheaper.

But — and this is the honest caveat — **it doesn't always win.** On a coding subset, a mid-tier model matched a frontier model's accuracy at ~60% of its cost. So the answer isn't "always use the frontier model" any more than it's "always use the cheap one." The answer is: **measure cost per completed task on your own workload**, because which model is cheaper *per task* depends on the task, and it's frequently the opposite of what per-token pricing suggests.

## Price the tail, not the median

The practice that matters most in model selection is subtle and decisive: **price the tail, not the median.** On any batch of tasks, the *typical* task looks similar across models and the cheapest model looks best — but the bill is decided by the tasks the cheap model *fails*. Anthropic's measured example: on a 20-problem run, **two problems carried 43% of total spend.** A small number of hard tasks dominate the bill.

Why does failure drive cost so much? Because a failed task bills its tokens, *then* the retry bills again, *then* there's the downstream cost of the failure (a human fixing it, a bad result propagating). So the cheap model's failures cost far more than its per-token savings on the easy tasks. Evaluating a model on the *median* task hides this entirely — the median looks fine on every model. You have to look at the *tail*: how the model does on the hard tasks that carry the spend and drive the failures. **The cheap model is only cheap if it doesn't fail the expensive tasks** — and whether it does is a tail question, not a median one. This reframes model selection from "compare average cost" to "compare cost including the tail of failures," which is the number that actually decides the bill.

Related tooling automates parts of this: AWS Bedrock Intelligent Prompt Routing (route each request to an appropriate model) and Model Distillation (train a smaller model to match a larger one on your task) are vendor mechanisms for getting the right model per request.

## Prompt auditing: the least-known lever

The second lever is the one almost no one knows, and it's the most likely to apply to an *existing* codebase: **audit your prompts against your current model.** Over time, prompts accumulate instructions written for *older* models — "verify twice," "be maximally thorough," mandatory step-by-step procedures, hand-rolled reasoning scratchpads. These made sense for the model they were written for. A *newer* model follows them literally, producing extra tool rounds and extra output *for no accuracy gain* — you're paying for instructions the new model doesn't need.

Anthropic's measured findings are striking:

- Prompts written for one model generation cost ~**36% more per ticket** on the next generation for *no change in accuracy* — pure waste from stale instructions.
- Removing a single instruction ("verify twice") cut cost per ticket by ~a third, and made the model both cheaper *and* more accurate.
- A migration between model generations, audited, took ~14% off at equal accuracy.

There are **two distinct failure modes** to look for, and they fail in opposite ways:

- **Instructions the new model over-obeys** — directives like "verify twice" or "be exhaustive" that a capable new model follows too literally, doing redundant work. These cost *money* (extra tokens, extra tool rounds) for no benefit.
- **Text that no longer fits the model** — retired settings, contradictory rules, hand-rolled scratchpads the model no longer needs. These cost *accuracy* (they confuse or constrain the model).

The practice: **re-run a prompt audit at every model change.** When you upgrade models, don't just swap the model and assume your prompts still fit — audit them for stale instructions the new model over-obeys or is confused by. It's the least-known lever because prompts feel "done," but they're written for a moving target, and a model upgrade is exactly when they go stale. This is often the highest-ROI cost lever for an established codebase, because the waste is invisible until you look.

## Putting model selection and audits together

These two levers combine into a disciplined approach to the model layer:

- **Choose the model by cost per completed task, measured on your workload** — not by per-token price, and not by median-task performance. Include the tail of failures, because a few hard tasks and the cheap model's failures on them decide the bill.
- **Don't assume the frontier or the cheap model wins** — it's task-dependent (frontier cheaper-per-task on some, mid-tier sufficient on others), so measure, and consider routing (Intelligent Prompt Routing) or distillation to get the right model per request.
- **Audit prompts at every model change** — remove stale instructions the new model over-obeys (cost) or is confused by (accuracy); this least-known lever often yields the biggest win on existing codebases (~36% waste from stale prompts in one measured case).
- **Use a cheap model for the cheap parts** — summarizing context before an expensive call (Google's suggestion) is a form of right-sizing: the expensive model only does the expensive part.

Model selection and prompt audits are where measuring the *right* number (cost per completed task, including the tail) beats the intuitive-but-wrong number (cost per token, on the median). The next post covers two more levers of control — effort tuning and budgets — including a cap that silently costs money.

## Key takeaways

- Model selection is the most botched cost decision because the intuitive metric (cost per token) is wrong; the right metric is cost per *completed task*, and a more capable model often wins by finishing in fewer turns/searches ("the per-token premium overwhelmed by doing less of everything") — measured ~10% cheaper per task AND more accurate in one case.
- It doesn't always favor the frontier model (a mid-tier matched it at ~60% cost on a coding subset), so measure cost per completed task on your own workload — which model is cheaper per task is task-dependent.
- Price the tail, not the median: on a 20-problem run two problems carried 43% of spend — the bill is decided by the tasks the cheap model *fails* (failed tokens + retry + downstream cost), which median evaluation hides; the cheap model is only cheap if it doesn't fail the expensive tasks.
- Prompt auditing is the least-known lever and most likely to apply to existing code: prompts accumulate stale instructions for older models that a new model over-obeys (~36% more cost for no accuracy gain) or is confused by — re-run an audit at every model change.
- Combine them: pick models by measured cost-per-completed-task including the tail, use routing/distillation to right-size per request, audit prompts on every upgrade (often the biggest win on established codebases), and use cheap models for cheap sub-tasks like context summarization.

## Further reading

- [Batching and token hygiene (previous post)](/blog/posts/aicostplay-03-batching-and-token-hygiene.html)
- [AWS Bedrock — cost optimization (routing, distillation)](https://docs.aws.amazon.com/bedrock/)
- [AI Architecture Decisions: RAG vs fine-tuning, and model choice](/blog/posts/ai-decisions-04-rag-vs-finetune.html)
