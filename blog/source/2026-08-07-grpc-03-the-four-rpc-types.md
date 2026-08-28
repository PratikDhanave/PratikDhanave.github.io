# The Four Types of RPC

*gRPC isn't just request-and-response. Because it rides on HTTP/2, it offers four distinct call patterns: unary, server streaming, client streaming, and bidirectional streaming. Each fits a different shape of problem, and choosing the right one is a real design decision — it changes how your API feels, how it performs, and how it handles data that arrives over time rather than all at once.*

The `.proto` `stream` keyword hinted at this: a gRPC method can stream on the request side, the response side, both, or neither. That yields four call types. Most developers only ever use the first and miss that the other three exist — and miss the problems they elegantly solve. This post covers all four, when to use each, and how streaming changes your thinking.

## Unary: the familiar one

**Unary RPC** is one request, one response — the classic function call, and the direct analog of a REST request:

```proto
rpc GetUser (GetUserRequest) returns (User);
```

The client sends a single `GetUserRequest`, the server does its work, and sends back a single `User`. This covers the vast majority of API calls: fetch a record, submit a form, run a query, perform an action. It's simple, easy to reason about, and where you should start. If a plain request→response models your operation, use unary — don't reach for streaming to look sophisticated.

The other three types exist for cases where "one message each way" is a poor fit — where data is *large*, *incremental*, or *continuous*.

## Server streaming: one request, many responses

**Server streaming** sends one request and gets back a *stream* of responses:

```proto
rpc ListUsers (ListUsersRequest) returns (stream User);
```

The client asks once; the server sends many messages over a single open call, then signals completion. This shines when the response is naturally a *sequence* or is too large to send at once:

- **Large result sets** — instead of returning a 100,000-item list in one giant message (memory-heavy, high latency-to-first-byte), the server streams items as it produces them. The client processes each as it arrives.
- **Server-pushed updates** — a subscription: "send me events as they happen." The server keeps the stream open and pushes new messages when there's something to say.
- **Progressive results** — anything where getting the first results quickly matters, like search hits or a model streaming tokens.

The win is *incremental delivery*: work starts flowing immediately, memory stays bounded, and the client isn't blocked waiting for a complete answer.

## Client streaming: many requests, one response

**Client streaming** is the mirror image — the client sends a stream, the server replies once at the end:

```proto
rpc UploadLogs (stream LogEntry) returns (UploadSummary);
```

The client sends many messages over one call, then closes its side; the server processes them (often incrementally) and returns a single summary. This fits *aggregation* and *upload* patterns:

- **Uploading large data** in chunks — a file or a big dataset streamed as pieces rather than one enormous message.
- **Streaming ingestion** — sending a batch of records, metrics, or events for the server to accumulate and then acknowledge with one result.
- **Incremental computation** — the server folds each incoming message into a running result and returns the final answer when the client is done.

Again the benefit is bounded memory and immediate processing: neither side has to hold the entire dataset in one message.

## Bidirectional streaming: many both ways

**Bidirectional streaming** opens a stream in *both* directions at once, independently:

```proto
rpc Chat (stream ChatMessage) returns (stream ChatMessage);
```

Client and server each send messages whenever they want, in any interleaving, over one long-lived call. The two streams are *independent* — the server doesn't have to wait for the client to finish, and vice versa. This enables genuinely interactive, real-time communication:

- **Chat and messaging** — both sides send as they go.
- **Real-time collaboration** — live cursors, edits, presence.
- **Interactive sessions** — a back-and-forth protocol, like a voice assistant streaming audio in while streaming responses out, or a game server exchanging state with a client.

Bidirectional streaming is the most powerful and the most complex: you're managing two concurrent flows and their coordination. Reach for it only when the interaction is genuinely full-duplex; if one side merely responds to the other in lockstep, a simpler type will do.

## Choosing the right type

The decision comes down to *how data flows in time* on each side:

- **One value each way?** → **Unary.** The default; use it unless you have a reason not to.
- **One question, a sequence or large/streamed answer?** → **Server streaming.**
- **A sequence or large/streamed input, one answer?** → **Client streaming.**
- **Continuous, independent, interactive flow both ways?** → **Bidirectional.**

Ask two questions of each side of the call: *is there one message or many?* and *do they all exist at once, or arrive over time?* When both sides are single, go unary. When either side is a sequence or too big for one message, stream that side. When both sides are continuous and interactive, go bidirectional.

## Streaming changes the mental model

The deeper shift streaming brings is from *values* to *flows*. A unary call is a value you request and receive. A stream is a *sequence over time* you consume message by message — closer to an iterator or a channel than a return value. This unlocks patterns impossible with request-response (server push, incremental upload, live interaction) but demands you think about the temporal dimension: messages arrive over time, order matters within a stream, and you handle completion and errors as stream events rather than a single return. It also raises **flow control** — what happens when one side produces faster than the other consumes — which HTTP/2 handles and we'll examine in the dedicated streaming post. For now, the key is that gRPC gives you four shapes, and matching the shape to your data's flow is a real and consequential design choice.

## Key takeaways

- gRPC offers **four call types** because it rides on HTTP/2: **unary** (one↔one), **server streaming** (one→many), **client streaming** (many→one), and **bidirectional** (many↔many).
- **Unary** is the request-response default and fits the vast majority of operations — start here and only stream when one-message-each-way is a genuinely poor fit.
- **Server streaming** delivers large result sets, server-pushed updates/subscriptions, and progressive results incrementally, with bounded memory and fast time-to-first-result.
- **Client streaming** handles chunked uploads, streaming ingestion, and incremental aggregation — the client sends many messages, the server returns one summary.
- **Bidirectional streaming** enables real-time, full-duplex interaction (chat, collaboration, interactive sessions) via two independent concurrent streams — the most powerful and complex type.
- Choose by asking, for each side, **one message or many?** and **all at once or over time?** — streaming shifts your model from *values* to *flows over time*, unlocking push/upload/interactive patterns and raising flow-control concerns.

## Further reading

- [gRPC — Core Concepts, Architecture and Lifecycle](https://grpc.io/docs/what-is-grpc/core-concepts/)
- [gRPC — Introduction to gRPC](https://grpc.io/docs/what-is-grpc/introduction/)
