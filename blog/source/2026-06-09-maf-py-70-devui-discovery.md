# Devui Discovery

*Serving a whole directory of agents at once by exporting a module-level agent variable.*

---

## What it demonstrates

DevUI can auto-discover agents and workflows laid out on disk and serve them all with one command. Discovery is directory-driven: each entity lives in its own folder whose `__init__.py` exports a module-level variable named literally `agent` (or `workflow`). Point the `devui` CLI at the parent folder and it finds every entity. This lesson scaffolds a discoverable `entities/` tree at runtime — one package per Foundry agent — prints the layout, and launches `devui ./entities`.

## One real excerpt

```python
# The only hard requirement for discovery: a module-level `agent` export in __init__.py.
ENTITY_TEMPLATE = '''\
agent = Agent(
    client=FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["FOUNDRY_MODEL"],
        credential=AzureCliCredential(),
    ),
    name="{name}",
    tools=[get_weather],
    instructions="{instructions}",
)
'''
# Then: devui ./entities --port 9000 --reload   → discovers weather_agent, concierge_agent
```

## The gotcha

The `__init__.py` must export a variable *literally* named `agent` or `workflow` — the folder name becomes the entity name, but the variable name is what discovery keys on. Implementation can live in `agent.py`/`workflow.py`, but the folder's `__init__.py` has to re-export the symbol. The entity dir must sit DIRECTLY under the path passed to `devui`; nesting deeper hides it. A parent-level `.env` loads for all entities, an entity-level `.env` for that one only. With no entities discovered, DevUI shows a curated sample gallery instead.

## Azure / MAF mapping

Every scaffolded entity is a plain `Agent` over `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`), and the `.env.example` documents exactly those Foundry vars. Discovery is pure packaging convention — DevUI reads the exported `agent` and serves the same Foundry-backed agents you'd build by hand.

## Run it

`uv run tutorial/04-hosting/06_devui_discovery.py` — runs partly offline (scaffolding), needs Foundry creds to actually chat. Worked if it prints "Scaffolded discoverable entities under: …" plus a file tree, then a launch line or install hint.

---

Next: [Devui Tracing](/blog/posts/maf-py-71-devui-tracing.html)
