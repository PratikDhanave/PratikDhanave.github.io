# Counterfactual and Example-Based Explanations

*Feature attributions tell you which inputs mattered, but humans often understand decisions better through a different lens: "what would have to change for a different outcome?" and "what similar cases did the model see?" Counterfactual and example-based explanations answer exactly those questions — and they're often more actionable and more intuitive than attribution scores. This post covers the explanation styles that speak the way people actually reason.*

Posts 3–5 covered attribution methods (importance, LIME, SHAP) that assign *credit* to features. This post covers a complementary family that explains by *contrast* and *example* rather than by scores. They matter because they map onto how humans naturally explain things — and because a counterfactual is often the single most *useful* explanation you can give a person affected by a model.

## Counterfactual explanations: what would change the outcome

A **counterfactual explanation** answers: *what is the smallest change to the input that would flip the model's decision?* Instead of "your loan was denied because debt contributed −0.3" (an attribution), it says "**your loan would have been approved if your income were $5,000 higher**, or if your debt were $3,000 lower." It explains a decision by describing the nearest alternative world where the outcome differs.

This is powerful for reasons attributions aren't:
- **It's actionable.** A counterfactual tells the person *what to do* to get a different result — exactly what someone denied a loan, a job, or a benefit most wants to know. "Reduce your debt by $3k" is directly useful in a way "debt had weight −0.3" is not. For decisions affecting people, the counterfactual is often the *most humane and useful* explanation form.
- **It's intuitive.** Humans naturally explain by contrast ("it would have been fine if…"), so counterfactuals match how people already reason, requiring no understanding of the model.
- **It's model-agnostic and needs no internal access.** You find counterfactuals by searching inputs that flip the output — treating the model as a black box.
- **It connects to recourse and rights.** The right-to-explanation and "algorithmic recourse" concerns (post 1, and AI governance) are often best served by counterfactuals, because they tell people how to *change* an adverse automated decision.

The craft is in finding *good* counterfactuals: the change should be **small** (close to the original), **realistic** (don't suggest changing age or an immutable attribute; suggest feasible changes), and **actionable** (something the person can actually do). A naive counterfactual ("if you were 20 years younger…") is useless or offensive, so real methods constrain the search to plausible, changeable features — which also ties counterfactuals to fairness (recourse should be achievable, not a mirage). And an important caveat echoing the whole series: a counterfactual describes what would change the *model's* output, which is only the same as changing the *real* outcome if the model is causally sound — so counterfactual explanations can suggest "recourse" that games the model without changing the underlying reality (again, the causal caveat).

## Example-based explanations: learning from cases

The second family explains a prediction by pointing to *other data points* rather than to features — mapping onto how humans reason by analogy and precedent:

- **Nearest neighbors / similar cases.** "This application was flagged because it resembles these past fraudulent applications." Explaining by showing the most similar training examples is intuitive (it's how case law and medical diagnosis often work) and directly builds trust or suspicion ("does this really look like those?").
- **Prototypes and criticisms.** Summarize what the model considers *typical* of a class (prototypes) and the outliers it handles poorly (criticisms), giving a feel for the model's mental model of each category.
- **Influential instances.** Identify which *training examples* most shaped the model (or this prediction) — if a prediction traces back to a few influential, possibly mislabeled, training points, that's a debugging goldmine (a training-data problem revealed through explanation).

Example-based explanations are valuable precisely where attributions feel abstract: a doctor may trust "this scan resembles these confirmed cases" more than a heatmap of pixel importances, and a reviewer may understand a fraud flag better through similar past cases than through feature scores. They're also a bridge to data quality — tracing predictions to training examples surfaces label errors and gaps.

## Choosing an explanation style — matching the method to the audience

The broader lesson of this post is that **there is no single "right" explanation — the best style depends on the question and the audience**, and a mature interpretability practice uses several:

- **Attribution (importance, LIME, SHAP — posts 3–5)** answers "*which features* drove this?" — best for debugging, auditing, and technical understanding.
- **Counterfactual** answers "*what would change* the outcome?" — best for giving affected people actionable recourse and for decisions where "what do I do about it?" is the real question.
- **Example-based** answers "*what similar cases* did the model see?" — best for building trust through analogy, for expert users (doctors, reviewers) who reason by precedent, and for surfacing training-data problems.

Often you want *several* for the same decision: a SHAP breakdown for the engineer, a counterfactual for the applicant, a set of similar cases for the reviewer. The methods are complementary, not competing — they illuminate different facets of the same model behavior. And all share the series' recurring humility: each is an *approximation and a framing*, useful for the question it answers and misleading if pushed beyond it (a counterfactual that's actionable-but-not-causal, an example-set that's cherry-picked, an attribution that hides interactions). The skill is choosing the explanation that genuinely serves the person who needs it — which, for human-affecting decisions, is very often the counterfactual, because it respects that people don't just want to know *why*; they want to know *what now*.

The throughline: beyond feature attributions (posts 3–5), two families explain by **contrast** and **example** — matching how humans actually reason. A **counterfactual explanation** gives the *smallest change that flips the decision* ("approved if income were $5k higher") — **actionable** (tells people what to do — the most humane form for human-affecting decisions, tied to recourse/right-to-explanation), **intuitive** (humans reason by contrast), and **model-agnostic** — but good ones must be **small, realistic, and actionable** (never "if you were younger"), and they change the *model's* output, not necessarily the real outcome (the causal caveat — recourse can game the model). **Example-based** explanations point to *other data points* — **similar cases** (reason by analogy/precedent, trusted by doctors/reviewers), **prototypes/criticisms**, and **influential instances** (surfacing training-data errors). The lesson: **no single right explanation** — match the style to the question and audience (attribution for debugging, counterfactual for recourse, examples for trust), often using several, all held as useful-but-approximate framings.

## Key takeaways

- Beyond attribution (posts 3–5), two complementary families explain by **contrast** and **example**, matching human reasoning.
- A **counterfactual explanation** gives the *smallest input change that flips the outcome* ("approved if income were $5k higher, or debt $3k lower") — it's **actionable** (tells affected people what to *do* — often the most useful/humane explanation, serving **recourse** and right-to-explanation), **intuitive** (contrast-based), and **model-agnostic**; good ones must be **small, realistic, and actionable** (never suggest immutable changes like age), and they flip the **model's** output, not necessarily the real outcome (causal caveat — recourse can game the model).
- **Example-based** explanations point to *data points* not features: **similar cases** ("resembles these past frauds" — reasoning by analogy/precedent, trusted by experts), **prototypes/criticisms** (typical vs poorly-handled examples), and **influential instances** (which training points shaped the prediction — surfacing label errors, a debugging goldmine).
- There is **no single right explanation**: **attribution** answers "which features?" (debugging/auditing), **counterfactual** answers "what would change it?" (recourse/action), **example-based** answers "what similar cases?" (trust/analogy, data-quality) — match style to **question and audience**, often using several for one decision (SHAP for the engineer, counterfactual for the applicant, cases for the reviewer).
- All share the series' **humility**: each is an approximation and a *framing*, useful for its question and misleading beyond it — the skill is choosing the explanation that genuinely serves the person who needs it (for human-affecting decisions, often the **counterfactual**, because people want to know not just *why* but *what now*).

## Further reading

- [Explainable artificial intelligence — counterfactual and example-based explanations](https://en.wikipedia.org/wiki/Explainable_artificial_intelligence)
- [Case-based reasoning — explaining by analogy to prior cases](https://en.wikipedia.org/wiki/Case-based_reasoning)
