# Group Chat

*A collaborative conversation among agents, coordinated by an orchestrator that decides who speaks next. Agents share full history and refine each other's work over rounds — a star topology.*

---

## What this lesson demonstrates

Group chat models a **collaborative conversation** among several agents coordinated by an orchestrator that decides who speaks next. Agents share the full conversation history and refine each other's work over multiple rounds (a Researcher gathers facts, then a Writer synthesizes them). The orchestrator sits at the center of a "star topology" and can select speakers via a simple function, an agent-based orchestrator, or fully custom logic.

The lesson pairs a Researcher and a Writer, cycles between them with a round-robin function, and caps the run at four messages so it always terminates.

## One real excerpt

Speaker selection and termination are chosen at construction time:

```python
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

def round_robin_selector(state: GroupChatState) -> str:
    names = list(state.participants.keys())
    return names[state.current_round % len(names)]

return GroupChatBuilder(
    participants=[researcher, writer],
    termination_condition=lambda conversation: len(conversation) >= 4,
    selection_func=round_robin_selector,
    intermediate_output_from=[researcher, writer],
).build()
```

## The gotcha

Speaker selection is set once via **one of** `selection_func` (a function over `GroupChatState`), `orchestrator_agent` (an intelligent `Agent`), or a custom orchestrator. `termination_condition` is a callable over the messages list — set a hard cap so the run always ends (an agent orchestrator may stop earlier on its own). Without `intermediate_output_from=[...]`, only the orchestrator's terminal `"output"` event is emitted — you won't see individual turns. Agents do **not** share one `AgentSession`; the orchestrator broadcasts each response so every agent has the full history before its next turn. Run with `stream=True`, then `await stream.get_final_response()` for the terminal `AgentResponse`.

## How it maps to Azure AI Foundry

Both participants are `FoundryChatClient` + `AzureCliCredential` agents; `GroupChatBuilder` is client-agnostic. Streaming yields `AgentResponseUpdate` chunks per turn, so you watch each Foundry-backed agent write live.

## Run it

```bash
uv run tutorial/03-workflows/orchestrations/04_group_chat.py
```

Needs Foundry credentials (`az login`). You should see streamed `[author]:` turns, then a Final Response, then `Workflow completed.`

---

Next: [Magentic](/blog/posts/maf-py-64-magentic.html)
