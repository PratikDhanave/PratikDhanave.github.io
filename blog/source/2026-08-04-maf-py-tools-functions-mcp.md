# Tools in Microsoft Agent Framework (Python): Functions, Hosted Tools, MCP, Skills & CodeAct

*A complete guide to giving a Microsoft Agent Framework agent the ability to act — from a plain Python function the model can call, to provider-hosted sandboxes, remote MCP servers, and higher-level packaging patterns like Skills and CodeAct.*

---

A language model on its own can only produce text. **Tools** are how an agent *does* things — look up a record, run Python, search the web, call a remote service. Microsoft Agent Framework gives you four distinct ways to put tools in front of a model, and choosing the right one is most of the design work:

1. **Function tools** — ordinary Python you write; runs in your process.
2. **Hosted tools** — provider-side capabilities (code interpreter, file search, web search) that run inside Azure AI Foundry, not your process.
3. **MCP tools** — tools borrowed from an external Model Context Protocol server, either dialed locally by your process or hosted by Foundry.
4. **Packaging patterns** — Skills and CodeAct, which change *how* tools are exposed to the model rather than adding new ones.

Every example below drives a `FoundryChatClient` on Azure AI Foundry with `AzureCliCredential()` (so `az login` first), but the tool mechanics are provider-agnostic.

---

## 1. Function tools: a Python function becomes a schema

The foundation. A *function tool* is ordinary Python the agent is allowed to call. Microsoft Agent Framework reads the function's signature and docstring, turns it into a JSON schema the model sees, invokes your function when the model asks, and feeds the return value back so the model can phrase its answer.

The lesson is in how that schema is built: the docstring becomes the tool description, and `Annotated[..., Field(description=...)]` describes each parameter so the model picks tools and arguments accurately.

```python
@tool(
    name="currency_convert",
    description="Convert an amount between INR, USD, EUR and GBP using a fixed rate table.",
    approval_mode="never_require",
)
def convert_currency(
    amount: Annotated[float, Field(description="The amount of money to convert.")],
    from_ccy: Annotated[str, Field(description="Source currency code: INR, USD, EUR or GBP.")],
    to_ccy: Annotated[str, Field(description="Target currency code: INR, USD, EUR or GBP.")],
) -> str:
    ...
```

Tools attach at agent creation: `tools=[get_weather, convert_currency]`.

**The gotcha:** the `@tool` decorator is *optional* — pass a plain function straight to `tools=[...]` and the framework falls back to the function name and docstring. Where the decorator earns its keep is overriding those defaults: `@tool(name=..., description=...)` decouples what the model sees from your Python identifier (and once you set an explicit description, the docstring is ignored). Per-parameter descriptions come from `Annotated[type, Field(description=...)]`; a bare `Annotated[int, "..."]` string also works.

---

## 2. Governing the tool set at runtime

Handing the model every tool up front is rarely optimal — a large schema hurts tool selection and costs tokens. Microsoft Agent Framework gives you two levers to control the tool set *while a turn is running*.

### Progressive tool availability

You can grow or shrink the tool set **from within a tool itself**, using the `FunctionInvocationContext` the framework injects. This keeps the initial schema small and lets you enforce ordering like "read before write" without a full workflow.

```python
@tool(approval_mode="never_require")
def get_record(record_id: str, ctx: FunctionInvocationContext) -> str:
    """Fetch a record. Unlocks update_record once a record has been read."""
    ctx.add_tools(update_record)  # visible to the model on the NEXT loop iteration
    return f"Record {record_id}: title='Example record', status='open'"
```

The mutation API lives on the context: `ctx.add_tools(...)`, `ctx.remove_tools(...)`, and the live mutable `ctx.tools`. To force the first call, pass a `ToolMode` via `options={"tool_choice": {"mode": "required", "required_function_name": "get_record"}}`.

**The gotcha:** changes take effect on the **next** iteration of the function-calling loop — calls already dispatched in the current batch still run. The tool list **resets to the original set on every new `agent.run()`**, so gates re-arm per turn. This API is experimental (`PROGRESSIVE_TOOLS`): it emits an `ExperimentalWarning`, and calling add/remove outside the loop (`ctx.tools is None`) raises `RuntimeError`. The framework resets `tool_choice` to `None` after the first iteration so later steps can pick the newly unlocked tool.

### Human approval for sensitive tools

Some tools are too sensitive to run automatically. Mark a tool `approval_mode="always_require"` and the agent **pauses** instead of executing: the run returns with `result.user_input_requests` populated rather than a final answer. You show the pending call to a human, collect a yes/no, and feed the approval back into a fresh `agent.run(...)`.

