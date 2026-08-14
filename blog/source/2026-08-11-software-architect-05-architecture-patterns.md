# Architecture Patterns

*The recurring structural patterns an architect actually reaches for — layered, hexagonal, DDD boundaries, CQRS, event sourcing, saga, strangler fig, and BFF — each with the problem it solves, the cost it charges, and the honest signal that you need it.*

---

A style is the top-level shape of a system; a *pattern* is a smaller, reusable answer to a recurring structural problem inside that shape. Where the previous post asked "monolith or microservices," this one asks the questions you face next: how do I keep my business logic from rotting into my database code? How do I map the domain onto module boundaries? What do I do when reads and writes want completely different models? How do I migrate a legacy system without a big-bang rewrite?

Patterns are tools, and every tool has a cost. The recurring mistake in this field is not ignorance of patterns — it is applying a heavy one where a light one would do, usually because the heavy one is more interesting to build. So for each pattern below I state three things plainly: the problem it solves, when it earns its keep, and what it charges you. The through-line: **apply the simplest pattern that solves the real problem, and treat CQRS and event sourcing as guilty until proven necessary.**

---

## 1. Layered / n-tier — and the sinkhole

Layered architecture slices a system by technical role: presentation, business logic, data access, database. Calls flow downward — presentation calls business, business calls data — and never the other way. It is the most-taught structure in the industry, and for good reason: it is easy to explain, easy to staff, and gives new developers an obvious answer to "where does this code go."

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

Its strength is familiarity and separation of concerns. Its structural weakness is the **architecture sinkhole**: a request that enters the top layer, passes straight through each layer adding nothing, and hits the database — a "get customer by id" that is four method calls of pure pass-through. When most of your requests are sinkhole requests, the layers are ceremony, not value; you are paying for indirection you never use. A handful of sinkhole flows is fine — the layering pays off elsewhere. When *most* flows are sinkholes, the layering is the wrong tool.

The deeper limitation is direction of dependency: business logic depends *downward* on data access, which means your domain rules import your database concerns. That is exactly the coupling the next pattern is built to break.

---

## 2. Ports & adapters / hexagonal — invert the dependency

