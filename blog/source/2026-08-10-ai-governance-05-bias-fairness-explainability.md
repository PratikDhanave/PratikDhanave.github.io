# Bias, Fairness, and Explainability

*The three trustworthy-AI properties regulators and users press on hardest — where bias enters a system, why the fairness definitions contradict each other so you must choose one deliberately, and why an explanation you can read is not the same as an explanation you can trust.*

---

Ask a room of engineers whether their model is "fair" and "explainable" and most will nod. Ask them *which* fairness definition they picked, and *why*, and *what an explanation would have to prove to count as evidence in an audit* — and the room goes quiet. That gap is where governance lives. Fairness and explainability are not features you switch on; they are contested, sociotechnical commitments where the hard part is deciding what you owe, to whom, and how you would ever check.

This post walks the two properties end to end for classical models and for LLMs, names the traps that make well-meaning teams ship harm anyway, and closes with a small disaggregated evaluation you can wire into a release gate — the same signal that feeds continuous monitoring in the next post of this series.

---

## Where bias enters — it is rarely the algorithm

The word "bias" gets used loosely. In governance it means *systematic* skew that disadvantages a group in a way you would not endorse if you saw it stated plainly. It almost never originates in the learning algorithm itself. It arrives through the data pipeline and the choices around it:

- **Sampling bias.** The training data does not reflect the population the model will serve. A dermatology classifier trained mostly on light skin performs worse on dark skin — not because the model is malicious, but because it never saw enough examples.
- **Label bias.** The labels encode historical human decisions that were themselves skewed. "Was this loan repaid?" is a clean label; "was this candidate a good hire?" is a proxy for a manager's past judgments, and those judgments carried bias forward.
- **Proxy features.** You drop the protected attribute (race, gender) to be "fair," but ZIP code, first name, or shopping history correlate with it and reconstruct it. Removing the sensitive column does not remove the information — this is why *fairness through unawareness* fails.
- **Feedback loops.** The model's own predictions shape the data it learns from next. A predictive-policing model sends patrols where it predicted crime; those patrols record more incidents there; the next model sees "confirmation" and doubles down. The loop manufactures its own evidence.

**The gotcha:** deleting the protected attribute does not make a model fair — it makes bias *harder to measure* while proxies quietly carry it. You often need the sensitive attribute *in your evaluation set* precisely so you can check for disparities, even if the model never trains on it. "We don't collect race, so we can't be biased" is a governance red flag, not a defense.

---

## Fairness notions — and why you cannot have them all

There is no single "fair." There is a family of formal definitions, and they encode genuinely different moral intuitions. The two broad camps:

**Group fairness** asks that some statistic be equal *across groups*. The common notions:

- **Demographic parity** (a.k.a. statistical parity): the positive-prediction rate is equal across groups. Same fraction of each group gets approved, full stop — regardless of the underlying base rate.
- **Equal opportunity**: the true-positive rate is equal across groups. Among people who *should* get a positive outcome, each group is equally likely to actually get it.
- **Equalized odds**: both true-positive *and* false-positive rates are equal across groups — a stricter condition than equal opportunity.

**Individual fairness** takes a different stance: similar individuals should receive similar predictions, where "similar" is defined by a task-appropriate distance metric. It sidesteps group averages but pushes the hard problem into defining that metric — who decides which two applicants are "similar"?

Here is the part teams underestimate: **these definitions are mathematically incompatible.** When base rates differ between groups and your classifier is not perfect, you *cannot* simultaneously equalize false-positive rates, equalize false-negative rates, and have calibrated scores across groups. This is not an engineering limitation you can out-optimize; it is an impossibility result, made precise by Kleinberg, Mullainathan, and Raghavan and, in the criminal-justice setting, by Chouldechova. The famous COMPAS recidivism debate was two parties each correct under a *different* fairness definition, talking past each other.

**The gotcha:** fairness definitions are mutually exclusive in realistic settings — you must **choose** the notion that fits the context, with stakeholders, and defend the choice. There is no universally correct metric to compute your way to. A lender worried about denying creditworthy applicants leans toward equal opportunity; a screening tool where a false accusation is catastrophic weights false-positive parity. Pick deliberately, write down why, and accept the tradeoff you are declining.

