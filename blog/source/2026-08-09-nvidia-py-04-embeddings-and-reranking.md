# Embeddings and Reranking with NeMo Retriever

*Building RAG's retrieval core in Python — turning a corpus and a query into vectors with NeMo Retriever embedding NIMs, scoring by cosine similarity, then sharpening the shortlist with a cross-encoder reranker NIM.*

---

Retrieval-augmented generation lives or dies on retrieval. If the passages you hand the model are the wrong ones, no amount of prompt engineering rescues the answer — the model will confidently summarize irrelevant text. The two workhorses that decide *which* passages reach the model are **embeddings** (fast, approximate recall over the whole corpus) and **reranking** (slow, precise scoring of a small shortlist). NVIDIA ships both as **NeMo Retriever** models, packaged as NIMs — self-hostable inference microservices with an OpenAI-compatible API surface — and exposes them in Python through the `langchain-nvidia-ai-endpoints` package.

This post builds the retrieval core end to end: embed a corpus, embed a query, score locally with a few lines of NumPy, then rerank the survivors with a cross-encoder and take the final top-k. Every code sample uses real libraries and real method signatures. Model ids are shown as examples to verify against the live catalog at [build.nvidia.com](https://build.nvidia.com) — treat them as placeholders you confirm, not gospel.

---

## Setup: one client library, one API key

Install the LangChain integration. It pulls in what you need to call the hosted NIMs on NVIDIA's API catalog, and the same classes work against a NIM you self-host by pointing `base_url` at your own endpoint.

```bash
pip install langchain-nvidia-ai-endpoints numpy
export NVIDIA_API_KEY="nvapi-..."   # from build.nvidia.com
```

Two classes carry this whole post:

- `NVIDIAEmbeddings` — the embedding NIM client. Turns text into dense vectors.
- `NVIDIARerank` — the reranking NIM client. Reorders a candidate list by relevance to a query.

Both read `NVIDIA_API_KEY` from the environment by default, so you rarely pass the key explicitly.

---

## Part 1 — Embeddings: text becomes geometry

An embedding model maps a chunk of text to a fixed-length vector of floats. The useful property is that *semantic closeness becomes geometric closeness*: two passages about the same topic land near each other in the vector space, even when they share no words. That is what lets you find "the document about refund windows" from a query that says "how long do I have to return this" — no keyword overlaps, but the vectors are neighbors.

`NVIDIAEmbeddings` gives you two methods, and the distinction between them is the single most important detail in this post:

- `embed_documents(list[str])` — encode a list of corpus passages. Returns a `list[list[float]]`, one vector per passage.
- `embed_query(str)` — encode a single search query. Returns one `list[float]`.

```python
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

# Example model id — confirm the exact string in the build.nvidia.com catalog.
embedder = NVIDIAEmbeddings(model="nvidia/nv-embedqa-e5-v5")

corpus = [
    "NIM microservices package a model with an OpenAI-compatible HTTP API.",
    "Cosine similarity measures the angle between two vectors, ignoring magnitude.",
    "A cross-encoder scores a query and document together in a single forward pass.",
    "GPUs accelerate the matrix multiplies at the heart of transformer inference.",
]

doc_vectors = embedder.embed_documents(corpus)   # list[list[float]]
query_vector = embedder.embed_query("What is a NIM?")  # list[float]

print(len(doc_vectors), "document vectors")
print("dimensionality:", len(query_vector))
```

### Why passages and queries are encoded differently

Here is the part people miss. A well-designed retrieval embedding model is **asymmetric**: passages and queries live in the *same* vector space so you can compare them, but they are *encoded differently* on the way in. A stored passage is usually a full, self-contained statement; a query is often a short, incomplete question. Retrieval-tuned models (the "QA" family, hence names like `nv-embedqa-*`) are trained on query/passage pairs and internally tag each input with its role — frequently by prepending an instruction like "represent this passage for retrieval" versus "represent this question for retrieving passages." That role tag nudges the two kinds of text so that a terse question lands near the fuller passage that answers it.

You do not construct those tags yourself. **The methods encode the distinction for you**: `embed_documents` applies the passage role, `embed_query` applies the query role. This is the entire reason the API has two methods instead of one generic `embed(text)`. Calling the right method is how you opt into the asymmetric behavior the model was trained to deliver.

**The gotcha:** `embed_documents` and `embed_query` are *not* interchangeable. If you embed your search query with `embed_documents` (or embed your corpus with `embed_query`), the call still succeeds, still returns same-length vectors, and still produces plausible-looking similarity scores — but retrieval quality quietly degrades because the query got the passage role and now sits in the wrong neighborhood. There is no exception, no warning. This is the asymmetric-embedding trap, and it is handled for you *only if you call the matching method for each side*. Corpus goes through `embed_documents`; live queries go through `embed_query`. Always.

### Scoring locally with cosine similarity

Once text is vectors, "most relevant" becomes "nearest neighbor." The standard distance for text embeddings is **cosine similarity** — the cosine of the angle between two vectors, which ranges from -1 (opposite) to 1 (identical direction) and, crucially, ignores vector length so a long passage isn't penalized for being long.

A few lines of NumPy score a query against the whole corpus:

```python
import numpy as np

def cosine_scores(query_vec, doc_vecs):
    """Cosine similarity of one query vector against a matrix of doc vectors."""
    q = np.asarray(query_vec, dtype=np.float32)
    m = np.asarray(doc_vecs, dtype=np.float32)
    # Normalize to unit length, then a dot product IS the cosine.
    q_norm = q / (np.linalg.norm(q) + 1e-12)
    m_norm = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-12)
    return m_norm @ q_norm   # shape: (num_docs,)

scores = cosine_scores(query_vector, doc_vectors)
ranked = np.argsort(scores)[::-1]   # indices, best first

for rank, idx in enumerate(ranked, 1):
    print(f"{rank}. score={scores[idx]:.3f}  {corpus[idx]}")
```

The `1e-12` guards against a divide-by-zero on a degenerate zero vector. In a real system you would not loop over every document with NumPy — you would push the vectors into a vector database (FAISS, Milvus, pgvector) that does approximate nearest-neighbor search in sub-linear time. But the math is exactly this, and for a few thousand chunks a normalized dot product in memory is perfectly fine and easy to reason about.

**The gotcha:** you *must* embed your corpus and your queries with the **same** embedding model. Vectors from `nv-embedqa-e5-v5` and vectors from some other model do not share a coordinate system; comparing across them yields numbers that mean nothing. This also bites on upgrades — the day you switch embedding models, every stored vector is stale and the whole corpus must be re-embedded before it can be compared against new queries. Version your index by the model that produced it.

### The raw `openai` client also works

Because a NeMo Retriever embedding NIM speaks the OpenAI embeddings API, you are not locked into LangChain. You can call the exact same model with the plain `openai` client by pointing `base_url` at the NIM endpoint:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="nvapi-...",
)

