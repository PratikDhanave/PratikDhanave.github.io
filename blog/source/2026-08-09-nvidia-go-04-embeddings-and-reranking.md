# Embeddings and Reranking with NeMo Retriever

*Building the retrieval core of RAG in Go by calling NeMo Retriever embedding and reranking NIMs over plain net/http, with asymmetric input types and a two-stage retrieve-then-rerank pipeline.*

---

Retrieval-augmented generation lives or dies on one question: when a user asks something, can you pull the *right* passages out of your corpus and hand them to the model? Get that wrong and no amount of prompt engineering saves the answer. NVIDIA's NeMo Retriever ships the two models that make this work — an **embedding** model and a **reranking** model — packaged as NIMs (NVIDIA Inference Microservices) you call over HTTP.

There is no NVIDIA Go SDK. Every example in this series talks to NVIDIA services the same way: a small REST client built on `net/http`. That is a feature, not a limitation — you see exactly what goes over the wire, and the two NeMo Retriever endpoints have very different request shapes that a wrapper would only hide.

This post builds the *retrieval core* of a RAG pipeline in Go. Part 1 turns text into vectors with the embedding NIM and scores them with a from-scratch cosine similarity. Part 2 adds a reranking NIM that re-scores a shortlist far more precisely. Then we wire them into the pattern every serious RAG system uses: **embed → shortlist by cosine → rerank → take top-k**.

---

## The client we reuse

Earlier in this series we built a tiny REST client — a base URL, an API key, and an `*http.Client` with a sane timeout. Here is the minimal version, so this post stands on its own:

```go
package retriever

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type Client struct {
	BaseURL string       // e.g. https://integrate.api.nvidia.com/v1, or your self-hosted NIM
	APIKey  string       // from https://build.nvidia.com; sent as a Bearer token
	HTTP    *http.Client
}

func NewClient(baseURL, apiKey string) *Client {
	return &Client{
		BaseURL: baseURL,
		APIKey:  apiKey,
		HTTP:    &http.Client{Timeout: 60 * time.Second},
	}
}

// postJSON marshals body, POSTs to {BaseURL}{path}, and decodes the JSON reply into out.
func (c *Client) postJSON(ctx context.Context, path string, body, out any) error {
	raw, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+path, bytes.NewReader(raw))
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := c.HTTP.Do(req)
	if err != nil {
		return fmt.Errorf("do request: %w", err)
	}
	defer resp.Body.Close()

	data, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("nvidia api %s: status %d: %s", path, resp.StatusCode, string(data))
	}
	if err := json.Unmarshal(data, out); err != nil {
		return fmt.Errorf("decode response: %w", err)
	}
	return nil
}
```

Whichever NeMo Retriever NIM you target — the hosted endpoints on `build.nvidia.com` or a container you run yourself — only `BaseURL` changes. The wire protocol is identical.

---

## Part 1 — Embeddings: text becomes vectors

An embedding model maps a string to a fixed-length vector of floats. Texts that mean similar things land near each other in that vector space, so "how do I reset my password" and "forgot login credentials" end up close even though they share no keywords. That is what lets you search by *meaning* instead of exact terms.

NeMo Retriever's embedding NIM is **OpenAI-compatible**: you `POST {baseURL}/embeddings` with a JSON body containing a `model`, an `input` list of strings, and — the NVIDIA-specific part — an `input_type`. The reply carries a `data` array (one entry per input, each with an `embedding` of floats) plus a `usage` block.

### Why input_type matters: asymmetric embeddings

This is the detail people miss, and it quietly wrecks retrieval quality. NVIDIA's retrieval embedding models are **asymmetric**: they were trained to embed *documents* and *questions* into the same space using two different modes. You select the mode with `input_type`:

- Embed the passages you store with `input_type: "passage"`.
- Embed the user's search query with `input_type: "query"`.

The model applies a different internal treatment to each so that a short question and the long passage that answers it land close together. If you embed everything as `"passage"` (or everything as `"query"`), the vectors still come back — no error — but they are living in the wrong halves of the space, and your similarity scores become noise.

Here is the Go for it. Note the two thin wrappers over one core function, so the call site can never forget which mode it is in:

```go
type embedRequest struct {
	Model     string   `json:"model"`
	Input     []string `json:"input"`
	InputType string   `json:"input_type"` // "query" or "passage" — NVIDIA-specific
}

type embedData struct {
	Index     int       `json:"index"`
	Embedding []float32 `json:"embedding"`
}

type embedResponse struct {
	Data  []embedData `json:"data"`
	Usage struct {
		PromptTokens int `json:"prompt_tokens"`
		TotalTokens  int `json:"total_tokens"`
	} `json:"usage"`
}

// embed is the core call. inputType must be "query" or "passage".
func (c *Client) embed(ctx context.Context, model, inputType string, texts []string) ([][]float32, error) {
	if len(texts) == 0 {
		return nil, nil
	}
	var out embedResponse
	req := embedRequest{Model: model, Input: texts, InputType: inputType}
	if err := c.postJSON(ctx, "/embeddings", req, &out); err != nil {
		return nil, fmt.Errorf("embed (%s): %w", inputType, err)
	}
	if len(out.Data) != len(texts) {
		return nil, fmt.Errorf("embed: asked for %d vectors, got %d", len(texts), len(out.Data))
	}
	// The API is not required to return data in input order — sort by Index.
	vectors := make([][]float32, len(texts))
	for _, d := range out.Data {
		if d.Index < 0 || d.Index >= len(vectors) {
			return nil, fmt.Errorf("embed: index %d out of range", d.Index)
		}
		vectors[d.Index] = d.Embedding
	}
	return vectors, nil
}

// EmbedPassages embeds documents you will store and search over.
func (c *Client) EmbedPassages(ctx context.Context, model string, docs []string) ([][]float32, error) {
	return c.embed(ctx, model, "passage", docs)
}

// EmbedQuery embeds a single user query.
func (c *Client) EmbedQuery(ctx context.Context, model, query string) ([]float32, error) {
	vecs, err := c.embed(ctx, model, "query", []string{query})
	if err != nil {
		return nil, err
	}
	return vecs[0], nil
}
```

For `model`, pass a NeMo Retriever embedding NIM id — for example `nvidia/nv-embedqa-e5-v5` or `nvidia/llama-3.2-nv-embedqa-1b-v2`. **Treat those as examples to verify** against the model catalog on `build.nvidia.com`; ids and their availability change, and each model has its own vector dimension.

**The gotcha:** NVIDIA retrieval embeddings are asymmetric — embedding a query with `input_type: "passage"` (or a passage with `"query"`) returns perfectly valid-looking vectors and *silently* tanks retrieval quality. There is no exception to catch. If your relevance suddenly looks random, check this first. And embed both sides with the **same model** — vectors from two different embedding models are not comparable, so your stored passages and your live queries must share one model for their whole lifetime.

### Cosine similarity, from scratch

To rank passages against a query you compare vectors. The standard measure is **cosine similarity**: the cosine of the angle between two vectors, which ignores their magnitude and rewards pointing the same direction. It runs from -1 (opposite) to 1 (identical direction). No library needed:

```go
import "math"

// CosineSimilarity returns the cosine of the angle between a and b, in [-1, 1].
func CosineSimilarity(a, b []float32) (float64, error) {
	if len(a) != len(b) {
		return 0, fmt.Errorf("cosine: dimension mismatch %d vs %d", len(a), len(b))
	}
	var dot, normA, normB float64
	for i := range a {
		x, y := float64(a[i]), float64(b[i])
		dot += x * y
		normA += x * x
		normB += y * y
	}
	if normA == 0 || normB == 0 {
		return 0, fmt.Errorf("cosine: zero-magnitude vector")
	}
	return dot / (math.Sqrt(normA) * math.Sqrt(normB)), nil
}
```

That dimension check is your safety net: if it ever fires, you have accidentally mixed vectors from two different embedding models, and the invariant above just caught the bug.

---

## Part 2 — Reranking: precision after recall

Embeddings are fast but *approximate*. Each passage is squeezed into one vector ahead of time, so scoring a query against a whole corpus is cheap — but the model never sees the query and a passage *together*. It compares two independent summaries. That is great for recall (pulling back a rough shortlist of plausible matches) and mediocre for precision (ordering that shortlist correctly).

A **reranker** is a different kind of model — a cross-encoder. It takes the query and one passage *as a single input* and outputs a relevance score, so it can weigh how the exact words of the query line up against the exact words of the passage. That is far more precise, and far more expensive: one model call per passage, no precomputation. You would never run a cross-encoder over your whole corpus. You run it over the shortlist that embeddings already narrowed down.

That is the two-stage pattern: **embeddings for cheap recall, a reranker for precise ordering.**

NeMo Retriever's reranking NIM exposes a **ranking** endpoint. You send it a query plus a list of candidate passages; it returns a relevance score for each, from which you reorder and keep the top-k. The request carries the model id, the query text, and the passages; the response carries, for each passage, its original index and a relevance score.

