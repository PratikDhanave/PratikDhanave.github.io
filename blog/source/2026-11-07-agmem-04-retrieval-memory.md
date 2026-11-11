# Retrieval Memory — Vector Stores, Scoring, and the Art of Remembering the Right Thing

*The standard answer to agent memory is "embed it and put it in a vector store" — and it's half right. Semantic search over past experience is genuinely the workhorse of episodic recall. But raw similarity is a weak model of what "relevant memory" means: similar is not important, recent, or true. The difference between a memory system and a junk drawer with an embedding index is the scoring, filtering, and hygiene this post covers.*

Post [3](/blog/posts/agmem-03-conversation-memory-and-compaction.html) ended with demotion: what leaves the window lands in a durable store. This post is about getting it back out well. It builds on ideas from [Agentic RAG](/blog/series/agentic-rag/) and [Vector Search Internals](/blog/series/vector-search-internals/) — but memory retrieval differs from document RAG in ways that matter, and treating them as identical is a design error this post keeps returning to.

## Memory retrieval is not document RAG

Document RAG retrieves from a corpus that is curated, mostly static, and written to be read. Memory retrieval works against a store that is **self-generated, append-heavy, time-sensitive, and full of near-duplicates** — every session deposits more, much of it mundane, some of it superseded. Three differences drive the design:

- **Time matters intrinsically.** A document's age is metadata; a memory's age changes its meaning. "The user prefers X" from yesterday and from last year are different claims.
- **Truth decays.** Documents are replaced by editors; memories are contradicted by newer memories, and the store keeps both unless something reconciles them (post 2's semantic-update problem).
- **The query is implicit.** A RAG system answers a user's explicit question; a memory system must decide *what the current moment calls for* — often with no question at all, just a task state that certain memories would help.

## Scoring: similarity is one signal of three

The design that has become canonical scores candidate memories on a blend, not similarity alone:

- **Relevance** — embedding similarity to the current query or task state. Necessary, insufficient.
- **Recency** — an exponential decay on time since the memory was created or last used. This captures truth-decay cheaply: fresher memories win ties, stale ones fade without being deleted.
- **Importance** — a stored weight reflecting how much the memory mattered: user corrections, explicit "remember this," decisions, and failures score high; routine chatter scores low. Assigned at write time (a cheap model call rates it, or the harness flags structurally-important events like corrections and errors).

The blend (a weighted sum works; exact weights are an eval problem, post 8) fixes the characteristic vector-only failures: the hundredth similar-but-trivial greeting outranking the one crucial constraint, and a long-dead decision surfacing as if current. Two refinements earn their complexity quickly: **last-accessed reinforcement** (retrieving a memory refreshes its recency — frequently-useful memories stay warm, a direct borrow from how human recall strengthens with use) and **retrieval-triggered reconciliation** (when top-scoring memories contradict each other, surface the conflict to the consolidation process rather than injecting both).

## Write-side hygiene decides read-side quality

Most retrieval-memory failures are written, not read. The store degrades without discipline at insert time:

- **Select before storing.** Post 1's selection problem lands here: embedding every message produces a store that is mostly noise. Store summaries of episodes (post 3's output), extracted facts, decisions, and failures — not raw transcript by default.
- **Write for the future reader.** A memory retrieved months later arrives without its surrounding context. "She said to use the second option" is garbage at retrieval time; "User (Dana) chose Postgres over DynamoDB for the orders service, citing team familiarity — 2026-03-04" is a memory. Contextual self-containment at write time is the highest-ROI habit in this whole series.
- **Deduplicate at the door.** Sessions re-establish the same facts repeatedly; naive insertion yields fifty copies of "user prefers Go" that crowd out everything else in any top-k. Near-duplicate detection at write time (same embedding neighborhood + same claim) should update the existing memory — count, recency — rather than insert.
- **Attach structure.** Type (episode/fact/decision/failure), entities involved, source session, confidence. Retrieval that can filter by type and entity before ranking by score is dramatically more precise than pure nearest-neighbor over everything — and it's what post 5's structured memory builds into a first-class representation.

## Injection: the last foot of the problem

Retrieved memories must still enter the window well. Three practices prevent the common injuries. **Budget strictly** — memory competes with task context for tokens; a handful of high-scoring memories under a hard token budget beats a generous top-k that crowds out the actual work. **Label provenance** — injected memories should be visibly memories ("From memory (2026-08-12, confidence: high): …"), so the model can weigh them rather than absorb them as present-tense ground truth; this single formatting habit defuses most stale-memory incidents. **Let the agent ask** — beyond automatic injection, expose retrieval as a tool the agent can call ("search memory for how we fixed the auth flake") — recall-on-demand catches what the implicit query missed, and is the bridge to post 6, where memory becomes something the agent actively operates rather than passively receives.

The takeaway: vector search is the right engine and the wrong whole answer — memory retrieval differs from document RAG because the store is self-generated, time-sensitive, and self-contradicting. Score on **relevance × recency × importance** (with last-accessed reinforcement), enforce **write-side hygiene** — select, write self-contained, dedupe at the door, attach structure — and inject with budget, provenance labels, and an on-demand retrieval tool. The store you can trust is the one you were disciplined about filling.

## Key takeaways

- Memory retrieval ≠ document RAG: the store is **append-heavy, near-duplicated, and truth-decaying**, and the "query" is often implicit task state.
- Score candidates on three signals — **relevance** (similarity), **recency** (exponential decay), **importance** (write-time weight; corrections/decisions/failures high) — not similarity alone; reinforce recency on access.
- Write-side hygiene decides quality: store selected summaries/facts not raw transcript, write memories **self-contained** (entities, dates, outcomes), **dedupe at insert** (update, don't re-add), attach type/entity structure for pre-filtering.
- Inject under a hard token **budget**, with **provenance labels** ("From memory (date, confidence)") so memories are weighed, not absorbed as current truth.
- Also expose memory as a **tool the agent can query** — recall-on-demand catches what automatic injection misses, and leads into post 6's agentic memory.

## Further reading

- [Vector database — the engine under episodic recall](https://en.wikipedia.org/wiki/Vector_database)
- [Information retrieval — ranking under more signals than similarity](https://en.wikipedia.org/wiki/Information_retrieval)
