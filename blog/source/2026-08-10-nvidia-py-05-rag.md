# RAG on the NVIDIA Stack

*Assembling a full retrieval-augmented generation pipeline in Python — chunk and embed with NeMo Retriever, shortlist by cosine, sharpen with a reranker, then ground a ChatNVIDIA answer that cites its sources — first from scratch, then the idiomatic LangChain wiring.*

---

The last two posts built the halves of a RAG system without ever bolting them together. Post 2 showed how to call a NIM — the plain `openai` client pointed at NVIDIA's endpoint, or the LangChain-native `ChatNVIDIA` chat model. Post 4 built the retrieval core — `NVIDIAEmbeddings` to turn text into vectors, cosine similarity to shortlist, and `NVIDIARerank` to sharpen that shortlist with a cross-encoder. This post connects the two into the thing you actually ship: a pipeline that takes a question, finds the right passages in *your* documents, and hands a NIM a grounded prompt so the answer comes from your corpus instead of the model's memory.

The shape never changes, no matter how large the system gets:

1. **Ingest** — split documents into chunks, embed the chunks, store the vectors.
2. **Retrieve** — embed the question, pull a shortlist of nearby chunks.
3. **Rerank** — reorder the shortlist with a cross-encoder, keep the best few.
4. **Augment + generate** — build a grounded prompt from those chunks and call the LLM, forcing it to answer only from what you gave it and to cite sources.

We build the whole thing twice. First from scratch with NumPy and the NIM clients, so nothing is hidden. Then the idiomatic LangChain assembly, because `langchain-nvidia-ai-endpoints` was designed to make this a handful of lines. Every library and method below is real; model ids are examples to confirm in the live catalog at [build.nvidia.com](https://build.nvidia.com).

```bash
pip install langchain-nvidia-ai-endpoints langchain langchain-community numpy
export NVIDIA_API_KEY="nvapi-..."   # from build.nvidia.com
```

---

## Step 1 — Ingest: chunk, embed, store

A document is too big to embed as one vector — a 10-page PDF crushed into a single 1024-dimensional vector loses all the local detail retrieval depends on. So you **chunk**: split each document into passages of a few hundred tokens, embed each one, and store the vectors. Chunk size is a genuine tradeoff. Too large and a chunk mixes several topics, so its vector is a muddy average that matches nothing sharply. Too small and a chunk loses the context that makes it meaningful. A few hundred characters with a small **overlap** between neighbors is a sane default; the overlap keeps a sentence that straddles a boundary from being orphaned.

Here is a minimal splitter that respects paragraph boundaries where it can and carries an overlap forward:

```python
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph breaks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            # Start the next chunk with the tail of the last one (the overlap).
            tail = current[-overlap:] if current else ""
            current = f"{tail}\n\n{para}" if tail else para
    if current:
        chunks.append(current)
    return chunks
```

This is deliberately simple so you can see the mechanics. In production, reach for LangChain's `RecursiveCharacterTextSplitter`, which does the same thing more carefully — it tries a prioritized list of separators (`"\n\n"`, then `"\n"`, then `" "`, then character-level) so it splits on the largest natural boundary that keeps a chunk under the limit:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
chunks = splitter.split_text(long_document)          # -> list[str]
# or, keeping metadata: splitter.create_documents([long_document], metadatas=[{"source": "handbook.md"}])
```

With chunks in hand, embedding is exactly the recall side from post 4. Every chunk goes through `embed_documents` — the *passage* role — and the returned vectors become your index. Keep the chunk text and its source alongside the vector so you can show the passage and cite it later.

```python
import numpy as np
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"   # confirm in the catalog

embedder = NVIDIAEmbeddings(model=EMBED_MODEL)

def build_index(chunks: list[dict]) -> np.ndarray:
    """chunks: list of {'text': str, 'source': str}. Returns a matrix of vectors."""
    vectors = embedder.embed_documents([c["text"] for c in chunks])  # passage role
    return np.asarray(vectors, dtype=np.float32)
```

**The gotcha:** embed the corpus with `embed_documents` and *only* the corpus. The query gets `embed_query` in the next step, and the two are not interchangeable — post 4 covered why. A retrieval embedding model is asymmetric: it tags passages and questions with different roles so a terse question lands near the fuller passage that answers it. Route your chunks through `embed_query` by accident and every call still succeeds, still returns same-length vectors, still produces plausible scores — but retrieval quality quietly degrades with no exception and no warning. Corpus through `embed_documents`, live queries through `embed_query`. Always.

---

## Step 2 — Retrieve: embed the query, shortlist by cosine

At query time you embed the question with `embed_query` and score it against every stored vector. "Most relevant" is "nearest neighbor," and for text embeddings the standard measure is **cosine similarity** — the cosine of the angle between two vectors, which ignores magnitude so a long passage isn't penalized for length. Normalize both sides to unit length and the cosine is just a dot product.

```python
def cosine_scores(query_vec, doc_matrix) -> np.ndarray:
    q = np.asarray(query_vec, dtype=np.float32)
    m = np.asarray(doc_matrix, dtype=np.float32)
    q = q / (np.linalg.norm(q) + 1e-12)
    m = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-12)  # new array — don't mutate the caller's index
    return m @ q   # shape: (num_chunks,)

