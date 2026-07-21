# Callbacks in Google ADK: Six Hooks and One Rule

*before/after the agent, model, and tool steps — and the single short-circuit rule that turns them into guardrails*

---

Most of what you'll ever bolt onto a production agent — a safety guardrail, a token counter, a response cache, a PII redactor — is not agent logic. It's *cross-cutting* logic that needs to run at a fixed moment in the agent's lifecycle without you editing the agent itself. Google's [Agent Development Kit](https://google.github.io/adk-docs/) exposes exactly those moments as **callbacks**: six hooks arranged as three before/after pairs around the agent, the model, and each tool. Learn the one rule that governs all six and you've learned the whole system.

## The six hooks

They come in pairs, one on each side of a lifecycle step:

| Hook | Fires | Returning a value… |
|------|-------|--------------------|
| `before_agent` | before the agent runs at all | short-circuits the entire agent |
| `after_agent` | after the agent finishes | replaces the final output |
| `before_model` | before each LLM call | **skips the model** (guardrail / cache) |
| `after_model` | after each LLM response | rewrites or inspects the response |
| `before_tool` | before each tool call | **skips the tool** (block / cache) |
| `after_tool` | after each tool call | rewrites the tool result |

The order they fire in is exactly the order you'd guess: user message → `before_agent` → `before_model` → *(model)* → `after_model` → `before_tool` → *(tool)* → `after_tool` → `after_agent` → response. A `before_*` hook sits *in front of* its step and can veto it; an `after_*` hook sits behind it and can edit what came out.

## The one rule

Every callback obeys a single contract:

> **Return nothing to proceed. Return a value to short-circuit.**

Return `None` (Python) or `nil` (Go) and the lifecycle continues normally. Return a *value* of the right type and ADK stops, skips the step, and uses your value instead. That's it. This one mechanism is why a guardrail and a cache are the same shape of code: a `before_model` callback that returns an `LlmResponse` means "don't call the model — use this." Whether "this" is a canned refusal (a guardrail) or a stored answer (a cache) is up to you.

## A `before_model` guardrail

Here is the canonical use: scan the outgoing prompt and, if it contains something disallowed, return a refusal so the model is never called. Keeping the decision logic in small pure helpers is deliberate — it makes the guardrail trivially unit-testable without a model or an API key.

```python
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

BLOCKED = "password"
REFUSAL = "I can't help with sharing passwords."

def request_text(req: LlmRequest) -> str:
    """Concatenate all user-visible text in a request."""
    parts = []
    for content in req.contents or []:
        for part in content.parts or []:
            if part.text:
                parts.append(part.text)
    return " ".join(parts)

def guardrail(ctx: CallbackContext, req: LlmRequest) -> Optional[LlmResponse]:
    if BLOCKED in request_text(req).lower():
        return LlmResponse(                       # <- short-circuit: model skipped
            content=types.Content(role="model", parts=[types.Part(text=REFUSAL)])
        )
    return None                                   # <- proceed to the model

root_agent = LlmAgent(
    name="guarded_agent",
    model="gemini-flash-latest",
    instruction="You are a helpful assistant. Answer general questions.",
    before_model_callback=guardrail,
)
```

Ask *"what's the admin password?"* and the callback returns the refusal — the model is never touched. Ask *"what's the capital of France?"* and it returns `None`, so the request flows through to Gemini as normal.

The Go form is the same shape. The callback signature is a plain function, and callbacks are attached as a **slice** on the agent's config:

```go
import (
    "google.golang.org/genai"
    "google.golang.org/adk/v2/agent"
    "google.golang.org/adk/v2/agent/llmagent"
    "google.golang.org/adk/v2/model"
)

const (
    blocked = "password"
    refusal = "I can't help with sharing passwords."
)

func requestText(req *model.LLMRequest) string {
    var b strings.Builder
    for _, c := range req.Contents {
        for _, p := range c.Parts {
            if p.Text != "" {
                b.WriteString(p.Text)
                b.WriteByte(' ')
            }
        }
    }
    return strings.TrimSpace(b.String())
}

// nil, nil => proceed; a response => skip the model.
func guardrail(_ agent.Context, req *model.LLMRequest) (*model.LLMResponse, error) {
    if strings.Contains(strings.ToLower(requestText(req)), blocked) {
        return &model.LLMResponse{
            Content: &genai.Content{Role: "model", Parts: []*genai.Part{{Text: refusal}}},
        }, nil
    }
    return nil, nil
}

// ... llmagent.New(llmagent.Config{
//         Name: "guarded_agent", Model: m,
//         BeforeModelCallbacks: []llmagent.BeforeModelCallback{guardrail},
//     })
```

## Python vs Go: the one cosmetic difference

The semantics are identical across both SDKs, down to the short-circuit rule. The only real difference is how you *attach* callbacks:

- **Python** accepts either a single callable or a list: `before_model_callback=guardrail` or `before_model_callback=[profanity, pii, cache]`.
- **Go** always takes a slice: `BeforeModelCallbacks: []llmagent.BeforeModelCallback{profanity, pii, cache}`.

When you pass several, ADK runs them **in order until one returns a value** — first hit wins, the rest are skipped. So composing independent guardrails is just list ordering: a profanity check, then a PII check, then a cache lookup, stacked front to back. Go additionally exposes `OnModelErrorCallbacks` and `OnToolErrorCallbacks` for the failure path — e.g. supply a fallback response when the model errors.

## Mental model

Think of the six hooks as a **pipeline with tap points**, and each callback as a valve: it can watch what flows past (logging, metrics), edit it (`after_*` rewriting a response or tool result), or close the valve and inject its own value (`before_*` returning something). Because a `before_model` guardrail is a *pure function of the request* — no model, no I/O — you should treat it like the safety-critical code it is and unit-test every rule. Both languages' guardrail tests here run in milliseconds with no credentials.

The common patterns all fall out of the same six hooks:

- **Guardrail** — `before_model` / `before_tool` returns a refusal or blocked result.
- **Cache** — `before_model` returns a stored `LlmResponse` for a repeated prompt.
- **Metrics** — `after_model` / `after_tool` records tokens, latency, outcomes.
- **Response shaping** — `after_model` redacts PII or enforces a format.

**Next in the series:** the Runner and event loop that actually *fire* these callbacks — the runtime that turns your agent definition into a running conversation.
