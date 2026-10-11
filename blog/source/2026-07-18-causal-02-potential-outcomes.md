# Potential Outcomes — Defining a Causal Effect Precisely

*To reason about causation rigorously, you first need to define what a "causal effect" even is — and the answer is more subtle than it looks. The potential-outcomes framework defines it through a counterfactual: the difference between what happened and what would have happened otherwise. That single idea, and the "fundamental problem" that you can never observe both, is the foundation on which all of causal inference is built.*

Post 1 argued causation is about intervention, not observation. This post makes "causal effect" precise using the **potential outcomes** framework (the Neyman-Rubin model), the dominant language of modern causal inference. It's abstract but essential: once you can state exactly what you're trying to estimate, the methods in later posts become ways of estimating that well-defined thing.

## The counterfactual definition

The potential-outcomes idea is this: for any unit (a user, a patient) and a treatment (shipped feature, drug), there are **two potential outcomes**:
- **Y(treated)** — the outcome if the unit *receives* the treatment.
- **Y(untreated)** — the outcome if the unit *does not*.

The **causal effect** for that unit is the *difference* between them: `Y(treated) − Y(untreated)` — how much the treatment changed *this unit's* outcome compared to the alternative. This is a **counterfactual** definition: the causal effect compares the real world to a *counter-to-fact* world that didn't happen. "Did the feature cause this user to retain?" means "did they retain *with* the feature when they would *not* have *without* it?"

This framing is powerful because it defines causation cleanly and operationally — a cause is something that makes an outcome different from what it would otherwise have been — and it forces precision: to claim a causal effect you must be clear about *the treatment, the outcome, and the counterfactual comparison.* Vague causal claims usually fall apart the moment you try to state them in potential-outcomes terms, which is itself a useful discipline.

## The fundamental problem of causal inference

Here's the catch that defines the entire field. For any single unit, **you can only ever observe one of the two potential outcomes.** A user either got the feature or didn't; you see their outcome under the path taken and *never* under the path not taken. The counterfactual — what *would* have happened the other way — is permanently unobservable for that individual.

This is **the fundamental problem of causal inference**: the individual causal effect `Y(treated) − Y(untreated)` can never be directly measured, because one of its two terms is always missing. Causal inference is, at its heart, a **missing-data problem** — half the data you'd need is counterfactual and unobservable. You cannot simply *look up* a causal effect; you must *infer* the missing counterfactual, and every method in the field is a strategy for doing that credibly.

This reframes what causal inference even is: not measurement, but the principled estimation of something unobservable. It also explains why causal claims demand assumptions (post 3) — you're always inferring a counterfactual you can't see, so you need assumptions about how the observed world relates to the unseen one. No assumptions, no causal conclusion; that's not a weakness of particular methods, it's inherent to the problem.

## From individuals to averages — and what makes estimation valid

Since individual causal effects are unobservable, causal inference targets the **average causal effect** across a population: the **Average Treatment Effect (ATE)** — the mean of `Y(treated) − Y(untreated)` over everyone. And here's the key move that makes the impossible possible: while you can't see *both* outcomes for any *one* unit, you *can* compare the *treated group* to the *untreated group* and estimate the average effect — **but only if the two groups are comparable.**

That "if" is everything:
- If the treated and untreated groups are alike in every relevant way *except* the treatment, then the untreated group's average outcome is a valid stand-in for what *would* have happened to the treated group without treatment — the missing counterfactual, recovered at the group level. The difference in group averages is then the causal effect.
- If the groups *differ* in other ways that also affect the outcome (they're **confounded**, post 3), the comparison is contaminated: you can't tell whether the outcome gap came from the treatment or from the pre-existing differences. The counterfactual stand-in is invalid.

So the entire problem reduces to: **make the treated and untreated groups comparable, so one can serve as the other's counterfactual.** This is the lens for everything that follows. **Randomized experiments** (post 4) achieve comparability *by construction* — randomly assigning treatment makes the groups statistically identical on average, so the comparison is clean (which is why randomization is the gold standard). **Observational methods** (posts 6–7) try to *reconstruct* comparability from data you didn't control, by adjusting for the ways the groups differ — harder and assumption-laden, precisely because you have to argue the groups are comparable rather than guarantee it.

The potential-outcomes framework thus gives the field its spine: define the causal effect as a counterfactual difference (unobservable per individual — the fundamental problem), target the average effect over a population, and estimate it by comparing groups that are — or have been made — comparable, so each serves as the other's missing counterfactual. Every method is a different answer to "how do I get comparable groups?" Understanding that makes the rest of causal inference legible.

The throughline: the **potential outcomes** framework defines a **causal effect** as a **counterfactual** difference — `Y(treated) − Y(untreated)`, the gap between what happened and what *would* have happened otherwise — which is clean and forces precision about treatment, outcome, and comparison. But the **fundamental problem of causal inference** is that you can only ever observe *one* potential outcome per unit (the path taken, never the counterfactual), making causal inference a **missing-data problem** of inferring the unobservable — which is why it always requires **assumptions**. Since individual effects are unobservable, the field targets the **average treatment effect** and estimates it by comparing the **treated and untreated groups** — valid *only if the groups are comparable* (alike except for treatment), so one serves as the other's missing counterfactual. Thus everything reduces to **making groups comparable**: randomized experiments do it *by construction* (post 4), observational methods *reconstruct* it from data (posts 6–7) — the lens for the whole field.

## Key takeaways

- The **potential outcomes** framework defines a **causal effect** as a **counterfactual** difference — `Y(treated) − Y(untreated)`, what happened versus what *would* have happened otherwise — forcing precision about the treatment, outcome, and comparison (vague causal claims collapse when stated this way).
- The **fundamental problem of causal inference**: for any unit you observe only **one** potential outcome (the path taken), never the counterfactual — so the individual causal effect is never directly measurable, making causal inference fundamentally a **missing-data problem** requiring **assumptions** (no assumptions, no causal conclusion).
- Because individual effects are unobservable, the field targets the **Average Treatment Effect (ATE)** across a population, estimated by comparing the **treated group** to the **untreated group**.
- That comparison is valid **only if the groups are comparable** (alike in everything relevant except treatment) — then the untreated group's outcome stands in for the treated group's missing counterfactual; if the groups differ (are **confounded**, post 3), the comparison is contaminated and the causal claim fails.
- Everything reduces to **making the groups comparable**: **randomized experiments** achieve it *by construction* (post 4, the gold standard); **observational methods** try to *reconstruct* it by adjusting for differences (posts 6–7, harder and assumption-laden) — every method is a different answer to "how do I get comparable groups?"

## Further reading

- [Rubin causal model — the potential-outcomes framework](https://en.wikipedia.org/wiki/Rubin_causal_model)
- [Average treatment effect — the population-level causal estimand](https://en.wikipedia.org/wiki/Average_treatment_effect)
