# Tool Use

*An LLM on its own can only do one thing: generate text. It can't search the web, run code, query a database, check the current time, or send a message — it can only produce words. Tools are what break that confinement, turning a model that can only talk into an agent that can act. Tool use is arguably the single most important capability that makes agents possible, and understanding how it works — and how to design tools well — is central to building effective agents.*

**Tool use** is how agents *act on the world* — the capability that lets an LLM do things beyond generating text. This post covers what tools are, how tool use works (function calling), why tools are transformative for agents, and how to design good tools. It's a foundational agent pattern: without tools, an LLM can only talk; with tools, an agent can act, gather information, and affect the world. (Related: the blog's MCP series covers a standard *protocol* for tools; this post covers the pattern.)

## What tools are

A **tool** (in the agent sense) is a capability the LLM can *invoke* to do something or get information — a function, API, or action available to the agent. Tools are the agent's "hands":

- **Tools extend the LLM beyond text.** On its own, an LLM only generates text — it can't take actions or access anything outside its training. Tools give it *capabilities*: searching the web, running code, querying databases, calling APIs, reading/writing files, doing calculations, retrieving current information, sending messages, and more. Each tool is an action the agent can take that it otherwise couldn't. Tools are what let the model *do things*.
- **Tools provide actions AND information.** Tools serve two roles: *acting* on the world (sending an email, running code, modifying data) and *getting information* the model doesn't have (searching, retrieving data, checking current state). Both are crucial — agents need to *act* and to *know things beyond their training* (current, specific, or private information). Tools cover both, extending the agent outward in both directions.
- **Tools are how agents overcome LLM limitations.** LLMs have real limitations — no access to current/private information, can't reliably do exact computation, can't affect anything. Tools *directly address* these: a search tool provides current information, a code/calculator tool provides reliable computation, action tools let the agent affect things. Tools compensate for what LLMs can't do alone, making the agent far more capable than the model by itself.

Tools are the capabilities an agent can invoke — functions, APIs, actions — that extend the LLM beyond text into acting on the world and accessing information it doesn't have. They're the agent's hands, and they're what make agents capable of real tasks (not just conversation). The mechanism by which the LLM invokes them is function calling.

## How tool use works: function calling

The mechanism behind tool use is **function calling** (or "tool calling") — a capability of modern LLMs to *request* that a tool be invoked, in a structured way. How it works:

- **The model is told what tools exist.** The agent is given *descriptions* of the available tools — what each does, and what inputs (parameters) it takes. This tells the LLM what actions are available and how to use them. The model reasons about which tool (if any) to use based on these descriptions. Good descriptions are essential (below) — the model chooses tools based on them.
- **The model requests a tool call.** When the LLM (in the reason step of the loop) decides to use a tool, it outputs a *structured request* to call that tool with specific arguments — e.g. "call `search` with query='...'". Modern LLMs are trained/tuned to produce these structured tool-call requests reliably (often as structured JSON). The model doesn't run the tool itself; it *requests* the call.
- **The system runs the tool and returns the result.** The agent framework (not the LLM) *executes* the requested tool with the given arguments, gets the result, and *feeds it back* to the LLM as an observation (the observe step of the loop). The LLM then continues — reasoning about the result, deciding the next action. So function calling is the concrete mechanism of the act-observe part of the loop.

```text
   Function calling in the agent loop:
     LLM (reason) → requests: call tool X with args → 
     system executes tool X → returns result →
     LLM observes result → reasons again → ...
   (the LLM decides & requests; the system executes & returns)
```

Function calling is how tool use works mechanically: the model is told what tools exist, requests a structured tool call when it decides to use one, and the system executes the tool and returns the result as an observation. This is the concrete implementation of the act-observe steps of the agent loop — the model decides, the system acts, the result feeds back. It's the plumbing that lets the deciding LLM actually *do* things.

## Why tools are transformative

Tool use is arguably *the* capability that makes agents genuinely useful — worth making explicit why it's so transformative:

- **It turns talking into doing.** The single biggest limitation of a bare LLM — that it can only produce text — is removed by tools. With tools, an agent can *act*: run code, search, modify data, call services, accomplish real tasks. This is the difference between a system that *describes* what to do and one that *does* it. Tools are what make agents *agents* (systems that act), not just chatbots.
- **It grounds the agent in real information.** Tools that *retrieve* information (search, database queries, current data) ground the agent in *real, current, specific* information rather than the model's static, possibly-outdated, possibly-wrong internal knowledge. This dramatically improves accuracy and usefulness — the agent can *look things up* rather than guess. (This connects to RAG — retrieval as a tool.) Grounding via tools is a major reliability improvement.
- **It compensates for LLM weaknesses.** LLMs are unreliable at exact computation, can't access private/current data, and hallucinate — tools directly fix these (a calculator/code tool for exact math, retrieval for current/private data, verification tools for checking). Offloading to tools what the LLM does poorly makes the overall system far more reliable than the LLM alone. Use tools for what LLMs are bad at.
- **It extends capability arbitrarily.** An agent's capabilities are largely defined by its *tools* — give it more/better tools, and it can do more. Tools make agents *extensible*: you expand what an agent can do by adding tools, without changing the model. This composability (agent = model + tools) is a key architectural strength. The tools you give an agent shape what it can accomplish.

