# RAG on watsonx

*Assembling a full retrieval-augmented generation pipeline in Python on watsonx.ai — ingest and chunk documents, embed them with slate, retrieve by cosine, rerank for precision, then generate a grounded, cited answer with a Granite model, shown both from scratch and with langchain-ibm.*

---

The two previous posts built the pieces. Post 2 got you making inference calls — `ModelInference.chat` for grounded generation and `ChatWatsonx` when watsonx.ai is one swappable part of a LangChain app. Post 4 built the retrieval core — `Embeddings.embed_documents` for a corpus, `embed_query` for a question, cosine similarity for a shortlist, and a reranker to sharpen it. This post wires all of that into one pipeline: **retrieval-augmented generation**.

RAG exists to solve a specific problem. A foundation model only knows what was in its training data, frozen at a cutoff, with no access to your private documents and no way to cite a source. RAG fixes that by *retrieving* the relevant passages from your own corpus at query time and *augmenting* the prompt with them, so the model answers from evidence you supply rather than from parametric memory alone. The shape is always the same four stages — **ingest, retrieve, rerank, generate** — and every one of them is concrete Python you can run against your own watsonx.ai project.

---

## Stage 1: Ingest — documents become searchable chunks

You cannot embed a 40-page PDF as one vector; the meaning smears and retrieval returns nothing useful. Ingestion splits each document into **chunks** small enough that one chunk is about one idea, embeds each chunk, and stores the vectors. Two decisions dominate: how you get *clean text* out of the source files, and how you *split* that text.

For real documents — PDFs, Word files, slide decks, HTML — parsing is where quality is won or lost. IBM's open-source **Docling** project (`github.com/docling-project/docling`) converts those formats into clean, structured text (and Markdown), preserving reading order, tables, and layout that a naive PDF text-dump mangles. It is the accurate front door for messy source material. For plain text you already have, you skip straight to splitting.

The splitter that follows keeps chunks bounded and adds **overlap** — repeating a tail of each chunk at the head of the next so a sentence cut across a boundary still appears whole in one chunk:

```python
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """Split text into overlapping character windows.

    chunk_size caps how much text an embedding must summarize into one
    vector; overlap repeats a tail of each chunk at the start of the next
    so an idea split across a boundary still lands whole in one chunk.
    """
    text = " ".join(text.split())          # collapse whitespace
    if len(text) <= chunk_size:
        return [text]

    chunks, start = [], 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap              # step back by overlap
    return chunks
```

This character splitter is deliberately simple so you can see the mechanism. In practice LangChain's `RecursiveCharacterTextSplitter` is the workhorse: it tries to break on paragraph, then sentence, then word boundaries before falling back to a hard cut, so chunks stay readable.

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
chunks = splitter.split_text(document_text)
```

With chunks in hand, embed them with the exact `Embeddings` class from post 4 and keep each chunk's text next to its vector so you can quote it later:

```python
import os
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Embeddings

EMBED_MODEL_ID = "ibm/slate-125m-english-rtrvr"   # verify in the docs

credentials = Credentials(
    url=os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
    api_key=os.environ["WATSONX_APIKEY"],
)
project_id = os.environ["WATSONX_PROJECT_ID"]

embedder = Embeddings(
    model_id=EMBED_MODEL_ID, credentials=credentials, project_id=project_id
)

def build_index(chunks: list[str], sources: list[str]):
    """Embed chunks once. Returns parallel arrays of vectors + metadata."""
    import numpy as np
    vectors = embedder.embed_documents(texts=chunks)         # list[list[float]]
    return {
        "matrix": np.asarray(vectors, dtype=np.float32),
        "texts": chunks,
        "sources": sources,          # e.g. "handbook.pdf#p12" per chunk
    }
```

**The gotcha:** embed the corpus with `embed_documents` and *only* the query with `embed_query` (post 4). Slate retriever models can encode the corpus side and the query side asymmetrically for better matching, so running your whole corpus through `embed_query` in a loop — or wrapping one question in a list to call `embed_documents` — silently degrades retrieval. Same model on both sides, matching method per role.

---

## Stage 2: Retrieve — the query finds its neighbors

Retrieval embeds the incoming question with `embed_query` and finds the chunks whose vectors point in the most similar direction. This is the same normalized-dot-product cosine from post 4, returning indices so we can carry each chunk's source metadata through:

```python
import numpy as np

