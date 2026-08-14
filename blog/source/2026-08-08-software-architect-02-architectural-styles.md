# Architectural Styles

*A trade-off-driven tour of the major ways to structure a system — monolith, modular monolith, layered, microservices, service-based, event-driven, and serverless — and how to choose one by team, scale, and organizational maturity rather than hype.*

---

An architectural style is the top-level shape of a system: how the code is partitioned, how the pieces are deployed, and how they talk to each other. It is the decision you make earliest and change latest, which is exactly why it deserves care. Every style solves some problems and creates others — there is no style that is simply "better." The job of an architect is not to pick the most impressive-sounding option; it is to name the forces acting on your system and choose the shape that pays for the complexity it introduces.

This post walks the major styles you will meet, states plainly what each one buys you and what it costs, and then gives you a way to choose that ignores fashion. The through-line is a single warning: **most of the pain in modern architecture comes from adopting distribution before the system needs it.**

---

## 1. The monolith — one deployable unit

A monolith is a system built and deployed as a single unit. One codebase, one build artifact, one process (or a set of identical copies behind a load balancer). All the modules call each other through ordinary in-process function calls.

"Monolith" has become an insult, which is unfortunate, because a monolith has real virtues that distributed systems spend years trying to claw back:

```text
        ┌─────────────────────────────┐
        │          Monolith            │
        │  ┌────────┐  ┌────────┐      │
        │  │ Orders │→ │ Billing │     │   in-process calls
        │  ┌────────┐  ┌────────┐      │   one transaction
        │  │ Users  │  │ Catalog │     │   one deploy
        │  └────────┘  └────────┘      │
        └──────────────┬──────────────┘
                       │
                  ┌────▼────┐
                  │   DB    │
                  └─────────┘
```

- **Simple calls.** A method call either returns or throws. There is no network in the middle to time out, retry, or lose.
- **Easy transactions.** A single database and a single process mean you can wrap related writes in one ACID transaction and get consistency for free.
- **One thing to deploy, debug, and reason about.** A stack trace crosses the whole request. There is one log to read and one thing to roll back.

The classic failure mode is the **big ball of mud**: a monolith with no internal structure, where every part reaches into every other part until no change is safe. But note that this is a failure of *modularity*, not of the monolithic *deployment*. That distinction is the whole point of the next section.

**The gotcha:** "the monolith won't scale" is usually false. A monolith scales *horizontally* — run many identical copies behind a load balancer, and you have scaled your compute. It scales further than most teams ever need. What a monolith cannot do is scale *parts* independently, or let teams deploy on separate schedules. Reach for microservices when you hit *those* walls, not because you assume a single deployable can't take the load.

---

## 2. The modular monolith — the underrated default

A modular monolith is a monolith with enforced internal boundaries. It still ships as one deployable, but the code inside is split into modules that expose a small public interface and hide everything else. A module talks to another module only through that interface — never by reaching into its tables or internal types.

```text
    ┌──────────────── One deployable ────────────────┐
    │                                                 │
    │  ┌─ Orders ──┐   ┌─ Billing ─┐   ┌─ Catalog ─┐  │
    │  │  public   │   │  public   │   │  public   │  │
    │  │  ── API ──│──▶│  ── API ──│   │  ── API ──│  │
    │  │  private  │   │  private  │   │  private  │  │
    │  └───────────┘   └───────────┘   └───────────┘  │
    │        each module owns its own data/schema      │
    └─────────────────────────────────────────────────┘
```

This is the style most teams should start with, and many should never leave. You get the operational simplicity of a monolith and most of the maintainability benefits people expect from microservices:

- Clear ownership: a team owns a module and its public contract.
- Fast, reliable in-process calls between modules — no network tax.
- **Cheap future extraction.** Because modules already talk through narrow interfaces and own their data, promoting one to a standalone service later is mechanical, not a rewrite. The seams are already drawn.

The discipline is the catch. Nothing at runtime stops one module from importing another's internals, so you enforce boundaries with code review, package structure, and sometimes architecture-fitness tests that fail the build on illegal dependencies.

