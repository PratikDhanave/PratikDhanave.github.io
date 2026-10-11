# Causal Graphs — Drawing What You Believe Causes What

*Causal reasoning gets dramatically clearer when you draw it. A causal graph is a diagram of what causes what — nodes for variables, arrows for causal influence — and it turns fuzzy debates about confounding and adjustment into visual rules you can actually check. This post introduces causal graphs (DAGs) and the single most useful thing they do: tell you exactly which variables to control for, and which ones you must leave alone.*

Post 3 said knowing *which* variables to adjust for is subtle and error-prone. This post is the tool that makes it a rule rather than a guess: the causal graph. Championed by Judea Pearl, it's the framework that complements potential outcomes (post 2) and brings discipline to observational causal inference (post 6). For engineers who like diagrams, it's the most intuitive entry into causal thinking.

## The graph: variables and arrows

A **causal graph** (a **directed acyclic graph**, or DAG, over the variables) represents your *assumptions* about causal structure:
- **Nodes** are variables (treatment, outcome, confounders, and others).
- **Arrows** point from cause to effect: `A → B` means "A causally influences B."
- **Directed and acyclic** — arrows have direction (causes point to effects) and there are no cycles (nothing causes itself through a loop).

The crucial point is that the graph encodes your *beliefs about the data-generating process* — it's a model of how the world works, drawn explicitly. This is valuable in itself: it forces you to state your causal assumptions out loud, where they can be examined and debated, instead of leaving them implicit in a regression. Two people who disagree about a causal conclusion often disagree about the *graph*, and drawing it surfaces the real disagreement. The graph doesn't prove causation — it's an assumption — but making the assumption explicit and visual is half the battle, because most causal mistakes come from unexamined structural assumptions.

## The three building blocks of causal structure

Every causal graph is built from three elementary patterns, and understanding how information flows through each is the key to the whole framework:

- **Chain: `A → B → C`** (B is a **mediator**). A affects C *through* B. Here A and C are correlated, and that correlation *is* causal (A really does cause C, via B). Critical implication: if you want A's *total* effect on C, you must **not** control for B — adjusting for the mediator would block the very causal pathway you're trying to measure. Controlling for a mediator is a classic over-adjustment error (post 3).
- **Fork: `A ← B → C`** (B is a **confounder**). B causes both A and C. This creates a *non-causal* correlation between A and C (the villain of post 3). Critical implication: to get A's true effect on C, you **must** control for B — adjusting for the confounder blocks the spurious path and reveals the real relationship. This is the one case where adjustment is required.
- **Collider: `A → B ← C`** (B is a **collider**). A and C both cause B, but A and C are *not* causally related. Critical and counterintuitive implication: A and C are *unrelated* until you control for B — and controlling for the collider **creates** a spurious correlation between them that wasn't there. Adjusting for a collider *introduces* bias. This is the subtle trap that trips up even experienced analysts, because the naive instinct "control for everything" actively manufactures false relationships here.

These three — chain (don't adjust the mediator), fork (must adjust the confounder), collider (never adjust the collider) — are the grammar of causal structure. The explosive insight is that **"control for more variables" is not always better** — adjusting for the right variable (confounder) removes bias, but adjusting for the wrong one (mediator or collider) *adds* bias. Whether to adjust for a variable depends entirely on its *role in the causal structure*, which is exactly what the graph tells you and a regression does not.

## The payoff: knowing what to adjust for

The practical power of causal graphs is a procedure for answering the question that confounding left open (post 3): *given my assumed causal structure, which variables must I control for to estimate this effect?* The graph answers it via path analysis (the formal version is Pearl's "backdoor criterion," but the intuition suffices):

- **Identify all the "backdoor" paths** — the non-causal paths connecting treatment and outcome through confounders (forks), which create spurious correlation.
- **Block them by adjusting** for the right confounding variables — closing the backdoor paths so only the true causal path remains.
- **Without opening new bias** — don't adjust for mediators (which block the real effect) or colliders (which open new spurious paths).

The result is a *principled adjustment set*: the exact variables to control for, derived from the causal structure rather than guessed or (worse) "throw everything into the regression." This is a genuine superpower for observational causal inference (post 6), because the hardest practical question there — *what do I adjust for?* — becomes a readable consequence of the graph. It also reveals when an effect is **not identifiable** at all from the available data (if a backdoor path runs through an *unmeasured* confounder, no adjustment can close it — post 3's unmeasured-confounding problem, now visible in the diagram).

The honest caveats keep it grounded: the graph is only as good as its assumptions — a wrong arrow gives wrong adjustment advice, and you usually can't *prove* the graph is correct (it encodes domain knowledge, which can be mistaken). And causal graphs tell you *what* to adjust for, not *how* (the estimation — matching, regression, propensity scores — is post 6). But within those limits, drawing the graph transforms causal reasoning from intuition into something you can inspect, debate, and compute over — which is why it's one of the most useful mental tools in all of data work, even when you never write down the formal math.

The throughline: a **causal graph** (a DAG — nodes = variables, arrows = causal influence) makes your **assumptions about what causes what explicit and visual**, surfacing disagreements and preventing unexamined structural mistakes. Its grammar is three building blocks with opposite adjustment rules: **chain** `A→B→C` (B a **mediator** — *don't* adjust, or you block the real effect), **fork** `A←B→C` (B a **confounder** — *must* adjust to remove spurious correlation), and **collider** `A→B←C` (B a **collider** — *never* adjust, or you *create* a spurious correlation). So "**control for more variables" is not always better** — the right role (confounder) removes bias, the wrong one (mediator/collider) adds it. The payoff is a **principled adjustment set** (close the non-causal "backdoor" paths through confounders without opening mediator/collider bias) and a way to see when an effect is **not identifiable** (a backdoor through an unmeasured confounder) — turning "what do I adjust for?" from a guess into a readable rule, as good as the graph's assumptions.

## Key takeaways

- A **causal graph** (directed acyclic graph) encodes your **assumptions** about causal structure — nodes = variables, arrows = cause→effect — forcing causal beliefs to be *explicit, visual, and debatable* (most causal mistakes are unexamined structural assumptions).
- Three building blocks have **opposite** adjustment rules: **chain** `A→B→C` (**mediator** B — do **not** adjust, or you block A's real effect on C), **fork** `A←B→C` (**confounder** B — you **must** adjust to kill the spurious correlation), **collider** `A→B←C` (**collider** B — **never** adjust, because controlling for it *creates* a false A–C correlation).
- Therefore **"control for everything" is wrong**: adjusting for a confounder removes bias, but adjusting for a **mediator** (blocks the real path) or a **collider** (opens a false path) *adds* bias — whether to adjust depends on the variable's **role in the structure**, which the graph shows and a regression doesn't.
- The payoff is a **principled adjustment set**: block the non-causal **backdoor paths** (through confounders) *without* adjusting mediators/colliders — turning "what do I control for?" into a readable rule; the graph also shows when an effect is **not identifiable** (backdoor through an *unmeasured* confounder — post 3's problem made visible).
- Caveats: the graph is only as good as its **assumptions** (a wrong arrow → wrong advice; usually unprovable), and it tells you *what* to adjust for, not *how* (estimation is post 6) — but it transforms causal reasoning from intuition into something inspectable and computable.

## Further reading

- [Directed acyclic graph — the structure of causal graphs](https://en.wikipedia.org/wiki/Directed_acyclic_graph)
- [Causal inference — graphical methods for identifying effects](https://en.wikipedia.org/wiki/Causal_inference)