resp = client.embeddings.create(
    model="nvidia/nv-embedqa-e5-v5",
    input=["NIM microservices expose an OpenAI-compatible API."],
)
vector = resp.data[0].embedding
```

The tradeoff: the raw client won't apply the passage-vs-query role for you — some NeMo embedding NIMs accept an `input_type` field (values along the lines of `"passage"` / `"query"`) in the request to express that distinction. `NVIDIAEmbeddings` sets it via the two methods so you don't have to think about it, which is exactly why the LangChain wrapper is the friendlier default for retrieval. Reach for the raw client when you're integrating into non-LangChain code or want direct control over the request body — but then it's on you to send the right `input_type`.

---

## Part 2 — Reranking: precision after recall

Embedding search is fast because it's *decoupled*: every passage is embedded once, ahead of time, and at query time you compare one query vector against precomputed vectors. That decoupling is also its weakness. The model never sees the query and a passage *together* — it compressed each passage into a single vector before it knew what anyone would ask. Two texts can look like neighbors in the vector space while missing the specific nuance a query cares about. Embeddings give you good *recall* (the right answer is probably somewhere in the top 50) but mediocre *precision at the very top* (it might be ranked 11th, not 1st).

A **reranker** fixes the top. It's a **cross-encoder**: instead of embedding query and passage separately, it feeds the query and one candidate passage through the model *together* and outputs a single relevance score. Because the two texts attend to each other inside the model, a cross-encoder judges relevance far more precisely than a dot product of two independent vectors. The cost is that it's *not* precomputable — you pay a forward pass for every (query, candidate) pair at query time, so you can only afford to run it on a shortlist, never the whole corpus.

That's the two-stage pattern, and it beats either stage alone:

1. **Retrieve** a modest shortlist (say, top 20–50) cheaply with embeddings — high recall.
2. **Rerank** that shortlist with the cross-encoder and keep the final top-k (say, 3–5) — high precision.

`NVIDIARerank` wraps the NeMo Retriever reranking NIM. Its method is `compress_documents(documents, query)`, which takes LangChain `Document` objects plus the query string and returns the documents **reordered by relevance**, most relevant first.

```python
from langchain_nvidia_ai_endpoints import NVIDIARerank
from langchain_core.documents import Document

