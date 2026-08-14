# Guardrails and Content Safety

*The defensive layer that screens what goes into a model and what comes out — input rails, output rails, topical rails, and groundedness checks — plus the real tooling ecosystem and a vendor-neutral Python pipeline that wraps a model call and knows how to refuse.*

---

Earlier posts in this series argued that prompt injection has no clean fix (post 2), and that the damage any injection can do equals the agent's agency (post 4). Both conclusions point at the same design move: since you cannot make the model perfectly obedient, you wrap it in controls that shrink what a manipulated model can do. Least-privilege tools and careful output handling are two of those controls. **Guardrails** are another — a screening layer that inspects the text flowing *into* the model and the text flowing *out* of it, and blocks, rewrites, or flags anything that violates policy.

The word "guardrail" gets used loosely, so let me be precise about what it is and, just as importantly, what it is not. A guardrail is a check that runs *around* your model call, in your control flow, deciding whether a given piece of text is allowed to proceed. It is not a property of the model's weights, not a system-prompt instruction (the model can ignore those), and not a substitute for the least-privilege design from post 4. It is a filter you own, run, and can reason about — and, crucially, one you can measure.

---

## What guardrails actually do

Think of a request's lifecycle as a pipe: user input → your model call → model output → your application. Guardrails are checkpoints you insert at the two ends of that pipe, and sometimes in the middle for retrieval. They fall into a few well-understood families.

**Input rails** screen the text *before* it reaches the model. They catch prompt-injection attempts, block off-topic or abusive input, strip or mask personal data the model has no business seeing, and reject requests that are out of scope for your application. An input rail can *block* ("refuse this request") or *transform* (redact a credit-card number, then let the sanitized text through).

**Output rails** screen the model's response *before* your application uses it. This is where you catch harmful content, responses that leak a secret or a system prompt, answers that wander off-policy (a banking assistant giving medical advice), and — for retrieval systems — answers that aren't actually supported by the retrieved sources.

**Topical rails** are a specialization worth naming on their own: they keep the conversation inside its intended subject. A customer-support bot for a shipping company should not be drawn into writing your Python homework, both because it's off-brand and because off-topic excursions are a common jailbreak on-ramp.

**Groundedness (or faithfulness) checks** are the output rail that matters most for RAG. The model produced an answer; the retrieval step produced source passages. A groundedness check asks a second model, "Is this answer actually supported by these sources?" and flags claims that aren't. It is the practical defense against confident hallucination in a system that's supposed to be citing documents.

The through-line: every rail is a **classifier** — it takes text and emits a verdict. That framing matters, because it tells you exactly how a guardrail can fail, which we'll return to.

---

## Defense in depth, not a silver bullet

The single most important thing to internalize about guardrails is that they are a *layer*, not a *fix*. They stack on top of the controls from earlier posts; they don't replace them.

Picture the layers around a tool-using agent:

```text
  Input rail   →  screen the incoming request
  System prompt →  instructions (advisory — the model may ignore them)
  The model     →  generates a response / tool call
  Least privilege → tools are scoped, side effects gated (post 4)
  Output handling → model output treated as untrusted (post 4)
  Output rail   →  screen the response before the app uses it
```

Each layer is porous. An input rail is a classifier with a miss rate, so some injections get through. The output rail is another classifier, so some harmful outputs get through *it*. The point of stacking is that an attack has to defeat *every* layer to cause harm, and the probability of that drops with each independent control.

This is why the least-privilege point from post 4 is load-bearing. Guardrails make a successful attack *less likely*; least-privilege tools make a successful attack *less damaging*. You need both.

**The gotcha:** a guardrail is a layer, not a cure. A determined injection that slips past your input rail, combined with an over-privileged tool, still wins — the output rail never sees the damage because the damage happened in a tool call, not in the text. If your agent can wire money or delete records, no amount of content filtering saves you when the tool itself isn't scoped. Fix the agency first (post 4); add rails second.

---

