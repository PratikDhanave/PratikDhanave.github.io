# RAG on the NVIDIA Stack

*Assembling an end-to-end retrieval-augmented generation pipeline in Go on NVIDIA NIM — chunking, passage embedding, cosine shortlisting, cross-encoder reranking, and a grounded, cited answer — over nothing but net/http.*

---

The two earlier posts in this series built the pieces of a RAG system without ever calling them RAG. Post 2 built a typed Go client for a NIM chat model over its OpenAI-compatible REST API. Post 4 built the retrieval core: a NeMo Retriever embedding NIM with asymmetric `input_type`, a from-scratch cosine similarity, and a NeMo Retriever reranking NIM for precise ordering. This post wires all of it into one thing: a function `Answer(question) (string, []Source)` that pulls the right passages out of your own documents and hands the model an answer it can actually stand behind, with citations.

Nothing new gets invented here at the transport layer. NVIDIA still ships no Go SDK, so every service call is `net/http` and `encoding/json`, exactly as before. What is new is the *orchestration* — the four stages that turn a pile of text and a question into a grounded reply: **ingest, retrieve, rerank, generate.** We'll build each as concrete Go, then assemble them.

---

## The full shape of RAG

Retrieval-augmented generation exists to solve one problem: a language model only knows what was in its training data, and it will confidently make up the rest. RAG fixes that by fetching relevant passages from *your* corpus at question time and pasting them into the prompt, so the model answers from evidence you control rather than from its frozen parametric memory.

The pipeline splits cleanly in two. **Ingest** runs offline, once per document: chunk it, embed each chunk, store the vectors. **Query** runs per question: embed the question, shortlist by cosine, rerank the shortlist, build a grounded prompt, and generate. Everything downstream of retrieval is only as good as the passages retrieval returns — which is why two of the four stages exist purely to get the right chunks in the right order.

---

## Stage 1 — Ingest: chunk, embed, store

You cannot embed a whole document as one vector and expect good retrieval. A 40-page manual squeezed into a single embedding is a blurry average of everything it says, and it matches every query weakly and none of them well. So the first job of ingest is **chunking**: splitting each document into passages small enough that one vector captures one idea, with a little **overlap** so a sentence straddling a boundary isn't orphaned from its context.

Here is a word-based chunker with configurable size and overlap. Word boundaries keep it simple and language-agnostic; the overlap slides the window back a fixed number of words each step.

```go
package rag

import "strings"

// Chunk splits text into windows of about maxWords words, each overlapping the
// previous by overlap words. overlap must be smaller than maxWords.
func Chunk(text string, maxWords, overlap int) []string {
	if maxWords <= 0 {
		maxWords = 200
	}
	if overlap < 0 || overlap >= maxWords {
		overlap = maxWords / 5 // sane default: 20% overlap
	}

	words := strings.Fields(text)
	if len(words) <= maxWords {
		if len(words) == 0 {
			return nil
		}
		return []string{strings.Join(words, " ")}
	}

	step := maxWords - overlap
	var chunks []string
	for start := 0; start < len(words); start += step {
		end := start + maxWords
		if end > len(words) {
			end = len(words)
		}
		chunks = append(chunks, strings.Join(words[start:end], " "))
		if end == len(words) {
			break // last window reached the end; don't emit a tail duplicate
		}
	}
	return chunks
}
```

Each chunk becomes a stored record. We keep the text alongside the vector and a source id so we can cite it later — retrieval that can't tell you *where* an answer came from is retrieval you can't trust.

```go
// Source identifies where a chunk came from, for citation.
type Source struct {
	DocID string // e.g. "handbook.md"
	Chunk int    // chunk index within the document
}

// Record is one stored, embedded passage.
type Record struct {
	ID     string    // stable unique id, e.g. "handbook.md#3"
	Text   string    // the chunk text
	Source Source
	Vector []float32 // passage embedding
}

// Store is a trivial in-memory index. Fine for learning; see the note at the
// end for what production uses instead.
type Store struct {
	Records []Record
}
```

Now ingest: chunk every document, embed all chunks with the embedding NIM using `input_type: "passage"` (the `EmbedPassages` wrapper from post 4), and append the records. We reuse the `retriever.Client` verbatim — this post never re-implements the HTTP layer.