**The gotcha:** a modular monolith gives you most of the benefit of microservices — bounded contexts, clear ownership, replaceable parts — *without* the distributed-systems tax. Start here. If a specific module later develops a real, measured pressure (it needs its own scaling profile, its own release cadence, or a different runtime), extract *that one* into a service. You will do it from a position of clean boundaries instead of untangling a ball of mud under duress.

---

## 3. Layered / n-tier — organize by technical role

Layered architecture slices the system by technical responsibility: presentation, business logic, data access, database. Each layer may only call the one below it. This is the default taught in most courses and lives inside many monoliths and services.

```text
   ┌──────────────────────────┐
   │  Presentation (UI / API) │
   ├──────────────────────────┤
   │   Business logic         │   calls flow downward only
   ├──────────────────────────┤
   │   Data access            │
   ├──────────────────────────┤
   │   Database               │
   └──────────────────────────┘
```

Its strengths are familiarity and separation of concerns: you can swap the database layer without touching business rules, and new developers know where things go. Its weakness is that a single feature usually cuts *across* every layer, so a change touches all of them — and layers can degrade into pass-through code that adds indirection without adding value. Layering is a fine *internal* organization; it is orthogonal to whether you deploy as one unit or many.

---

## 4. Microservices — independence at a price

Microservices split a system into many small, independently deployable services, each owning its own data and communicating over the network. This is the style that gets the conference talks, and it delivers genuinely valuable things:

- **Independent deployment.** A team ships its service without coordinating a release with everyone else.
- **Independent scaling.** Scale only the service under load, not the whole system.
- **Team autonomy.** A small team can own a service end to end, choose its own tools, and move at its own pace.
- **Fault isolation** — done well, one service failing degrades a feature instead of taking down the system.

Those benefits are real. So are the costs, and they are steep:

```text
   ┌─────────┐   network    ┌─────────┐   network   ┌─────────┐
   │ Orders  │─────────────▶│ Billing │────────────▶│ Ledger  │
   └────┬────┘   may fail   └────┬────┘  may retry   └────┬────┘
        │ own DB                 │ own DB                  │ own DB
     ┌──▼──┐                  ┌──▼──┐                   ┌──▼──┐
     │ DB  │                  │ DB  │                   │ DB  │
     └─────┘                  └─────┘                   └─────┘
   no shared transaction — consistency is now YOUR problem
```

- **Distributed-systems complexity.** Every in-process call becomes a network call that can be slow, fail, or return twice. You now need timeouts, retries, idempotency, and circuit breakers everywhere.
- **Data consistency.** With a database per service, you lose cross-service transactions. Keeping data correct means sagas, outbox patterns, and eventual consistency — real engineering, not a config flag.
- **Operational burden.** Many deployables means service discovery, distributed tracing, centralized logging, per-service CI/CD, and a platform team to keep it all running.
- **Harder debugging.** A single user action fans out across services; understanding what happened means correlating logs and traces across process boundaries.

Much of this ground is covered in the System Design series — see [asynchronous processing](/blog/posts/system-design-06-asynchronous-processing.html) for the messaging and consistency patterns microservices lean on, and [designing a system end to end](/blog/posts/system-design-08-designing-a-system-end-to-end.html) for how these pieces fit together under load.

**The gotcha:** microservices trade in-process simplicity for distributed-systems complexity — network failure, data consistency, and operational overhead you did not have before. That trade is worth making when a real pressure demands it (team scale, independent release cadence, wildly different scaling profiles). It is a bad trade when the only pressure is a résumé or a blog post. Adopting microservices to *look* modern is how teams end up with a distributed monolith: all the network cost, none of the independence.

---

## 5. Service-oriented / service-based — the middle ground

Between the monolith and fine-grained microservices sits a family of coarser service architectures. Classic **SOA** organized an enterprise around shareable services, often coordinated through a central bus that handled routing and transformation — powerful but frequently a bottleneck and a single point of coupling.

