# Interpreting Deep Networks and LLMs

*The hardest interpretability frontier is the models that matter most right now: deep neural networks and large language models, with billions of parameters and no obvious place to look for "the reason." The attribution methods that work on tabular models strain here, and a new field — mechanistic interpretability — is trying to reverse-engineer what these networks actually compute. This post covers how we peer inside deep models and LLMs, and why it's both crucial and genuinely unsolved.*

Posts 3–6 covered methods that largely treat the model as a black box. This post is about the deepest black boxes — deep nets and LLMs — where interpretability is hardest and highest-stakes. It's where the field is most active and least settled, and where honesty about what we *can't* yet explain matters most.

## Why deep models are especially hard

Deep networks defeat the comfortable assumptions of tabular interpretability:

- **No meaningful input features to attribute to.** SHAP on a tabular model attributes to "income" and "debt" — meaningful features. But a deep net's inputs are *raw pixels* or *tokens*, and "this pixel contributed 0.02" isn't a human-meaningful explanation. The model's real "concepts" live in its *internal* representations, not its inputs.
- **Enormous scale and distributed representations.** Meaning in a deep net is spread across millions or billions of parameters and activations, with concepts represented in combinations of neurons rather than individual ones (and single neurons often responding to many unrelated things — "superposition"). There's no single weight to read.
- **Emergent, compositional behavior** — especially in LLMs, capabilities emerge from the interaction of many layers in ways nobody explicitly designed, so there's no blueprint to consult.

So the tabular toolkit adapts awkwardly, and new approaches are needed. Two broad directions have emerged: *attribution adapted to deep models* (what in the input mattered) and *mechanistic interpretability* (what the network internally computes).

## Attribution and probing for deep models

The first direction extends the attribution idea (posts 3–5) to deep nets, mostly asking "which parts of the input drove this output?":

- **Saliency / attribution maps** — for vision, highlight which *pixels or regions* most influenced the prediction (gradient-based methods and their relatives). The output is a heatmap over the image: "the model looked here." These are intuitive and widely used, and they're exactly what caught the "husky = snow" and "pneumonia = scanner" failures (post 1). But they're known to be **fragile and sometimes misleading** — some saliency methods produce similar-looking maps regardless of what the model actually learned, so a plausible heatmap isn't proof the model is reasoning well.
- **Attention visualization** — for transformers/LLMs, show which input tokens the model "attended to." Intuitive, but with a crucial caveat: **attention is not explanation** — where a model attends is not reliably *why* it predicted something, and reading attention maps as explanations is a documented mistake. Attention is suggestive, not authoritative.
- **Probing** — train a simple classifier on a network's *internal activations* to test whether some concept (part of speech, sentiment, a fact) is represented there. Probing reveals *what information* the network encodes at various layers, giving insight into its internal representations — a key tool for understanding what LLMs "know" and where.
- **Feature visualization** — for vision nets, synthesize the input that maximally activates a given neuron/channel, revealing what it detects (edges, textures, then object parts, then whole objects up the layers). This produced the famous result that CNNs build a hierarchy of increasingly abstract features.

These help, but note they're largely about *input attribution* and *what's encoded*, not the full *how* of the computation — which is the gap mechanistic interpretability tries to fill.

## Mechanistic interpretability and the honest state of the art

The most ambitious direction is **mechanistic interpretability**: trying to *reverse-engineer* a network into human-understandable algorithms — not "which input mattered" but "what computation is this network actually performing, circuit by circuit?" The goal is to identify **circuits** (subgraphs of neurons implementing a specific function) and **features** (the concepts the network represents) and show how they combine to produce behavior, as if decompiling the network into readable logic.

This is where much frontier interpretability energy goes, especially for LLMs and AI safety, because:
- **For safety, we need to know what models actually do** — whether a powerful model has learned deceptive or dangerous behaviors, whether it's reasoning or pattern-matching, what it "knows." Input attribution can't answer these; understanding the internal mechanism might.
- There have been real successes — identifying specific circuits (e.g. mechanisms for in-context learning or simple reasoning), and work on resolving superposition into interpretable features — genuine progress in reading pieces of these networks.

But honesty is essential, and it's the most important thing to convey: **we largely cannot yet explain why large models do what they do.** Mechanistic interpretability has illuminated *fragments* of small-to-medium networks and specific behaviors, but fully reverse-engineering a frontier LLM is far beyond current ability — the scale is staggering, superposition makes features hard to isolate, and the techniques are young. So the state of the art is: good tools for *input attribution* (fragile but useful), useful *probing* of what's encoded, and *early, partial* mechanistic understanding of internals — with the frontier models that most need explaining remaining substantially opaque. This matters because it tempers the expectation that we can simply "open up" an LLM and read its reasons; for now, we can see shadows and fragments, not the whole machine. Understanding this limit is itself crucial interpretability literacy — it's the difference between appropriate caution about deploying powerful opaque models and false confidence that we understand them.

The throughline: deep nets and LLMs are the hardest interpretability frontier because their inputs (**pixels/tokens**) aren't human-meaningful features, meaning is spread across billions of parameters in **distributed, superposed** representations, and behavior is **emergent** — so the tabular toolkit strains. Two directions respond: **input attribution/probing** — **saliency maps** (which pixels mattered — caught the husky=snow failure, but **fragile/misleading**), **attention visualization** (**attention is not explanation**), **probing** (train classifiers on internal activations to see *what's encoded*), and **feature visualization** (what a neuron detects — revealing CNNs' feature hierarchy) — and **mechanistic interpretability**, the ambitious attempt to reverse-engineer networks into human-readable **circuits and features**, crucial for AI safety (knowing whether a model reasons, deceives, or merely pattern-matches). The honest state of the art: good-but-fragile input attribution, useful probing, and only **early, partial** mechanistic understanding — **we largely cannot yet explain why frontier LLMs do what they do**, a limit whose recognition is itself essential literacy against false confidence in opaque models.

## Key takeaways

- Deep nets/LLMs are the hardest frontier: inputs are **raw pixels/tokens** (not meaningful features to attribute to), meaning is **distributed** across billions of parameters with **superposition** (neurons encode many concepts), and behavior is **emergent/compositional** — so tabular methods (SHAP on "income") don't transfer cleanly.
- **Input-attribution/probing** tools adapt the attribution idea: **saliency/attribution maps** (which pixels/regions mattered — caught husky=snow, pneumonia=scanner, but **fragile and sometimes misleading**), **attention visualization** (intuitive but **"attention is not explanation"** — where a model attends ≠ why it predicted), **probing** (classifiers on internal activations reveal *what concepts are encoded* and where), and **feature visualization** (what maximally activates a neuron — revealed CNNs' edge→part→object hierarchy).
- These mostly explain **input influence and what's encoded**, not the full **how** of the computation — the gap **mechanistic interpretability** targets.
- **Mechanistic interpretability** tries to reverse-engineer networks into human-understandable **circuits** (neuron subgraphs implementing functions) and **features** (represented concepts) — decompiling the model — crucial for **AI safety** (does a powerful model reason, deceive, or pattern-match?), with real but **fragmentary** successes.
- The honest state of the art: good-but-fragile attribution, useful probing, only **early/partial** mechanistic understanding — **we largely cannot yet explain why frontier LLMs behave as they do**; recognizing this limit is essential literacy, separating appropriate caution about deploying opaque models from false confidence that we understand them.

## Further reading

- [Explainable artificial intelligence — interpreting deep networks](https://en.wikipedia.org/wiki/Explainable_artificial_intelligence)
- [Large language model — the opaque models interpretability targets](https://en.wikipedia.org/wiki/Large_language_model)
