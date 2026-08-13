# Making RAG Good

*Why the naive RAG pipeline from post 9 underperforms in production, and the concrete, evaluation-driven fixes — structure-aware chunking, hybrid search, reranking, query transformation, and deliberate context construction — each explained with the reasoning and a real Go sketch.*

---

In post 9 we built a RAG pipeline in Go end to end: chunk the documents, embed each chunk, drop the vectors into the `vstore.VectorStore` from post 8, and at query time call `Search(embed(query), k)`, paste the top-*k* chunks into a prompt, and generate. It works. In a demo, with clean documents and softball questions, it looks like magic.

Then you point it at real documents and real users, and it disappoints. It misses the one paragraph that had the answer. It confidently cites the wrong section. Ask it for an exact error code or a person's name and it returns three chunks *vaguely about* the topic that never mention the term you typed. The generation half is fine — the model writes a fluent answer. The problem is almost always the *retrieval* half: you fed the model the wrong chunks, so it answered the wrong question well.

This post is about closing that gap. Every technique here targets one thing: **get the right chunks in front of the model.** And the discipline that makes all of them work is measurement — so we start there, because the single most expensive mistake in RAG is tuning the prompt when the bug is in retrieval.

---

## Start by measuring retrieval, not vibes

You cannot improve what you don't measure, and "the answers feel better now" is not a measurement. Before touching chunking or search, build a tiny evaluation set: a handful of real questions, and for each one, the id(s) of the chunk(s) that actually contain the answer. That's your ground truth. Then compute **recall@k** — of the questions whose answer chunk *exists* in the store, how often does it appear in the top *k* you retrieved?

Recall@k is the ceiling on your whole system. If the right chunk isn't in the top *k*, no prompt, no reranker, no bigger model can recover it — the information never reached the generator.

```go
package rageval

// Case is one labeled question: the query and the set of chunk ids that
// genuinely answer it.
type Case struct {
	Query   string
	Relevant map[string]bool // chunk ids that contain the answer
}

// Retriever is any function that returns ranked chunk ids for a query.
type Retriever func(query string, k int) []string

// RecallAtK is the fraction of cases whose retrieval contained at least one
// relevant chunk in the top k. This is the number you improve against.
func RecallAtK(cases []Case, retrieve Retriever, k int) float64 {
	if len(cases) == 0 {
		return 0
	}
	var hits int
	for _, c := range cases {
		for _, id := range retrieve(c.Query, k) {
			if c.Relevant[id] {
				hits++
				break
			}
		}
	}
	return float64(hits) / float64(len(cases))
}
```

Run this once against your post-9 baseline and write the number down. Every change below is a hypothesis: *this will raise recall@k.* Some will; some won't for your data. The point is you'll know, instead of guessing.

**The gotcha:** you can't improve what you don't measure — fix retrieval metrics *before* you touch the prompt. Teams burn weeks rewording system prompts to fix answers that were doomed the moment retrieval returned the wrong chunks. If recall@5 is 0.6, the model is answering a third of your questions blind, and no prompt engineering changes that. Measure retrieval first, in isolation, and only optimize the generator once the right context is reliably reaching it. (We go deep on end-to-end RAG evaluation in post 13; recall@k is the retrieval-only foundation it builds on.)

---

## Chunk with structure, not with a ruler

The naive pipeline split text every N characters. That's a ruler, and documents don't obey rulers. A fixed-length cut lands mid-sentence, severs a heading from the paragraph it introduces, and splits a table row from its header. The embedding of half a thought is a bad embedding, and it retrieves badly.

Two fixes carry most of the weight. First, **split on structure** — paragraph and section boundaries, list items, code blocks — so each chunk is a coherent unit of meaning. Second, keep a small **overlap** between adjacent chunks so an answer that straddles a boundary survives in at least one whole chunk. And throughout, carry **metadata** with every chunk: which document it came from and which section. That metadata is what lets you cite sources later and filter by document.

