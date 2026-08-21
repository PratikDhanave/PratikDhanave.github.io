# Fine-Tuning in Production

*Training a good fine-tune is the easy half. Running it in production — deciding it's even worth it, serving adapters efficiently, keeping it from going stale as base models leap ahead, and re-tuning as your needs shift — is where fine-tuning becomes an ongoing commitment rather than a one-time project. This is the reality check that closes the series.*

The series has taken you from *whether* to fine-tune through the techniques (LoRA, QLoRA), the data, alignment, and evaluation. This final post covers living with a fine-tuned model in production: the lifecycle, serving, the maintenance burden, and the honest verdict on when fine-tuning pays off. Because a fine-tune is not a deliverable you finish — it's an artifact you *own and maintain*, and understanding that commitment is the last piece of using fine-tuning well.

## Fine-tuning is a lifecycle, not a task

The framing that matters most: a fine-tuned model is a **frozen artifact**, and the world around it keeps moving. Your task evolves, your data grows, and — critically — **base models keep improving**, sometimes dramatically. A fine-tune that beat the base model today can be worse than *next quarter's* base model with a good prompt. This makes fine-tuning an ongoing lifecycle:

```text
  define behavior → curate data → fine-tune (LoRA/QLoRA) → evaluate vs base
        ▲                                                        │
        └────────── re-tune as data grows / base models improve ─┘
```

You re-enter this loop when your data improves, your requirements change, or a better base model arrives that you want your fine-tune's behavior on top of. This is a real, recurring cost that prompting and RAG *don't* have — they ride base-model upgrades for free, while a fine-tune must be *redone* to benefit. Budgeting for that ongoing re-tuning is part of choosing fine-tuning honestly.

## Serving fine-tuned models

How you deploy depends on the technique, and the LoRA adapter model (from earlier posts) shapes the options:

- **Merged model** — merge the LoRA adapter into the base weights to produce a standalone fine-tuned model, served like any model (the serving techniques from the LLM Inference series apply directly). Simplest to reason about; one model per fine-tune to host.
- **Base + hot-swappable adapters** — keep the base model loaded once and serve *multiple* LoRA adapters on top, swapping per request. This is the powerful multi-tenant pattern: one base model in memory serves dozens of "fine-tuned models" (one adapter per customer/task), because adapters are tiny (the LoRA post). Some serving stacks support this adapter-multiplexing directly, and it dramatically cuts the cost of offering many fine-tunes.
- **Managed fine-tuning** — many model providers offer fine-tuning as a service: you upload data, they train and host the fine-tuned model behind an API. This trades control and portability for not operating the training/serving yourself — the managed-vs-self-host trade-off from the AI Architecture Decisions series, applied to fine-tuning.

The adapter approach is fine-tuning's serving superpower: because a fine-tune is a megabyte-scale adapter, not a full model, you can offer per-customer or per-task specialization at a fraction of the cost of hosting separate models — provided your serving stack supports adapter multiplexing.

## The maintenance burden

Owning a fine-tune means owning its upkeep, and these costs are easy to underestimate at the start:

- **Re-tuning as base models improve.** The big one — you must periodically re-evaluate whether a newer base model plus your fine-tune (or even just a good prompt on the newer base) beats your current fine-tune, and re-tune to stay current. A fine-tune left alone ages.
- **Data and behavior drift.** As real inputs shift and your requirements evolve, the fine-tune trained on old data/behavior degrades in relevance; you refresh the dataset and re-tune.
- **Versioning and reproducibility.** You must version the base model, the dataset, the training config, *and* the resulting adapter together, so you can reproduce and roll back — an MLOps discipline (the AI production series) beyond normal software versioning.
- **Evaluation on every iteration.** Every re-tune needs the full evaluation from the last post (vs. base, general capabilities, held-out set) — you can't skip it because "it worked last time"; each iteration is a new model.
- **Monitoring in production.** Because you can't fully observe a model's quality from outputs alone, you need production monitoring (privacy-respecting) to catch degradation over time.

None of this is prohibitive, but it's *ongoing*, and it's why the first post insisted fine-tuning be a last resort after prompting and RAG: those alternatives don't carry this maintenance tail.

## The honest verdict: when fine-tuning pays off

Pulling the whole series together into a decision. Fine-tuning is worth its cost and maintenance when:

- **It's a behavior problem, not a knowledge problem** (post one) — format, style, a narrow skill, tone — and RAG/prompting genuinely can't deliver it reliably.
- **You have, and can maintain, quality data** (post five) — the determinant of success, and a recurring input for re-tuning.
- **The behavior is stable and valuable enough** to justify the lifecycle cost — a core, lasting capability, not a passing need.
- **The efficiency or quality gain is real and measured** (post seven) — a cheaper fine-tuned small model beating a prompted big one, or a quality lift you've proven against the base model.
- **You can serve it well** — ideally via adapters for multi-task/tenant economics, or via a managed service.

And it's *not* worth it when: prompting or RAG solves the problem (most of the time), the data isn't there, the need is transient, or you can't commit to the maintenance. The mark of maturity is choosing fine-tuning deliberately for the cases that fit — and *not* reaching for it when a prompt or a retrieval step would do, which is more often than the hype suggests.

## The series in one arc

Fine-tuning, end to end: decide it's a *behavior* problem worth fine-tuning (not knowledge → RAG, not solvable by prompting); locate it on the spectrum (usually SFT, sometimes alignment); make it affordable with LoRA and QLoRA; invest overwhelmingly in a clean, representative dataset; add DPO alignment if judgment quality matters; evaluate rigorously against the base model and for forgetting; and then own the production lifecycle of serving, maintenance, and re-tuning. Done with that discipline, fine-tuning is a precise, powerful tool for shaping model behavior. Used without it — for knowledge, on bad data, without evaluation, without maintenance — it's an expensive way to get a worse model. The whole series is really one message: fine-tune deliberately, on great data, for behavior, and measure everything.

## Key takeaways

- A fine-tune is a frozen artifact in a moving world — your task evolves and base models keep improving — so fine-tuning is an ongoing lifecycle of re-tuning, not a one-time task; prompting and RAG ride base-model upgrades for free, a fine-tune must be redone.
- Serving options follow the adapter model: merge the LoRA adapter into a standalone model, or (the superpower) keep one base model loaded and hot-swap tiny per-task/per-tenant adapters for cheap multi-tenant specialization; managed fine-tuning trades control for not operating it yourself.
- The maintenance burden is real and ongoing: re-tuning as base models improve, refreshing on data/behavior drift, versioning base+data+config+adapter together, re-evaluating every iteration, and monitoring in production.
- Fine-tuning pays off when it's a behavior problem prompting/RAG can't solve, you have and can maintain quality data, the behavior is stable and valuable, the gain is measured against the base model, and you can serve it well (adapters or managed).
- The series' one message: fine-tune deliberately (last resort after prompting and RAG), for behavior not knowledge, on a great dataset, with alignment only if judgment matters, measuring everything against the base model — otherwise it's an expensive way to get a worse model.

## Further reading

- [Evaluating a fine-tuned model (previous post)](/blog/posts/finetune-07-evaluation.html)
- [What fine-tuning is and when to use it — start of the series](/blog/posts/finetune-01-what-fine-tuning-is.html)
- [LLM Inference and Serving series — serving the model you fine-tuned](/blog/series/llm-inference-and-serving/)
