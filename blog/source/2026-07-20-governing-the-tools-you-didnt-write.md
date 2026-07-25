# Governing the Tools You Didn't Write
*An autonomous agent injects its own plan-and-execute tools at runtime. If your gateway is fail-closed, you have to find and allowlist them — deliberately.*

Most tool-governance stories are about the tools you can see. You enumerate the functions your agents can call, you write a policy row for each `(workload, tool)` pair, and you route every invocation through a gateway that checks that row before the call executes. Clean. Auditable. The kind of thing you put in a compliance deck.

Then you turn on an autonomous harness and your neat model springs a leak — not because the gateway is weak, but because some of the tools don't exist yet when you write the policy.

## The setup: a gateway as function middleware

In a governed multi-agent system I built on the Microsoft Agent Framework (Python), every tool call passes through a single choke point. The framework exposes a function-invocation layer — middleware that fires on *each* tool call, wrapping the actual function execution. My gateway lives there. Before any function runs, the middleware looks up a policy entry keyed by `(workload, tool)`, decides allow or deny, and either proceeds or raises.

Crucially, the default is **fail-closed**. No matching policy row means *deny*. I did not want an "allow unless explicitly blocked" posture, because that quietly trusts anything new. Fail-closed means the blast radius of a forgotten policy row is a blocked call and a loud error — not a silent, ungoverned execution.

That default is the whole point of this post. It is also what nearly broke the harness.

## The twist: tools injected at runtime

Some specialist agents don't just answer — they run as an autonomous harness: a function-calling loop with a plan/execute mode. To support that mode, the harness needs its own control surface. A mode provider hooks into the agent lifecycle via a `before_run` hook and calls `context.extend_tools(...)`, injecting a small pair of control tools — call them `mode-set` and `mode-get` — so the model can switch between planning and executing.

These tools are not in my source tree's tool registry. They are conjured at runtime, per run, by the provider. And here is the property that matters:

Because the gateway is middleware on the function-invocation layer, it fires on *these* calls too. Runtime injection does not smuggle a tool past the gateway. The middleware sees `mode-set` and `mode-get` exactly like it sees a hand-registered tool.

Which sounds like good news until you remember the default. These injected tools carry no `(workload, tool)` policy entry — I never wrote one, because I never saw them at build time. So they hit the fail-closed default and get **blocked**. The harness tries to set its own mode, the gateway denies it, and the autonomous loop dies on the first control call.

```
                        build-time tools            runtime-injected tools
                        (in the registry)           (mode provider .before_run
                                                     -> context.extend_tools)
                              |                             |
   agent decides to call  ───┤                             ├── mode-set / mode-get
                              v                             v
              ┌───────────────────────────────────────────────────────┐
              │        function-invocation middleware (gateway)         │
              │  look up policy for (workload, tool) on EVERY call      │
              └───────────────────────────────────────────────────────┘
                              |
              ┌───────────────┴───────────────┐
        policy row exists?               no row found
              |                                |
        allow / deny                    ── FAIL-CLOSED default ──┐
        per policy                                               |
              |                          internal-tools allowlist?
              v                          (mode-set, mode-get)    |
        [ execute ]                        yes ──> [ execute ]   |
                                            no  ──> [ BLOCKED ]  |
                                                          (unknown tool
                                                           surfaces loudly)
```

The diagram is the argument. Both tool origins converge on one middleware. The fail-closed default is the net that catches everything without a policy row. And the only sanctioned way through, for a tool that legitimately has no external side effect, is an explicit internal-tools allowlist.

## The fix: enumerate, then allowlist deliberately

The remedy is not to weaken the default. It is to *name the exceptions*.

I added an internal-tools allowlist: a short, explicit set of tool names that the gateway treats as pre-approved regardless of the `(workload, tool)` policy table. Right now it holds exactly the confirmed pair, `mode-set` and `mode-get`. They qualify because I could reason about them concretely: they mutate in-process harness state, they call no network, they touch no store, they have no external side effect. Allowlisting them is a decision I can defend in a review, not a blanket "trust the harness."

```python
INTERNAL_TOOLS = frozenset({"mode-set", "mode-get"})

async def gateway(context, next_):
    name = context.function.name
    if name in INTERNAL_TOOLS:          # known-safe, no external side effect
        return await next_(context)
    policy = lookup(context.workload, name)
    if policy is None:                  # fail-closed: unknown => deny
        raise ToolBlocked(name)
    if not policy.allowed:
        raise ToolBlocked(name)
    return await next_(context)
```

Two things make this honest rather than a loophole. First, the allowlist is a fixed set of *names I have personally verified*, not a pattern like `mode-*` that would auto-bless whatever the provider decides to inject next release. Second, I hardened the surrounding surface so fewer surprise tools can appear at all: on specialist agents I **disabled the built-in web-search and memory tools**. Those framework built-ins would otherwise show up as ungoverned callables the moment an agent reached for them. Turning them off means the only runtime-injected tools in play are the ones I deliberately went looking for.

## The caveat I'm not going to paper over

There is a second provider in the system — a todo provider — that also injects tools at runtime. I have *not* allowlisted its tools, and I'm not going to until I've done a live run and read the actual injected names off the wire.

This is the uncomfortable, correct part: you cannot allowlist what you have not observed. Guessing the names from the provider's source is not enumeration; a rename or a wrapper changes the string the middleware actually sees. Until that live-run enumeration happens, those tools stay subject to the fail-closed default — which means any specialist that triggers them will get a visible block, not a silent bypass. That is exactly the failure mode I want while the gap is open: loud, not quiet.

## Why it matters

Fail-closed governance is only *complete* if it accounts for tools that don't exist at build time. A tool registry you can enumerate at compile time is the easy 90%. The dangerous 10% is everything a provider, a harness, or a plugin conjures at runtime — and those are precisely the tools your static policy table has never heard of.

The design lesson generalizes past this one framework: put your policy check on the *invocation* path, not the *registration* path. Middleware that fires per call sees runtime-injected tools for free; a gateway that only validates a startup manifest never will. Then make the default deny. A fail-closed default converts the runtime-injection blind spot from a silent ungoverned bypass into a visible failure — a blocked call with a name attached — and a named block is something you can triage, enumerate, and resolve. You allowlist the known-safe internals deliberately, one verified name at a time, and you leave the rest to fail loud until you've actually looked.

Governance you can only assert about tools you wrote isn't governance. It's a manifest.
