# A2A Transports and Core Methods

*A2A defines what agents exchange independently of how it travels, so the same operations work over JSON-RPC, gRPC, or plain REST — and the operation set is small enough to hold in your head.*

We have covered discovery, tasks, and the content model. This post is about the wire: how an A2A message actually moves between agents, and the set of operations the protocol defines. The Agent2Agent protocol (A2A) deliberately separates its abstract operations from any single transport, then provides multiple concrete bindings. This fifth post in the series covers the transports A2A supports and the core methods every binding exposes.

## Abstract operations, multiple bindings

A2A's specification is defined in a binding-independent way — the operations are described abstractly, and each transport binding must provide a functionally equivalent representation of them. That design choice is why A2A can meet teams where they are: an organization standardized on gRPC and one standardized on REST can both speak A2A without either abandoning its stack. The three supported bindings:

- **JSON-RPC 2.0 over HTTP** — the same JSON-RPC message style used by MCP; requests carry a method and params, responses carry a result or error.
- **gRPC** — a service definition with the operations as RPCs, for teams that want typed, high-performance, streaming-native transport.
- **HTTP+JSON / REST** — conventional REST, mapping operations onto HTTP verbs and URL patterns (for example, POST to send a message, GET a task by id).

An agent declares which interface(s) and binding(s) it speaks in its Agent Card, so a client knows how to reach it. Because the operations are equivalent across bindings, the *semantics* you learn here are portable — only the surface syntax differs.

## The core operations

The operation set is small and maps directly onto the concepts from earlier posts. Named as they appear in the JSON-RPC/gRPC bindings:

- **`SendMessage`** — send a message to a remote agent, initiating a task (or advancing an existing one). Returns a Task or a Message.
- **`SendStreamingMessage`** — like `SendMessage`, but the response streams real-time updates as the work progresses (covered fully in the next post).
- **`GetTask`** — retrieve a task's current state, artifacts, and history by its `id`. This is how a client polls long-running work.
- **`ListTasks`** — retrieve a filtered, paginated list of tasks.
- **`CancelTask`** — request cancellation of an in-progress task.
- **`SubscribeToTask`** — attach a streaming connection to an *existing* task to receive its updates (useful after reconnecting).
- **Push notification config operations** — `CreateTaskPushNotificationConfig`, `GetTaskPushNotificationConfig`, `ListTaskPushNotificationConfigs`, and `DeleteTaskPushNotificationConfig` manage webhooks for asynchronous updates (next post).
- **`GetExtendedAgentCard`** — retrieve the authenticated, richer Agent Card when the public card advertises one.

That is essentially the whole surface. Notice how cleanly it maps to the model built so far: you *send a message* to create a *task*, then *get*, *list*, *cancel*, or *subscribe to* that task, and manage *push configs* for async delivery. The concepts drive the API, not the other way around.

## A concrete exchange

Over the JSON-RPC binding, initiating work looks like a familiar JSON-RPC call. The client sends a message; the remote agent responds with a Task it created to track the work:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "role": "ROLE_USER",
      "parts": [ { "text": "Summarize the attached report." } ]
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "task": {
      "id": "t-77",
      "status": { "state": "SUBMITTED" }
    }
  }
}
```

The client now holds `t-77` and can call `GetTask` with that id to check progress, `CancelTask` to stop it, or subscribe for streaming updates. Over the REST binding the same interaction would be an HTTP POST to a messages endpoint returning the task as JSON; over gRPC it would be the `SendMessage` RPC returning a typed Task. Same operation, three surfaces.

## Protocol versioning and negotiation headers

A2A carries a small amount of protocol metadata alongside each request so both sides stay aligned. An **`A2A-Version`** value (for example, `1.0`) identifies the protocol version and is included with requests. An **`A2A-Extensions`** value lets a client advertise which optional extension URIs it supports, so agents can negotiate optional features without breaking base compatibility. These travel as HTTP headers in the REST and JSON-RPC bindings, or as metadata in gRPC. The practical takeaway mirrors MCP's versioning advice: honor the declared version and negotiate extensions rather than assuming a peer supports everything.

## Choosing a binding

Which transport you expose (or consume) is an engineering decision, not a semantic one:

- **JSON-RPC over HTTP** is a sensible, widely-interoperable default and pairs naturally if you already speak MCP.
- **gRPC** suits internal, high-throughput, strongly-typed environments and has first-class streaming.
- **REST** is the most universally approachable and easiest to consume from any HTTP client or existing API gateway.

Because A2A guarantees equivalent operations across bindings, you can pick per deployment and still interoperate. Expose the binding your ecosystem prefers, declare it in your Agent Card, and clients that speak it will work — the operations, and everything you learned about tasks and messages, stay the same underneath.

## Key takeaways

- A2A defines its operations abstractly and provides three equivalent bindings — JSON-RPC 2.0 over HTTP, gRPC, and HTTP+JSON/REST — so teams interoperate without changing stacks.
- The core operations are small and concept-driven: SendMessage / SendStreamingMessage to start work, GetTask / ListTasks / CancelTask / SubscribeToTask to manage it, push-notification config operations for async, and GetExtendedAgentCard.
- You send a message to create a task, then get, list, cancel, or subscribe to that task by id — the API mirrors the task/message model directly.
- The same operation has different surface syntax per binding (a JSON-RPC method, a gRPC RPC, or a REST endpoint) but identical semantics; an agent declares its binding in the Agent Card.
- Requests carry `A2A-Version` and `A2A-Extensions` metadata; honor the declared version and negotiate extensions rather than assuming full support. Choose a binding to fit your ecosystem — the semantics are portable.

## Further reading

- [A2A Protocol — official site](https://a2a-protocol.org)
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)
- [Agent2Agent (A2A) on GitHub](https://github.com/a2aproject/A2A)