---

## Fairness metrics and mitigation stages

Once you have chosen a notion, you measure the gap. Two open-source libraries dominate in Python:

- **Fairlearn** (Microsoft) centers on a `MetricFrame` abstraction that computes any metric disaggregated by a sensitive feature, plus reduction-based mitigation algorithms and post-processing. It leans toward group-fairness metrics and a clean sklearn-style API.
- **AIF360** (AI Fairness 360, from IBM Research) is a broader toolkit — dozens of fairness metrics and mitigation algorithms spanning all three stages below, with its own dataset abstractions.

Both move fast, so treat any specific class or argument name here as a pointer, not gospel — check the current docs before you copy a signature. Conceptually, mitigation happens at one of three stages:

- **Pre-processing** — transform the *training data* to remove bias before the model sees it (reweighting samples, learning fair representations). Model-agnostic, but you are editing data, which has its own governance questions.
- **In-processing** — change the *training objective* so the optimizer trades off accuracy against a fairness constraint directly. Often the most effective, but it couples fairness into the model and requires retraining to adjust.
- **Post-processing** — adjust the *trained model's outputs* (e.g., group-specific decision thresholds) to equalize a chosen metric. Cheapest to deploy on an existing model, but using group-specific thresholds is itself a policy choice that may be legally fraught in some domains.

**The gotcha:** debiasing is a balloon — squeeze one metric and another bulges. Improving demographic parity can degrade equalized odds *and* accuracy at once. Every mitigation is a move along a tradeoff surface, not a strict improvement. Measure *all* the metrics you care about before and after, and get sign-off on the net position — never report only the number that got better.

---

## Fairness for LLMs — the harms change shape

Classical fairness assumes a clear outcome (approved / denied) and defined groups. LLMs break both assumptions, and the harms mutate accordingly:

- **Representational harms.** The model demeans or erases a group — defaulting "doctor" to male pronouns, producing degrading associations, or simply having little to say about a culture it saw rarely in training.
- **Stereotyping.** Completions reproduce societal stereotypes ("the nurse... she", "the engineer... he") even when nothing in the prompt invited it.
- **Disparate quality of service.** The model is fluent and accurate in high-resource languages and noticeably worse in others — same for dialects (e.g., regional English varieties), which get more refusals, more errors, or a flattened, less helpful voice.

You test these the way you test any LLM property that averages hide: with **curated probe sets** and **disaggregated evaluation**. Build (or adopt) probe prompts that hold the task constant while varying only the group signal — a name, a dialect, a language — and compare quality *per slice*. This ties directly to the evaluation discipline from post 4 of this series: you are not asking "is the model good?" but "is it good *for each group I serve?*"

**The gotcha:** an aggregate quality score is where subgroup harm goes to hide. A model at 92% overall can be 96% for one group and 71% for another, and the headline number will never tell you. Always evaluate **disaggregated** — the average is the enemy of fairness measurement.

---

## Explainability — why governance needs it

Explainability (often XAI, explainable AI) matters to governance for reasons beyond curiosity:

- **Contestability.** A person affected by a decision has to be able to challenge it. "The model said no" is not a reason they can argue against.
- **Debugging and assurance.** Engineers need to know *why* a model decided as it did to catch a model keying off a spurious feature (the classic snow-in-the-background husky detector).
- **Regulatory expectation.** Frameworks and laws increasingly expect meaningful information about automated decisions — the GDPR's provisions on automated decision-making are the most cited, and sectoral rules in credit and employment demand adverse-action reasons.

Explanations come in two granularities. **Global** explanations describe the model's overall behavior — which features matter most across all predictions. **Local** explanations justify a *single* prediction — why *this* application was denied. Contestability needs local; debugging often needs both.

---

## Feature attribution for classical models — SHAP and LIME

For tabular and other classical models, two techniques anchor the field:

