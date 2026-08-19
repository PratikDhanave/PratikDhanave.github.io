# Tasks and the Task Lifecycle

*Delegating real work between agents is rarely a quick round trip, so A2A makes the task a first-class object with an explicit lifecycle that survives long-running, interruptible, asynchronous collaboration.*

When one agent hands work to another, that work may take seconds or hours, may need clarification partway through, may require authorization, and may ultimately succeed or fail. A protocol that only modeled instant request/response could not express any of that. The Agent2Agent protocol (A2A) instead makes the **Task** a first-class object with a defined lifecycle. This third post in the series covers the Task, its states, and how the lifecycle enables durable, long-running collaboration between agents.

## The Task as the unit of work

In A2A, when a client agent asks a remote agent to do something non-trivial, the remote agent creates a **Task** to represent that unit of work. The Task is the handle both sides refer to for the life of the request. Its key fields:

- `id` — a unique identifier the client uses to check on, stream, or cancel the work.
- `contextId` — groups related tasks into a larger conversation or workflow, so multiple exchanges can share context.
- `status` — a `TaskStatus` capturing the current state, an optional message, and a timestamp.
- `artifacts` — the outputs the task produces (covered in the next post).
- `history` — the messages exchanged as the task progressed.
- `metadata` — additional structured data.

Because the Task has a stable `id`, work becomes addressable: the client can walk away, come back, and ask "what is the state of task X?" without holding a connection open. That single property — a task you can name and revisit — is what makes asynchronous, long-running agent collaboration possible.

## The lifecycle states

A Task moves through an explicit set of states. A2A names them precisely, and understanding the categories matters more than memorizing the strings:

- **`SUBMITTED`** — the task has been received and accepted but work has not started.
- **`WORKING`** — the remote agent is actively processing.
- **`INPUT_REQUIRED`** — the agent needs more information from the client to continue; the task is paused waiting on input. This is an *interrupted* (non-terminal) state.
- **`AUTH_REQUIRED`** — the agent needs authentication or authorization before it can proceed; also interrupted, waiting on the client.
- **`COMPLETED`** — the task finished successfully. **Terminal.**
- **`FAILED`** — the task could not be completed. **Terminal.**
- **`CANCELED`** — the task was canceled, typically by the client. **Terminal.**
- **`REJECTED`** — the agent declined the task. **Terminal.**

The three categories are the thing to hold onto: **active** (submitted, working), **interrupted** (input-required, auth-required — paused, waiting on the client to unblock it), and **terminal** (completed, failed, canceled, rejected — the task is over). Every task ends in exactly one terminal state, and a well-behaved client drives interrupted tasks back to active by supplying what was asked for.

## Why interrupted states matter

The interrupted states are what separate A2A from a fire-and-forget RPC. Real delegated work frequently needs a human-in-the-loop moment or a clarification: a travel agent needs to know your budget, a document agent needs a credential to reach a private source. Rather than fail, the task moves to `INPUT_REQUIRED` or `AUTH_REQUIRED` and waits. The client sees the state, provides the missing input or auth, and the task resumes as `WORKING`. This models the back-and-forth of genuine collaboration, where the delegate can ask the delegator for what it needs and pick up where it left off.

## Checking on and canceling tasks

Because tasks are addressable by `id`, A2A provides operations to manage them over their lifetime (the exact method names are covered in the transports post):

- **Get a task** — retrieve its current `status`, `artifacts`, and `history` by `id`. This is how a client polls a long-running task without holding a stream open.
- **List tasks** — retrieve a filtered, paginated set of tasks, useful for dashboards or resuming after a restart.
- **Cancel a task** — request cancellation of an in-progress task, moving it toward the `CANCELED` terminal state.

For real-time progress rather than polling, A2A offers streaming and push notifications, which are the subject of a later post. The point here is that the Task's stable identity plus its explicit states give a client full control over work it has delegated: it can start it, watch it, feed it, cancel it, and know unambiguously when it is done.

## Context and multi-turn workflows

The `contextId` deserves a note because it enables workflows larger than a single task. Related tasks — several delegations that are part of one overarching goal, or a multi-turn conversation with a remote agent — can share a `contextId`, letting the remote agent maintain continuity across them. Where the `id` addresses one unit of work, the `contextId` threads many units into a coherent collaboration. This is how a client agent can conduct an extended, stateful engagement with a remote agent rather than a series of disconnected calls.

## Key takeaways

- A2A makes the Task a first-class object with a stable `id`, so delegated work is addressable and can be revisited without holding a connection open — the basis for long-running, async collaboration.
- A Task carries `id`, `contextId`, `status`, `artifacts`, `history`, and `metadata`; its `status` records the current state, a message, and a timestamp.
- Lifecycle states fall into three groups: active (submitted, working), interrupted (input-required, auth-required — paused on the client), and terminal (completed, failed, canceled, rejected); every task ends in exactly one terminal state.
- Interrupted states model real collaboration: the delegate can pause to ask for input or authentication and resume, instead of failing.
- Tasks can be fetched, listed, and canceled by `id`, and a shared `contextId` threads related tasks into larger multi-turn workflows.

## Further reading

- [A2A Protocol — official site](https://a2a-protocol.org)
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)
- [Agent2Agent (A2A) on GitHub](https://github.com/a2aproject/A2A)
