# Beyond REST: GraphQL and gRPC

*When REST is the wrong shape for the problem, GraphQL and gRPC each fix a different pain — and each buys that fix with a new cost you have to design around.*

---

REST is a fine default. A resource has a URL, HTTP verbs map to operations, responses cache for free, and every tool in the ecosystem already speaks it. But "fine default" is not "always right." Two failure modes push teams past REST. The first is *shape mismatch*: a mobile screen needs three fields from five resources, and REST forces it to either make five round trips or download five full documents to use fifteen fields. The second is *cost*: an internal service calling another internal service a million times an hour doesn't want to parse JSON text and re-open a TCP connection each time.

GraphQL answers the first problem by letting the client describe the exact shape it wants. gRPC answers the second by making the wire format binary, the transport multiplexed, and the client code generated. Neither is "better than REST" — they are differently shaped tools, and the interesting part is the trade-offs each one drags along. This post walks through both from primary sources, then gives a decision framework you can actually apply.

---

## The problem REST leaves on the table

Earlier in this series we hit over-fetching and under-fetching. A `GET /users/42` returns the whole user record even when the caller only wanted the display name. A profile screen that shows a user, their latest three posts, and each post's comment count needs `GET /users/42`, then `GET /users/42/posts?limit=3`, then a comment-count call per post — the classic *under-fetch, then loop*. You can paper over this with custom endpoints (`GET /users/42/profile-card`), but every new screen wants a slightly different bundle, and you end up with a drawer full of one-off endpoints that nobody dares delete.

The root issue is that in REST the **server decides the response shape**. The two alternatives below move that decision — GraphQL hands shape control to the client, and gRPC fixes the shape in a shared contract compiled into both sides.

---

## GraphQL: the client selects the fields

GraphQL, originally published by Facebook and now stewarded by the GraphQL Foundation, is a query language for APIs plus a runtime that resolves those queries. Instead of many URLs, there is usually **one endpoint** (conventionally `/graphql`), and instead of the server dictating the payload, the client sends a query naming exactly the fields it wants. The server returns a JSON object mirroring the query's shape — no more, no less.

At the center is a **typed schema**. The schema is the contract: it declares the types, their fields, and the operations clients may perform. Because it is machine-readable, it powers introspection, editor autocomplete, and validation before a query ever runs.

```graphql
type User {
  id: ID!
  displayName: String!
  posts(limit: Int = 5): [Post!]!
}

type Post {
  id: ID!
  title: String!
  commentCount: Int!
}

type Query {
  user(id: ID!): User
}
```

A client that wants exactly the profile-card data sends one query:

```graphql
query ProfileCard {
  user(id: "42") {
    displayName
    posts(limit: 3) {
      title
      commentCount
    }
  }
}
```

One request, one round trip, and the response contains precisely those fields. The over/under-fetching problem from post 3 evaporates: the client asks for the graph shape it needs, and adding a new screen means writing a new query, not a new endpoint.

GraphQL defines three operation types. **Queries** read data. **Mutations** write it, and run their top-level fields in series so ordering is predictable. **Subscriptions** stream updates to the client over a long-lived transport (usually WebSockets) for live data like notifications or chat. All three are described in the same schema, so the contract stays in one place.

```graphql
type Mutation {
  publishPost(title: String!, body: String!): Post!
}

type Subscription {
  postPublished: Post!
}
```

### Where GraphQL sends the bill

Flexibility does not delete work — it moves it. GraphQL relocates cost from the client to the server, and if you don't design for that, the server pays interest.

The first cost is the **N+1 resolver problem**. Each field can have a *resolver* — a function that fetches that field's data. When a query asks for a list of users and then each user's team, the naive execution runs one query for the user list, then one query per user for the team: 1 + N database hits. This is invisible in the schema and only shows up under load. The standard fix is **DataLoader**, a batching-and-caching utility (open-sourced by Facebook) that collects the individual per-item loads within a single tick of the event loop, dispatches them as one batched call (`WHERE id IN (...)`), and caches results within the request. It turns N+1 into 1+1, but you have to actually wire it in — nothing forces you to.

```text
Naive resolvers:  1 query for users  +  N queries (one team per user)   = N+1
With DataLoader:  1 query for users  +  1 batched query for all teams   = 2
```

