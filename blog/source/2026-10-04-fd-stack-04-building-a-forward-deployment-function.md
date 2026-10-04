# Building a Forward Deployment Function

*A practical blueprint for founders and GTM leaders: when to start forward deployment, who to hire first, how to scope engagements, what to measure, and how to keep it from eating your margins.*

This closes [The Forward Deployment Stack](/blog/posts/fd-stack-01-the-forward-deployment-stack.html). The first three posts named the layers — [engineer](/blog/posts/fd-stack-02-the-forward-deployed-architect.html) (build), architect (scale), [leader](/blog/posts/fd-stack-03-the-forward-deployed-leader.html) (run). This one is the operator's guide: how to actually stand the function up without the usual mistakes.

## When to start

Start forward deployment when your product has a **demo-to-production gap** — when prospects are impressed but can't get to real value on their own. For most AI products, that's day one: a model dazzles in a demo and then stalls on the customer's messy data, costs, security review, and edge cases. If your deals die *after* a good demo, that's not a product problem. It's a motion problem, and forward deployment is the motion.

Do *not* start it to paper over a product nobody wants. Forward deployment amplifies real value; it can't manufacture it.

## The hiring sequence

1. **First, one FDE.** Not a team — one excellent, broad engineer who can do discovery, build end-to-end, and talk to humans. Point them at one lighthouse customer and one real win. You're proving the motion exists.
2. **Add the architect layer when you build the same thing twice.** Often this is your first FDE promoted into watching for patterns. The trigger is concrete: the second near-duplicate build, or the second security review that restarts from scratch.
3. **Formalize the leader layer when it's a real line of business.** When forward deployment is influencing meaningful revenue and you have several engagements running, it needs an owner managing economics, scoping, and productization — early on, usually a founder.

Resist hiring the whole stack up front. Each layer should be pulled into existence by a wall you're actually hitting.

## Scope every engagement (the one-page SOW)

The discipline that saves the function. Before an engineer starts, agree in writing:

- **The win** — the single outcome this build proves. Not a feature list.
- **The boundary** — what's explicitly *out*. Write the "we will not build X" line.
- **The timebox** — days or weeks, not "until they're happy."
- **The handoff** — who owns it after, and what "done" unlocks (expansion, rollout, a reference).
- **The reuse test** — will this help the next ten customers, or just this one? If just one, it needs a reason bigger than one deal.

## Define production success criteria before the pilot

AI pilots die for lack of a finish line. Fix it up front, together: what task, what bar (accuracy, latency, cost), who signs off, and what happens on day one *after* it passes. No agreement on those four means you don't have a pilot — you have an unpaid science project.

## The economics

Know the fully-loaded cost of a deployment and what it must return — in new revenue, expansion, or a reference that wins the next deal — to be worth doing. Then watch the trend: **cost per deployment must fall as your reference architecture matures.** If it's flat after ten deployments, your reuse rate is broken and you're running an agency. Track:

- Time-to-production (yes → live)
- POC-to-production conversion
- Reuse rate (bespoke work that becomes product)
- Cost per deployment, trending down

## The flywheel that makes it compound

Forward deployment only beats consulting if learning flows back:

1. The FDE builds a bespoke win and hits reality first.
2. The FDA extracts the reusable pattern into reference architecture.
3. The FDL funds the best patterns into product.
4. The next deployment starts from product, not zero — so it's cheaper and faster.

Every engagement should make the next one cheaper. If yours don't, you're missing the upward learning flow — usually because no one owns the architect or leader layer.

## Common failure modes

- **The agency trap.** Endless bespoke work, no reuse, inverting margins. Cause: no FDL discipline, no FDA extraction.
- **The hero trap.** The whole motion lives in one irreplaceable engineer's head. Cause: no documented reference architecture.
- **The science-project trap.** Pilots that never end. Cause: no pre-agreed success criteria.
- **The over-serving trap.** Saying yes to every customer request. Cause: no scoping discipline.

Every one of these is a missing *layer*, not a missing effort.

## A 90-day start

- **Days 1–30:** Pick one lighthouse customer. Write the first one-page scope. Define success criteria. Put your best engineer on it.
- **Days 30–60:** Build the win on their real data. Prove it against the criteria. Document what you built.
- **Days 60–90:** Extract the first reusable pattern. Instrument time-to-production and reuse rate. Decide what, if anything, graduates toward product.

Do that once, well, and you have a motion. Do it three times and you have a function.

---

*If your AI deals keep dying after a great demo, forward deployment is likely the fix — and it's a motion you can build deliberately rather than stumble into. I write about the Forward Deployment Stack and help teams stand it up. Find me on LinkedIn to talk.*
