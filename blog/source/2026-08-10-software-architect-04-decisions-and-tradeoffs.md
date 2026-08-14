# Architectural Decisions and Trade-offs

*The core of the architect's job is not drawing boxes but making, justifying, and recording the significant, hard-to-reverse decisions a system is built on — deliberately, under uncertainty, and with the reasoning written down.*

---

Earlier in this series I argued that an architecture *is* its set of significant, hard-to-reverse decisions — the choices that shape everything built afterward and that you cannot easily undo once code, teams, and data have grown around them. If that is true, then the daily work of an architect is not producing diagrams. Diagrams are a byproduct. The work is choosing: picking one option over others when the information is incomplete, being explicit about what each choice costs, and leaving a trail so the next person understands *why*.

This post is about that core loop. How to tell which decisions deserve deliberation and which deserve speed. How to run a trade-off analysis that produces a defensible choice instead of a gut call dressed up in slides. How to avoid the anti-patterns that quietly make the decision for you. And how to record a decision so its rationale survives the six months until everyone who was in the room has forgotten it.

---

## One-way doors and two-way doors

Not every decision carries the same weight, and treating them as if they do is one of the most expensive habits a team can develop. Amazon popularized a useful frame for this, attributed to Jeff Bezos in his shareholder letters: some decisions are **one-way doors** and some are **two-way doors**.

A two-way door is reversible. You walk through, and if you don't like what's on the other side, you walk back out at low cost. Choosing a logging library, a code-formatting style, the internal layout of a package, or which of two comparable HTTP frameworks to use inside one service — these are usually two-way doors. If you're wrong, you refactor and move on.

A one-way door is hard or impossible to reverse. Your public API contract. Your primary datastore and data model. Whether the system is a monolith or a fleet of services. Your tenancy model. Your authentication and authorization foundation. Walk through one of these and the door tends to lock behind you: migrating a production data model or breaking an API that thousands of clients depend on is a project, not an afternoon.

The rule that follows is simple and freeing: **match the deliberation to the reversibility.**

- For **two-way doors**, decide fast. Push the decision to the people closest to the code, pick a reasonable option, and reserve your energy. The cost of being wrong is a revert.
- For **one-way doors**, slow down. Gather options, run the trade-off analysis below, get more eyes on it, and write down the reasoning. The cost of being wrong is measured in quarters.

**The gotcha:** treating a two-way door like a one-way door is a silent tax. Teams burn weeks debating a choice that could be changed in a day — a caching library, a folder structure — while the genuinely irreversible decisions sail through on someone's default preference. Before you convene the third meeting about a decision, ask out loud: *if we're wrong, what does it cost to reverse this?* If the answer is "an afternoon," stop analyzing and choose.

---

## Trade-off analysis: there is no "best"

The single most important mental shift for an architect is this: **there is no best architecture, only the best architecture for a given set of priorities.** Every meaningful decision improves some qualities at the expense of others. Add a cache and you improve latency while trading away consistency and adding operational surface. Split a monolith into services and you gain independent deployability while paying with network failure modes, distributed debugging, and eventual consistency. Nothing is free.

This is where the quality attributes from earlier in the series — the "-ilities" like performance, scalability, availability, security, maintainability, cost — become the currency of the conversation. A trade-off analysis is the disciplined act of holding options against the attributes that actually matter for *this* system and being honest about what each option gives up.

A workable structure for any significant decision:

```markdown
1. Frame the decision. What problem are we solving? What constraints are
   fixed (budget, deadline, team skills, compliance)?

2. List the realistic options. At least two, ideally three. "Do nothing"
   and "the obvious default" both count as options and deserve to be on
   the list.

3. Identify the quality attributes that matter here, ranked. Not all of
   them — the two or three that this decision most affects. A billing
   system ranks correctness and auditability above raw latency; a live
   feed ranks the reverse.

4. Score each option against those attributes, and write the consequence
   in words, not just a number. "Option B halves p99 latency but adds a
   Redis cluster we must now operate and page on."

5. State what you are giving up. Every option has a cost column. If an
   option appears to have none, you haven't looked hard enough.

6. Decide, and record why — including the options you rejected and why.
```

The output of this is not a winner that is good at everything. It is a defensible statement of the form: *given that we value X and Y more than Z for this system, we chose option B, accepting that we give up Z.* That sentence is the deliverable.

---

## The decision anti-patterns

Most bad architectural decisions are not the result of bad analysis. They are the result of *no* analysis — a decision made by reflex, politics, or inertia. Learn to name these, because naming them in the room is often enough to stop them.

