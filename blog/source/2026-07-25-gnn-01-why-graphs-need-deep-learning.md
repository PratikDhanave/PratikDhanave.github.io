# Why Graphs Need Their Own Deep Learning

*Neural networks conquered images, text, and audio — but a huge amount of the world's most valuable data isn't any of those. It's graphs: social networks, molecules, knowledge graphs, payment networks, supply chains. Standard deep learning can't handle them, because graphs break the assumptions CNNs and transformers are built on. Graph neural networks are the architecture built for data whose meaning lives in its connections, and this series builds them from first principles.*

This series complements the blog's deep learning and [Ontologies and Knowledge Graphs](/blog/series/ontologies-and-knowledge-graphs/) coverage with the one architecture designed for graph-structured data. It assumes the [machine learning foundations](/blog/series/machine-learning-from-first-principles/) and a little neural-network familiarity. Post 1 answers the motivating question: why can't you just use a normal neural network on a graph, and what does a GNN do differently?

## The data deep learning couldn't handle

Standard neural networks assume a *regular, fixed structure* in their input:
- A **CNN** assumes a grid — an image is a fixed array of pixels with a consistent notion of "the pixel above/left," and convolution exploits that spatial regularity.
- A **transformer or RNN** assumes a sequence — text is an ordered line of tokens with a clear "next" and "previous."

Graphs have neither. A **graph** is a set of **nodes** connected by **edges**, and it has properties that break those assumptions:
- **No fixed size or shape** — different graphs have different numbers of nodes, and a node can have any number of neighbors (one friend or ten thousand), so there's no fixed-size input to feed a standard network.
- **No natural ordering** — the nodes aren't in any canonical order; "node 1" and "node 2" are arbitrary labels. A molecule is the same molecule however you number its atoms.
- **The structure *is* the information** — in an image the grid is just a container; in a graph the *connections* carry the meaning. Who is connected to whom in a social network, which atoms bond in a molecule, which accounts transact — the edges are the signal, not scaffolding.

You *could* try to force a graph into a standard network — flatten it into a vector, or feed its adjacency matrix to a dense layer — but this fails badly: it imposes an arbitrary node ordering (so the same graph looks different depending on numbering), it can't generalize to graphs of different sizes, and it ignores the relational structure that mattered. Graphs need an architecture that respects their nature.

## The two properties a graph architecture must have

A neural network for graphs has to satisfy two requirements that standard architectures don't, and these define what a GNN is:

- **Permutation invariance / equivariance.** Because node ordering is arbitrary, the network's output must *not depend on how the nodes are numbered.* Relabel the nodes and a graph-level prediction (is this molecule toxic?) must be identical; node-level predictions must simply follow their nodes. This rules out anything that treats node 1 specially, and it's the formal reason you can't just flatten a graph — flattening bakes in an order the data doesn't have.
- **Handling variable structure.** The network must work on graphs with any number of nodes and any connectivity, and a node must be able to incorporate information from however many neighbors it has. The architecture has to adapt to each graph's shape rather than assuming a fixed one.

A standard neural network violates both; a GNN is precisely an architecture designed to satisfy both. The key realization that makes it possible: instead of operating on the graph as a whole fixed object, operate *locally and identically at every node* — have each node gather information from its neighbors using the *same* learned operation everywhere. Shared-everywhere local operations are naturally permutation-equivariant (relabeling doesn't change what each node computes from its neighborhood) and naturally handle any size (the same operation runs wherever there are nodes). This is the seed of **message passing** (post 3), the mechanism at the heart of every GNN.

## What a GNN learns, and why it matters now

A **graph neural network** learns to produce useful **representations (embeddings) of nodes, edges, or whole graphs** by combining each node's own features with information aggregated from its neighborhood across the graph. The learned embedding of a node captures not just *what it is* (its features) but *where it sits* in the graph (its structural context) — and those embeddings then feed ordinary ML tasks: classify a node, predict a missing edge, or classify a whole graph (post 2).

This matters because graph-structured problems are everywhere and economically enormous:
- **Social and web networks** — recommend connections, detect communities, rank pages.
- **Molecules and materials** — predict a molecule's properties for drug and materials discovery (atoms = nodes, bonds = edges), one of GNNs' highest-impact uses.
- **Fraud and financial networks** — spot fraud rings and money-laundering patterns in transaction graphs, where the signal is *structural*.
- **Knowledge graphs** — infer missing facts and relationships (link prediction), connecting directly to the Ontologies series and to GraphRAG.
- **Recommendation** — model user-item interactions as a graph (a technique behind large-scale recommenders).

The reason GNNs surged is that the same deep-learning revolution that transformed vision and language finally got an architecture that fits *relational* data — and relational data is a vast, previously-underserved category. If your problem's meaning lives in how things connect, a GNN is the tool that can learn from the connections rather than throwing them away. This series builds up from this motivation to the mechanisms (message passing), the main architectures (GCN, GraphSAGE, GAT), training at scale, and the honest judgment of when GNNs are worth it.

The throughline: standard neural networks assume **regular structure** — a CNN a grid, a transformer a sequence — but a **graph** (nodes + edges) has **no fixed size, no natural ordering, and structure that *is* the information**, so flattening it or feeding its adjacency matrix fails (arbitrary ordering, no size generalization, ignores relations). A graph architecture must be **permutation-invariant/equivariant** (output independent of node numbering) and **handle variable structure** — achieved by operating **locally and identically at every node**, each gathering from its neighbors with the same learned operation (the seed of **message passing**, post 3). A **GNN** learns **embeddings of nodes/edges/graphs** capturing both features and structural position, feeding node classification, link prediction, and graph classification — and it surged because it finally brought deep learning to the vast, valuable category of **relational data** (social networks, molecules, fraud, knowledge graphs, recommendation).

## Key takeaways

- Standard neural nets assume **regular structure** (CNN → grid, transformer/RNN → sequence); a **graph** (nodes + edges) has **no fixed size/shape**, **no natural node ordering**, and structure that **is the information** (the edges are the signal, not a container).
- Forcing a graph into a standard network (flattening, adjacency-to-dense) **fails**: it imposes an arbitrary ordering, can't generalize across graph sizes, and discards the relational structure.
- A graph architecture must be **permutation-invariant/equivariant** (relabeling nodes can't change the output) and **handle variable structure** (any node count, any connectivity) — achieved by operating **locally and identically at every node** (shared operation over each node's neighborhood), the seed of **message passing** (post 3).
- A **GNN** learns **embeddings of nodes, edges, or whole graphs** that capture both a node's **features** and its **structural position**, which then feed standard tasks: **node classification**, **link prediction**, **graph classification** (post 2).
- GNNs surged because they bring deep learning to **relational data** — a vast, high-value category: social/web networks, molecules/materials (drug discovery), fraud rings in financial graphs, knowledge-graph completion (→ GraphRAG), and recommendation. If meaning lives in the connections, a GNN learns from them rather than discarding them.

## Further reading

- [Graph neural network — deep learning for graph-structured data](https://en.wikipedia.org/wiki/Graph_neural_network)
- [Graph (abstract data type) — nodes and edges](https://en.wikipedia.org/wiki/Graph_(abstract_data_type))