```go
// Chunk is a retrievable unit plus where it came from. The metadata rides
// along through embedding, search, and into the final citation.
type Chunk struct {
	ID      string
	Text    string
	Source  string // document filename or URL
	Section string // nearest heading above this chunk
}

// splitStructured breaks a document into chunks on blank-line (paragraph)
// boundaries, packing paragraphs up to a soft size limit and carrying the
// current heading. It never cuts mid-paragraph.
func splitStructured(source, doc string, maxRunes int) []Chunk {
	var chunks []Chunk
	section := ""
	var buf strings.Builder
	flush := func() {
		if buf.Len() == 0 {
			return
		}
		chunks = append(chunks, Chunk{
			ID:      fmt.Sprintf("%s#%d", source, len(chunks)),
			Text:    strings.TrimSpace(buf.String()),
			Source:  source,
			Section: section,
		})
		buf.Reset()
	}
	for _, para := range strings.Split(doc, "\n\n") {
		para = strings.TrimSpace(para)
		if para == "" {
			continue
		}
		if h, ok := headingText(para); ok { // e.g. a Markdown "## ..." line
			flush()
			section = h
			continue
		}
		if utf8.RuneCountInString(buf.String())+utf8.RuneCountInString(para) > maxRunes {
			flush()
		}
		buf.WriteString(para)
		buf.WriteString("\n\n")
	}
	flush()
	return chunks
}
```

Overlap is a one-line policy on top of this: when you flush, seed the next buffer with the last sentence or two of the chunk you just emitted, so a fact sitting on the seam appears whole in both neighbors.

**The gotcha:** chunk size is a real trade-off, not a default to copy from a tutorial. Chunks too large dilute the embedding — one vector now averages several topics, so it's a strong match for none of them and reranking has more junk to wade through. Chunks too small fragment the answer across many hits and blow your top-*k* budget on pieces of one paragraph. Structure-aware splitting sidesteps the worst of it by cutting where the meaning already breaks, but you still tune `maxRunes` against recall@k on *your* documents — legal contracts and chat logs want different numbers.

---

## Hybrid search: dense plus lexical

Embeddings are semantic — they find text that *means* the same thing even with no shared words, which is exactly why post 8 beat keyword matching. But that strength is also a blind spot. Ask for the exact error code `ERR_2048`, an SKU, a function name, or a person's surname, and the dense vector for that token is weak and generic. The model that made the embedding never learned that `ERR_2048` is special; it's just a rare string. Lexical search, meanwhile, nails exact tokens by construction — that's all it does.

So run both. **Dense** (your `vstore.Search`) for meaning, **sparse** keyword search (BM25, the standard lexical ranking function) for exact terms, then fuse the two ranked lists. The catch is that the scores live on incompatible scales: cosine similarity is roughly `[-1, 1]`, BM25 is an unbounded positive number that depends on term frequency and corpus statistics. Averaging them directly is meaningless.

**Reciprocal Rank Fusion (RRF)** sidesteps the scale problem entirely by throwing the scores away and fusing on *rank* alone. Each list contributes `1 / (rrfK + rank)` to every id it ranks; sum across lists; sort by the total. A chunk that both methods rank highly floats to the top; a chunk only one method found still gets a fair contribution.

```go
// fuseRRF combines several ranked id lists into one by Reciprocal Rank Fusion.
// rrfK is a smoothing constant (60 is the value from the original paper).
// It uses only rank, so dense cosine and BM25's different scales never meet.
func fuseRRF(rankings [][]string, rrfK int) []string {
	score := map[string]float64{}
	for _, list := range rankings {
		for rank, id := range list { // rank is 0-based
			score[id] += 1.0 / float64(rrfK+rank+1)
		}
	}
	fused := make([]string, 0, len(score))
	for id := range score {
		fused = append(fused, id)
	}
	sort.Slice(fused, func(i, j int) bool {
		if score[fused[i]] != score[fused[j]] {
			return score[fused[i]] > score[fused[j]]
		}
		return fused[i] < fused[j] // stable tie-break
	})
	return fused
}

// hybridSearch runs dense and lexical retrieval and fuses the two rankings.
func hybridSearch(query string, n int) []string {
	dense := ids(store.Search(embed(query), n)) // post 8/9 vector search
	sparse := bm25.Search(query, n)             // any BM25 index over the same chunks
	return fuseRRF([][]string{dense, sparse}, 60)
}
```

