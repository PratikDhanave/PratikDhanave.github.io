# Postgres/pgvector vs a Dedicated Vector Database

*The vector-storage decision has a boringly practical answer that cuts against the hype: for most systems, the database you already run with a vector extension beats adding a new specialized system — until scale or specific features force the upgrade.*

Building RAG means storing embeddings and searching them by similarity, and that raises a decision teams often over-think: use a vector extension on your existing database (like `pgvector` on Postgres) or adopt a dedicated vector database (Qdrant, Milvus, Weaviate, Pinecone, and others)? The marketing pushes you toward specialized systems; the engineering usually pushes back. This final post in the AI Architecture Decisions series works through it. (Retrieval is treated in depth in the [Agentic RAG](/blog/series/agentic-rag/) series; this is the storage chooser.)

## The two options

- **Vector extension on your existing database** — `pgvector` turns Postgres into a vector store: store embeddings alongside your relational data, index them (HNSW or IVFFlat), and query by similarity with ordinary SQL. No new system to run; your embeddings live next to the data they relate to. Similar extensions exist for other databases.
- **Dedicated vector database** — a purpose-built system (Qdrant, Milvus, Weaviate, Pinecone, etc.) engineered specifically for high-scale vector search: optimized ANN indexes, advanced filtering, distributed scaling, and vector-specific features, run as its own service (self-hosted or managed).

The trade is the familiar one: reuse what you run vs adopt a specialized system. And the underrated cost of the specialized option is *operational* — a dedicated vector DB is another system to deploy, monitor, back up, secure, and keep in sync with your source of truth.

## The case for "just use Postgres"

For a large fraction of systems, `pgvector` (or your existing DB's vector extension) is the right call, and the reasons are practical rather than exciting:

- **One less system to operate.** You already run, monitor, back up, and secure Postgres. Adding vectors to it adds a column and an index, not a new service, a new failure mode, and a new thing to keep in sync.
- **No sync problem.** When embeddings live in the same database as the records they describe, a document and its vector update in the *same transaction* — no dual-write, no drift between your source of truth and a separate vector store. With a dedicated DB, keeping the two in sync (and handling deletes/updates/erasure) is real, ongoing work.
- **Relational + vector together.** You can filter by ordinary SQL predicates (tenant, permissions, date) *and* do similarity search in one query, with real transactions and joins. Metadata filtering for access control and freshness is just a `WHERE` clause.
- **It's enough for most scales.** For thousands to millions of vectors — where a great many real RAG systems live — Postgres with an HNSW index performs well.

The honest default, matching this series' theme: start with the database you already run. Adopt a specialized system when you've measured a specific need it doesn't meet, not preemptively.

## When a dedicated vector database earns it

There are real reasons to reach for a specialized system, and they're about scale and vector-specific capability:

- **Very large scale.** At hundreds of millions or billions of vectors, or very high query throughput, purpose-built systems with distributed sharding and heavily-optimized ANN indexes outperform a general database. This is their home turf.
- **Advanced vector features.** Sophisticated hybrid search, multiple index types tuned per workload, advanced quantization, and vector-native filtering that a general DB's extension doesn't match.
- **Performance at the edge of recall/latency.** When you need to tune the recall/latency/memory trade-off precisely at scale, specialized systems expose more knobs.
- **Vectors are the primary workload.** If your system is fundamentally a vector-search product (not an app that also does similarity search), a system built for that is a better fit.

The pattern: dedicated vector databases win at *scale* and on *vector-specific sophistication*. Below that, their advantages don't justify the operational cost of a separate system.

## The decision, and the mistake to avoid

The mistake is adopting a dedicated vector database *by default* because it's the "proper" AI-native choice, before you have the scale or features that justify it — paying operational and sync costs for capability you don't yet need. The better path: begin with your existing database's vector extension, measure it against your real corpus size, query volume, and latency needs, and migrate to a dedicated system when (and only when) you hit a wall it solves. Because embeddings and the retrieval layer should be somewhat swappable anyway (changing the embedding model already forces re-embedding, per the data-foundations discussion), moving from pgvector to a dedicated DB later is a bounded migration, not a rewrite — which makes "start simple" low-risk.

## Pick this when

- **Postgres/pgvector (or your existing DB's extension)** — thousands to millions of vectors, you already run the database, you want embeddings transactionally beside your data with SQL filtering, and you'd rather not operate a new system. The right default for most RAG systems.
- **Dedicated vector database** — hundreds of millions/billions of vectors or very high query throughput, you need advanced vector-specific features or fine-grained recall/latency tuning, or vector search *is* the product — and you can bear operating another system.
- **Start simple, migrate on evidence** — begin with the extension, measure against your real workload, and move to a dedicated system only when you hit a wall it specifically solves.

## Key takeaways

- The choice is reuse-what-you-run (`pgvector` on Postgres) vs adopt-a-specialized-system (Qdrant/Milvus/Weaviate/Pinecone); the underrated cost of the latter is operating and syncing a whole extra system.
- For most systems (thousands to millions of vectors) the existing-database extension wins: one less system to run, no embedding-vs-source sync problem (same transaction), combined SQL filtering + similarity, and enough performance.
- Dedicated vector databases earn their cost at very large scale/throughput, for advanced vector-specific features and fine-grained recall/latency tuning, or when vector search is the primary product.
- The common mistake is adopting a dedicated vector DB by default before you have the scale to justify it — paying operational and sync costs for unneeded capability.
- Start with your existing database's vector extension, measure against your real corpus and query load, and migrate on evidence — a bounded migration, since the retrieval layer should be swappable anyway.

## Further reading

- [Agentic RAG series](/blog/series/agentic-rag/)
- [The AI Production Roadmap series](/blog/series/the-ai-production-roadmap/)
- [AI Architecture Decisions — start of the series](/blog/posts/ai-decisions-01-how-to-choose.html)
