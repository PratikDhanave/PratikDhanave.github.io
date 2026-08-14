# Monitoring and Drift in Production

*Governance doesn't stop at deploy. This is the NIST RMF MANAGE function in practice: what to monitor for an LLM system, how to detect the drift — including the silent kind where a provider swaps the model under you — and why the audit trail you log is the regulatory deliverable, not a debugging convenience.*

---

Earlier in this series we mapped an AI risk register (post 2), wrote a model card (post 3), and built an offline evaluation harness (post 4). All of that describes the system *at the moment you shipped it*. Production is a moving target. Inputs shift, users find edge cases you never tested, and — uniquely for LLM systems — the model itself can change underneath you without a single line of your code changing.

The NIST AI Risk Management Framework organizes governance into four functions: GOVERN, MAP, MEASURE, and MANAGE. Monitoring lives in MANAGE — the function that says risks must be tracked, responded to, and reviewed *over the deployment lifetime*, not signed off once. This post is where offline MEASURE becomes online MEASURE, and where the risk register stops being a document and starts being a live feed.

The core discipline: **decide what to watch, watch it continuously, alert when it moves, and log enough to explain any single decision after the fact.** Everything below is a variation on those four verbs.

---

## Four things to monitor

An LLM system fails in more ways than a traditional service, so the monitoring surface is wider. Group it into four buckets and you can reason about coverage.

### Operational signals

The classic service-health metrics, and the cheapest to collect because your infrastructure already emits most of them:

- **Latency** — p50/p95/p99 end-to-end, and separately for retrieval vs. generation so you know which stage is slow.
- **Error rate** — provider 429/500s, timeouts, JSON-parse failures on structured outputs, tool-call failures.
- **Cost and tokens** — input/output tokens per request and rolled up per day. Token count is a leading indicator: a creeping prompt or a retriever returning more chunks shows up here before it shows up on the invoice.

### Quality signals

Operational health tells you the system *responded*, not that it responded *well*. Quality has to be sampled, because you cannot run an expensive judge on every request:

- **Online faithfulness / groundedness** — for RAG, sample a percentage of live traffic and score whether the answer is supported by the retrieved context. This is the same faithfulness check from the offline harness (post 4), now run against real inputs.
- **Task success** — did the agent complete what the user asked? For structured tasks you can measure this directly (did the booking go through); for open-ended ones you approximate it with an LLM judge or human review.
- **User feedback** — thumbs up/down, explicit ratings, and implicit signals like edits, retries, and abandonment.
- **Deflection / containment** — for support use cases, the share of conversations resolved without escalation to a human. A falling deflection rate is a quality regression even when every individual metric looks fine.

### Safety signals

The guardrails you put in front of and behind the model (post 5, the security series) are also a monitoring source:

- **Guardrail trips** — how often input filters, prompt-injection detectors, or output moderators fire, broken down by rule.
- **Flagged content** — refusals, PII detections, toxicity hits. A sudden spike often means an attack or a prompt regression, not organic traffic.

### Drift

The category that is specific to statistical systems and the reason this post exists — covered in its own section below.

**The gotcha:** monitoring you don't *alert* on is just expensive logging. A dashboard nobody looks at catches nothing. Every metric that matters needs a threshold and a named owner who gets paged when it crosses. If you can't say who responds when faithfulness drops below 0.8, you are not monitoring faithfulness — you are collecting it.

---

## Drift: the same word for three different problems

"Drift" gets used loosely. Pulling it apart matters because the three kinds have different causes and different detection methods.

**Data drift (input distribution shift).** The distribution of inputs moves away from what you saw at training/evaluation time. A new customer segment starts using the product, a marketing campaign changes the question mix, a new product line introduces vocabulary your retriever has never indexed. The model hasn't changed; the world feeding it has. Detection: statistical distance between a reference window and a current window of inputs.

**Concept drift.** The relationship between inputs and the *correct* output changes, even if the inputs look the same. A policy update means last month's correct answer is now wrong; "current CEO" has a different right answer than it did a year ago. This is insidious because your inputs can look statistically identical while your accuracy quietly collapses. Detection is harder — it usually requires ground-truth labels or a judge scoring correctness, not just input statistics.