**The gotcha:** GraphQL's flexibility moves cost to the server, and the N+1 resolver problem plus unbounded query complexity are real performance and denial-of-service surfaces. A single well-formed query can ask for deeply nested, cyclic relationships (`user → posts → author → posts → author …`) and force the server to do enormous work. You cannot rely on clients to be polite. Defend the endpoint with **query depth limits**, **complexity scoring** (assign a cost to each field and reject queries over a budget), **pagination on list fields**, and DataLoader batching on every resolver that touches a data store. Treat the query itself as untrusted input.

The second cost is **caching**. REST gets HTTP caching almost for free: each resource has a URL, and CDNs, browsers, and proxies cache `GET` responses by that URL with `ETag` and `Cache-Control`. GraphQL typically sends every operation as a `POST` to one URL, so URL-based HTTP caching does not apply. You have to rebuild caching at other layers — a normalized client-side cache (Apollo Client, Relay, urql), persisted queries so a query becomes a cacheable identifier, or response caching keyed on the query plus variables. It's solvable, but it is now your problem instead of the network's.

**The gotcha:** GraphQL gives up HTTP's free caching. Because everything is a `POST` to a single endpoint, the shared-cache infrastructure that makes REST cheap at the edge doesn't see your responses. Budget for a client cache and/or persisted queries from day one rather than discovering the missing cache layer in production.

The third cost is **authorization**. In REST, access control often lives at the endpoint: this route requires this scope. In GraphQL a single query can straddle many types and fields, so authorization has to happen **per field** — the resolver for `User.salary` must independently check that the caller may see salaries, even if `User.displayName` is public. Centralizing auth at "the endpoint" is not enough, because one endpoint exposes the whole graph.

---

## gRPC: contract-first, binary, and fast

gRPC is a high-performance RPC framework from Google. Where GraphQL optimizes for flexible clients, gRPC optimizes for efficient, strongly-typed service-to-service calls. It rests on two pillars: **Protocol Buffers** (Protobuf) as the interface definition language and serialization format, and **HTTP/2** as the transport.

You start with a `.proto` file — the contract comes *first*, before any implementation. It defines messages (the data) and services (the callable methods). A compiler (`protoc`) then generates typed client and server code in your language of choice — Go, Java, Python, C++, C#, and many more — so both sides share one source of truth.

```protobuf
syntax = "proto3";
package catalog.v1;

message GetProductRequest {
  string product_id = 1;
}

message Product {
  string id = 1;
  string name = 2;
  int64 price_cents = 3;
  repeated string tags = 4;
}

service Catalog {
  rpc GetProduct(GetProductRequest) returns (Product);
  rpc ListProducts(ListProductsRequest) returns (stream Product);
}
```

Those numbered field tags (`= 1`, `= 2`) are the heart of Protobuf's wire format: the binary encoding carries the tag number, not the field name, which is why payloads are compact and why you must never renumber or reuse a tag on an existing message. The generated `Catalog` client exposes `GetProduct(...)` as an ordinary typed method call — no hand-written URL building, no manual JSON parsing.

Because gRPC runs on HTTP/2, it gets multiplexed streams over one connection, header compression, and — most importantly — first-class **streaming**. There are four call types:

| Call type | Shape | Example |
|---|---|---|
| Unary | one request → one response | fetch a product |
| Server streaming | one request → stream of responses | subscribe to a price feed |
| Client streaming | stream of requests → one response | upload metrics in chunks |
| Bidirectional streaming | stream ↔ stream | a live chat or telemetry link |

The combination — binary Protobuf payloads, HTTP/2 multiplexing, generated typed stubs, and streaming — is why gRPC shines for **internal, service-to-service** communication where latency and throughput matter and both ends are under your control.

### Where gRPC sends the bill

**The gotcha:** gRPC is not browser-native. Browsers do not expose the low-level HTTP/2 control that the gRPC protocol needs, so a web page cannot call a gRPC service directly. You reach it through **grpc-web**, which speaks a browser-compatible variant and requires a proxy (such as Envoy) to translate to real gRPC. If your primary clients are browsers, this friction is a real cost — and often the sign that a REST or GraphQL edge in front of your gRPC core is the better shape.