```go
import (
	"context"
	"fmt"

	"example.com/retriever" // the client from post 4
)

// Document is raw input to ingest.
type Document struct {
	ID   string
	Text string
}

// Ingest chunks each document, embeds the chunks as passages, and stores them.
func Ingest(
	ctx context.Context,
	c *retriever.Client,
	embedModel string,
	docs []Document,
	maxWords, overlap int,
) (*Store, error) {
	store := &Store{}
	for _, d := range docs {
		chunks := Chunk(d.Text, maxWords, overlap)
		if len(chunks) == 0 {
			continue
		}
		// One batched embed call per document — input_type = "passage".
		vecs, err := c.EmbedPassages(ctx, embedModel, chunks)
		if err != nil {
			return nil, fmt.Errorf("embed %s: %w", d.ID, err)
		}
		for i, chunk := range chunks {
			store.Records = append(store.Records, Record{
				ID:     fmt.Sprintf("%s#%d", d.ID, i),
				Text:   chunk,
				Source: Source{DocID: d.ID, Chunk: i},
				Vector: vecs[i],
			})
		}
	}
	if len(store.Records) == 0 {
		return nil, fmt.Errorf("ingest produced no records")
	}
	return store, nil
}
```

**The gotcha:** the asymmetric `input_type` has to be right on *both* ends of the pipeline, and ingest is the half people forget. Passages go in as `"passage"` here; queries go in as `"query"` in the next stage (post 4 covered why). Embed your corpus with the wrong mode and there is no error and no crash — the vectors come back looking perfectly normal, they just live in the wrong half of the space, and every retrieval quietly returns near-random passages. If relevance looks like noise, audit the ingest `input_type` before you touch anything else.

---

## Stage 2 — Retrieve: embed the query, shortlist by cosine

At query time, embed the question as a `"query"` and score it against every stored vector with the cosine similarity from post 4. This stage is deliberately *cheap and approximate*: its only job is recall — pull back a shortlist of plausible passages, over-retrieving modestly so the good ones are in there somewhere. Precision is the next stage's problem.

```go
import "sort"

// shortlist embeds the query and returns the top-n records by cosine.
func (s *Store) shortlist(
	ctx context.Context,
	c *retriever.Client,
	embedModel, query string,
	n int,
) ([]Record, error) {
	qVec, err := c.EmbedQuery(ctx, embedModel, query) // input_type = "query"
	if err != nil {
		return nil, fmt.Errorf("embed query: %w", err)
	}

	type scored struct {
		rec Record
		sim float64
	}
	ranked := make([]scored, 0, len(s.Records))
	for _, r := range s.Records {
		sim, err := retriever.CosineSimilarity(qVec, r.Vector)
		if err != nil {
			return nil, fmt.Errorf("cosine on %s: %w", r.ID, err)
		}
		ranked = append(ranked, scored{rec: r, sim: sim})
	}
	sort.Slice(ranked, func(i, j int) bool { return ranked[i].sim > ranked[j].sim })

	if n > 0 && n < len(ranked) {
		ranked = ranked[:n]
	}
	out := make([]Record, len(ranked))
	for i, sc := range ranked {
		out[i] = sc.rec
	}
	return out, nil
}
```

The embedding model *must* be the same one used at ingest — vectors from two different models aren't comparable, and the dimension check inside `CosineSimilarity` is your tripwire if they ever get mixed. Over the whole corpus this is a linear scan, which is fine for thousands of chunks in memory; the "what if it's millions" answer comes at the end.

---

## Stage 3 — Rerank: precision after recall

The cosine shortlist is fast because each passage was embedded ahead of time, in isolation — the model never saw the query and the passage *together*. That is exactly why it's only approximate. The reranking NIM is a cross-encoder: it reads the query and one candidate passage as a single input and scores how well they actually match. Far more precise, far more expensive, so you only ever run it over the shortlist recall already narrowed down.

We reuse `Rerank` from post 4, which sends the query plus candidate texts to the reranking NIM's ranking endpoint and returns passages ordered most-relevant first. The one wrinkle: the reranker works in plain text, but we need to map its winners back to our `Record`s to keep the source ids for citation. So we rerank the texts, then re-associate.

```go
// rerankRecords reorders the shortlist with the reranking NIM and keeps top-k,
// preserving each record's Source for citation.
func rerankRecords(
	ctx context.Context,
	c *retriever.Client,
	rerankModel, query string,
	shortlist []Record,
	topK int,
) ([]Record, error) {
	if len(shortlist) == 0 {
		return nil, nil
	}
	texts := make([]string, len(shortlist))
	for i, r := range shortlist {
		texts[i] = r.Text
	}

	scored, err := c.Rerank(ctx, rerankModel, query, texts, topK)
	if err != nil {
		return nil, fmt.Errorf("rerank: %w", err)
	}

	// Map reranked text back to the record that carried it. Chunk texts can
	// repeat across documents, so match by first unused occurrence.
	used := make([]bool, len(shortlist))
	out := make([]Record, 0, len(scored))
	for _, sc := range scored {
		for i, r := range shortlist {
			if !used[i] && r.Text == sc.Text {
				used[i] = true
				out = append(out, r)
				break
			}
		}
	}
	return out, nil
}
```

