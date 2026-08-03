# Explaining Credit Decisions: SHAP and Adverse-Action Reason Codes

*How lenders turn a model's raw probability into the specific, legally required reasons a declined applicant must receive.*

When a credit model declines an applicant, the lender does not get to say "the algorithm decided." In most consumer-lending regimes, a declined borrower is entitled to a concrete, honest explanation: the principal reasons the application fell short. That obligation predates machine learning by decades, but it collides awkwardly with modern gradient-boosted and neural scorers, which produce a single probability rather than a tidy list of causes. Explainability is the bridge. This post walks through how a per-applicant explanation is computed, how it becomes human-readable reason codes, and why a fairness check has to travel alongside it.

## Two questions, two kinds of explanation

It helps to separate two questions that people often blur together. The first is *global*: across all applicants, what does this model generally rely on? Income, credit utilization, delinquency history, length of file. Global explanations describe the model's overall behavior and are useful for governance, monitoring, and sanity-checking that the model has not latched onto something absurd.

The second question is *local*: for **this specific applicant**, why did the score land where it did? Two applicants can be declined by the same model for entirely different reasons — one for a thin credit file, another for a recent missed payment. A global summary cannot answer that. Adverse-action notices are inherently a local problem: you owe *this* person *their* reasons, not a description of the average customer.

SHAP (Shapley additive explanations) is popular precisely because it answers the local question with a property that regulators and auditors like: additivity.

## What a SHAP value actually measures

The underlying idea is borrowed from cooperative game theory. Imagine the features are players cooperating to move the prediction away from a baseline — typically the model's average output over some reference population. Each feature's SHAP value is its fair share of the credit (or blame) for the gap between that baseline and the applicant's actual score, averaged over every possible order in which features could be added to the coalition.

The practical payoff is an exact decomposition. For one applicant:

    baseline score + sum of all feature contributions = this applicant's score

Every contribution is *signed*. A positive value pushed the applicant toward approval; a negative value pushed toward decline (sign conventions vary, but the point is directionality). Because the pieces sum back to the exact prediction, nothing is hand-waved: you can point at "utilization cost you the most, recent delinquency was second" and the arithmetic backs you up. That auditability is what makes the method defensible when someone asks how a number was produced.

There are well-known variants. Tree-based estimators can compute contributions efficiently and exactly for tree ensembles; model-agnostic sampling estimators approximate them for anything else at higher cost. The choice affects runtime and precision, not the interpretation.

## From contributions to reason codes

A list of signed numbers is not a reason a person can act on. The next step is a deterministic transform: rank the contributions that pushed the applicant toward decline, take the top few, and map each responsible feature to a plain-language code such as "level of revolving debt too high" or "insufficient length of credit history."

That mapping is the piece teams most often underinvest in. A feature name like `util_ratio_l3m` is not a reason; the reason is the human sentence a compliance team has approved. The mapping table is a governed artifact — reviewed, versioned, and stable — because it is the actual text an applicant reads.

```text
   SOURCES            ATTRIBUTE          RANK          MAP            CONSUME
 +-----------+
 | applicant |----feature values--+
 |  record   |                    v
 +-----------+              +-------------+   signed    +---------+  top   +----------+   codes   +-----------+
 | scoring   |--prediction->|    SHAP     |--values--->|  rank   |------->| reason-  |---------->| adverse-  |
 |  model    |              | attribution |  (local)   | adverse |        | code map |           | action    |
 +-----------+              +-------------+            +---------+        +----------+           | notice    |
      |                                                                                          +-----------+
      | scored outcomes (population)
      v
 +-----------+                                                                    impact         +-----------+
 |  fairness |------------------------------------------------------------------- ratio -------->| fairness  |
 |  monitor  |                                                                                   |  report   |
 +-----------+                                                                                   +-----------+
```

> **▸ [Open the interactive diagram](/blog/diagrams/finai-credit-explainability-shap-reason-codes.html)** — one declined applicant flows into local SHAP attribution and out as reason codes, while population outcomes feed a parallel fairness report.

## The mechanics of ranking adverse contributions

Two subtleties decide whether reason codes are trustworthy. The first is the *reference point*. SHAP contributions are always relative to a baseline, and the baseline you pick changes the story. A common and defensible choice for adverse action is to explain the applicant against a population of approved or near-approved applicants, so the reasons read as "here is where you fell short of the people we accept" rather than a comparison against a meaningless global average. Whatever you choose, document it — the baseline is part of the explanation.

The second subtlety is *feature grouping*. Real models often carry several correlated features describing the same underlying concept — a few different views of debt load, say. If you rank raw features, an applicant's notice can list three near-duplicate reasons that are really one. Summing contributions within a concept group before ranking produces cleaner, non-redundant reason codes and better reflects what actually drove the decision.

Once contributions are grouped and ranked by how strongly they pushed toward decline, selecting the principal reasons is straightforward: take the top N adverse groups, look up their approved text, and assemble the notice. The count of reasons disclosed is a policy choice, not a modeling one.

## Fairness lives next to explanations

Explaining an individual decision is necessary but not sufficient. A model can be perfectly explainable and still produce discriminatory outcomes across protected groups. So the same pipeline that generates reason codes should feed a parallel process that watches outcomes in aggregate.

The workhorse metric is the *adverse-impact ratio* (often called the four-fifths or disparate-impact check). Conceptually: compute the approval rate for each group, divide the lower group's rate by the reference group's rate, and see how far the ratio falls below one. A ratio well under the customary 0.8 threshold is a flag — not automatic proof of illegal discrimination, but a signal that demands investigation and, often, justification that the disparity is driven by legitimate creditworthiness factors rather than a proxy for a protected attribute.

This matters because explanations and fairness answer different questions. Reason codes tell an individual why *they* were declined. The adverse-impact ratio tells the institution whether the model treats *groups* comparably. A responsible deployment produces both artifacts from every scoring run and keeps them for audit. Notice in the flow above that the two paths stay separate on purpose: the explanation path handles one applicant, the fairness path handles the population, and neither should be quietly folded into the other.

## Pitfalls and practical guardrails

A few things reliably cause trouble. Explanations computed against an ill-chosen or drifting baseline slowly stop matching reality — pin and monitor the reference set. Reason-code text that is technically accurate but incomprehensible defeats the purpose; write for the applicant, not the data scientist. Approximate SHAP estimators can be noisy for individual applicants, so verify that top-ranked reasons are stable under reasonable perturbation before you print them. And correlated features masquerading as independent reasons erode trust; group them.

Finally, treat the whole chain as a governed system. The model, the attribution method, the baseline, the grouping logic, the mapping table, and the fairness thresholds are all decisions that a regulator can ask you to defend. The value of SHAP here is not that it makes a complex model simple — it does not — but that it gives you a faithful, additive, per-applicant account you can rank, translate, and stand behind.

## Wrapping up

Turning a model score into a compliant credit decision is a small pipeline with big obligations: attribute locally, rank the adverse contributions, map them to approved language, and run the population through a fairness check in parallel. SHAP supplies the honest per-applicant decomposition; disciplined engineering around baselines, grouping, and governed text turns that decomposition into reason codes a person can actually understand — and an audit trail an institution can actually defend.