def cosine_shortlist(query_vec, matrix, n: int):
    """Return indices of the top-n chunks by cosine similarity."""
    q = np.asarray(query_vec, dtype=np.float32)
    q /= np.linalg.norm(q) + 1e-10
    m = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
    scores = m @ q
    return np.argsort(scores)[::-1][:n]        # highest score first

def retrieve_candidates(index, query: str, recall_n: int = 25):
    query_vec = embedder.embed_query(text=query)
    idx = cosine_shortlist(query_vec, index["matrix"], recall_n)
    return [(index["texts"][i], index["sources"][i]) for i in idx]
```

Cosine recall is fast and approximate — each chunk was compressed to one vector *before* the query existed, so it is cheap to search but blurry. Over-retrieve *modestly* here: pull a few dozen candidates, not five and not five hundred. Those few dozen are the input to the stage that actually gets the order right.

---

## Stage 3: Rerank — precision where it matters

A reranker looks at the **query and one candidate together** and scores how well that passage answers that question — a far more precise judgment than comparing two pre-computed vectors, and far more expensive, which is exactly why you run it over the shortlist and not the whole corpus. This is the `Rerank` class from post 4. As that post stressed, the *exact* method name and response field names are things to confirm against the SDK reranking docs for your installed version — write against the request/response *contract* (query in, candidate passages in, a relevance-ordered result with per-candidate scores and original indices out) and read the precise keys from the docs.

```python
from ibm_watsonx_ai.foundation_models import Rerank

RERANK_MODEL_ID = "cross-encoder/ms-marco-minilm-l-12-v2"   # verify in the docs

reranker = Rerank(
    model_id=RERANK_MODEL_ID, credentials=credentials, project_id=project_id
)

def rerank_top_k(query: str, candidates: list[tuple[str, str]], k: int = 4):
    """Reorder (text, source) candidates by joint relevance, keep top k.

    Field names below (results / score / index) follow the shape post 4
    used — confirm them against the reranking docs and adjust the parse.
    """
    texts = [text for text, _ in candidates]
    response = reranker.rerank(query=query, inputs=texts)
    results = response["results"] if isinstance(response, dict) else response
    ranked = sorted(results, key=lambda r: r["score"], reverse=True)
    return [candidates[r["index"]] for r in ranked[:k]]
```

**The gotcha:** reranking is where most of RAG's answer quality comes from — do not skip it. A large share of "the model ignored my documents" and "it hallucinated" complaints are really *retrieval* failures: cosine ranked a keyword-y near-miss above the passage that actually held the answer, so the answer never reached the prompt. Adding a reranker over a modest shortlist is usually the single highest-leverage fix for a mediocre RAG system, and it is a few lines, not a model swap.

---

## Stage 4: Augment and generate — a grounded, cited answer

Now the top-k chunks become **context** in a prompt, and a Granite model answers from that context. This is `ModelInference.chat` from post 2. Two things make or break this stage: the context is clearly delimited and tagged with source labels so the model can cite them, and the system message *forbids* answering from anything but the supplied context.

```python
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

chat_model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",   # verify a live id for your region
    credentials=credentials,
    project_id=project_id,
)

SYSTEM_PROMPT = (
    "You are a question-answering assistant. Answer ONLY using the numbered "
    "context passages provided. Cite the passages you use by their [n] label. "
    "If the context does not contain the answer, reply exactly: "
    "\"I don't know based on the provided documents.\" Do not use outside knowledge."
)