**Silent model drift (the LLM-specific one).** You pinned nothing and pointed your client at a moving alias like `gpt-4o` or `claude-3-5-sonnet-latest`. The provider ships an update behind that alias. Your prompts, your code, and your eval set are byte-for-byte identical, and the behavior changes anyway — sometimes better, sometimes a regression in exactly the formatting or reasoning your downstream parsing depends on. Nothing in *your* diff explains it, so nobody thinks to look.

**The gotcha:** a model behind a moving alias drifts silently when the provider updates it. Pin an explicit, dated model version in production (most providers publish snapshot identifiers for exactly this reason), record that version in every log line, and watch your quality metrics for *step changes* — a discontinuity on a specific date is the fingerprint of a model swap, whereas a gradual slope is usually input drift. Treat a provider version bump like any other dependency upgrade: stage it, re-run the offline eval set, and promote deliberately.

---

## Detecting drift

Three complementary techniques, roughly in order of cost.

**Distribution tests on features you can measure cheaply.** For numeric or categorical features — input length, language, detected topic, retrieval score, token count — compare a reference window to the current window. Two standard measures:

- **Population Stability Index (PSI)** bins both distributions and sums `(current% - reference%) * ln(current% / reference%)` across bins. A common rule of thumb from credit-risk practice treats PSI below 0.1 as stable, 0.1–0.25 as moderate shift worth investigating, and above 0.25 as significant drift. It is a rule of thumb, not a law — calibrate the thresholds to your own baseline.
- **KL divergence** measures how much one distribution diverges from another; it is asymmetric and unbounded, which makes PSI's symmetric, bounded-in-practice behavior easier to threshold for alerting.

**Embedding-distribution shift.** Free text has no natural numeric feature to bin, so embed the inputs (or outputs) and track the distribution in vector space — for example the mean distance of recent inputs from a reference centroid, or a divergence between reference and current embedding clusters. This is how you catch "users are suddenly asking about a topic we never indexed" without hand-defining topics.

**Metric-trend tracking.** Drift often shows up first as a slow slide in a downstream metric — faithfulness, task success, thumbs-up rate — before any single request looks anomalous. Rolling windows and trend alerts on the quality metrics above are drift detection, just measured on outcomes instead of inputs.

**Sampling for judgement.** For anything a formula can't score — nuance, tone, subtle wrongness — sample a slice of production traffic and route it to an LLM judge or a human reviewer. This closes the loop on concept drift, which pure input statistics will miss entirely.

**The gotcha:** offline eval scores expire. The 0.92 faithfulness you measured at launch describes your *eval set*, and production input distribution drifts away from that set over time. A green offline number and a red production reality can coexist. Monitor online, and periodically fold real production inputs (the failures especially) back into the eval set so it keeps describing the traffic you actually get.

---

## A lightweight monitor

Here is a self-contained monitor that does the four verbs: log a structured record per request, maintain a rolling window of a quality metric, compute a simple drift signal (PSI) on an input feature, and raise an alert when either crosses a threshold. It has no external dependencies so you can read the whole mechanism; the next section maps each piece to the production tools you would actually reach for.

