# Tools: Giving Agents Capabilities

*An agent without tools can only think and write; tools are what let it act — search the web, query a database, call an API — and turning a Python function into a CrewAI tool is deliberately almost effortless.*

Agents reason and communicate, but on their own they can't reach outside the model — they can't look something up, run a calculation against real data, or take an action in another system. **Tools** close that gap. This fifth post in the CrewAI series covers giving agents capabilities: built-in tools, writing your own, and how tools connect to the broader ecosystem.

## Why tools matter

An agent's raw ability is bounded by its model's training and whatever is in its context. A tool extends it into the real world: a search tool lets it find current information, a database tool lets it query your data, a calculator gives it exact arithmetic, an API tool lets it act. Without tools, a "research agent" can only recall what the model already knows; with a search tool, it can actually research. Tools are what turn an agent from a text generator into something that *does* things — so choosing the right tools for each agent is as important as its role and goal.

## Built-in and community tools

CrewAI ships and supports a broad set of ready-made tools for common needs — web search and scraping, file and document reading, code execution, database and API access, and more, including a `crewai-tools` package and integrations. For a great many use cases you don't write a tool at all; you attach an existing one to an agent:

```python
from crewai import Agent
from crewai_tools import SerperDevTool   # example: a web search tool

researcher = Agent(
    role="Market Researcher",
    goal="Find current, sourced information on a topic",
    backstory="A rigorous analyst who always verifies against live sources.",
    tools=[SerperDevTool()],
)
```

The agent now decides, during its reasoning, when to invoke the tool. You gave it a capability; the LLM chooses when to use it. Reach for built-in tools first — they cover the common cases and save you writing and maintaining your own.

## Writing custom tools

When you need something specific — access to *your* internal API, a domain calculation, a proprietary data source — you write a custom tool. CrewAI makes this straightforward: a tool is essentially a function with a clear name, a description, and typed inputs, exposed to the agent. You can define one with a simple decorator or by subclassing the tool base class:

```python
from crewai.tools import tool

@tool("Lookup account balance")
def account_balance(account_id: str) -> str:
    """Return the current balance for an account id, in minor units."""
    # call your internal service here
    return fetch_balance(account_id)
```

The name and docstring/description are not incidental — they're how the agent understands *what the tool does and when to use it*, exactly like the tool-description discipline from good tool design everywhere. A precise description ("Return the current balance for an account id") produces correct tool selection; a vague one ("does account stuff") produces wrong or missing calls. Typed inputs let CrewAI validate and structure the arguments. Writing a good custom tool is mostly writing a good description and a clean signature.

## Tool design principles

The same principles that make any agent's tools effective apply in CrewAI:

- **Name and describe for the agent.** The description is the agent's basis for choosing the tool — make it specific about what it does and when to use it.
- **One clear job per tool.** Narrow, well-named tools get selected correctly; a Swiss-army tool with a `mode` argument confuses the agent.
- **Validate inputs and return helpful errors.** A tool's error message is feedback the agent will act on — make it actionable so the agent can recover.
- **Give each agent only the tools its role needs.** A crowded toolset both costs context tokens and makes the agent's selection harder; scope tools to the role.

That last point connects to cost and reliability: every tool attached to an agent adds to what the model must consider, so match tools to roles rather than giving every agent everything.

## Tools, MCP, and the ecosystem

Tools are also where CrewAI meets the broader agent ecosystem. Because the Model Context Protocol standardizes how agents consume tools from external servers, CrewAI agents can draw on MCP-exposed tools, letting you reuse a tool built once across frameworks rather than re-implementing it per framework. This is the [MCP](/blog/series/model-context-protocol-from-scratch/) value proposition applied to CrewAI: an agent's capabilities aren't limited to what you hand-write for it: they can include the growing set of standardized, reusable tools the ecosystem provides. When you're deciding whether to build a tool, check whether it already exists as a built-in, a community tool, or an MCP server before writing your own.

## Key takeaways

- Tools let an agent act beyond the model — search, query data, run code, call APIs; without them even a "research agent" can only recall what the model already knows.
- Reach for built-in and community tools first (`crewai-tools` covers search, scraping, files, code, DB/API); attach them to an agent via `tools=[...]` and the LLM decides when to invoke.
- Write custom tools for specific/internal needs as a function with a decorator (or by subclassing) — the name and description are how the agent knows what the tool does and when to use it.
- Apply tool-design discipline: describe precisely for the agent, one clear job per tool, validate inputs with actionable errors, and give each agent only the tools its role needs.
- CrewAI agents can consume MCP-exposed tools, so check for an existing built-in, community, or MCP tool before writing your own.

## Further reading

- [CrewAI documentation](https://docs.crewai.com)
- [Model Context Protocol from Scratch series](/blog/series/model-context-protocol-from-scratch/)
- [CrewAI, Concept by Concept — start of the series](/blog/posts/crewai-01-what-is-crewai.html)
