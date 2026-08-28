# Code Generation and Stubs

*The magic that makes an RPC feel like a local function call is code generation. You run a compiler over your `.proto` file and out come typed classes and methods for your language — the client stub you call and the server interface you implement. Understanding what's generated, and the boundary between generated and hand-written code, is what turns gRPC from a black box into a tool you control.*

We've written a `.proto` contract and chosen call types. Now: how does that text become callable code? The answer is the protobuf compiler, `protoc`, plus a gRPC plugin for your language. This post is about the generation step — what goes in, what comes out, and how you build on it without fighting it.

## From `.proto` to code

The compiler `protoc` reads your `.proto` file and, with the appropriate language plugin, emits source code. For a message like `User`, it generates a class or struct with typed fields, accessors, and serialization built in. For a `service`, it generates two things that mirror each other across the network:

- **A client stub** — an object with a method for each `rpc`. You call `stub.GetUser(ctx, req)` and it handles serializing the request, sending it, and deserializing the response into a typed value. This is what makes the remote call *look local*.
- **A server interface (skeleton)** — an interface/base class with one method per `rpc` for you to *implement*. The generated server code handles receiving requests, deserializing them, calling your implementation, and serializing what you return.

A typical Go generation command wires the two plugins together:

```bash
protoc --go_out=. --go-grpc_out=. \
       --go_opt=paths=source_relative \
       --go-grpc_opt=paths=source_relative \
       user/v1/user.proto
```

This produces `user.pb.go` (the message types and their serialization) and `user_grpc.pb.go` (the client stub and server interface). Every language has its equivalent plugin; the output shape is the same everywhere because it all derives from the one contract.

## The two sides of the generated boundary

The generated code defines a precise seam between "framework's job" and "your job." Seeing it clearly is what makes gRPC feel simple.

On the **server** side, you implement the generated interface — writing only the business logic:

```go
type userServer struct {
    pb.UnimplementedUserServiceServer   // forward-compatibility embed
}

func (s *userServer) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    u, err := s.db.FindUser(ctx, req.GetId())
    if err != nil {
        return nil, status.Errorf(codes.NotFound, "user %d not found", req.GetId())
    }
    return &pb.User{Id: u.ID, Name: u.Name, Email: u.Email}, nil
}
```

You receive an already-deserialized, typed `*GetUserRequest` and return a typed `*User` (or an error). Everything around it — the network, the bytes, the framing — is the framework's concern. Note the embedded `UnimplementedUserServiceServer`: that's a forward-compatibility device so that when you regenerate after adding a new method to the `.proto`, your existing server still compiles (the new method has a default "unimplemented" behavior until you write it).

On the **client** side, you connect and call:

```go
conn, _ := grpc.NewClient("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
defer conn.Close()
client := pb.NewUserServiceClient(conn)

user, err := client.GetUser(ctx, &pb.GetUserRequest{Id: 42})
```

`client.GetUser` looks like an ordinary method. Behind it, the stub serializes `GetUserRequest`, sends it over the connection, waits for the response, and hands you a typed `*User`. The RPC-as-local-call promise from post 1 is delivered right here, by generated code.

## Why generated code is the point

It's tempting to see codegen as boilerplate you tolerate. It's actually the source of gRPC's core guarantees:

- **Type safety across the network.** Because both stub and skeleton are generated from the same `.proto`, the client physically *cannot* send a request the server doesn't expect — it wouldn't compile. Whole classes of integration bugs (wrong field name, wrong type, missing field) become compile-time errors instead of runtime failures. The contract is enforced by the type system, not by hope and documentation.
- **No hand-written serialization.** You never parse or build a wire message by hand. The generated code does it correctly and efficiently every time, eliminating a notorious source of bugs.
- **Polyglot consistency, guaranteed.** Generate a Go server and Python/TypeScript/Java clients from one `.proto` and they're all guaranteed to agree, because they share a generated definition. This is *why* gRPC works so well across language boundaries.

The generated code is not overhead around the real work — it *is* the mechanism that makes cross-service, cross-language calls safe.

## Working with codegen in practice

Because generated code is derived from the `.proto`, a few habits keep it healthy:

- **Treat generated code as a build artifact.** Regenerate it from the `.proto` as part of your build rather than editing it by hand — hand edits are erased on the next generation. The `.proto` is the source; the generated files are output. (Teams differ on whether to commit generated code or generate on the fly; either way, never edit it.)
- **The `.proto` is the interface's single source of truth.** Change the contract by editing the `.proto` and regenerating, never by tweaking output. This is also why the field-numbering discipline from post 2 matters: a `.proto` change ripples through generated code on every side.
- **Manage `.proto` files deliberately.** In multi-service systems the `.proto` files are shared contracts; teams often keep them in a central repository or use tooling (like Buf) to lint them, check for breaking changes, and generate consistently. The contract deserves the same version discipline as an API, because that's exactly what it is.
- **Keep your logic separate from the generated interface.** Implement the generated server interface as a thin adapter that calls into your real business logic, so your domain code isn't entangled with gRPC types. This keeps the framework at the edge and your core testable.

## Key takeaways

- `protoc` plus a language-specific gRPC plugin turns a `.proto` file into typed code: message types with built-in serialization, a **client stub** (methods you call), and a **server interface** (methods you implement).
- The generated code defines a clean **seam**: the framework handles the network, bytes, and framing; you write only business logic — receiving typed requests and returning typed responses (or errors).
- Forward-compatibility helpers like Go's embedded `UnimplementedUserServiceServer` let your server keep compiling when new methods are added to the contract and regenerated.
- Generated code *is* gRPC's value, not boilerplate: it delivers **type safety across the network** (mismatches are compile-time errors), **no hand-written serialization**, and **guaranteed polyglot consistency** from one contract.
- Treat generated code as a **build artifact never edited by hand**, keep the **`.proto` as the single source of truth** (managed and linted like the API it is), and implement the server interface as a **thin adapter** over separate business logic.

## Further reading

- [gRPC — Core Concepts, Architecture and Lifecycle](https://grpc.io/docs/what-is-grpc/core-concepts/)
- [Protocol Buffers — Language Guide (proto3)](https://protobuf.dev/programming-guides/proto3/)
