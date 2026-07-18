# File Search

*Ground an agent's answers in documents you upload — the provider indexes them into a vector store and searches server-side, no retrieval code of your own.*

---

## What this lesson demonstrates

File search is a *hosted* tool. Rather than writing a Python function that reads and chunks documents, you upload files, create a vector store, index the files into it, and hand the agent a file-search tool bound to that store's id. When the model decides it needs the documents, Foundry runs retrieval server-side and grounds the reply. Here a one-line weather note is uploaded, indexed, and queried — the answer comes from the file, not the model's own knowledge.

## The code

The tool is built from the client and pointed at a staged vector store:

```python
async def create_vector_store(client: FoundryChatClient) -> tuple[str, str]:
    file = await client.client.files.create(
        file=("todays_weather.txt", b"The weather today is sunny with a high of 75F."),
        purpose="assistants",
    )
    vector_store = await client.client.vector_stores.create(
        name="knowledge_base",
        expires_after={"anchor": "last_active_at", "days": 1},
    )
    result = await client.client.vector_stores.files.create_and_poll(
        vector_store_id=vector_store.id, file_id=file.id
    )
    if result.last_error is not None:
        raise RuntimeError(f"indexing failed: {result.last_error.message}")
    return file.id, vector_store.id
```

The agent is then wired with `tools=[client.get_file_search_tool(vector_store_ids=[vector_store_id])]`.

## What to notice

- **The tool comes from the client, not a `@tool` function.** `client.get_file_search_tool(vector_store_ids=[...])` produces a hosted tool; there is no local retrieval callback to implement.
- **File and vector-store ops go through the raw SDK handle** `client.client` — `files.create`, `vector_stores.create`, `vector_stores.files.create_and_poll`.
- **`create_and_poll` blocks until indexing finishes.** Check `result.last_error` before running the agent, or the store may be empty when the model searches.

## The gotcha

Vector stores are billable, provider-specific resources. On Foundry you upload with `purpose="assistants"` (OpenAI's sample uses `"user_data"`). Delete the store and file when done; the `expires_after` anchor of `last_active_at` with `days: 1` is a backstop, not a substitute for cleanup.

## How it maps to MAF and Foundry

This is the same retrieval-augmented pattern as the RAG lesson, but the framework and Foundry own the index. You stage documents once; the model, at its discretion, issues a search against the store id and receives grounded context. Your code never touches embeddings or similarity — MAF exposes the hosted tool and Foundry does the work.

## Run it

```bash
uv run tutorial/02-agents/tools/05_file_search.py
```

Needs Foundry credentials (`AzureCliCredential`, so `az login` first) plus `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_MODEL`. Success looks like an answer about today's weather drawn from the uploaded file.

---

Next: [Web Search](/blog/posts/maf-py-42-web-search.html)
