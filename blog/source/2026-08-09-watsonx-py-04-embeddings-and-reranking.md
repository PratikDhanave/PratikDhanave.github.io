# Embeddings and Reranking with watsonx

*Building RAG's retrieval core with watsonx.ai from Python — turning a corpus into vectors with IBM's slate embedding models, scoring a query against them, and then sharpening the shortlist with a reranking model so the LLM gets the right passages, not just plausible ones.*

---

Retrieval-augmented generation lives or dies on one question: *did the right passages reach the model?* Everything downstream — the prompt, the temperature, the model choice — is wasted if the context you stuffed in was the wrong context. That first hop, from a user's question to a small set of genuinely relevant chunks, is the retrieval core, and watsonx.ai gives you two purpose-built model families to construct it: an **embedding** model to turn text into vectors, and a **reranking** model to reorder candidates by true relevance.

This post builds that core with the first-party `ibm-watsonx-ai` SDK. We embed a corpus, embed a query, score them with a few lines of numpy, and then do the thing most tutorials skip — feed the shortlist to a reranker and take the top-k. By the end you will have a complete `retrieve → rerank` pipeline and, more importantly, a feel for *why two stages beat one*.

---

## Part 1: Embeddings — text becomes geometry

An embedding model maps a piece of text to a fixed-length vector of floats. Texts that mean similar things land near each other in that vector space, so "how do I reset my password" and "I forgot my login credentials" end up close even though they share almost no words. That proximity is what makes semantic search work: you compare *meaning*, not keywords.

IBM's **slate** family are encoder models built specifically for retrieval — the "rtrvr" in an id like `ibm/slate-125m-english-rtrvr` signals a *retriever* variant tuned to produce vectors good for search, rather than a general-purpose encoder. Treat that id as an example to confirm against the current watsonx.ai model catalog; available embedding models and their exact ids change by region and over time.

The SDK surfaces embeddings through a dedicated class:

```python
import os
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Embeddings

credentials = Credentials(
    url="https://us-south.ml.cloud.ibm.com",   # your regional endpoint
    api_key=os.environ["WATSONX_API_KEY"],
)

embedder = Embeddings(
    model_id="ibm/slate-125m-english-rtrvr",   # example slate retriever id — verify in the docs
    credentials=credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)
```

The construction is the same three-part shape as any watsonx.ai client: a regional `url` plus IAM `api_key` in `Credentials`, a `model_id`, and the workspace `project_id` (or `space_id`). Nothing new to learn — just a different class bound to an embedding model instead of a generative one.

### Two methods, two roles

`Embeddings` gives you two methods, and the distinction between them is not cosmetic:

- **`embed_documents(texts: list[str])`** — embeds your *corpus*: a list of passages you will store and search over. Returns a list of vectors, one per input text.
- **`embed_query(text: str)`** — embeds a *single query*: the user's question you want to match against the corpus. Returns one vector.

```python
corpus = [
    "watsonx.ai runs foundation models for inference, tuning, and deployment.",
    "watsonx.governance tracks model drift, quality metrics, and factsheets.",
    "watsonx.data is an open lakehouse for the documents you retrieve over.",
    "IBM Granite models ship under a permissive open license.",
]

corpus_vectors = embedder.embed_documents(texts=corpus)   # list[list[float]]
query_vector = embedder.embed_query(text="Which watsonx product watches for model drift?")
```

Each returned vector is a plain Python list of floats. The length is fixed by the model (every vector from one model has the same dimensionality), which is exactly what lets you compare them with straight linear algebra.

**The gotcha:** `embed_documents` and `embed_query` exist to express the *corpus role* versus the *query role* — retriever models can encode the two sides asymmetrically for better matching, so use the method that matches what the text *is*. Do not run your whole corpus through `embed_query` in a loop, and do not wrap a single question in a list just to call `embed_documents`. The methods are the API's way of telling the model which side of the search it is looking at.

### Scoring locally with cosine similarity

Once query and corpus are vectors, "most relevant" becomes "nearest in vector space." The standard measure is **cosine similarity** — the cosine of the angle between two vectors, which ignores their magnitude and looks only at direction. It runs from -1 (opposite) to 1 (identical direction); higher means more similar. A dozen lines of numpy is all you need for a local shortlist:

```python
import numpy as np

def cosine_shortlist(query_vec, doc_vecs, texts, top_n=3):
    """Return the top_n (score, text) pairs by cosine similarity."""
    q = np.asarray(query_vec, dtype=np.float32)
    m = np.asarray(doc_vecs, dtype=np.float32)

    # Normalize each vector to unit length; cosine sim is then a dot product.
    q_norm = q / (np.linalg.norm(q) + 1e-10)
    m_norm = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-10)

    scores = m_norm @ q_norm            # one score per document
    order = np.argsort(scores)[::-1]    # highest score first
    return [(float(scores[i]), texts[i]) for i in order[:top_n]]

shortlist = cosine_shortlist(query_vector, corpus_vectors, corpus, top_n=3)
for score, text in shortlist:
    print(f"{score:.3f}  {text}")
```

The `+ 1e-10` guards against a divide-by-zero on an all-zero vector. For four documents this is overkill — you could eyeball it — but the pattern scales: in a real system the corpus vectors live in a vector database (FAISS, Milvus, Elasticsearch, watsonx.data, or another store) that does this nearest-neighbor search for you across millions of chunks. The math is identical; only the index changes.

**The gotcha:** you must use the **same embedding model** for the corpus and for every query. Vectors from two different models live in two different, incomparable spaces — cosine similarity between them is noise dressed up as a number, and it fails *silently*: you still get scores, they are just meaningless. If you re-embed your corpus with a new model, re-embed all queries with that same model too, and if you upgrade the model, you must re-index the whole corpus. Pin the embedding `model_id` in one place in your config and read it from there for both sides.

---

## Part 2: Reranking — precision after recall

Embedding search is fast and approximate. Each document is compressed into a single vector *once, ahead of time, without knowing the query*, so retrieval at query time is just cheap vector math. That speed is the point — it lets you search millions of chunks in milliseconds. But the compression loses information: a single vector cannot capture every way a passage might be relevant, so the top of your cosine shortlist is *usually* right and *often* slightly wrong — a near-miss ranked above the real answer, a keyword-y decoy that scored high.

A **reranker** fixes this. It is a different kind of model: instead of encoding query and document separately, it looks at the **query and one candidate passage together** and scores how well that specific passage answers that specific query. That joint view is far more precise than comparing two pre-computed vectors — and far more expensive, because it is a fresh model call per candidate. You cannot run it over a million documents. You do not have to: you run it over the *shortlist* the embeddings already narrowed down. This is the two-stage pattern — **embeddings for cheap recall, reranking for expensive precision** — and it is why serious RAG systems use both.

watsonx.ai exposes reranking through a dedicated class:

```python
from ibm_watsonx_ai.foundation_models import Rerank

reranker = Rerank(
    model_id="cross-encoder/ms-marco-minilm-l-12-v2",   # example rerank id — verify in the docs
    credentials=credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)
```

Same construction shape again — the only thing that changes is that the `model_id` names a reranking model. As with every id in this series, confirm the exact reranking model ids available to you against the current watsonx.ai docs rather than hard-coding the example above.

### The rerank call, at the request/response level

Conceptually a rerank call takes a **query** and a **list of candidate passages** and returns those candidates **reordered by relevance**, each with a relevance score and an index back into the input list. You send N candidates; you get back a ranking over those same N, best first. From there you slice the top-k and pass only those to your LLM.

The important honesty here: the *exact* method name and the *exact* field names in the response are things to confirm against the SDK's reranking documentation for the version you installed — do not trust a shape invented from memory. What is stable and safe to rely on is the request/response *contract*: query in, candidate passages in, a relevance-ordered result with per-candidate scores and original indices out. Write your code against that contract and read the precise call signature and response keys from the docs. A defensive wrapper that does not assume field names looks like this:

```python
def rerank_top_k(reranker, query, candidate_texts, k=3):
    """Rerank candidate_texts against query, return the top k texts.

    The rerank response contains, per candidate, a relevance score and the
    index of that candidate in the input list. Field names vary by SDK
    version — confirm them in the reranking docs and adjust the parsing.
    """
    response = reranker.rerank(query=query, inputs=candidate_texts)

    # The response carries a ranked list of results; each result points back
    # to its position in candidate_texts and carries a relevance score.
    results = response["results"] if isinstance(response, dict) else response
    ranked = sorted(results, key=lambda r: r["score"], reverse=True)

    top = []
    for r in ranked[:k]:
        top.append(candidate_texts[r["index"]])
    return top
```

