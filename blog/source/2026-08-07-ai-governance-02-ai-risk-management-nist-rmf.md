# AI Risk Management with the NIST AI RMF

*Turning the four functions of the NIST AI Risk Management Framework — GOVERN, MAP, MEASURE, MANAGE — into something an engineering team can actually run: a risk taxonomy for LLM apps, a versioned risk register in code, and the eval hooks that keep MEASURE honest.*

---

Most teams meet AI risk management as a document. Someone in legal or compliance sends a spreadsheet, you fill in a column, and the file goes to sleep in a shared drive until the next audit. That artifact is not risk management — it is the fossil of a single conversation that happened once. The NIST AI Risk Management Framework (AI RMF 1.0) exists to fix exactly this failure mode: it describes risk management as a set of *continuous functions* your team performs, not a form you submit.

This post is for engineers. I am not going to recite the framework — you can read the source, and you should. Instead I want to make it concrete: what the four functions mean when you are the person shipping an LLM feature, a risk taxonomy that actually maps to how these systems break, and a small amount of Python and YAML that turns "we should manage AI risk" into a reviewable, versioned artifact that lives next to your code.

One framing note before we start. The AI RMF is **voluntary and flexible by design**. It is not a certification, it does not mandate specific controls, and it does not tell you your acceptable risk threshold — that is a business and legal decision. What it gives you is a shared vocabulary and a repeatable structure. When a hard obligation *does* land on you — the EU AI Act, a sector regulator, a customer's security questionnaire — a working RMF practice is what you map those obligations onto. We will come back to that.

---

## The four functions, in engineering terms

The framework is organized around four functions. The trap is reading them as a waterfall — MAP, then MEASURE, then MANAGE, with GOVERN as a preamble. They are not stages. They are concurrent, iterative activities that feed each other, and MEASURE routinely sends you back to MAP when it surfaces a risk you did not anticipate.

### GOVERN — the function that makes the other three stick

GOVERN is about culture, policies, roles, and accountability, and it cuts across everything else. It answers unglamorous questions: Who owns AI risk for this feature? What is our policy on using customer data in prompts? Who signs off before a model with a known bias profile ships? What happens when an incident is reported?

GOVERN is the function teams skip, and it is the reason the other three decay. You can run a beautiful risk assessment, but if no named human owns each risk and no cadence forces a review, MAP and MEASURE go stale and MANAGE never happens. GOVERN is what converts a one-time analysis into a standing practice.

Concretely, GOVERN for an engineering team looks like: a documented owner per AI use case, a written policy on data handling and acceptable use, a defined review cadence, and an incident path. None of that requires a governance committee — it requires a `CODEOWNERS`-style assignment and a recurring calendar entry.

### MAP — establish context before you measure anything

MAP is where you build the shared understanding of what you are actually deploying and why. Intended and *unintended* uses. Who the stakeholders are — not just users, but people affected by the output who never touch the product. What could go wrong, and who it lands on when it does.

The output of MAP is context, not numbers. A well-mapped use case can answer: What is this system for? What is explicitly out of scope? Who is harmed if it is wrong, biased, or abused? What is the impact if it fails silently versus loudly? You cannot MEASURE meaningfully until you have MAPped, because measurement without context is just collecting metrics nobody agreed matter.

### MEASURE — analyze, benchmark, and track with real metrics

MEASURE is quantifying the risks MAP identified. Accuracy, hallucination rate, refusal behavior, bias across cohorts, latency, cost, robustness to adversarial input — whatever the mapped risks demand. This is the function engineers are best equipped for and most tempted to shortcut.

**The gotcha:** MEASURE without an eval set is vibes. If your evidence that "the model is accurate enough" is a few prompts someone tried in a playground, you have not measured anything — you have anecdotes. Real MEASURE needs a benchmark: a fixed, versioned evaluation set with defined metrics you can re-run on every model or prompt change and compare over time. Building that eval harness is the subject of post 4 in this series; for now, treat MEASURE as a promissory note that points at concrete, repeatable evaluation, not a gut check.

