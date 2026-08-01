# On-Chain Event Indexing and Chain-Data Pipelines

*Turning raw blocks and logs into queryable app state that survives reorgs, backfills, and finality.*

A blockchain node is an excellent source of truth and a terrible application database. It answers "what is the log at block N, index K?" cheaply, but "what is this account's token balance right now, and how did it change over the last month?" is a full-table scan across millions of blocks. An **indexer** closes that gap: it reads blocks and event logs, decodes them against contract ABIs, and materializes the result into tables an application can query in milliseconds. The hard part is not the reading. It is keeping the materialized state *correct* while the chain underneath it rewrites recent history.

This post walks the pipeline end to end, then focuses on the three engineering problems that separate a demo indexer from one you can bill customers against: idempotent writes, reorg rollback, and consistency with finality.

## The shape of the pipeline

At a high level the data moves through five stages: sources, ingest, decode plus write, store, and serve.

```
 SOURCES        INGEST         DECODE + WRITE        STORE          SERVE
 ┌────────┐                    ┌──────────┐
 │ ABI    │───contract ABIs──▶ │ Log      │
 │Registry│                    │ Decoder  │──┐
 └────────┘                    └──────────┘  │ typed events
 ┌────────┐   ┌──────────┐                   ▼
 │ Chain  │──▶│  Block   │──raw logs──▶ ┌──────────┐   upsert   ┌────────┐   ┌───────┐
 │ Node   │   │ Ingestor │             │ Reorg-Safe │─────────▶ │ Index  │──▶│ Query │──▶ App
 └────────┘   └────┬─────┘             │  Writer    │           │ Store  │   │  API  │
 (blocks+logs)     │ parent hash       └────▲───────┘           └────────┘   └───────┘
                   ▼                        │ rollback range      (finalized)   (balances
              ┌──────────┐                  │                                    + history)
              │  Reorg   │──────────────────┘        ┌───────────┐
              │ Detector │       checkpoint (safe head)│Checkpoint │
              └──────────┘◀───────────────────────────└───────────┘
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-onchain-event-indexing.html)** — Block ingestion, ABI decoding, reorg-safe writes, and serving balances and history.

The consumer at the far right never talks to the chain node directly. It reads a curated store that the indexer keeps consistent. Everything interesting happens in the middle three stages.

## Ingesting blocks in order

The ingestor pulls two things per block: the header (number, hash, parent hash, timestamp) and the receipts, which carry the event logs. Two delivery modes coexist. A WebSocket subscription pushes new heads with low latency but drops messages on reconnect; a polling loop over `getBlockByNumber` is slower but gives you replay control. Production ingestors run both — subscribe for freshness, poll to close gaps — and treat the poll loop as the source of truth.

The non-negotiable invariant is **ordered, gapless processing**. The indexer keeps a cursor: the highest block number it has fully processed. It only ever advances the cursor by one, and only after that block's writes have committed. If block 1,000,041 arrives while the cursor sits at 1,000,038, the ingestor fetches 39 and 40 first. Skipping a block silently corrupts every downstream aggregate, and the corruption is invisible until someone reconciles a balance by hand.

## Decoding logs against ABIs

A raw log is opaque bytes: an ordered list of `topics` (indexed parameters, the first of which is the event signature hash) and a `data` blob (non-indexed parameters, ABI-encoded). To make it meaningful you need the contract's ABI. The decoder maintains an **ABI registry** keyed by contract address, matches `topics[0]` against known event signatures, and unpacks the remaining topics and data into typed fields.

Two realities make this messier than it sounds. Contracts get upgraded behind proxies, so the same address can emit differently shaped events over its lifetime — the registry has to be versioned by block range, not just by address. And you will encounter logs you cannot decode, either because the ABI is missing or because a signature collides. The decoder should record the raw log with a "undecoded" marker rather than dropping it. A gap you can see and backfill later is recoverable; a log you silently discarded is gone.

## Writing idempotently: the (block, log index) key

Every event in a block has a stable, unique coordinate: its block number and its **log index** within that block. That pair is the natural primary key for the events table, and it is the single most important design decision in the whole pipeline.

Keying writes by `(block_number, log_index)` turns every insert into an **idempotent upsert**. Reprocess the same block ten times — because a subscription hiccuped, because a backfill overlapped the live tip, because a deploy replayed a range — and you get exactly one row per event. This is what lets the rest of the system be sloppy in safe ways. The ingestor can re-fetch a block it is unsure about. A backfill worker can march through history while the live indexer runs, and the overlap in the middle simply overwrites identical data. Without this key, "at-least-once" delivery becomes "double-counted balances," and you are back to hand reconciliation.

Derived state — token balances, position sizes, running totals — is computed from the event rows, not written independently. Recomputing a balance from its event history must always yield the same number. If it does not, the derivation, not the events, is where your bug lives.

## Surviving reorganizations

Here is the fact that breaks naive indexers: **recent blocks are not final.** A chain can discard the last few blocks and replace them with a different history — a reorganization, or reorg. If your indexer wrote events from the discarded blocks, your database now contains transactions that, as far as the canonical chain is concerned, never happened.

Detection is a parent-hash check. When the indexer processes block N, it verifies that block N's `parentHash` equals the hash it stored for block N-1. If they match, the chain is intact. If they diverge, a reorg has occurred, and the indexer walks backward until it finds the last block whose stored hash still matches the chain — the fork point.

Recovery is a **rollback range**. Every write carries its block number, so reverting is a delete of all rows with `block_number > fork_point`, followed by reprocessing the new canonical blocks from the fork point forward. Because writes are keyed by `(block, log index)`, the reprocess is just more idempotent upserts. Derived balances are recomputed for the affected accounts. The rollback is bounded: reorgs deeper than a handful of blocks are extraordinarily rare, so you only ever revert a small tail.

## Consistency with finality

Reorgs motivate the last piece: the indexer distinguishes the **live head** from the **finalized head**. Most chains expose a finality signal — a block depth or a checkpoint beyond which reorgs cannot occur. The indexer advances a **safe-head checkpoint** only past finalized blocks.

This gives you two serving modes. Queries that demand correctness — settlement, accounting, anything that moves money — read only up to the finalized checkpoint, where data can never be rolled back. Queries that want freshness — a pending-activity feed — can read to the live head with an explicit "unconfirmed" flag. The checkpoint is also your restart anchor: on crash, the indexer resumes from the last finalized cursor and re-derives the unfinalized tail, because that tail is cheap to rebuild and unsafe to trust.

## Backfills without downtime

Launching against a chain with years of history means backfilling. Run backfill as a separate worker that processes historical ranges in parallel, writing through the same idempotent path as the live indexer. Because the key is `(block, log index)`, the backfill and the live tip can overlap with zero coordination — whichever writes a given event last writes identical bytes. Track per-range completion so a crashed backfill resumes mid-history instead of restarting, and only expose a contract's data to the API once its backfill has reached the range users will query.

## What holds it together

Strip away the vocabulary and an on-chain indexer is a stream processor with three unusual constraints: its input can rewrite its own recent past, its output must be queryable like a warehouse, and "correct" is defined by a finality rule rather than a wall clock. The `(block, log index)` key makes writes idempotent, parent-hash detection plus a bounded rollback range makes them reorg-safe, and a finalized checkpoint makes the whole thing consistent with what the chain will actually keep. Get those three right and everything else — backfills, retries, multiple contracts — reduces to replaying the same safe write.