Read that snippet as *the shape of the parsing*, not as verbatim API. The `query=`/`inputs=` argument names and the `results`/`score`/`index` keys are placeholders you replace with whatever the current SDK actually uses — the point is that a rerank response is a relevance-ordered set of results you sort and slice, and you should never invent those names when the docs state them precisely.

**The gotcha:** reranking is a **separate model call over N candidates for every query** — its cost and latency scale with N. The whole economic logic of the two-stage design collapses if you over-retrieve wildly: sending the reranker your top 500 cosine hits defeats the purpose and can dominate your request latency and bill. Over-retrieve *modestly* — pull maybe 20 to 50 candidates from the embedding stage, then rerank those down to the 3 to 5 you actually pass to the LLM. Tune those two numbers deliberately; they are the main dial on the recall-versus-cost trade-off.

---

## Wiring the two stages together

Here is the full retrieval core with error handling. The flow is: embed the corpus once (offline, ideally), then per query — embed the query, shortlist by cosine, rerank the shortlist, take the final top-k.

```python
import os
import numpy as np
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Embeddings, Rerank
from ibm_watsonx_ai.wml_client_error import WMLClientError

EMBED_MODEL_ID = "ibm/slate-125m-english-rtrvr"       # verify in the docs
RERANK_MODEL_ID = "cross-encoder/ms-marco-minilm-l-12-v2"  # verify in the docs

credentials = Credentials(
    url=os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
    api_key=os.environ["WATSONX_API_KEY"],
)
project_id = os.environ["WATSONX_PROJECT_ID"]

embedder = Embeddings(model_id=EMBED_MODEL_ID, credentials=credentials, project_id=project_id)
reranker = Rerank(model_id=RERANK_MODEL_ID, credentials=credentials, project_id=project_id)


def build_index(corpus):
    """Embed the corpus once. In production, persist these vectors."""
    try:
        vectors = embedder.embed_documents(texts=corpus)
    except WMLClientError as exc:
        raise RuntimeError(f"Corpus embedding failed: {exc}") from exc
    return np.asarray(vectors, dtype=np.float32), corpus


def cosine_shortlist(query_vec, matrix, texts, n):
    q = np.asarray(query_vec, dtype=np.float32)
    q /= np.linalg.norm(q) + 1e-10
    m = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
    order = np.argsort(m @ q)[::-1][:n]
    return [texts[i] for i in order]


def retrieve(query, matrix, texts, recall_n=20, final_k=3):
    """Two-stage retrieval: cosine recall, then rerank for precision."""
    try:
        query_vec = embedder.embed_query(text=query)
    except WMLClientError as exc:
        raise RuntimeError(f"Query embedding failed: {exc}") from exc

    candidates = cosine_shortlist(query_vec, matrix, texts, recall_n)

    try:
        response = reranker.rerank(query=query, inputs=candidates)
        results = response["results"] if isinstance(response, dict) else response
        ranked = sorted(results, key=lambda r: r["score"], reverse=True)
        return [candidates[r["index"]] for r in ranked[:final_k]]
    except WMLClientError as exc:
        # Reranking is a refinement — if it fails, degrade to cosine order
        # rather than returning nothing.
        return candidates[:final_k]


if __name__ == "__main__":
    corpus = [
        "watsonx.ai runs foundation models for inference, tuning, and deployment.",
        "watsonx.governance tracks model drift, quality metrics, and factsheets.",
        "watsonx.data is an open lakehouse for the documents you retrieve over.",
        "IBM Granite models ship under a permissive open license.",
    ]
    matrix, texts = build_index(corpus)
    for passage in retrieve("Which product watches models for drift?", matrix, texts, recall_n=4, final_k=2):
        print(passage)
```

