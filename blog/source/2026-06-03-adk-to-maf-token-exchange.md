# Token Exchange Patterns: Porting Multi-Turn State from ADK to MAF

*How conversation threads replace session state; how to track token usage across agent chains.*

---

## The Shift: Sessions → Threads

**ADK** uses a `SessionService`:
```python
session = session_service.get_or_create(user_id)
session.state["context"] = "..."
result = await agent.run(prompt, session=session)
# Next call: agent has access to session.state["context"]
```

State persists across calls in a dictionary. It's implicit.

**MAF** uses an `AgentThread`:
```python
thread = AgentThread(user_id=user_id)
# Conversation history is the thread
result1 = await agent1.run(prompt, thread=thread)
result2 = await agent2.run(prompt, thread=thread)
# Both agents see the same conversation history
```

History is explicit. State is in messages, not in a dict.

## Why This Matters

**Clarity**: In MAF, you can serialize a thread, read it back, and the conversation is replayed. In ADK, `session.state` is opaque.

**Auditability**: Every turn is a message. You can log, redact, or verify each turn independently.

**Token tracking**: Messages have token counts. You can sum them across a thread.

## Pattern 1: Sequential Refinement

Convert an ADK refinement loop (agent calls itself until converged):

**ADK**:
```python
session.state["iterations"] = 0
while session.state["iterations"] < 3:
    result = await agent.run(f"Refine the plan", session=session)
    session.state["iterations"] += 1
```

**MAF**:
```python
thread = AgentThread()
for i in range(3):
    result = await agent.run(f"Refine the plan (iteration {i+1})", thread=thread)
```

The thread carries history. You control the loop.

## Pattern 2: Multi-Agent Conversation (Token Exchange)

ADK agents read/write shared state. MAF agents read/write a thread.

**ADK**:
```python
session.state["analysis"] = ""
analysis_agent = Agent(..., name="Analyzer", tools=[...])
result = await analysis_agent.run("Analyze this", session=session)
session.state["analysis"] = result.message.content

# Later, another agent reads it
reviewer = Agent(..., instructions=f"Review the analysis: {session.state['analysis']}")
result2 = await reviewer.run("Is this good?", session=session)
```

State is implicit, scattered across the code.

**MAF** (cleaner):
```python
thread = AgentThread()

# Analyzer writes to thread via message
analyzer = Agent(..., name="Analyzer")
result = await analyzer.run("Analyze this", thread=thread)

# Reviewer reads from thread implicitly
reviewer = Agent(..., instructions="Review the analysis in the conversation above")
result2 = await reviewer.run("Is this good?", thread=thread)
```

Reviewer doesn't need to know about `session.state["analysis"]`. The thread IS the context.

## Pattern 3: Token Budgeting

In a regulated environment, you need to track LLM costs across a multi-agent run.

**ADK**: You'd manually accumulate:
```python
total_tokens = 0
for agent in agents:
    result = await agent.run(prompt, session=session)
    total_tokens += result.usage.total_tokens
```

**MAF**: Same pattern, but cleaner instrumentation:
```python
thread = AgentThread()
total_tokens = 0

for agent in agents:
    result = await agent.run(prompt, thread=thread)
    total_tokens += result.message.token_count
    
    # Optionally, enforce a budget
    if total_tokens > MAX_TOKENS:
        print(f"Budget exceeded: {total_tokens} > {MAX_TOKENS}")
        break
```

The thread carries the full conversation, so you can audit token usage per turn.

## Pattern 4: Long-Term Memory

ADK sessions don't distinguish short-term (conversation) from long-term (facts about the user).

**MAF** cleanly separates them:

```python
# Short-term: conversation thread
thread = AgentThread(user_id=user_id)

# Long-term: file store or vector DB
memory_store = MemoryFileStore(user_id)
context = await memory_store.query("user preferences")

# Agent reads from both
agent = Agent(
    ...,
    instructions=f"You know: {context}. Conversation so far: [in thread]"
)
result = await agent.run(prompt, thread=thread)

# If agent learns something, save it
if learned = extract_learnings(result):
    await memory_store.upsert(learned)
```

**Clarity**: Thread = conversation. Memory = facts. No ambiguity.

## The Conversion Checklist

When you see ADK `session.state[key]`:

- [ ] If it's conversation history → migrate to `AgentThread`
- [ ] If it's user facts → migrate to `MemoryStore` or vector DB
- [ ] If it's control flow (iteration count, step number) → own the loop, use local variables
- [ ] If it's per-agent metadata → store in the agent's instructions or a context object

## Real Example: Genie's Financial Supervisor

**ADK**:
```python
session.state["analysis"] = ""
session.state["forecast"] = ""
session.state["decision"] = ""

analyzer = ...
result = await analyzer.run(prompt, session=session)
session.state["analysis"] = result.content

forecaster = ...
result = await forecaster.run(f"Based on: {session.state['analysis']}", session=session)
session.state["forecast"] = result.content

# Supervisor reads all three
supervisor = ...
result = await supervisor.run(
    f"Given analysis={session.state['analysis']}, forecast={session.state['forecast']}, decide",
    session=session
)
```

State is scattered. Control flow is implicit.

**MAF**:
```python
thread = AgentThread()

analyzer = Agent(..., name="Analyzer")
await analyzer.run(prompt, thread=thread)

forecaster = Agent(..., name="Forecaster")
await forecaster.run("Given the analysis above, forecast", thread=thread)

supervisor = Agent(..., name="Supervisor", instructions="Review the conversation above and decide")
result = await supervisor.run("Based on everything above, make the decision", thread=thread)
```

Control flow is explicit. State lives in the thread. Each agent sees the full conversation.

---

Next: [Tool Wrapping and Governed Tools](/blog/posts/adk-to-maf-tool-wrapping.html)
