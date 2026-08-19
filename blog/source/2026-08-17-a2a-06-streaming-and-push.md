# Streaming and Push Notifications

*Long-running agent work needs a way to report progress without the client holding its breath, and A2A offers two: stream the updates live, or register a webhook and get called back.*

Delegated agent work often takes long enough that a single request/response is the wrong shape. The client wants to see progress as it happens, or it wants to fire the task and be notified later without keeping a connection alive. The Agent2Agent protocol (A2A) supports both patterns — **streaming** for live updates and **push notifications** for asynchronous callbacks. This sixth post in the series covers how each works, the update events they carry, and when to choose which.

## Why not just poll?

You *can* poll: call `GetTask` repeatedly until the state is terminal. For short tasks that is fine. But polling wastes requests, adds latency between an update happening and the client seeing it, and scales badly across many concurrent tasks. Streaming and push notifications exist so a client can learn about progress *as it occurs* — either by holding an efficient live channel or by being called back — instead of asking again and again.

An agent advertises which of these it supports in its Agent Card: `capabilities.streaming` for live updates and `capabilities.pushNotifications` for webhooks. A client checks the card and uses whichever the agent offers.

## Streaming with Server-Sent Events

Streaming is for when the client wants real-time progress over a live connection. It is initiated with `SendStreamingMessage` (to start a new task with streaming) or `SubscribeToTask` (to attach to an existing one). Over the HTTP bindings, the server streams updates using **Server-Sent Events (SSE)** — a one-way channel where the server pushes a sequence of events to the client over a single held-open HTTP response. (Over gRPC, the same is delivered via a server-streaming RPC.)

What flows over the stream is a series of `StreamResponse` objects, each carrying one of a small set of update types:

- a **Task** (the full task, e.g. the initial state),
- a **Message** (a conversational turn from the agent),
- a **`TaskStatusUpdateEvent`** — the task changed state (for example, `WORKING` → `INPUT_REQUIRED`, or reaching a terminal state),
- a **`TaskArtifactUpdateEvent`** — an artifact was produced or updated.

The stream must continue until the task reaches a terminal state (`COMPLETED`, `FAILED`, `CANCELED`, or `REJECTED`), at which point it ends. This gives the client a live, ordered view: it sees the task go to `WORKING`, watches artifacts appear via artifact-update events, notices if the task pauses for `INPUT_REQUIRED`, and knows the moment it completes. Streaming is the right tool for interactive experiences — a user watching an agent work in something close to real time.

## Push notifications with webhooks

Streaming assumes the client can hold a connection open. Often it cannot, or should not: a task that runs for hours, a client that is a serverless function, a workflow that should not tie up a socket. For these, A2A offers **push notifications** — the remote agent calls the client back over a webhook when something happens.

The flow:

1. The client registers a webhook with `CreateTaskPushNotificationConfig`, providing a URL the agent should call and optional authentication for it.
2. As the task progresses, the remote agent sends HTTP POST requests to that URL, carrying `StreamResponse` payloads — the same `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent` types as streaming.
3. The client's webhook receives these asynchronously, with no connection held open in between.
4. The client can inspect, update, list, or delete its push configs with `GetTaskPushNotificationConfig`, `ListTaskPushNotificationConfigs`, and `DeleteTaskPushNotificationConfig`.

Push notifications decouple the client's availability from the task's duration entirely. The client kicks off the work, registers where to be reached, and can go away — even shut down — and still be notified when the task changes state or produces an artifact. This is the pattern for genuinely long-running, asynchronous delegation.

## Securing the callback

Push notifications introduce a security concern streaming does not: the agent is now making an inbound HTTP call to a URL the client supplied, and the client is receiving calls it must trust. Two obligations follow. The client should register the webhook with authentication so the agent can prove who it is, and — critically — the client's webhook endpoint must **verify the authenticity** of incoming notifications before acting on them, rather than trusting any POST that arrives. An unauthenticated webhook is an open door; treat inbound push notifications as untrusted until verified. The general A2A authentication model, which the next post covers, applies here on the callback path too.

## Choosing between them

The decision is about connection lifetime and interactivity:

- **Use streaming** when the client can hold a connection and wants live, ordered progress — interactive UIs, a user watching an agent work, short-to-medium tasks.
- **Use push notifications** when the task may run long, the client cannot or should not hold a connection, or the architecture is event-driven and serverless — fire-and-be-notified delegation.

Some systems use both: stream while a user is actively watching, and fall back to push notifications for work that outlives the session. Both deliver the same update events, so the task model you learned earlier is exactly what surfaces through either channel — only the delivery mechanism differs.

## Key takeaways

- Polling with `GetTask` works for short tasks, but streaming and push notifications let a client learn about progress as it happens instead of asking repeatedly.
- Streaming (via `SendStreamingMessage`/`SubscribeToTask`) delivers a live sequence of `StreamResponse` events over SSE — Task, Message, `TaskStatusUpdateEvent`, `TaskArtifactUpdateEvent` — until the task reaches a terminal state.
- Push notifications call the client back over a registered webhook with the same event payloads, decoupling the client's availability from the task's duration — ideal for long-running, async work.
- Manage webhooks with the push-notification config operations; an agent advertises `streaming` and `pushNotifications` support in its Agent Card.
- Secure the callback path: register webhooks with authentication and verify the authenticity of inbound notifications before acting; choose streaming for interactive/live and push for long-running/event-driven.

## Further reading

- [A2A Protocol — official site](https://a2a-protocol.org)
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)
- [Agent2Agent (A2A) on GitHub](https://github.com/a2aproject/A2A)