## The real ecosystem, by category

You rarely build guardrails from nothing. There's a mature ecosystem, and it splits into three categories. I'll name real tools and say what each is *for* — but treat their exact method names and parameters as things to confirm against current docs, because these projects move fast.

### Safety classifier models

These are open-weight models fine-tuned to do one job: read a piece of text (a prompt, a response, or both) and classify it against a taxonomy of harms.

- **Llama Guard** (Meta) — an LLM-based input/output safety classifier. You give it the conversation and it returns whether the content is safe or unsafe, and which hazard categories were triggered. It's designed to sit on both the input and output side.
- **Granite Guardian** (IBM) — a family of guardrail models covering harm categories plus RAG-specific risks like groundedness and answer relevance, which makes it interesting for retrieval systems specifically.
- **ShieldGemma** (Google) — Gemma-based content-moderation classifiers that score text against harm categories.

You run these yourself (self-hosted or via a provider that serves them), so you control latency, cost, and data residency — at the price of operating a model.

### Programmable guardrail frameworks

These are libraries that let you *express* rails as configuration or code, orchestrating checks around your model call.

- **NeMo Guardrails** (NVIDIA) — an open-source toolkit where you define input, output, topical, and dialog rails, often in a purpose-built configuration format, and it runs them around your LLM calls.
- **Guardrails AI** — an open-source framework built around composable validators (a "hub" of checks for things like toxic language, PII, competitor mentions, valid JSON) that you attach to inputs and outputs, with actions to take when a validator fails.
- **Microsoft Presidio** — not a full guardrail framework but a focused, excellent one for **PII**: it detects and de-identifies personal data (names, emails, card numbers, and many more) using recognizers you can extend. It's the tool to reach for when your input or output rail is specifically "find and mask personal data."

### Hosted moderation APIs

These are managed services you call over the network — no model to operate.

- **OpenAI moderation** — a free moderation endpoint that classifies text (and images, for some models) against OpenAI's harm categories and returns per-category scores and flags.
- **Azure AI Content Safety** — a Microsoft service that detects harmful content across categories like hate, violence, sexual, and self-harm, with severity levels, plus dedicated detectors for things like jailbreak/prompt-injection attempts and groundedness.

How to choose, roughly: hosted APIs are the fastest to adopt and need no infrastructure, but send your text to a third party and cost per call. Self-hosted classifier models keep data in-house and can be cheaper at scale, but you operate them. Programmable frameworks are the orchestration layer that ties either kind of check into coherent input/output rails. Most serious systems mix all three.

---

## A vendor-neutral guardrail pipeline

Here's the shape that matters, independent of any specific tool: a pipeline that wraps a model call with an input check and an output check, and treats "blocked" as a first-class result rather than an exception to swallow. I'll model the verdicts explicitly so the *state machine* is visible — that's the real lesson, more than any one check's implementation.

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol


class Decision(Enum):
    ALLOW = "allow"        # text is fine as-is
    TRANSFORM = "transform"  # text is usable after modification (e.g. PII masked)
    BLOCK = "block"        # text must not proceed


@dataclass
class RailResult:
    decision: Decision
    text: str              # possibly-rewritten text
    reason: str = ""       # why, for logging and for the user-facing refusal
    rail: str = ""         # which rail fired, for observability


class Rail(Protocol):
    """A rail is just a classifier over text that returns a RailResult."""
    def __call__(self, text: str) -> RailResult: ...
```

A rail is nothing more than a function from text to a `RailResult`. That uniform shape lets you compose rails and swap implementations — a hosted moderation call, a self-hosted Llama Guard call, a Presidio redaction pass — behind one interface.

Now the pipeline. Note what it returns: not a string, but a tagged outcome the caller *must* branch on.

```python
@dataclass
class Outcome:
    ok: bool               # did a real model answer make it through?
    text: str              # the answer, OR a safe refusal message
    blocked_by: str = ""   # which rail refused, if any