- **SHAP** (SHapley Additive exPlanations) assigns each feature a contribution to a specific prediction using Shapley values from cooperative game theory — the payoff of "which features, in coalition, moved the prediction from the baseline to this output." Its appeal is a solid theoretical grounding and additivity: the per-feature contributions sum to the gap between the prediction and the baseline. Exact Shapley values are exponential to compute, so the library ships specialized estimators (e.g., a fast path for tree ensembles and sampling-based approximations for general models). It supports both local attributions and aggregated global views.
- **LIME** (Local Interpretable Model-agnostic Explanations) explains one prediction by perturbing the input, seeing how the black-box output changes, and fitting a simple interpretable model (like sparse linear regression) in that local neighborhood. It is model-agnostic and intuitive, but the explanation depends on how you sample perturbations and can be unstable across runs.

```python
# Sketch of the SHAP local-explanation shape. Check current shap docs
# for the exact explainer class and call signature for your model type.
import shap

explainer = shap.Explainer(model, background_data)   # pick the right explainer per model
shap_values = explainer(instance)                     # per-feature contributions for one row
# shap_values.values -> contribution of each feature; sums to (prediction - baseline)
```

**The gotcha:** attribution methods are approximations of the model, not ground truth. SHAP and LIME can *disagree* on the same prediction, and both can be sensitive to their configuration (the background/reference distribution for SHAP, the perturbation sampling for LIME). A single attribution is a hypothesis to investigate, not a verdict to quote — and be aware that these explanations can themselves be gamed by an adversarial model.

---

## Explainability for LLMs — the honest, uncomfortable part

Here is where you must resist a comforting story. When an LLM gives you a chain-of-thought or says "I recommended this because...", that text is **a plausible narrative, not a faithful account of the computation.** Research on unfaithful reasoning shows models will produce confident rationales that do not match the factors that actually drove the output — a model can be steered by a bias in the prompt and then write a rationalization that never mentions it. Attention weights are similarly unreliable as explanations: what a layer attends to is not the same as what caused the answer.

So what *can* you use for LLM governance?

- **Input attribution.** Techniques that trace which input tokens most influenced an output (gradient- or perturbation-based) are more grounded than asking the model to explain itself, though still approximate.
- **Behavioral evaluation.** Instead of explaining one output, characterize behavior across many — the disaggregated probe evals above are your strongest evidence about *what the system actually does*.
- **Documentation.** Model cards, data statements, and system cards record intended use, training data provenance, known limitations, and eval results. For governance this is often the most durable "explanation": a written, reviewable account of what the system is and is not for.

**The gotcha:** never present an LLM's own chain-of-thought or self-explanation as audit evidence. It reads like a causal account and is not one. If a reviewer needs to know why the system behaves a certain way, point them to evals, input-attribution studies, and documentation — not to the model's own words about itself.

---

## A disaggregated evaluation gate

Concretely, the single most valuable fairness artifact for an engineering team is a **disaggregated evaluation** that computes a quality metric per subgroup and fails the build when the gap exceeds a threshold you agreed on. It works for a classifier's accuracy, an LLM's answer-correctness, refusal rate — any per-example quality score. Below is a small, dependency-free version; in practice you would compute per-group metrics with Fairlearn's `MetricFrame` and feed the same gap check.

```python
from dataclasses import dataclass
from statistics import mean


@dataclass
class Eval:
    group: str      # the subgroup label, e.g. language or dialect
    correct: bool   # was this example judged correct / acceptable?


def disaggregated_report(results, max_gap=0.05, min_group_n=30):
    """Per-group quality plus a fairness-gap check.

    Returns (report, passed). `passed` is False if any adequately-sized
    group's score trails the best group by more than `max_gap`.
    """
    groups = sorted({r.group for r in results})
    scores, sizes = {}, {}
    for g in groups:
        rows = [r for r in results if r.group == g]
        sizes[g] = len(rows)
        scores[g] = mean(1.0 if r.correct else 0.0 for r in rows)

    # Only judge groups with enough samples to be meaningful.
    scored = {g: scores[g] for g in groups if sizes[g] >= min_group_n}
    small = [g for g in groups if sizes[g] < min_group_n]

    if not scored:
        return {"error": "no group meets min_group_n", "sizes": sizes}, False

    best = max(scored.values())
    gaps = {g: round(best - s, 4) for g, s in scored.items()}
    worst_gap = max(gaps.values())
    passed = worst_gap <= max_gap

    report = {
        "overall": round(mean(1.0 if r.correct else 0.0 for r in results), 4),
        "per_group": {g: round(scored[g], 4) for g in scored},
        "gaps": gaps,
        "worst_gap": round(worst_gap, 4),
        "underpowered_groups": small,   # too few samples to trust — flag, don't pass silently
    }
    return report, passed


results = [
    *[Eval("en", True) for _ in range(46)], *[Eval("en", False) for _ in range(4)],
    *[Eval("hi", True) for _ in range(33)], *[Eval("hi", False) for _ in range(9)],
    *[Eval("sw", True) for _ in range(20)], *[Eval("sw", False) for _ in range(15)],
]

report, passed = disaggregated_report(results)
print(report)
print("GATE:", "PASS" if passed else "FAIL")
```