`bm25.Search` is a keyword index over the same chunk corpus — you can build one from an inverted index and the Okapi BM25 formula, or borrow a small Go library; the fusion above doesn't care how the sparse list was produced, only that it's ranked.

**The gotcha:** hybrid search needs score normalization, and getting it wrong quietly wrecks the ranking. Dense cosine and BM25 are different scales, so any scheme that *adds* their raw scores is dominated by whichever number happens to be bigger. You can normalize both to `[0, 1]` and take a weighted sum — but then you own a fragile weight to tune per corpus. RRF sidesteps the whole problem by fusing on rank instead of score. Start with RRF; reach for weighted score fusion only if you have the eval harness to tune the weight and evidence it beats RRF on your data.

---

## Rerank the shortlist

Here is the highest-leverage change in this whole post, and the one people skip. Your retriever — dense, sparse, or fused — is optimized for *speed over a huge corpus*. It compares a single query vector against millions of chunk vectors, so it can only afford a cheap similarity. That cheapness costs accuracy: the top 20 are roughly right, but the true best chunk might be sitting at rank 11, not rank 1.

A **reranker** fixes the ordering of a short list with a much stronger, much slower signal. The standard tool is a *cross-encoder*: instead of embedding the query and chunk separately and comparing vectors, it feeds the query and one candidate chunk *together* into a model that scores their relevance directly. That joint attention is far more accurate than comparing two independent embeddings — and far too expensive to run over the whole corpus, which is exactly why it only sees a shortlist. Reranker models and hosted reranking endpoints exist from several providers; the mechanics below are vendor-neutral, so treat `rerank` as whichever model or API you wire in.

The control flow is: **over-retrieve** N (say 30), **rerank** all N, **take** the top *k* (say 5) for the prompt.

```go
// Reranker scores how well each candidate answers the query. A cross-encoder
// model or a hosted reranking endpoint implements this; higher is better.
type Reranker interface {
	Score(ctx context.Context, query string, candidates []string) ([]float64, error)
}

// retrieveRerank over-retrieves N, reranks with a stronger model, keeps top k.
func retrieveRerank(ctx context.Context, rr Reranker, query string, n, k int) ([]Chunk, error) {
	shortlist := lookup(hybridSearch(query, n)) // []Chunk for the fused top-N ids
	texts := make([]string, len(shortlist))
	for i, c := range shortlist {
		texts[i] = c.Text
	}
	scores, err := rr.Score(ctx, query, texts)
	if err != nil {
		return shortlist[:min(k, len(shortlist))], nil // degrade to retrieval order
	}
	sort.SliceStable(shortlist, func(i, j int) bool { return scores[i] > scores[j] })
	return shortlist[:min(k, len(shortlist))], nil
}
```

If you have no reranker model handy, an **LLM-as-reranker** is a serviceable stand-in: prompt a capable model with the query and the numbered candidates and ask it to return the ids in relevance order. It's slower and pricier per query than a dedicated cross-encoder, but it needs no extra infrastructure and often beats raw retrieval order handily.

**The gotcha:** reranking is where most of the quality gains hide, but it adds latency and cost on every query — you're now running a second model over N candidates. So over-retrieve *modestly*. Going from N=20 to N=100 rarely moves recall enough to justify 5x the rerank bill and latency; the answer chunk that isn't in your fused top 30 usually isn't in the top 100 either. Tune N against recall@k: find the smallest N where the true chunk is almost always present, then let the reranker sort *that* out. Note the fallback in the code — if the reranker call fails, degrade to retrieval order rather than failing the query; a slightly worse ranking beats no answer.

