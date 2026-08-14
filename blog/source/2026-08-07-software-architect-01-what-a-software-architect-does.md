# What a Software Architect Does

*The opening post of "The Software Architect's Path" — demystifying the role by separating what architecture actually is (the decisions that are hard to reverse) from day-to-day coding, and arguing for the hands-on architect over the ivory-tower one.*

---

Ask ten engineers what a software architect does and you will get ten answers, most of them wrong in an instructive way. Someone will say the architect draws the boxes and arrows. Someone will say the architect is the person who stopped coding. Someone will say the architect decides the tech stack in a kickoff meeting and then disappears. Each of these captures a fragment and misses the center.

This series, **The Software Architect's Path**, is my attempt to describe the role as it is actually practiced by people who are good at it — pragmatic, hands-on, accountable for outcomes. This first post demystifies the job. The rest of the series goes deep on the tools of the trade. Before we can talk about styles, quality attributes, or decision records, we have to agree on what the job even is.

---

## Architecture is the set of decisions that are hard to change

Here is the definition I keep coming back to, drawn from Ralph Johnson's oft-quoted framing that Martin Fowler popularized: architecture is the stuff that is hard to change later. Not the stuff that is important-sounding. The stuff that is *expensive to reverse*.

Rename a variable and no one notices. Swap a sorting function and you write a test. But decide that your system will be a single deployable process sharing one database, and three years later "let's split this into services" becomes a two-quarter migration with a war room. Decide that every module talks to every other module directly, and the day you need to insert an audit boundary you find there is no seam to cut along. Those early decisions calcify. They become the terrain everyone else has to build on.

So architecture is not the diagram. The diagram is a *representation* of the architecture. The architecture itself lives in the decisions the diagram implies:

```text
Architecture = the significant decisions, where "significant" means:
  - high cost to reverse once code and teams depend on them
  - wide blast radius (touch many modules, teams, or deployments)
  - constraining (they rule other options in or out)

Examples of architectural decisions:
  - synchronous request/response vs. event-driven messaging
  - one shared database vs. a datastore per service
  - where the transactional boundary sits
  - what the system must never lose, leak, or slow down under load

NOT architectural decisions (day-to-day engineering):
  - which HTTP client library to import
  - how a single function is structured
  - the name of a class
```

The three ingredients an architect is always juggling are **structure** (how the system is decomposed and how the parts communicate), the **"-ilities"** (the quality attributes: scalability, availability, security, maintainability, and their cousins — the subject of a whole later post), and the **cross-cutting concerns** that refuse to live in one module: authentication, logging, error handling, observability, configuration. These three show up in every architecture conversation you will ever have.

**The gotcha:** you cannot tell whether a decision is architectural by how technical it sounds. "Which message broker" sounds architectural and often isn't — you can swap Kafka for another log-based broker with contained effort. "Do we allow any service to read another service's tables" sounds like a coding-standards footnote and is one of the most consequential architectural decisions you will make. Judge by reversibility and blast radius, not by vocabulary.

---

## What the architect is actually responsible for

If the material of the job is significant decisions, the responsibilities follow from that. In practice the role breaks into a handful of duties that recur across every company I have worked in.

```text
1. Make and justify high-leverage decisions
   Pick the few choices that shape everything downstream — and be able
   to explain WHY, so the decision survives when you're not in the room.

2. Define constraints and guardrails
   You cannot review every pull request. Instead you set the rules of
   the road: layering rules, dependency directions, "no service reads
   another's database," approved integration patterns. Constraints scale;
   your attention doesn't.

3. Own the quality attributes
   Nobody else is accountable for "the system stays up at 10x traffic"
   or "a breach in one module can't read everything." The architect
   turns fuzzy wishes into measurable targets.

4. Manage trade-offs
   Every -ility bought is another one sold. More consistency usually
   costs availability. More flexibility usually costs simplicity. The
   architect names the trade and makes the call in the open.

5. Align technology with business
   A design that ignores the business timeline, budget, or risk appetite
   is a wrong design, however elegant. Architecture serves the business,
   not the other way around.

6. Communicate and align teams
   Conway's Law is real: systems mirror the communication structure of
   the org that builds them. Part of the job is shaping both.

7. Mentor
   Every decision you explain well is a decision the next engineer can
   make without you. Multiplying judgment is the highest-leverage thing
   an architect does.
```

