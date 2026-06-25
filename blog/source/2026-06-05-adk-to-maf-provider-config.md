# Provider Abstraction: From Gemini-Only to Swappable LLMs

*How to port ADK's model hard-codes to Microsoft Agent Framework's provider factory pattern.*

---

## The Problem: Vendor Lock-In

**ADK**:
```python
agent = Agent(
    model="gemini-2.5-flash",
    name="Analyzer",
    instructions="Analyze the data"
)
```

The model is baked in. To swap to OpenAI, you'd need to:
1. Change every `model=` parameter
2. Update credentials (GOOGLE_API_KEY → OPENAI_API_KEY)
3. Adjust prompts (Gemini and GPT-4 have different instruction styles)
4. Retrain your mental model of the system

That's 3 months of engineering for a provider swap.

## The Solution: Provider Abstraction

**Microsoft Agent Framework (MAF)**:
```python
from multi_agent.providers import build_chat_client

client = build_chat_client()  # Reads PROVIDER env var

agent = Agent(
    client=client,
    name="Analyzer",
    instructions="Analyze the data"
)
```

Change `.env`:
```bash
# PROVIDER=ollama
PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Same code. Different model. Same results (modulo model-specific quirks).

## The Architecture

Microsoft Agent Framework's `build_chat_client()` is a factory:

```python
# Pseudocode
def build_chat_client():
    provider = os.getenv("PROVIDER", "ollama")
    
    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "granite4.1:3b")
        return OllamaChatClient(model=model)
    
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return OpenAIChatClient(api_key=api_key, model=model)
    
    elif provider == "foundry":
        endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
        return AzureAIChatClient(endpoint=endpoint)
    
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

All clients implement the same interface: `ChatClient`. Your agents don't care which one they're using.

## Pattern 1: Local Development (Ollama)

**Zero API key required.**

```bash
# .env
PROVIDER=ollama
OLLAMA_MODEL=granite4.1:3b  # Or phi4, neural-chat, etc.
```

You run Ollama locally. Agents talk to `localhost:11434`. Free, fast, offline.

```python
from multi_agent.providers import build_chat_client

client = build_chat_client()  # Reads PROVIDER=ollama
# Calls http://localhost:11434/v1/chat/completions

agent = Agent(client=client, ...)
await agent.run("Analyze this")  # Runs on your laptop via Ollama
```

## Pattern 2: Cost Control (OpenAI)

When you need better quality and don't mind paying:

```bash
# .env
PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # Cheaper than gpt-4o; faster than gpt-3.5
```

```python
client = build_chat_client()  # Reads PROVIDER=openai
# Calls api.openai.com/v1/chat/completions with your API key

agent = Agent(client=client, ...)
await agent.run("Analyze this")
```

## Pattern 3: Production (Azure Foundry)

For regulated environments (healthcare, FinTech):

```bash
# .env
PROVIDER=foundry
FOUNDRY_PROJECT_ENDPOINT=https://my-foundry-project.aiservices.azure.com/
FOUNDRY_MODEL=gpt-4o-mini  # Your Azure-deployed model name
```

```python
from azure.identity import AzureCliCredential

client = build_chat_client()  # Reads PROVIDER=foundry, uses AzureCliCredential
# Calls Azure AI Foundry endpoint with managed identity

agent = Agent(client=client, ...)
await agent.run("Analyze this")  # Runs on Azure; audit-logged, compliant
```

## Pattern 4: Hybrid (Multi-Provider Agents)

You can even mix providers in the same orchestration:

```python
# Fast, cheap analyzer (Ollama)
analyzer_client = OllamaChatClient(model="granite4.1:3b")
analyzer = Agent(client=analyzer_client, name="Analyzer", ...)

# High-quality final decision (OpenAI)
reviewer_client = OpenAIChatClient(model="gpt-4o")
reviewer = Agent(client=reviewer_client, name="Reviewer", ...)

# Orchestrate
thread = AgentThread()
await analyzer.run(prompt, thread=thread)  # Uses Ollama
await reviewer.run("Review the analysis above", thread=thread)  # Uses OpenAI
```

Cost: Cheaper. Quality: Higher (expensive model for final call only).

## The Conversion Checklist

**For every ADK agent:**

1. Remove `model="gemini-..."`
2. Add `client=build_chat_client()` parameter
3. Create `.env` with:
   ```bash
   PROVIDER=ollama  # Start here; cost is $0
   OLLAMA_MODEL=granite4.1:3b  # Or any Ollama model
   # Optional:
   # PROVIDER=openai
   # OPENAI_API_KEY=sk-...
   # OPENAI_MODEL=gpt-4o-mini
   ```
4. Test locally (Ollama)
5. In CI/CD, swap to production provider (Foundry, OpenAI, etc.)
6. No code changes. Just `.env`.

## Real Example: Genie's Migration

**ADK**:
```python
# financials.py
planner = Agent(model="gemini-2.5-flash", name="Planner", ...)
analyzer = Agent(model="gemini-2.5-flash", name="Analyzer", ...)
forecaster = Agent(model="gemini-2.5-flash", name="Forecaster", ...)
reviewer = Agent(model="gemini-2.5-flash", name="Reviewer", ...)
```

Gemini everywhere. Cost is $X/month for 10K requests.

**Microsoft Agent Framework**:
```python
# financials.py
client = build_chat_client()

planner = Agent(client=client, name="Planner", ...)
analyzer = Agent(client=client, name="Analyzer", ...)
forecaster = Agent(client=client, name="Forecaster", ...)
reviewer = Agent(client=client, name="Reviewer", ...)
```

Same code. Toggle `.env`:

- `PROVIDER=ollama`: Cost $0, runs on my laptop (dev)
- `PROVIDER=openai`: Cost $Y/month, faster (staging)
- `PROVIDER=foundry`: Cost $Z/month, HIPAA-eligible (production)

No code changes. Not one line.

---

Next: [Callbacks and Middleware](/blog/posts/adk-to-maf-callbacks.html)
