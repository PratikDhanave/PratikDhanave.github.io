# Hello Agent

*The smallest possible Python agent: a Foundry chat client plus instructions, run once collected and once streamed.*

---

## What this lesson demonstrates

This is the Agent primitive stripped to essentials. You wire a `FoundryChatClient` to a deployed model, hand it an instruction string and a name, and call it with a message. That single loop is what tools, memory, and workflows all build on. The lesson runs the same agent two ways: `agent.run(...)` collects the whole answer, and `stream=True` yields chunks as they arrive.

## The code

Construction is factored out of `main` so it can be built and tested on its own:

```python
client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ["FOUNDRY_MODEL"],
    credential=AzureCliCredential(),
)
instructions = (
    "You are a terse, knowledgeable travel guide. "
    "Answer in at most two sentences and never use bullet points."
)
return Agent(client=client, name="HelloAgent", instructions=instructions)
```

Then `main` runs it two ways off the same object:

```python
result = await agent.run("What is the capital of France?")
async for chunk in agent.run("Tell me a fun fact.", stream=True):
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

## What to notice

- **The instructions ARE the agent.** That single string shapes persona, tone, and guardrails. Tweak it, re-run, and both answers shift.
- **One method, two call styles.** `agent.run(...)` returns the finished answer; the same call with `stream=True` becomes an async iterator of chunks — guard each with `if chunk.text` since some carry no text.
- **The gotcha:** the client reads `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_MODEL` from the environment (via `load_dotenv()`), and auth comes from your `az login` session through `AzureCliCredential`. Miss any of those three and construction fails before a single token.

## How it maps to Azure AI Foundry

`FoundryChatClient` binds the agent to your Foundry project endpoint, keyed by the deployed model name. `AzureCliCredential` reuses the token from `az login`, so there are no secrets in code. `instructions` is the system prompt; `name` is how the agent identifies itself.

## Run it

```bash
uv run tutorial/01-get-started/01_hello_agent.py
```

Expected: a non-streaming answer, then the same agent streaming a second reply. The live call needs Foundry creds and `az login`.

---

Next: [Add Tools](/blog/posts/maf-py-02-add-tools.html)
