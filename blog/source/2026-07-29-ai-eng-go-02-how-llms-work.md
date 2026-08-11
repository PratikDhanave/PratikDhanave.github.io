# How LLMs Work, Enough to Build With Them

*The working mental model an AI engineer needs — next-token prediction, attention, training, and sampling — without the transformer math, and with every fact tied back to a decision you make in code.*

---

You do not need to derive backpropagation to build reliable software on top of a language model. But you do need a mental model that predicts how the model will behave — why it invents a plausible-sounding API that does not exist, why the same prompt gives two different answers, why rephrasing a question fixes it. Almost every strange behavior an AI engineer hits traces back to a handful of facts about what the model actually is and how it was made. This post is that mental model: enough of how large language models work to make good engineering decisions, and nothing you would only need for a research exam.

We will stay concrete. Each idea comes with a "so as an engineer you should…" because the whole point is to change what you build, not just what you know.

---

## An LLM is a next-token predictor

Strip away the marketing and a large language model does exactly one thing: given a sequence of text, it predicts what comes next. Not the next word, exactly — the next *token*, a chunk that might be a whole word (`banana`), a word fragment (`ban` + `ana`), a space-prefixed word (` the`), or a punctuation mark. The model reads your text as a list of token IDs and outputs a probability for every token in its vocabulary being the next one.

That is the entire core loop. To generate a sentence, the model predicts one token, appends it to the input, and predicts again — over and over, feeding its own output back in. What looks like reasoning or conversation is this one operation repeated hundreds of times.

Here is the shape of a single prediction step, as plain text rather than real API output:

```text
Prompt: "The capital of France is"

Model's predicted next-token probabilities:
  " Paris"     0.91
  " a"         0.03
  " located"   0.02
  " the"       0.01
  ... (thousands more, each tiny)
```

The model learned these probabilities from an enormous amount of text — books, code, web pages, documentation. Nobody wrote a rule that Paris follows "the capital of France is." The model saw that pattern, and countless others, often enough to encode it in its weights as a probability.

**The gotcha:** the model outputs *probabilities*, never facts. "Paris" scores 0.91 because that continuation was overwhelmingly common in training text, not because the model looked anything up. This one fact explains most of what follows — hold onto it.

**So as an engineer you should:** treat every model output as a statistically likely continuation, not a retrieved answer. When you need ground truth — a real customer record, today's price, an exact calculation — get it from a tool or database and put it *in the prompt*, rather than trusting the model to recall it.

---

## Attention, at the level you actually need

If a model only predicts the next token, how does it keep track of context across a long passage — knowing that "it" refers to the invoice mentioned three sentences ago? The answer is the mechanism at the heart of the *transformer* architecture that modern LLMs are built on: **self-attention**, introduced in the 2017 paper "Attention Is All You Need."

Here is the intuition, no equations. When the model processes each token, it looks at all the other tokens in the input and decides how much each one matters for understanding the current one. Every token gets to "attend to" every other token and pull in the context that is relevant. Processing "it" in "the invoice was overdue so I flagged it," the model can weigh "invoice" heavily and "so" barely, effectively resolving what "it" points at.

That weighing happens in parallel across the whole input, in many layers stacked on top of each other, with multiple independent attention patterns ("heads") per layer. Early layers might track grammar; later layers track meaning and long-range references. You do not need the linear algebra — you need the consequence: the model builds a rich, context-sensitive representation of your entire input before it predicts the next token, and *which* tokens you include changes how every other token is understood.

**So as an engineer you should:** understand that context is not a passive backdrop — the model actively reweighs the whole input on every call. Irrelevant or contradictory text in your prompt does not get politely ignored; it competes for attention and can pull the answer off course. Keep prompts focused, and put the most important instructions where they will not be drowned out.

---

## Two phases of training: pretraining and post-training

The raw next-token predictor and the helpful assistant you actually call are the same network at two different stages of training.

