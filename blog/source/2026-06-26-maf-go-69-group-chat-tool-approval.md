# group_chat_tool_approval · Human-in-the-loop inside a group chat

*How a multi-agent group chat pauses to ask a human for approval before one gated tool is allowed to run.*

---

## What this lesson demonstrates

Two agents — a **QAEngineer** and a **DevOpsEngineer** — collaborate in a *group chat workflow* to coordinate a production deployment. A custom `GroupChatManager` scripts the turn order (QA runs the tests, then DevOps deploys) and decides when the chat is done. The DevOps engineer owns a `DeployToProduction` tool wrapped with `tool.ApprovalRequiredFunc` — so the workflow does **not** just call it. It pauses, emits a `RequestInfoEvent` carrying a `ToolApprovalRequestContent`, and waits for `main()` to send a response back before the deployment tool executes. That is the human-in-the-loop pattern applied *inside* a multi-agent orchestration.

## The gated tool and the manager

The whole workflow is factored into `buildWorkflow(...)` so the offline test builds it with a fake credential. Approval is a property of the *tool*, not the agent:

```go
devops = newDeploymentAgent(endpoint, model, cred, mw,
	"DevOpsEngineer",
	"DevOps engineer who handles deployments",
	"You are a DevOps engineer... Call CheckStagingStatus, then CreateRollbackPlan, then DeployToProduction - in that order...",
	checkStagingStatusTool,
	createRollbackPlanTool,
	tool.ApprovalRequiredFunc(deployToProductionTool),
)
```

Only `DeployToProduction` is wrapped — the other tools (`RunTests`, `CheckStagingStatus`, `CreateRollbackPlan`) run without interruption. The agents are handed to `agentworkflow.NewGroupChatWorkflowBuilder(newDeploymentGroupChatManager, qa, devops)`.

## What to notice

- **The manager is the brain of the group chat.** `newDeploymentGroupChatManager` is a `GroupChatManagerFactory`: given the workflow's agents it returns a `agentworkflow.GroupChatManager` whose `SelectNextAgent`, `ShouldTerminate`, and `Reset` fields point at plain methods. `SelectNextAgent` scripts QA-then-DevOps; `ShouldTerminate` stops once a deployment summary appears, with a hard cap at four turns.
- **The pause surfaces as an event, resolved out-of-band.** The runtime emits a `workflow.RequestInfoEvent`; `approveToolRequest` reads the `*message.ToolApprovalRequestContent` via `workflow.PortableValueAs`, builds a response with `approvalRequest.CreateResponse(true, …)`, and calls `run.SendResponse`. Swap the auto-approve for a real prompt and you have a genuine human gate.
- **The run is kicked with a `TurnToken`.** After `RunStreaming`, `main` sends `workflow.TurnToken{EmitEvents: &emitEvents}` so the group chat starts emitting per-agent updates.

## How it maps to the Agent Framework Go SDK

`agentworkflow` gives you group-chat orchestration on top of the workflow engine; `tool.ApprovalRequiredFunc` is the SDK primitive that turns any tool into an approval-gated one; and `RequestInfoEvent` / `SendResponse` are the same external-request machinery used across the Foundry human-in-the-loop lessons — here applied to a tool call rather than a raw prompt.

## Run it

```bash
go test ./tutorial/03-workflows/agents/group_chat_tool_approval            # offline
AF_LIVE=1 go test ./tutorial/03-workflows/agents/group_chat_tool_approval  # + live (needs az login)
go run  ./tutorial/03-workflows/agents/group_chat_tool_approval            # needs Foundry
```

The offline tests pin the wiring and the manager's turn/termination logic; the live workflow call is gated behind `AF_LIVE=1`.

---

Next: [workflow_as_an_agent · A Workflow, Wrapped as One Agent](/blog/posts/maf-go-70-workflow-as-an-agent.html)