Tools are transformative because they turn talking into doing (the core of what makes agents useful), ground the agent in real information (improving accuracy), compensate for LLM weaknesses (computation, current data, verification), and extend capability arbitrarily (agent = model + tools). Tool use is the capability that most makes agents worthwhile. Which means designing tools well matters a lot.

## Designing good tools

Because tools so directly shape an agent's capability and reliability, *designing them well* is important — and there are clear principles:

- **Clear descriptions and interfaces.** The LLM chooses and uses tools based on their *descriptions*, so tools need *clear, accurate descriptions* of what they do and *well-defined inputs*. Ambiguous or poor descriptions lead the model to misuse or not use tools. Treat tool descriptions as a critical interface *for the model* — clarity here directly affects how well the agent uses tools. (This is a bit like writing good API docs, but the consumer is the LLM.)
- **Right granularity.** Tools should be at a useful *granularity* — not so fine-grained that simple tasks need many calls, not so coarse that they're inflexible. Well-scoped tools that do a clear, useful unit of work are easier for the model to use correctly. Design tools around the meaningful actions the agent needs.
- **Robust and safe.** Tools *execute real actions*, so they must be *robust* (handle errors gracefully, return useful error info the model can react to) and *safe* (especially tools that can cause harm — modifying data, spending money, sending messages). Dangerous tools need guardrails (confirmation, restricted scope, sandboxing — e.g. running LLM-generated code safely). Tool safety is a real concern because tools give the agent real-world power. Never give an agent an unguarded dangerous tool.
- **Helpful results.** Tools should return results in a form the LLM can *use* — clear, relevant, appropriately concise (not overwhelming the context). Since the result becomes an observation the model reasons over, well-formatted, informative results help the agent act well on them. Design the *output* for the model's consumption, not just the input.
- **Don't over-tool.** More tools isn't always better — too many tools can confuse the model (which to use?) and bloat the context. Give the agent the tools it needs for its task, well-designed, rather than every possible tool. Focused, well-designed tools beat a sprawling toolbox.

Tool use — invoking capabilities via function calling — is what turns an LLM that can only talk into an agent that can act and access real information, arguably the most important capability making agents useful. Design tools with clear descriptions, right granularity, robustness and safety, helpful results, and appropriate focus. Next: planning and decomposition — how agents break down complex tasks.

## Key takeaways

- A tool is a capability the LLM can invoke (function, API, action) that extends it beyond text — providing both *actions* (run code, modify data, send messages) and *information* (search, query data, current state) — compensating for LLM limitations (no current/private data, unreliable computation, can't affect anything); tools are the agent's "hands."
- Tool use works via function calling: the model is told what tools exist (descriptions + parameters), requests a structured tool call when it decides to use one, and the *system* executes the tool and returns the result as an observation — the concrete implementation of the act-observe steps of the agent loop (the model decides/requests, the system executes/returns).
- Tools are transformative because they turn talking into doing (making agents that *act*, not just chat), ground the agent in real/current information (improving accuracy over the model's static knowledge — cf. RAG), compensate for LLM weaknesses (offload exact math, current data, verification), and extend capability arbitrarily (agent = model + tools, extensible by adding tools).
- Design good tools with clear, accurate descriptions and well-defined inputs (the LLM chooses/uses tools based on these — a critical interface *for the model*), the right granularity (well-scoped units of work), and results formatted for the model to reason over.
- Make tools robust (handle errors, return useful error info) and *safe* — tools execute real actions, so dangerous ones (modifying data, spending money, running code) need guardrails (confirmation, sandboxing, restricted scope) — and don't over-tool (too many tools confuse the model; give focused, well-designed tools for the task).

## Further reading

- [Toolformer: Language Models Can Teach Themselves to Use Tools (Schick et al., 2023)](https://arxiv.org/abs/2302.04761)
- [Retrieval-augmented generation — retrieval as a grounding tool (Wikipedia)](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- [The core agent loop (previous post)](/blog/posts/agent-02-the-core-agent-loop.html)
