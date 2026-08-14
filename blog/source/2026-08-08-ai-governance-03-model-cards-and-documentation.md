# Model Cards and Documentation

*The evidence layer of AI governance — how model cards, datasheets, system cards, and automated FactSheets turn "trust us" into an auditable paper trail, and why the EU AI Act makes these artifacts the actual deliverable.*

---

Governance without evidence is just opinion. You can write a beautiful policy that says "our models are fair, safe, and used only as intended" — but the first time a regulator, an auditor, or an incident post-mortem asks *how you know*, you need artifacts, not assurances. **Documentation is the evidence layer**: the set of durable, versioned records that describe what a model is, what data shaped it, how it was evaluated, and where it must not be used.

This post covers the four documentation artifacts that matter for engineers shipping AI systems: **model cards** (describing a model), **datasheets** (describing the data behind it), **system/use-case cards** (describing the application you assembled around a model you didn't train), and **AI FactSheets / lineage** (the automated version that captures all of the above from the pipeline instead of a human writing it by hand). Then we build a small tool that generates a card at deploy time, so the documentation is a build output rather than a stale wiki page.

---

## Model cards: the origin

The **model card** was introduced by Margaret Mitchell and colleagues in their 2019 paper *Model Cards for Model Reporting*. The core argument is simple and still under-applied: a trained model is usually shipped with a headline accuracy number and nothing else, which hides the fact that a model performing well *on average* can perform terribly for specific groups or in specific conditions. A model card is a short, structured document that travels *with* the model and forces the author to disclose the parts that a single accuracy score erases.

The sections that carry the weight are consistent across implementations:

- **Intended use** — the tasks, users, and contexts the model was built for.
- **Out-of-scope use** — the uses the authors explicitly do *not* endorse. This is the most valuable and most-skipped section.
- **Training data (at a high level)** — provenance and rough composition, not the raw rows.
- **Evaluation** — metrics, but crucially *disaggregated* across relevant subgroups and conditions, not one global number.
- **Limitations and ethical considerations** — known failure modes, bias findings, safety observations.

I am describing the *concept* here rather than reproducing the paper's template — the templates in the literature are illustrative, and the point of a card is that you design one that fits your system. What matters is that these sections exist and are honestly filled.

**The gotcha:** the "intended use / out-of-scope use" pair is where liability lives, and it's the section people delete because it feels legalistic. A credit-scoring model card that says "not validated for jurisdictions outside the training region, not for automated adverse-action decisions without human review" *bounds the misuse* — it converts a foreseeable harm into a documented, communicated boundary. Skip it and every downstream misuse becomes your problem. Write it and you've shifted the story from negligence to a boundary someone crossed on purpose.

---

## Datasheets: describing the data, not the model

A model card describes the model; a **datasheet for a dataset** describes the raw material. The concept comes from Timnit Gebru and colleagues' *Datasheets for Datasets*, which borrows from the electronics industry — every component ships with a datasheet stating its operating characteristics, and datasets should too.

A datasheet answers questions the model card can't, because they're about the data's origin and legitimacy:

- **Motivation and provenance** — why was this dataset created, by whom, and from what source?
- **Composition** — what does each instance represent, are there sensitive attributes, are there known gaps?
- **Collection process** — how was it gathered, over what time window, with what sampling?
- **Consent and licensing** — did the people in the data agree to this use, and does the license permit what you're doing?
- **Recommended and discouraged uses** — the data-layer twin of intended/out-of-scope.

For engineers assembling LLM systems, the datasheet question that bites hardest is **consent and licensing on retrieval corpora**. If your RAG assistant retrieves from a scraped corpus, a licensed third-party dataset, or internal documents that include personal data, that provenance is a governance fact you must record — and increasingly one a regulator can ask you to produce.

**The gotcha:** "we fine-tuned on customer chat logs" is a sentence that can invalidate an entire deployment if those logs were collected under a privacy notice that never mentioned model training. The datasheet is where you catch this *before* launch — the consent and licensing fields are a forcing function, not paperwork. If you can't fill them in, you don't have the right to use the data.

---

## System cards: you document what you assembled

Here's the shift that trips up teams building on foundation models. You probably **did not train the model**. You called an API or pulled weights from a hub. So a classic model card — with its training-data and disaggregated-evaluation sections — is partly out of your hands.

But you *did* assemble a **system**: a base model, a set of prompts, a retrieval corpus, a collection of tools the model can call, guardrails, and an evaluation suite. That assembly is what your users experience, and it's what you're accountable for. The document that describes it is a **system card** (sometimes "use-case card"). It answers a different question than a model card: not "what is this model?" but "what did this team build, and out of what parts?"

A system card for an LLM application should pin down:

- **Base model and exact version** — the model id *and* the version/snapshot string.
- **Prompts** — the system prompt and any templated instructions, ideally by content hash so you can prove which version ran.
- **Retrieval sources** — which corpora, which snapshot/version, and their datasheets.
- **Tools** — what the model can invoke and what side effects those have.
- **Guardrails** — input/output filters, refusal policies, human-in-the-loop gates.
- **Evaluations** — the offline eval suite and the scores from the last run.

**The gotcha:** capture the base-model *version*, not the family. "Built on GPT-4-ish" or "uses Claude" is not documentation — it's a shrug. Model providers ship dated snapshots, deprecate them, and change behavior between versions; when your assistant's outputs shift overnight, the only way to correlate that with a provider update is if you recorded the exact version string that was live. A system card that says `gpt-4o` without the snapshot date can't answer the one question an incident review will ask: *what changed?*

---

## AI FactSheets and lineage: stop writing docs by hand

Every artifact above shares one failure mode: it's written once, by a human, at launch — and then the system keeps moving while the document sits still.

**The gotcha:** a model card written at launch and never updated is *worse than no card at all*, because it manufactures false assurance. It says "evaluated for bias" while pointing at scores from a model version that was retired two quarters ago. An auditor who trusts it is being misled, and so are you. A stale card is a liability that looks like a control. The fix is not "remember to update the card" — humans don't, reliably. The fix is to **generate the card from the pipeline** so it can't drift from reality.

This is the idea behind **AI FactSheets**, an approach from IBM Research: instead of authoring documentation as prose, you *capture metadata across the lifecycle* — at data prep, at training, at evaluation, at deployment — and assemble the record automatically. Each stage emits facts (dataset version, hyperparameters, eval scores, approval sign-offs) and the FactSheet is the accumulated, timestamped collection of them. Governance platforms have productized this: **watsonx.governance**, Azure ML, Vertex AI, and others attach lineage and metadata to model and endpoint objects so the "card" is queryable rather than written. The common thread is that documentation becomes a *byproduct of the pipeline*, keyed to a specific run, rather than a document someone maintains on the side.

You don't need a platform to adopt the principle. You need a build step that reads the facts that already exist — the model id, the prompt file, the dataset version, the last eval report, the git SHA — and writes them into a card automatically.

---

## An original system card, filled for a RAG assistant

Here's a system card for a hypothetical internal support assistant, "HelpDesk RAG," that answers employee IT questions by retrieving from an internal knowledge base. This is my own template, not a reproduction of any published one — designed to be small enough that a team will actually keep it current, because most of it is machine-filled (see the generator below).

```yaml
# system_card.yaml — HelpDesk RAG assistant
card_type: system
name: helpdesk-rag-assistant
owner: platform-ml@example.com
generated_at: "2026-08-08T14:22:05Z"      # stamped by the build, not by hand

base_model:
  id: gpt-4o
  version: "2024-11-20"                    # the exact snapshot, not the family
  provider: azure-openai
  temperature: 0.2

prompts:
  system_prompt_path: prompts/helpdesk_system.txt
  system_prompt_sha256: "9f2c...e41a"       # proves which prompt version ran
  retrieval_template_sha256: "1b77...9c03"

retrieval:
  corpus: it-knowledge-base
  corpus_version: "2026-08-01"
  datasheet: datasheets/it-kb.md            # consent + licensing recorded there
  top_k: 6
  reranker: none

tools:
  - name: create_ticket
    side_effects: true                      # writes to the ticketing system
    approval: human_in_loop
  - name: lookup_asset
    side_effects: false

guardrails:
  input_filters: [pii_redaction, prompt_injection_screen]
  output_filters: [pii_redaction, refusal_policy_v3]
  human_review_for: [create_ticket]

intended_use:
  users: internal employees
  tasks: [answer IT how-to questions, surface KB articles, open support tickets]
scope_boundaries:
  out_of_scope:
    - HR, legal, or medical questions
    - decisions affecting employment or compensation
    - any use outside the corporate network

evaluation:
  suite: evals/helpdesk_suite_v4
  run_id: "eval-2026-08-07-113"
  results:
    groundedness: 0.94                      # fraction of answers supported by retrieved docs
    answer_relevance: 0.91
    refusal_correctness: 0.97               # correctly refuses out-of-scope asks
    pii_leak_rate: 0.00

limitations:
  - "Coverage limited to KB snapshot; newer incidents may not be reflected."
  - "Groundedness measured on a 300-question offline set, not live traffic."

lineage:
  git_sha: "c1a9f30"
  pipeline_run: "deploy-2026-08-08-0072"
```

Notice how much of this is *fact*, not *narrative* — versions, hashes, scores, ids. That's the part a machine should fill.

---

## Generating the card at deploy time

The point of the FactSheet philosophy is that the fields above should be *captured*, not typed. Here's a small generator that reads the facts already present in a deploy — the prompt files on disk, the eval report the CI run just produced, the git state — and emits the card. It uses only the Python standard library plus PyYAML (`yaml.safe_dump`), so there are no invented APIs.

```python
"""build_system_card.py — assemble a system card from pipeline facts at deploy time."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml  # PyYAML: yaml.safe_dump


def sha256_of(path: str) -> str:
    """Content hash of a file, so we can prove which version was deployed."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_sha() -> str:
    """Short commit SHA of the code being deployed."""
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def build_card(config: dict, eval_report_path: str) -> dict:
    """Merge hand-authored intent (config) with captured facts (hashes, scores, SHA)."""
    evals = json.loads(Path(eval_report_path).read_text())

    card = dict(config)  # intended_use, scope_boundaries, tools, etc. authored once
    card["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    card["prompts"] = {
        "system_prompt_path": config["prompts"]["system_prompt_path"],
        "system_prompt_sha256": sha256_of(config["prompts"]["system_prompt_path"]),
        "retrieval_template_sha256": sha256_of(config["prompts"]["retrieval_template_path"]),
    }
    card["evaluation"] = {
        "suite": evals["suite"],
        "run_id": evals["run_id"],
        "results": evals["results"],
    }
    card["lineage"] = {"git_sha": git_sha(), "pipeline_run": config["pipeline_run"]}
    return card


def gate_on_evals(card: dict, thresholds: dict) -> None:
    """Fail the deploy if the card can't clear governance thresholds."""
    results = card["evaluation"]["results"]
    breaches = [
        f"{metric}={results[metric]} < {floor}"
        for metric, floor in thresholds.items()
        if results.get(metric, 0) < floor
    ]
    if breaches:
        raise SystemExit("Deploy blocked — eval floors not met: " + "; ".join(breaches))


if __name__ == "__main__":
    config = yaml.safe_load(Path("card_config.yaml").read_text())  # the authored intent
    card = build_card(config, eval_report_path="evals/latest_report.json")
    gate_on_evals(card, thresholds={"groundedness": 0.85, "pii_leak_rate": 0.0})
    Path("system_card.yaml").write_text(yaml.safe_dump(card, sort_keys=False))
    print(f"Wrote system_card.yaml @ {card['generated_at']} ({card['lineage']['git_sha']})")
```

Two design choices make this governance rather than logging. First, the card is split into **authored intent** (`card_config.yaml` holds intended use, out-of-scope boundaries, tool list — the parts that require human judgment) and **captured facts** (hashes, eval scores, git SHA — the parts that must never be typed by hand). Second, `gate_on_evals` makes the card a **deploy gate**: if the last eval run didn't clear the floors, the deploy fails and no stale card is written. The document can't lie about the scores, because the scores are what let the deploy proceed.

Run this in CI on every deploy and the card is always keyed to the exact artifact that shipped — the failure mode of the launch-day-only card is designed out.

---

## Why this is the regulatory deliverable

None of this is optional hygiene anymore. The **EU AI Act** (which the next post in this series covers in depth) requires providers of high-risk AI systems to draw up and keep current **technical documentation** — its Annex IV enumerates a description of the system, its intended purpose, the data used, and the validation and testing procedures with their results. Read that list against the sections above: intended use, data provenance, evaluation results, limitations. The Act is, in effect, mandating a maintained model-and-system card, and requiring that it stay current for the life of the system.

That reframes the whole exercise. The documentation is not a nice-to-have you produce if you have time after shipping — for a regulated system, **the artifact *is* the deliverable**. And the "keep it current" clause is exactly why the auto-generation approach matters: a hand-maintained document cannot meet an obligation to stay accurate across a system that changes every sprint. Generate it from the pipeline and the compliance requirement becomes a build step you already run.

---

## The artifacts at a glance

| Artifact | Describes | Key sections | Who owns it |
|---|---|---|---|
| Model card | A trained model | Intended/out-of-scope use, training data, disaggregated evals, limitations | Model trainer |
| Datasheet | A dataset | Provenance, composition, collection, consent, licensing | Data owner |
| System card | An assembled application | Base model + version, prompts, retrieval, tools, guardrails, evals | System builder |
| FactSheet / lineage | The whole lifecycle | Auto-captured metadata across every stage | The pipeline |

---

## Key takeaways

- **Documentation is the evidence layer.** Policy says what you intend; artifacts prove what you did. Governance without them is unfalsifiable.
- **Model cards force disclosure a single accuracy number hides** — especially intended and out-of-scope use, the section that bounds liability and is skipped most often.
- **Datasheets catch data-legitimacy problems before launch.** If you can't fill in consent and licensing, you don't have the right to use the data.
- **You document the system you assembled, not just the model you didn't train** — base model *and* exact version, prompts by hash, retrieval sources, tools, guardrails, evals.
- **Auto-generate the card from the pipeline.** A card written at launch and never updated manufactures false assurance; capture facts as build outputs and gate the deploy on them.
- **For high-risk systems, the artifact is the compliance deliverable.** The EU AI Act's technical-documentation obligation makes a maintained system card the thing you hand over.

---

## Further reading

- [Model Cards for Model Reporting — Mitchell et al., 2019 (arXiv 1810.03993)](https://arxiv.org/abs/1810.03993)
- [Datasheets for Datasets — Gebru et al. (arXiv 1803.09010)](https://arxiv.org/abs/1803.09010)
- [Hugging Face — Model Cards documentation](https://huggingface.co/docs/hub/model-cards)
- [IBM Research — AI FactSheets 360](https://aifs360.res.ibm.com/)
- [EU AI Act — Annex IV, Technical documentation](https://artificialintelligenceact.eu/annex/4/)
