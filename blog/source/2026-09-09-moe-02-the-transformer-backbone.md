# The Transformer Backbone, Recapped

*Mixture of Experts is a modification to the transformer, so you can't understand modern LLM architecture without a clear picture of the transformer itself. This post is a focused recap of the parts that matter for the rest of the series: attention as the mechanism that mixes information across tokens, the feed-forward block that MoE replaces, and how the pieces stack into the model everyone is now modifying.*

The previous post promised MoE sits *inside* the transformer. To see how, you need the transformer's structure clearly, especially the two blocks in every layer — attention and feed-forward — because MoE changes one of them and efficient-attention techniques (later posts) change the other. This is a deliberately practical recap aimed at the architecture, not a from-scratch derivation.

## The problem attention solves

A language model processes a sequence of tokens and must, for each position, draw on relevant information from *other* positions — to understand a word, you need its context. The transformer's core mechanism, **attention**, is how each token gathers information from the others.

The intuition: for each token, attention computes how much it should "pay attention to" every other token, then produces a weighted blend of their information. A pronoun attends to the noun it refers to; a verb attends to its subject. Attention is the mechanism that *mixes information across the sequence* — it's the only place in the transformer where tokens actually influence each other. Everything else operates on each token independently.

## Self-attention, briefly

Mechanically, self-attention works through three learned projections of each token, by convention called **queries (Q)**, **keys (K)**, and **values (V)**:
- Each token emits a **query** ("what am I looking for?"), a **key** ("what do I offer?"), and a **value** ("what information do I carry?").
- A token's query is compared against every token's key (a dot product) to get attention scores — how relevant each other token is to this one.
- Those scores are normalized (softmax) into weights, and the token's output is the weighted sum of all tokens' **values**.

So each token's new representation is a blend of all tokens' values, weighted by relevance. Two details matter for later posts:
- **Multi-head attention.** This is done in parallel across several "heads," each with its own Q/K/V projections, letting the model attend to different kinds of relationships at once. The number of heads and how K/V are shared across them is exactly what the efficient-attention techniques (post 7) modify.
- **The Q·K comparison is all-pairs.** Every token compares against every other token, which is why attention costs scale with the *square* of sequence length — the fact that drives the long-context problem (post 6).

You don't need the full math for this series; you need the shape: attention = each token blends others' values, weighted by query-key relevance, across multiple heads, comparing all pairs.

## The two blocks in every layer

A transformer is a stack of identical **layers**, and each layer has two sub-blocks, applied in sequence (with residual connections and normalization around them):

1. **The attention block** — mixes information *across tokens* (described above). This is where tokens communicate.
2. **The feed-forward block (FFN)** — processes *each token independently*, applying the same small neural network (typically two linear layers with a non-linearity) to every position separately. This is where much of the model's per-token "thinking" and stored knowledge lives.

The division of labor is worth internalizing: **attention moves information between tokens; the FFN processes each token's information.** They alternate — attend (gather context), then feed-forward (process it), layer after layer.

This is the key setup for the whole series: **Mixture of Experts replaces the FFN block.** In a dense model, every token goes through the same single FFN. MoE swaps that one FFN for many expert FFNs plus a router (post 3). So when we talk about MoE, we're talking about changing block #2. And when we talk about efficient/long-context attention (posts 6–7), we're changing block #1. The transformer's two-block structure is the map for everything that follows.

## Stacking into a model

Zooming out, an LLM is:
- An **embedding** layer that turns tokens into vectors,
- A **stack of N transformer layers** (each: attention block + FFN block), where N is the model's depth (dozens to over a hundred in large models),
- An **output** layer that turns the final representations into next-token probabilities.

The model is **autoregressive**: it predicts the next token, appends it, and repeats — generating text one token at a time. (This generation loop, and the memory it requires, is central to the long-context and serving discussion in later posts.) Scale comes from making the layers wider (bigger dimensions), deeper (more layers), and — the FFN especially — larger. Because the FFN blocks hold a large share of a transformer's parameters, they're the natural target for the capacity-vs-compute trick: making the FFN into a Mixture of Experts is how you add parameters there without spending them on every token.

That's the backbone. Modern LLM architecture is largely the story of two modifications to this structure: turning the FFN into a Mixture of Experts (to scale parameters cheaply) and making attention more efficient (to scale context cheaply). With the two-block picture in hand, we can now open up the first one.

## Key takeaways

- **Attention** is the transformer's core mechanism for mixing information *across tokens* — each token blends other tokens' **values**, weighted by **query–key** relevance — and it's the only place tokens influence each other.
- **Multi-head attention** runs this in parallel across heads (attending to different relationship types); how keys/values are shared across heads is what efficient-attention techniques later modify, and the **all-pairs** query–key comparison is why cost scales with the *square* of sequence length.
- Every transformer layer has **two blocks**: the **attention block** (moves information *between* tokens) and the **feed-forward block/FFN** (processes *each token independently* — where much per-token computation and knowledge lives); they alternate, layer after layer.
- The series' key setup: **MoE replaces the FFN block** (block #2 — many expert FFNs + a router instead of one FFN), while **efficient/long-context attention modifies the attention block** (block #1) — the two-block structure is the map for modern architecture.
- An LLM stacks embedding → N transformer layers → output and generates **autoregressively** (one token at a time); FFN blocks hold a large share of parameters, making them the natural target for MoE's add-capacity-without-per-token-compute trick.

## Further reading

- [Attention Is All You Need — Vaswani et al. (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762)
- [The Illustrated Transformer — Jay Alammar](https://jalammar.github.io/illustrated-transformer/)