### MANAGE — prioritize, mitigate, monitor, respond

MANAGE is acting on what you measured. You rank risks by how bad they are and how likely, decide which to mitigate now versus accept, implement the mitigations, monitor in production, and respond when something fires. This is where the risk register earns its keep — it is the ledger that records what you decided and why.

MANAGE is also where you close the loop back to GOVERN. A residual risk you decided to accept needs a named owner and an expiry date, or "we accept this for now" quietly becomes "we forgot about this forever."

**The gotcha:** the RMF is iterative, not a launch checklist. A risk assessment you do once, at launch, is stale the moment your model provider ships a new version, your prompt changes, a new jailbreak circulates, or your usage pattern shifts. Models are non-stationary and so is the threat landscape. The whole point of framing these as *functions* rather than *phases* is that you keep doing them. Bake the review cadence into GOVERN or the register rots.

---

## A risk taxonomy for LLM applications

MAP asks "what could go wrong?" and a blank page is a bad way to answer it. A taxonomy gives you a checklist to run every mapped use case against. NIST's Generative AI Profile (AI 600-1) catalogs risks that are amplified or newly introduced by generative systems; the categories below are my engineering-facing framing of the failure modes that actually show up in LLM apps. For each, the question to ask during MAP is "does this apply here, and how badly?"

- **Accuracy and hallucination** — the model states false things fluently and confidently. Highest stakes when output feeds a decision without a human check, or when users treat generated text as retrieved fact.
- **Bias and fairness** — outputs vary in quality or tone across demographic groups, or encode stereotypes. Shows up in ranking, screening, summarization of people, and anything touching protected attributes.
- **Privacy** — training-data memorization, leakage of data placed in the prompt or context window, or PII flowing into logs and provider-side retention. Cross-references the data-handling posture you set in GOVERN.
- **Security** — prompt injection, tool/agent abuse, data exfiltration through crafted inputs, and the classic application vulnerabilities that LLM features drag along. This deserves its own treatment; see my AI security series for the attack surface in depth, and treat those threats as first-class entries in this register rather than a separate silo.
- **Safety and harmful content** — generation of dangerous, illegal, or abusive content, or advice that causes real-world harm. Scales with how open-ended the interface is.
- **Robustness** — brittleness under distribution shift, adversarial or out-of-distribution inputs, and inconsistent answers to trivially reworded prompts. A model that is accurate on your test set and erratic in the wild has a robustness problem, not an accuracy one.
- **Transparency and explainability** — can you tell users they are talking to an AI, explain roughly how an output was produced, and disclose limitations? Often a compliance obligation, not just good manners.
- **Over-reliance and automation bias** — users trusting the system past its competence. This is a *design* risk: a confident UI with no uncertainty signal manufactures over-reliance even from an otherwise well-behaved model.
- **Environmental and cost** — inference has a real energy and dollar footprint. Cost is a risk when a feature is economically unsustainable at scale, or when a retry loop or agentic tool-call storm quietly 10x's spend.

You will not have all nine on every use case, and you should not pretend to. The value is running the list deliberately during MAP so that the risks you *omit* are omitted on purpose, with a note, rather than by oversight.

---

## Operationalizing it: a risk register that lives in the repo

Here is the shift that makes this real for engineers. Stop thinking of the risk register as a document and start thinking of it as **a versioned artifact in your repository**, reviewed like code. It goes in git, it changes through pull requests, its history is auditable, and stale entries are visible in `git blame`.

**The gotcha:** a risk register only helps if it is versioned and reviewed, not a dead doc. The single most common way AI risk management fails in practice is that the assessment exists but nobody looks at it again. Putting it in the repo — under the same review cadence as the code it describes — is the cheap structural fix. A YAML file that a PR must touch when you change the model is worth ten spreadsheets nobody opens.

Start with a schema. Here it is as YAML, one entry per mapped risk for a use case:

```yaml
# risk-register/support-summarizer.yaml
use_case:
  id: support-summarizer
  name: "Support ticket summarizer"
  intended_use: "Summarize customer support threads for agents"
  out_of_scope: "Not for automated replies or customer-facing output"
  owner: alice@example.com          # GOVERN: a named human, not a team alias
  review_cadence_days: 90
  last_reviewed: 2026-08-07
  schema_version: 1

risks:
  - id: SS-hallucination-01
    category: accuracy_hallucination
    description: "Summary invents ticket details not present in the thread"
    likelihood: likely          # rare | unlikely | possible | likely | almost_certain
    impact: moderate            # negligible | minor | moderate | major | severe
    mitigations:
      - "Constrain prompt to extract-only; forbid new facts"
      - "Show source spans alongside summary in the agent UI"
    measure_ref: eval/summarizer/faithfulness   # points at the MEASURE benchmark
    owner: alice@example.com
    status: mitigating          # open | mitigating | monitoring | accepted | closed
    review_by: 2026-11-05

  - id: SS-privacy-01
    category: privacy
    description: "PII from tickets retained in provider-side logs"
    likelihood: possible
    impact: major
    mitigations:
      - "Redact PII before the model call"
      - "Use zero-retention API tier; contractually confirmed"
    measure_ref: eval/summarizer/pii-leakage
    owner: bob@example.com
    status: monitoring
    review_by: 2026-11-05
```

Notice what the schema encodes. Every risk has an **owner** and a **review_by** date (GOVERN), a **category** from the taxonomy (MAP), a **measure_ref** pointing at the benchmark that quantifies it (MEASURE), and **mitigations** plus a lifecycle **status** (MANAGE). The four functions are not an abstraction here — they are fields.

Now the code side. A small dataclass model gives you validation, a scoring helper, and the ability to fail CI when the register goes stale. No external dependencies beyond a YAML parser:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum


class Likelihood(IntEnum):
    RARE = 1
    UNLIKELY = 2
    POSSIBLE = 3
    LIKELY = 4
    ALMOST_CERTAIN = 5


class Impact(IntEnum):
    NEGLIGIBLE = 1
    MINOR = 2
    MODERATE = 3
    MAJOR = 4
    SEVERE = 5


# Ordered worst-to-best so sorting a register surfaces the ugly ones first.
class Status(IntEnum):
    OPEN = 0          # identified, nothing done
    MITIGATING = 1    # mitigations in progress
    MONITORING = 2    # mitigated, watched in production
    ACCEPTED = 3      # residual risk consciously accepted
    CLOSED = 4        # no longer applicable


@dataclass
class Risk:
    id: str
    category: str
    description: str
    likelihood: Likelihood
    impact: Impact
    status: Status
    owner: str
    review_by: date
    mitigations: list[str] = field(default_factory=list)
    measure_ref: str | None = None

    def inherent_score(self) -> int:
        """Likelihood x impact, 1..25. The size of the problem before controls."""
        return int(self.likelihood) * int(self.impact)

    def band(self) -> str:
        s = self.inherent_score()
        if s >= 15:
            return "critical"
        if s >= 9:
            return "high"
        if s >= 4:
            return "medium"
        return "low"

    def is_stale(self, today: date | None = None) -> bool:
        """A risk past its review date is unmanaged, regardless of score."""
        today = today or date.today()
        return today > self.review_by and self.status not in (Status.CLOSED,)

    def needs_attention(self, today: date | None = None) -> bool:
        high_and_unhandled = (
            self.band() in ("high", "critical")
            and self.status in (Status.OPEN, Status.MITIGATING)
        )
        return high_and_unhandled or self.is_stale(today)