**The gotcha:** reranking is where most of your RAG quality actually comes from, and it is the stage teams are most tempted to skip. Feeding the LLM the raw cosine top-5 gives mushy, half-relevant context and mediocre answers — and everyone blames the model. Nine times out of ten the retrieval was the problem: cosine got the right passage *into* the top 30 but not into the top 5, and only the cross-encoder can tell the difference. Over-retrieve modestly (a shortlist of 20–50), then let the reranker pick the handful that go in the prompt. Don't skip it.

---

## Stage 4 — Augment and generate: a grounded, cited prompt

Now the top-k records become context for the chat NIM from post 2. Two design choices decide whether generation is trustworthy. First, **structure the context so the model can cite it** — number each passage and tell the model to reference passages by number. Second, **instruct it to answer only from the context and to admit when the context doesn't contain the answer.** Without that instruction the model happily falls back to parametric memory and hallucinates a confident, wrong answer.

```go
import "strings"

const systemPrompt = `You are a precise assistant. Answer the user's question
using ONLY the numbered context passages provided. Cite the passages you use by
their number in square brackets, like [1] or [2]. If the context does not
contain the answer, reply exactly: "I don't know based on the provided context."
Do not use any knowledge beyond the context.`

// buildContext renders the top-k records as a numbered block and returns the
// per-number Source list so callers can resolve citations.
func buildContext(records []Record) (string, []Source) {
	var b strings.Builder
	sources := make([]Source, len(records))
	for i, r := range records {
		fmt.Fprintf(&b, "[%d] (%s) %s\n\n", i+1, r.ID, r.Text)
		sources[i] = r.Source
	}
	return b.String(), sources
}
```

The generation call is the `nim.Client.Chat` from post 2 — a system message carrying the rules, a user message carrying the context and the question. A low temperature keeps the model close to the evidence.

```go
import "example.com/nim" // the chat client from post 2

// generate calls the chat NIM with the grounded prompt.
func generate(
	ctx context.Context,
	chat *nim.Client,
	chatModel, question, contextBlock string,
) (string, error) {
	userMsg := fmt.Sprintf(
		"Context passages:\n\n%s\nQuestion: %s",
		contextBlock, question,
	)
	resp, err := chat.Chat(ctx, nim.ChatRequest{
		Model: chatModel, // e.g. "meta/llama-3.1-8b-instruct" — verify in the catalog
		Messages: []nim.Message{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: userMsg},
		},
		Temperature: 0.1,
		MaxTokens:   512,
	})
	if err != nil {
		return "", fmt.Errorf("generate: %w", err)
	}
	return resp.Choices[0].Message.Content, nil
}
```

**The gotcha:** the grounding instruction is not optional decoration — it is the difference between RAG and an expensive way to hallucinate. If you don't explicitly tell the model to use only the context *and* give it permission to say "I don't know," it treats the passages as a hint and pads the gaps with its training data. That failure is invisible in a demo (the answer sounds great) and disastrous in production (the answer is wrong and cites nothing). Make "admit the context doesn't cover it" an allowed, named outcome.

---

## Wiring it together: Answer(question)

A small pipeline type holds the two clients and the model ids, and `Answer` runs the four stages end to end, returning the text and the sources behind it.

```go
// Pipeline holds the clients and model ids for one RAG system.
type Pipeline struct {
	Retriever   *retriever.Client // embedding + reranking NIMs (post 4)
	Chat        *nim.Client       // chat NIM (post 2)
	EmbedModel  string
	RerankModel string
	ChatModel   string
	Store       *Store

	Shortlist int // candidates to rerank, e.g. 30
	TopK      int // passages to put in the prompt, e.g. 5
}

// Answer runs retrieve -> rerank -> generate and returns the grounded reply
// plus the sources of the passages used to produce it.
func (p *Pipeline) Answer(ctx context.Context, question string) (string, []Source, error) {
	// 1. Recall: cosine shortlist.
	shortlist, err := p.Store.shortlist(ctx, p.Retriever, p.EmbedModel, question, p.Shortlist)
	if err != nil {
		return "", nil, err
	}
	// 2. Precision: rerank, keep top-k.
	top, err := rerankRecords(ctx, p.Retriever, p.RerankModel, question, shortlist, p.TopK)
	if err != nil {
		return "", nil, err
	}
	if len(top) == 0 {
		return "I don't know based on the provided context.", nil, nil
	}
	// 3. Augment + generate.
	contextBlock, sources := buildContext(top)
	answer, err := generate(ctx, p.Chat, p.ChatModel, question, contextBlock)
	if err != nil {
		return "", nil, err
	}
	return answer, sources, nil
}
```

And a caller that ingests a corpus once, then asks:

```go
func main() {
	ctx := context.Background()

	rc := retriever.NewClient("https://integrate.api.nvidia.com/v1", os.Getenv("NVIDIA_API_KEY"))
	chat := nim.NewWithBaseURL("https://integrate.api.nvidia.com/v1", os.Getenv("NVIDIA_API_KEY"))

	docs := []rag.Document{
		{ID: "handbook.md", Text: "..."}, // your real documents
		{ID: "faq.md", Text: "..."},
	}

	store, err := rag.Ingest(ctx, rc, "nvidia/nv-embedqa-e5-v5", docs, 200, 40)
	if err != nil {
		log.Fatalf("ingest: %v", err)
	}

	p := &rag.Pipeline{
		Retriever:   rc,
		Chat:        chat,
		EmbedModel:  "nvidia/nv-embedqa-e5-v5",           // verify in the catalog
		RerankModel: "nvidia/nv-rerankqa-mistral-4b-v3",  // verify in the catalog
		ChatModel:   "meta/llama-3.1-8b-instruct",        // verify in the catalog
		Store:       store,
		Shortlist:   30,
		TopK:        5,
	}

	answer, sources, err := p.Answer(ctx, "What is the refund window?")
	if err != nil {
		log.Fatalf("answer: %v", err)
	}
	fmt.Println(answer)
	for i, s := range sources {
		fmt.Printf("[%d] %s (chunk %d)\n", i+1, s.DocID, s.Chunk)
	}
}
```

The whole system runs over REST from Go — three NIMs (embedding, reranking, chat), one small `net/http` client shared shape, and no vendor SDK anywhere. Model ids are examples; confirm the current ones against the catalog on build.nvidia.com.

---

## Where the in-memory store stops

The `Store` above is a slice, and its `shortlist` scans every vector on every query. That is a *teaching* tool: it makes the data flow obvious and it is genuinely fine for thousands of chunks. It does not survive contact with production, where corpora run to millions of vectors and a linear scan per query is far too slow.

Production RAG puts the vectors in a **vector database** that indexes them for approximate-nearest-neighbor search. NVIDIA's ecosystem integrates with vector DBs rather than shipping its own: **Milvus**, for instance, supports a **GPU index** for accelerated similarity search, and **NVIDIA cuVS** provides GPU-accelerated vector-search primitives that such databases can build on. You would talk to Milvus over its *own* client or REST API — there is no NVIDIA Go SDK for it any more than there is for NIM — so from Go you'd swap the in-memory `shortlist` for a call to your vector DB and leave everything else alone. NVIDIA also publishes **RAG reference architectures / blueprints** that assemble these components into a deployable system; treat those as the blueprint for scaling this pattern up, not as an API to call from here.

**The gotcha:** the in-memory store is the *only* part of this design that changes when you scale. The `retrieve → rerank → generate` shape is identical whether recall comes from a Go slice or a GPU-indexed Milvus collection — you're still embedding the query, pulling back a shortlist, reranking it with the NeMo Retriever cross-encoder, and grounding the chat NIM on the top-k. Learn the shape on the slice; move the shortlist to a real vector DB before production and nothing downstream has to move with it.

---

## Key takeaways

- **RAG is four stages, and two of them exist to fix retrieval.** Ingest and generate are the obvious ends; the shortlist-then-rerank middle is what makes the answer good.
- **Chunk with overlap.** One vector should capture one idea; overlap keeps boundary-straddling sentences from losing their context.
- **`input_type` must be right on both ends.** Passages as `"passage"` at ingest, queries as `"query"` at retrieval — a silent, error-free failure that destroys relevance if you get it wrong.
- **Don't skip reranking.** Cosine gets the right passage into the top 30; only the cross-encoder gets it into the top 5. Most "bad RAG" is unranked retrieval.
- **Ground the model and let it say "I don't know."** Without that instruction it falls back to parametric memory and hallucinates confidently.
- **In-memory is a teaching tool.** Move to a real vector DB (Milvus GPU index, cuVS) before production — but the `retrieve → rerank → generate` shape stays identical.

---

## Further reading

- [NeMo Retriever Text Embedding NIM — documentation](https://docs.nvidia.com/nim/nemo-retriever/text-embedding/latest/overview.html) — the embedding endpoint, `input_type`, and model ids.
- [NeMo Retriever Text Reranking NIM — documentation](https://docs.nvidia.com/nim/nemo-retriever/text-reranking/latest/overview.html) — confirm the ranking request/response fields for your version.
- [NVIDIA RAG Blueprint](https://build.nvidia.com/nvidia/build-an-enterprise-rag-pipeline) — NVIDIA's reference architecture for an enterprise RAG pipeline.
- [Milvus documentation — GPU index](https://milvus.io/docs/gpu_index.md) — GPU-accelerated vector indexing in Milvus.
- [NVIDIA cuVS](https://github.com/rapidsai/cuvs) — GPU-accelerated vector search primitives.
- [Go `net/http` package reference](https://pkg.go.dev/net/http) — the whole transport layer of this pipeline.