```python
result = await agent.run(query)
while result.user_input_requests:
    new_inputs = [query]
    for request in result.user_input_requests:
        new_inputs.append(Message("assistant", [request]))
        approved = (await asyncio.to_thread(input, "Approve? (y/n): ")).strip().lower() == "y"
        new_inputs.append(Message("user", [request.to_function_approval_response(approved)]))
    result = await agent.run(new_inputs)
```

**The gotcha:** after each run, check `result.user_input_requests`; if non-empty the agent is waiting. You must **resend the full context every turn** — the original query, the assistant's request echoed back as a `Message`, and the user's `to_function_approval_response(True|False)`. Keep looping until it's empty, since one query can trigger several approvals. The pause is entirely client-side control flow — the model never runs the guarded tool until your approval comes back.

---

## 3. Hosted tools: capabilities that run in the provider

A *hosted* tool runs inside the provider, not your process. You don't register a Python function — you hand the agent the hosted tool and the model decides when to reach for it. Three are worth knowing.

### Code interpreter — a sandbox for exact answers

The model writes Python, Foundry executes it in a sandbox, and the result flows back. Perfect for exact arithmetic and data crunching — things a model guesses badly but an interpreter nails.

```python
Agent(
    client=client,
    name="coder",
    instructions="Write and execute Python to solve problems. Prefer running code over estimating.",
    tools=[FoundryChatClient.get_code_interpreter_tool()],
)
```

The generated code and its output arrive as **separate content parts** on the result messages — `code_interpreter_tool_call` (the code) and `code_interpreter_tool_result` (the output) — while `result.text` holds only the final answer. To see what the sandbox did, iterate `result.messages` and inspect the structured parts.

### File search — grounded retrieval, no retrieval code

Upload files, create a vector store, index into it, and hand the agent a file-search tool bound to the store id. When the model needs the documents, Foundry runs retrieval server-side and grounds the reply.

```python
file = await client.client.files.create(
    file=("todays_weather.txt", b"The weather today is sunny with a high of 75F."),
    purpose="assistants",
)
vector_store = await client.client.vector_stores.create(name="knowledge_base",
    expires_after={"anchor": "last_active_at", "days": 1})
result = await client.client.vector_stores.files.create_and_poll(
    vector_store_id=vector_store.id, file_id=file.id)
# then: tools=[client.get_file_search_tool(vector_store_ids=[vector_store.id])]
```

Note that file and vector-store ops go through the raw SDK handle `client.client`, and `create_and_poll` **blocks until indexing finishes** — check `result.last_error` before running the agent or the store may be empty when the model searches.

**The gotcha:** vector stores are billable, provider-specific resources. On Foundry upload with `purpose="assistants"`. Delete the store and file when done; `expires_after` is a backstop, not a substitute for cleanup.

### Web search — live results with citations

Attach the hosted web-search tool and Foundry performs the search and grounds the answer, returning **URL citations**.

```python
web_search_tool = FoundryChatClient.get_web_search_tool()
Agent(client=client, name="web-researcher",
      instructions="Use web search to find current, factual information and cite your sources.",
      tools=[web_search_tool])
```

Citations arrive as annotations: iterate `result.messages → message.contents → content.annotations` and read `annotation.url` / `annotation.title`.

**The gotcha:** availability is provider-gated. If your Foundry project lacks the generic web-search tool, switch to Bing grounding — resolve a Bing connection id from the project, then `FoundryChatClient.get_bing_grounding_tool(connection_id=..., market="en-US", freshness="Day")`, passed via `tools=[...]` exactly the same way.

---

## 4. MCP: borrowing tools from an external server

The Model Context Protocol lets an agent borrow tools from an **external** server — a filesystem server, a GitHub server, your own — over a standard protocol. You don't write the tool; you connect to a server that provides it. Microsoft Agent Framework supports two postures.

### Local MCP — your process dials the server

```python
filesystem = MCPStdioTool(
    name="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
)
# also: MCPStreamableHTTPTool(name, url) and MCPWebsocketTool(name, url)
```

The MCP tool object is a **connection, not a value** — you must enter it before use: `async with agent.mcp_tools[0]:` performs the handshake and loads the server's tool catalog, then `run()` can call the remote tools. Passing it in `tools=[...]` merges its remote tools alongside any local `@tool` functions.

### Hosted MCP — Foundry dials the server

Hosted MCP inverts the posture: you describe the server once and the *Foundry service* connects and calls it. Your process never opens a socket.

```python
learn_mcp = client.get_mcp_tool(
    name="Microsoft Learn MCP",
    url="https://learn.microsoft.com/api/mcp",
    approval_mode="never_require",
)
Agent(client=client, name="MicrosoftLearnAgent",
      instructions="Answer by searching Microsoft Learn content only.",
      tools=[learn_mcp])
```

