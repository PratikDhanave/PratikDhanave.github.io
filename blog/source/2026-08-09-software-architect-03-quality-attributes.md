# Quality Attributes: Architecting for the -ilities

*Why the non-functional requirements — performance, scalability, availability, security, maintainability and their kin — are what your architecture is actually optimized for, how to make them measurable, and why they always trade off against one another.*

---

Ask a team what their system does and you'll get a list of features: place an order, upload a photo, run a payroll batch. Those are the **functional requirements** — the *what*. Here's the uncomfortable truth of architecture: the functional requirements almost never determine the design. You can satisfy "place an order" with a monolith, with microservices, with a spreadsheet and a human, with an event-sourced ledger. All of them work. What separates a good architecture from a bad one is *how well* it does those things under pressure — how fast, how reliably, how cheaply, how safely, how easily it can be changed six months from now.

Those are the **quality attributes**, the "-ilities": scalab*ility*, availab*ility*, maintainab*ility*, secur*ity*, and the rest. This post is about the single most important idea in software architecture, and it fits in one sentence: **functional requirements can be met many ways; the architecture is chosen by the quality attributes.** Everything else here is a consequence of that sentence.

---

## Why the -ilities drive the architecture

A feature is local. "Add a discount code field" touches a form, a validation rule, a column. You can bolt it on to almost any structure. A quality attribute is *global* — it's a property of the whole system, and you cannot bolt it on later.

Consider two teams asked to build the same order service. Team A is told "it must handle Black Friday — 50,000 orders per minute, no downtime." Team B is told "it's an internal tool, a few hundred orders a day, back-office staff only." Same feature list. Wildly different architectures. Team A needs horizontal scaling, a queue to absorb spikes, idempotent writes, multi-zone redundancy, and a caching layer. Team B needs a single database and a nightly backup. If Team B's architect had built Team A's system, they'd have wasted a year and a fortune. If Team A's architect had built Team B's, the site would have melted on the first big sale.

The features didn't decide anything. The *quality attributes* decided everything. This is why we say architecture is the set of decisions that are **hard to change later** — and the decisions that are hard to change are precisely the ones driven by quality attributes. You can refactor a function in an afternoon. You cannot refactor "we chose eventual consistency" without rewriting how the whole system thinks about data.

---

## The major -ilities and how each one shapes structure

There is no official master list, but a working architect returns to the same handful again and again. Here's what each one actually means and, more usefully, the structural fingerprint each one leaves on a design.

- **Performance / latency** — how quickly a single request completes. Drives caching, denormalized read models, connection pooling, moving work off the request path into background jobs, and choosing data structures for read speed.
- **Scalability** — how throughput holds up as load grows. Drives statelessness (so you can add instances), partitioning and sharding, load balancing, and queues that decouple producers from consumers.
- **Availability / reliability** — the share of time the system is usable, and how it behaves when parts fail. Drives redundancy, health checks, retries with backoff, circuit breakers, graceful degradation, and multi-region deployment.
- **Security** — protecting data and access from misuse. Drives authentication and authorization boundaries, encryption in transit and at rest, secret management, network segmentation, input validation, and audit logging.
- **Maintainability / modifiability** — how cheaply the system absorbs change. Drives modular boundaries, low coupling and high cohesion, clean interfaces, and keeping volatile decisions behind stable seams.
- **Testability** — how easily you can verify behavior. Drives dependency injection, pure functions, small units with clear contracts, and the ability to run components in isolation.
- **Deployability** — how safely and often you can ship. Drives small independently releasable units, backward-compatible interfaces, feature flags, and blue-green or canary rollout.
- **Observability** — how well you can understand the running system from the outside. Drives structured logging, metrics, distributed tracing, and correlation IDs threaded through every call.
- **Usability** — how effectively humans accomplish their goals. Drives response-time budgets the UI can honor, sensible error surfaces, and sometimes optimistic updates that shape the data flow.
- **Cost** — the money the whole thing burns. Drives instance sizing, storage tiering, choosing managed services versus self-hosting, and knowing when "good enough" beats "gold plated."

Notice that every entry has a *structural consequence*. That's the tell. If a requirement doesn't push on the structure, it isn't architecturally significant.

---

## Make them measurable, or you can't design for them

Here is the mistake I see most often, from juniors and executives alike: stating a quality attribute as an adjective. "It must be fast." "It has to be secure." "We need it to scale." These feel like requirements. They are not. They are wishes. You cannot design for "fast" because you don't know when you've arrived, and you cannot *verify* "fast" because there's nothing to measure against.

The fix is the **quality attribute scenario** — a small, structured statement that turns an -ility into something you can build toward and test. A scenario names a stimulus (what happens), an environment (under what conditions), and a response measure (the number that says you succeeded).