SAFE_REFUSAL = (
    "I can't help with that request. If you think this is a mistake, "
    "rephrase it or contact support."
)


def run_guarded(
    user_input: str,
    input_rails: list[Rail],
    model_call: Callable[[str], str],
    output_rails: list[Rail],
) -> Outcome:
    # --- input rails: run before spending a token on the model ---
    text = user_input
    for rail in input_rails:
        result = rail(text)
        if result.decision is Decision.BLOCK:
            return Outcome(ok=False, text=SAFE_REFUSAL, blocked_by=result.rail)
        if result.decision is Decision.TRANSFORM:
            text = result.text  # e.g. PII stripped; keep going with sanitized text

    # --- the actual model call ---
    answer = model_call(text)

    # --- output rails: the model's answer is untrusted until screened ---
    for rail in output_rails:
        result = rail(answer)
        if result.decision is Decision.BLOCK:
            return Outcome(ok=False, text=SAFE_REFUSAL, blocked_by=result.rail)
        if result.decision is Decision.TRANSFORM:
            answer = result.text  # e.g. redact a leaked secret, then allow

    return Outcome(ok=True, text=answer)
```

The input rails run *first*, so a blocked request never costs you a model call. The output rails run *last*, treating the model's own text as untrusted — the same principle as post 4's insecure-output-handling defense, applied to content rather than to code injection. And the return type forces the caller to handle refusal explicitly:

```python
outcome = run_guarded(user_input, input_rails, model_call, output_rails)
if outcome.ok:
    display(outcome.text)
else:
    display(outcome.text)               # the safe refusal
    log.warning("guardrail blocked", extra={"rail": outcome.blocked_by})
```

**The gotcha:** a tripped rail returns a refusal or an altered answer — that is a *distinct application state*, not a normal completion. If your code does `answer = run_guarded(...)` and pipes it straight into the UI, a blocked request and a real answer look identical downstream, and your metrics can't tell "the model helped" from "the model was stopped." Model the outcome as a tagged result, branch on it, and log which rail fired. A guardrail you can't observe is a guardrail you can't tune.

---

## Classifier-as-a-gate: calling a safety model

The most common concrete rail is "ask a safety model, parse its verdict, act on it." Here's that pattern in the abstract, with the model call left as a boundary you fill in for your chosen tool. The important part is the *contract*: send text, get back a structured verdict, translate it into a `RailResult`.

```python
def safety_classifier_rail(classify: Callable[[str], dict], name: str) -> Rail:
    """
    Wrap any safety-model call into a Rail.

    `classify(text)` is your provider call. Whatever the tool (Llama Guard,
    a hosted moderation endpoint, Azure AI Content Safety), it returns a
    verdict you normalize into this shape:
        {"flagged": bool, "categories": [str, ...], "max_severity": float}
    Confirm the exact response schema against that tool's current docs.
    """
    # Per-category severity threshold: tune these against YOUR data, not defaults.
    THRESHOLD = 0.5

    def rail(text: str) -> RailResult:
        verdict = classify(text)
        if verdict["flagged"] and verdict["max_severity"] >= THRESHOLD:
            cats = ", ".join(verdict["categories"]) or "policy violation"
            return RailResult(Decision.BLOCK, text, reason=cats, rail=name)
        return RailResult(Decision.ALLOW, text, rail=name)

    return rail