def shortlist(query: str, chunks, index, k: int = 20) -> list[dict]:
    q_vec = embedder.embed_query(query)          # query role — NOT embed_documents
    scores = cosine_scores(q_vec, index)
    top = np.argsort(scores)[::-1][:k]
    return [chunks[i] for i in top]
```

The `1e-12` guards a degenerate zero vector against divide-by-zero. Looping over every vector with NumPy is fine for a few thousand chunks and easy to reason about; past that you want a vector database doing approximate nearest-neighbor search in sub-linear time (more on that below). The math is identical either way — only the data structure under it changes.

**The gotcha:** the corpus and the query must go through the **same** embedding model. Vectors from `nv-embedqa-e5-v5` and vectors from any other model don't share a coordinate system, so comparing across them yields numbers that mean nothing. This also bites on upgrades: the day you switch embedding models, every stored vector is stale and the whole corpus must be re-embedded before it can be compared against new queries. Version your index by the model that produced it.

---

## Step 3 — Rerank: precision after recall

Embedding search is fast because it's decoupled — each chunk was compressed into a vector *before* it knew what anyone would ask. That gives good recall (the right chunk is probably somewhere in the top 20) but mediocre precision at the very top (it might be ranked 11th, not 1st). A **reranker** fixes the top. It's a cross-encoder: it feeds the query and one candidate through the model *together* and emits a single relevance score, so the two texts attend to each other instead of being judged as independent vectors. It's far more precise — and not precomputable, so you run it only on the shortlist.

`NVIDIARerank.compress_documents(documents, query)` takes LangChain `Document` objects plus the query and returns them reordered, most relevant first, capped at `top_n`:

```python
from langchain_nvidia_ai_endpoints import NVIDIARerank
from langchain_core.documents import Document

RERANK_MODEL = "nvidia/nv-rerankqa-mistral-4b-v3"   # confirm in the catalog
reranker = NVIDIARerank(model=RERANK_MODEL, top_n=4)

def rerank(query: str, candidates: list[dict]) -> list[Document]:
    docs = [Document(page_content=c["text"], metadata={"source": c["source"]})
            for c in candidates]
    return reranker.compress_documents(documents=docs, query=query)
```

Each returned `Document` carries a `relevance_score` in its `metadata`, and the source we attached survives the round trip — which is what lets the final answer cite where each fact came from.

**The gotcha:** reranking is where most of RAG's quality comes from — don't skip it. When answers come back subtly off-topic, the reflex is to tweak the prompt or swap the generation model, but if stage one handed the LLM the 11th-best chunk instead of the 1st, the generator was doomed before it saw a token. Reranking is the cheapest, highest-leverage quality win in most RAG systems because it fixes the input the LLM never gets to see you got wrong. And keep the shortlist modest — the reranker runs a forward pass per candidate, so pulling 500 chunks "to be safe" turns one cheap lookup into 500 cross-encoder passes per query. Over-retrieve in the tens, then rerank down to a handful.

---

## Step 4 — Augment + generate: a grounded, cited answer

Now the reranked top-k becomes context. You build a prompt that (a) lays out the passages with numbered source labels, (b) instructs the model to answer *only* from those passages, and (c) tells it to cite the labels it used and to say it doesn't know when the context doesn't cover the question. Then you call `ChatNVIDIA` — the same chat model from post 2.

```python
from langchain_nvidia_ai_endpoints import ChatNVIDIA

CHAT_MODEL = "meta/llama-3.1-8b-instruct"   # confirm in the catalog
llm = ChatNVIDIA(model=CHAT_MODEL, temperature=0.1, max_tokens=512)

SYSTEM = (
    "You are a careful assistant. Answer the question using ONLY the numbered "
    "context passages below. If the context does not contain the answer, reply "
    'exactly: "I don\'t know based on the provided context." '
    "Cite the passages you use with their bracketed numbers, e.g. [1], [2]."
)

def build_prompt(query: str, docs: list[Document]) -> tuple[str, list[str]]:
    blocks, sources = [], []
    for i, doc in enumerate(docs, 1):
        src = doc.metadata.get("source", "unknown")
        sources.append(src)
        blocks.append(f"[{i}] (source: {src})\n{doc.page_content}")
    context = "\n\n".join(blocks)
    user = f"Context:\n{context}\n\nQuestion: {query}"
    return user, sources