> **Confirm the exact path and field names in the docs.** The shape below matches the NeMo Retriever reranking (ranking) API at the time of writing — a `query` object with a `text`, a `passages` array of `{text}` objects, and a `rankings` array of `{index, logit}` in the reply. But reranking request/response fields have varied across NIM versions. Before you ship, verify the endpoint path and every JSON field name against the NeMo Retriever reranking API reference for the specific NIM you deploy. Do not assume the shape below is exact for your version.

```go
type rankQuery struct {
	Text string `json:"text"`
}

type rankPassage struct {
	Text string `json:"text"`
}

// rankRequest mirrors the documented reranking (ranking) request shape.
// VERIFY every field name and the endpoint path against the NIM's API docs.
type rankRequest struct {
	Model    string        `json:"model"`
	Query    rankQuery     `json:"query"`
	Passages []rankPassage `json:"passages"`
}

// ranking is one scored result. "logit" is the model's raw relevance score;
// a higher value means more relevant. The exact field name may differ by version.
type ranking struct {
	Index int     `json:"index"` // position in the passages array we sent
	Logit float64 `json:"logit"`
}

type rankResponse struct {
	Rankings []ranking `json:"rankings"`
}

// Scored pairs a passage with its reranker relevance score.
type Scored struct {
	Text  string
	Score float64
}

// Rerank scores each passage against the query and returns them ordered
// most-relevant first. topK <= 0 returns all of them.
func (c *Client) Rerank(ctx context.Context, model, query string, passages []string, topK int) ([]Scored, error) {
	if len(passages) == 0 {
		return nil, nil
	}
	body := rankRequest{Model: model, Query: rankQuery{Text: query}}
	for _, p := range passages {
		body.Passages = append(body.Passages, rankPassage{Text: p})
	}

	var out rankResponse
	// NOTE: confirm this path ("/ranking") against the reranking NIM's API docs.
	if err := c.postJSON(ctx, "/ranking", body, &out); err != nil {
		return nil, fmt.Errorf("rerank: %w", err)
	}
	if len(out.Rankings) == 0 {
		return nil, fmt.Errorf("rerank: no rankings returned")
	}

	scored := make([]Scored, 0, len(out.Rankings))
	for _, r := range out.Rankings {
		if r.Index < 0 || r.Index >= len(passages) {
			return nil, fmt.Errorf("rerank: index %d out of range", r.Index)
		}
		scored = append(scored, Scored{Text: passages[r.Index], Score: r.Logit})
	}

	sort.Slice(scored, func(i, j int) bool {
		return scored[i].Score > scored[j].Score
	})
	if topK > 0 && topK < len(scored) {
		scored = scored[:topK]
	}
	return scored, nil
}
```

The reranker returns results keyed by the *index we sent*, so we map each score back onto its original passage before sorting — never assume the response is already ordered, and never assume it is in input order. For `model`, use a reranking NIM id such as `nvidia/nv-rerankqa-mistral-4b-v3` or `nvidia/llama-3.2-nv-rerankqa-1b-v2` — again, **examples to verify** in the catalog.

**The gotcha:** reranking is a *separate model call per query*, and it scores every candidate you send. Send 500 passages and you pay for 500 cross-encoder comparisons on every single query — latency and cost explode. The whole point of the two-stage design is to over-retrieve only *modestly* with embeddings (say a shortlist of 20–50), then rerank that shortlist. And the opposite failure is just as common: teams skip reranking, feed the LLM the raw cosine top-5, get mushy answers, and blame the LLM. Nine times out of ten the retrieval was the problem — the reranker is what turns "roughly relevant" into "actually the right passage."

---

## Wiring it together: the retrieval core

Now assemble the pipeline. Offline (or at ingest time) you embed every passage as `"passage"` and store the vectors. At query time you embed the query as `"query"`, shortlist by cosine, rerank that shortlist, and return the final top-k. Here is a self-contained in-memory version — swap the slice for a real vector store when you scale:

```go
// Store is a trivial in-memory index. In production, back this with a
// vector database; the retrieval logic is identical.
type Store struct {
	Passages []string
	Vectors  [][]float32
}

func (c *Client) Index(ctx context.Context, embedModel string, docs []string) (*Store, error) {
	vecs, err := c.EmbedPassages(ctx, embedModel, docs) // input_type = "passage"
	if err != nil {
		return nil, err
	}
	return &Store{Passages: docs, Vectors: vecs}, nil
}

// Retrieve runs the two-stage pipeline: cosine shortlist, then rerank.
func (c *Client) Retrieve(
	ctx context.Context,
	embedModel, rerankModel, query string,
	s *Store, shortlist, topK int,
) ([]Scored, error) {
	// 1. Embed the query — as a QUERY, matching the passages' embedding model.
	qVec, err := c.EmbedQuery(ctx, embedModel, query) // input_type = "query"
	if err != nil {
		return nil, err
	}

	// 2. Cheap recall: cosine-score every stored passage, keep the shortlist.
	rough := make([]Scored, 0, len(s.Passages))
	for i, v := range s.Vectors {
		sim, err := CosineSimilarity(qVec, v)
		if err != nil {
			return nil, fmt.Errorf("scoring passage %d: %w", i, err)
		}
		rough = append(rough, Scored{Text: s.Passages[i], Score: sim})
	}
	sort.Slice(rough, func(i, j int) bool { return rough[i].Score > rough[j].Score })
	if shortlist > 0 && shortlist < len(rough) {
		rough = rough[:shortlist]
	}

	// 3. Precise reordering: rerank the shortlist, keep top-k.
	candidates := make([]string, len(rough))
	for i, r := range rough {
		candidates[i] = r.Text
	}
	return c.Rerank(ctx, rerankModel, query, candidates, topK)
}
```

A caller ties it off:

```go
func main() {
	c := retriever.NewClient(
		"https://integrate.api.nvidia.com/v1",
		os.Getenv("NVIDIA_API_KEY"),
	)
	ctx := context.Background()

	const embedModel = "nvidia/nv-embedqa-e5-v5"        // verify in the catalog
	const rerankModel = "nvidia/nv-rerankqa-mistral-4b-v3" // verify in the catalog

	docs := []string{
		"NeMo Retriever provides embedding and reranking models as NIMs.",
		"Cosine similarity measures the angle between two vectors.",
		"A cross-encoder reranker scores a query and passage together.",
		// ... your corpus ...
	}

	store, err := c.Index(ctx, embedModel, docs)
	if err != nil {
		log.Fatalf("index: %v", err)
	}

	results, err := c.Retrieve(ctx, embedModel, rerankModel,
		"How does NeMo Retriever help RAG?", store, 20, 3)
	if err != nil {
		log.Fatalf("retrieve: %v", err)
	}
	for i, r := range results {
		fmt.Printf("%d. (%.3f) %s\n", i+1, r.Score, r.Text)
	}
}
```

You now have the retrieval core of a RAG system in a few hundred lines of Go, talking to NeMo Retriever over nothing but `net/http`. Feed `results` into your generation step and the LLM finally has passages worth reasoning over.

**The gotcha:** the cosine `Score` and the reranker `Score` are on *different, incomparable scales* — cosine is bounded in [-1, 1], the reranker returns raw model scores. Don't average them or threshold them with one number. Use cosine only to *order the shortlist*, then let the reranker's scores decide the final order. They are two stages, not two votes.

---

## Key takeaways

- **No Go SDK, no problem.** Both NeMo Retriever NIMs are plain JSON over HTTP; one small `net/http` client handles the embedding and ranking endpoints alike — only `BaseURL` changes between hosted and self-hosted.
- **Respect `input_type`.** Embed stored documents as `"passage"` and live queries as `"query"`. Getting this wrong fails silently and destroys relevance.
- **One embedding model, both sides, forever.** Passage vectors and query vectors are only comparable if they came from the same model; a dimension check in cosine catches accidental mixing.
- **Two stages beat one.** Embeddings give cheap approximate recall; a cross-encoder reranker gives expensive precise ordering. Over-retrieve modestly, then rerank the shortlist.
- **Don't skip the reranker and blame the LLM.** Most "bad RAG" is bad retrieval. The reranker is what turns roughly-relevant into actually-right.
- **Verify ids and field names.** Model ids and the reranking request/response shape drift between versions — confirm both against the catalog and API docs before you ship.

---

## Further reading

- [NeMo Retriever Text Embedding NIM — documentation](https://docs.nvidia.com/nim/nemo-retriever/text-embedding/latest/overview.html)
- [NeMo Retriever Text Reranking NIM — documentation](https://docs.nvidia.com/nim/nemo-retriever/text-reranking/latest/overview.html)
- [NVIDIA NIM documentation hub](https://docs.nvidia.com/nim/index.html)
- [build.nvidia.com — model catalog and API keys](https://build.nvidia.com/)
- [Go `net/http` package reference](https://pkg.go.dev/net/http)