# Example model id — confirm the exact string in the catalog.
reranker = NVIDIARerank(
    model="nvidia/nv-rerankqa-mistral-4b-v3",
    top_n=3,   # keep only the best 3 after reranking
)

query = "How does a cross-encoder differ from embedding search?"

# Turn a shortlist of passage strings into Document objects.
shortlist = [Document(page_content=text) for text in corpus]

reranked = reranker.compress_documents(documents=shortlist, query=query)

for rank, doc in enumerate(reranked, 1):
    score = doc.metadata.get("relevance_score")
    print(f"{rank}. score={score}  {doc.page_content}")
```

`compress_documents` returns a list of `Document` objects in relevance order; each carries a `relevance_score` in its `metadata` so you can threshold or log it. The `top_n` constructor argument caps how many survive — the "compress" in the name is literal: it hands back a shorter, sharper list than it received.

**The gotcha:** reranking is a *separate model call that scores every candidate you pass it*. Its cost and latency scale with the size of the shortlist, so over-retrieving is not free. Pull the top 500 from your vector store "to be safe" and you've turned one cheap embedding lookup into 500 cross-encoder forward passes per query — latency and bill both balloon. Over-retrieve *modestly* (tens, not hundreds), then rerank. The shortlist is a knob you tune against your latency budget, not a place to be generous.

---

## Wiring it together

Here is the full retrieval core: embed the corpus once, embed the query, shortlist by cosine, rerank the shortlist, return the final top-k. Error handling wraps every network call, because a NIM request can fail for the ordinary reasons any HTTP call can — bad key, rate limit, transient timeout.

```python
import numpy as np
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, NVIDIARerank
from langchain_core.documents import Document

EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"       # verify in the catalog
RERANK_MODEL = "nvidia/nv-rerankqa-mistral-4b-v3"  # verify in the catalog


def cosine_scores(query_vec, doc_vecs):
    q = np.asarray(query_vec, dtype=np.float32)
    m = np.asarray(doc_vecs, dtype=np.float32)
    q /= np.linalg.norm(q) + 1e-12
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-12
    return m @ q


def build_index(corpus, embedder):
    """Embed the corpus once. In production this vector store is persisted."""
    vectors = embedder.embed_documents(corpus)   # passage role
    return np.asarray(vectors, dtype=np.float32)


def retrieve(query, corpus, index, embedder, reranker,
             shortlist_size=20, final_k=3):
    # Stage 1: cheap recall via embeddings + cosine.
    q_vec = embedder.embed_query(query)          # query role — NOT embed_documents
    scores = cosine_scores(q_vec, index)
    top_idx = np.argsort(scores)[::-1][:shortlist_size]
    shortlist = [Document(page_content=corpus[i]) for i in top_idx]

    # Stage 2: precise reordering via the cross-encoder reranker.
    reranked = reranker.compress_documents(documents=shortlist, query=query)
    return reranked[:final_k]


