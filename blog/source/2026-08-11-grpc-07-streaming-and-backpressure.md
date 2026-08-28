# Streaming and Backpressure

*Streaming is gRPC's most powerful feature and its most misused. Sending a stream of messages sounds simple until one side produces faster than the other can consume — then, without flow control, you get unbounded memory growth and crashes. gRPC inherits HTTP/2's flow control to prevent exactly this. Understanding backpressure is the difference between streaming that scales and streaming that falls over under load.*

Post 3 introduced the four call types and promised a deeper look at streaming. Here it is. Streaming changes the programming model from values to flows, and flows raise a problem values never do: what happens when the producer outruns the consumer? This post covers how you actually write streaming handlers, and the flow-control mechanism that keeps them safe.

## Streaming is a flow, not a value

A streaming RPC gives you a *stream object* you read from or write to repeatedly, rather than a single request/response. On the server side of a server-streaming call, you loop and `Send`:

```go
func (s *userServer) ListUsers(req *pb.ListUsersRequest, stream pb.UserService_ListUsersServer) error {
    rows, err := s.db.QueryUsers(stream.Context(), req.GetPageSize())
    if err != nil {
        return status.Error(codes.Internal, "query failed")
    }
    for rows.Next() {
        u := rows.Scan()
        if err := stream.Send(toProto(u)); err != nil {   // may block for flow control
            return err   // client gone or stream broken
        }
    }
    return nil   // returning nil closes the stream successfully
}
```

On the client side, you loop and `Recv` until the stream ends:

```go
stream, _ := client.ListUsers(ctx, req)
for {
    user, err := stream.Recv()
    if err == io.EOF { break }        // server finished cleanly
    if err != nil { /* handle */ }
    process(user)
}
```

Two things to notice. Completion is a *signal*, not a return value: the server ending its handler closes the stream, and the client sees `io.EOF`. And errors are *stream events* — a broken stream or a status error surfaces from `Send`/`Recv`, not as a single call's return. Streaming asks you to think in terms of a sequence over time, with explicit start, per-message handling, and end/error events.

## The backpressure problem

Now the danger. Imagine the server in `ListUsers` can read rows from a fast database at 100,000/second, but the client processes each user slowly (writing to disk, say) at 1,000/second. What happens to the 99,000 messages per second the server produces but the client hasn't consumed?

Without any control, they'd pile up — buffered in memory somewhere between producer and consumer, growing without bound until the process runs out of memory and crashes. This is the fundamental hazard of any streaming or producer-consumer system: **a fast producer and a slow consumer, with no coordination, is an out-of-memory bug waiting to happen.** The mismatch doesn't have to be permanent; even a temporary burst where the producer gets ahead can blow up an unbounded buffer.

The solution is **backpressure**: a way for the slow consumer to signal the fast producer to *slow down* — to stop producing until the consumer has caught up. Backpressure turns "produce as fast as you can and hope" into "produce as fast as the consumer can actually take."

## How gRPC provides flow control

Here's the good news: gRPC gets backpressure largely for free from **HTTP/2 flow control**, its transport. HTTP/2 tracks, per stream, how much data the receiver has declared it's ready to accept (a *window*). The receiver advertises window space; as the sender transmits, it consumes that space; when the window is full, the sender *must stop* until the receiver processes buffered data and advertises more room.

The practical effect on your code is elegant: when the consumer isn't keeping up, the producer's `Send` call **blocks** (or, in async styles, signals not-ready) until there's window space again. In the `ListUsers` example, if the client is slow, `stream.Send` simply doesn't return immediately — it waits. The server's loop naturally paces itself to the client's consumption rate, because it can't get ahead of the flow-control window. Memory stays bounded because the unconsumed data sits in a *bounded* window, not an unbounded queue.

This is why gRPC streaming scales where a naive "fire messages as fast as possible" approach wouldn't: the transport enforces the coupling between producer and consumer speed automatically.

## Writing streams that respect flow control

Flow control protects you, but you can still defeat it. To write streaming that scales:

- **Let `Send` block — don't buffer around it.** The blocking is the backpressure working. If you "fix" a slow `Send` by spawning goroutines that queue messages into your own unbounded buffer, you've reintroduced the exact OOM problem HTTP/2 was preventing. Respect the block.
- **Produce lazily.** Generate or fetch each message *as* you're about to send it (streaming rows from a cursor, reading a file chunk at a time), not by loading everything into memory first. The point of streaming is bounded memory; materializing the whole dataset up front throws that away.
- **Honor the context and cancellation.** Check `stream.Context()` and stop producing if the client has disconnected or the deadline (post 5) passed. Streaming forever to a client that's gone is wasted work; cancellation should propagate and stop the producer promptly.
- **Handle `Send`/`Recv` errors as stream termination.** A non-EOF error means the stream is broken (client gone, network failure, deadline hit) — clean up and return; don't keep trying to send.
- **Right-size messages.** Very large individual messages undermine streaming's incremental nature and strain flow-control windows; very tiny ones add per-message overhead. Stream reasonably-sized chunks.

## When streaming pays off — and when it doesn't

Streaming is the right tool when data is genuinely large, incremental, or continuous — the cases from post 3. But it adds real complexity: flows, lifecycle events, cancellation, and flow-control awareness. Don't stream by default. If a result fits comfortably in one message and arrives all at once, unary is simpler, easier to load-balance, and easier to reason about. Reach for streaming when its benefits — bounded memory on large data, low time-to-first-result, server push, interactivity — actually apply, and when they do, lean on HTTP/2 flow control rather than fighting it. The systems that stream well are the ones that treat backpressure as a feature to cooperate with, not an inconvenience to buffer around.

## Key takeaways

- A streaming RPC is a **flow, not a value**: you loop over `Send`/`Recv`, completion is a signal (`io.EOF` / handler return, not a return value), and errors arrive as **stream events**.
- The core hazard is **a fast producer with a slow consumer**: with no coordination, unconsumed messages buffer without bound until the process runs out of memory — even a temporary burst can do it.
- **Backpressure** solves this by letting the slow consumer signal the fast producer to slow down, and gRPC gets it largely free from **HTTP/2 per-stream flow control** (a receiver window the sender can't overrun).
- In practice this means **`Send` blocks** when the consumer is behind — that blocking *is* the backpressure working, so the producer paces itself and memory stays bounded.
- Write streams that respect it: **let `Send` block** (don't buffer around it), **produce lazily**, honor context/cancellation, treat `Send`/`Recv` errors as termination, and right-size messages.
- **Don't stream by default** — unary is simpler for results that fit one message; stream only when data is genuinely large/incremental/continuous, and then cooperate with flow control rather than fighting it.

## Further reading

- [gRPC — Core Concepts, Architecture and Lifecycle](https://grpc.io/docs/what-is-grpc/core-concepts/)
- [gRPC — Introduction to gRPC](https://grpc.io/docs/what-is-grpc/introduction/)
