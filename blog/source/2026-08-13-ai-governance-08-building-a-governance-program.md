# Building an AI Governance Program

*The capstone of this series — assembling roles, a use-case inventory, lifecycle gates, and policy-as-code into a right-sized governance program that produces evidence instead of paperwork, without crushing the velocity of a two-person team or failing an enterprise audit.*

---

Across this series I have argued for one idea from seven angles: governance is not a document you file, it is a set of controls that produce *evidence*. A model card is evidence. A passing eval gate is evidence. A drift alert with a runbook is evidence. Each of the previous posts built one of those controls in isolation. This finale is about the wiring — how the pieces become a *program* that a real engineering organization can run, and how to keep that program honest, proportionate, and out of the way.

A program is not more controls. It is the connective tissue: who is accountable, what you are governing, when each control fires, and how the checks run themselves so they don't depend on someone remembering. Get that wiring wrong in one of two directions and the program dies — either it collapses into governance theater (paperwork that generates the *look* of safety without the substance), or it becomes an enterprise bureaucracy bolted onto a team that ships weekly, and the team routes around it. The whole art is right-sizing.

Let me assemble the program from four load-bearing parts: **accountability**, **the inventory**, **lifecycle gates**, and **policy-as-code** — then close by tracing the arc of the whole series.

---

## Roles and accountability: the GOVERN function, made concrete

The NIST AI Risk Management Framework puts GOVERN at the center of its four functions for a reason — MAP, MEASURE, and MANAGE all assume someone is accountable for acting on what they surface. GOVERN is the culture, the roles, and the lines of accountability that make the other three mean something. Post 2 in this series unpacked the four functions; here I turn GOVERN into an org chart you could actually staff.

A working AI governance program needs a small number of clear roles, not a new department:

- **Use-case owner (usually the product owner).** Accountable end to end for one AI use case: its business justification, its risk tier, and the fact that its governance artifacts exist and stay current. There is exactly one per use case. This is the single most important role — most governance failures are ownership failures wearing a technical costume.
- **Engineering lead.** Responsible for building the controls — the eval gate, the monitors, the model-card generation — and keeping them green. Owns the *mechanism*.
- **Data / ML lead.** Accountable for training data provenance, dataset documentation, and the fairness analysis (the subject of post 5).
- **Legal / risk / compliance.** Maps use cases to external obligations — the EU AI Act risk category, sector rules, contractual commitments — and consulted whenever a use case's risk tier is set or changed.
- **AI review board.** A small cross-functional group (product, engineering, data, legal, and a security representative) that meets on a cadence to approve high-risk use cases, adjudicate tier disputes, and own the policy thresholds. Not a rubber stamp and not a standing committee that reviews everything — it exists for the decisions that a single owner should not make alone.

The cleanest way to write this down is a high-level RACI — who is **R**esponsible, **A**ccountable, **C**onsulted, and **I**nformed for each governance activity. Keep it to one page:

| Activity | Use-case owner | Eng lead | Data/ML lead | Legal/Risk | Review board |
|---|---|---|---|---|---|
| Register use case & set risk tier | A | C | C | C | I |
| Build eval gate & monitors | C | A | R | I | I |
| Author model card & datasheet | A | R | R | C | I |
| Fairness / bias analysis | C | C | A | C | I |
| Approve high-risk deploy | R | C | C | C | A |
| Periodic review / retire | A | R | C | C | I |

**The gotcha:** every activity needs exactly one **A**. When two people are accountable for the same control, nobody is — the classic failure mode is "the ML team assumed product owned the model card, product assumed ML did," and the card never gets written. A RACI with two A's in a row, or an activity with none, is not a documentation nit; it is a live governance hole. Resolve it on paper before it becomes an incident.

---

## The use-case inventory: you cannot govern what you have not catalogued

Everything else in the program hangs off one artifact: a central inventory of every AI use case in the organization. Not every model — every *use case*, because the same base model powering an internal summarizer and a customer-facing credit assistant carries wildly different risk. The inventory is the backbone. Without it you have no denominator, no way to know what "all our AI" even is, and therefore no way to prove any control covers everything.

The inventory answers, for each use case: who owns it, what risk tier it sits in, which model and version it runs, where its documentation lives, whether it has a passing eval, and whether it is monitored in production. That is the minimum record that lets you *ask* the governance questions at all.

