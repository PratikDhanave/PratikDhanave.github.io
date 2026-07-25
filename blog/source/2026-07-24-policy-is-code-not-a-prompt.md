# Policy Is Code, Not a Prompt
*Prompt injection can hijack what a model says, but not what it's allowed to do — as long as policy lives in a middleware pipeline the model never sees.*

There is a comfortable lie in a lot of agent architectures: that you can write "you must never delete production records" at the top of a system prompt and call it a security control. You can't. A system prompt is advice. The model is free to ignore it, and an attacker with a well-crafted input can convince it to. If your access control lives inside the same text stream the model reads, you have handed the enforcement of your security policy to the least trustworthy component in the system.

I learned to take this seriously while building a governed multi-agent system — an operational incident-triage platform where autonomous agents call real tools against real infrastructure. The design principle that made it defensible is boring and absolute: **policy is code, enforced out-of-band, in a place the model cannot reach.**

## The model is untrusted input

Start from the right threat model. A large language model consuming a stream of tickets, logs, alerts, and third-party payloads is processing attacker-controllable data on every turn. Prompt injection is not an edge case; it is the default condition of any agent that reads from the outside world. So the correct mental posture is the one every backend engineer already knows: **treat everything the model emits as untrusted input, and validate it at a trust boundary the caller does not control.**

That reframing does something clarifying. It means the interesting question is not "can the model be tricked into *trying* something bad?" — assume yes, always. The question is "when it tries, what actually happens?" If the answer depends on the model having behaved, you have no control. If the answer depends on code the model never executes, you do.

## The Governed Gateway

In the platform I built, every tool call — without exception — passes through what we called the Governed Gateway: a composable middleware pipeline that intercepts the call before it reaches any tool implementation. For each `(workload_id, tool_name)` pair it resolves exactly one decision: `allow`, `require_approval`, `read_only`, or `forbid`. The model does not see this decision, does not participate in it, and cannot influence it. It emits an intent; the gateway disposes.

Here is the shape of it. Note where the trust boundary sits.

```
              UNTRUSTED                    │           TRUST BOUNDARY
                                           │
  ┌─────────┐   emits tool-call intent     │   ┌──────────────────────────────┐
  │   LLM   │ ───────────────────────────► │   │       Governed Gateway       │
  │ (agent) │   {tool, args, workload_id}  │   │   (composable middleware)    │
  └─────────┘                              │   └──────────────────────────────┘
       ▲                                   │                 │
       │  tool result OR                   │      ┌──────────▼───────────┐
       │  policy denial                    │      │ 1. AGT  (governance) │──deny─┐
       └───────────────────────────────────│──────│ 2. ContentSafety     │       │
                                           │      │ 3. CostCap           │       │
                                           │      │ 4. Policy (OPA/Rego) │──forbid┤
                                           │      │ 5. ComplianceTag     │       │
                                           │      │ 6. PII redaction     │       ▼
                                           │      │ 7. Audit             │   short-circuit
                                           │      │ 8. CircuitBreaker    │   (no tool run)
                                           │      └──────────┬───────────┘
                                           │                 │ allow
                                           │           ┌─────▼─────┐
                                           │           │   Tool    │
                                           │           └───────────┘
```

The stages run in a deliberate order. Agent-governance (AGT) runs **first** and short-circuits on deny — if this workload isn't allowed to act at all, nothing downstream even executes. Then ContentSafety, CostCap, Policy, ComplianceTag, PII redaction, Audit, and CircuitBreaker. Policy is the stage that resolves the `(workload_id, tool_name)` decision, backed by code and OPA/Rego rules. Audit records the attempt — allowed or not — because a blocked malicious call is exactly the event you most want in your logs.

The middleware pattern matters here beyond tidiness. Each stage is independent and composable, so you reason about, test, and evolve one concern at a time. A change to cost caps cannot accidentally weaken content safety. And because interception is universal, there is no code path that "forgets" to check — the gateway is the only door.

## Why prompt injection stops being an access-control problem

This is the payoff, and it's worth stating precisely: **prompt injection is irrelevant to access control in this design.**

Injection is real and it works — it can change what the model *outputs*. A malicious ticket can absolutely convince an agent to *try* to call a destructive tool, with attacker-chosen arguments, while narrating a perfectly plausible justification. All of that is downstream of the model, and all of it is untrusted. When that call arrives at the gateway, the Policy stage evaluates `(workload_id, "delete_records")`, finds `forbid`, and short-circuits. The tool never runs. The model's eloquence, its confidence, the clever story in the ticket — none of it is an input to the decision.

The attacker got to play in the model's sandbox. They never got near the control. That is the entire point of putting enforcement out-of-band: you move it somewhere the attack surface does not extend.

Contrast this with the common anti-pattern — encoding guardrails as prose in the prompt and hoping for compliance:

```python
# Anti-pattern: the "policy" is a suggestion inside the attacker's reach.
SYSTEM_PROMPT = "You are a helpful agent. You must NEVER delete records."

# The control: policy is code, evaluated where the model can't reach.
def gateway(workload_id: str, tool_name: str, args: dict) -> Decision:
    decision = policy.evaluate(workload_id, tool_name)   # OPA/Rego + code
    if decision is FORBID:
        audit.record(workload_id, tool_name, blocked=True)
        raise PolicyDenied(tool_name)                     # tool never runs
    return decision
```

The first version asks the model to enforce your security against inputs specifically designed to subvert the model. The second doesn't ask the model anything.

## Fail-closed, or don't bother

One detail separates a real control from theater: the default. In the gateway, a tool with **no policy entry is denied** — not allowed. Fail-closed. When someone registers a new tool, it is locked until an explicit policy grants access to specific workloads. The failure mode of forgetting to write a rule is "the tool doesn't work," which is loud and gets fixed, rather than "the tool works for everyone," which is silent and gets exploited.

Fail-open defaults are how systems that *look* governed quietly aren't. Every new capability that lands without a corresponding rule becomes an ungoverned hole. Inverting the default means your blast radius only ever grows by deliberate, reviewable decisions.

This post is about *where* you enforce policy. For how you author it, I've written separately on [keeping policy as code you don't redeploy to change](/blog/posts/policy-as-code-without-shipping-code.html) and [treating the policy as a reviewable YAML file the board can read](/blog/posts/the-board-policy-is-a-yaml-file.html) — the placement argument here is what makes those authoring choices safe.

## Why it matters

Every serious agent system eventually has to answer one question: when the model is wrong — because it was fooled, or jailbroken, or simply confused — does anything bad actually happen? If your answer lives in the system prompt, you don't have an answer; you have a hope, and you're pinning it on the exact component an attacker gets to manipulate. Move the enforcement out-of-band, into a fail-closed middleware pipeline the model never sees, and the question resolves itself: the model can be as wrong as it likes, and the forbidden call still doesn't run. A prompt is advice. A middleware pipeline is a control. Build the thing that can't be talked out of anything.
