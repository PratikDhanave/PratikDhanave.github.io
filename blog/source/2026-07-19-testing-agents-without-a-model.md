# Testing Agents Without a Model
*The full pipeline should run in CI with zero API keys and zero network. A deterministic classifier is the test double that makes an agentic system testable.*

"Agents are untestable." I have heard this on every team that ships an LLM-driven system, and it is almost always wrong. What people actually mean is: "We wired our orchestration directly to a live model, so now every test needs an API key, a network round trip, and a coin flip on whether the assertions pass." That is not a property of agents. That is a design mistake, and it is fixable.

I built a governed multi-agent system for operational incident triage on the `Microsoft Agent Framework` in Python on Azure. The orchestration is a multi-stage pipeline: `triage → enrich → diagnose → approval → close`. Each phase can consult a function-calling agent, hit a policy gateway, suspend for human approval, and checkpoint its state. That is a lot of orchestration surface, and none of it is interesting to test through a live model. The model's job is to classify and draft text. The pipeline's job is to route, gate, suspend, resume, and serialize correctly. Those are different concerns, and they deserve different test strategies.

## Put the seam at the classifier

The single decision that makes the whole system testable is this: every phase does not call a model. It calls a `Router` interface that decides which route the phase takes. There are two implementations behind that interface. One is a live function-calling agent that asks the model. The other is a deterministic keyword classifier that maps input text to a route with a lookup table — no API key, no network, no tokens.

```
                       ┌──────────────────────────┐
   incident text ─────▶│   Router  (interface)    │
                       │   classify(text) -> Route │
                       └──────────────────────────┘
                             ▲                ▲
              provider=real  │                │  provider=<anything else>
                             │                │
             ┌───────────────┴─────┐   ┌──────┴─────────────────────┐
             │  LiveModelRouter    │   │  KeywordRouter             │
             │  function-calling   │   │  deterministic lookup      │
             │  agent, tokens, net │   │  $0, no tools, no model    │
             └─────────────────────┘   └────────────────────────────┘
                                              ▲
                                              │  exercised end-to-end
                       ┌──────────────────────┴───────────────────────┐
                       │  CI: triage→specialist→…→documentation        │
                       │  policy gateway · suspend/resume · checkpoint │
                       │  httpx ASGITransport in-process · 0 API keys  │
                       └───────────────────────────────────────────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/testing-agents-without-a-model.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Both implementations satisfy the same interface and return the same `Route` type. The pipeline downstream cannot tell them apart — and that is the entire point. When tests run, the `KeywordRouter` is the active implementation, so the pipeline executes its real routing, gating, and checkpoint logic against a classifier that behaves identically every single time.

## Selection is config-driven, not code-driven

Which router you get is a normalization step at startup, not a branch scattered through the codebase. If a real model provider is configured, you get the live agent. Any other value normalizes to the deterministic path. Nothing downstream inspects the environment.

```python
def build_router(config) -> Router:
    provider = (config.model_provider or "").strip().lower()
    if provider in {"azure_openai", "openai"}:
        return LiveModelRouter(config)      # tokens, network, real classification
    return KeywordRouter()                  # deterministic, $0, offline
```

The default in CI is "no provider configured," so CI gets the deterministic path automatically. A developer who exports a real endpoint gets the live path with zero code changes. The model has become a swappable dependency, selected the same way you would select a database driver — not a hard prerequisite baked into the call sites.

## A deterministic runner serves canned plans

The classifier decides the route; a deterministic runner executes it. For every known route, the runner serves a canned plan — the sequence of phase transitions and the shape of each phase's output — with no tool calls and no model invocation. This is what makes an end-to-end pipeline test cost `$0` and finish in milliseconds. The plan for "database connection pool exhausted" is fixed: it triages to the data-tier specialist, escalates to engineering, proposes a documented remediation, and writes the incident record. The test asserts the transitions, the gateway verdicts, and the serialized checkpoint — all deterministic, all reproducible.

This is also where human-in-the-loop gets tested honestly. The pipeline suspends at the approval gate, the runner serializes a checkpoint, the test deserializes it and resumes with a canned "approved" decision, and the pipeline continues. No model, no server, no clock dependency — just the suspend/resume machinery under test.

## API tests call FastAPI in-process

The HTTP layer gets the same treatment. The integration tests do not spin up a live server and poll a port. They mount the FastAPI app and call it through `httpx` with an `ASGITransport`, so requests travel in-process straight to the ASGI handler. Combined with the deterministic router, a test can `POST` an incident, walk the whole pipeline, and assert the final JSON — with no network sockets opened anywhere. The result is a hermetic suite: the same inputs produce the same outputs on a laptop, in CI, and on a machine with no internet at all.

## Reserve the model for a separate eval gate

None of this means you never test against the real model. It means you stop conflating two questions. "Does the orchestration route, gate, suspend, and serialize correctly?" is a deterministic question — answer it in CI, for free, on every push. "Does the model classify this incident well enough?" is a statistical question — answer it in a separate eval gate that runs on a schedule or before release, with real credentials and quality thresholds, where a little nondeterminism is expected and measured rather than asserted.

Keeping those gates separate is what keeps CI fast and trustworthy. Your unit and integration suite never flakes because a model had an off day, and your eval suite never gets diluted with plumbing assertions that a keyword table already covers.

## Why it matters

The label "untestable" is a self-inflicted wound. Couple your orchestration to a live model and every test inherits the model's cost, latency, and nondeterminism. Put the seam at the classifier — one interface, a deterministic implementation for tests, the live agent for production and evals — and the orchestration becomes ordinary software: fast to test, cheap to run, reproducible byte-for-byte. The model stops being a prerequisite for your test suite and becomes what it always should have been: a dependency you can swap out. Build the seam first, before the pipeline grows, and you will never have to argue that your agents are untestable again.
