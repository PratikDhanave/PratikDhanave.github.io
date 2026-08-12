# Embeddings

*Turn text into a `[]float32` that places meaning in space — what an embedding is, cosine similarity implemented by hand in Go, calling an OpenAI-compatible /embeddings endpoint with net/http, and a worked pairwise-similarity example that scores related sentences higher.*

---

So far in this series the model has only ever handed us text back. Post 4 built a typed client that sends a list of messages and reads a completion. That is enough to *chat*, but it is not enough to *retrieve* — to answer "which of my ten thousand documents is relevant to this question?" A keyword search can find documents that share words with the query, but it is blind to meaning: "car" and "automobile" look like different strings, and "the bank raised rates" and "the river bank flooded" look like the same word. Embeddings are the fix. They convert a piece of text into a fixed-length vector of numbers such that texts *about the same thing* end up close together, even when they share no words at all.

This post is the from-scratch foundation for retrieval. We will define exactly what an embedding is, implement the similarity math ourselves so nothing is a black box, call a real embeddings endpoint with the same standard-library tools from post 4, and run a small experiment that shows related sentences scoring higher than unrelated ones. Post 8 takes this and searches *many* vectors efficiently; post 9 assembles both into RAG.

---

## An embedding is a vector

Strip away the mystique and an embedding is just a slice of floats:

```go
// A 5-dimensional embedding of some text.
vec := []float32{0.021, -0.114, 0.087, -0.043, 0.190}
```

Real models produce far larger vectors — a fixed size the model was trained to output, commonly somewhere in the hundreds to low thousands of dimensions (a given model might emit 384, 768, 1536, or more; the exact number is a property of the model, not something you choose). Every text you send that model back comes out as a vector of *that same length*. That fixed length is what makes the vectors comparable: they all live in the same high-dimensional space, and each dimension is a coordinate along one axis of that space.

The magic is not in any single number — no dimension means "is about cars." The meaning is *distributed* across all of them, learned during training so that texts humans consider similar land near each other geometrically. You never interpret the components by hand. You only ever ask one kind of question: **how close are two of these vectors?** Closeness in the space is the model's learned proxy for similarity in meaning.

This is fundamentally different from keyword matching. A keyword index compares *surface form* — the literal characters. An embedding compares *position in a learned semantic space*. "How do I reset my password?" and "I forgot my login credentials" share almost no words, but a good embedding model places them near each other because they mean nearly the same thing. That is the entire reason embeddings exist.

---

## Measuring closeness: dot product, magnitude, cosine

To turn "close" into a number we need geometry. Three quantities do all the work, and we will write each one in plain Go.

The **dot product** multiplies the vectors component-by-component and sums the result. It is the raw ingredient for everything else:

```go
func dot(a, b []float32) float32 {
	var sum float32
	for i := range a {
		sum += a[i] * b[i]
	}
	return sum
}
```

The **magnitude** (or L2 norm) is the length of a vector — the square root of its dot product with itself. It tells you how "far out" the vector reaches from the origin:

```go
import "math"

func magnitude(a []float32) float32 {
	return float32(math.Sqrt(float64(dot(a, a))))
}
```

Notice we widen to `float64` for `math.Sqrt` and narrow back. Go's `math` package operates on `float64`, so the conversions are unavoidable; we will come back to why staying disciplined about float widths matters.

Now the important one. **Cosine similarity** measures the *angle* between two vectors, ignoring their lengths. It is the dot product divided by the product of the two magnitudes:

```go
func cosine(a, b []float32) float32 {
	magA := magnitude(a)
	magB := magnitude(b)
	if magA == 0 || magB == 0 {
		return 0 // a zero vector has no direction; refuse to divide by zero
	}
	return dot(a, b) / (magA * magB)
}
```

Cosine ranges from **-1** (pointing in exactly opposite directions) through **0** (perpendicular, unrelated) to **1** (pointing the same way, maximally similar). For text embeddings the values you see in practice are usually positive, and higher means more similar.

Why the *angle* rather than the straight-line (Euclidean) distance between the two points? Because for text, direction encodes meaning and length often encodes incidentals like document length or word count. Two passages about the same topic can differ in magnitude simply because one is longer, yet point in nearly the same direction. Euclidean distance would penalize that length difference; cosine ignores it and compares only orientation. That is why cosine is the default similarity for text, and why almost every vector database defaults to it.

**The gotcha:** a bare dot product is *not* cosine similarity. The dot product mixes direction and length together — a longer vector produces a bigger dot product even at the same angle. Cosine only equals the dot product in one special case: when both vectors have magnitude 1. Skip the division by magnitudes and you are silently ranking by "length times alignment" instead of "alignment," which quietly corrupts your rankings whenever vector lengths vary.

---

## Normalize once, then dot products are free

