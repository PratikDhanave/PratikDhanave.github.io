# Code Agents: Actions as Code

*The single idea that defines smolagents is that an agent's action is a snippet of Python, not a JSON blob. It sounds like a minor encoding detail and turns out to change what an agent can do in a single step — because code carries logic, loops, variables, and composition that structured tool calls simply can't express.*

The last post introduced the code agent as smolagents's signature. This post goes deep on it: what a code action actually is, how it differs from JSON tool calling, and why expressing actions as code is more than a formatting choice. Understanding the code agent is understanding smolagents, because everything else in the library serves this one idea.

## Two ways for an agent to act

When an agent decides to *do* something — call a tool — that decision has to be expressed in some format the framework can execute. There are two approaches, and the difference is the whole point of smolagents:

- **JSON tool calling** (the standard) — the model outputs a structured description of *one* tool call: the tool name and its arguments, as JSON. The framework parses it, runs that one tool, feeds the result back, and the model decides the next call. This is how most providers and frameworks work.
- **Code actions** (smolagents's default) — the model outputs *Python code* that calls tools and does whatever logic it needs, and the framework *executes the code*. The action isn't "call tool X with args Y"; it's a snippet that can call tools, use their results, loop, branch, compute, and store variables — all in one step.

```text
JSON tool call (one action = one tool call):
  { "tool": "search", "args": { "query": "largest EU cities" } }
  → framework runs search, returns result, model decides next call

Code action (one action = a code snippet):
  cities = search("largest EU cities")
  populations = [get_population(c) for c in cities[:3]]
  answer = sum(populations)
  → framework runs the whole snippet: search, loop, three get_population calls, a sum
```

Look at what the code action did in *one* step: a search, a loop over its results, three more tool calls, and a computation. In the JSON approach, that's *many* separate round-trips — call search, get result, call get_population, get result, call again, again, then sum — each a separate model turn. The code agent collapses all of it into a single action. That's the crux of why code actions are powerful.

## Why code is more expressive

The deeper reason code actions matter is *expressiveness*: code can naturally express things JSON tool calls express awkwardly or not at all. A JSON tool call is, fundamentally, "invoke one function with these arguments" — it has no native way to represent:

- **Control flow** — loops (do this for each result), conditionals (if this, call that), which code has built in but JSON tool-calling handles only through many separate model turns.
- **Variables and intermediate state** — storing a tool's result and using it in a later call *within the same action*. In JSON tool calling, intermediate results go back to the model as text between turns; in code, they're just variables.
- **Composition** — combining tools, transforming their outputs, feeding one tool's result into another — the essence of real work, which code does directly and JSON tool calls do only by round-tripping through the model.
- **Computation** — actual logic (arithmetic, string manipulation, data transformation) inline, rather than needing a separate tool or model turn for each small operation.

The insight is that **real tasks are usually more than a sequence of isolated function calls** — they involve looping, branching, combining results, and computing, which is exactly what a programming language expresses and a JSON schema doesn't. So code actions aren't just a different encoding; they let the agent express *richer actions* that match the actual shape of the work. An agent that can write code can, in a single action, do what a JSON-tool-calling agent needs many turns to accomplish — because code is a fuller language for "what to do" than a list of function calls.

## Why it plays to the model's strengths

There's a second argument, about the *model*: LLMs are trained on enormous amounts of code, so writing code is something they're often exceptionally good at — arguably more natural for them than emitting a specific, rigid JSON schema. The code agent leans into this:

- **Code is in-distribution** — models have seen vast quantities of Python, so generating correct, expressive code that calls functions is well within their training, often more reliably than producing exactly-schema-conforming JSON.
- **The model can reason in code** — writing code to solve a step is a form of reasoning the model is practiced at, aligning the *action format* with something the model does well.

So code actions align the agent's action language with what LLMs are strongest at, which is part of why the approach performs well (the next post covers the measured efficiency gains). Rather than forcing the model into a constrained JSON format for each isolated call, you let it write code — a language it knows deeply and can use to express rich, composed actions. This is the elegant core of smolagents's bet: the best way for a code-fluent model to act is by writing code.

## Code agents vs tool-calling agents in smolagents

smolagents supports *both* approaches (it has a code agent and a tool-calling agent), and knowing when each fits is practical:

- **Code agent** (the default and the library's focus) — best when tasks involve logic, computation, loops, or composing tool results — which is most substantive agentic work. Its expressiveness and efficiency shine here.
- **Tool-calling agent** (JSON) — can be effective for *simple* systems that don't need variable handling or complex composed actions — where a straightforward one-call-at-a-time approach suffices, or where the environment can't safely execute code (the security post).

smolagents primarily emphasizes code agents *because they perform better overall* on substantive tasks, but offers tool-calling agents for the simple cases (and for constrained environments). The guidance: default to code agents for real work, and use tool-calling agents for simple flows or where code execution isn't safe. The next post quantifies *why* code agents win — the efficiency and accuracy evidence — and then the security post covers the cost that comes with executing code.

## Key takeaways

- The code agent is smolagents's defining idea: instead of the model emitting a JSON description of one tool call (the standard), it writes executable Python that the framework runs — the action is a code snippet, not a JSON blob.
- A single code action can do what many JSON tool-call round-trips would: call a tool, loop over its results, call more tools, compute, and store variables — all in one step — because code carries control flow, variables, composition, and computation that JSON tool calls can't.
- Code is more expressive because real tasks are more than isolated function calls (they involve looping, branching, combining results, computing), which a programming language expresses directly and a JSON schema doesn't — so code actions match the actual shape of the work.
- Code actions play to LLMs' strengths: models are trained on vast amounts of code, so generating expressive tool-calling code is often more natural and reliable than producing exactly-schema-conforming JSON — the action format aligns with what the model does best.
- smolagents supports both: default to code agents for substantive work (logic, computation, composition — where they perform better), and use tool-calling (JSON) agents for simple flows or environments where executing model-written code isn't safe.

## Further reading

- [What is smolagents? (previous post)](/blog/posts/smol-01-what-is-smolagents.html)
- [smolagents documentation — building code agents](https://huggingface.co/docs/smolagents/index)
- [Pydantic AI: structured outputs — the typed-JSON approach's strengths](/blog/posts/pydai-03-structured-outputs.html)