def build_context(top_chunks: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Render numbered, source-labelled context and return the citation list."""
    blocks, citations = [], []
    for n, (text, source) in enumerate(top_chunks, start=1):
        blocks.append(f"[{n}] (source: {source})\n{text}")
        citations.append(f"[{n}] {source}")
    return "\n\n".join(blocks), citations

def generate_answer(query: str, top_chunks: list[tuple[str, str]]):
    context, citations = build_context(top_chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",
         "content": f"Context:\n{context}\n\nQuestion: {query}"},
    ]
    params = TextChatParameters(max_tokens=400, temperature=0.0)
    response = chat_model.chat(messages=messages, params=params)
    answer = response["choices"][0]["message"]["content"]
    return answer, citations
```

Note `temperature=0.0`: a grounded answer should be reproducible and faithful to the context, not creative. The response shape is the same `choices[0].message.content` from post 2, and `response["usage"]` still carries the token counts if you want to track cost.

**The gotcha:** you must *instruct* the model to ground itself and to say "I don't know" when the context is silent — otherwise it happily fills gaps from parametric memory, and a confident answer sourced from training data instead of your documents is exactly the failure RAG was meant to prevent. The `[n]` labels in the context plus a system rule to cite them give you traceable answers; without the "I don't know" escape hatch, the model has no permitted way to admit the retrieval missed.

---

## The whole pipeline, end to end

The four stages compose into one function. Ingest runs once (offline, ideally); retrieve, rerank, and generate run per query.

```python
def rag_answer(index, query: str, recall_n: int = 25, final_k: int = 4):
    candidates = retrieve_candidates(index, query, recall_n=recall_n)
    top_chunks = rerank_top_k(query, candidates, k=final_k)
    return generate_answer(query, top_chunks)

if __name__ == "__main__":
    docs = {
        "watsonx-overview.md": (
            "watsonx.ai runs foundation models for inference, tuning, and "
            "deployment. watsonx.governance tracks model drift, quality "
            "metrics, and factsheets. watsonx.data is an open lakehouse for "
            "the documents you retrieve over."
        ),
        "granite.md": "IBM Granite models ship under a permissive open license.",
    }
    chunks, sources = [], []
    for name, text in docs.items():
        for i, ch in enumerate(chunk_text(text, chunk_size=200, overlap=40)):
            chunks.append(ch)
            sources.append(f"{name}#chunk{i}")

    index = build_index(chunks, sources)
    answer, citations = rag_answer(index, "Which product watches models for drift?")
    print(answer)
    print("\nSources:")
    for c in citations:
        print(" ", c)
```

That is a complete RAG system in one file: chunk, embed, store, retrieve, rerank, generate, cite. The numbers to tune are `recall_n` (how many the embeddings hand the reranker) and `final_k` (how many reach the model) — the main dial on the recall-versus-cost trade-off from post 4.

---

## The idiomatic langchain-ibm assembly

If your app already lives in LangChain, the same four stages assemble from off-the-shelf components: `WatsonxEmbeddings` and `WatsonxRerank` (post 4) plus `ChatWatsonx` (post 2), wired through a vector store and a compression retriever. The exact chain-construction helpers evolve with LangChain's own conventions, so treat the wiring below as the accurate *shape* and confirm the current constructor and chain APIs in the langchain-ibm and LangChain docs.

```python
import os
from langchain_ibm import WatsonxEmbeddings, WatsonxRerank, ChatWatsonx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.retrievers import ContextualCompressionRetriever

url = os.environ["WATSONX_URL"]
project_id = os.environ["WATSONX_PROJECT_ID"]

embeddings = WatsonxEmbeddings(
    model_id="ibm/slate-125m-english-rtrvr", url=url, project_id=project_id,
)
reranker = WatsonxRerank(
    model_id="cross-encoder/ms-marco-minilm-l-12-v2", url=url, project_id=project_id,
)
llm = ChatWatsonx(
    model_id="ibm/granite-3-8b-instruct", url=url, project_id=project_id,
    apikey=os.environ["WATSONX_APIKEY"],
)

# Ingest: split, embed, and store in a vector index.
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
docs = splitter.create_documents([document_text])
vector_store = FAISS.from_documents(docs, embeddings)

# Retrieve + rerank as one call: the compression retriever pulls a wide
# cosine shortlist, then WatsonxRerank compresses it to the best few.
base_retriever = vector_store.as_retriever(search_kwargs={"k": 25})
retriever = ContextualCompressionRetriever(
    base_compressor=reranker, base_retriever=base_retriever,
)
```

`WatsonxEmbeddings` is a drop-in backend for any LangChain vector store; `WatsonxRerank` is a *document compressor* that plugs into a `ContextualCompressionRetriever` wrapping your base retriever, so retrieve-then-rerank happens in one retriever call. From there you feed the retrieved documents and your grounding prompt into `ChatWatsonx` — the same model as the native path, wrapped for LangChain's interface. The engine is identical to the from-scratch pipeline; LangChain just supplies the plumbing.

---

## Storage: in-memory to learn, a vector DB to ship

Everything above kept vectors in a numpy array. That is the right way to *learn* the pipeline — you can see every step — and it is fine for a few thousand chunks. It does not survive a restart, it holds everything in RAM, and a full-scan cosine over millions of vectors is too slow for interactive use.

Production moves the vectors into a **vector database** that persists them and does approximate nearest-neighbor search in sublinear time. Named accurately, without inventing APIs: on the IBM stack, **watsonx.data** integrates the **Milvus** vector engine, so your retrieval store lives alongside the lakehouse your documents came from; standalone, **Milvus** runs on its own, and **Chroma** and **FAISS** are common lighter-weight options (FAISS is an in-process index library; Chroma is an embeddable store). LangChain has integrations for all of them, so the `FAISS.from_documents(...)` line above becomes a `Milvus` or `Chroma` constructor with the same downstream retriever code.

**The gotcha:** the in-memory numpy index is a teaching tool, not a deployment target — move to a vector DB for anything real. But do not over-rebuild when you do: the pipeline *shape* is invariant. Ingest → embed → store, then retrieve → rerank → generate is identical whether the store is a numpy array, FAISS, Chroma, or Milvus inside watsonx.data. You are swapping the index, not redesigning the system, and the embedding model, reranker, and grounding prompt do not change at all.

---

## Native vs. langchain-ibm at a glance

| Stage | From scratch (`ibm-watsonx-ai`) | langchain-ibm |
|---|---|---|
| Chunk | your splitter / `RecursiveCharacterTextSplitter` | `RecursiveCharacterTextSplitter` |
| Embed | `Embeddings.embed_documents` / `embed_query` | `WatsonxEmbeddings` |
| Store | numpy array → vector DB | vector store (FAISS / Chroma / Milvus) |
| Retrieve | cosine over the matrix | `vector_store.as_retriever(...)` |
| Rerank | `Rerank.rerank` | `WatsonxRerank` in `ContextualCompressionRetriever` |
| Generate | `ModelInference.chat` | `ChatWatsonx` |

---

## Key takeaways

- **RAG is four stages: ingest, retrieve, rerank, generate.** Each is concrete watsonx.ai Python, and the shape never changes regardless of scale or framework.
- **Chunk with overlap, parse cleanly.** Bounded overlapping chunks keep one idea per vector; use Docling to turn PDFs and office files into clean text, and `RecursiveCharacterTextSplitter` to split it.
- **Embed the corpus and the query with their matching methods** — `embed_documents` vs. `embed_query`, same model both sides — or retrieval silently degrades.
- **Rerank; do not skip it.** Cosine recall is blurry, and reranking a modest shortlist is where most RAG answer quality comes from — the highest-leverage fix for weak results.
- **Ground the generation and allow "I don't know."** Delimit and label the context, instruct the model to answer only from it and cite `[n]` sources; without that it hallucinates from parametric memory.
- **In-memory to learn, a vector DB to ship.** Move to Milvus (standalone or in watsonx.data), Chroma, or FAISS for production — the retrieve → rerank → generate shape is identical; you swap the index, not the design.
- **langchain-ibm assembles the same pipeline** from `WatsonxEmbeddings`, `WatsonxRerank`, and `ChatWatsonx` when watsonx.ai is one component of a larger LangChain app.

---

## Further reading

- [`ibm-watsonx-ai` SDK — Embeddings](https://ibm.github.io/watsonx-ai-python-sdk/fm_embeddings.html)
- [`ibm-watsonx-ai` SDK — Rerank / reranking](https://ibm.github.io/watsonx-ai-python-sdk/fm_rerank.html)
- [`ibm-watsonx-ai` SDK — ModelInference (chat)](https://ibm.github.io/watsonx-ai-python-sdk/fm_model_inference.html)
- [Docling — document parsing for RAG](https://github.com/docling-project/docling)
- [LangChain — RecursiveCharacterTextSplitter](https://python.langchain.com/docs/how_to/recursive_text_splitter/)
- [`langchain-ibm` — ChatWatsonx](https://python.langchain.com/docs/integrations/chat/ibm_watsonx/)
- [`langchain-ibm` — WatsonxRerank](https://python.langchain.com/docs/integrations/document_transformers/ibm_watsonx_ranker/)
- [IBM watsonx.data — Milvus vector database](https://www.ibm.com/docs/en/watsonx/watsonxdata/2.1.x?topic=components-milvus)
- [Milvus vector database documentation](https://milvus.io/docs)