def generate(query: str, docs: list[Document]) -> dict:
    user, sources = build_prompt(query, docs)
    answer = llm.invoke([("system", SYSTEM), ("human", user)]).content
    return {"answer": answer, "citations": list(dict.fromkeys(sources))}
```

Low `temperature` keeps a grounded answer from drifting into invention. Numbering the passages gives the model something concrete to cite, and returning the deduplicated `sources` list (order-preserving via `dict.fromkeys`) gives your UI the citations to render. Because `ChatNVIDIA` is a standard LangChain chat model, you could swap in the plain `openai` client from post 2 here without changing the pipeline's shape — same messages, same grounded prompt.

**The gotcha:** the grounding instruction is not optional. Without an explicit "answer only from the context, and say you don't know otherwise," the model falls back on its parametric memory the moment the retrieved passages are thin — and it does so *fluently*, producing a confident answer that isn't in your documents at all. That's the worst failure mode in RAG, because it looks exactly like a correct answer. Pin the model to the context and give it a sanctioned way to decline. A RAG system that occasionally says "I don't know" is working; one that never does is hallucinating.

---

## The whole from-scratch pipeline

Put the four steps together and the entire loop is small enough to read at a glance:

```python
def rag(query: str, chunks, index, k_shortlist=20, k_final=4) -> dict:
    candidates = shortlist(query, chunks, index, k=k_shortlist)  # recall
    top = rerank(query, candidates)[:k_final]                    # precision
    return generate(query, top)                                  # grounded answer

if __name__ == "__main__":
    raw_docs = [
        {"source": "nim.md", "text": "NVIDIA NIM packages a model behind an "
         "OpenAI-compatible HTTP API, so existing clients work unchanged."},
        {"source": "retriever.md", "text": "NeMo Retriever provides embedding and "
         "reranking models as NIMs for building RAG pipelines."},
        {"source": "rerank.md", "text": "A cross-encoder reranker scores a query "
         "and a passage together in one forward pass for high precision."},
    ]
    # In a real ingest you would chunk_text() each source document first.
    chunks = raw_docs
    index = build_index(chunks)

    result = rag("How does NIM expose its models?", chunks, index)
    print(result["answer"])
    print("Sources:", result["citations"])
```

That is a complete RAG system: ingest, retrieve, rerank, generate — all on the NVIDIA stack, all with real APIs.

---

## The idiomatic LangChain assembly

The from-scratch version is worth keeping in your head, but `langchain-nvidia-ai-endpoints` is built to make this terser. Two integrations do most of the plumbing.

First, a **vector store** replaces the hand-rolled NumPy index and gives you a `retriever` — an object that turns a query string into a list of `Document`s. FAISS is the usual in-memory choice, and `NVIDIAEmbeddings` plugs straight in:

```python
from langchain_community.vectorstores import FAISS

store = FAISS.from_texts(
    texts=[c["text"] for c in chunks],
    embedding=embedder,                       # NVIDIAEmbeddings: uses embed_documents
    metadatas=[{"source": c["source"]} for c in chunks],
)
base_retriever = store.as_retriever(search_kwargs={"k": 20})
```

`FAISS.from_texts` calls `embed_documents` for you, and the resulting retriever calls `embed_query` at search time — the passage/query split from post 4 is handled correctly without you touching either method.

Second, `NVIDIARerank` is a LangChain *document compressor*, so it drops into a `ContextualCompressionRetriever`. That wrapper retrieves with the base retriever, then runs the compressor (the reranker) over the results — fusing steps 2 and 3 into a single retriever object:

```python
from langchain.retrievers import ContextualCompressionRetriever

compression_retriever = ContextualCompressionRetriever(
    base_compressor=reranker,          # NVIDIARerank(top_n=4)
    base_retriever=base_retriever,     # FAISS top-20
)
# .invoke(query) -> reranked top-4 Documents, each with relevance_score + source metadata
```

For the generation step, LangChain ships helpers that stuff retrieved documents into a prompt and wire a retriever to an LLM: `create_stuff_documents_chain(llm, prompt)` builds the "fill `{context}`, answer `{input}`" node, and `create_retrieval_chain(retriever, doc_chain)` runs retrieval first and feeds the result in. Confirm the exact import paths and the `{context}` / `{input}` placeholder names against the version you install — these helpers have moved between LangChain releases — but the composition is the point:

```python
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "Context:\n{context}\n\nQuestion: {input}"),
])
doc_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(compression_retriever, doc_chain)

