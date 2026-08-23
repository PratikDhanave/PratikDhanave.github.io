# Tools

*In a model-driven agent, tools are everything the agent can actually do — the model supplies the reasoning, the tools supply the capability. Strands makes defining them almost trivial (decorate a Python function) and plugs into MCP's large ecosystem, so equipping an agent well becomes the developer's main lever.*

The agent loop needs tools for the model to act. This post covers **tools** in Strands: how you define them (a decorated Python function), the built-in tools and MCP ecosystem, and why — in a model-driven framework specifically — tool quality is the developer's primary point of leverage. If the model drives, the tools are what it drives *with*.

## Tools are decorated Python functions

Strands makes tool definition minimal, consistent with its whole philosophy: a tool is a **Python function you decorate**, and the SDK generates what the model needs from the function's signature and docstring:

```python
# Illustrative shape — see the Strands docs for exact API.
from strands import tool

@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return fetch_weather(city)   # your implementation
```

As with the other typed-function-as-tool frameworks (the Pydantic AI and LangChain tools posts), you don't hand-write a JSON schema — Strands derives the tool's interface from the type hints, and the **docstring becomes the description** the model uses to decide when to call it. So a Strands tool is just a well-typed, well-documented Python function registered with the agent. This minimalism matters: because the model drives, adding a capability should be as frictionless as writing a function, and it is.

The same tool-design disciplines from across the blog apply, and they matter *more* here because the model relies entirely on tool descriptions to plan:

- **Clear docstrings** — the description is what the model reasons over to choose tools; vague descriptions cause misuse or neglect.
- **Precise type hints** — so the model's arguments are validated and the tool's contract is explicit.
- **Focused tools** — each tool does one thing; few, well-described tools beat many overlapping ones for reliable selection.

## Built-in tools and MCP

Beyond your own functions, Strands gives an agent capabilities two other ways:

- **Built-in tools** — Strands ships common tools so you don't reinvent them.
- **MCP (Model Context Protocol)** — Strands has built-in support for MCP servers, connecting the agent to the large and growing ecosystem of MCP-exposed tools (the [MCP from Scratch](/blog/series/model-context-protocol-from-scratch/) series covers the protocol). This is significant: rather than writing every integration, you connect to MCP servers and the agent gains their tools. MCP is becoming the standard way agents access tools across frameworks, and Strands embracing it means an agent's capabilities aren't limited to what you hand-write.

The combination — trivial custom tools, built-in tools, and the MCP ecosystem — means equipping a Strands agent is largely *assembling* capabilities (some yours, many pre-built) rather than building each from scratch. For a model-driven agent, this is exactly what you want: a rich, easily-assembled toolset for the model to draw on.

## Why tools are the developer's main lever

Here's the point specific to model-driven frameworks: **because the model drives, tools are the developer's primary lever on what the agent can accomplish.** In a workflow-first framework, you shape the agent through the workflow you author; in Strands, you don't author the workflow — so your leverage is elsewhere, and it's mostly in *the tools you provide* (and the prompt). The model can only do what its tools let it do, and it chooses among tools based on their descriptions, so:

- **The toolset defines the agent's capability ceiling.** A model-driven agent with poor tools is a capable planner with nothing to act on; a well-equipped one can accomplish far more. Investing in good tools directly expands what the agent can do.
- **Tool descriptions shape the model's decisions.** Since the model selects tools by their descriptions, description quality directly affects whether the model plans well — clear, accurate descriptions are how you *guide* a model-driven agent without scripting it.
- **Tool granularity affects reliability.** Too many overlapping tools degrade the model's selection; a focused, well-chosen set keeps the model's tool decisions reliable — especially important when the model, not your code, is choosing.

So in Strands, "programming the agent" is largely (a) writing the system prompt and (b) equipping it with good tools. The tools aren't just a feature — they're the main thing you control in a model-driven design, which is why this post matters more than a "tools" post would in a workflow-first framework. Equip the model well, and the model-driven approach flourishes; equip it poorly, and no amount of model capability compensates.

## Tools and reliability

The tool layer is also where several reliability concerns live (detailed in the production post):

- **Tool errors** — tools call real systems that fail; handle errors and feed them back so the model can adapt or degrade gracefully. A model-driven agent needs to *observe* tool failures to route around them.
- **Tool safety** — tools *act* (they can change things, call APIs, spend money), so dangerous tools need guardrails, and a model driving autonomously should have appropriately-scoped, safe tools — you're trusting the model to choose when to use them.
- **Observability of tool calls** — since the model chooses tools dynamically, observing which tools it called (and why) is central to understanding and debugging the agent (the exposed loop from the last post).

The theme: tools are the agent's hands, and in a model-driven framework the model wields them autonomously — so giving it *good, safe, well-described, observable* tools is both the main lever of capability and a key locus of reliability. The next post covers the other swappable ingredient: the model providers behind the agent.

## Key takeaways

- A Strands tool is a decorated Python function: the SDK derives the interface from type hints and the description from the docstring (no hand-written JSON schema) — minimal, consistent with the model-driven philosophy that adding a capability should be as easy as writing a function.
- Beyond custom functions, Strands provides built-in tools and built-in MCP support, connecting agents to the large MCP tool ecosystem — so equipping an agent is largely *assembling* capabilities (yours + pre-built + MCP) rather than building each from scratch.
- In a model-driven framework, tools are the developer's primary lever: the model drives, so you shape the agent through the tools you provide (and the prompt), not an authored workflow — the toolset is the agent's capability ceiling.
- Tool descriptions directly shape the model's decisions (it selects tools by description), so clear docstrings, precise type hints, and focused, non-overlapping tools are how you *guide* a model-driven agent without scripting it.
- Tools are also a reliability locus: handle tool errors so the model can adapt, scope tools safely (the model wields them autonomously), and observe tool calls (since the model chooses dynamically) — good, safe, well-described, observable tools are what make the model-driven approach work.

## Further reading

- [The agent loop (previous post)](/blog/posts/strands-03-the-agent-loop.html)
- [Model Context Protocol from Scratch series](/blog/series/model-context-protocol-from-scratch/)
- [Pydantic AI: tools and function calling — the typed-function-as-tool pattern](/blog/posts/pydai-04-tools-and-function-calling.html)
