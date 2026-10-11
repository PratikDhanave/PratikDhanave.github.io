# Graph Convolutional Networks — The First Great GNN

*The graph convolutional network is the "linear regression" of graph deep learning: the simplest architecture worth knowing, the one that made GNNs practical, and the baseline every other method is compared against. It's message passing with the most natural possible aggregation — average your neighbors — and understanding exactly what it does, and where its simplicity bites, is the foundation for everything more sophisticated.*

Post 3 established message passing and noted that architectures differ in *how* a node aggregates its neighbors. This post covers the first and most important choice: the **graph convolutional network (GCN)**, which aggregates by a normalized average. It's where most people start, it's a strong baseline, and its limitations motivate GraphSAGE and GAT (posts 5–6).

## GCN: aggregate by normalized averaging

The **GCN** instantiates the message-passing loop (post 3) with the simplest sensible aggregation: each node updates itself by taking a **weighted average of its neighbors' representations** (including itself), then passing that through a learned linear transformation and a nonlinearity. In message-passing terms, the *aggregate* step is "average the neighbors" and the *update* is "transform and activate."

The one refinement that makes it work well is **normalization**. A naive average has a problem: a node with 1,000 neighbors and a node with 2 neighbors would produce wildly different-magnitude aggregates, destabilizing training, and high-degree nodes (hubs) would dominate. The GCN normalizes the aggregation by node degrees (down-weighting contributions through high-degree nodes), which keeps the scale consistent and prevents hubs from swamping everything. This *symmetric degree normalization* is the GCN's signature detail and a big reason it trains stably — it's "average your neighbors, but account for how connected everyone is."

Stack two or three such layers (post 3) and you get a model where each node's final embedding is a learned, normalized blend of its 2–3-hop neighborhood — simple, effective, and the workhorse baseline for node classification. The GCN's appeal is exactly its simplicity: few parameters, fast, stable, and often *good enough*, which is why it remains the first thing to try on a graph problem.

## Why GCN works — and the semi-supervised sweet spot

The GCN became influential because it hit a sweet spot, especially for **semi-supervised node classification** — the common situation where you have a big graph but only a *few* labeled nodes (most nodes unlabeled). This is exactly where GCNs shine, because of a powerful implicit assumption:

- **Smoothing over the graph spreads labels.** By repeatedly averaging neighbors, the GCN makes connected nodes' embeddings similar — so the labels of the few known nodes effectively *propagate* along the edges to their unlabeled neighbors. If you know a handful of users are bots and bots cluster together, averaging over the graph pulls the unlabeled cluster members toward the "bot" representation. The GCN encodes the assumption that *connected nodes tend to be similar* (homophily), and when that assumption holds, it extracts enormous value from very few labels.

This is why GCNs were a breakthrough for problems like classifying papers in a citation network or users in a social graph from sparse labels: the graph structure does much of the work, and the GCN turns "a few labels + lots of structure" into accurate predictions across the whole graph. When your graph is **homophilous** (connected things are alike — true of most citation, social, and purchase networks), the GCN is both simple and remarkably strong.

## The limitations that motivate everything else

The GCN's simplicity is also its ceiling, and each limitation points directly at a later architecture:

- **It's transductive (in its original form).** The classic GCN learns using the *whole fixed graph's* structure at once, so it can't naturally embed a *new* node that wasn't present at training time (post 2's transductive/inductive distinction). For a growing graph with new nodes arriving, this is disqualifying — and it's exactly what **GraphSAGE** (post 5) fixes by learning an inductive aggregation function and sampling neighbors.
- **It treats all neighbors as (degree-normalized) equal.** The GCN's averaging gives every neighbor the same importance (up to degree normalization) — but some neighbors are far more relevant to a node than others, and a fixed average can't express that. This is exactly what **GAT** (post 6) fixes by *learning attention weights* so a node listens more to important neighbors.
- **It assumes homophily.** The GCN's smoothing helps when connected nodes are similar but actively *hurts* when they're not (heterophilous graphs — where connected nodes tend to *differ*), because averaging blurs away the very differences that matter. Not every graph is homophilous, and the GCN silently assumes it is.
- **It over-smooths with depth** (post 3), capping it at a few layers and limiting how far it can see.

None of these make the GCN bad — it's a genuinely strong, often-sufficient baseline, and the right first thing to try. They make it a *starting point*: GraphSAGE adds inductive capability and scalability, GAT adds learned per-neighbor importance, and later work addresses heterophily and depth. The GCN is to GNNs what logistic regression is to classification — simple, interpretable, strong, and the baseline you must beat before reaching for something fancier. Start here, and only add complexity when the GCN's specific limitations are the thing holding you back.

The throughline: the **graph convolutional network (GCN)** is message passing with the simplest aggregation — each node takes a **degree-normalized weighted average** of its neighbors (and itself), then a learned transform + nonlinearity — where the **normalization** (down-weighting high-degree hubs) is the signature detail that makes it train stably. Stacked 2–3 layers, it's the workhorse baseline, and it shines at **semi-supervised node classification** because averaging **propagates labels** along edges under a **homophily** assumption (connected nodes are alike), turning a few labels + lots of structure into graph-wide predictions. Its simplicity is its ceiling, and each limit motivates a successor: it's **transductive** (→ GraphSAGE adds inductive + scalability), treats **all neighbors as equal** (→ GAT learns per-neighbor attention), **assumes homophily** (hurts on heterophilous graphs), and **over-smooths** with depth. It's the logistic regression of graphs — the strong baseline to beat.

## Key takeaways

- The **GCN** instantiates message passing with the simplest aggregation: a **degree-normalized weighted average** of a node's neighbors (and itself), then a learned linear transform + nonlinearity; the **normalization** (down-weighting hubs so high- and low-degree nodes stay comparable) is its signature and the reason it trains stably.
- Stacked 2–3 layers, it's the **workhorse baseline** — few parameters, fast, stable, often *good enough* — and the first thing to try on a graph problem.
- It excels at **semi-supervised node classification** (big graph, few labels) because averaging neighbors **propagates labels** along edges, encoding a **homophily** assumption (connected nodes are similar) — extracting great value from sparse labels when that holds (citation, social, purchase graphs).
- Its limitations each motivate a successor: **transductive** (can't embed new nodes → **GraphSAGE**, post 5), **treats all neighbors equally** (→ **GAT** learns attention, post 6), **assumes homophily** (hurts on heterophilous graphs where connected nodes differ), and **over-smooths** with depth (post 3).
- It's the **logistic regression of graphs** — simple, strong, interpretable, the baseline to beat — so start with a GCN and add complexity only when its specific limits are what's holding you back.

## Further reading

- [Graph neural network — GCN and the convolutional approach](https://en.wikipedia.org/wiki/Graph_neural_network)
- [Convolutional neural network — the convolution GCN generalizes](https://en.wikipedia.org/wiki/Convolutional_neural_network)
