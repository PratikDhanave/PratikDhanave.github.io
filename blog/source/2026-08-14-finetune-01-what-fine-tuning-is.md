# What Fine-Tuning Is and When to Use It

*Fine-tuning is the most misunderstood tool in the LLM toolkit. Reach for it to teach a model new facts and you'll waste weeks and get worse results than a day of RAG. Reach for it to change how a model behaves — its format, tone, or a narrow skill — and nothing else comes close. The whole discipline starts with knowing which problem you actually have.*

Fine-tuning — continuing to train a pretrained model on your own data — is powerful, expensive, and constantly used for the wrong reasons. This series covers how it works (LoRA, QLoRA, data, alignment, evaluation, production), but it opens with the single most important decision: *whether to fine-tune at all*. Get that wrong and every technique after it is wasted effort, so this post is about what fine-tuning is, what it's for, and when something simpler is the right answer.

## What fine-tuning actually is

A base LLM is pretrained on enormous general text, learning language and broad knowledge. **Fine-tuning** takes that pretrained model and trains it *further* on a smaller, targeted dataset, adjusting its weights to specialize it. You're not building a model from scratch — you're nudging an existing one toward your task, which is why it needs far less data and compute than pretraining.

The critical thing to understand is *what that adjustment does well*. Fine-tuning is excellent at shaping **behavior**: the *way* a model responds — its output format, tone, style, structure, and its skill at a specific narrow task. It changes patterns the model has learned to produce. What it is *not* good at is reliably injecting **knowledge**: teaching the model new facts it can recall accurately. This distinction is the entire key to using fine-tuning correctly, and it's where most teams go wrong.

## The rule: RAG for knowledge, fine-tuning for behavior

The most useful heuristic in applied LLMs, and the one this series returns to constantly:

- **RAG (retrieval) is for knowledge** — giving the model *facts*: your documents, current data, domain information it needs to answer from. Retrieval puts the right information in the context at query time.
- **Fine-tuning is for behavior** — shaping *how* the model acts: always output valid JSON in your schema, adopt a specific voice, follow your classification taxonomy, perform a narrow task reliably.
- **Long context** is a third option — just putting information directly in the prompt — a convenience for modest amounts of data, not a strategy for large or changing knowledge.

Why not fine-tune in knowledge? Because facts learned via fine-tuning are baked into weights unreliably — the model may recall them wrong, mix them up, or hallucinate confidently, and updating a fact means retraining. Facts *retrieved* via RAG are accurate, current, updatable instantly, and citable. So the failure mode to avoid is fine-tuning a model on your company documents hoping it will "know" them — it won't reliably, and RAG would do it better, faster, and cheaper. Conversely, RAG can't make a model consistently output your exact format or adopt a skill — that's fine-tuning's job. (The [RAG-vs-fine-tune decision](/blog/posts/ai-decisions-04-rag-vs-finetune.html) in the AI Architecture Decisions series works this through in depth.)

## When fine-tuning is the right tool

Fine-tuning earns its cost when you need to change behavior in ways prompting can't reliably achieve:

- **Consistent output format or structure** — reliably producing a specific JSON schema, a particular style, or a fixed structure, especially at scale where prompt-based formatting is fragile.
- **A specialized narrow task** — classification, extraction, or a domain-specific transformation where a fine-tuned smaller model matches or beats a large general model with a long prompt.
- **Tone and voice** — a consistent brand voice or persona that's hard to hold with prompting alone.
- **Efficiency** — a fine-tuned small model can do a narrow task as well as a big prompted model, but cheaper and faster (baking the instructions into weights means shorter prompts and a smaller model — connecting to the cost and serving series).
- **A skill or behavior the base model lacks** — teaching a genuinely new *capability* or response pattern, not new facts.

The common thread: you want to change *how* the model responds, consistently, in a way that prompting can't reliably or affordably deliver.

## When NOT to fine-tune (usually)

Because fine-tuning is expensive (data, compute, expertise, maintenance), the default should be to *avoid* it until simpler options are exhausted:

- **Try prompting first.** A better prompt, few-shot examples, or clearer instructions solve a huge fraction of "the model doesn't do what I want" problems — for free, instantly, with no training. Exhaust prompt engineering before fine-tuning.
- **Use RAG for knowledge problems.** If the issue is "the model doesn't know X," that's retrieval, not fine-tuning.
- **Don't fine-tune for facts that change.** Anything current or frequently updated belongs in retrieval, not weights.
- **Don't fine-tune without enough good data.** Fine-tuning needs quality task-specific examples; without them you'll degrade the model, not improve it (the data post covers this).
- **Consider the maintenance cost.** A fine-tuned model is a frozen artifact — as base models improve, your fine-tune ages, and you must re-tune to benefit. RAG and prompts ride base-model upgrades for free.

The disciplined order is: **prompt engineering → RAG → fine-tuning**, escalating only when the simpler tool genuinely can't do the job. Fine-tuning is the last resort, not the first, precisely because it's the most expensive and least reversible.

## The honest decision framework

Before fine-tuning, ask:

1. **Is this a knowledge problem or a behavior problem?** Knowledge → RAG. Behavior → maybe fine-tuning.
2. **Have I exhausted prompting?** Better prompts and few-shot examples first — they're free and instant.
3. **Do I have enough high-quality task data?** No good data → don't fine-tune yet.
4. **Is the behavior stable?** Fine-tune stable behaviors, not moving targets.
5. **Can I afford the ongoing cost?** Training, evaluation, and re-tuning as base models improve.

If you land on "behavior problem, prompting isn't enough, I have good data, the behavior is stable, and I can maintain it" — fine-tuning is the right tool, and the rest of this series shows how to do it efficiently and well. If not, the simpler tool will serve you better. The whole point of starting here is to make sure the effort ahead is aimed at a problem fine-tuning can actually solve.

## Key takeaways

- Fine-tuning continues training a pretrained model on targeted data to specialize it — and it excels at shaping *behavior* (format, tone, style, a narrow skill) but is unreliable at injecting *knowledge* (facts).
- The governing rule: RAG for knowledge (accurate, current, updatable, citable facts in context), fine-tuning for behavior (how the model responds), long context as a convenience for small data — fine-tuning facts into weights is the classic expensive mistake.
- Fine-tune when you need consistent output format/structure, a specialized narrow task, a specific tone/voice, efficiency (a cheap fine-tuned small model beating a prompted big one), or a genuinely new behavior — all cases of changing *how* the model responds.
- Default to avoiding it: exhaust prompt engineering first (free, instant), use RAG for knowledge, don't fine-tune changing facts or without good data, and account for maintenance (a fine-tune ages as base models improve).
- Follow the order prompt engineering → RAG → fine-tuning; before committing, confirm it's a behavior problem, prompting isn't enough, you have quality data, the behavior is stable, and you can afford ongoing re-tuning.

## Further reading

- [RAG vs Fine-Tuning vs Long Context (AI Architecture Decisions)](/blog/posts/ai-decisions-04-rag-vs-finetune.html)
- [Hugging Face — fine-tuning guide](https://huggingface.co/docs/transformers/en/training)
- [Agentic RAG series — the knowledge alternative](/blog/series/agentic-rag/)
