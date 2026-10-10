# Governing Agentic AI — When the Model Can Act

*Governing a model that answers questions is hard; governing one that takes actions is a different problem entirely. Agentic AI — systems that plan, call tools, and execute steps toward a goal with limited human oversight — moves AI from producing outputs to producing consequences. The governance frameworks built for predictive models and even for chatbots don't fully cover an agent that can send an email, move money, or modify a system. This post is about the controls that specifically matter when AI can act.*

Posts 1–2 built the operating model and model-risk discipline for AI systems in general. This post addresses the hardest and newest frontier: **agentic** systems. The core shift is that a wrong answer from a chatbot is contained in the conversation, but a wrong *action* from an agent escapes into the world — so governing agents is less about output quality and more about *bounding authority and consequences*.

## Why agents break the usual frameworks

An **agent** is an AI system that pursues a goal through a loop of reasoning and *acting* — choosing and invoking tools, taking steps, observing results, and continuing — with meaningfully less step-by-step human control than a chatbot. That autonomy creates governance problems the earlier frameworks weren't built for:

- **Actions have consequences that outlast the session.** A hallucinated sentence is embarrassing; a hallucinated *action* — a wrong payment, a deleted record, a sent message — is real-world harm that can't be un-said. Governance must shift focus from "is the output correct?" to "what is this system *allowed to do*, and what happens when it does the wrong thing?"
- **The behavior space is combinatorial and emergent.** An agent composes tools and steps in ways its builders didn't enumerate, so you can't pre-test every path. Multi-agent systems compound this — emergent interactions between agents produce behavior no single agent's design predicts.
- **Prompt injection becomes an action exploit.** For a chatbot, a hijack (from the [LLMOps series](/blog/series/llmops-in-practice/)) produces bad text; for an agent with tools, a malicious instruction hidden in a web page or document can make the agent *act* — exfiltrate data, make purchases, invoke privileged tools. The attack surface now reaches the agent's authority.
- **Accountability blurs.** When an autonomous system takes a harmful action, who's responsible — the user who set the goal, the builder, the tool provider? Agentic governance has to assign accountability *before* the action, not litigate it after.

The unifying point: autonomy and authority are the risk, and they scale together. The more an agent can do without a human, the more governance it needs — so the first governance question for any agent is simply *how much authority does this actually need?*

## The controls that bound an acting system

Governing agents is primarily about **constraining authority and consequences**, through controls layered around the agent:

- **Least privilege for tools and data.** Give the agent exactly the tool permissions and data access its task requires, and no more — scoped, revocable, and audited. If an agent only needs to read, it can't delete; if a hijack occurs, the blast radius is bounded by what the agent was ever allowed to do. This is the single most important agentic control, and it's classic security discipline applied to AI authority.
- **Human-in-the-loop for consequential actions.** Define which actions require human approval before execution — irreversible, high-value, or high-impact ones — so autonomy is granted for the routine and withheld for the dangerous. The autonomy spectrum (assistive → approval-gated → fully autonomous) should be set *per action type by stakes*, not globally.
- **Bounded execution.** Limit what an agent can do in one run: step/iteration caps, spending limits, rate limits, timeouts, and sandboxing of any code execution. These prevent a confused or hijacked agent from doing unbounded damage while looping — "exhausted is not failure" is a feature, not a bug.
- **Confirmation, reversibility, and dry-runs.** Prefer reversible actions, stage changes for review, and let agents propose-then-execute so a human or a guardrail can catch a bad plan before it lands.
- **Identity and authorization for agents.** An acting agent needs its own identity and permissions (not a borrowed human's), so its actions are attributable and its access governable like any other principal — increasingly a first-class part of agent architecture.

Across all of these, the principle is **fail-safe**: when an agent is uncertain or a guardrail trips, the safe default is to stop and ask, not to act. Containing an autonomous system means designing so that the *worst case* is bounded, because you cannot enumerate every path it will take.

## Observability and accountability for actions

Because you can't pre-verify every path, agentic governance leans heavily on *seeing and accounting for* what agents actually do:

- **Full action audit trails.** Log every action an agent takes, with the reasoning/plan that led to it, the tools invoked, and the results — so a harmful action can be reconstructed, attributed, and learned from (this is the tracing from the LLMOps series, extended to *actions*, and it's also the evidence a regulator or incident review needs).
- **Runtime guardrails on actions, not just text.** Check proposed *actions* against policy before execution (post 4's policy-as-code is how), block disallowed ones, and escalate the ambiguous — the action-layer guardrail is the one that matters most for agents.
- **Clear accountability mapping.** Decide and document, per agent and per action class, who is accountable — which ties agent governance back to the operating model's ownership (post 1). An autonomous system still has a human owner answerable for it.
- **Monitoring for emergent and anomalous behavior.** Watch for agents doing unusual things — unexpected tool sequences, scope creep, runaway loops — because the risks you didn't anticipate show up in production behavior first.

The throughline: agentic AI moves governance from *managing outputs* to *bounding authority and consequences*, because an agent's mistakes are actions in the world, its behavior is emergent and un-enumerable, and prompt injection becomes an action exploit. The controls are therefore about limiting what the agent *can* do — **least privilege**, **human-in-the-loop for consequential actions**, **bounded execution**, **reversibility**, and **agent identity** — all defaulting to **fail-safe**, backed by **action-level audit trails, runtime action-guardrails, clear accountability, and anomaly monitoring**. The question that opens all of it is the discipline's core: *how much authority does this agent actually need?* — and the answer should always be the least that lets it do the job.

## Key takeaways

- An **agent** pursues goals through a loop of reasoning and *acting* (tool calls, steps) with reduced human control — so a wrong *action* is real-world harm that outlasts the session, unlike a chatbot's wrong text; governance shifts from "is the output correct?" to "what may it do, and what if it does the wrong thing?"
- Agents break earlier frameworks via **consequential actions**, **combinatorial/emergent behavior** (can't pre-test every path; multi-agent compounds it), **prompt injection as an action exploit** (a hijack now *acts* — exfiltrates, buys, invokes privileged tools), and **blurred accountability** (assign it *before* the action).
- The core controls **bound authority and consequences**: **least privilege** for tools/data (the single most important — bounds blast radius; classic security applied to AI authority), **human-in-the-loop for consequential actions** (set the autonomy level per action by stakes), **bounded execution** (step/spend/rate caps, timeouts, sandboxing), **reversibility/confirmation/dry-runs**, and **agent identity** (own permissions, attributable).
- Default to **fail-safe**: when uncertain or a guardrail trips, stop and ask — because you can't enumerate every path, design so the *worst case* is bounded.
- Lean on **seeing and accounting**: **action audit trails** (actions + the reasoning behind them), **runtime guardrails on actions** (policy-as-code, post 4), **clear accountability** back to an owner (post 1), and **anomaly monitoring** for emergent behavior — the first question for any agent is *how much authority does it actually need?* (answer: the least that does the job).

## Further reading

- [Software agent — autonomous goal-directed systems](https://en.wikipedia.org/wiki/Software_agent)
- [AI safety — controlling autonomous and powerful AI systems](https://en.wikipedia.org/wiki/AI_safety)