Hexagonal architecture (Alistair Cockburn's name; "ports and adapters") and its cousins **clean** and **onion** architecture all share one idea: put the domain at the center and make everything else depend *inward* on it. The domain defines interfaces — *ports* — for what it needs from the outside world. Concrete *adapters* (a Postgres repository, an HTTP handler, a Stripe client) implement those ports. Because the domain owns the interface and the infrastructure implements it, the arrow of dependency points from infrastructure toward the domain, not the reverse.

```text
                 ┌─────────────────────────────┐
   HTTP handler  │        driving adapters       │  CLI, test
      (adapter)  │   ┌───────────────────────┐   │  (adapters)
            ────▶│   │      Application       │   │◀────
                 │   │   ┌───────────────┐    │   │
                 │   │   │    Domain      │    │   │
                 │   │   │  (pure logic,  │    │   │
                 │   │   │  no I/O, no    │    │   │
                 │   │   │  framework)    │    │   │
                 │   │   └───────────────┘    │   │
                 │   │   ports = interfaces   │   │
                 │   └───────────────────────┘   │
            ────▶│      driven adapters          │◀────
   Postgres repo │   (DB, queue, email, APIs)    │  payment gateway
      (adapter)  └─────────────────────────────┘  (adapter)
        the domain declares the port; adapters implement it
        dependencies point INWARD — infra depends on domain
```

The payoff is testability and replaceability. The domain has no imports from your web framework or your database driver, so you can test business rules with fast in-memory fakes and no container. Swapping Postgres for DynamoDB, or REST for gRPC, means writing a new adapter — the domain never changes. In Go this falls out naturally because interfaces are satisfied implicitly and are conventionally declared by the consumer:

```go
// Port: the domain declares what it needs. It knows nothing
// about SQL, HTTP, or any concrete store.
package billing

type Invoice struct {
    ID     string
    Amount int64 // minor units
    Paid   bool
}

type InvoiceStore interface {
    Get(ctx context.Context, id string) (Invoice, error)
    Save(ctx context.Context, inv Invoice) error
}

// Domain service depends on the port, never on an adapter.
type Service struct{ store InvoiceStore }

func NewService(s InvoiceStore) *Service { return &Service{store: s} }

func (s *Service) MarkPaid(ctx context.Context, id string) error {
    inv, err := s.store.Get(ctx, id)
    if err != nil {
        return err
    }
    if inv.Paid {
        return nil // idempotent: already paid
    }
    inv.Paid = true
    return s.store.Save(ctx, inv)
}
```

```go
// Adapter: a concrete implementation lives at the edge and
// depends on the domain's interface — not the other way round.
package postgres

type InvoiceRepo struct{ db *sql.DB }

func (r *InvoiceRepo) Get(ctx context.Context, id string) (billing.Invoice, error) { /* ... */ }
func (r *InvoiceRepo) Save(ctx context.Context, inv billing.Invoice) error         { /* ... */ }

// In tests, a map-backed fake satisfies billing.InvoiceStore too —
// no database required to exercise MarkPaid.
```

**The gotcha:** hexagonal/clean architecture's indirection is worth real money for a complex domain — one with genuine business rules, invariants, and a long life — because it keeps that logic pure, testable, and insulated from infrastructure churn. For a CRUD app that mostly maps HTTP to SQL, the same indirection is pure ceremony: ports, adapters, DTOs, and mappers wrapped around logic that is one line of `INSERT`. Match the pattern to the complexity. A layer of interfaces around code with no behavior to protect is cost with no benefit.

---

## 3. DDD building blocks at the architecture level

Domain-Driven Design supplies the vocabulary that turns "where do I draw boundaries" from taste into method. Two building blocks matter most at the architecture level.

A **bounded context** is a boundary within which a model — its terms, its rules, its data — is internally consistent. "Customer" in the sales context (a lead with a pipeline stage) is a different thing from "Customer" in the billing context (an account with a payment method), and pretending they are one shared model is how you get a tangle that serves neither. Each bounded context becomes a natural seam: a module in a modular monolith, or a service in a distributed system.

An **aggregate** is a cluster of objects treated as a single unit for consistency, with one *aggregate root* as the only entry point. An `Order` with its `LineItems` is an aggregate: you never modify a line item directly, you go through the order, which enforces the invariants (totals add up, a shipped order can't add items). The aggregate is also your transactional boundary — one aggregate, one transaction, is the rule that keeps consistency tractable.

These map straight onto the boundary decisions from the previous post: **a bounded context is a candidate service or module; an aggregate is a candidate transaction.** Get these right and your service boundaries fall out of the domain. Get them wrong and you spend years paying for it.

**The gotcha:** bounded-context boundaries drawn in the wrong place are the single most expensive mistake in this whole post — because they *become your service boundaries* (see [Architectural Styles](/blog/posts/software-architect-02-architectural-styles.html)). A boundary that splits one aggregate across two services turns a local transaction into a distributed one and forces a saga where none was needed. A boundary that fuses two real contexts creates a service two teams fight over. Boundaries are cheap to redraw on a whiteboard and ruinous to redraw in production. Spend the time up front.

---

## 4. CQRS — separate read and write models

Command Query Responsibility Segregation splits the model you write through from the model you read through. Commands (change state) go through one path with rich domain objects and invariants; queries (return state) go through another that can hit denormalized, read-optimized views. In its fuller form the two sides live in separate stores kept in sync asynchronously.

The power is real when read and write needs genuinely diverge: a system that takes a trickle of complex writes but serves a flood of varied read shapes (dashboards, search, reports) benefits from a write model tuned for correctness and read models tuned per query. You scale the two independently and stop contorting one schema to serve both jobs.

The cost is equally real: two models to build and maintain, and — if the read side is updated asynchronously — **eventual consistency**, where a user can complete a write and not immediately see it on the next read. That single fact ripples through your UI, your tests, and your support tickets.

**The gotcha:** CQRS is powerful and *frequently misapplied*. Most systems do not have divergent read and write needs — they have one model that serves both fine — and bolting on CQRS gives them two models, a sync mechanism, and an eventual-consistency window in exchange for nothing. The honest signal is measured divergence: reads that are throttling writes, or read shapes so different from the write shape that one schema can't serve both without pain. Absent that, a single model with a few well-chosen indexes and maybe a read replica is the right answer. Reach for CQRS *inside a bounded context that demonstrably needs it*, not as a default.

---

## 5. Event sourcing — the log is the source of truth

Event sourcing stores state as an append-only sequence of events — `OrderPlaced`, `ItemAdded`, `OrderShipped` — rather than as current rows you overwrite. Current state is *derived* by replaying the events. Nothing is updated in place; nothing is deleted. It pairs naturally with CQRS (the events feed read models) but is a distinct decision.

The superpowers are genuine. You get a **perfect audit trail** for free — the log *is* the history, so "how did this account reach this balance" is answerable to the exact event. You can **replay** the log to rebuild state, to build a brand-new read model after the fact, or to debug by reconstructing exactly what the system knew at any past instant. In regulated domains this is transformative; the [fintech handbook's post on audit trails and event sourcing](/blog/posts/fintech-handbook-03-audit-trails-event-sourcing.html) walks through why finance appends and never mutates.

The costs are the ones teams discover too late:

- **Schema (event) evolution.** Events are immutable and live forever, so a v1 event you emitted two years ago must still be replayable today. You need versioning and upcasting strategies from day one; you cannot just "migrate the table."
- **Rebuilds.** Deriving state by replaying millions of events is slow, so you maintain snapshots — and snapshotting is its own subsystem to build and test.
- **Eventual consistency.** Read models trail the log, with all the consequences from the CQRS section.
- **Query difficulty.** "Show me all open orders" is a single `SELECT` against a state table and a projection you must build and keep current against an event log.

**The gotcha:** event sourcing is the most over-applied pattern in this post. It is *spectacular* for a subset of domains — ledgers, anything with a legal audit requirement, anything where "how did we get here" is a first-class question — and it is a tax with no return for the rest. Before adopting it, ask: do I actually need the full history, or do I just need an `updated_at` column and an audit log table? The latter answers most needs at a fraction of the cost. Use event sourcing where the append-only log *is* the business requirement, not because replay sounds powerful.

---

## 6. Saga — transactions across services

Once a business operation spans multiple services (or multiple aggregates), you can no longer wrap it in one database transaction. A **saga** coordinates it as a sequence of local transactions, each with a **compensating action** that semantically undoes it if a later step fails. Book flight → charge card → reserve hotel; if the hotel step fails, you compensate by refunding the card and cancelling the flight. There is no rollback — only forward steps and their compensations.

Sagas come in two flavors:

- **Choreography** — each service reacts to events and emits its own; no central coordinator. Loosely coupled and simple to start, but the overall flow is implicit, scattered across handlers, and hard to see whole.
- **Orchestration** — a coordinator explicitly drives each step and invokes compensations on failure. The flow lives in one place and is easy to reason about, at the cost of a component that knows about everyone.

```text
   Orchestrated saga (happy path, then a failure)

   [Coordinator]──▶ Charge card ──▶ Reserve hotel ──▶ Book flight ✓
        │
        │  hotel step FAILS ↓
        └──▶ compensate: Refund card ◀── (no forward step remains)
        each step has a compensating action; there is no rollback
```

This is the consistency machinery microservices lean on, and it builds directly on the messaging patterns in the System Design series' [asynchronous processing post](/blog/posts/system-design-06-asynchronous-processing.html). The cost is that compensations are real business logic you must design (a refund is not a database rollback), and the system is eventually consistent throughout the saga's lifetime. The best way to avoid a saga is to draw aggregate boundaries so a given operation stays inside one transaction — which loops right back to getting your DDD boundaries right.

---

## 7. Strangler fig — migrate without a rewrite

Named by Martin Fowler after the vine that grows around a host tree until it can stand alone, the **strangler fig** pattern replaces a legacy system incrementally instead of in one terrifying big-bang cutover. You put a routing layer (a proxy or gateway) in front of the old system, then build new functionality — or reimplement old functionality — in a new system behind it. Route by route, you redirect traffic from old to new; when nothing routes to the legacy system anymore, you retire it.

```text
   client ──▶ ┌── facade / router ──┐
              │  /orders   ──▶ NEW  │   migrated slices go new
              │  /billing  ──▶ NEW  │
              │  /reports  ──▶ OLD  │   not-yet-migrated go old
              └─────────────────────┘
        traffic shifts route-by-route until OLD serves nothing
```

The value is risk reduction: every step is small, reversible, and shippable, and the business keeps running throughout. The cost is living with both systems at once and maintaining the facade — real overhead, but far cheaper than the failure rate of big-bang rewrites. This pattern gets its own full treatment later in the series when we look at evolving and migrating systems.

---

## 8. BFF and gateway — shaping the edge

At the boundary between clients and services, two patterns recur. An **API gateway** is a single entry point that fronts many services and handles cross-cutting edge concerns — routing, auth, rate limiting, TLS termination — so each service doesn't reimplement them. A **Backend for Frontend (BFF)** goes further: a dedicated backend per client type (web, mobile, partner API), each shaping and aggregating downstream calls for exactly that client's needs, so a mobile app isn't forced through the same chatty, over-fetching API as a desktop dashboard.

The gateway centralizes edge concerns; the BFF trades a little duplication for client-specific fit and lets each client team own its own aggregation layer. The cost of both is another hop and another component to operate — worth it when you have several distinct clients or genuine cross-cutting edge logic, overkill for a single web app talking to one service.

---

## Pattern → problem → cost, at a glance

| Pattern | Problem it solves | What it costs |
|---|---|---|
| Layered / n-tier | Organize code by technical role | Sinkhole pass-through; domain depends on data layer |
| Hexagonal / clean | Isolate domain from infrastructure; testability | Indirection, ceremony — dead weight on a CRUD app |
| Bounded context | Where to draw module/service seams | Wrong boundary = wrong (expensive) service boundary |
| Aggregate | Consistency unit and transaction boundary | Over-large aggregates hurt concurrency |
| CQRS | Read and write needs genuinely diverge | Two models; eventual consistency if async |
| Event sourcing | Perfect audit + replay is a requirement | Event versioning, snapshots, rebuilds, hard queries |
| Saga | Consistency across services/aggregates | Compensations are real logic; eventual consistency |
| Strangler fig | Migrate legacy without a big-bang rewrite | Two systems + facade running in parallel |
| BFF / gateway | Client-specific shaping; centralize edge concerns | Extra hop and component to operate |

---

## Key takeaways

- **Patterns are tools with costs.** Apply the simplest one that solves the real problem; complexity you add "to be safe" is complexity you pay for forever.
- **Hexagonal earns its keep on a complex domain and is ceremony on a CRUD app.** Let the domain declare ports; let adapters at the edge implement them — but only when there is real logic worth protecting.
- **Your DDD boundaries decide everything downstream.** A bounded context becomes a service; an aggregate becomes a transaction. Getting a boundary wrong is the most expensive mistake here.
- **CQRS and event sourcing are guilty until proven necessary.** They add two models, eventual consistency, and rebuilds. Use them where the divergence or the audit requirement is real and measured — not by default.
- **A pattern copied without its context is cargo cult.** Every pattern here was born from a specific pressure; adopt it because you feel that pressure, not because it is fashionable.

---

## Further reading

- [Alistair Cockburn — Hexagonal Architecture (Ports and Adapters)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Robert C. Martin — The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Martin Fowler — CQRS](https://martinfowler.com/bliki/CQRS.html)
- [Martin Fowler — Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Martin Fowler — Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html)
- [microservices.io — Pattern: Saga](https://microservices.io/patterns/data/saga.html)
- [Sam Newman — Pattern: Backends For Frontends](https://samnewman.io/patterns/architectural/bff/)