```python
import json
import math
import time
import uuid
from collections import deque
from dataclasses import dataclass, asdict, field


@dataclass
class RequestRecord:
    """One row of the audit trail. Everything needed to reconstruct a decision."""
    request_id: str
    timestamp: float
    model_version: str          # PINNED snapshot id, never a moving alias
    prompt_version: str         # the prompt template revision in effect
    input_text: str             # redact PII before this reaches storage
    output_text: str
    retrieved_context_ids: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    quality_score: float | None = None   # e.g. sampled faithfulness in [0, 1]
    guardrail_trips: list[str] = field(default_factory=list)


def population_stability_index(reference: list[float],
                               current: list[float],
                               bins: int = 10) -> float:
    """PSI between a reference and current numeric distribution.

    Higher means more drift. Common rule of thumb: <0.1 stable,
    0.1-0.25 moderate, >0.25 significant. Calibrate to your baseline.
    """
    if not reference or not current:
        return 0.0
    lo, hi = min(reference), max(reference)
    if hi == lo:
        return 0.0
    width = (hi - lo) / bins
    edges = [lo + i * width for i in range(bins + 1)]

    def histogram(values: list[float]) -> list[float]:
        counts = [0] * bins
        for v in values:
            idx = min(int((v - lo) / width), bins - 1) if v >= lo else 0
            idx = max(0, min(idx, bins - 1))
            counts[idx] += 1
        total = len(values)
        # floor each bucket so we never take log(0)
        return [max(c / total, 1e-6) for c in counts]

    ref_pct, cur_pct = histogram(reference), histogram(current)
    return sum((c - r) * math.log(c / r) for r, c in zip(ref_pct, cur_pct))


class ProductionMonitor:
    """Logs per-request records, tracks a rolling quality metric, and
    watches an input feature for drift. Alerts when either crosses a
    threshold. Deliberately small; wire the real pieces in production."""

    def __init__(self,
                 log_path: str,
                 reference_feature: list[float],
                 quality_floor: float = 0.80,
                 psi_ceiling: float = 0.25,
                 window: int = 200):
        self._log_path = log_path
        self._reference_feature = reference_feature
        self._quality_floor = quality_floor
        self._psi_ceiling = psi_ceiling
        self._recent_quality: deque[float] = deque(maxlen=window)
        self._recent_feature: deque[float] = deque(maxlen=window)

    def record(self, rec: RequestRecord, drift_feature: float) -> list[str]:
        """Append the audit row, update rolling state, return any alerts."""
        self._append(rec)
        self._recent_feature.append(drift_feature)
        if rec.quality_score is not None:
            self._recent_quality.append(rec.quality_score)
        return self._evaluate()

    def _append(self, rec: RequestRecord) -> None:
        # One JSON object per line: cheap to write, trivial to ship to a
        # log pipeline, and queryable after the fact for an audit.
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(rec)) + "\n")

    def _evaluate(self) -> list[str]:
        alerts: list[str] = []

        if len(self._recent_quality) >= 30:
            avg = sum(self._recent_quality) / len(self._recent_quality)
            if avg < self._quality_floor:
                alerts.append(
                    f"QUALITY: rolling faithfulness {avg:.3f} "
                    f"below floor {self._quality_floor:.2f}")

        if len(self._recent_feature) >= 30:
            psi = population_stability_index(
                self._reference_feature, list(self._recent_feature))
            if psi > self._psi_ceiling:
                alerts.append(
                    f"DRIFT: input-feature PSI {psi:.3f} "
                    f"above ceiling {self._psi_ceiling:.2f}")

        return alerts


def notify(owner: str, alerts: list[str]) -> None:
    """Stand-in for paging. A threshold without an owner is not an alert."""
    for a in alerts:
        print(f"[PAGE -> {owner}] {a}")
```

Wiring it into a request path looks like this. Note that scoring quality is sampled — you decide the rate — while the audit record is written for *every* request:

```python
import random

monitor = ProductionMonitor(
    log_path="audit_trail.jsonl",
    reference_feature=baseline_input_lengths,   # captured at launch
    quality_floor=0.80,
    psi_ceiling=0.25,
)

def handle(user_input: str) -> str:
    started = time.perf_counter()
    redacted = redact_pii(user_input)           # from the security series
    context = retriever.search(redacted)
    answer, usage = model.generate(redacted, context)  # pinned model version
    latency = (time.perf_counter() - started) * 1000

    # Score only a sample; judging every request is too expensive.
    score = faithfulness_judge(answer, context) if random.random() < 0.05 else None

    rec = RequestRecord(
        request_id=str(uuid.uuid4()),
        timestamp=time.time(),
        model_version="my-provider/model-2026-05-13",   # PINNED, dated
        prompt_version="rag-answer-v7",
        input_text=redacted,
        output_text=answer,
        retrieved_context_ids=[c.id for c in context],
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        latency_ms=latency,
        quality_score=score,
    )
    alerts = monitor.record(rec, drift_feature=float(len(redacted)))
    if alerts:
        notify(owner="rag-oncall@example.com", alerts=alerts)
    return answer
```

The functions `redact_pii`, `retriever.search`, `model.generate`, and `faithfulness_judge` are placeholders for your own components — the monitor doesn't care how they're implemented, only that the record captures the versions, the retrieved context, and (sometimes) a score.

