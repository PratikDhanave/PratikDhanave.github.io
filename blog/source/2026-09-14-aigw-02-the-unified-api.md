# The Unified API

*The first thing an AI gateway gives you is one interface to every model. Instead of your applications learning each provider's SDK, request format, and quirks, they speak a single API and the gateway translates. That translation layer is what decouples your code from any one vendor — and it's what makes model-swapping a config change instead of a rewrite.*

The previous post named the unified API as the gateway's foundational capability. This post is about what it actually does: present one consistent interface to applications, translate to each provider's native format, and normalize the differences between them. It sounds simple, and the core is, but the value is large — it's what turns "we're locked into vendor X" into "we can use any model."

## The problem: every provider is different

Model providers expose different APIs. They differ in:
- **Request and response shapes** — the JSON structure of messages, parameters, and outputs varies.
- **Authentication** — different key schemes and headers.
- **Parameter names and semantics** — what one calls `max_tokens` another may name or bound differently; sampling parameters vary.
- **Features** — tool/function calling, structured output, streaming, and multimodal inputs are expressed differently, when supported at all.
- **Error formats** — each returns errors in its own structure with its own codes.

If your applications call providers directly, they must encode all these differences. Using two providers means two integrations; switching means a rewrite; and every app repeats the work. Your code becomes coupled to specific vendors at a deep level.

## The solution: one interface, gateway translates

A unified API fixes this by giving applications **a single, provider-agnostic interface**. The app makes one kind of call — typically an OpenAI-compatible chat-completions request, since that shape has become a de-facto standard many tools speak — and the gateway does the translation:

1. The app sends a request in the unified format, naming a model (`gpt-...`, `claude-...`, `gemini-...`, or a self-hosted model).
2. The gateway maps that to the *target provider's* native request format, auth, and parameters.
3. It calls the provider, receives the native response, and **translates it back** into the unified response format.
4. The app gets a consistent response regardless of which provider served it.

The application never sees the provider's specifics. It knows models by name and speaks one dialect; the gateway absorbs every difference behind that dialect. This is the classic *adapter* pattern applied across providers — one interface, many backends.

## What this decouples

The payoff is **decoupling your applications from any specific model provider**, which has compounding benefits:

- **Model-swapping is a config change.** Switch an app from one model to another — even across providers — by changing the model name in configuration, with no code change. This is enormous: it lets you adopt a better or cheaper model the day it appears, A/B test models, or migrate off a provider, all without touching application code.
- **Multi-provider is trivial.** Use different models for different tasks (a cheap model for classification, a strong one for reasoning) through the same interface, and mix providers freely.
- **No vendor lock-in at the code level.** Your business logic depends on "a model," not on "OpenAI's SDK." The dependency is on the gateway's stable interface, not a vendor's.
- **New providers integrate once.** When a new provider or model appears, you add one adapter in the gateway, and *every* application can use it immediately — versus updating every app.

This is the same benefit the framework-agnostic and model-agnostic designs elsewhere in AI engineering chase, delivered at the infrastructure layer: your code targets a stable abstraction, and the churn of the provider landscape stays behind it.

## The hard parts of translation

The unified API's core is straightforward, but honest engineering acknowledges where it's tricky:

- **Feature mismatch.** Providers don't support the same features. If the unified API exposes tool calling but a target model doesn't support it, the gateway must handle the gap — emulate it, degrade gracefully, or error clearly. The abstraction can only cleanly cover the *intersection* of features; beyond that, it must make deliberate choices.
- **Parameter normalization.** Mapping parameters across providers isn't always one-to-one — ranges and meanings differ, so the gateway normalizes as best it can and must be transparent about what it can't map exactly.
- **Response and streaming normalization.** Providers stream tokens and structure responses differently; the gateway must present a consistent streaming interface and response shape over varied backends.
- **Staying current.** Providers change their APIs and ship new models; the gateway's adapters must keep up. This maintenance is real, but it's *centralized* — done once in the gateway rather than in every app, which is the whole point.

The key trade-off to understand: a unified API is a **lowest-common-denominator-plus** abstraction. It cleanly covers what providers share and makes explicit choices about what they don't. That's a worthwhile trade — you accept a small amount of abstraction leakiness at the edges in exchange for decoupling all your applications from all your providers. When you need a truly provider-specific feature, good gateways provide a pass-through, so the abstraction helps by default without trapping you.

## Key takeaways

- Providers differ in request/response shapes, auth, parameter names/semantics, feature support, and error formats — so direct integration couples every app to specific vendors and makes switching a rewrite.
- A **unified API** gives applications one provider-agnostic interface (commonly OpenAI-compatible, a de-facto standard); the gateway **translates** to each provider's native format and back, so the app never sees provider specifics — the adapter pattern across providers.
- The payoff is **decoupling apps from any provider**: model-swapping becomes a *config change* (adopt better/cheaper models instantly, A/B test, migrate — no code change), multi-provider is trivial, there's no code-level lock-in, and a new provider integrates *once* for all apps.
- The hard parts are **translation at the edges**: feature mismatch (the abstraction cleanly covers the *intersection*; gaps need emulation/graceful-degradation/clear errors), parameter and streaming normalization, and keeping adapters current — but this maintenance is *centralized* in the gateway, not repeated per app.
- A unified API is a **lowest-common-denominator-plus** abstraction — clean for shared features, explicit about differences, with a pass-through for truly provider-specific needs — a worthwhile trade for decoupling all apps from all providers.

## Further reading

- [LiteLLM — one interface to 100+ LLMs](https://docs.litellm.ai/)
- [OpenRouter — unified API across providers](https://openrouter.ai/docs)