def main():
    corpus = [
        "NIM microservices package a model with an OpenAI-compatible HTTP API.",
        "Cosine similarity measures the angle between two vectors, ignoring magnitude.",
        "A cross-encoder scores a query and document together in one forward pass.",
        "GPUs accelerate the matrix multiplies at the heart of transformer inference.",
        "NeMo Retriever provides embedding and reranking models as NIMs.",
        "Vector databases do approximate nearest-neighbor search in sub-linear time.",
    ]
    query = "Why add a reranker on top of embedding search?"

    try:
        embedder = NVIDIAEmbeddings(model=EMBED_MODEL)
        reranker = NVIDIARerank(model=RERANK_MODEL, top_n=3)
    except Exception as exc:
        raise SystemExit(f"Failed to initialize NIM clients: {exc}")

    try:
        index = build_index(corpus, embedder)
        results = retrieve(query, corpus, index, embedder, reranker)
    except Exception as exc:
        # Network, auth, or rate-limit failures surface here.
        raise SystemExit(f"Retrieval failed: {exc}")

    print(f"Query: {query}\n")
    for rank, doc in enumerate(results, 1):
        score = doc.metadata.get("relevance_score")
        print(f"{rank}. score={score}  {doc.page_content}")


if __name__ == "__main__":
    main()
```

The flow is worth internalizing because it's the skeleton of essentially every serious RAG pipeline: **embed corpus → store → embed query → shortlist by similarity → rerank → final top-k → feed to the LLM.** Swap the in-memory NumPy index for a vector database and this scales to millions of chunks without changing the shape.

**The gotcha:** don't skip reranking and then blame the LLM for bad RAG. When answers are subtly off-topic, the reflex is to tweak the prompt or swap the generation model — but if stage one handed the LLM the 11th-best passage instead of the 1st, the generator was doomed before it saw a token. Reranking is the cheapest, highest-leverage quality win in most RAG systems precisely because it fixes the input the LLM never gets to see you got wrong. Measure retrieval quality (is the gold passage in your final top-k?) before you touch generation.

---

## Embeddings vs. reranking at a glance

| | Embeddings (bi-encoder) | Reranking (cross-encoder) |
|---|---|---|
| Sees query + passage together | No — encoded separately | Yes — one joint forward pass |
| Precomputable | Yes — embed corpus once | No — runs per query at query time |
| Speed | Fast; scales to millions | Slow; run on a shortlist only |
| Strength | Recall (finds the neighborhood) | Precision (nails the top ranks) |
| Python method | `embed_documents` / `embed_query` | `compress_documents(documents, query)` |
| Role in the pipeline | Stage 1: shortlist the corpus | Stage 2: reorder the shortlist |

---

## Key takeaways

- **Two methods, on purpose.** `embed_documents` encodes passages, `embed_query` encodes queries — the model is asymmetric, and calling the matching method is how you opt into the retrieval-tuned behavior. Mixing them silently wrecks quality with no error.
- **Same model, both sides.** Corpus and queries must be embedded by the same model, or the vectors don't share a coordinate system. Re-embed the whole corpus when you upgrade models.
- **Cosine on unit vectors is just a dot product.** A few lines of NumPy score a query against a corpus; a vector DB does the same math at scale.
- **Two stages beat one.** Embeddings give recall, the cross-encoder reranker gives precision. Retrieve a modest shortlist, then `compress_documents` to sharpen the top-k.
- **Over-retrieve modestly.** Reranking cost scales with shortlist size — tens of candidates, not hundreds.
- **Fix retrieval before generation.** Bad RAG is usually bad retrieval. Reranking is the highest-leverage fix, and it lives entirely upstream of the LLM.
- **OpenAI-compatible either way.** Use `NVIDIAEmbeddings` for the free passage/query handling, or the raw `openai` client against the NIM `base_url` when you want direct control — just remember to send the right `input_type` yourself.

---

## Further reading

- [NeMo Retriever documentation](https://docs.nvidia.com/nemo/retriever/) — the embedding and reranking NIMs, deployment, and model catalog.
- [`langchain-nvidia-ai-endpoints` — text embeddings](https://python.langchain.com/docs/integrations/text_embedding/nvidia_ai_endpoints/) — `NVIDIAEmbeddings`, `embed_documents`, and `embed_query`.
- [`langchain-nvidia-ai-endpoints` — reranking](https://python.langchain.com/docs/integrations/retrievers/nvidia_rerank/) — `NVIDIARerank` and `compress_documents`.
- [build.nvidia.com](https://build.nvidia.com) — the live catalog; confirm the exact embedding and reranking model ids and dimensions.