```text
{'overall': 0.7826, 'per_group': {'en': 0.92, 'hi': 0.7857, 'sw': 0.5714},
 'gaps': {'en': 0.0, 'hi': 0.1343, 'sw': 0.3486}, 'worst_gap': 0.3486,
 'underpowered_groups': []}
GATE: FAIL
```

Notice what the overall 0.78 concealed: Swahili sits at 0.57, a 0.35 gap the aggregate would have waved through. Two design choices matter. First, the gate reports the gap it *cannot* judge — `underpowered_groups` — instead of quietly passing groups with too few samples; "we didn't have enough data to check" is a finding, not a pass. Second, `max_gap` is a *policy* value, chosen with stakeholders for this context, not a universal constant. This is the honest shape of a fairness gate: it makes a chosen tradeoff visible and blocks a release that violates it, and it emits exactly the per-slice signal that continuous monitoring (next post) watches for drift over time.

---

## Key takeaways

- **Bias enters through data, labels, proxies, and feedback loops** — almost never the algorithm alone. Dropping the protected attribute hides bias rather than removing it; keep it in your *eval* set to measure disparities.
- **Fairness notions conflict by mathematical necessity.** Group fairness (demographic parity, equal opportunity, equalized odds) and individual fairness cannot all hold at once when base rates differ. Choose the notion with stakeholders and defend the tradeoff you decline.
- **Mitigate at one of three stages** — pre-, in-, or post-processing — and remember that improving one metric can worsen another and utility. Measure the whole tradeoff surface, not the number that improved.
- **For LLMs, harms become representational and disparate-quality.** Test with curated probes and disaggregated evals; the aggregate score is where subgroup harm hides.
- **Explainability serves contestability, debugging, and regulation.** SHAP and LIME give local/global attributions for classical models but are approximations that can disagree.
- **LLM self-explanations are narratives, not faithful causal accounts.** Do not use chain-of-thought as audit evidence; rely on input attribution, behavioral evals, and documentation.
- **Fairness is a sociotechnical choice, not a single number.** A disaggregated gate makes that choice explicit and enforceable.

---

## Further reading

- [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) and its companion [Towards a Standard for Identifying and Managing Bias in Artificial Intelligence (NIST SP 1270)](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.1270.pdf)
- [Fairlearn documentation](https://fairlearn.org/) — `MetricFrame`, fairness metrics, and mitigation algorithms
- [AI Fairness 360 (AIF360) documentation](https://aif360.readthedocs.io/) — metrics and mitigation across all three stages
- [SHAP documentation](https://shap.readthedocs.io/) and the paper, Lundberg & Lee, ["A Unified Approach to Interpreting Model Predictions" (2017)](https://arxiv.org/abs/1705.07874)
- [LIME repository](https://github.com/marcotcr/lime) and the paper, Ribeiro, Singh & Guestrin, ["Why Should I Trust You?": Explaining the Predictions of Any Classifier (2016)](https://arxiv.org/abs/1602.04938)
- Kleinberg, Mullainathan & Raghavan, ["Inherent Trade-Offs in the Fair Determination of Risk Scores" (2016)](https://arxiv.org/abs/1609.05807) — the fairness impossibility result
- Chouldechova, ["Fair prediction with disparate impact" (2017)](https://arxiv.org/abs/1703.00056) — impossibility in the recidivism setting
- Turpin et al., ["Language Models Don't Always Say What They Think: Unfaithful Explanations in Chain-of-Thought Prompting" (2023)](https://arxiv.org/abs/2305.04388) — why LLM rationales aren't faithful explanations
