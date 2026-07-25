# Give Every Agent Its Own Credential
*In a multi-agent system, a shared identity means one compromised agent carries every agent's blast radius. Here's how I split agent identity across three layers.*

Most multi-agent applications ship with exactly one identity: the process. The whole app authenticates to the cloud as a single workload, and every specialist agent inside it — the one that reads network telemetry, the one that reboots hardware, the one that talks to the help-desk ticketing system — borrows that one credential. It's convenient. It's also the single worst decision you can make for blast radius.

I learned this building a governed multi-agent operational incident-triage platform on the Microsoft Agent Framework (Python) and Azure. Several specialist agents cooperate to diagnose and remediate incidents. Once you accept that any one of them can be prompt-injected, buggy, or fed a hostile tool response, the question stops being "will an agent misbehave" and becomes "when one does, how much can it touch." The honest answer for a single-identity app is: everything. So I gave every agent its own identity — across three complementary layers, each buying something the others cannot.

## The three layers at a glance

```
                     WHAT AN AGENT "IS" — THREE LAYERS
  ┌──────────────────────────────────────────────────────────────┐
  │ Layer 3 · CRYPTO      signed per-agent token (PyJWT / HS256)  │
  │   buys: NON-REPUDIATION — provable actor (issuer + jti)       │
  │   fails at: containment (in-process key)                      │
  ├──────────────────────────────────────────────────────────────┤
  │ Layer 2 · CLOUD       one Azure user-assigned managed         │
  │                       identity PER agent                      │
  │   buys: CONTAINMENT — least-privilege RBAC, enforced by AAD   │
  │   survives: application compromise                            │
  ├──────────────────────────────────────────────────────────────┤
  │ Layer 1 · APP         agent_id threaded through the gateway   │
  │   buys: POLICY resolution + AUDIT attribution                 │
  │   fails at: containment (only as honest as the process)       │
  └──────────────────────────────────────────────────────────────┘
     Layer 1 says who claims to act · Layer 2 limits what they can
     do · Layer 3 proves who actually did it.
```

These are not redundant. They answer three different questions — *who claims to act*, *what can they actually do*, and *who provably did it* — and the mistake is thinking any one of them covers the others.

## Layer 1: the app-layer `agent_id`

Every tool call in the system flows through a gateway pipeline, and the first thing I thread through it is an `agent_id`. It does two jobs.

First, **policy resolution**. Policy isn't only a property of the workload; it's a property of the agent. The `agent_id` lets an agent *tighten* the workload default — a diagnostic agent that never needs to write can be pinned read-only — or be *granted* a tool the workload policy is silent on, so the network agent gets a topology-read tool the help-desk agent will never see. Resolution is agent-scoped, not global.

Second, **audit attribution**. Every audit record names the agent that acted. When you're reconstructing an incident afterward, "the app did X" is useless; "the hardware agent issued a reboot at 03:14" is the whole story.

But be clear about what this layer is *not*. An app-layer id is only as trustworthy as the process holding it. If an attacker is executing inside your process, they can set `agent_id` to anything. Layer 1 is **attribution, not containment**. It tells you what an honest process claims. It does nothing against a dishonest one — and that's fine, because that's Layer 2's job.

## Layer 2: one managed identity per agent (the real boundary)

This is where containment actually lives. Each agent gets its own **Azure user-assigned managed identity**, and a selector resolves the right credential at call time.

```python
def credential_for_agent(agent_id: str) -> Credential:
    # Prefer a per-agent managed identity, by convention:
    client_id = os.environ.get(f"AGENT_MI_CLIENT_ID_{agent_id.upper()}")
    if client_id:
        return ManagedIdentityCredential(client_id=client_id)
    # Fall back to a shared workload identity, then local dev.
    if shared := os.environ.get("AGENT_MI_CLIENT_ID_SHARED"):
        return ManagedIdentityCredential(client_id=shared)
    return DefaultAzureCredential()  # local developer login
```

The precedence matters. A per-agent client id (via `AGENT_MI_CLIENT_ID_<AGENT>`) wins; absent that, a shared client id; absent *that*, local developer credentials so the thing still runs on a laptop. The fallbacks keep the system runnable in every environment without weakening production, where the per-agent variables are always set.

The critical, deliberate part is the RBAC. Each managed identity gets its **own role assignments as an explicit deploy-time step** — the hardware agent's identity can restart the machines it owns and nothing else; the help-desk agent's identity can touch tickets and nothing else. It would be far easier to hand every identity one broad role and move on. That's exactly the trap: a broad grant reproduces the single-identity problem under prettier names. Least-privilege is only real if someone assigns narrow privileges on purpose.

What this buys you is the property no in-process mechanism can: it is **enforced by Azure AD and survives application compromise**. If an agent is hijacked, the attacker still authenticates as *that agent's* managed identity and can reach only what its RBAC allows. The blast radius collapses from "every resource the app can touch" to "the resources of one role." The boundary is outside your process, so your process being owned doesn't dissolve it.

## Layer 3: signed per-agent tokens for non-repudiation

Containment tells you an attacker *couldn't* do more than a role allows. It doesn't give you a cryptographically provable record of who acted. That's Layer 3.

Each agent signs a per-agent token — PyJWT, HS256 — and the audit trail records the **verified issuer and token id (`jti`)**. Now an audit entry isn't just "the network agent claims it acted"; it's "a token cryptographically issued by the network agent's key, id `jti=…`, authorized this action." That's **non-repudiation**: a provable actor, not an asserted one.

And again, the boundary of the claim: an in-process signing key gives you non-repudiation, **not containment**. Anyone who can run code in the process can sign. So Layer 3 does not replace Layer 2 — it complements it. Layer 2 gives you least-privilege enforced from outside; Layer 3 gives you a provable actor recorded inside. Least-privilege *and* provable actor. You want both, because they fail in different directions.

## Why split identity at all

The default architecture — one workload identity for the whole app — quietly couples every agent's authority together. A prompt-injected planning agent, or a plain bug in a tool wrapper, inherits the union of every agent's permissions. The compromise of the weakest agent is the compromise of the strongest.

Per-agent identity breaks that coupling three ways at once. The `agent_id` makes policy and audit agent-specific, so you can reason about one agent at a time. The per-agent managed identity turns a compromise into a bounded incident — one role's worth of damage, enforced by the cloud rather than your own code. The signed token makes the audit trail something you can stand behind in a post-incident review instead of a set of unverifiable log lines.

Outside Azure, the same containment idea shows up as [SPIFFE/SPIRE workload identity](/blog/posts/spiffe-spire-workload-identity-basics.html); and per-agent identity is only one layer of a broader [defence-in-depth for agentic systems](/blog/posts/defence-in-depth-for-agentic-ai.html).

**Why it matters:** identity is the cheapest lever you have on blast radius, and almost everyone leaves it at its worst setting. One workload identity means the worst-behaved agent defines your worst day. Give every agent its own credential — attributed at the app, contained by the cloud, proven by crypto — and the worst-behaved agent can only ever cost you a single role, on a trail you can prove. That's the difference between an incident and a breach.
