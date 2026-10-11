# Interpretability in Practice — Choosing Methods and Avoiding Traps

*Interpretability has a toolbox — intrinsic models, feature importance, LIME, SHAP, counterfactuals, saliency maps — but knowing the tools isn't the same as using them wisely. The real skill is matching the method to the need, reading explanations with appropriate skepticism, and avoiding the traps that turn interpretability into false confidence. This closing post is the practical judgment the series was building toward: how to actually do interpretability without fooling yourself.*

Posts 1–7 built the methods; this post is how to use them well. The recurring theme of the series — explanations are useful approximations, not truth — comes to a head here, because the biggest danger in interpretability isn't having no explanation, it's trusting a bad one. This post is about using the toolbox with the skepticism it requires.

## Matching the method to the need

There's no universally best method; the right choice depends on the model, the data, the audience, and the question (posts 2, 6). A practical decision guide:

- **By model/data:** For **tabular** models, **SHAP** (especially TreeSHAP) is the strong default — fast and principled; **permutation importance** (post 3) for a quick global ranking; an **intrinsic** model (post 2) if you can afford it. For **images**, saliency/attribution maps (post 7, with skepticism). For **text/LLMs**, attention is suggestive-only, probing and example-based methods help, and mechanistic interpretability is frontier/partial (post 7).
- **By level/question:** **Global** understanding ("what does the model rely on overall?") → feature importance, SHAP summaries. **Local** ("why *this* prediction?") → SHAP local, LIME, counterfactuals. **Actionable recourse** ("what would change it?") → counterfactuals (post 6). **Trust by analogy** → example-based (post 6).
- **By audience:** **Engineers** want attributions for debugging; **affected individuals** want counterfactuals (actionable recourse); **domain experts** often prefer example-based (similar cases); **regulators** want documented, consistent explanations and evidence of fairness auditing.
- **Prefer the strongest option:** intrinsic models give faithful explanations for free (post 2); among post-hoc methods, SHAP's guarantees make it more trustworthy than LIME (posts 4–5). Reach down the ladder only when the stronger option isn't feasible.

The meta-point: use *several* methods for important decisions (a SHAP breakdown, a counterfactual, similar cases) — they illuminate different facets, and agreement across methods is reassuring while disagreement is a warning sign worth investigating.

## The traps that cause false confidence

The series' hardest-won lessons are the traps, because interpretability's failure mode is *confident wrongness* — an explanation that looks authoritative and misleads:

- **Explanations are approximations, not truth** (the series' through-line). Post-hoc explanations are *models of the model*, and they can be unfaithful — LIME is unstable (post 4), saliency maps can be misleading (post 7), and even SHAP faithfully explains a flawed model's flaws (post 5). Never treat an explanation as the model's actual reasoning; treat it as a useful, fallible summary.
- **Explanation is not causation** (the most common and costly trap, linking to the [causal inference](/blog/series/causal-inference-for-engineers/) series). "Feature X is important / has high SHAP value" means the *model uses X*, **not** that X *causes* the outcome or that *changing X* would change anything. Reading attributions as causal — and acting on them ("X is important, so intervene on X") — is the single most damaging interpretability mistake, and it's everywhere.
- **Plausible ≠ correct.** A believable explanation ("the model denied the loan due to high debt — makes sense!") feels validating but may not reflect what the model actually did — confirmation bias makes us accept explanations that match our priors. An explanation's *plausibility* is not evidence of its *faithfulness*.
- **Explanations can be gamed.** Models can be adversarially built to produce innocent-looking explanations while behaving badly (post 4) — so an explanation used for auditing isn't automatically trustworthy; the auditor must verify, not just read.
- **Interpretability-washing.** Producing an explanation can create false comfort that lets a bad or biased model ship — "look, we explained it" becomes cover rather than genuine scrutiny. An explanation is a tool for *finding* problems, not a certificate that there are none.

The defense against all of these is **skepticism and validation**: check whether explanations are *stable* (rerun them), whether methods *agree*, whether the explanation makes sense *and* survives probing (not just matches your priors), and whether it's being used to genuinely interrogate the model or to rubber-stamp it. Interpretability done without this skepticism is worse than none, because it manufactures confidence without justification.

## The bottom line

Pulling the series together into working wisdom:

- **Interpretability is essential, not optional** (post 1) — for trust, debugging, fairness, accountability, and regulation. As models grow more powerful and more deployed in high-stakes settings, the ability to understand them is increasingly a *requirement*, sometimes a legal one.
- **Prefer interpretable models when you can** (post 2) — the accuracy sacrifice is often smaller than assumed, and a faithful intrinsic explanation beats an approximate post-hoc one, especially for high-stakes decisions. Don't reach for a black box plus explanation when a transparent model would do.
- **When you must use a black box, SHAP is the strong default** (post 5), complemented by counterfactuals for recourse (post 6) and the right method for your data/audience — always held as fallible approximations.
- **Hold explanations with skepticism** — they're approximations, not truth; they describe the model, not the world (not causal); plausible isn't correct; and they can be gamed or used as cover. Validate them.
- **Honesty about limits is part of the discipline** — for the deepest models (LLMs, post 7), we often *can't* fully explain behavior yet, and acknowledging that is more responsible than a false explanation.

The deepest takeaway is a posture: interpretability is the practice of *trying to understand models while staying honest about how much we actually do.* It gives real, essential tools for opening black boxes — but those tools produce approximations that must be read critically, never confused with causation, and never used to manufacture confidence. Used that way, interpretability makes AI more trustworthy, debuggable, fair, and accountable. Used naively — explanations trusted as truth, attributions read as causes, "we explained it" as a certificate — it creates exactly the false confidence that makes opaque AI dangerous. The skill, and the point of the series, is the former: understanding models *and* understanding the limits of that understanding.

The throughline: interpretability's hardest skill isn't knowing the tools but **using them wisely** — **match the method to the need** (tabular → SHAP/permutation/intrinsic; images → saliency-with-skepticism; text/LLMs → probing/attention-as-suggestive/partial-mechanistic; global → importance/SHAP-summaries; local → SHAP/LIME; recourse → counterfactuals; trust → example-based; and by audience — engineers/attributions, individuals/counterfactuals, experts/examples, regulators/documentation), preferring the strongest feasible option and using **several methods** (agreement reassures, disagreement warns). The dominant danger is **confident wrongness**, via traps: **explanations are approximations not truth**, **explanation is not causation** (the costliest — using attributions as causal levers), **plausible ≠ correct** (confirmation bias), explanations can be **gamed**, and **interpretability-washing** (explanation as cover). The defense is **skepticism and validation** (stability, cross-method agreement, probing, genuine interrogation). Bottom line: interpretability is **essential**, **prefer interpretable models**, **SHAP + counterfactuals** for black boxes, hold all explanations **skeptically and non-causally**, and be **honest about limits** (frontier LLMs often can't be fully explained) — understanding models *and* the limits of that understanding.

## Key takeaways

- There's **no universally best method** — match to **model/data** (tabular → **SHAP**/TreeSHAP + permutation importance, or **intrinsic**; images → saliency *with skepticism*; text/LLMs → probing, attention-as-suggestive, partial mechanistic), **level/question** (global → importance/SHAP summaries; local → SHAP/LIME; recourse → **counterfactuals**; trust → example-based), and **audience** (engineers→attributions, affected people→counterfactuals, experts→examples, regulators→documentation); use **several methods** (agreement reassures, disagreement warns).
- Interpretability's failure mode is **confident wrongness**. Traps: **explanations are approximations not truth** (post-hoc methods are models-of-the-model, can be unfaithful — LIME unstable, saliency misleading, SHAP faithfully explains flaws); **explanation ≠ causation** (the costliest — "important/high-SHAP" means the *model uses* it, not that it *causes* the outcome or that changing it helps); **plausible ≠ correct** (confirmation bias); explanations can be **gamed** (adversarially innocent-looking); and **interpretability-washing** (explanation as cover for shipping a bad model).
- The defense is **skepticism + validation**: check **stability** (rerun), **cross-method agreement**, whether it survives probing (not just matches priors), and whether it's used to *interrogate* or *rubber-stamp* — unskeptical interpretability is **worse than none** (manufactures unjustified confidence).
- Working wisdom: interpretability is **essential** (trust/debug/fairness/accountability/regulation, increasingly legal); **prefer interpretable models** (post 2 — small accuracy cost, faithful explanations, especially high-stakes); for black boxes, **SHAP is the strong default** + counterfactuals for recourse; hold explanations as **fallible, non-causal approximations**; and be **honest about limits** (frontier LLMs often can't be fully explained — post 7).
- The posture, and the point of the series: **understand models while staying honest about how much you actually do** — real tools for opening black boxes whose outputs must be read critically, never confused with causation, never used to manufacture confidence.

## Further reading

- [Explainable artificial intelligence — practice, methods, and limitations](https://en.wikipedia.org/wiki/Explainable_artificial_intelligence)
- [Right to explanation — the regulatory driver for interpretability](https://en.wikipedia.org/wiki/Right_to_explanation)