**The gotcha:** the audit trail is the regulatory deliverable, not a debugging convenience. Capture the *pinned* model version, the prompt version, and the retrieved context IDs on every record — without them you cannot reconstruct why a decision was made, and "we can't reproduce it" is not an answer to a regulator or an affected user. And redact PII *before* the text reaches storage (cross-reference the security series): an audit log full of raw personal data is itself a compliance liability, not evidence.

---

## Use the ecosystem, don't rebuild it

The monitor above exists to make the mechanism legible. In production you compose real tools, each strong at one layer:

- **Prometheus** — the de facto standard for operational time-series: latency histograms, error counters, token and cost gauges, with alerting rules via Alertmanager. This is where the operational bucket lives.
- **OpenTelemetry** — vendor-neutral tracing/metrics/logs. Its **GenAI semantic conventions** define standard attribute names for model calls (model, tokens, and related fields), so you emit spans in a portable shape rather than a bespoke schema. Instrument once, export anywhere.
- **Evidently** — an open-source library focused on ML/LLM monitoring and data/prediction drift: it implements distribution tests (including PSI and others), text and embedding drift checks, and report/test-suite generation. Reach for it instead of hand-rolling PSI.
- **Langfuse** and **Arize Phoenix** — LLM observability platforms built around tracing every request, prompt, and retrieval step, with online evaluation and dataset/experiment tracking. They are the natural home for the quality bucket and the sampled-judgement loop, and both integrate with OpenTelemetry-style tracing.

A realistic stack: OpenTelemetry for portable instrumentation, Prometheus/Alertmanager for operational alerting, Evidently for scheduled drift reports on inputs and embeddings, and Langfuse or Phoenix for per-request traces plus online quality evaluation. The hand-written monitor is what those tools are doing under the hood — knowing the mechanism helps you configure them and read their output critically.

---

## Closing the governance loop

Monitoring is only valuable if it feeds back into the governance artifacts from earlier posts:

- When a metric threshold is crossed, that is a **risk event** — it belongs in the risk register (post 2) with its trigger, response, and owner, so MANAGE has a record of what fired and what you did.
- When you observe production behavior — a new failure mode, a revised operating range, a version pin — update the **model card** (post 3) so it keeps describing the deployed system, not the launch-day one.
- The **audit trail** is the raw material for the accountability and reporting obligations coming in post 7: the evidence that lets you explain, reconstruct, and defend any individual decision the system made.

Governance that ends at deploy is a snapshot of a system that no longer exists. The MANAGE function is the standing commitment to keep the snapshot true.

---

## Key takeaways

- **Monitoring is the MANAGE function.** Governance is a lifecycle commitment, not a launch checklist — watch the system for as long as it runs.
- **Four buckets:** operational (latency, errors, cost/tokens), quality (sampled faithfulness, task success, user feedback, deflection), safety (guardrail trips, flagged content), and drift.
- **Three drifts, three detections.** Data drift → distribution tests on inputs; concept drift → labels or a judge on outputs; silent model drift → pin versions and watch for step-changes on a date.
- **Alert or it's just logging.** Every metric that matters needs a threshold *and* a named owner.
- **The audit trail is the deliverable.** Log pinned model + prompt versions, retrieved context, and scores per request — and redact PII before it lands.
- **Compose the ecosystem.** Prometheus, OpenTelemetry (GenAI semconv), Evidently, and Langfuse/Phoenix each own a layer; the hand-rolled monitor just shows what they do.

---

## Further reading

- [NIST AI Risk Management Framework (AI RMF 1.0)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) — see the MANAGE and MEASURE functions.
- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/) — actionable guidance per function.
- [Evidently AI documentation](https://docs.evidentlyai.com/) — data/LLM drift metrics and test suites.
- [Langfuse documentation](https://langfuse.com/docs) — LLM tracing and online evaluation.
- [Arize Phoenix documentation](https://arize.com/docs/phoenix) — open-source LLM observability and evaluation.
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — standard attributes for instrumenting model calls.
- [Prometheus documentation](https://prometheus.io/docs/introduction/overview/) — metrics collection and alerting.