Build it from the client (`client.get_mcp_tool(...)`), so the call runs server-side. `approval_mode` gates execution — `"never_require"` is only safe for **read-only** servers; use `"always_require"` for any write-capable server (GitHub, payments) so a human gates side effects before Foundry executes them. Auth travels in `headers={"Authorization": "Bearer ..."}`, and you can attach several servers at once, each with its own `approval_mode`.

---

## 5. Packaging patterns: Skills and CodeAct

These don't add new tools — they change *how* tools and instructions reach the model.

### Skills — capabilities that load lazily

A skill is a portable package of instructions, resources, and scripts. Skills load via **progressive disclosure**: only the skill's name and description (~100 tokens) sit in the system prompt. The agent then calls built-in tools — `load_skill` for full instructions, `read_skill_resource` for a doc, `run_skill_script` for a bundled script — only when a task needs them.

```python
unit_converter_skill = InlineSkill(
    frontmatter=SkillFrontmatter(
        name="unit-converter",
        description="Convert between common units... Use when asked to convert miles, kilometers...",
    ),
    instructions="Use this skill when the user asks to convert between units. ...",
)

@unit_converter_skill.script(name="convert", description="Multiply a value by a factor")
def convert_units(value: float, factor: float) -> str:
    return json.dumps({"result": round(value * factor, 4)})
# attach via context_providers=[SkillsProvider(unit_converter_skill)]
```

**The gotcha:** the frontmatter `description` is the only thing the model sees up front — pack it with trigger keywords. Code-defined scripts run in-process; gate risky ones with `SkillsProvider(skill, require_script_approval=True)` and drain `result.user_input_requests`. For file-based skills on disk, use `SkillsProvider.from_paths(...)`.

### CodeAct — one program instead of a tool loop

CodeAct collapses the "model → tool → model → tool" loop. A connector adds a single `execute_code` tool: the model writes one short Python program combining control flow, data transforms, and tool calls, and the sandbox runs it once. Provider tools on the connector aren't exposed directly — the generated code reaches them via `call_tool("name", ...)`.

```python
from agent_framework.hyperlight import HyperlightCodeActProvider

codeact = HyperlightCodeActProvider(tools=[fetch_users, compute], approval_mode="never_require")
agent = Agent(client=client, name="CodeActAgent",
    instructions="Orchestrate work in a single execute_code block using call_tool(...). End with print(...).",
    context_providers=[codeact])
```

**The gotcha:** install `agent-framework-hyperlight --pre`; it needs a supported sandbox backend, so wrap construction in `try/except` and fall back to direct tool calling on unsupported platforms. The generated code must end with `print(...)` (Hyperlight doesn't return the last expression), in-memory state doesn't persist across `execute_code` calls, and `call_tool(...)` runs the host callback in the **host** process (with host filesystem, network, and creds) — not re-implemented in the sandbox.

---

## 6. Choosing the right tool type

| Need | Use | Runs where |
|---|---|---|
| Call your own code / business logic | Function tool | Your process |
| Exact math, data crunching, file processing | Code interpreter (hosted) | Provider sandbox |
| Ground answers in your documents | File search (hosted) | Provider |
| Answer about current events | Web search / Bing grounding (hosted) | Provider |
| Reuse an existing tool server | MCP (local or hosted) | Your process or provider |
| Enforce read-before-write / shrink schema | Progressive tools | Your process |
| Gate a sensitive action on a human | `approval_mode="always_require"` | Client-side pause |
| Package a reusable capability | Skill (progressive disclosure) | Your process |
| Replace a long tool loop with one program | CodeAct | Sandbox + host callbacks |

---

## Key takeaways

- **Function tools are schemas.** The model chooses by wording, so invest in the description and `Annotated` parameter docs.
- **Hosted tools move work to the provider.** No local function, provider-gated availability, and structured results ride alongside `result.text` — inspect `result.messages` for the details.
- **MCP is about *who dials the server*.** Local MCP is a connection you enter with `async with`; hosted MCP hands the dialing to Foundry.
- **Approval and progressive tools are client-side control flow.** They gate and shape the loop; the model never bypasses them.
- **Skills and CodeAct trade schema size for indirection** — reach for them when a flat tool list stops scaling.

Everything here is provider-agnostic in shape: swap the `FoundryChatClient` for another chat client and the tool mechanics hold. The model reads schemas and citations; your job is to decide *where each tool runs* and *what a human must approve*.

---

## Interactive diagrams

Explore the concepts in this guide as self-contained, pan/zoom interactive diagrams (light/dark, no dependencies):

- [Code Act](/blog/diagrams/maf-py-24-code-act.html)