Notice how little of this is about drawing. Most of it is judgment, communication, and accountability. The diagram is a byproduct.

**The gotcha:** the responsibility that gets dropped first under pressure is number 2 — defining guardrails. It feels less urgent than shipping. But an architect who reviews everything personally is a bottleneck, and an architect who reviews nothing has abdicated. Guardrails are how you stay out of both traps: encode judgment into rules and automated checks so the system stays coherent without you standing over it.

---

## The spectrum: ivory tower versus the architect who codes

There is a spectrum of how the role gets played, and where you land on it matters more than your title.

At one end sits the **ivory-tower architect**: hands off keyboard, produces slide decks and reference diagrams, hands them "down" to teams, and is genuinely surprised when the implementation diverges. This is an anti-pattern, and it fails predictably. Detached from the code, the architect's mental model drifts from reality. Decisions get made without knowing what is actually cheap or expensive to build. And teams, sensibly, route around a person whose guidance doesn't survive contact with a compiler.

At the other end is the **architect who codes** — sometimes called the tech-lead or "player-coach" model. This person still writes code, though not on the critical path of every feature. They build the risky proof-of-concept themselves. They feel the friction of their own guardrails because they live under them. They earn authority from demonstrated judgment rather than from an org chart.

I argue firmly for the hands-on end, and here is the practical reason:

```text
Ivory tower                        Architect who codes
------------------------------     ------------------------------
Design divorced from feasibility   Design tested against real code
Authority from title               Authority from earned trust
Feedback loop: months (or never)   Feedback loop: days
Guardrails theorists don't feel    Guardrails the author lives under
Teams route around the design      Teams pull the architect in
```

You do not need to be the most prolific coder on the team. You need to stay close enough to the code that your decisions are grounded and your credibility is earned. When you stop being able to build the thing you're designing, your designs quietly stop being buildable.

---

## Architecture is a continuous activity, not a one-time artifact

The most damaging myth about the role is that architecture happens at the start. You gather requirements, you design the system, you produce the blueprint, and then engineering "implements" it. This is the building-construction metaphor, and software is not a building.

Requirements change. Traffic patterns you predicted turn out wrong. A dependency you bet on gets acquired and sunset. The team doubles and Conway's Law reshapes the seams. A design that was right for ten thousand users is wrong for ten million. If your architecture is a diagram you drew in month one and never revisited, it is already a work of fiction by month six.

Good architecture is a **continuous activity**: you make decisions as late as you responsibly can (when you have the most information), you revisit past decisions when the assumptions behind them expire, and you build systems that expect to change. This is the whole premise of *evolutionary architecture*, which gets its own post later in the series. For now, hold onto the frame: the architect is not a person who *made* the design. The architect is a person who *tends* it, continuously, as the system and the business evolve.

**The gotcha:** "decide as late as possible" is not "decide never." Deferring a genuinely reversible decision is prudence; deferring a hard-to-reverse one until it's forced on you by a crisis is negligence. The skill is telling the two apart — which is exactly why the "hard to change" definition is the architect's most important tool.

---

## How this differs from being a senior engineer

Senior engineers and architects overlap so much that the boundary is worth naming precisely. A strong senior engineer already makes local design decisions well. The architect's job differs along a few axes:

| Axis | Senior engineer | Architect |
|---|---|---|
| Scope | Deep in a component or service | Across services, teams, the whole system |
| Optimizes for | Correct, clean, performant code | Quality attributes and trade-offs system-wide |
| Owns | Implementation quality | The consequences of hard-to-reverse choices |
| Communicates with | Mostly other engineers | Engineers *and* product, security, execs |
| Time horizon | This sprint, this release | Years — sometimes the next decade |
| Thinks in | Functions, classes, modules | Systems, boundaries, flows, org structure |