```text
Quality Attribute Scenario — template
------------------------------------------------------------
Source:       who or what triggers it   (a user, a downstream service, a clock)
Stimulus:     the event that arrives     (a request, a failure, a spike, a deploy)
Artifact:     the part being stimulated  (the checkout API, the whole system)
Environment:  the operating condition    (normal load, peak load, degraded mode)
Response:     what the system does       (serves it, queues it, sheds it, fails over)
Measure:      the number that proves it   (p99 latency, % uptime, recovery time)
------------------------------------------------------------

Filled in — performance:
"Under peak load of 10,000 requests/second (environment), when a user
submits a checkout (stimulus), the checkout API (artifact) returns a
confirmation (response) with p99 latency < 200 ms and zero dropped
requests (measure)."

Filled in — availability:
"When a single availability zone goes offline (stimulus) during normal
operation (environment), the system (artifact) continues serving reads
and writes (response) with < 30 seconds of failover and no data loss
(measure)."
```

"p99 < 200 ms at 10,000 rps" is a requirement. "Must be fast" is a mood. The number does three jobs at once: it tells the architect how much machinery to build (a p99 of 200 ms and a p99 of 2 seconds justify entirely different designs), it tells the team when to *stop* building (over-engineering is just as much a failure as under-engineering), and it gives QA and monitoring a threshold to alarm on. A measurable target is often called a **fitness function** — a test the architecture must continuously pass.

**The gotcha:** "make it fast / secure / scalable" is not a requirement — it's a feeling. An unmeasurable -ility cannot be designed for and cannot be verified, so it will be quietly ignored under deadline pressure and then blamed after launch. Force every quality attribute you care about into a scenario with a number attached. If a stakeholder can't or won't give you a number, that's a signal the attribute doesn't matter as much as they think — or that you need to propose one and get it ratified.

---

## They trade off — you cannot maximize all of them

If you could have every -ility at its maximum, architecture would be trivial: turn every dial to eleven. You can't. Quality attributes are coupled, and pushing one up almost always pushes another down. Recognizing these tensions is the core skill.

A few of the classic tensions:

- **Security vs. usability.** Every extra authentication step, every session timeout, every permission prompt hardens the system and irritates the user. Mandatory MFA on every action is very secure and nearly unusable.
- **Consistency vs. availability.** This is the famous one, and it ties directly to the CAP theorem from distributed systems design: when the network partitions, you must choose between refusing to answer (staying consistent) and answering with possibly-stale data (staying available). You cannot have strong consistency *and* full availability during a partition. Your choice here reshapes the entire data layer.
- **Performance vs. maintainability.** The fastest code is often the ugliest — hand-tuned, inlined, coupled to hardware assumptions. Clean, modular, easy-to-change code carries indirection that costs cycles. Caching buys latency at the price of a whole new class of invalidation bugs.
- **Cost vs. everything.** Availability costs money (redundant everything). Performance costs money (more/bigger machines, caches). Security costs money (audits, encryption, dedicated infra). Cost is the attribute that sits across the table from all the others, and "how much reliability can we afford?" is a real and honest question.

Because you can't maximize all of them, the job is not optimization — it's **prioritization**. Pick the two or three that matter most for *this* system, optimize hard for those, and accept "good enough" on the rest. A prioritization exercise makes the trade explicit:

```text
Prioritization — a payments platform (illustrative)
------------------------------------------------------------
Rank  Quality attribute     Why it wins here
1     Security              handling money + PII; a breach is existential
2     Availability          if payments are down, revenue stops instantly
3     Consistency           double-charging a customer is unacceptable
------------------------------------------------------------
Deliberately traded away:
  - Usability      : extra verification steps are acceptable friction
  - Cost           : redundancy and audits are worth the spend
  - Deploy speed   : ship carefully and rarely, not fast and often
------------------------------------------------------------

Contrast — a social photo feed (illustrative)
------------------------------------------------------------
Rank  Quality attribute     Why it wins here
1     Availability          the feed must never feel "down"
2     Performance           scroll must be instant or users leave
3     Scalability           traffic is spiky and enormous
------------------------------------------------------------
Deliberately traded away:
  - Consistency    : a like count off by one for a few seconds is fine
  - Cost           : optimize aggressively, eat some staleness
------------------------------------------------------------
```

Same engineers could build both. The architectures share almost nothing, because the top three -ilities are different — and where one system spends its complexity budget, the other deliberately refuses to.

**The gotcha:** you cannot maximize every quality attribute at once — optimizing one taxes another, always. An architecture that claims to be maximally secure *and* maximally usable *and* maximally cheap is either lying or hasn't been stressed yet. Name your top three to five explicitly, write down what you're trading away, and get that ranking agreed *before* you design. An unspoken priority order is still an order — it just gets decided by accident, usually by whoever complains loudest after launch.

---

## Eliciting the top few that matter for THIS system

The priority list doesn't fall out of the code. It comes from **stakeholders**, and different stakeholders carry different -ilities in their heads. The business owner cares about cost and time-to-market. The operations team cares about availability and observability. Compliance cares about security and auditability. End users care about usability and performance. Nobody holds the whole picture, which is exactly why eliciting quality attributes is an active, deliberate step — not something you infer from a feature backlog.

