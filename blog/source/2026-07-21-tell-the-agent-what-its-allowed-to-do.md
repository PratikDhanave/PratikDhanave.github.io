# Tell the Agent What It's Allowed to Do
*If your gateway will block a tool call, don't make the agent discover that by trying. Hand it a capabilities brief and stop paying for turns it can't complete.*

I built a governed multi-agent system for operational incident triage — a set of specialist agents on the Microsoft Agent Framework, Python, running on Azure. Every tool call, from every agent, passes through a policy gateway before it executes. The gateway answers one question for a `(workload, tool)` pair: `allow`, `require_approval`, `read_only`, or `forbid`. That gateway is the control. It is the thing an auditor points at. It is non-negotiable.

And for the first few weeks, it quietly cost me money on every incident.

## The failure mode nobody flags

The gateway works. That was never in question. The problem is subtler and it only shows up in your token bill and your latency graphs, not your error logs.

A specialist agent — say the one that owns network remediation — gets a task. The model reasons about what it needs. It decides to call `restart_service`. The gateway looks up `(network_remediation, restart_service)`, sees `forbid`, and returns a block. The framework hands that block back to the model as a tool result. The model, now mildly confused, reasons again, tries `drain_node`. Blocked. Tries `open_change_ticket`. Blocked. Eventually it stumbles onto `read_interface_status`, which is `read_only` and allowed, and gets on with its life.

Nothing broke. The guardrails held perfectly. But you just paid for three model turns whose entire content was the agent negotiating with a wall it couldn't see. Multiply that by every specialist, every incident, every shift.

```
WITHOUT capabilities brief
---------------------------
 task ──► [model turn 1] ──► call restart_service
                                   │
                              ┌────▼────┐
                              │ GATEWAY │  (network_remediation, restart_service) = forbid
                              └────┬────┘
                                   ▼  BLOCK  ($ + tokens spent)
          [model turn 2] ──► call drain_node
                                   │
                              ┌────▼────┐
                              │ GATEWAY │  = forbid
                              └────┬────┘
                                   ▼  BLOCK  ($ + tokens spent)
          [model turn 3] ──► call read_interface_status
                                   │
                              ┌────▼────┐
                              │ GATEWAY │  = read_only -> allow
                              └────┬────┘
                                   ▼  OK   (finally — after 2 wasted turns)

WITH capabilities brief
-----------------------
 task + brief ──► [model turn 1] ──► call read_interface_status
                                          │
                                     ┌────▼────┐
                                     │ GATEWAY │  = read_only -> allow
                                     └────┬────┘
                                          ▼  OK   (first try)
```

The model wasn't being dumb. It was being blind. It had no way to know its own permissions, so its only discovery mechanism was to try things and read the rejections. That is the most expensive possible way to learn a config file.

## The fix: hand the model its own permissions

The policy set already exists — it has to, because the gateway reads it. So the information the model needs is sitting right there at construction time. The fix is to stop hiding it.

When policies are passed to the agent factory, each specialist gets a **capabilities brief** appended to its system instructions. It's a generated markdown list of exactly the tools that agent's policy permits, with approval-gated tools flagged and forbidden tools simply omitted. No forbidden tool ever appears — not even to say "you can't use this." If the model never reads the name, it never reaches for it.

```python
def capabilities_brief(policies: dict[str, str]) -> str:
    lines = []
    for tool, decision in sorted(policies.items()):
        if decision == "forbid":
            continue                       # omit — don't advertise the wall
        note = " (requires approval)" if decision == "require_approval" else ""
        note = " (read-only)" if decision == "read_only" else note
        lines.append(f"- `{tool}`{note}")
    if not lines:
        return ""                          # best-effort: no brief, no change
    return "## Tools you are permitted to use\n" + "\n".join(lines)
```

That's the whole idea. It gets appended to the instructions the specialist already has. The result is that turn one, the model reaches for a tool that's actually allowed, because it can see the menu instead of guessing at it.

## Two things this is not

It is worth being blunt about the boundaries, because it's easy to oversell this.

**This is not a security control.** Deleting the forbidden tools from the brief does not remove them from the runtime. If the model hallucinates `restart_service` anyway — and models do — the gateway still catches it and still returns `forbid`. The brief is advisory; the gateway is enforcement. I keep those two facts strictly separate in my head, and so should you. The day you start treating the prompt as the boundary is the day you get owned.

**This is not required for correctness.** The system was already correct without it. It was just wasteful. The brief is a cost-and-latency optimization that happens to also make traces far easier to read, because agents stop generating turns full of doomed tool calls.

It is also strictly best-effort. If the policy map is empty, `capabilities_brief` returns an empty string and the instructions are left untouched. There is no code path where a missing or malformed brief degrades safety, because safety was never living in the brief. Worst case, you're back to the blind-probing behavior you started with.

## The real principle: enforcement and self-understanding must agree

Here's the framing that made this click for me. A governed agent has two representations of what it can do. One lives in the enforcement layer — the gateway's policy table. The other lives in the model's head — whatever it infers about its own abilities from its instructions and its history.

When those two representations disagree, the model fights the guardrails. Every disagreement is paid for at least once, per round, in tokens and wall-clock latency, as the model rediscovers a boundary you already knew about at build time. Security-by-blocking is necessary — you cannot trust the model's self-image as a control. But blocking alone, with a blind model, is necessary *and* wasteful.

The capabilities brief is alignment in the plain, mechanical sense of the word: you make the model's self-understanding match the enforcement layer's ground truth. Same source of truth, two consumers. The gateway reads the policy to enforce; the factory reads the same policy to inform. When they converge, the model stops probing and starts working inside the lines on the first try.

## Why it matters

Blocking a bad tool call protects you. Making the agent *discover* the block by trying is a tax you pay on every incident, forever, for information you already had. If your enforcement layer knows the answer at construction time, tell the model the answer at construction time. Keep the gateway as the wall — but stop charging yourself full price to teach the agent where the wall is.
