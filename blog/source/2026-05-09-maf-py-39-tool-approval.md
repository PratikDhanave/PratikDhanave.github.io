# Tool Approval

*Pausing the agent for a human yes/no before a sensitive tool runs.*

---

## What it demonstrates

Some tools are too sensitive to run automatically. By marking a tool with `approval_mode="always_require"`, the agent **pauses** instead of executing it: the run returns with `result.user_input_requests` populated rather than a final answer. You show the pending function and arguments to a human, collect a yes/no, then feed the approval back into a fresh `agent.run(...)` so the agent can proceed.

This lesson pairs a low-risk `get_weather` (runs automatically) with a guarded `get_weather_detail` (always asks first).

## The code

```python
result = await agent.run(query)
while result.user_input_requests:
    new_inputs = [query]
    for request in result.user_input_requests:
        print(f"Approval needed for tool: {request.function_call.name}")
        new_inputs.append(Message("assistant", [request]))
        approved = (await asyncio.to_thread(input, "Approve? (y/n): ")).strip().lower() == "y"
        new_inputs.append(Message("user", [request.to_function_approval_response(approved)]))
    result = await agent.run(new_inputs)
```

## The gotcha

After each run, check `result.user_input_requests`. If it's non-empty the agent is waiting; each request exposes `.function_call.name` and `.function_call.arguments`. Without a thread you must **resend the full context every turn** — the original query, the assistant's request echoed back as a `Message`, and the user's approval response. Build the response with `request.to_function_approval_response(True|False)`: `True` approves and runs the tool, `False` rejects it. Keep looping until `user_input_requests` is empty, since one query can trigger several approvals (one per sensitive call).

## Azure / MAF mapping

`approval_mode` is a `@tool` decorator setting, evaluated by the framework before it dispatches the call to Azure AI Foundry (`FoundryChatClient` + `AzureCliCredential()`). The pause is entirely client-side control flow — the model never runs the guarded tool until your approval message comes back on a subsequent run.

## Run it

`uv run tutorial/02-agents/tools/03_tool_approval.py` — needs Foundry creds. It pauses with `Approval needed for tool: get_weather_detail`, waits for `y/n`, then answers.

---

Next: [Code Interpreter](/blog/posts/maf-py-40-code-interpreter.html)
