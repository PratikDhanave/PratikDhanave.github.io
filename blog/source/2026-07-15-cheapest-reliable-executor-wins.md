# The Cheapest Reliable Executor Wins
*Deterministic rules get first refusal at zero model cost. Only the unknown cases escalate to graduated AI agents. A human approves anything that mutates.*

I built a governed multi-agent system for operational incident triage — Microsoft Agent Framework, Python, Azure — and the whole thing turns on a single sentence I kept repeating in design reviews: **the cheapest reliable executor always wins.**

That principle is deliberately hostile to the default 2026 instinct, which is to pipe every event straight into an LLM and let the model figure it out. That instinct is expensive and, worse, it's fragile. An LLM is the most capable rung of your system and also the most fallible and the most costly per invocation. Reaching for it first is like paying a senior consultant to answer "is the disk full?" — a `df -h` and a threshold would have told you for free, and it would have told you even during an outage when your consultant is unreachable.

So I didn't build an agent that triages incidents. I built a ladder, and the model is near the top of it.

## First refusal goes to code that costs nothing

The bottom rung is a set of **deterministic rules**: pure standard-library Python, no model call, no agent-framework import anywhere in that module. Every incoming event hits this tier first and gets **first refusal**. If a rule matches, the event is handled right there — diagnosis, classification, recommended action — at **$0** and at effectively 100% reliability.

The rules are an ordered list, and **list order is priority order**: first match wins. That's not a limitation I tolerated, it's a property I wanted. Priority becomes something you can read top-to-bottom in one file, diff in a pull request, and reason about without simulating a model's judgment. There's no temperature, no token budget, no "it usually classifies this correctly." A known pattern gets a known response.

```python
def deterministic_triage(event):
    for rule in RULES:            # list order == priority order
        if rule.matches(event):
            return rule.handle(event)   # $0, no model, always available
    return ESCALATE               # only the unknown long tail gets here
```

> **▸ [Open the interactive diagram](/blog/diagrams/cheapest-reliable-executor-wins.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The reason this rung matters more than any other is subtle: **it still fires when the model is down.** Azure OpenAI throttling you? Rate limit hit? Regional blip? The deterministic tier does not care, because it never depended on the model in the first place. That tier is your **reliability floor** — the set of behaviors the system guarantees under total AI failure. If disk-full, cert-expiry, and known-flapping-service incidents are covered by rules, then those incidents get triaged during the exact conditions (a broad outage) when your model provider is most likely to be degraded too. You do not want your incident system's availability correlated with the thing that's on fire.

## The escalation ladder

Only **unmatched** events climb. And they climb one rung at a time, each rung more capable and more expensive than the last.

```
                        EVENT
                          │
                          ▼
        ┌──────────────────────────────────┐
        │  0. DETERMINISTIC RULES           │
        │     first-match-wins, list order  │
        │     $0 · no model · always up     │◄── reliability floor
        └──────────────────────────────────┘
              │ match → handle at $0 ─────────────► DONE
              │
              │ no match → escalate
              ▼
        ┌──────────────────────────────────┐
        │  1. AGENT TRIAGE (cheap model)    │
        │     diagnose → propose → document │
        └──────────────────────────────────┘
              │ confident → proposal
              │
              │ novel / low-confidence → escalate
              ▼
        ┌──────────────────────────────────┐
        │  2. SPECIALIST (capable model)    │
        │     graduated model class         │
        │     deeper reasoning, more $      │
        └──────────────────────────────────┘
              │
              │ proposes an action that MUTATES
              ▼
        ┌──────────────────────────────────┐
        │  H. HUMAN-IN-THE-LOOP APPROVAL    │
        │     explicit sign-off required    │
        └──────────────────────────────────┘
              │ approved
              ▼
                       EXECUTE
```

Rung 1 is **agent triage** on a cheap model: it diagnoses the event, proposes an action, and documents its reasoning. Most of what escapes the rules gets resolved here — these are novel-ish but not genuinely hard. Rung 2 is a **specialist** on a more capable, more expensive model class, invoked only when triage is out of its depth. This is a **model cascade** — none → cheap → capable — where each event is handled by the least capable model that can actually handle it.

The economics of this are lopsided in your favor. Operational incidents follow a brutal power law: a handful of patterns account for the overwhelming majority of volume. Rules eat that fat head at $0. The cheap model handles the shoulder. The capable model touches only the genuinely novel long tail — which is exactly where its cost is justified, because that's the only place its capability is required.

## Nothing mutates without a human

Every rung above produces a **proposal**, not an action. The moment a proposed action would **mutate** anything — restart a service, scale a pool, flip a flag, touch a record — the workflow **pauses for explicit human approval** before it executes.

This is the deliberate seam between "thinking is cheap and reversible" and "acting is expensive and not." I let models diagnose freely; diagnosis is read-only and wrong diagnoses cost tokens, not incidents. But side effects go through a person. The human-in-the-loop rung is not a nod to compliance theater — it's the acknowledgement that a confidently-wrong model executing an irreversible action is the single worst outcome an ops system can produce, and it's cheaply prevented by making the model ask first.

## Two architectures wearing one trench coat

What I like most about this design is that it's simultaneously a **cost-governance** architecture and a **reliability** architecture, and it didn't require choosing between them.

As cost governance: you never pay model tokens for a problem a rule could solve, and you never pay capable-model tokens for a problem a cheap model could solve. Spend graduates with genuine difficulty.

As reliability: the tier that handles the most volume is the tier with zero external dependencies, so your busiest path is also your most available path. Capability and availability run in opposite directions up the ladder, and that's fine, because volume runs down it.

Note this is a different axis from latency- or budget-based dispatch — routing by SLA or by a token allowance. Those are real and complementary; I've written about [cost-aware agent dispatch](/blog/posts/cost-aware-agent-dispatch.html) on its own terms. The claim here is narrower and, I think, more foundational: **rules first, then graduate.** Sort your executors by cost-times-fallibility and always try the cheapest reliable one first.

## Why it matters

Do not make an LLM your first executor. It is the expensive, fallible rung — save it for when the cheap rungs genuinely can't cope, and keep a deterministic rung underneath that keeps the system alive when the model isn't. Build the ladder: rules, cheap model, capable model, human. Let each rung handle only what the rung below couldn't. You'll spend a fraction of the tokens, you'll survive your provider's bad days, and the one time a model wants to do something irreversible, a person will be standing at the top of the ladder saying "not yet."
