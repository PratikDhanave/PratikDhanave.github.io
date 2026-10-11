# Node Embeddings and Graph Learning Tasks

*Before diving into how graph neural networks work, it's worth being precise about what they produce and what problems they solve. The output is embeddings — vectors that place each node (or edge, or whole graph) in a meaningful space — and the problems come in three flavors that cover almost every graph application. Getting this vocabulary straight makes the architectures in the rest of the series click into place.*

Post 1 said GNNs learn representations of graph elements. This post defines those representations (embeddings) and the three task types (node-level, edge-level, graph-level) they serve. It's the map of *what you're trying to do* with a graph, which is what determines how you use a GNN — so it's worth getting clear before the mechanics.

## Embeddings: position in a meaningful space

The core output of a GNN is an **embedding** — a dense vector representing a node (or edge, or graph) such that the geometry of the vector space is meaningful: similar or related elements sit close together. This is the same idea as word embeddings or the vectors in semantic search (ML series, post 7), now for graph elements.

What makes a *graph* embedding special is what "similar" means. A good node embedding captures two things at once:
- **The node's own features** — its attributes (a user's age, a paper's topic, an atom's element).
- **Its structural role and context** — *where it sits in the graph*: who its neighbors are, what community it belongs to, how central it is. Two nodes with identical features but very different neighborhoods should get different embeddings, because they play different roles.

This fusion is the whole point: a node's embedding encodes *what it is and where it is in the network*, compressed into a vector that downstream models can use. The quality of a GNN is really the quality of the embeddings it produces — do nodes that *should* be treated similarly (same community, same function) end up close in the space? Once you have good embeddings, the actual prediction tasks become straightforward standard ML on those vectors, which is why "learn good embeddings" is the real job.

## The three levels of graph tasks

Almost every graph problem is one of three types, distinguished by *what* you're making a prediction about. Knowing which you have tells you how to apply a GNN:

- **Node-level tasks** — predict something about individual nodes. *Node classification*: given a partially-labeled graph, label the rest (classify users as bot/human, papers by field, accounts as fraudulent). *Node regression*: predict a numeric property per node. The GNN produces a node embedding, and a classifier/regressor on top makes the per-node prediction. This is the most common task type.
- **Edge-level tasks** — predict something about pairs of nodes, especially whether an edge *should* exist. *Link prediction* is the flagship: given the current graph, predict missing or future edges — recommend friends (will these two connect?), suggest products (will this user like this item?), or complete a knowledge graph (what relationship holds between these entities?). You combine the two nodes' embeddings to score the likelihood of an edge. Link prediction powers recommendation and knowledge-graph completion, so it's enormously valuable.
- **Graph-level tasks** — predict something about an *entire graph*. *Graph classification/regression*: is this molecule toxic? what's this protein's function? what's this material's property? Here you need a single embedding for the *whole graph*, obtained by aggregating (pooling) all the node embeddings into one — and then a standard predictor acts on it. This is the setting for molecular and drug-discovery applications.

These three levels — node, edge, graph — are a complete map, and the first question to ask of any graph problem is "which level is my prediction at?" because it determines what embedding you need (per-node, per-pair, or whole-graph) and how you read it out.

## Transductive vs inductive: a distinction that matters a lot

One more distinction shapes which GNN approach you need and is a common source of confusion:

- **Transductive** learning — you train and predict on the *same, fixed* graph. You have one graph, some nodes are labeled, and you want to label the rest *in that graph* (classify the unlabeled users in *this* social network). The model never needs to handle a node it didn't see during training. Early graph-embedding methods were transductive — they learned an embedding for each specific node and couldn't embed a new one without retraining.
- **Inductive** learning — you train on some graph(s) and must generalize to *new, unseen* nodes or entirely *new graphs* at test time. A model that classifies *new* users joining the network tomorrow, or predicts properties of *novel* molecules never seen in training, must be inductive. It can't have memorized per-node embeddings; it must learn a *function* that computes an embedding from a node's features and neighborhood, applicable to anything.

This distinction is decisive in practice because most real systems are inductive — new users, new transactions, new molecules arrive constantly, and retraining per new node is untenable. It's exactly why modern GNNs (GraphSAGE and successors, post 5) are built to be *inductive*: they learn a reusable neighborhood-aggregation function rather than fixed per-node vectors, so they embed anything on the fly. When you evaluate a graph method, "is it inductive?" is one of the most important practical questions — a transductive method that can't handle new nodes is a poor fit for a living, growing graph.

The throughline: a GNN produces **embeddings** — vectors placing each node/edge/graph in a meaningful space where related elements sit close — and a *node* embedding fuses **what it is** (features) with **where it sits** (structural context), so "learn good embeddings" is the real job and the prediction is easy standard ML on top. Graph problems come in **three levels**: **node-level** (classify/score individual nodes — the most common), **edge-level** (**link prediction** — recommend connections, complete knowledge graphs — combine two node embeddings), and **graph-level** (classify a whole graph, e.g. molecule toxicity — pool all node embeddings into one). And the **transductive vs inductive** distinction is decisive: transductive works only on the fixed training graph, while **inductive** methods learn a reusable aggregation *function* that embeds new/unseen nodes and graphs — which most real, growing systems require, and why modern GNNs are inductive.

## Key takeaways

- A GNN's output is an **embedding** — a vector placing a node/edge/graph in a space where related elements are close; a **node embedding** fuses the node's **features** (what it is) with its **structural context** (where it sits — neighbors, community, centrality), so two feature-identical nodes in different neighborhoods get different embeddings.
- The real job is **learning good embeddings**; the prediction is then straightforward standard ML on those vectors.
- Graph tasks come in **three levels**: **node-level** (node classification/regression — most common), **edge-level** (**link prediction** — recommend friends/products, complete knowledge graphs — by combining two node embeddings), and **graph-level** (classify/score a whole graph like molecule toxicity — by **pooling** all node embeddings into one).
- The first question for any graph problem: **which level is my prediction at?** — it determines whether you need per-node, per-pair, or whole-graph embeddings and how to read them out.
- **Transductive** (train and predict on the same fixed graph; can't handle unseen nodes without retraining) vs **inductive** (learn a reusable function that embeds *new* nodes/graphs at test time) is decisive — most real systems (new users/transactions/molecules arriving constantly) need **inductive** methods, which is why modern GNNs (GraphSAGE, post 5) learn aggregation functions rather than fixed per-node vectors.

## Further reading

- [Graph neural network — producing node and graph embeddings](https://en.wikipedia.org/wiki/Graph_neural_network)
- [Feature learning — learning representations like embeddings](https://en.wikipedia.org/wiki/Feature_learning)
