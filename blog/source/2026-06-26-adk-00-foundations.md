# Foundations: The Smallest ADK Agent and the Shape Everything Builds On
*An `LlmAgent`, a `Runner`, a `Session`, and a CLI that runs it all — the four pieces the other 25 concepts sit on top of.*

---

Google's **Agent Development Kit (ADK)** is a code-first framework for building, evaluating, and deploying LLM agents. It is model-agnostic (tuned for Gemini, but it also drives Claude, LiteLLM-backed models, and Ollama) and deployment-agnostic (your laptop, Cloud Run, GKE, or Vertex Agent Engine). It ships in two parallel forms — the Python package `google-adk` and the Go module `google.golang.org/adk/v2` — and this series works through both side by side.

This first post is the load-bearing one. Almost everything later — tools, memory, multi-agent orchestration, evaluation — is a variation on four primitives you meet here: the **agent**, the **runner**, the **session**, and the **`adk` CLI**. Get these into muscle memory and the rest of ADK reads as elaboration.

## An agent is a configured LLM with a job

An `LlmAgent` (usually written just `Agent`) is not a model call. It is a bundle of four things: a `name`, a `model`, an `instruction` (its system prompt / job description), and a list of `tools` it is allowed to call. When a message arrives, the model reads the instruction, sees the tool schemas, and decides whether to answer directly or call a tool. You never invoke the tool yourself — you *describe* it and let the model choose.

Here is a minimal weather-and-time agent in Python. Each tool is a plain function; ADK reads its type hints to build the argument schema the model sees, and its docstring to tell the model what the tool is for.

```python
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
    """Retrieve the current weather report for a city.

    Args:
        city: Name of the city, e.g. "Paris".
    """
    data = {"paris": "sunny, 22°C", "london": "overcast, 15°C"}
    key = city.strip().lower()
    if key in data:
        return {"status": "success", "report": f"The weather in {city} is {data[key]}."}
    return {"status": "error", "error_message": f"No data for {city!r}."}

root_agent = Agent(
    name="weather_agent",
    model="gemini-flash-latest",
    description="Answers questions about the weather in a city.",
    instruction="Answer weather questions using get_weather. Refuse anything else.",
    tools=[get_weather],
)
```

Two conventions are doing quiet work here. First, `root_agent` is a *module-level variable with that exact name* — the CLI discovers agents by looking for it. Second, the tool returns a `dict` with a `status` key instead of a bare string. That structured envelope lets the model reliably branch on success versus failure rather than parsing prose — a pattern worth adopting everywhere.

The Go form expresses the same agent, but the idioms invert. Where Python introspects a function at runtime, Go derives the tool's schema from declared struct types at compile time. The `json` tags become the parameter names the model sees.

```go
import (
    "google.golang.org/adk/v2/agent"
    "google.golang.org/adk/v2/agent/llmagent"
    "google.golang.org/adk/v2/model/gemini"
    "google.golang.org/adk/v2/tool"
    "google.golang.org/adk/v2/tool/functiontool"
)

type cityInput struct {
    City string `json:"city"` // Name of the city, e.g. "Paris".
}
type toolOutput struct {
    Status       string `json:"status"`
    Report       string `json:"report,omitempty"`
    ErrorMessage string `json:"errorMessage,omitempty"`
}

model, _ := gemini.NewModel(ctx, "gemini-flash-latest", &genai.ClientConfig{
    APIKey: os.Getenv("GOOGLE_API_KEY"),
})
weatherTool, _ := functiontool.New(functiontool.Config{
    Name:        "get_weather",
    Description: "Retrieve the current weather report for a city.",
}, func(_ agent.Context, in cityInput) (toolOutput, error) {
    return weatherReport(in.City), nil
})

rootAgent, _ := llmagent.New(llmagent.Config{
    Name:        "weather_agent",
    Model:       model,
    Description: "Answers questions about the weather in a city.",
    Instruction: "Answer weather questions using get_weather. Refuse anything else.",
    Tools:       []tool.Tool{weatherTool},
})
```

Note the model difference: Python takes a model *string* and resolves it lazily; Go wants a constructed `*gemini.Model` *value*, so you pass a `context.Context` and a client config up front — and model construction can fail, which is why Go threads `ctx` and error returns through agent setup.

## The runner owns the loop; the session holds the memory

An agent decides; a **`Runner`** orchestrates. The runner sends your message to the agent, executes any tool calls the model asks for, feeds results back, and repeats until the model produces a final answer — the "reason → act → observe" cycle. What it yields is a *stream of `Event` objects* (partial text, tool calls, tool results, the final response), not a single string.

Conversation state lives in a **`Session`**, handed out by a **`SessionService`**. The session is where the message history and any accumulated state persist across turns. For local work, `InMemoryRunner` bundles in-memory session, artifact, and memory services so you can experiment without wiring up storage.

```python
import asyncio
from google.adk.runners import InMemoryRunner
from google.genai import types

async def ask(question: str) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="foundations")
    session = await runner.session_service.create_session(
        app_name="foundations", user_id="learner"
    )
    message = types.Content(role="user", parts=[types.Part(text=question)])
    async for event in runner.run_async(
        user_id="learner", session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content:
            print(event.content.parts[0].text)

asyncio.run(ask("What's the weather in Paris?"))
```

This is the pattern real applications embed: swap `InMemoryRunner` for `Runner(...)` backed by persistent services and the same loop runs against a database. Go builds the runner explicitly via the `runner` package — a topic later in the series — but the mental model is identical.

> **Mental model.** Agent = *what to do* (instruction + tools). Runner = *the loop that does it*. Session = *what it remembers*. Keep those three separate in your head and ADK stops feeling magical.

## The CLI: run an agent with zero server code

The best part of the foundations: you do not write a server to try an agent. ADK's `adk` CLI auto-discovers your agent package and runs it two ways.

```bash
adk web            # local web chat with a trace/inspector panel
adk run greeting_agent   # terminal REPL against the same agent
```

`adk web` opens a dev UI where you can chat *and* watch every event, tool call, and token flow through — invaluable for debugging why the model did or didn't call a tool. `adk run` gives you a REPL for the same agent. The `full` launcher in `adk-go` is the equivalent, exposing `web` and `console` subcommands off the compiled binary. In both languages the point is the same: a fast dev loop where the framework, not your boilerplate, is running the agent.

## When to reach for each run mode

- **`adk web`** — building and debugging; you want to *see* the event trace.
- **`adk run`** — quick terminal sanity checks, no browser.
- **Programmatic `Runner`** — production; you embed the loop in your own service and control sessions, streaming, and persistence.

That is the whole foundation. Every later concept — richer instructions, structured output, memory, sub-agents, evaluation, deployment — plugs into these same four sockets.

**Next in the series:** LLM Agents — going deeper on instructions, model configuration, and structured output.
