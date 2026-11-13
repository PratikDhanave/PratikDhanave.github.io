<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/setax-01-what-evolves.html -->

# What Evolves? A Map of Self-Evolving AI

*The phrase "self-evolving agent" gets attached to systems so different that arguments about it are usually category errors: an agent that rewrites its own prompts, a loop that breeds faster GPU kernels, and a model that updates its weights from its own consensus answers are all "self-evolving" — and almost nothing else about them is alike. This series builds a working taxonomy by asking three questions that dissolve the terminology fights: what evolves, what feedback drives it, and where does the loop close?*

This blog already has two deep series in this space — [Self-Evolving Agents](/blog/series/self-evolving-agents/) (the practitioner mechanisms) and [The Frontier](/blog/series/self-evolving-agents-the-frontier/) (automated agent design and open-ended search). This series sits above and beside them: the organizing map, plus deep treatment of the two loci those series don't cover — evolution of *artifacts* and evolution of *model weights*.

## The anatomy: model, harness, artifact

Three components recur in every system the label touches, and naming them is half the taxonomy:

- **The model** — the weights: the trained network that maps context to output. Expensive to change (training compute, data pipelines, regression risk), opaque to inspect, and the only place certain capabilities can ultimately live.
- **The harness** — everything wrapped around the model that makes it an *agent*: the loop, the prompts, the memory ([Agent Memory Systems](/blog/series/agent-memory-systems/) is this blog's deep dive), the tools and skills, the routing between specialists. Cheap to change, inspectable, reversible — which is why most production "self-improvement" happens here.
- **The artifacts** — what the system produces: code, algorithms, proofs, designs, documents, policies. Usually treated as mere output; the interesting move of the last few years is treating artifacts as *themselves* the thing under evolution.

An agent is a model plus a harness; a self-evolving system is any arrangement where the outputs of running the system feed back into improving one or more of these three components.

## The three loci of evolution

Sort every system by *what the feedback changes* and three clean families emerge — the series' spine:

- **Artifact evolution** (posts 2–3): the model and harness stay fixed; the *artifact* is generated, evaluated, and regenerated until it's excellent — the algorithm made faster, the kernel made tighter, the hypothesis made sharper. The system improves its products, not itself; the AlphaEvolve-and-kin pattern of search over candidate artifacts with an LLM as the mutation operator.
- **Harness evolution** (post 4): the model stays fixed; the *scaffolding* improves — prompts refined from failures, memories and lessons accumulated, tools and skills written and reused, routing restructured. This is where the two existing series live, and post 4 places their mechanisms on the map rather than re-teaching them.
- **Model evolution** (posts 5–6): the weights themselves change, specifically *without gold-labeled answers* — self-training on pseudo-labels, self-play, consensus-as-reward, test-time training. The most powerful locus and the most dangerous one, because weight changes are global, persistent, and hard to inspect.

Two cross-cutting axes complete the taxonomy. **Feedback** (post 7): what signal drives the loop — an exact verifier, an environment, a learned judge, self-consistency, a human — matters more than which locus it feeds, because every self-evolution failure mode is ultimately a feedback failure. **Loop closure** (post 8): where and when the improvement is applied — inside one task, between tasks, offline in a training phase — which determines blast radius, reversibility, and what governance the loop needs.

## Why a taxonomy, and not a definition

Definitions of "self-evolving" or "self-improving" invite boundary wars (is a RAG index update evolution? is fine-tuning?). The taxonomy sidesteps them: any system can be *located* — what evolves, on what feedback, with the loop closing where — and once located, its real properties follow: cost of a change, reversibility, inspectability, failure modes, and the right safety posture. Locating systems this way also exposes the field's actual trajectory, which the closing post takes up: the frontier isn't any single locus but their *composition* — loops that improve artifacts, distill the lessons into the harness, and eventually consolidate them into weights. The map is how you reason about that composition without drowning in terminology.

The takeaway: self-evolving AI untangles into an anatomy — **model, harness, artifact** — and three loci of evolution: **artifact evolution** (improve the products; models fixed), **harness evolution** (improve the scaffolding; this blog's existing two series), and **model evolution** (improve the weights without gold answers), crossed by two axes — **what feedback drives the loop** and **where the loop closes**. Three questions replace the definition fights: what evolves, what feeds it, where it closes — and the rest of the series walks the map.

## Key takeaways

- The anatomy: **model** (expensive, opaque, ultimate), **harness** (cheap, inspectable, reversible — where production self-improvement lives), **artifact** (the products, newly treated as evolvable).
- The three loci: **artifact evolution** (posts 2–3, the uncovered AlphaEvolve-class territory), **harness evolution** (post 4, mapping the existing series), **model evolution** (posts 5–6, learning without labels).
- The two axes: **feedback type** (post 7 — every failure mode is a feedback failure) and **loop closure** (post 8 — blast radius, reversibility, governance).
- Taxonomy over definition: locate a system by the three questions and its cost, risk, and safety posture follow — no boundary wars required.

## Further reading

- [Recursive self-improvement — the limiting idea the taxonomy grounds](https://en.wikipedia.org/wiki/Recursive_self-improvement)
- [Software agent — the model-plus-harness unit doing the evolving](https://en.wikipedia.org/wiki/Software_agent)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-06
Canonical: https://pratikdhanave.com/blog/posts/setax-01-what-evolves.html
Attribution: please link the canonical URL when citing or quoting this post.