The practical technique is to gather the interested parties and have them each propose concrete scenarios, then rank them by *business impact* and *technical risk*. Scenarios that are both high-impact and high-risk are your architectural drivers. The output is short on purpose: a handful of prioritized, measurable scenarios that the design must satisfy. Everything the architecture does should trace back to one of them.

**The gotcha:** teams discover the *important* -ility far too late because nobody elicited it. A system ships beautifully, then legal asks "where's the audit trail?" (auditability), or a customer in Germany asks "is our data stored in the EU?" (data residency), or the on-call engineer asks "how do I even see what's happening in there?" (observability). These aren't features you sprinkle on — they're structural, and retrofitting them can mean rebuilding the data layer. Ask up front: run through the full list of -ilities *with the stakeholders* and force each one to be either prioritized or explicitly dismissed. Silence is not dismissal.

---

## "Architecturally significant" means "driven by a quality attribute"

Pull the thread all the way and you arrive at a clean definition. A requirement is **architecturally significant** when it forces a structural decision — and it forces a structural decision precisely because it expresses a quality attribute. "Support discount codes" is not architecturally significant; it's a feature you can add to any structure. "Process 50,000 orders per minute with p99 < 200 ms and zero data loss on zone failure" *is* architecturally significant, because it dictates statelessness, partitioning, queuing, and redundancy. Same domain, completely different weight.

This gives you a filter for where to spend your scarce architecture attention. Not every requirement deserves a diagram and a debate. The ones that do are the ones a quality attribute is pushing on.

Here's the reference table — the -ilities, what each means, and the structural mark each leaves:

| -ility | What it means | How it shapes the architecture |
|---|---|---|
| Performance / latency | Speed of a single operation | Caching, read models, async offload, connection pooling |
| Scalability | Throughput as load grows | Statelessness, sharding, load balancing, queues |
| Availability / reliability | Uptime and failure behavior | Redundancy, retries, circuit breakers, multi-region, degradation |
| Security | Protection of data and access | Auth boundaries, encryption, secret management, segmentation, audit logs |
| Maintainability | Cost of change over time | Modular boundaries, low coupling, stable interfaces |
| Testability | Ease of verification | Dependency injection, pure functions, isolatable components |
| Deployability | Safety and cadence of releases | Small releasable units, backward compatibility, canary/blue-green |
| Observability | Visibility into a running system | Structured logs, metrics, tracing, correlation IDs |
| Usability | Effectiveness for humans | Response-time budgets, error surfaces, optimistic UI flows |
| Cost | Total money burned | Right-sizing, storage tiering, managed vs. self-hosted |

---

## Key takeaways

- **Quality attributes choose the architecture, not the features.** The same feature list yields radically different designs once you fix the -ilities. Architecture is the set of hard-to-change decisions, and those decisions are driven by quality attributes.
- **An unmeasured -ility is a wish.** "Fast," "secure," and "scalable" cannot be designed for or verified. Convert each one into a quality attribute scenario with a number — "p99 < 200 ms at 10k rps" — so you know how much to build, when to stop, and what to alarm on.
- **You cannot maximize all of them.** Security fights usability, consistency fights availability, performance fights maintainability, and cost fights everything. The job is prioritization: pick the top three to five, optimize hard for those, and write down what you're trading away.
- **Elicit the priorities up front, from stakeholders.** Nobody holds the whole picture. Walk the full list of -ilities with the people who care, and force each to be prioritized or explicitly dropped — or you'll discover auditability or data residency the hard way, after launch.
- **Architecturally significant = driven by a quality attribute.** Use that as your filter for where to spend design effort. A beautiful architecture optimized for the *wrong* quality attribute is still a failure — get the ranking right first.

Name your top few quality attributes, make them measurable, and accept that everything trades off. Do that, and the architecture largely designs itself. Skip it, and no amount of clean code will save you.

---

## Further reading

- [ISO/IEC 25010 — the software product quality model](https://en.wikipedia.org/wiki/ISO/IEC_25010) — the standard taxonomy of quality characteristics (functional suitability, performance efficiency, reliability, security, maintainability, and more). A useful checklist to make sure you haven't forgotten an -ility during elicitation.
- [Software Architecture in Practice (SEI) — the quality attribute scenario method](https://insights.sei.cmu.edu/library/software-architecture-in-practice-third-edition/) — the source of the source/stimulus/environment/response/measure structure and the idea of ranking scenarios by impact and risk.
- [Martin Fowler — Software Architecture Guide](https://martinfowler.com/architecture/) — a practical, plain-language take on what architecture is and why the "hard-to-change decisions" framing matters.
- [CAP theorem](https://en.wikipedia.org/wiki/CAP_theorem) — the consistency-vs-availability trade that recurs across every distributed system (see also this series' post 5).
