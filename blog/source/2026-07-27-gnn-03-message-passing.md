# Message Passing — The Core Mechanism of Every GNN

*Strip away the variations and every graph neural network does the same fundamental thing: each node repeatedly gathers information from its neighbors and updates itself. This is message passing, and it's the single idea you need to understand GNNs — GCN, GraphSAGE, GAT, and the rest are all just different choices for how a node listens to its neighbors. This post builds message passing from scratch and shows why it elegantly satisfies everything a graph architecture must.*

Post 1 said the key is operating locally and identically at every node; post 2 said the goal is good embeddings. This post is the mechanism that delivers both: the message-passing framework. Understanding it deeply means understanding GNNs in general, because the specific architectures (posts 4–6) are all instances of this one pattern.

## The core loop: aggregate and update

Message passing builds a node's embedding by having it listen to its graph neighborhood, in a repeated two-step loop. For each node, in each round (**layer**):

1. **Aggregate** — gather the current representations of all the node's neighbors and combine them into a single "message" (for example, by summing, averaging, or taking a weighted combination). This is where the node pulls in information from its surroundings.
2. **Update** — combine that aggregated neighbor message with the node's *own* current representation, through a small learned neural network, to produce the node's *new* representation.

Every node does this *simultaneously* with the *same* learned aggregate and update functions, so the operation is shared everywhere — which is exactly what gives GNNs their two required properties (post 1): it's **permutation-equivariant** (aggregation treats neighbors as an unordered set, so node numbering doesn't matter — this is why sum/mean/max are used, since they ignore order) and it **handles any structure** (a node aggregates over however many neighbors it has, so any connectivity works). The entire GNN is this loop, run for a few layers, with the learned functions trained end-to-end for the task (post 2). That's it — message passing is the whole engine.

## Why stacking layers lets information travel

A single round of message passing lets each node see only its *immediate* neighbors. The power comes from **stacking layers**: after two rounds, a node has heard from its neighbors — who, in the previous round, heard from *their* neighbors — so the node now indirectly incorporates information from *two hops* away. After *k* layers, each node's embedding reflects its entire **k-hop neighborhood**.

This is the crucial intuition: **the number of layers is the radius of the graph a node can "see."** One layer = immediate neighbors; three layers = everything within three hops. You choose the number of layers to match how far relevant information sits in your graph — if a node's label depends on its local cluster, two or three layers suffice; if it depends on distant structure, you'd need more. This progressive widening of each node's receptive field is directly analogous to how stacking convolutional layers in a CNN grows the receptive field over an image — message passing is, in a real sense, "convolution generalized to graphs," which is why the first great GNN is called a graph *convolutional* network (post 4).

## The failure modes that shape real GNNs

Message passing is elegant, but stacking layers naively breaks down — and knowing *how* explains most of the design choices and limitations in the field:

- **Over-smoothing.** With too many layers, every node ends up aggregating information from almost the whole graph, so all node embeddings converge toward the *same* vector — they become indistinguishable and the model loses the local detail that made nodes different. This is why GNNs are usually **shallow** (2–4 layers), unlike the very deep stacks common in CNNs and transformers. Over-smoothing is the defining tension of GNN depth: you need enough layers to reach relevant information but few enough to keep nodes distinct.
- **Over-squashing.** Information from an exponentially growing number of distant nodes gets compressed into a fixed-size embedding, so signal from far away gets "squashed" and lost. This makes long-range dependencies on graphs genuinely hard, and it's an active research problem.
- **The bottleneck of fixed depth.** Because a *k*-layer GNN only sees *k* hops, it structurally cannot capture dependencies beyond that radius — a real limit on what message passing can learn.

These aren't footnotes — they're why GNN architectures differ and why GNNs look different from other deep nets (shallow, carefully designed aggregation). The variations in posts 4–6 are largely different answers to "how should a node aggregate its neighbors?" chosen to get good representations within these constraints: GCN uses a fixed normalized average, GraphSAGE samples neighbors and supports flexible aggregators, GAT learns *attention* weights so a node listens more to important neighbors. All three are the *same* aggregate-and-update loop — they differ only in the aggregate step. Once you see message passing as the universal skeleton, every GNN architecture is just a choice of how nodes listen.

The throughline: every GNN is the same **message-passing** loop — each node, each **layer**, **aggregates** its neighbors' current representations into a message (sum/mean/max/weighted — order-ignoring, which gives permutation-equivariance) and **updates** by combining that message with its own representation via a shared learned network; running this for a few layers, trained end-to-end, *is* the GNN. **Stacking layers** widens each node's view — after *k* layers a node sees its **k-hop neighborhood** (layers = receptive-field radius) — making message passing "convolution generalized to graphs." But naive depth breaks down: **over-smoothing** (all embeddings converge to the same vector — why GNNs are shallow, 2–4 layers), **over-squashing** (distant signal compressed away), and the **fixed-depth bottleneck** (can't see beyond *k* hops). The architectures in posts 4–6 (GCN, GraphSAGE, GAT) are all this same loop differing only in *how a node aggregates its neighbors*.

## Key takeaways

- **Message passing** is the universal GNN mechanism: each node, per **layer**, **aggregates** its neighbors' current representations into a message and **updates** by combining that with its own representation through a *shared learned* network — the whole GNN is this loop run for a few layers, trained end-to-end.
- Aggregation uses **order-ignoring** operations (sum/mean/max/weighted) over the neighbor *set*, which is what makes GNNs **permutation-equivariant** and able to handle **any connectivity** (post 1's required properties).
- **Stacking layers** grows each node's receptive field: after *k* layers a node incorporates its **k-hop neighborhood**, so **layers = the radius a node can see** — analogous to stacking CNN convolutions (message passing is "convolution generalized to graphs").
- Naive depth fails via **over-smoothing** (too many layers → all embeddings converge to the same vector, nodes become indistinguishable — why GNNs stay **shallow**, 2–4 layers), **over-squashing** (distant information compressed into a fixed vector and lost), and the **fixed-depth bottleneck** (can't capture dependencies beyond *k* hops).
- The architectures (GCN, GraphSAGE, GAT — posts 4–6) are all the **same aggregate-and-update loop**, differing only in *how a node aggregates its neighbors* (fixed normalized average vs sampled flexible aggregators vs learned attention) — so message passing is the one idea that unlocks all of them.

## Further reading

- [Graph neural network — the message-passing framework](https://en.wikipedia.org/wiki/Graph_neural_network)
- [Convolutional neural network — the receptive-field analogy](https://en.wikipedia.org/wiki/Convolutional_neural_network)
