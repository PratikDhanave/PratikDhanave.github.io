# Host Your Agent

*Everything so far ran once and exited. To use an agent like a product, put a server in front of it — DevUI stands up a local web chat around any agent with one call.*

---

## What this lesson demonstrates

Every prior lesson ran a script and quit. `serve()` from `agent_framework.devui` wraps any agent (or several) in a local web inspector and chat surface, so you can interact with it live instead of editing print statements. This turns the same `build_agent()` you already know into a running, browsable service.

## The code

Build the agent as usual, then hand it to `serve()`:

```python
from agent_framework.devui import serve

agent = build_agent()
print("Starting DevUI… open the printed URL, chat, Ctrl-C to stop.")
serve(entities=[agent])   # blocks, running a local web server until Ctrl-C
```

DevUI ships as a separate package, so the import is guarded with a helpful hint:

```python
try:
    from agent_framework.devui import serve
except ModuleNotFoundError as e:
    raise SystemExit(f"DevUI isn't installed: {e}\nInstall it: uv add agent-framework-devui")
```

## What to notice

- **`serve()` blocks and manages its own event loop.** That's why this entry point is a plain sync `main()` — no `asyncio.run()`. Pass `entities=[a1, a2]` to host several agents at once.
- **DevUI is an extra install.** It isn't in the base package: `uv add agent-framework-devui` (or `uv sync --extra hosting`). The guarded import surfaces that exact hint instead of a raw traceback.
- **The gotcha:** don't wrap `serve()` in `asyncio.run()` — it runs its own loop, so doing so double-starts one and errors.

## How it maps to Azure AI Foundry

The hosted agent is the same `FoundryChatClient` + `AzureCliCredential` agent from lesson 1; DevUI only adds a web front end. Each chat message in the browser becomes a Foundry Responses call under the hood, so live use needs Foundry creds and `az login`.

## Run it

```bash
uv run tutorial/01-get-started/08_host_your_agent.py
```

Expected: "Starting DevUI…" then a local URL; the server blocks until Ctrl-C. Needs Foundry creds and the DevUI extra.

---

Next: [Middleware](/blog/posts/maf-py-09-middleware.html)