The second cost is **debuggability**. REST and GraphQL send human-readable text you can eyeball in browser dev tools or `curl`. Protobuf is binary — you cannot read a captured payload without the corresponding `.proto` to decode it. Tooling exists (`grpcurl`, reflection, server logging), but the "just look at the network tab" ergonomics are gone.

The third cost is **coupling to the contract**. The generated code is only as good as the `.proto`, and every client is compiled against a specific version of it. Protobuf has clear rules for evolving safely — add new fields with new tag numbers, never reuse or renumber existing tags, reserve retired field numbers — but the discipline is on you. Break those rules and you silently corrupt data across services that were compiled against the old shape.

---

## A decision framework

Reach for the tool that matches your *client needs* and *network shape*, not the one that sounds most modern.

**Use REST when** the domain is resource-oriented, the API is public or partner-facing, and cacheability matters. REST's URL-per-resource model gets you free HTTP caching at the edge, the widest possible tooling and client support, and the lowest learning curve for third-party developers. For a public API, boring is a feature.

**Use GraphQL when** many different clients need different slices of the same data, or when one request must aggregate several backends. This is the classic **Backend-for-Frontend (BFF)** and mobile scenario: a phone app on a slow network wants exactly its fields in one round trip, and next month's screen wants a different shape without a server deploy. GraphQL trades HTTP caching and per-field auth complexity for that client flexibility — worth it when client shapes vary a lot, wasteful when they don't.

**Use gRPC when** the caller and callee are both services you own, latency and throughput dominate, or you need streaming. Internal microservice meshes, low-latency data planes, and long-lived streaming links are its home turf. You trade browser-friendliness and easy debugging for compact, fast, strongly-typed calls.

These are not mutually exclusive. A common mature architecture uses **gRPC between internal services**, a **GraphQL or REST BFF at the edge** for varied external clients, and **REST** for the truly public, cacheable, partner-facing surface. The transport is a per-boundary decision, not a company-wide religion.

**The gotcha:** "GraphQL because it's modern" or "gRPC because it's fast" is not a reason. Adopting GraphQL for a single first-party web client that fetches fixed shapes just costs you HTTP caching for nothing. Adopting gRPC for a public, browser-first API buys you a proxy and a debugging headache for throughput you didn't need. Pick by the two questions that actually discriminate: *who are the clients, and what does the network between them look like?*

---

## Key takeaways

- **REST's limitation is server-decided response shape**, which produces over- and under-fetching. GraphQL and gRPC each relocate that decision differently.
- **GraphQL puts field selection in the client's hands** via one endpoint and a typed schema contract, with queries, mutations, and subscriptions all described in that schema.
- **GraphQL's costs are server-side**: the N+1 resolver problem (mitigated with DataLoader batching), lost HTTP caching (everything is `POST` to one URL), query-complexity/depth limits as a DoS defense, and per-field authorization.
- **gRPC is contract-first**: a Protobuf `.proto` compiles to typed clients and servers across languages, runs on HTTP/2, and supports four streaming modes — ideal for internal, low-latency, high-throughput service-to-service calls.
- **gRPC's costs are edge-side**: not browser-native without grpc-web plus a proxy, binary payloads are harder to debug, and clients are tightly coupled to the `.proto` version.
- **Choose by client needs and network shape**: REST for public/cacheable/resource-oriented, GraphQL for varied clients and aggregation (BFF, mobile), gRPC for internal microservices, streaming, and performance. Modernity is not a selection criterion.

---

## Further reading

- [GraphQL — official site and learning docs](https://graphql.org/learn/)
- [GraphQL Specification](https://spec.graphql.org/)
- [gRPC — official documentation](https://grpc.io/docs/)
- [gRPC concepts: service definitions and the four RPC types](https://grpc.io/docs/what-is-grpc/core-concepts/)
- [Protocol Buffers documentation](https://protobuf.dev/)
- [Protobuf: rules for updating messages safely](https://protobuf.dev/programming-guides/proto3/#updating)
- [DataLoader — batching and caching for the N+1 problem](https://github.com/graphql/dataloader)
- [gRPC-Web for browser clients](https://github.com/grpc/grpc-web)