A lighter, more current variant is **service-based architecture**: a handful of coarse-grained services (not dozens of tiny ones), often still sharing a single database, deployed separately but without the full microservices ceremony.

```text
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │  Customer  │   │   Orders   │   │  Reporting │
   │  service   │   │  service   │   │  service   │
   └──────┬─────┘   └──────┬─────┘   └──────┬─────┘
          └────────────────┼────────────────┘
                     ┌──────▼──────┐
                     │  shared DB   │   (fewer moving parts
                     └──────────────┘    than microservices)
```

This is a pragmatic middle ground: some deployment independence and team separation, far less operational overhead than microservices, and — because there is often one database — none of the cross-service consistency nightmare. Its cost is that the shared database re-couples the services, so schema changes must be coordinated.

---

## 6. Event-driven architecture — coupling through events

In an event-driven architecture, components communicate by emitting and reacting to events rather than calling each other directly. A producer announces that something happened ("order placed"); any number of consumers react, and the producer neither knows nor cares who they are.

```text
   ┌─────────┐   "OrderPlaced"   ┌──────────────┐
   │ Orders  │──────────────────▶│  Event broker │
   └─────────┘                   └───┬───┬───┬────┘
                                     │   │   │
                       ┌─────────────┘   │   └─────────────┐
                       ▼                 ▼                 ▼
                 ┌──────────┐      ┌──────────┐      ┌──────────┐
                 │ Billing  │      │ Shipping │      │ Analytics│
                 └──────────┘      └──────────┘      └──────────┘
             producer doesn't know its consumers exist
```

The upside is **loose coupling and extensibility**. Adding a new reaction — say, a loyalty-points service that also listens for "order placed" — requires no change to the producer. Events also absorb load spikes: the broker buffers work so a slow consumer does not stall the producer. This is the async backbone described in the System Design series' [asynchronous processing post](/blog/posts/system-design-06-asynchronous-processing.html).

The downside is that the loose coupling that helps you at design time hurts you at debugging time. There is no call stack that spans an event flow; understanding "what happens when an order is placed" means tracing events across many independent handlers. And because reactions happen after the fact, the system is *eventually consistent* — for a window, the order exists but the invoice does not.

**The gotcha:** event-driven decoupling does not remove complexity — it *moves* it, from the call graph into debugging and eventual consistency. You trade "this function calls that function" (easy to follow, hard to extend) for "something reacts to this event, somewhere, eventually" (easy to extend, hard to follow). Both are valid; just know which pain you are signing up for, and invest in tracing and idempotent handlers before you need them.

---

## 7. Serverless / FaaS — functions and glue

Serverless (Function-as-a-Service) pushes decomposition to its extreme: you deploy individual functions, and the platform runs them on demand, scaling from zero to many and back with no servers for you to manage.

```text
   event ──▶ ┌───────────────┐ ──▶ managed service
             │  function()    │      (queue, DB, API)
   event ──▶ │  runs on demand│
             │  scales to 0   │ ──▶ another function
             └───────────────┘
        you write logic; the platform owns the runtime
```

It shines for event glue and spiky, intermittent workloads: image thumbnailing, webhook handlers, scheduled jobs. You pay only for execution time, and idle costs nothing. But the model imposes hard constraints:

- **Cold starts.** A function that has scaled to zero must spin up on the next request, adding latency that hurts user-facing paths.
- **Statelessness.** Functions keep nothing between invocations, so all state lives in external services — which you now coordinate.
- **Vendor lock-in.** Functions bind tightly to one provider's triggers, identity, and services; moving is a rewrite.
- **Observability and limits.** Execution timeouts, cold-start jitter, and fragmented logs make debugging a distributed flow of tiny functions genuinely hard.

Serverless is a superb *complement* — the glue between larger components — and a risky choice as the primary structure of a large, latency-sensitive application.

---

## 8. How to choose — forces, not fashion

The styles above are tools, not a ranking. Choose by naming the forces on your system and picking the cheapest shape that handles them.

