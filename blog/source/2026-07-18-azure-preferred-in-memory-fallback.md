# Azure-Preferred, In-Memory Fallback
*Same interface, two implementations: cloud-backed stores when config exists, in-memory when it doesn't. The whole service boots with zero external dependencies.*

There is a failure mode I have watched teams walk into again and again. You clone the repo, run `make test`, and it hangs — because the test suite wants a database, and the database wants a connection string, and the connection string wants a cloud subscription, and the subscription wants a login you don't have on a Friday afternoon. The app cannot run without the cloud. Nobody decided this on purpose. It accreted, one hard dependency at a time.

On a governed multi-agent system I built with the Microsoft Agent Framework in Python on Azure, I refused to let that happen. The rule was simple: the cloud is preferred, never required. Every persistence concern hides behind an interface with two implementations — an Azure-backed one for real deployments, and a dead-simple in-memory one for everything else. The service picks which to wire at startup based on whether cloud config is present. Boot it with no config and it comes up clean, in memory, with zero external dependencies.

## Three stores, two shapes each

The system had three durable concerns worth abstracting:

- an **audit store**, backed by Azure Cosmos DB, that records every governed action for later review;
- a **checkpoint store**, also on Cosmos, that snapshots workflow state so a long-running agent run can resume;
- a **knowledge store**, backed by Azure AI Search, that indexes documents for retrieval.

Each one is defined as a `Protocol` — a structural interface, no inheritance required. For each `Protocol` there are two concrete types. `CosmosAuditStore` talks to a real Cosmos container; `InMemoryAuditStore` appends to a list. `AzureSearchKnowledgeStore` issues vector queries; `InMemoryKnowledgeStore` does a linear scan over a dict. The in-memory versions are intentionally trivial — a few dozen lines each. They are not a mock and not a stub in the testing sense. They are a real, correct, non-durable implementation of the same contract.

That distinction matters. A mock asserts on calls. These adapters actually store and return data, so the code paths that exercise them behave like production, minus durability. Tests read back what they wrote. The retrieval logic runs for real against the linear scan.

## The composition root decides

The selection lives in exactly one place: a wiring module with no business logic in it. This is the composition root — the single spot allowed to know which concrete class satisfies which interface. Everything else in the codebase depends only on the `Protocol`, never on `Cosmos` or `Search` directly.

```
                         ┌───────────────────────────┐
                         │      composition root      │
                         │   (wiring only, no logic)  │
                         └─────────────┬─────────────┘
                                       │
                        reads AZURE_* config present?
                                       │
                 ┌─────────────yes─────┴─────no─────────────┐
                 ▼                                           ▼
     ┌───────────────────────┐                 ┌───────────────────────┐
     │  CosmosAuditStore     │                 │  InMemoryAuditStore   │
     │  CosmosCheckpointStore│                 │  InMemoryCheckpoint   │
     │  AzureSearchKnowledge │                 │  InMemoryKnowledge    │
     └───────────┬───────────┘                 └───────────┬───────────┘
                 │                                          │
                 └──────────────────┬───────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │   AuditStore / CheckpointStore │
                    │   / KnowledgeStore  (Protocol) │
                    └───────────────┬───────────────┘
                                    ▼
                    agents, workflows, API handlers
                    depend on the interface only
```

The rest of the application never learns which branch was taken. It receives an `AuditStore` and calls `.record(...)`. Whether that write lands in a Cosmos partition or a Python list is not its concern, and that is the whole point.

Here is the shape of it, generically:

```python
from typing import Protocol

class AuditStore(Protocol):
    def record(self, event: dict) -> None: ...
    def query(self, actor: str) -> list[dict]: ...

class CosmosAuditStore:
    def __init__(self, client): self._c = client
    def record(self, event): self._c.upsert_item(event)
    def query(self, actor): return self._c.query(actor)

class InMemoryAuditStore:
    def __init__(self): self._events: list[dict] = []
    def record(self, event): self._events.append(event)
    def query(self, actor):
        return [e for e in self._events if e["actor"] == actor]

def build_audit_store(cfg) -> AuditStore:
    if cfg.cosmos_endpoint:
        return CosmosAuditStore(make_cosmos_client(cfg))
    return InMemoryAuditStore()
```

`build_audit_store` is the only function that mentions both classes. Delete the cloud account and it still returns a valid `AuditStore`.

## What this buys you

**Local dev needs no cloud account.** A new contributor clones, runs, and the service is up in seconds against in-memory stores. No `az login`, no provisioning, no shared dev subscription that three people are fighting over.

**Tests are hermetic and fast.** The suite wires the in-memory adapters and runs with no network, no credentials, no flaky cloud latency. A hermetic test suite is one that produces the same result on a laptop, in CI, and on a plane with the wifi off. That is only possible if the cloud is optional.

**The boundary documents itself.** Because the seam is a real interface with two honest implementations, the interface *is* the spec for what a store must do. When someone later writes a third adapter — Postgres, say — the `Protocol` tells them exactly what to satisfy, and the in-memory version is the reference behavior to match.

I extended the same idea to operations. A `DEPLOY_MODE=simulated` flag lets the deploy and smoke-test scripts run their full sequence — validate config, exercise the store contracts, report readiness — without provisioning anything or spending a cent. You get the choreography of a deploy in CI without the bill.

## The honest framing

I want to be precise, because this is easy to oversell. The in-memory stores are **by design, not a bug**. They are a proof-of-concept choice appropriate to a system whose durability needs were still being validated. In-memory means data does not survive a restart, does not scale past one process, and has no retention or indexing guarantees. That is fine for dev, test, and demos. It is not fine for production, and the code says so.

So the repo ships a documented "PoC → production" path: the audit and checkpoint stores swap to managed Cosmos with retention policies; the knowledge store swaps to a provisioned Azure AI Search index with the right analyzers; the simulated deploy mode gives way to real infrastructure-as-code. None of that changes a line of agent or workflow code, because none of that code ever depended on the concrete stores. Only the composition root changes.

## Why it matters

This is not a novel pattern. It is ports-and-adapters, it is dependency inversion, it is the oldest advice in the book: define the interface, ship a trivial adapter, select by config. What is novel is only how consistently teams abandon it the moment there is schedule pressure — they inline the Cosmos client into a handler "just for now," and six months later nobody can run the app without a subscription and the test suite takes four minutes because every case round-trips to a real database.

The seam is cheap to build and it pays rent forever: developer experience that starts in seconds, a test suite that runs anywhere in milliseconds, and a production boundary that is documented for free because it is expressed as code. Do not let the cloud be a hard dependency for `make test`. Make it preferred. Never make it required.