out = rag_chain.invoke({"input": "How does NIM expose its models?"})
print(out["answer"])
for doc in out["context"]:                      # the reranked passages that grounded it
    print("cited:", doc.metadata.get("source"))
```

`create_retrieval_chain` returns a dict with the generated `answer` and the `context` documents that produced it, so you get the same answer-plus-citations you built by hand — with the retrieve→rerank→generate wiring collapsed into three composable objects. Same pipeline, less glue.

---

## Storage at scale: past the in-memory index

The NumPy matrix and FAISS-in-memory are teaching and prototyping tools. They're genuinely fine for thousands to low-hundreds-of-thousands of chunks. Past that — or the moment you need the index to survive a restart, be shared across processes, or filter by metadata — you move to a real vector database. The important part is that **the retrieve→rerank→generate shape does not change**; only the store behind the retriever does.

- **FAISS** (`langchain_community.vectorstores.FAISS`) — fast, local, and it persists: `store.save_local(path)` and `FAISS.load_local(path, embedder)`. A great next step up from raw NumPy.
- **Milvus** — a full vector database that scales to billions of vectors and offers a **GPU index** for high-throughput search on NVIDIA hardware; LangChain integrates it as a vector store.
- **NVIDIA cuVS** — NVIDIA's CUDA library for GPU-accelerated vector search (the successor to RAFT's ANN work), which several vector databases build on under the hood to move the nearest-neighbor step onto the GPU.

NVIDIA also publishes **RAG blueprints** — reference architectures (part of NVIDIA AI Blueprints, built on NeMo Retriever NIMs) that wire ingestion, embedding, reranking, and generation into a deployable service. They're a useful map for what a production pipeline contains; the four steps in this post are exactly the stages they formalize.

**The gotcha:** don't mistake the storage choice for the architecture. In-memory NumPy, FAISS, and a GPU-backed Milvus cluster all sit behind the same retriever interface, and the reranker and generator above them don't know or care which one answered. Prototype on the simplest store that fits, prove the pipeline's *quality* first (is the gold passage in your reranked top-k?), and swap in the scalable store when data volume — not architecture — forces it. Migrating the store is a config change; the retrieve→rerank→generate shape is identical.

---

## Key takeaways

- **RAG is four steps, always the same shape.** Ingest (chunk, embed, store) → retrieve (embed query, shortlist) → rerank → augment + generate. Everything else is a scaling detail.
- **Chunk with overlap.** A few hundred characters with a small overlap keeps passages topically tight without orphaning boundary-straddling sentences; `RecursiveCharacterTextSplitter` does this well.
- **`embed_documents` for the corpus, `embed_query` for the question.** Mixing them silently degrades retrieval — no error, just worse answers. Same embedding model on both sides, always.
- **Reranking is the highest-leverage quality win.** Embeddings give recall, the cross-encoder gives precision. `compress_documents` sharpens a modest shortlist; over-retrieve in the tens, not hundreds.
- **Ground the generator or it hallucinates.** Instruct the model to answer only from the context and to say "I don't know" — otherwise it fills gaps from parametric memory, fluently and wrongly.
- **`langchain-nvidia-ai-endpoints` collapses the plumbing.** A FAISS retriever plus `ContextualCompressionRetriever` with `NVIDIARerank`, fed into a retrieval chain, is the same pipeline in a fraction of the code.
- **Storage scales independently of shape.** In-memory is for learning; FAISS, Milvus (GPU index), and cuVS scale it. The retrieve→rerank→generate architecture never changes.

---

## Further reading

- [NeMo Retriever documentation](https://docs.nvidia.com/nemo/retriever/) — the embedding and reranking NIMs that power ingestion and retrieval.
- [`langchain-nvidia-ai-endpoints` — reranking](https://python.langchain.com/docs/integrations/retrievers/nvidia_rerank/) — `NVIDIARerank`, `compress_documents`, and `ContextualCompressionRetriever` usage.
- [`langchain-nvidia-ai-endpoints` — text embeddings](https://python.langchain.com/docs/integrations/text_embedding/nvidia_ai_endpoints/) — `NVIDIAEmbeddings`, `embed_documents`, and `embed_query`.
- [NVIDIA AI Blueprints — RAG](https://build.nvidia.com/nvidia/build-an-enterprise-rag-pipeline) — the reference RAG pipeline built on NeMo Retriever NIMs.
- [FAISS documentation](https://faiss.ai/) — the in-memory / on-disk vector index used above.
- [Milvus documentation](https://milvus.io/docs) — a production vector database with GPU-accelerated indexing.
- [NVIDIA cuVS](https://docs.rapids.ai/api/cuvs/stable/) — GPU-accelerated vector search primitives.