---

## Transform the query before you search

The naive pipeline embeds the user's raw question and searches with it. But users ask badly for retrieval: they're terse ("the timeout thing"), they carry context from earlier turns ("what about the second one?"), and their phrasing rarely matches how the *documents* are written. A short pre-processing step reshapes the query into something that retrieves better.

- **Rewriting and expansion.** Use a cheap LLM call to rewrite a vague or conversational query into a self-contained, keyword-rich one — resolving "the second one" against the conversation, adding synonyms the docs might use. The rewrite is what you embed and search.
- **Multi-query.** Generate two or three paraphrases of the question, retrieve for each, and fuse the results with the same `fuseRRF` from above. Different phrasings surface different true chunks; fusion keeps what they agree on.
- **HyDE (Hypothetical Document Embeddings).** The intuition: a question and its answer are written differently, so a question embedding sits awkwardly among *answer*-shaped document chunks. HyDE has the LLM draft a hypothetical answer to the question — fabricated, possibly wrong — then embeds *that* and searches with it. You're matching answer-shaped text against answer-shaped chunks, which lands closer in embedding space. You never show the hallucinated draft to the user; it's purely a better search key.

```go
// multiQuery rewrites the raw query into several phrasings, retrieves for each,
// and fuses. rewrite() is a cheap LLM call returning paraphrases; embed/search
// are the post 8/9 primitives.
func multiQuery(ctx context.Context, raw string, n int) []string {
	variants := rewrite(ctx, raw) // e.g. 3 self-contained paraphrases
	rankings := make([][]string, 0, len(variants))
	for _, q := range variants {
		rankings = append(rankings, ids(store.Search(embed(q), n)))
	}
	return fuseRRF(rankings, 60)
}
```

**The gotcha:** every transformation is an extra LLM call before you've retrieved anything — that's latency and cost on the critical path, and a rewrite can *drift* the query away from the user's intent. Gate these on the eval set like everything else: adopt HyDE or multi-query only where recall@k actually rises. They pay off most for short, ambiguous, or conversational queries and add little for already-precise ones.

---

## Build the context deliberately

Retrieval hands you *k* good chunks. How you assemble them into the prompt is not an afterthought — it changes the answer. Three rules.

**Order matters, and not how you'd guess.** Long-context models under-use the *middle* of their context — the "lost in the middle" effect. Attention favors the beginning and end, so a critical chunk buried in the middle of ten gets skimmed. Put your strongest chunks first and last, not in a neat descending pile.

**Deduplicate.** Overlapping chunks and multi-query fusion both produce near-duplicate passages. Sending the same fact three times wastes budget and biases the model toward whatever got repeated. Drop near-identical chunks before assembling.

**Respect the token budget (post 3).** Context isn't free and it isn't infinite. Count tokens as you add chunks and stop before you blow the budget — leaving headroom for the model's answer. And **carry the source metadata into the prompt** so the model can cite it and you can trace every claim back to a chunk.

```go
// buildContext assembles reranked chunks into a prompt block: dedup, respect a
// token budget, and place the strongest chunks at the edges (not the middle).
func buildContext(chunks []Chunk, budget int) string {
	chunks = dedup(chunks) // drop near-identical passages
	kept := []Chunk{}
	used := 0
	for _, c := range chunks {
		t := countTokens(c.Text) // post 3's tokenizer
		if used+t > budget {
			break
		}
		kept = append(kept, c)
		used += t
	}
	kept = edgeOrder(kept) // best first and last; weakest toward the middle
	var b strings.Builder
	for _, c := range kept {
		fmt.Fprintf(&b, "[%s — %s]\n%s\n\n", c.Source, c.Section, c.Text)
	}
	return b.String()
}
```

