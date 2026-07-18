# Code Interpreter

*A provider-hosted sandbox that writes and runs Python for exact answers.*

---

## What it demonstrates

A "hosted" tool runs inside the provider, not in your process: the model writes Python, the provider executes it in a sandbox, and the result flows back into the conversation. It's perfect for exact arithmetic, data crunching, and file processing — things a language model guesses badly but a Python interpreter nails.

The key difference from a function tool: you don't register a Python function. You just hand the agent the hosted tool and the model decides when to reach for it.

## The code

```python
return Agent(
    client=client,
    name="coder",
    instructions=(
        "You are a helpful assistant that writes and executes Python code "
        "to solve problems. Prefer running code over estimating answers."
    ),
    tools=[FoundryChatClient.get_code_interpreter_tool()],
)
```

The generated code and its output arrive as separate content parts on the result messages — type `code_interpreter_tool_call` (the code) and `code_interpreter_tool_result` (the execution output) — while `result.text` holds the final answer.

## The gotcha

Foundry exposes the tool through the classmethod `FoundryChatClient.get_code_interpreter_tool()` passed in `tools=[...]` — you do **not** write your own `@tool` function for this. Availability is provider-dependent (Azure AI Foundry supports it). And if you want to see what the sandbox actually did, iterate `result.messages` and inspect the structured content parts; the raw code and its stdout are not folded into `result.text`, they ride along as separate parts.

## Azure / MAF mapping

This is a hosted capability of Azure AI Foundry, not a local callable — the client is a `FoundryChatClient` with `AzureCliCredential()`, and the code runs server-side in Foundry's sandbox. Contrast with the function-tools lesson, where your Python ran in-process; here the model's Python runs in the provider.

## Run it

`uv run tutorial/02-agents/tools/04_code_interpreter.py` — needs Foundry creds. It prints the generated code, its execution output, then the answer (e.g. factorial of 100 has 158 digits).

---

Next: [File Search](/blog/posts/maf-py-41-file-search.html)