```

The scoring is deliberately simple: likelihood times impact on a 1–5 scale gives a 1–25 number and a band. Do not mistake the number for precision — it is a *sorting key*, a way to force a prioritization conversation, not a measurement. The bands are where the value is: they tell MANAGE what to look at first.

The two methods that matter most are `is_stale` and `needs_attention`. They are what let the register defend itself. Wire them into CI:

```python
def audit(register: list[Risk]) -> list[str]:
    """Return human-readable findings; non-empty means the build should fail."""
    findings: list[str] = []
    for r in register:
        if r.is_stale():
            findings.append(f"{r.id}: review overdue (was due {r.review_by})")
        if r.band() in ("high", "critical") and not r.mitigations:
            findings.append(f"{r.id}: {r.band()} risk with no mitigations listed")
        if r.band() in ("high", "critical") and r.measure_ref is None:
            findings.append(f"{r.id}: {r.band()} risk not tied to any eval")
    return findings


if __name__ == "__main__":
    import sys

    findings = audit(load_register("risk-register/"))  # your YAML loader
    for f in findings:
        print(f"RISK-AUDIT: {f}", file=sys.stderr)
    sys.exit(1 if findings else 0)
```

That last block is the whole trick. A high-or-critical risk with no mitigations, no linked eval, or a lapsed review date fails the build. The register can no longer rot silently, because the CI system nags on your behalf — which is exactly the enforcement GOVERN is supposed to provide, automated.

---

## Where MEASURE plugs in

The `measure_ref` field is not decoration. It is the seam between this framework and your actual test suite. Each high-severity risk should point at a benchmark that quantifies it: a faithfulness eval for hallucination, a PII-leakage probe for privacy, a cohort-sliced accuracy report for bias, an adversarial suite for robustness and prompt injection.

The register tells you *what* to measure and *why it matters*; the eval harness tells you *how bad it currently is* and *whether it got worse*. Run the evals on every model or prompt change, write the results back so the register reflects reality, and MEASURE stays alive instead of being a launch-day snapshot. Building that harness — datasets, metrics, LLM-as-judge, regression gates — is post 4, and it is where "we manage AI risk" stops being a claim and becomes a number you can put in front of a reviewer.

---

## From voluntary framework to hard obligation

The AI RMF is voluntary, but it is also the cheapest on-ramp to the obligations that are not. When the EU AI Act's requirements for high-risk systems land — risk management systems, data governance, transparency, human oversight, accuracy and robustness — you will find they rhyme closely with the RMF functions. A team already running MAP/MEASURE/MANAGE with a versioned register has most of the evidence those obligations demand; they mostly need to be pointed at the right paperwork.

That mapping — RMF functions and register fields onto specific EU AI Act articles and duties — is post 7. The point for now: doing the voluntary thing well is not busywork ahead of the mandatory thing. It *is* the mandatory thing, minus the deadline pressure.

---

## Key takeaways

- **The four functions are concurrent, not sequential.** GOVERN wraps the others; MAP builds context; MEASURE quantifies; MANAGE acts. MEASURE routinely sends you back to MAP.
- **GOVERN is the function teams skip, and its absence is why the rest decay.** No named owner and no review cadence means controls quietly rot.
- **Use the taxonomy as a checklist during MAP** so the risks you skip are skipped on purpose — accuracy, bias, privacy, security, safety, robustness, transparency, over-reliance, and cost.
- **Put the risk register in git and gate CI on it.** A versioned, reviewed YAML file with owners, review dates, and eval links beats any spreadsheet, because it defends itself against going stale.
- **MEASURE without a benchmark is vibes.** Tie each serious risk to a repeatable eval (post 4); the score is a sorting key, not a measurement.
- **Doing the voluntary RMF well is the cheapest path to the mandatory EU AI Act obligations** (post 7).

---

## Further reading

- [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) — the framework itself, including the GOVERN/MAP/MEASURE/MANAGE functions.
- [NIST AI RMF 1.0 full document (NIST AI 100-1)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) — the complete published framework as a PDF.
- [Generative AI Profile (NIST AI 600-1)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — companion profile cataloging risks specific to generative AI.
- [NIST Trustworthy and Responsible AI Resource Center](https://airc.nist.gov/) — the RMF Playbook, crosswalks, and related guidance.
- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/) — suggested actions for each function and subcategory.