**Pretraining** is the expensive part. The model reads a vast corpus of text and learns to predict the next token across all of it. This is where it absorbs grammar, facts, coding patterns, reasoning-shaped structure, and a rough model of the world — purely as a side effect of getting good at prediction. The output of pretraining is a *base model*: fluent, knowledgeable, but not particularly cooperative. Ask a base model a question and it might continue with more questions, because in its training data a question was often followed by more questions.

**Post-training** turns that base model into an assistant. Two ideas matter here:

- **Instruction tuning:** the model is further trained on examples of instructions paired with good responses, teaching it to treat your input as a task to complete rather than a passage to continue.
- **Preference tuning (RLHF and its relatives):** humans (or a model trained to mimic their judgments) rank alternative responses, and the model is nudged toward the preferred ones. This is how models learn to be helpful, to refuse harmful requests, and to match a house style and tone.

Preference tuning shapes behavior, not knowledge. It changes *how* the model responds, not *what* it fundamentally knows — the facts came from pretraining.

**So as an engineer you should:** remember you are talking to a post-trained assistant with a particular "personality" baked in by its provider. Its willingness to answer, its default verbosity, its caution — these are training artifacts, not laws of nature, and they differ between providers and model versions. When you swap models, re-test your prompts; the same words can land differently.

---

## Why real behaviors happen (and what to do about each)

Now the payoff. Four behaviors that surprise people all fall straight out of "it is a next-token predictor trained on fixed text."

### Hallucination

When a model states something false with total confidence, it is not lying or malfunctioning — it is doing exactly its job. It predicted the most plausible continuation. If your prompt looks like it should be followed by a citation, a function name, or a statistic, the model will produce something that *looks* like one, whether or not it corresponds to reality. Plausibility and truth are correlated in the training data but they are not the same thing, and the model only optimizes for the first.

**So as an engineer you should:** never rely on the model for facts you cannot verify. Ground it with retrieved documents, give it tools to look things up, and validate anything consequential — especially code, URLs, and numbers — against a real source before acting on it.

### Knowledge cutoff

A model's pretraining data was collected up to some date. It knows nothing that happened after — a library released last month, a news event, your internal systems. It may still answer confidently, because it will happily predict plausible tokens about things it has no information on.

**So as an engineer you should:** provide current information in the prompt rather than assuming the model has it. For anything time-sensitive or private to your domain, retrieval or a tool call is not optional.

### Sensitivity to phrasing

Because the input reshapes the whole attention computation, small wording changes can produce meaningfully different outputs. "Summarize this" and "Extract the three key decisions from this" walk down different probability paths from the very first token.

**So as an engineer you should:** treat prompts as code worth iterating on and testing. Pin down the wording that works, keep a small suite of example inputs to check against when you change a prompt, and do not assume a phrasing that works on one model transfers to another.

### Non-determinism

Ask the same question twice and you may get two different answers. Part of this is the sampling step (next section); part is that at production scale the exact numerical computation can vary slightly run to run. Either way, identical input does not guarantee identical output.

**So as an engineer you should:** design for variation. Do not hard-code assertions that expect one exact string. If you need reproducibility, lower the randomness (below) and, where a provider offers a `seed` parameter, use it — but treat even that as best-effort, not a contract.

---

## Sampling: how the next token is actually chosen

The model hands you a probability for every possible next token. Something still has to *pick one*. That picking step is **sampling**, and it is where you have direct, dial-turning control over the model's behavior.

If you always picked the single highest-probability token ("greedy" decoding), output would be repetitive and often dull. Instead, providers expose knobs that let you introduce controlled randomness:

- **Temperature** rescales the probabilities before choosing. Low temperature (near 0) sharpens the distribution so the top token almost always wins — focused, predictable, repeatable. High temperature (say 0.8–1.2) flattens it so less-likely tokens get a real chance — more varied and creative, more prone to wandering.
- **Top-p (nucleus sampling)** restricts the choice to the smallest set of tokens whose probabilities add up to `p` (e.g. 0.9), then samples among those. It adapts to how confident the model is: a peaked distribution yields few candidates, a flat one yields many.
- **Top-k** simply restricts the choice to the `k` most likely tokens before sampling.

