# Deadlines, Metadata, and Interceptors

*A production RPC is more than a request and a response. Every call should carry a deadline so it can't hang forever, metadata for cross-cutting concerns like auth and tracing, and it should pass through interceptors that apply logging, authentication, and metrics uniformly. These three mechanisms are how a gRPC system becomes observable, secure, and resilient — and they're the pieces beginners most often skip.*

So far we can define, generate, and call RPCs. This post is about the machinery that turns a working call into a *production-grade* one: bounding it in time (deadlines), attaching side-channel data (metadata), and wrapping every call in reusable cross-cutting logic (interceptors). Skip these and your first serious outage will teach them to you the hard way.

## Deadlines: never wait forever

The single most important production habit in gRPC is setting a **deadline** on every call. A deadline says "this call must complete by time T; after that, give up." Without one, a client can block indefinitely waiting on a slow or hung server — and in a chain of services, one stuck call can exhaust connections and cascade into a system-wide stall.

In gRPC, deadlines are set via the context and, crucially, **propagate across service boundaries**:

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

user, err := client.GetUser(ctx, &pb.GetUserRequest{Id: 42})
if err != nil {
    if status.Code(err) == codes.DeadlineExceeded {
        // the call ran out of time
    }
}
```

Two things make gRPC deadlines special. First, they're *absolute*, not per-hop timeouts — a deadline is a point in time, and it travels with the call. Second, they **propagate**: if service A calls B with a 2-second deadline and B calls C, C sees the *remaining* time. If the deadline passes, the whole chain can stop wasting work on a result nobody will use anymore. This is deadline propagation, and it's what keeps a microservice mesh from doing pointless work after the client has already given up.

Prefer **deadlines** (an absolute time by which to finish) over **timeouts** (a per-call duration) conceptually, because the deadline is the thing that should hold across an entire request's fan-out. Set it at the edge based on how long the *user* will wait, and let it flow down.

## Metadata: the side channel

**Metadata** is key-value data attached to a call *outside* the request and response messages — gRPC's equivalent of HTTP headers. It carries information *about* the call rather than the call's payload:

- **Authentication** — bearer tokens, API keys (`authorization: Bearer ...`).
- **Tracing and correlation** — a request/trace ID so one logical operation can be followed across many services.
- **Routing and context** — tenant IDs, locale, client version, feature flags.

The client attaches outgoing metadata to the context; the server reads incoming metadata from it:

```go
// client: attach a token
ctx := metadata.AppendToOutgoingContext(ctx, "authorization", "Bearer "+token)

// server: read it
md, _ := metadata.FromIncomingContext(ctx)
tokens := md.Get("authorization")
```

The reason metadata is separate from the message is *separation of concerns*: auth, tracing, and routing are cross-cutting infrastructure that shouldn't pollute every request message's schema. Putting a trace ID in metadata means you don't add a `trace_id` field to all thousand of your message types. Metadata is where the plumbing lives so your business messages stay clean.

## Interceptors: cross-cutting logic in one place

You could read the auth token and log timing inside every single RPC method — and you'd repeat that code hundreds of times and forget it somewhere. **Interceptors** solve this: they're middleware that wraps RPC calls, running your logic before and/or after the actual handler, uniformly across every method. If you've used HTTP middleware, it's the same idea for gRPC.

Interceptors exist on both sides:

- **Server interceptors** wrap incoming calls — the place for authentication, authorization, request logging, metrics, panic recovery, and rate limiting. Auth in an interceptor means *every* method is protected by default, not just the ones a developer remembered to guard.
- **Client interceptors** wrap outgoing calls — the place to inject auth tokens, add tracing metadata, retry on transient failures, and record client-side latency.

A minimal server logging interceptor in Go:

```go
func loggingInterceptor(ctx context.Context, req any, info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler) (any, error) {
    start := time.Now()
    resp, err := handler(ctx, req)         // call the actual RPC
    log.Printf("method=%s dur=%s code=%s", info.FullMethod, time.Since(start), status.Code(err))
    return resp, err
}
// register: grpc.NewServer(grpc.ChainUnaryInterceptor(loggingInterceptor, authInterceptor))
```

You register interceptors once when constructing the server or client, and they apply to all calls. They can be *chained*, so each concern (logging, then auth, then metrics) is its own small, composable, independently-testable interceptor. There are separate interceptor types for unary and streaming calls, but the principle is identical.

## Why these three go together

Deadlines, metadata, and interceptors are the three mechanisms that turn RPC into infrastructure, and they reinforce each other. Interceptors are where you *enforce* the other two uniformly: a server interceptor reads the auth token from **metadata** and rejects unauthenticated calls; a client interceptor injects a trace ID into **metadata** and ensures a **deadline** is always set. Together they give you the cross-cutting concerns every real system needs — observability (logging, tracing, metrics), security (auth on every call), and resilience (deadlines that prevent hangs and cascades) — applied consistently rather than sprinkled by hand.

The lesson beginners most need: a bare `GetUser` call that works in a demo is not production-ready. Production readiness is the deadline that caps its latency, the metadata that authenticates and traces it, and the interceptors that guarantee those apply to every call in the system. Build these in from the start and your gRPC services are observable and safe by default; bolt them on later and you'll be retrofitting during an incident.

## Key takeaways

- **Set a deadline on every call.** gRPC deadlines are absolute points in time that **propagate across service boundaries** (downstream services see the remaining time), preventing indefinite hangs and stopping a whole call chain from doing work nobody will use — the most important production habit.
- **Metadata** is key-value data attached *outside* the request/response messages (like HTTP headers) for cross-cutting concerns — auth tokens, trace/correlation IDs, tenant/routing info — keeping infrastructure data out of your business message schemas.
- **Interceptors** are middleware that wrap RPC calls uniformly: **server** interceptors handle auth, logging, metrics, and panic recovery for every method; **client** interceptors inject tokens/tracing and add retries — registered once, applied everywhere, and chainable.
- The three reinforce each other: interceptors are where you **enforce** deadlines and read/inject metadata consistently, delivering observability, security, and resilience by default.
- A bare call that works in a demo isn't production-ready — production readiness *is* the deadline, the metadata, and the interceptors; build them in from the start rather than retrofitting during an outage.

## Further reading

- [gRPC — Core Concepts: Deadlines and Cancellation](https://grpc.io/docs/what-is-grpc/core-concepts/)
- [gRPC — Authentication guide](https://grpc.io/docs/guides/auth/)