- **Resume-driven development.** Choosing a technology because it is new, fashionable, or good to have on your CV, rather than because it fits the problem. "We chose Kafka because everyone uses it" is not a trade-off; it is marketing you repeated to yourself. The tell is that the justification points at the *industry* or *your career* instead of at *this system's priorities*.
- **Cargo-culting.** Copying a pattern from a company whose constraints you don't share. Netflix's microservices and a big tech firm's cell-based architecture solve problems of a scale most systems never reach. Adopting the solution without the problem imports all the cost and none of the benefit.
- **Analysis paralysis.** Endless comparison with no decision. Often a fear of the one-way door applied — wrongly — to a two-way door. The cure is a deadline and the reversibility question.
- **The HiPPO.** The *Highest Paid Person's Opinion* wins, not because it's better but because of who said it. This is corrosive because it teaches everyone else to stop bringing options. Guard against it by writing the trade-off down *before* the senior person speaks, so the analysis, not the hierarchy, is on the table.
- **Deciding by default (inertia).** The most common anti-pattern of all: not deciding, and letting the status quo or the first thing someone prototyped harden into the architecture. A decision you never consciously made is still a decision — you just made it badly, by not looking.

**The gotcha:** "we chose X because it's modern / everyone uses it" is resume-driven development wearing a trade-off's clothes. A real justification names the quality attributes X wins on *for your priorities* and admits what X costs you. If your rationale would be equally true for a completely different system, it isn't a rationale — it's a preference you haven't examined.

---

## Architecture Decision Records

Here is what actually happens without a written record. You make a careful, correct decision. You add a constraint — say, "all writes go through the command service; no service writes to the ledger table directly" — because you reasoned through consistency and auditability. Six months pass. The people who were in the room move teams. A new engineer sees the constraint, finds it annoying, sees no reason for it, and rips it out. The system breaks in a way no one connects to the change for weeks, because the *why* evaporated.

An **Architecture Decision Record** (ADR) is the cheap fix for this. The format was popularized by Michael Nygard in a 2011 post: a short, plain-text document, one per significant decision, that captures the context, the decision, and the consequences. You keep it *with the code* — in the repository, versioned in git, reviewed in the same pull request as the change it describes — so it lives and moves with the system instead of rotting in a wiki no one opens.

The point of an ADR is not ceremony. It is to answer one question for future-you and every future joiner: **why is it this way?** A good ADR is short enough that people actually write them and specific enough that they actually help. A template that works:

```markdown
# ADR 0007: Use idempotency keys for all payment write endpoints

## Status
Accepted — 2026-08-10. Supersedes ADR 0004.

## Context
Payment clients retry on network timeout. Without deduplication, a retried
POST /charges can create a duplicate charge. We must guarantee at-most-once
effect per client intent, and we are optimizing for correctness and
auditability over write latency. Constraint: clients are third parties we
cannot force to change quickly.

## Decision
Every write endpoint requires an `Idempotency-Key` header. We persist the
key with the request hash and the response, and return the stored response
on any replay within a 24-hour window.

## Alternatives considered
- Client-side dedup only. Rejected: we do not control third-party clients.
- Natural-key uniqueness constraints in the DB. Rejected: intent is not
  always expressible as a natural key, and it leaks storage schema into the
  contract.

## Consequences
+ Duplicate charges become structurally impossible within the window.
+ Safe client retries; simpler client error handling.
- Every write path now depends on the idempotency store being available.
- 24-hour retention adds storage and a cleanup job to operate.
```

Notice the two sections that do the heavy lifting and that people most often skip. **Alternatives considered** is what stops a team from re-litigating the same debate every year — it records not just what you chose but what you *rejected and why*. **Consequences** with an explicit cost column (the `-` lines) is the honest record of what you traded away, so no one later mistakes a deliberate cost for an accident.

**The gotcha:** not writing down the alternatives you rejected means you will re-litigate them forever. Every six months a well-meaning engineer proposes the exact option you already dismissed, and without the ADR you have no memory of *why* — so you run the whole analysis again, or worse, you switch, hit the same wall that made you reject it the first time, and switch back. The rejected options are not clutter; they are the most valuable part of the record.

---

## Lightweight methods to get to a decision

You don't need heavyweight process for most decisions. A few small, structured methods carry almost all the weight.

**The decision matrix.** When you have a handful of options and a handful of attributes, put them in a grid. Weight the attributes by importance to *this* system, score each option, and let the structure force honesty. The matrix doesn't make the decision — you can always override it — but it makes your reasoning visible and comparable.

