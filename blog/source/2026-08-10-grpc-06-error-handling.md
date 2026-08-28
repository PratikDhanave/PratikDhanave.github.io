# Error Handling in gRPC

*Errors are part of every API's contract, and gRPC has a specific, structured model for them: a fixed set of status codes, a message, and optional rich details — not the HTTP status codes you know from REST. Using this model well is what makes failures actionable for callers instead of opaque. Getting it wrong turns every error into a debugging session.*

A method that only handles the happy path isn't finished. This post covers how gRPC represents failure: the status code model, how to return and interpret errors, the rich-details mechanism for structured error data, and the discipline that keeps errors useful across a distributed system.

## The status code model

Every gRPC call ends with a **status**: a numeric **code**, a human-readable **message**, and optional **details**. The codes are a fixed, well-defined set — not HTTP codes — designed specifically for RPC. The common ones you'll use constantly:

- `OK` — success (code 0).
- `INVALID_ARGUMENT` — the client sent a malformed or invalid request. The client's fault; don't retry unchanged.
- `NOT_FOUND` — the requested entity doesn't exist.
- `ALREADY_EXISTS` — a create conflicted with an existing entity.
- `PERMISSION_DENIED` — authenticated but not authorized for this action.
- `UNAUTHENTICATED` — missing or invalid credentials.
- `UNAVAILABLE` — the service is (transiently) down or unreachable; typically *retryable*.
- `DEADLINE_EXCEEDED` — the call ran out of time (post 5).
- `RESOURCE_EXHAUSTED` — a quota or rate limit was hit.
- `INTERNAL` — an unexpected server-side failure; the catch-all for bugs.

This fixed vocabulary is a feature: because the codes are standard, clients, load balancers, and libraries can react to them *automatically* — retry `UNAVAILABLE`, refresh credentials on `UNAUTHENTICATED`, surface `INVALID_ARGUMENT` to the user. A well-chosen code is machine-actionable in a way a free-text error never is.

## Returning and reading errors

On the server, you return a status by constructing an error with a code and message:

```go
func (s *userServer) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    if req.GetId() <= 0 {
        return nil, status.Errorf(codes.InvalidArgument, "id must be positive, got %d", req.GetId())
    }
    u, err := s.db.FindUser(ctx, req.GetId())
    if errors.Is(err, sql.ErrNoRows) {
        return nil, status.Errorf(codes.NotFound, "user %d not found", req.GetId())
    }
    if err != nil {
        return nil, status.Error(codes.Internal, "failed to load user")   // don't leak internals
    }
    return toProto(u), nil
}
```

On the client, you inspect the code to decide what to do:

```go
user, err := client.GetUser(ctx, req)
if err != nil {
    switch status.Code(err) {
    case codes.NotFound:
        // show "not found" to the user
    case codes.Unavailable:
        // transient — retry with backoff
    default:
        // log and surface a generic failure
    }
}
```

The pattern is: **the server picks the code that correctly classifies the failure; the client branches on the code to react appropriately.** This is the contract errors are supposed to fulfill — a shared, structured vocabulary both sides understand.

## Rich error details

A code and a string are often not enough. gRPC supports **rich error details**: structured, typed data attached to a status, using standard protobuf messages from Google's error-model (like `BadRequest` listing exactly which fields failed and why, `QuotaFailure`, `RetryInfo` telling the client how long to wait before retrying, or `ErrorInfo` with a machine-readable reason and metadata).

This is powerful for validation and for machine-driven retry logic:

```go
st := status.New(codes.InvalidArgument, "invalid CreateUser request")
st, _ = st.WithDetails(&errdetails.BadRequest{
    FieldViolations: []*errdetails.BadRequest_FieldViolation{
        {Field: "email", Description: "must be a valid email address"},
    },
})
return nil, st.Err()
```

Now the client doesn't just learn "invalid argument" — it learns *which field* and *why*, in structured form it can act on (highlight the field, show the message). Rich details let you carry the actionable specifics without inventing an ad-hoc error format in your response messages. Use them when callers benefit from machine-readable specifics; a plain code and message suffice for the rest.

## Choosing the right code

The most common error-handling mistake is sloppy code selection — returning `INTERNAL` for everything, or `OK` with an error flag buried in the response body. A few principles keep codes meaningful:

- **Client's fault vs. server's fault.** `INVALID_ARGUMENT`, `NOT_FOUND`, `PERMISSION_DENIED`, `UNAUTHENTICATED` say *the caller* needs to change something. `INTERNAL`, `UNAVAILABLE`, `DATA_LOSS` say *the server* had a problem. This distinction tells the caller whether retrying unchanged could ever help.
- **Retryable vs. terminal.** `UNAVAILABLE`, `RESOURCE_EXHAUSTED`, and `DEADLINE_EXCEEDED` are often transient and worth a retry with backoff; `INVALID_ARGUMENT` and `NOT_FOUND` will fail identically on retry. Choosing the right code is what lets automatic retry logic work correctly — a mislabeled error either retries a hopeless call or gives up on a recoverable one.
- **Don't leak internals.** Return `INTERNAL` with a generic message to the client while logging the real stack trace and details server-side. Error messages cross a trust boundary; don't expose database errors or stack traces to callers.
- **Never signal errors in the payload.** Returning `OK` with a `success: false` field defeats the entire system — clients, interceptors, and infrastructure can't see it. Use the status; that's what it's for.

## Errors as part of the contract

The through-line: **errors are part of your API contract, as much as the request and response messages.** Which codes a method can return, what they mean, and what details they carry are things callers depend on and that you should document and keep stable. A caller writes retry logic and user-facing handling against your error codes; changing them silently breaks that code just as surely as changing a field number.

Treated this way, gRPC's structured error model becomes a strength unique to RPC: a standard vocabulary that makes failures *actionable* across languages and services automatically — retryable errors get retried, auth errors trigger re-auth, validation errors reach the user with specifics — instead of every failure collapsing into an opaque 500 that someone has to investigate by hand.

## Key takeaways

- Every gRPC call ends with a **status**: a numeric **code** (from a fixed RPC-specific set, *not* HTTP codes), a message, and optional details — a standard vocabulary that clients and infrastructure can react to automatically.
- The **server picks the code** that classifies the failure; the **client branches on the code** to react (retry `UNAVAILABLE`, re-auth on `UNAUTHENTICATED`, surface `NOT_FOUND`/`INVALID_ARGUMENT`).
- **Rich error details** attach typed protobuf structures (`BadRequest` field violations, `RetryInfo`, `ErrorInfo`) so callers get machine-readable specifics — which field failed, how long to wait — without inventing an ad-hoc error format.
- Choose codes by **client-fault vs server-fault** and **retryable vs terminal** (so automatic retry logic works), **don't leak internals** (return generic `INTERNAL`, log the real error), and **never bury errors in an `OK` payload**.
- **Errors are part of the API contract** — document and keep stable which codes and details a method returns — because callers write retry and UX logic against them.

## Further reading

- [gRPC — Error handling guide](https://grpc.io/docs/guides/error/)
- [gRPC — Core Concepts, Architecture and Lifecycle](https://grpc.io/docs/what-is-grpc/core-concepts/)