That special case is worth engineering for. If you scale every vector to length 1 — **L2 normalization** — then `magA * magB == 1` for any pair, and `cosine(a, b)` collapses to plain `dot(a, b)`. Normalizing turns an expensive per-comparison operation (two square roots) into a one-time cost you pay when you first store the vector:

```go
func normalize(a []float32) []float32 {
	mag := magnitude(a)
	if mag == 0 {
		return a // nothing sensible to do with an all-zero vector
	}
	out := make([]float32, len(a))
	for i := range a {
		out[i] = a[i] / mag
	}
	return out
}
```

After `a = normalize(a)` and `b = normalize(b)`, `dot(a, b)` *is* the cosine similarity — no per-query square roots at all. When you are comparing one query against thousands of stored vectors (post 8's whole problem), that saving compounds. The pattern is: **normalize once at write time, dot-product at read time.** We return a new slice rather than mutating in place so the caller keeps the original if they need it; for a hot path you might normalize in place to avoid the allocation.

**The gotcha:** normalization only helps if you apply it *consistently*. If you normalize your stored vectors but forget to normalize the query — or vice versa — your "dot product equals cosine" shortcut breaks and the scores are wrong. Either normalize everything and use `dot`, or normalize nothing and use `cosine`. Don't mix the two conventions in one codebase.

---

## Getting embeddings from an API

We do not train the model — we call one. The OpenAI-compatible embeddings endpoint is a sibling of the chat endpoint from post 4, and dozens of providers and local runtimes speak the same shape. You **POST** to `/embeddings` a JSON body with a `model` and an `input`, and you get back a `data` array where each element carries an `embedding` field — an array of floats.

The request and response as Go structs, reusing exactly the net/http and encoding/json muscles from post 4:

```go
package embed

type embedRequest struct {
	Model string   `json:"model"`
	Input []string `json:"input"` // batch: one vector back per string
}

type embedResponse struct {
	Data []struct {
		Index     int       `json:"index"`
		Embedding []float32 `json:"embedding"`
	} `json:"data"`
	Model string `json:"model"`
	Usage struct {
		PromptTokens int `json:"prompt_tokens"`
		TotalTokens  int `json:"total_tokens"`
	} `json:"usage"`
}
```

The `input` is a slice on purpose: the endpoint accepts a whole batch in one call and returns one embedding per input. The `Index` field on each result tells you which input it corresponds to — providers are expected to return them in order, but reading `Index` keeps you correct even if that ever changes. `encoding/json` decodes a JSON array of numbers straight into `[]float32` for us, so parsing is nearly free.

The client mirrors post 4's structure — a shared `*http.Client`, a key from the environment, a context for cancellation:

```go
import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

type Client struct {
	BaseURL    string
	APIKey     string
	Model      string
	HTTPClient *http.Client
}

func NewClient() (*Client, error) {
	key := os.Getenv("LLM_API_KEY")
	if key == "" {
		return nil, fmt.Errorf("LLM_API_KEY is not set")
	}
	return &Client{
		BaseURL:    "https://api.openai.com/v1",
		APIKey:     key,
		Model:      "text-embedding-3-small",
		HTTPClient: &http.Client{Timeout: 30 * time.Second},
	}, nil
}

// Embed returns one vector per input string, in input order.
func (c *Client) Embed(ctx context.Context, inputs []string) ([][]float32, error) {
	payload, err := json.Marshal(embedRequest{Model: c.Model, Input: inputs})
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		c.BaseURL+"/embeddings", bytes.NewReader(payload))
	if err != nil {
		return nil, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.APIKey)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("api error %d: %s", resp.StatusCode, body)
	}

	var out embedResponse
	if err := json.Unmarshal(body, &out); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}

	vecs := make([][]float32, len(out.Data))
	for _, d := range out.Data {
		vecs[d.Index] = d.Embedding // place by Index, not append order
	}
	return vecs, nil
}
```

Everything that made the chat client robust carries over: read the body before checking the status so a provider error message survives, thread a `context.Context` so a slow call can be cancelled, and read the key from the environment rather than a literal. The only new idea is the batch: one HTTP round-trip yields many vectors.

**The gotcha:** never compare embeddings produced by *different models or model versions*. Each model learns its own space with its own axes; a vector from `text-embedding-3-small` and a vector from some other model are coordinates in incompatible coordinate systems, and their cosine similarity is meaningless noise. If you re-embed your corpus with a new model, you must re-embed **everything**, including old stored vectors — you cannot mix generations. Store the model name alongside your vectors so you can detect a mismatch instead of silently returning garbage.

---

## A worked example: pairwise similarity

Let us prove the claim that related sentences score higher. We embed six short sentences — two about pets, two about programming, two about weather — and print the cosine similarity of every pair.

```go
func main() {
	c, err := embed.NewClient()
	if err != nil {
		log.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	texts := []string{
		"My cat sleeps on the windowsill all afternoon.",
		"The dog chased its tail around the yard.",
		"Go compiles to a single static binary.",
		"Rust guarantees memory safety without a garbage collector.",
		"Heavy rain is expected across the coast tonight.",
		"Tomorrow will be sunny with a light breeze.",
	}

	vecs, err := c.Embed(ctx, texts) // one batched call for all six
	if err != nil {
		log.Fatal(err)
	}
	for i := range vecs {
		vecs[i] = normalize(vecs[i]) // normalize once; dot == cosine afterwards
	}

	for i := 0; i < len(texts); i++ {
		for j := i + 1; j < len(texts); j++ {
			fmt.Printf("%.3f  [%d]<->[%d]\n", dot(vecs[i], vecs[j]), i, j)
		}
	}
}
```

Because we normalized every vector, the inner `dot` *is* cosine similarity. The exact numbers depend on the model, but the *structure* of the output is the point — the within-topic pairs sit well above the across-topic pairs:

```text
0.61  [0]<->[1]   cat / dog          (both pets — high)
0.58  [2]<->[3]   Go / Rust          (both languages — high)
0.67  [4]<->[5]   rain / sunny       (both weather — high)
0.12  [0]<->[2]   cat / Go           (unrelated — low)
0.09  [1]<->[4]   dog / rain         (unrelated — low)
0.14  [3]<->[5]   Rust / weather     (unrelated — low)
```

No shared vocabulary drove the pet pair together — "cat" and "dog" appear in neither of each other's sentences. The model placed them near each other because it learned they occupy similar semantic territory. That is retrieval's whole engine: to find the documents relevant to a query, embed the query, then rank stored documents by cosine similarity and take the top few. Post 8 is about doing that ranking fast when there are millions of vectors instead of six.

**The gotcha:** pick `float32` *or* `float64` for your vectors and hold the line across your whole pipeline. Most embedding APIs return 32-bit-precision floats and most vector stores keep `float32` to halve memory, so `float32` is the sensible default — but the moment you mix widths (decode as `float64` here, store as `float32` there, compare across the two) you invite subtle rounding drift that nudges similarity scores and reorders your top results. Decide once, encode it in your struct tags, and convert only where a library like `math` forces your hand.

---

## Practical notes

A few habits keep an embedding pipeline correct and cheap.

| Practice | Why it matters |
|---|---|
| Batch inputs per request | One HTTP round-trip for many texts amortizes latency and cost; the endpoint returns one vector per input. |
| Normalize once at write time | Turns every later comparison into a plain dot product — no per-query square roots. |
| Store the model name with each vector | Lets you detect and refuse cross-model comparisons instead of silently returning noise. |
| Guard the all-zero vector | An empty or degenerate input can yield a zero vector; cosine then divides by zero — return 0 and move on. |
| Cache embeddings | The same text always embeds to the same vector for a given model; re-embedding unchanged text is wasted spend. |

The through-line is that embeddings are *model-specific, fixed-length, and reusable*. Compute them once, normalize them once, store them next to the identity of the model that made them, and every downstream comparison is a single cheap loop. With that foundation in place, the next post can focus entirely on the hard part we deferred here: searching many vectors quickly.

---

## Key takeaways

- **An embedding is a fixed-length `[]float32`** whose position in a learned high-dimensional space encodes meaning; the model's dimension count is fixed, not something you pick.
- **Embeddings compare meaning, not surface form** — texts with no shared words still score high if they mean the same thing, which keyword matching can never do.
- **Cosine similarity is the dot product over the product of magnitudes.** It measures angle, ignores length, and is the right default for text; raw Euclidean distance penalizes incidental length differences.
- **Normalize once and cosine becomes a bare dot product.** L2-normalize at write time, then rank with a single multiply-and-sum loop — but apply the convention consistently to both stored vectors and queries.
- **Vectors are only comparable within one model.** Never mix generations, guard the zero vector against divide-by-zero, and pick one float width for the whole pipeline.

---

## Further reading

- [OpenAI API reference — Embeddings](https://platform.openai.com/docs/api-reference/embeddings) — the `/embeddings` request/response shape this post mirrors, including the `data[].embedding` array.
- [Cohere — Introduction to Embeddings](https://docs.cohere.com/docs/embeddings) — a second provider's take on the same concept, with its own model families and dimensions.
- [Wikipedia — Cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity) — the underlying definition, its relation to the dot product, and why it is used for high-dimensional text vectors.
- [Go `math` package documentation](https://pkg.go.dev/math) — `Sqrt` and the `float64` domain that forces the width conversions in `magnitude`.
- [Go `encoding/json` package documentation](https://pkg.go.dev/encoding/json) — decoding a JSON array of numbers straight into a `[]float32`.
