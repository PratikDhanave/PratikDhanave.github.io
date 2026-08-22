# Testing and Evals

*Most agent code is tested by running it and eyeballing the output — because testing agents properly is genuinely hard. Pydantic AI's whole design has been quietly building toward making it easy: type safety, dependency injection, and test models combine so you can unit-test agent logic deterministically, offline, without ever calling a real LLM. This is arguably the framework's biggest practical advantage.*

Everything so far — typed outputs, dependency injection, explicit messages — has been setting up this post. **Testing** LLM agents is notoriously difficult, and Pydantic AI is unusually good at it, which for production applications may be its most important strength. This post covers why agents are hard to test, how Pydantic AI makes them testable (test models plus injected dependencies), and how that extends to *evals* — measuring agent quality. Testable agents are the difference between hoping your agent works and knowing it does.

## Why testing agents is hard

Agents resist normal testing for two reasons, both of which Pydantic AI's design addresses:

- **They call unpredictable, slow, costly models.** A real LLM gives different outputs run to run, takes real time, and costs money per call — so tests that hit a real model are non-deterministic, slow, and expensive. You can't build a fast, reliable test suite on top of real model calls.
- **They reach into real systems.** Agents use tools that touch databases, APIs, and services — so testing them naively means touching those real systems, making tests fragile and side-effectful.

Together these push most teams to "test" agents by running them manually and eyeballing results — which doesn't scale, doesn't catch regressions, and isn't real testing. To test agents properly, you need to remove *both* problems: replace the real model with something deterministic, and replace the real systems with fakes. Pydantic AI provides exactly those two capabilities.

## Test models: agents without a real LLM

Pydantic AI provides **test models** — stand-ins for a real LLM that let you run an agent *without calling any model API*. These come in forms suited to different testing needs:

- **A test model** that returns canned or simple generated responses (and calls the agent's tools) without a real LLM — so you can exercise the agent's *logic* deterministically and offline.
- **A function model** where *you* supply a function that plays the model's role — giving you full control to script exactly what "the model" does at each step, so you can test specific scenarios (the model calls this tool, then returns this output).
- **Overriding the model** on an existing agent for the duration of a test — so you test your *real* agent (its tools, prompts, dependencies, output type) with a fake model substituted in.

The key insight: because Pydantic AI agents are model-agnostic (the first post), swapping in a test model is natural — the agent doesn't care which model backs it. This removes the first testing problem: with a test model, agent tests are **deterministic, fast, and free** (no real API calls), so you can run them in CI on every change like any other unit test. You're testing your agent's *logic* — does it call the right tools, construct prompts correctly, produce the right typed output shape — separately from the model's unpredictable *content*.

## Dependency injection completes it

Test models remove the real-LLM problem; **dependency injection** (from its own post) removes the real-systems problem. Because an agent's dependencies are injected, you inject *fakes* in tests — a fake database, a stub API client, a fixed user — so the agent's tools run against test doubles instead of real systems:

```python
# Illustrative shape — see the Pydantic AI docs for exact API.
def test_recent_orders():
    fake_deps = Deps(db=FakeDB(orders=[...]), user_id=1)
    with agent.override(model=TestModel()):          # no real LLM
        result = agent.run_sync("my orders", deps=fake_deps)  # no real DB
    assert isinstance(result.output, OrdersReport)   # typed assertion
    assert result.output.count == 3
```

With both substitutions in place — **test model + injected fakes** — you can test an agent end-to-end with no real model and no real systems: fully deterministic, fast, offline, and side-effect-free. And because outputs are *typed* (structured outputs), your assertions are clean and precise — you assert on typed fields (`result.output.count == 3`), not by parsing strings. This is the culmination of the whole framework's design: type safety gives you assertable typed outputs, dependency injection gives you fake systems, and model-agnosticism gives you fake models — the three together make agents genuinely unit-testable, which is rare in the agent world.

## From testing to evals

Unit testing (does the agent's logic work?) is distinct from **evaluation** (is the agent's *quality* good?) — the eval discipline that runs through the AI production, RAG, and fine-tuning series. Both matter, and Pydantic AI's testability supports both:

- **Testing** verifies deterministic *logic*: given this input and these (fake) dependencies, does the agent call the right tools and produce the right output *structure*? Fast, deterministic, run in CI on every change — a regression safety net.
- **Evaluation** measures *quality* against real (or realistic) models: given real inputs, is the agent's output actually *good* — correct, helpful, accurate? This needs real models (or careful judges) and representative datasets, and it's about performance, not logic-correctness.

Pydantic AI supports evals (including tooling in the ecosystem for evaluating agent outputs), and the same principles from the earlier series apply: build a dataset of representative cases, run the agent against them, and score the outputs (with metrics, LLM-as-judge, or human review), so you can measure quality and catch regressions in *behavior*, not just logic. The typed outputs help here too — scoring structured outputs is more precise than scoring free text.

The practical division: use fast deterministic *tests* (test model + fakes) to guard logic on every change, and periodic *evals* (real models, real datasets) to measure and track quality. Together they give agents the same engineering rigor as any critical system — which, given how unpredictable LLMs are, is exactly what production agents need.

## Testability as a first-class advantage

The theme of this post, and much of the series: Pydantic AI treats **testability as a first-class design goal**, and its other features (typing, DI, model-agnosticism) exist partly to enable it. In a field where "testing" usually means manual eyeballing, the ability to write real, deterministic, CI-runnable tests for agents is a genuine competitive advantage — it's what lets you refactor confidently, catch regressions, and build agents you *trust*. If you're choosing an agent framework for a production application where reliability matters, this testability is one of the strongest reasons to pick Pydantic AI. The final post covers taking that tested agent to production.

## Key takeaways

- Agents are hard to test because they call unpredictable/slow/costly models and reach into real systems — pushing most teams to manual eyeballing instead of real tests; proper testing requires removing both problems.
- Test models (a canned test model, a function model you script, or overriding the model) let you run an agent with no real LLM — deterministic, fast, and free — testing the agent's *logic* (right tools, right output structure) apart from the model's unpredictable content; model-agnosticism makes this natural.
- Dependency injection removes the real-systems problem: inject fake dependencies (fake DB, stub client) so tools run against test doubles — combined with a test model, you get fully deterministic, offline, side-effect-free end-to-end agent tests.
- Typed (structured) outputs make test assertions clean and precise (assert on typed fields, not parsed strings) — so type safety + DI + model-agnosticism together make agents genuinely unit-testable, which is rare.
- Testing (deterministic logic, in CI on every change) is distinct from evals (quality against real models/datasets, scored with metrics/judges/humans); use both, and Pydantic AI's testability — a first-class design goal — is one of its strongest reasons for production use.

## Further reading

- [Messages, history, and streaming (previous post)](/blog/posts/pydai-06-messages-history-streaming.html)
- [Pydantic AI documentation — testing and evals](https://ai.pydantic.dev/)
- [The AI Production Roadmap — evaluation in depth](/blog/series/the-ai-production-roadmap/)
