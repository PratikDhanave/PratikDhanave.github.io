# Web Search

*Let an agent reach live search results for anything past its training cutoff — Foundry runs the search and grounding server-side, and returns URL citations.*

---

## What this lesson demonstrates

The hosted web search tool lets an agent answer questions about current events and other information the model was never trained on. You attach the tool; Foundry performs the search and grounds the answer for you. There is no local function to register and no callback to implement. The reply comes back with URL citations attached, which this lesson walks and prints as a `Sources:` list.

## The code

The tool is a classmethod on the client, attached like any other:

```python
def build_agent() -> Agent:
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["FOUNDRY_MODEL"],
        credential=AzureCliCredential(),
    )
    web_search_tool = FoundryChatClient.get_web_search_tool()
    return Agent(
        client=client,
        name="web-researcher",
        instructions="Use web search to find current, factual information and cite your sources.",
        tools=[web_search_tool],
    )
```

## What to notice

- **`get_web_search_tool()` is a classmethod.** No local search function exists — the whole search runs on the provider side.
- **Citations arrive as annotations.** Iterate `result.messages -> message.contents -> content.annotations` and read `annotation.url` / `annotation.title`. Grounded answers carry their sources so you can display or verify them.
- **Availability is provider-gated.** Because it is a server-side tool, a Foundry project must have the capability enabled.

## The gotcha

If your Foundry project does not have the generic web search tool provisioned, `get_web_search_tool()` won't work — switch to Bing grounding. That path needs a Bing connection whose id you resolve from the project, then `FoundryChatClient.get_bing_grounding_tool(connection_id=..., market="en-US", freshness="Day")`, passed via `tools=[...]` exactly as above.

## How it maps to MAF and Foundry

The MAF web-search doc shows OpenAI's `client.get_web_search_tool()`; the Foundry provider exposes the same feature as the `FoundryChatClient.get_web_search_tool()` classmethod. Either way the tool is hosted: the model requests a search, the provider executes it, grounds the response, and returns annotated citations. Your process only reads results — it never issues an HTTP request itself.

## Run it

```bash
uv run tutorial/02-agents/tools/06_web_search.py
```

Needs Foundry credentials (`az login`, `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`). Success is a factual answer followed by a `Sources:` list of URL citations.

---

Next: [Hosted Mcp](/blog/posts/maf-py-43-hosted-mcp.html)