```

Two things to notice. First, the verdict is normalized into your own small schema *before* you make a decision — so swapping OpenAI moderation for Azure AI Content Safety touches only the `classify` function, not the rail logic. Second, the threshold is explicit and tunable. That is not incidental; it's the whole game.

**The gotcha:** every guardrail is a classifier, which means it has false positives *and* false negatives — always both, never neither. A high threshold lets more harmful content through (more false negatives); a low threshold blocks more legitimate requests (more false positives), and users hate a bot that refuses everything. There is no threshold that eliminates both. Measure each rate on labelled data, then tune per rail *per risk*: a bank's rail against leaking account numbers should err toward blocking; a topical rail on a casual chatbot can afford to be lenient. Ship a threshold you measured, not one you guessed.

---

## The costs nobody puts in the demo

Guardrails are not free, and honest engineering means budgeting for their downsides.

**Latency and cost.** Each safety-model rail is an *extra inference call*. An input rail plus an output rail plus a groundedness check can triple the number of model calls per request, and the user waits for all of them (unless you run some in parallel). A hosted moderation API adds a network round-trip; a self-hosted classifier adds GPU time you pay for. This forces a real prioritization: decide *which* rails matter for *this* application rather than bolting on all of them. A public-facing chatbot needs strong content-safety rails; an internal tool behind SSO might need only a PII output rail and a groundedness check.

**The gotcha:** every rail is a model call, so latency and cost scale with how many you stack — you cannot afford "all rails on everything." Choose deliberately: put the expensive groundedness check only on RAG answers, run cheap regex/PII rails on every request, and consider running independent rails concurrently so the user waits for the slowest, not the sum. Rails are a budget you spend, not a checkbox you tick.

**False positives are a product problem.** A rail that blocks a legitimate request produces a refusal the user didn't deserve. Enough of those and people route around your product entirely. This is why the "safe refusal" in the pipeline above should be helpful and honest — tell the user what happened and offer a path forward — and why you should log every block and review the false-positive rate like any other quality metric.

| Rail | Typical check | Block vs transform | Watch out for |
|---|---|---|---|
| Input: injection | jailbreak/injection classifier | block | novel attacks (false negatives) |
| Input: PII | Presidio detect + mask | transform | over-redaction breaking the request |
| Input: topical | on-topic classifier | block | legitimate edge-case questions |
| Output: safety | Llama Guard / moderation API | block | latency; miss rate on subtle harm |
| Output: PII / secrets | detector on the response | transform | secrets in formats you didn't model |
| Output: groundedness | RAG faithfulness check | block/flag | cost; strictness vs. useful answers |

---

## Key takeaways

- **Guardrails screen the two ends of the pipe.** Input rails block or sanitize what reaches the model; output rails block or sanitize what reaches your application. Groundedness checks are the output rail that defends RAG against hallucination.
- **They're a layer, not a fix.** Rails stack on top of least-privilege tools and untrusted-output handling from post 4 — they lower the *probability* of a successful attack; least-privilege lowers its *blast radius*. You need both.
- **Every rail is a classifier with two failure modes.** False positives annoy real users; false negatives let harm through. There's no threshold that removes both — measure each on your own data and tune per risk.
- **Rails cost latency and money.** Each is an extra model call, so choose which rails matter for your application rather than enabling all of them, and parallelize where you can.
- **A blocked response is its own state.** Model the outcome as a tagged result, branch on it, log which rail fired, and give the user an honest refusal — don't let a refusal masquerade as a normal answer.
- **Use the ecosystem.** Safety classifier models (Llama Guard, Granite Guardian, ShieldGemma), programmable frameworks (NeMo Guardrails, Guardrails AI, Presidio for PII), and hosted moderation (OpenAI, Azure AI Content Safety) each cover part of the job. Confirm exact APIs against current docs — they change.

---

## Further reading

- [Llama Guard model card and docs (Meta / Llama)](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/)
- [IBM Granite Guardian (GitHub)](https://github.com/ibm-granite/granite-guardian)
- [ShieldGemma (Google, on Hugging Face)](https://huggingface.co/google/shieldgemma-2b)
- [NeMo Guardrails (NVIDIA, GitHub)](https://github.com/NVIDIA/NeMo-Guardrails)
- [Guardrails AI documentation](https://www.guardrailsai.com/docs)
- [Microsoft Presidio (PII detection and de-identification)](https://microsoft.github.io/presidio/)
- [OpenAI moderation guide](https://platform.openai.com/docs/guides/moderation)
- [Azure AI Content Safety documentation](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/)
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/)