You typically tune one or two of these, not all three. Here is the intuition of what temperature does to the same prediction from earlier:

```text
Prediction with temperature 0.0 (greedy):
  " Paris"  -> chosen every time

Prediction with temperature 1.0 (flatter):
  " Paris"     0.72
  " a"         0.09
  " located"   0.07   <- these now stand a real chance
  " the"       0.05
```

**The gotcha:** "temperature 0" is often described as deterministic, and it does make the sampling step pick the top token every time — but it does not guarantee byte-identical output across calls, because of the run-to-run numerical variation mentioned above. Treat temperature 0 as "as repeatable as this model gets," not "guaranteed identical."

**So as an engineer you should:** match the dial to the job. For extraction, classification, structured output, or anything where you want the same answer every time, use temperature 0 (or very low). For brainstorming, drafting, or varied phrasing, raise it. Change one knob at a time and observe — do not set temperature *and* top-p to extremes at once and wonder why output turned to noise.

---

## The context window: everything the model sees, and nothing else

Every call to a model includes a **context window** — the full block of tokens the model reads before predicting: your system instructions, the conversation history, retrieved documents, tool outputs, and the user's latest message. The window has a fixed maximum size (measured in tokens), and it is the model's *entire* world for that call.

The consequence that trips up newcomers most: **the model has no memory between calls.** It does not remember your previous question unless you send that question again as part of the new input. A "conversation" is an illusion your code maintains by resending the accumulating history on every turn. The model is stateless; you supply the state.

This reframes a lot of engineering:

| If you want… | You must… |
|---|---|
| The model to recall earlier turns | Resend the conversation history each call |
| The model to use a document | Put its text in the context window |
| The model to know a fact from your database | Retrieve it and include it in the prompt |
| A long chat to keep working | Trim or summarize old turns before you exceed the window |

Because the window is finite, long conversations and large documents eventually overflow it. And because attention reweighs everything, stuffing the window with marginally relevant text is not free — it costs tokens (money and latency) and can dilute the signal.

**So as an engineer you should:** treat the context window as a budget you actively manage. Decide deliberately what goes in each call, keep the important material prominent, summarize or drop stale history before you hit the limit, and never assume the model "remembers" anything you did not resend.

---

## Key takeaways

- **It predicts tokens, not truth.** Every output is a statistically likely continuation. Ground facts with tools and retrieval; verify anything consequential.
- **Attention makes context active.** The model reweighs your whole input on every call, so irrelevant text competes with the signal — keep prompts focused.
- **Training explains personality, not knowledge.** Pretraining supplies the facts; post-training shapes helpfulness and tone. Re-test prompts when you switch models.
- **The weird behaviors are the mechanism, not bugs.** Hallucination, knowledge cutoff, phrasing sensitivity, and non-determinism all fall out of next-token prediction over fixed data.
- **Sampling is your control dial.** Temperature and top-p decide how the next token is chosen; use temperature 0 for repeatable, structured tasks and raise it for creative ones.
- **The model is stateless.** The context window is all it sees, it has no memory between calls, and managing that budget is your job, not the model's.

Hold these six facts and most "why did it do that?" moments become predictable. In the next posts in this series we start putting them to work in Go — making calls, controlling sampling, and managing the context window in code.

---

## Further reading

- Vaswani et al., "Attention Is All You Need" (2017) — the paper that introduced the transformer and self-attention: [arxiv.org/abs/1706.03762](https://arxiv.org/abs/1706.03762)
- Your provider's model documentation — the authoritative reference for context-window sizes, supported sampling parameters (temperature, top-p, top-k, seed), knowledge cutoffs, and per-model behavior. Always check the docs for the specific model you are calling; these details differ between models and change over time.
