# The Fine-Tuning Spectrum

*"Fine-tuning" is not one thing — it's a family of techniques that range from cheaply nudging a model's output format to expensively rebuilding its knowledge base. Confusing them leads to using a sledgehammer for a thumbtack. Knowing where your task sits on the spectrum tells you which technique, how much data, and how much compute you actually need.*

The last post decided *whether* to fine-tune. This one maps the *kinds*, because people say "fine-tuning" to mean wildly different operations with different costs and purposes. From continued pretraining to preference alignment, the spectrum runs from "teach the model a new domain of language" to "make the model prefer one style of answer." This post lays out that spectrum so you can locate your task on it — which is what determines everything downstream.

## The spectrum, end to end

Arrange the techniques by *what they change and how much*:

```text
  more data/compute, broader change ◀───────────────▶ less data/compute, narrower change

  continued        supervised          preference
  pretraining  →   fine-tuning    →    alignment
  (new domain      (SFT: task           (RLHF/DPO: shape
   knowledge/       behavior from        which responses
   language)        input→output         are preferred)
                    examples)
```

Each stage changes the model in a different way, and most applied fine-tuning lives in the middle (SFT), reaching to the right (alignment) for quality. The left end (continued pretraining) is rare and expensive. Let's walk them.

## Continued pretraining: new domain, new language

**Continued pretraining** (also called domain-adaptive pretraining) continues the model's *original* self-supervised training — predicting the next token — but on a large corpus of *your domain's* text: legal documents, medical literature, code in a niche language, a low-resource human language. The goal is to shift the model's fundamental grasp of a domain's *language and patterns*, not to teach a specific task.

This is the heaviest, rarest form of fine-tuning:

- **It needs a lot of data** — large amounts of domain text, closer to pretraining scale than task-example scale.
- **It's expensive** — substantial compute, closer to pretraining cost.
- **It's for when the base model doesn't understand your domain's language at all** — genuinely specialized vocabulary and patterns the model wasn't exposed to.

Most teams never do this. It's justified only when the domain is so specialized that the base model's language understanding itself falls short — and even then, note that it teaches *domain fluency*, not reliable facts (which is still RAG's job). If you're considering continued pretraining, be sure a much cheaper technique to the right won't do.

## Supervised fine-tuning (SFT): the workhorse

**Supervised fine-tuning (SFT)** is what most people mean by "fine-tuning," and it's where the overwhelming majority of applied work happens. You train on **labeled input→output examples** — pairs showing the model exactly what response you want for a given input:

```text
{ "input": "Classify sentiment: 'The service was slow.'",
  "output": "negative" }
{ "input": "Extract the date: 'Meeting moved to March 3rd.'",
  "output": "2026-03-03" }
```

The model learns to produce outputs like your examples — this is how you get consistent format, a narrow skill, a classification taxonomy, or a specific style (the behaviors from the last post). SFT's characteristics:

- **Modest data** — hundreds to thousands of high-quality examples often suffice (far less than pretraining), because you're shaping behavior on top of existing capability.
- **Affordable** — especially with the parameter-efficient methods (LoRA/QLoRA, next posts) that make it runnable on limited hardware.
- **Directly targets behavior** — the input→output examples *are* the behavior you want, so SFT is the precise tool for "make the model respond like this."

**Instruction tuning** is a well-known form of SFT: training on instruction→response examples so a base model learns to *follow instructions* (turning a raw completion model into a helpful assistant). When you fine-tune for your task, you're almost always doing SFT, and the quality of your input→output dataset is the single biggest determinant of the result (the data post).

## Preference alignment: RLHF and DPO

The right end of the spectrum shapes something SFT can't easily express: *which of several valid responses is better*. SFT teaches the model to produce a correct output; **preference alignment** teaches it to produce the *preferred* output — more helpful, more harmless, better-toned — by training on **comparisons** (response A is better than response B) rather than single correct answers.

Two approaches, covered fully in a later post:

- **RLHF (Reinforcement Learning from Human Feedback)** — train a *reward model* on human preference comparisons, then use reinforcement learning to optimize the LLM against that reward. Powerful, and how many assistant models are aligned, but complex (multiple models, an RL loop, instability).
- **DPO (Direct Preference Optimization)** — achieve similar preference alignment *directly* from the comparison data, without training a separate reward model or running RL. Much simpler and more stable, which is why it's widely adopted.

Alignment sits after SFT: you typically SFT a model to do the task, then align it to do it *well* by human standards. It needs *preference* data (comparisons), a different and often harder-to-collect kind of data than SFT's input→output pairs. Most applied projects start (and often stop) at SFT; alignment is the escalation when *quality of judgment* — not just correctness of format — matters.

## Locating your task on the spectrum

The practical value of the spectrum is diagnostic — match the technique to what you actually need to change:

- **"The model doesn't understand my domain's language at all"** → continued pretraining (rare, expensive; be sure SFT won't do).
- **"I need consistent format, a narrow skill, a specific style, or a taxonomy"** → SFT (the common case; start here).
- **"The model does the task but I want it to prefer better/safer/on-tone responses"** → alignment (RLHF/DPO), usually after SFT.
- **"I need it to know facts"** → not the spectrum at all → RAG (from the last post).

Choosing the wrong point wastes resources: continued pretraining for a format problem is absurdly overkill; trying to SFT in nuanced judgment that really needs preference data underdelivers. Most projects live at SFT, reach right to alignment for polish, and should resist the expensive left end unless the domain genuinely demands it. With the spectrum clear, the next posts go deep on the techniques that make SFT affordable — LoRA and QLoRA.

## Key takeaways

- "Fine-tuning" is a spectrum from continued pretraining (broad, expensive) through supervised fine-tuning (SFT) to preference alignment (narrow, quality-focused) — each changes the model differently, and locating your task on it determines technique, data, and cost.
- Continued pretraining continues next-token training on large domain text to shift the model's grasp of a domain's language — the heaviest, rarest form, justified only when the base model doesn't understand the domain's language (and it still doesn't give reliable facts).
- Supervised fine-tuning (SFT) trains on labeled input→output examples to shape behavior (format, skill, style, taxonomy) — the workhorse of applied fine-tuning, needing only modest quality data and affordable with LoRA/QLoRA; instruction tuning is a well-known form.
- Preference alignment (RLHF, DPO) trains on comparisons (A better than B) to make the model produce *preferred* responses, not just correct ones — usually applied after SFT, needing preference data; DPO does it directly without RLHF's reward model and RL loop.
- Match technique to need: continued pretraining for domain-language gaps (rare), SFT for behavior (common, start here), alignment for judgment quality (escalation), and RAG — not the spectrum — for facts.

## Further reading

- [What fine-tuning is and when to use it (previous post)](/blog/posts/finetune-01-what-fine-tuning-is.html)
- [InstructGPT: Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155)
- [Hugging Face — training and fine-tuning](https://huggingface.co/docs/transformers/en/training)
