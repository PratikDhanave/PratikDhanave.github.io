# Semantic and Hybrid Search — Matching by Meaning

*Keyword search has one incurable weakness: it matches words, not meaning, so it misses relevant results that use different vocabulary than the query. Semantic search fixes this by representing queries and documents as vectors of meaning and matching by proximity in that space — the technology behind modern RAG. But the surprising lesson of production search is that semantic didn't replace keyword; the best systems combine them. This post explains vector search and why hybrid retrieval wins.*

Post 4 named BM25's ceiling (the vocabulary gap), and post 6 traced the path toward learned, embedding-based retrieval. This post completes the arc: how semantic search works, why it's powerful, where it's weak, and why hybrid retrieval — the combination of BM25 and vectors — is the modern default and the backbone of RAG. (This blog has a dedicated *Vector Search Internals* series for the indexing details; here we focus on the IR picture.)

## Semantic search: matching meaning, not words

The core idea is to stop matching words and start matching **meaning**, using **embeddings** (ML series, post 7): a neural model maps any text — a query or a document — into a dense vector in a high-dimensional space, arranged so that texts with *similar meaning* sit close together, regardless of the words they use.

- "car," "automobile," and "vehicle" land near each other even though they share no letters.
- "how do I make my app faster?" lands near a document about "reducing application latency" though they share almost no words.

Search then becomes **nearest-neighbor retrieval** in vector space: embed the query, find the documents whose vectors are closest (by cosine similarity), return them. This directly dissolves BM25's vocabulary gap (post 4) — relevance is judged by *meaning*, so synonyms, paraphrases, and conceptual matches are found automatically, with no hand-maintained synonym lists (post 3). It's why semantic search feels like it "understands" the query, and why it became the retrieval mechanism for **RAG**: given a user's question, embed it, retrieve the semantically closest document chunks, and feed them to the LLM.

Two pieces make it practical, both covered deeply in the Vector Search series: an **embedding model** (what turns text into meaningful vectors — the quality of retrieval rests on it) and a **vector index** using **approximate nearest neighbor (ANN)** search, because exact nearest-neighbor over millions of high-dimensional vectors is too slow — ANN trades a tiny bit of accuracy for the speed that makes semantic search scale, the vector-space analog of the inverted index's role for keywords.

## Why semantic search isn't a free upgrade

It's tempting to conclude vectors make keyword search obsolete. Production experience says otherwise — semantic search has real, complementary weaknesses:

- **It's weak at exact matches.** Embeddings capture *meaning*, which blurs *specifics*: exact product codes, error numbers, names, acronyms, rare technical terms, and precise phrases. A search for a specific SKU, a function name, or "error 0x80070057" is exactly where semantic search struggles and keyword search excels — the embedding smears the exact string into its neighborhood. The very fuzziness that bridges the vocabulary gap *loses* exactness.
- **It can retrieve the plausibly-related-but-wrong.** Because it matches on semantic similarity, it can surface documents that are topically near but don't actually answer the query — "about the same thing" isn't "contains the answer."
- **It depends entirely on the embedding model.** Retrieval quality is capped by the embedding model's quality and its domain fit; an embedding trained on general text may not place *your* domain's jargon correctly, and it has a knowledge cutoff of its own.
- **It's harder to interpret and debug.** "Why did this rank high?" has a clean answer for BM25 (these terms matched, with these weights) and a murky one for vectors (it was close in a 768-dimensional space).

So semantic and lexical search have *opposite* strengths: keyword nails exact terms and is interpretable but misses meaning; semantic captures meaning but blurs specifics. Neither dominates — which points directly at combining them.

## Hybrid search: the best of both, and the modern default

The production answer is **hybrid search** — run *both* a keyword (BM25) retriever and a semantic (vector) retriever, and combine their results:

- **BM25** contributes exact-term precision, rare-term and phrase matching, and interpretability.
- **Vector search** contributes semantic recall — finding relevant results that use different words.
- Their results are **fused** (commonly by reciprocal-rank fusion, or by feeding both scores into a learned reranker from post 6), so a document benefits from matching either lexically *or* semantically.

Hybrid consistently outperforms either alone, because the two methods fail on *different* queries: hybrid catches the exact-match query that vectors fumble *and* the conceptual query that keywords miss. This is why serious RAG and search systems are hybrid, and often add a **reranker** (post 6) as a final precision stage over the fused candidates — the retrieve-then-rank, multi-signal architecture that recurs everywhere in retrieval.

The meta-lesson closes the series' arc: the history of search is not "new method replaces old" but "methods accumulate and combine." The inverted index (post 2), BM25 (post 4), learning to rank (post 6), and semantic search all coexist in a modern system, each doing what it does best. Semantic search was the most important addition in years because it finally addressed the vocabulary gap that limited search from the beginning — but it joined the toolkit rather than emptying it. Understanding *why* keyword and semantic are complementary, not competing, is the single most useful thing to know when building retrieval for a RAG system: reach for hybrid by default, and know which half is carrying each kind of query.

The throughline: **semantic search** matches **meaning** by embedding queries and documents into a vector space where similar meanings sit close, turning retrieval into **nearest-neighbor** search (via **ANN** for scale) — dissolving BM25's **vocabulary gap** (synonyms, paraphrases, concepts found automatically) and powering **RAG**. But it's **not a free upgrade**: it's weak at **exact matches** (codes, names, rare terms, phrases — the fuzziness that bridges meaning *loses* exactness), can retrieve plausible-but-wrong results, depends wholly on the embedding model, and is hard to interpret. Since lexical and semantic have **opposite strengths**, **hybrid search** (run both, **fuse** the results, often + a **reranker**) consistently wins — the modern default and the backbone of RAG. The series' arc: search methods **accumulate and combine** (index + BM25 + LTR + vectors coexist), they don't replace — so build retrieval **hybrid by default**.

## Key takeaways

- **Semantic search** matches **meaning**, not words: an **embedding** model maps text to vectors where similar meanings are close, so retrieval is **nearest-neighbor** search (scaled by **approximate nearest neighbor / ANN**, the vector analog of the inverted index) — dissolving BM25's **vocabulary gap** (synonyms/paraphrases/concepts found automatically) and powering **RAG**.
- It's **not a free upgrade**: weak at **exact matches** (product codes, names, acronyms, error numbers, precise phrases — embedding fuzziness loses specificity), prone to **plausible-but-wrong** topical matches, wholly dependent on the **embedding model's** quality/domain fit, and **hard to interpret/debug**.
- Lexical (BM25) and semantic have **opposite strengths** — keyword = exact terms + interpretable but misses meaning; semantic = meaning but blurs specifics — so neither dominates.
- **Hybrid search** runs **both** retrievers and **fuses** results (reciprocal-rank fusion or a learned reranker), consistently beating either alone because they fail on *different* queries; serious RAG/search systems are hybrid, often with a final **reranker** (post 6) — the retrieve-then-rank architecture.
- The series' arc: search methods **accumulate and combine** (inverted index + BM25 + learning-to-rank + vectors all coexist), not replace — so for RAG/search, go **hybrid by default** and know which half carries each query type.

## Further reading

- [Nearest neighbor search — the core operation of vector search](https://en.wikipedia.org/wiki/Nearest_neighbor_search)
- [Vector database — storing and searching embeddings at scale](https://en.wikipedia.org/wiki/Vector_database)
