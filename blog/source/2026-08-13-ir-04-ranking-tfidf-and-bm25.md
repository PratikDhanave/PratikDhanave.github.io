# Ranking — TF-IDF and BM25, the Math of Relevance

*Finding the documents that contain your words is the easy part; putting the best one first is where search lives or dies. For decades, the answer to "how relevant is this document to this query?" has come from two intuitions made precise: a word matters more in a document that uses it often, and matters less if it's common across all documents. TF-IDF and BM25 turn those intuitions into the scoring functions that rank most of the world's text search — and understanding them demystifies why search returns what it does.*

Posts 2–3 gave us matching documents and clean terms. This post is the ranking problem (post 1): scoring and ordering the matches by relevance. BM25 in particular is the workhorse — the default in Elasticsearch and Lucene and the "keyword score" in hybrid RAG retrievers — so understanding it is understanding what classical search relevance actually is.

## Two intuitions about relevance

Imagine scoring how relevant a document is to the query "reinforcement learning." Two common-sense intuitions drive almost all classical ranking:

- **Term frequency (TF): more mentions = more relevant.** A document that says "reinforcement" ten times is probably more about reinforcement than one that mentions it once. So a term's contribution to the score grows with how often it appears in the document. (The postings list stores exactly this count, post 2.)
- **Inverse document frequency (IDF): rarer words matter more.** The word "learning" appears in millions of documents; "reinforcement" in far fewer. A match on a *rare* word is far more informative about relevance than a match on a common one — matching "reinforcement" tells you much more than matching "the." So a term's contribution is *weighted up* if it's rare across the collection and *down* if it's common.

**TF-IDF** combines them: a document's score for a query is the sum, over query terms, of `TF × IDF` — reward documents that use the query's terms often (TF), especially the rare, discriminating ones (IDF). This single idea — frequent-in-this-document but rare-across-documents = important — is one of the most influential in information retrieval, and it captures a surprising amount of what "relevance" means. It also explains search behavior you've seen: common words barely affect ranking (low IDF), while an unusual query term dominates it (high IDF).

## BM25: TF-IDF, done right

TF-IDF is the intuition; **BM25** (Okapi BM25) is the refined, production-grade version that fixes TF-IDF's rough edges and has been the dominant ranking function for decades. It keeps the TF and IDF intuitions but adds two crucial corrections:

- **Term-frequency saturation.** Raw TF is too generous: a document mentioning a word 100 times isn't 100× more relevant than one mentioning it once — the *second* mention adds a lot, the *fiftieth* almost nothing. BM25 makes term frequency's contribution *saturate* — rise quickly then level off — so repetition helps with diminishing returns. This prevents keyword-stuffed documents from dominating, a real and important fix.
- **Document-length normalization.** A long document naturally contains more words, so it would unfairly rack up TF scores just by being long. BM25 *normalizes for length*, discounting matches in long documents relative to short ones, so a tight, focused document isn't beaten by a long rambling one that happens to mention the terms more. This makes relevance about *density*, not raw count.

BM25 exposes two tunable knobs (commonly called k1, controlling how fast TF saturates, and b, controlling how strongly length is normalized), letting you adapt it to a collection — but its defaults work remarkably well out of the box, which is a big reason it's the universal default. The practical reality: **BM25 is the baseline that's shockingly hard to beat.** Decades of more sophisticated methods have struggled to consistently outperform well-tuned BM25 on general text search, which is why it remains the default scoring function in essentially every full-text search engine and a core component of modern hybrid retrieval.

## What ranking by term statistics can and can't do

BM25 and TF-IDF are *lexical* — they score based on the *words* that appear, their frequencies, and their rarity. This is their strength and their ceiling:

- **Strengths:** fast (computed from the postings-list statistics the index already stores, post 2), interpretable (you can explain exactly why a document scored high), robust, needs no training data, and genuinely effective — they match on the *exact terms* the user asked for, which is often exactly what's wanted (especially for names, codes, rare technical terms, and exact phrases).
- **The ceiling — the vocabulary gap again (post 1):** because they match words, not meaning, they fail when relevant documents use *different words* than the query. A search for "car" won't score a document about "automobiles" (unless synonyms were added in analysis, post 3), and a conceptual query ("how do I make my app faster?") may miss a perfectly relevant document that never uses those exact words. Lexical ranking can't bridge meaning it can't see in the words.

This ceiling is precisely what **semantic / vector search** (post 7) was built to overcome — matching by *meaning* via embeddings rather than by terms — and it's why modern systems increasingly run **hybrid** retrieval: BM25 for exact-term precision *and* vector search for semantic recall, combining the strengths. But understand this clearly: vector search didn't make BM25 obsolete. BM25 remains superb at exactly what embeddings are weakest at — exact keyword, rare-term, and precise-phrase matching — which is why the two are *combined* rather than one replacing the other. Knowing what lexical ranking does well (exact terms, interpretably, fast, untrained) and badly (meaning, synonyms, concepts) is knowing exactly when each half of a hybrid system earns its place.

The throughline: ranking scores how relevant each matching document is, built on two intuitions — **term frequency** (more mentions = more relevant) and **inverse document frequency** (rarer words are more informative) — combined as **TF-IDF** (sum of TF×IDF over query terms), one of IR's most influential ideas. **BM25** is the production-grade refinement and decades-long default (Elasticsearch/Lucene, the keyword score in hybrid RAG), adding **TF saturation** (repetition with diminishing returns, defeating keyword stuffing) and **document-length normalization** (relevance = density, not raw count), with tunable knobs but great defaults — a baseline shockingly hard to beat. Its ceiling is that it's **lexical** (matches words, not meaning), so it nails exact terms/rare words/phrases fast and interpretably but hits the **vocabulary gap** — which **semantic/vector search** (post 7) complements, making **hybrid** retrieval (BM25 precision + vector recall) the modern norm, not replacement.

## Key takeaways

- Classical ranking rests on two intuitions: **term frequency (TF)** — more mentions of a query term = more relevant — and **inverse document frequency (IDF)** — matches on *rare* words are far more informative than matches on common ones; **TF-IDF** sums `TF × IDF` over query terms.
- **BM25** is the refined, decades-dominant version that fixes TF-IDF: **term-frequency saturation** (repetition helps with diminishing returns — defeats keyword stuffing) and **document-length normalization** (so long documents don't win on raw counts — relevance becomes *density*), with tunable knobs (k1, b) but strong defaults.
- **BM25 is the baseline that's hard to beat** — still the default scoring function in essentially every full-text engine and the keyword component of hybrid RAG retrieval.
- These are **lexical** methods (score by words, frequencies, rarity): **strengths** = fast (from stored index stats), interpretable, robust, untrained, excellent at exact terms/names/codes/phrases; **ceiling** = the **vocabulary gap** — they can't match relevant documents that use *different words* than the query (meaning they can't see in the words).
- **Semantic/vector search** (post 7) overcomes that ceiling by matching meaning, so modern systems run **hybrid** retrieval (BM25 for exact-term precision + vectors for semantic recall) — a combination, not a replacement, because BM25 excels exactly where embeddings are weakest.

## Further reading

- [tf–idf — term frequency × inverse document frequency](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)
- [Okapi BM25 — the dominant ranking function](https://en.wikipedia.org/wiki/Okapi_BM25)