```yaml
# registry/use-cases/support-copilot.yaml
id: uc-042
name: "Customer support copilot"
owner: priya.n@example.com          # exactly one accountable human
status: production                   # intake | design | approved | production | retired
risk_tier: high                     # low | limited | high  (EU AI Act-aligned)
description: "Drafts support replies grounded in the KB; agent edits before send."
model:
  provider: internal-gateway
  base_model: "gpt-x-2026-07-01"     # pinned; version bumps re-open the gate
  version: "3.2.0"
documentation:
  model_card: docs/cards/support-copilot-v3.2.md   # post 3
  datasheet: docs/datasheets/kb-corpus-v7.md
governance:
  eval:
    gate: evalset/v7                 # post 4 — the versioned eval set
    last_run: "2026-08-11"
    passed: true
  fairness_reviewed: true            # post 5
  monitors:                          # post 6
    - drift.faithfulness
    - safety.refusal_rate
  human_in_the_loop: true
regulatory:
  eu_ai_act_category: high-risk
  last_review: "2026-08-01"
  next_review: "2026-11-01"          # high tier => quarterly
```

**The gotcha:** the danger is not the use cases in the registry — it is the ones that are not. Every team spinning up an LLM feature without an entry is *shadow AI*: ungoverned, uncounted, and invisible until it causes the incident. The registry is therefore step one of the whole program, and its real control is not the schema — it is the rule that **no AI use case reaches production without an entry**. Enforce that rule at the pipeline, not in a policy wiki, and the inventory stays complete on its own.

---

## Lifecycle gates: governance that fires at the right moments

The inventory is a snapshot; the lifecycle is the film. A use case moves through predictable stages, and the program attaches a lightweight check to each transition. This is where the earlier posts' controls slot in as gates rather than good intentions.

```text
intake / risk-triage  →  design review  →  pre-deploy eval gate  →  approval (by tier)  →  monitored production  →  periodic review / retire
   (register + tier)      (map risks,       (post 4: eval must      (low: owner sign-off;   (post 6: monitors +      (re-run eval; confirm
                           choose controls)   pass thresholds)        high: review board)      drift tripwires live)    still needed; retire)
```

Read left to right:

- **Intake / risk-triage.** A new use case gets a registry entry and a risk tier. The tier — I lean on the EU AI Act's shape of unacceptable / high / limited / minimal — sets how much rigor everything downstream demands. This is the single decision with the most leverage: over-tier and you drown a trivial feature in review; under-tier and a high-risk system skips the checks that matter.
- **Design review.** Map the risks (post 2's MAP function) and pick the controls that answer them. A limited-risk internal tool may need only a model card; a high-risk external one needs fairness analysis, human-in-the-loop, and monitors.
- **Pre-deploy eval gate.** The versioned eval set from post 4 must pass its thresholds. This gate is automated and non-negotiable — a failing eval blocks the deploy the way a failing unit test blocks a merge.
- **Approval by tier.** Here is where rigor scales with risk. A low-risk change ships on a green pipeline and the owner's sign-off. A high-risk change additionally needs the review board — a named human gating a *category* of decision that automation should not make alone.
- **Monitored production.** Post 6's monitors go live: drift tripwires, safety-rate alarms, and a runbook that says who does what when one fires.
- **Periodic review / retire.** Tier sets the cadence — high-risk quarterly, limited annually. Review re-runs the eval, confirms the use case is still needed, and retires it if not. Retirement is a governance act too: a decommissioned model still in the registry with `status: retired` is evidence you turned it off deliberately.

**The gotcha:** an enterprise-weight process on a two-person team kills velocity, and a startup-weight process at an enterprise fails the audit — so the gate's *weight* must scale with the tier, not the calendar. The mistake is a one-size process where every use case, trivial or critical, walks the same seven approvals. Make the low-risk path nearly frictionless (register, pass eval, ship) so the heavy path is credible when it matters. A process that treats a spell-checker like a loan-approval model teaches everyone to treat the loan-approval model like a spell-checker.

---

## Policy-as-code: a gate that runs is a control, a wiki page is a hope

The difference between a governance program that holds and one that erodes is whether its rules *execute*. A policy document that says "every high-risk use case must have a passing eval and an assigned owner" is a hope — it depends on humans remembering and choosing to comply under deadline. The same policy encoded as a CI check that reads the registry and fails the build is a control. It runs every time, it can't be forgotten, and its result is itself evidence.

Here is a compact policy-as-code gate. It reads a use case's registry entry and refuses to let it deploy if any required governance artifact is missing — scaling the requirements by risk tier so a low-risk tool isn't held to a high-risk bar.

```python
"""Governance gate: block deploy if a use case is missing required
governance artifacts. Requirements scale with the declared risk tier."""
from __future__ import annotations
import sys, datetime as dt
from pathlib import Path
import yaml   # pip install pyyaml

# What each risk tier must have present and true before it can ship.
# This mapping IS the policy — it lives in version control and changes
# only through review, never quietly to make a red build go green.
REQUIRED_BY_TIER = {
    "low":     ["owner", "risk_tier"],
    "limited": ["owner", "risk_tier", "model_card", "eval_pass"],
    "high":    ["owner", "risk_tier", "model_card", "eval_pass",
                "fairness_reviewed", "monitors", "human_in_the_loop",
                "review_current"],
}


def _present(uc: dict, requirement: str) -> bool:
    """Resolve one requirement against a registry entry to a boolean."""
    if requirement == "owner":
        return bool(uc.get("owner"))
    if requirement == "risk_tier":
        return uc.get("risk_tier") in REQUIRED_BY_TIER
    if requirement == "model_card":
        card = uc.get("documentation", {}).get("model_card")
        return bool(card) and Path(card).exists()      # must exist on disk
    if requirement == "eval_pass":
        return uc.get("governance", {}).get("eval", {}).get("passed") is True
    if requirement == "fairness_reviewed":
        return uc.get("governance", {}).get("fairness_reviewed") is True
    if requirement == "monitors":
        return len(uc.get("governance", {}).get("monitors", [])) > 0
    if requirement == "human_in_the_loop":
        return uc.get("governance", {}).get("human_in_the_loop") is True
    if requirement == "review_current":
        nxt = uc.get("regulatory", {}).get("next_review")
        return bool(nxt) and dt.date.fromisoformat(str(nxt)) >= dt.date.today()
    return False


def check(uc: dict) -> list[str]:
    """Return the list of unmet requirements for this use case."""
    tier = uc.get("risk_tier", "high")   # unknown tier => strictest, fail-safe
    required = REQUIRED_BY_TIER.get(tier, REQUIRED_BY_TIER["high"])
    return [r for r in required if not _present(uc, r)]


def main(path: str) -> int:
    uc = yaml.safe_load(Path(path).read_text())
    missing = check(uc)
    label = f'{uc.get("id", "?")} "{uc.get("name", "?")}" [{uc.get("risk_tier")}]'
    if missing:
        print(f"[FAIL] {label} missing: {', '.join(missing)}", file=sys.stderr)
        return 1                        # non-zero exit blocks the deploy
    print(f"[PASS] {label} — all required governance artifacts present")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
```

Wiring it into CI is ordinary — and the same script can sweep the whole registry so a use case can't quietly fall out of compliance after it ships:

```yaml
# .github/workflows/governance-gate.yml (excerpt)
- name: Governance gate for changed use case
  run: python governance_gate.py registry/use-cases/${{ inputs.use_case }}.yaml
- name: Nightly sweep of the whole registry
  run: |                                # fail if ANY entry drifts out of policy
    fail=0
    for f in registry/use-cases/*.yaml; do python governance_gate.py "$f" || fail=1; done
    exit $fail
```

Note what the tier does: a `low` use case needs only an owner and a tier, so the gate is nearly free; a `high` one must additionally carry a model card that exists on disk, a passing eval, a fairness review, live monitors, human-in-the-loop, and a review that hasn't lapsed. The `review_current` check is what turns periodic review from a calendar reminder into an enforced control — let the next-review date slip past today and the nightly sweep goes red.

**The gotcha:** policy-as-code beats policy-as-PDF, but only if the code checks something real. A gate that confirms a `model_card:` *field* is filled in — without confirming the file exists, is current, and matches the deployed version — is theater with a green checkmark, which is more dangerous than no check because it manufactures false assurance. Tie every check to the artifact it stands for: `model_card` resolves a path and asserts the file is on disk; `eval_pass` reads the actual last-run result; `review_current` compares against today. A control that can pass while the thing it guards is absent is not a control.

---

## Right-sizing: theater is worse than nothing

The two failure modes bracket the whole design. Governance theater — controls that generate documents but not safety — is worse than no governance, because it consumes effort and buys false confidence; the sign-off gets signed, the checkbox gets checked, and nothing is safer. At the other extreme, an enterprise process transplanted onto a small team doesn't make it safe, it makes the team invent a shadow process off to the side.

Right-sizing is not a compromise between the two; it is the actual skill. A practical calibration:

- **A two-to-ten-person startup** needs the registry (even as a folder of YAML), one accountable owner per use case, an automated eval gate, and basic monitoring. That is a complete program at that scale. No review board — the founder *is* the board. No quarterly paperwork on a minimal-risk feature.
- **An enterprise** needs the same backbone plus the review board, tiered approval, formal fairness sign-off, an audit trail, and mapping to external obligations (EU AI Act conformity, ISO/IEC 42001 management-system requirements). The controls are the same shape; there are simply more of them and they are witnessed.

The invariant across both: **every control traces to a real risk.** If you cannot name the harm a control prevents, delete it. That single test — *what goes wrong if this control is absent?* — is the sharpest instrument you have against theater, and it works at any company size.

---

## The arc of the series

Step back and the seven prior posts form one argument:

1. **What governance is** — the discipline of ensuring AI systems are safe, fair, accountable, and compliant across their lifecycle; distinct from security and compliance, and already partly yours as an engineer.
2. **The NIST AI RMF** — GOVERN, MAP, MEASURE, MANAGE as a runnable operating model, anchored by a versioned risk register.
3. **Model cards and documentation** — the evidence layer that turns "trust us" into an auditable paper trail.
4. **Evaluation and quality gates** — MEASURE made real: a versioned eval set and a CI gate that fails on regression.
5. **Bias, fairness, and explainability** — measuring disparate treatment and making decisions inspectable.
6. **Monitoring in production** — drift and safety tripwires that compare live behavior against the eval baseline.
7. **AI regulation** — the EU AI Act, ISO/IEC 42001, and how external obligations map onto the controls above.
8. **This post** — wiring all of it into a program: accountability, inventory, lifecycle gates, and policy-as-code.

The throughline is a single sentence: **governance is the set of evidence-producing controls engineers build in, not paperwork bolted on.** Every artifact in this series — the risk register, the model card, the eval gate, the monitor, the registry, the policy-as-code check — exists to produce a durable, inspectable record that the system behaves as claimed. That is what a program *is*: not a binder, but the machinery that keeps generating proof while you ship.

---

## Key takeaways

- **A program is wiring, not more controls.** Accountability, an inventory, lifecycle gates, and policy-as-code turn isolated controls into something an org can run.
- **One accountable owner per use case, per activity.** A RACI with a lone **A** on every row is the antidote to the most common failure — ownership diffusion.
- **The inventory is the backbone.** You cannot govern uncatalogued AI; the registry, enforced at the pipeline, is what makes shadow AI impossible to hide.
- **Gates scale with risk tier, not the calendar.** Make the low-risk path frictionless so the heavy path stays credible where it counts.
- **Policy-as-code beats policy-as-PDF — if it checks something real.** A gate that passes while the artifact it guards is missing is theater with a green check.
- **Right-size relentlessly, and delete any control whose harm you can't name.** Theater is worse than nothing; enterprise weight on a small team just breeds a shadow process.

---

## Further reading

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — the GOVERN function and the four-function operating model that this program instantiates.
- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/) — suggested actions and roles for each function; the closest thing to an implementation guide from the primary source.
- [ISO/IEC 42001:2023 — AI management systems](https://www.iso.org/standard/81230.html) — the management-system standard an enterprise program maps to for certification.
- [EU AI Act — full text (EUR-Lex)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) — the risk-tier structure behind the intake triage and the high-risk obligations.
- [Google's Responsible AI practices](https://ai.google/responsibility/responsible-ai-practices/) — a reference for what a mature responsible-AI program covers end to end.
- [Evaluation and Quality Gates](/blog/posts/ai-governance-04-evaluation-and-quality-gates.html) — the eval gate this program treats as a required pre-deploy control.
- [Model Cards and Documentation](/blog/posts/ai-governance-03-model-cards-and-documentation.html) — the evidence artifact the policy-as-code gate checks for.
