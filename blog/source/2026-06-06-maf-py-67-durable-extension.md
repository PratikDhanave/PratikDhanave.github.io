# Durable Extension

*Making agent threads and orchestrations crash-proof with AgentFunctionApp on Durable Task infrastructure.*

---

## What it demonstrates

The Durable Extension makes agents and multi-agent orchestrations *durable*: threads, orchestration progress, and workflow steps are checkpointed on Durable Task infrastructure. Sessions survive process crashes, resume on any worker, and can pause for hours or days (human-in-the-loop) without burning compute. You wrap normal agents in `AgentFunctionApp(agents=[...])`, which auto-generates HTTP endpoints (`POST /api/agents/<Name>/run`) and persists conversation state per `x-ms-thread-id` — no manual thread objects.

## One real excerpt

```python
from agent_framework.azure import AgentFunctionApp

app = AgentFunctionApp(agents=agents)  # registering makes each thread durable

@app.orchestration_trigger(context_name="context")
def triage_orchestration(context):          # a generator (def + yield), NOT async
    email_text = context.get_input()
    spam_agent = app.get_agent(context, "SpamDetector")   # the DURABLE wrapper
    session = spam_agent.create_session()
    detection = yield spam_agent.run(messages=f"...{email_text}", session=session,
                                     options={"response_format": SpamDetectionResult})
```

## The gotcha

Inside an `@app.orchestration_trigger` you must NOT call the raw agent — fetch the durable wrapper with `app.get_agent(context, "Name")`, or the step won't be checkpointed. The trigger is a *generator* (`def` + `yield`), not `async def`, because Durable Functions replays it after a failure and every `yield`ed step must be a resumable point. Structured output goes through `options={"response_format": MyModel}` and comes back under `.get("structured_response")`. This can't run under plain `uv run`: durable hosting needs the Azure Functions host (`func start`), Azurite, the Durable Task Scheduler emulator, and `agent-framework-azurefunctions`.

## Azure / MAF mapping

Each registered agent is a plain `Agent` over `FoundryChatClient` (`project_endpoint` + `model` + `AzureCliCredential`) — identical whether or not it is later made durable. The lesson runs the same Foundry agent in plain (non-durable) mode as a smoke test, then shows the durable wiring for `func start`.

## Run it

`uv run tutorial/04-hosting/03_durable_extension.py` — needs Foundry creds (`az login`). Worked if optional durable lines print, then a local smoke test classifies the spam email.

---

Next: [Openai Endpoints](/blog/posts/maf-py-68-openai-endpoints.html)