The move from senior engineer to architect is mostly a move from *depth* to *breadth plus depth*, and from owning code to owning consequences. You trade some of the satisfaction of building the perfect component for the responsibility of making sure the components add up to a system that survives contact with reality — and with the business. It is also a move toward stakeholders who don't speak in code, which is why the soft-skills post later in this series is not a throwaway.

---

## Three myths worth killing now

**"Architecture is boxes and arrows."** The diagram is documentation. The architecture is the decisions. You can draw a beautiful diagram of a bad architecture and a napkin sketch of a great one. We will use the C4 model later precisely so the diagrams communicate decisions instead of decoration.

**"Architects don't code."** The good ones stay close to the code. The ones who don't lose the feedback loop that keeps their designs honest. Coding less is normal; not coding at all is a warning sign.

**"There is one right architecture."** There is no best architecture, only the least-bad set of trade-offs *for this system, this team, this business, right now*. The same requirements at a three-person startup and a thousand-person enterprise produce different correct answers. Anyone selling you a universal blueprint is selling you someone else's constraints.

---

## The road ahead: mapping this series

This post is the "what and why." The rest of the series is the "how" — roughly eight posts, each a tool you can pick up:

```text
1. What a Software Architect Does          ← you are here
2. Architectural styles                    monolith, modular monolith,
                                           microservices, event-driven,
                                           and how to choose
3. Quality attributes (the -ilities)       turning "it should be fast"
                                           into measurable targets
4. Decisions & trade-offs (ADRs)           making calls in the open and
                                           recording WHY they were made
5. Architecture patterns                   layered, ports & adapters,
                                           CQRS, saga — and their misuse
6. Documenting architecture (C4)           diagrams that communicate
                                           decisions, not decoration
7. Evolutionary architecture & tech debt   designing for change; managing
                                           debt as a deliberate ledger
8. The architect's soft skills             influence, communication,
                                           and leading without authority
```

If there is one idea to carry out of this opening post, it is the definition: **architecture is the set of decisions that are hard to change, and the architect's job is to make those few decisions well, keep them honest as the system evolves, and help everyone else understand why.** Everything else in this series hangs off that sentence.

---

## Key takeaways

- **Architecture is the hard-to-reverse decisions**, judged by cost of reversal and blast radius — not by how technical they sound.
- **The material of the job is structure, the -ilities, and cross-cutting concerns** — and the diagram is a byproduct, not the thing itself.
- **The responsibilities are judgment and communication**: make high-leverage calls, set guardrails that scale past your attention, own quality attributes, name trade-offs, align tech with business, and mentor.
- **Favor the architect who codes over the ivory tower** — grounded designs and earned authority beat detached blueprints every time.
- **Architecture is continuous.** You tend it as the system and business change; a month-one diagram never revisited is fiction by month six.
- **It differs from senior engineering in breadth, trade-off ownership, stakeholder communication, and time horizon** — thinking in systems and decades, not sprints.

---

## Further reading

- [Software Architecture Guide](https://martinfowler.com/architecture/) — Martin Fowler's collected writing on what architecture is and why "the important stuff, whatever that is" and "the decisions that are hard to change" are useful working definitions.
- [Who Needs an Architect?](https://www.martinfowler.com/ieeeSoftware/whoNeedsArchitect.pdf) — Fowler's classic essay (with Ralph Johnson's definition) on the ambiguity of the role and the case against the ivory tower.
- *Fundamentals of Software Architecture* by Mark Richards and Neal Ford (O'Reilly) — a broad, modern survey of the discipline: architecture characteristics, styles, and the expectations of the role. [Publisher page](https://www.oreilly.com/library/view/fundamentals-of-software/9781492043447/).
- [The C4 model for visualising software architecture](https://c4model.com/) — Simon Brown's approach to architecture diagrams at four levels of abstraction; the basis for the documentation post later in this series.
- [Conway's Law](https://martinfowler.com/bliki/ConwaysLaw.html) — Fowler's summary of why systems come to mirror the communication structure of the organizations that build them.
