# Safety & Security in Google ADK: Defense in Depth

*Stack the guardrails — callbacks, model filters, restricted tools, and clean-room sandboxing — so that if one layer misses, the next one catches*

---

Safety is not a feature you switch on. It is a *stack* of independent layers, each one covering the failures the others miss. A prompt-injection guardrail can be phrased around; a model's built-in content filter is generic and doesn't know your business rules; a tool guardrail can be misconfigured. None of these is sufficient alone — but layered, a request has to slip past every one of them to do harm. Google's [Agent Development Kit](https://google.github.io/adk-docs/) gives you a hook at every stage of the agent lifecycle (the callbacks from the previous post) plus model-level and identity controls, so you can build defense in depth without leaving the framework.

## The layers

Trace a single request from input to reply and drop a guard at each stage:

| Layer | Control | Stops |
|-------|---------|-------|
| Input guardrail | `before_model` callback | prompt injection, disallowed asks |
| Model safety settings | `safety_settings` on the gen config | harmful content categories |
| Tool guardrail | `before_tool` callback | dangerous tool calls (destructive args) |
| In-tool validation | a check *inside* the tool function | out-of-policy actions the callback missed |
| Identity / least privilege | scoped tool credentials | over-broad access if a tool is abused |
| Output filter | `after_model` callback | leaking PII / secrets in the reply |

The callback layers all obey the one short-circuit rule from the callbacks post: a `before_*` callback that returns a value **skips** its step; an `after_*` callback that returns a value **replaces** the output. Safety guardrails are just callbacks with a safety job.

## Two guardrails, both pure functions

The load-bearing insight: keep the *decision* logic pure — plain functions of strings and dicts, no framework, no model — and let the callback be a thin adapter. Safety code is exactly what you want fast, exhaustive, offline unit tests around.

An **output redactor** masks PII before the user ever sees it (`after_model`), and a **dangerous-tool blocker** refuses destructive calls before they run (`before_tool`):

```python
import re
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
DANGEROUS = ("rm -rf", "drop table", "sudo", "; rm", "mkfs", "> /dev/")

def redact_pii(text: str) -> str:                      # pure, unit-tested
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return PHONE_RE.sub("[REDACTED_PHONE]", text)

def is_dangerous_tool_call(name: str, args: dict) -> bool:
    return any(isinstance(v, str) and any(p in v.lower() for p in DANGEROUS)
               for v in args.values())

def redact_output_callback(callback_context, llm_response):  # after_model
    for part in (llm_response.content.parts if llm_response.content else []):
        if part.text:
            part.text = redact_pii(part.text)
    return llm_response

def block_dangerous_tool_callback(tool, args, tool_context):  # before_tool
    if is_dangerous_tool_call(tool.name, args):
        return {"status": "blocked", "reason": "Refused: destructive arguments."}
    return None                                          # None → proceed
```

The Go form is the same shape — pure helpers wrapped by callbacks whose signatures return `(value, error)`, where returning a non-nil value short-circuits:

```go
func blockDangerousTool(_ agent.Context, t tool.Tool, args map[string]any) (map[string]any, error) {
    if IsDangerousToolCall(t.Name(), args) {
        return map[string]any{"status": "blocked", "reason": "Refused: destructive arguments."}, nil
    }
    return nil, nil // nil → proceed
}
```

Wire both onto the agent. In Python they're single keyword args; in Go they're slices, so you can stack several callbacks per hook:

```python
LlmAgent(name="safe_agent", model="gemini-flash-latest",
         instruction=SAFETY_CONSTITUTION, tools=[apply_discount],
         after_model_callback=redact_output_callback,
         before_tool_callback=block_dangerous_tool_callback)
```

```go
llmagent.New(llmagent.Config{
    Name: "safe_agent", Model: m, Instruction: SafetyConstitution,
    AfterModelCallbacks: []llmagent.AfterModelCallback{redactOutput},
    BeforeToolCallbacks: []llmagent.BeforeToolCallback{blockDangerousTool},
})
```

## Guard the tool from the inside

The `before_tool` callback lives *outside* the tool and can be misconfigured, bypassed, or simply forgotten the next time you add a tool. So validate business limits *inside* the tool function too. The callback is defense in *breadth*; the in-tool check is defense in *depth* — the last line where a destructive or expensive action still can't execute, no matter which layer let it through:

```python
MAX_DISCOUNT_PCT = 20.0

def apply_discount(order_id: str, discount_pct: float) -> dict:
    if not 0 <= discount_pct <= MAX_DISCOUNT_PCT:
        return {"status": "rejected", "reason": "discount outside allowed range"}
    return {"status": "applied", "order_id": order_id, "discount_pct": discount_pct}
```

The check is identical in Go; only the wiring differs — Python registers the plain function and ADK infers the schema, while Go wraps it with `functiontool.New[Args, Result]` over a typed args struct.

## Model safety settings

Underneath your callbacks, Gemini can filter broad harm categories at the source. Configure it on the generation config — coarse and provider-managed, catching the obvious cases so your app-specific callbacks handle the rest:

```python
types.GenerateContentConfig(safety_settings=[
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)])
```

```go
&genai.GenerateContentConfig{SafetySettings: []*genai.SafetySetting{{
    Category: genai.HarmCategoryDangerousContent,
    Threshold: genai.HarmBlockThresholdBlockMediumAndAbove}}}
```

Model filters and your callbacks are *different* layers, both worth running: the model's filters catch generic harm; your callbacks encode *your* PII patterns, blocked tools, and compliance rules.

## Restrict tools and identity

The safest tool is the one an abused agent can't reach. Callbacks can't save you from an over-privileged credential — so:

- Give each tool the **minimum** credentials it needs. Never hand an agent your admin key.
- Use tool **auth** so sensitive tools acquire scoped credentials at call time.
- Require **human-in-the-loop** approval for irreversible, high-blast-radius actions.
- Keep an **isolated identity per user/session** so one user can't reach another's data by construction.

A guardrail that redacts a leaked secret is good; not giving the tool access to the secret in the first place is better.

## Sandbox untrusted actions with a clean-room Runner

When you invoke an **untrusted or under-test** agent, give it a throwaway `Runner` plus a fresh `InMemorySessionService` *per invocation* so it shares zero session, state, or memory with the caller. A new session service each call mimics a stateless API request — nothing leaks in, nothing leaks out:

```python
session_service = InMemorySessionService()   # fresh per call — nothing carries over
runner = Runner(agent=untrusted, app_name="sandbox", session_service=session_service)
```

Go expresses it identically with `session.InMemoryService()` and a per-call `runner.New(...)`. Contrast this with `AgentTool` (which shares the caller's whole invocation context — right for *trusted* sub-agents) and `include_contents='none'` (which drops prompt history but still shares state). The clean room shares **nothing** — that's the point.

> **Mental model.** Every layer is a filter with holes. Input guardrail, model filter, tool guard, in-tool check, least privilege, output filter, sandbox — line them up and a malicious request must find a hole through *all* of them. That's defense in depth: not one perfect wall, but seven imperfect ones.

For compliance beyond your code, GCP adds managed layers *around* the agent — **Model Armor** (a `model_armor_config` naming server-side prompt/response screening templates on Vertex AI) and **VPC Service Controls** (a network perimeter that keeps agent traffic inside a trusted boundary even with valid credentials). Neither is an ADK API; both are platform controls you enable outside the code.

**Next in the series:** Protocols — MCP and A2A, where connecting external tool servers and other agents opens each a new trust boundary this defense-in-depth mindset applies to.