```markdown
Decision: primary datastore for the new orders service
Weights reflect this system's priorities (transactional integrity first).

| Attribute (weight)        | PostgreSQL | DynamoDB | MongoDB |
|---------------------------|-----------:|---------:|--------:|
| Transactional integrity(5)|          5 |        2 |       3 |
| Query flexibility (4)     |          5 |        2 |       4 |
| Operational familiarity(3)|          5 |        3 |       3 |
| Horizontal scale (2)      |          3 |        5 |       4 |
| Managed-cost fit (1)      |          3 |        4 |       4 |
| Weighted total            |         72 |       42 |      56 |
```

Here PostgreSQL wins *because this system weights transactional integrity and query flexibility highest*. Re-weight for a system that needs massive horizontal scale above all else and DynamoDB may win. That is the whole point: the matrix encodes priorities, and the priorities decide.

**The spike / proof of concept.** Sometimes the honest answer is "we don't have enough information to choose." A spike is a time-boxed experiment that *buys* that information — build the risky slice, measure the thing you're unsure about, throw the code away. A one-week spike that de-risks a one-way door is one of the best investments an architect can make. The discipline is the time box and the explicit question: you are buying an answer, not building the feature.

**Trade-off analysis at scale (ATAM).** For the biggest, most contested one-way doors, the Software Engineering Institute at Carnegie Mellon formalized the **Architecture Tradeoff Analysis Method** (ATAM). You don't need the full ceremony often, but its core idea is worth internalizing: gather stakeholders, turn vague goals into concrete *quality-attribute scenarios* ("a returning customer's dashboard loads in under 500 ms at the 99th percentile under peak load"), and evaluate architectural approaches against those scenarios to surface the **trade-off points** — the places where one approach helps one attribute and hurts another. Even a two-hour version of this, done informally, beats an unstructured debate.

---

## Decisions are not permanent — revisit them

A decision is correct *for the context in which it was made.* Context changes: traffic grows an order of magnitude, a managed service you couldn't use before becomes available, a team that could operate a complex system disbands, a regulation lands. When the context that justified a decision no longer holds, the decision is due for review — and this is not failure, it is the system working as intended.

This is exactly why the ADR has a **Status** field, and why ADRs are never edited into a lie or deleted. You don't rewrite ADR 0004; you write ADR 0007 that says *supersedes ADR 0004*, and mark the old one `Superseded by ADR 0007`. The history stays intact. Anyone reading the code later can see not just what the current decision is but the whole chain — what you used to do, why you changed, and what forced the change. That immutable trail is worth as much as the current decision, because it teaches the reasoning, not just the conclusion.

A healthy discipline is a lightweight periodic review of the significant ADRs: are the assumptions in the Context section still true? If not, the decision is a candidate for a new ADR, not a quiet in-place edit.

---

## Key takeaways

- **Architecture is the set of significant, hard-to-reverse decisions.** The job is making them well, not drawing them.
- **Match deliberation to reversibility.** Two-way doors: decide fast, delegate, revert if wrong. One-way doors: slow down, analyze, and record.
- **There is no "best," only best-for-these-priorities.** Every decision trades some quality attributes for others. Name the ones you're giving up.
- **Anti-patterns make the decision for you.** Resume-driven development, cargo-culting, analysis paralysis, the HiPPO, and deciding-by-inertia all replace analysis with reflex. Name them in the room.
- **Write ADRs, and keep them with the code.** Context, decision, alternatives rejected, and consequences — the *why* evaporates in six months without them.
- **Revisit as context changes.** Supersede an ADR, never silently overwrite it; the history is part of the value.

The through-line: decide deliberately for the irreversible calls, record the *why* including what you rejected, and be explicit about what you traded away. Do that, and the next person — often future-you — inherits a system they can reason about instead of one they're afraid to touch.

## Further reading

- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) — Michael Nygard's original 2011 post that introduced the ADR.
- [Architecture Decision Records](https://adr.github.io/) — a community hub of ADR templates, tooling, and examples.
- [2015 Amazon shareholder letter](https://www.aboutamazon.com/news/company-news/2016-letter-to-shareholders) — Jeff Bezos on Type 1 (one-way door) vs. Type 2 (two-way door) decisions.
- [Architecture Tradeoff Analysis Method (ATAM)](https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-collection/) — the Software Engineering Institute's method for evaluating architectures against quality-attribute trade-offs.
- [Architecture decision record (Microsoft Azure Well-Architected)](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record) — practical guidance on writing and maintaining ADRs.