Note the small resilience decision in `retrieve`: reranking is a *refinement* over an already-decent cosine order, so if the rerank call fails we fall back to the embedding order instead of returning an empty result. Embedding failures, by contrast, are fatal — with no vectors there is nothing to search — so those propagate. The exact exception type to catch is worth confirming against the SDK; `WMLClientError` is the SDK's general client-error base, and catching it keeps a transient service error from taking down the whole request.

**The gotcha:** do not skip the rerank stage and then blame the LLM when your RAG answers are weak. A huge share of "the model hallucinated" and "it ignored my documents" complaints are really *retrieval* failures — the right passage never made it into the context because cosine similarity ranked a near-miss above it. Adding a reranker over a modest shortlist is often the single highest-leverage fix for a mediocre RAG system, and it is a few lines of code, not a model swap.

---

## The LangChain path

If your application already lives in LangChain, the `langchain-ibm` package wraps both capabilities so they slot into retrievers and chains you already have. `WatsonxEmbeddings` is a drop-in embeddings backend for any LangChain vector store, and `WatsonxRerank` is a document compressor you place in front of a base retriever so the two-stage pattern happens automatically.

```python
from langchain_ibm import WatsonxEmbeddings, WatsonxRerank

embeddings = WatsonxEmbeddings(
    model_id="ibm/slate-125m-english-rtrvr",   # verify in the docs
    url="https://us-south.ml.cloud.ibm.com",
    project_id=os.environ["WATSONX_PROJECT_ID"],
)

reranker = WatsonxRerank(
    model_id="cross-encoder/ms-marco-minilm-l-12-v2",   # verify in the docs
    url="https://us-south.ml.cloud.ibm.com",
    project_id=os.environ["WATSONX_PROJECT_ID"],
)
# WatsonxRerank plugs into a ContextualCompressionRetriever wrapping your
# vector-store retriever, so retrieve-then-rerank runs as one retriever call.
```

Same engine, familiar steering wheel: `WatsonxEmbeddings` and `WatsonxRerank` call the same watsonx.ai models as the first-party classes, just packaged for LangChain's retriever abstractions. Confirm the constructor arguments and the recommended wiring against the `langchain-ibm` docs, since the integration layer tracks LangChain's own conventions.

---

## Key takeaways

- **Embeddings turn text into comparable geometry.** Use `Embeddings` from `ibm-watsonx-ai` with a slate retriever model; `embed_documents` for the corpus, `embed_query` for the question — the two methods encode the two roles.
- **Cosine similarity is the local scorer.** Normalize, dot-product, sort. At scale a vector database does this for you; the math is unchanged.
- **Use one embedding model for both sides, always.** Mismatched models produce incomparable vectors and fail silently — pin the id in config and re-index if you ever change it.
- **Reranking buys precision that embeddings cannot.** A reranker scores query and passage *together*, so it corrects the near-misses at the top of a cosine shortlist. Confirm the exact method and response fields in the SDK reranking docs rather than inventing them.
- **Two stages, tuned numbers.** Over-retrieve modestly (tens of candidates), rerank down to a handful. Skipping the rerank stage is the most common hidden cause of weak RAG.
- **LangChain users get the same power via `WatsonxEmbeddings` and `WatsonxRerank`** — the identical models, wrapped for retrievers and chains.

---

## Further reading

- [`ibm-watsonx-ai` SDK — Embeddings](https://ibm.github.io/watsonx-ai-python-sdk/fm_embeddings.html)
- [`ibm-watsonx-ai` SDK — Rerank / reranking](https://ibm.github.io/watsonx-ai-python-sdk/fm_rerank.html)
- [`ibm-watsonx-ai` SDK — API reference](https://ibm.github.io/watsonx-ai-python-sdk/)
- [IBM watsonx.ai — supported embedding models](https://www.ibm.com/docs/en/watsonx/saas?topic=models-supported-embedding)
- [IBM watsonx.ai — supported reranker models](https://www.ibm.com/docs/en/watsonx/saas?topic=models-supported-reranker)
- [IBM Granite and slate model documentation](https://www.ibm.com/granite/docs/)
- [`langchain-ibm` — WatsonxEmbeddings](https://python.langchain.com/docs/integrations/text_embedding/ibm_watsonx/)
- [`langchain-ibm` — WatsonxRerank](https://python.langchain.com/docs/integrations/document_transformers/ibm_watsonx_ranker/)