**Team size and topology (Conway's Law).** Organizations ship systems whose structure mirrors their communication structure. Three engineers who talk constantly will build — and *should* build — one well-structured deployable; forcing twelve microservices onto them just adds network calls between people who sit together. Fifty engineers in eight teams, by contrast, will strangle a single codebase with merge conflicts and release coordination. Match service boundaries to team boundaries.

**The gotcha:** Conway's Law means your architecture will end up mirroring your org chart whether you plan for it or not. So design the two together. If you want independent services, you need independent teams that own them; if you have one team, one well-modularized deployable is the honest answer. Fighting Conway's Law with an architecture your org can't staff produces services no one clearly owns.

**Scale — and be honest about it.** Ask what actually needs to scale independently. If the whole system scales together, horizontal copies of a monolith are simpler and cheaper. Split out a service only when one part has a genuinely different load or resource profile.

**Deployment independence.** The strongest honest reason to split is release cadence: when teams must ship on separate schedules without a shared release train, separate deployables earn their cost. If everyone still ships together, you are paying distribution's price for none of its benefit.

**Organizational maturity.** Microservices demand a platform: CI/CD per service, centralized logging, distributed tracing, on-call, infrastructure automation. Without that foundation, a microservices adoption mostly produces outages. Be honest about what your org can operate today.

| Style | Strengths | Costs | When to use |
|---|---|---|---|
| Monolith | Simple calls, easy transactions, one deploy | Can't scale/release parts independently | Early stage; small team; simple domain |
| Modular monolith | Monolith simplicity + clean boundaries + cheap extraction | Boundaries need discipline to hold | **Default for most teams and startups** |
| Layered / n-tier | Familiar, clear separation of concerns | Changes cut across layers; pass-through code | Internal organization of a monolith or service |
| Microservices | Independent deploy/scale, team autonomy | Distributed complexity, consistency, ops burden | Large org, many teams, proven scaling pressure |
| Service-based | Some independence, far less overhead | Shared DB re-couples services | Middle ground; a few coarse services |
| Event-driven | Loose coupling, extensible, absorbs spikes | Hard debugging, eventual consistency | Reactive flows, fan-out, decoupled integration |
| Serverless / FaaS | Scale to zero, pay per use, event glue | Cold starts, statelessness, lock-in | Spiky/intermittent workloads; glue code |

The consistent advice — often called **monolith-first** — is to begin with a well-structured (modular) monolith and extract services only when a concrete pressure justifies the cost. Or, put more bluntly: *you must be this tall to ride microservices.* If you cannot deploy the monolith reliably, monitor it well, and staff independent teams, you are not ready for the distributed version of the same problem — you will just have more places for it to break.

---

## Key takeaways

- **There is no silver bullet.** Every style trades one set of problems for another; the architect's job is to pick which problems to have.
- **The modular monolith is the right default** for most teams and startups: monolith simplicity plus clean boundaries, and cheap extraction later when a real pressure appears.
- **Microservices buy independence and pay in distribution** — network failure, data consistency, and operational overhead. Adopt them for measured pressure, never for hype or a résumé.
- **Event-driven and serverless move complexity rather than remove it** — into debugging and eventual consistency, and into cold starts and lock-in respectively.
- **Choose by forces, not fashion.** Team size and topology (Conway's Law), what actually needs to scale, real release-cadence needs, and your org's operational maturity decide the style — not what is trending.

---

## Further reading

- [Martin Fowler — MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html)
- [Martin Fowler — Microservices](https://martinfowler.com/articles/microservices.html)
- [Martin Fowler — Microservice Premium](https://martinfowler.com/bliki/MicroservicePremium.html)
- [Martin Fowler — Conway's Law](https://martinfowler.com/bliki/ConwaysLaw.html)
- [Mark Richards & Neal Ford — *Fundamentals of Software Architecture* (O'Reilly)](https://www.oreilly.com/library/view/fundamentals-of-software/9781492043447/)