**The gotcha:** more chunks in context is not better. It's tempting to raise *k* to 20 "to be safe," but that pushes real evidence into the lost-in-the-middle dead zone, dilutes attention across mostly-irrelevant text, and costs tokens on every call. A tightly reranked top 3–5 usually beats a loose top 20. Retrieve wide, rerank hard, and send *few*.

---

## Know when not to retrieve

The last improvement is retrieving less. Not every query needs your documents. "Rewrite this email more formally," "what's 15% of 240," "translate this to French" — the answer is in the request, not your corpus. Retrieving anyway injects irrelevant chunks that can only distract the model, and spends latency and money to make the answer *worse*.

So put a gate in front of retrieval: a cheap classification — a small LLM call, or even a heuristic — deciding whether this query is knowledge-seeking against your corpus at all. If not, skip straight to generation. This also handles conversational filler ("thanks!", "can you redo that") that would otherwise retrieve noise. The best RAG systems retrieve *when it helps* and get out of the way when it doesn't.

---

## The improvements, at a glance

| Technique | Fixes | Cost it adds |
|---|---|---|
| Recall@k evaluation | Optimizing blind | Building a labeled set (do it anyway) |
| Structure-aware chunking + overlap | Severed, incoherent chunks | Tuning chunk size per corpus |
| Hybrid search (dense + BM25, RRF) | Missing exact terms, IDs, names | A second index; fusion step |
| Reranking (cross-encoder / LLM) | Right chunk buried below top-k | A slow model over N candidates |
| Query transformation (rewrite/HyDE/multi) | Vague, conversational, mismatched queries | Extra LLM call(s) before retrieval |
| Deliberate context construction | Lost-in-the-middle, dupes, budget overruns | Dedup + token accounting |
| Retrieval gating | Distraction on non-corpus queries | A cheap classifier call |

---

## Key takeaways

- **Retrieval quality is the ceiling.** If the answer chunk isn't in the top *k*, nothing downstream can save the response. Measure recall@k first, and treat every change as a hypothesis you verify against it.
- **Chunk on structure, not size.** Split where meaning breaks, overlap the seams, and carry source/section metadata through the whole pipeline so you can cite and filter.
- **Run dense and lexical together.** Embeddings find meaning; BM25 nails exact tokens. Fuse them with RRF, which combines on rank and sidesteps the incompatible-scale problem.
- **Reranking is the biggest single win.** Over-retrieve N, rerank with a cross-encoder or an LLM, take the top *k*. Over-retrieve modestly — it's a per-query cost.
- **Reshape the query and assemble the context on purpose.** Rewrite/HyDE/multi-query help ambiguous questions; then dedup, respect the token budget, and place strong chunks at the edges to beat lost-in-the-middle.
- **Sometimes the fix is not retrieving at all.** Gate retrieval so non-corpus queries skip it entirely.
- **It's a loop, not a checklist.** Change one thing, re-run recall@k (and, in post 13, end-to-end answer quality), keep what wins on *your* data. RAG is tuned, not configured.

Post 9 got you a pipeline that runs. This post gets you one that's worth trusting — and the reason you can trust it is that every step is now something you measure, not something you hope.

---

## Further reading

- [Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond" (Foundations and Trends in Information Retrieval, 2009)](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf) — the definitive reference for the Okapi BM25 lexical ranking function.
- [Cormack, Clarke & Büttcher, "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods" (SIGIR 2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — the original RRF paper, including the `k=60` constant used above.
- [Nogueira & Cho, "Passage Re-ranking with BERT" (arXiv:1901.04085)](https://arxiv.org/abs/1901.04085) — the cross-encoder reranking approach that popularized over-retrieve-then-rerank.
- [Gao et al., "Precise Zero-Shot Dense Retrieval without Relevance Labels" (arXiv:2212.10496)](https://arxiv.org/abs/2212.10496) — the HyDE (Hypothetical Document Embeddings) paper.
- [Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172)](https://arxiv.org/abs/2307.03172) — the empirical study behind edge-ordering your context.
