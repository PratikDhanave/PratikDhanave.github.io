# Most-Restrictive-Wins: Composing Two Layers of Policy
*An agent can tighten a workload's policy, or claim a tool the workload never mentioned — but it can't loosen an explicit forbid. Here's the resolution rule.*

In a governed multi-agent system I built on the Microsoft Agent Framework (Python), every tool call passes through authorization before it executes. The wrinkle that made this interesting: authorization is not one decision, it's two. Each call is evaluated against a workload-scoped policy `(workload_id, tool)` *and* an agent-scoped policy `(agent_id, tool)`. Each scope independently resolves to one of four verdicts: `allow`, `require_approval`, `read_only`, or `forbid`. Then the two verdicts have to be composed into a single effective decision.

The moment you have two policy layers, you have a composition problem, and composition is where home-grown agent authorization quietly goes wrong. Get the rule right and you get delegation without privilege escalation. Get it wrong and a "specialist" sub-agent silently out-privileges the workload that spawned it.

## Two scopes, one decision

The mental model is a hierarchy: the workload is the *team* charter, the agent is an *individual member*. A workload might be broadly allowed to touch a `search` tool, a `write_record` tool, and a `send_email` tool. Within that workload, a summarizer agent has no business sending email, and a triage agent should be able to *read* records but never write them. The agent scope exists to express exactly those per-member narrowings.

Crucially, the two scopes are not symmetric peers that vote. They stack. The workload sets a ceiling (and sometimes a floor); the agent operates inside it. The resolution rule is **most-restrictive-wins**, with a rank order:

```
forbid  >  read_only  >  require_approval  >  allow
(most restrictive)                    (least restrictive)
```

Compose by taking the max on that scale — almost. The "almost" is the whole point of this post, and it's the case everyone botches.

## The one distinction that matters: forbid vs. silence

Here is the subtlety. A workload verdict of `forbid` and a workload that simply *has no entry* for a tool are not the same thing, even though a naive implementation collapses both to "not allowed."

- An **explicit `forbid`** is a deliberate floor. Someone wrote it down. It means "no agent under this workload may ever touch this tool." A tighter layer cannot cross it.
- **Silence** (no `(workload_id, tool)` row at all) is an *absence*, not a denial. It carries no intent. It's a gap the more specific layer is allowed to fill.

This is standard IAM discipline — an explicit `Deny` outranks everything, but the *absence* of an `Allow` is just an implicit deny that a more specific grant can satisfy. AWS-style policy has drawn this line for years. Yet in agent systems I keep seeing both cases mapped to a single boolean, which forces you to pick one broken behavior: either silence hard-blocks (and you can never grant an agent a capability the workload didn't pre-enumerate) or explicit forbid becomes loosenable (and your floor leaks).

So the actual rules are four:

1. **An agent can TIGHTEN.** Workload says `allow`; agent says `require_approval` or `forbid` → the stricter agent verdict wins.
2. **An agent can fill a SILENCE.** Workload has *no entry*; agent says `allow` → effective `allow`. Silence is not a hard deny, so the agent layer may add the tool.
3. **An agent CANNOT loosen an explicit FORBID.** Workload says `forbid`; agent says `allow` → effective `forbid`. The floor holds.
4. **`agent_id=""` reproduces workload-only behavior.** The empty agent scope is a no-op layer — it contributes nothing, so the effective decision is exactly the workload verdict. This is the compatibility escape hatch: existing callers that never learned about agents keep working unchanged.

## The full truth table

Spelling out workload verdict × agent verdict → effective decision. `∅` means the workload is silent (no entry).

```
                          AGENT SCOPE
                 allow   approval  read_only  forbid   (none/"")
              +--------------------------------------------------+
   allow      | allow   approval  read_only  forbid    allow     |
WL  approval  | approv. approval  read_only  forbid    approval  |
    read_only | read_o. read_only read_only  forbid    read_only |
    forbid    | FORBID  FORBID    FORBID     forbid    forbid     |  <- floor
    ∅ (none)  | allow   approval  read_only  forbid    DENY*      |
              +--------------------------------------------------+

  * ∅ × none  = deny: neither layer ever granted the tool.
  Read every cell as: max(workload, agent) on the restrictiveness scale,
  EXCEPT the ∅ row, where the agent verdict passes through unclamped
  because there is no workload ceiling to clamp against.
```

Two rows carry the whole design. The `forbid` row is flat — every cell is `forbid`, including the one where the agent says `allow`. That flatness *is* the floor. The `∅` row is the opposite: the agent verdict passes straight through, because there's no ceiling to enforce, only a gap to fill. Everywhere else it's a plain max.

## Resolving it in code

The generic shape, stripped of the surrounding framework:

```python
RANK = {"allow": 0, "require_approval": 1, "read_only": 2, "forbid": 3}
INV = {v: k for k, v in RANK.items()}

def resolve(workload, agent):
    # workload / agent are a verdict string or None (silent / no entry)
    if workload == "forbid":
        return "forbid"                 # explicit floor: cannot be loosened
    if workload is None:                # silence: agent layer may fill it
        return agent or "deny"          # no entry anywhere -> deny
    if agent is None:                   # agent_id="" -> workload-only behavior
        return workload
    return INV[max(RANK[workload], RANK[agent])]   # most-restrictive-wins
```

Note the ordering of the guards. `forbid` is checked *before* silence and before the generic max, so nothing downstream can talk it out of the floor. That's not incidental — it's the invariant the whole scheme rests on.

## Attribution is not containment

One caveat I'll be blunt about, because conflating these two is its own common mistake. This layered policy is **app-layer attribution**: it decides whether a call is permitted and the audit log records *which agent acted* — the `agent_id`, not just the workload, is stamped on every decision. That gives you per-agent accountability and least-privilege *intent*.

It is not the containment boundary. If an agent is compromised, an app-layer policy check running in the same process is inside the blast radius. Real containment lives one level down — a distinct cloud identity per agent, so the tool's own IAM refuses the call regardless of what the app believes. Keep the two ideas in separate boxes: policy composition buys you *least privilege and clean attribution*; per-agent identity buys you *isolation*. You need both, and neither substitutes for the other.

## Why it matters

Layered policy is how real authorization scales: org → team → agent, or here workload → agent. But layers only compose *safely* under most-restrictive-wins, and most-restrictive-wins only works if you refuse to conflate an explicit forbid with an absence. Nail that one distinction and the net guarantee falls out for free: a specialist agent can be strictly more constrained than its workload, or fill a gap the workload never spoke to — but it can never, ever loosen a floor someone deliberately laid down. That's delegation without privilege escalation, and it's the property you actually want when you start handing tools to a swarm of agents.
