# Protocol Buffers: The Contract and the Wire Format

*Protocol Buffers are the foundation gRPC is built on — both the language you write your API contract in and the binary format your data travels as. A `.proto` file is a strict, versioned schema; the encoding is a compact, tag-based binary that's a fraction of JSON's size. Understanding both halves — the schema language and how it serializes — is what lets you design APIs that stay compatible as they evolve.*

The previous post named the `.proto` file as gRPC's beating heart. This post opens it up. Protocol Buffers ("protobuf") do two jobs: they're an *interface definition language* for declaring your data and services, and they're a *serialization format* for putting that data on the wire. We'll cover both, and the field-numbering discipline that makes protobuf APIs evolvable.

## The schema language

A `.proto` file declares **messages** — structured records — using a small, typed syntax. Here's a realistic one:

```proto
syntax = "proto3";
package user.v1;

message User {
  int64  id    = 1;
  string name  = 2;
  string email = 3;
  Role   role  = 4;
  repeated string tags = 5;
}

enum Role {
  ROLE_UNSPECIFIED = 0;
  ROLE_ADMIN       = 1;
  ROLE_MEMBER      = 2;
}
```

Each field has a **type** (`int64`, `string`, `bool`, nested messages, `enum`, `repeated` for lists, `map` for dictionaries), a **name**, and — critically — a **field number** (the `= 1`, `= 2`). That number, not the name, is what identifies the field on the wire. This is the single most important fact about protobuf, and the next sections explain why.

`proto3` (the current syntax) also has deliberate rules: every enum's first value must be `0` and serves as the default/"unspecified" case, and scalar fields have zero-value defaults rather than a distinction between "absent" and "empty" unless you opt into it. These choices exist to make schema evolution safe.

## How it encodes: tags, not names

When protobuf serializes a message, it does *not* write field names. For each field it writes a small **tag** — the field number combined with a wire-type (indicating how many bytes follow and how to read them) — followed by the value's bytes. Integers use a variable-length encoding (**varint**) so small numbers take one byte; strings and nested messages are length-prefixed.

Two consequences fall out of this design, and they're the whole reason protobuf is worth learning:

- **It's tiny and fast.** No field names, no punctuation, no whitespace — just numeric tags and packed binary values. A message that's 100 bytes of JSON is often a small fraction of that in protobuf, and encoding/decoding is simple byte manipulation rather than text parsing. This compactness, message after message, is much of gRPC's performance advantage.
- **The field number is the identity.** Because only the number goes on the wire, you can *rename* a field freely — the name is a local, code-generation concern — but you can *never* reuse or change a number without breaking compatibility. The number is the permanent contract; the name is cosmetic.

## Schema evolution: the real payoff

APIs change. Protobuf's field-numbering design is engineered so schemas can evolve without breaking existing clients or servers — *if* you follow the rules. This is protobuf's killer feature, and misunderstanding it is where teams get burned.

The safe operations:

- **Add a new field** with a *new, never-before-used* number. Old code simply doesn't know about it and ignores its tag; new code reads it. Forward and backward compatible.
- **Rename a field** — harmless, since names aren't on the wire (though it changes generated code, so coordinate with consumers).
- **Remove a field** — but you must *reserve* its number so no one accidentally reuses it later.

The dangerous operations, which silently corrupt data:

- **Reusing a field number** for a different field. Old messages carrying the old meaning under that number will be misread by new code as the new field — a data-corruption bug that no compiler catches.
- **Changing a field's type** in an incompatible way, so existing bytes are reinterpreted wrongly.
- **Changing a field number** — equivalent to deleting the old field and adding a new one, breaking anyone using the old number.

This is why protobuf has a `reserved` keyword: when you remove a field, you mark its number (and optionally name) reserved so the toolchain refuses to let anyone reuse it:

```proto
message User {
  reserved 4;              // Role field was removed; never reuse 4
  reserved "role";
  int64  id    = 1;
  string name  = 2;
  string email = 3;
  repeated string tags = 5;
}
```

Internalize the rule and evolution is safe: **only ever add fields with fresh numbers, and reserve the numbers of fields you remove.** Follow it and a service can evolve for years while old and new clients keep interoperating.

## Defining services

Beyond messages, `.proto` files declare **services** — the callable methods gRPC generates stubs for:

```proto
service UserService {
  rpc GetUser (GetUserRequest) returns (User);
  rpc ListUsers (ListUsersRequest) returns (stream User);   // server streaming
}

message GetUserRequest  { int64 id = 1; }
message ListUsersRequest { int32 page_size = 1; }
```

Each `rpc` names a method, its request message, and its response message. The `stream` keyword (on the request, the response, or both) selects among the four RPC types — the subject of the next post. Notice the discipline: **every method takes exactly one request message and returns exactly one response message.** This is why even a method with several parameters wraps them in a dedicated request message — it keeps every operation evolvable via the same add-a-field rules, rather than pinning you to a fixed parameter list. The message-per-operation convention is protobuf's evolvability applied to method signatures.

## Why this foundation matters

Protocol Buffers give gRPC its two defining properties. The *compact tag-based encoding* is where the performance comes from — small messages, fast codec, no text parsing. The *strict, numbered schema* is where the safety comes from — a contract enforced at compile time and evolvable without breakage. Every later topic in this series (codegen, streaming, errors, production) sits on top of these two facts. Get field numbering right and you've mastered the one thing most likely to bite a growing gRPC API.

## Key takeaways

- A `.proto` file is both an **interface definition language** (declaring typed `message`s and `service`s) and the spec for a **binary serialization format** — one artifact, two jobs.
- Protobuf encodes each field as a numeric **tag (field number + wire type) plus packed binary value**, writing *no field names* — which makes messages tiny and fast (a fraction of JSON) and makes the **field number, not the name, the field's identity**.
- **Schema evolution is protobuf's killer feature**: safely *add* fields with fresh numbers, *rename* freely (names aren't on the wire), and *remove* by `reserved`-ing the number — but **never reuse or change a field number or type**, which silently corrupts data.
- Services declare `rpc` methods each taking **exactly one request message and returning exactly one response message** (with `stream` selecting the RPC type) — the message-per-operation convention keeps method signatures evolvable.
- Protobuf gives gRPC its two defining properties: **performance** (compact tag-based encoding) and **safety** (a strict, compile-time-enforced, evolvable contract).

## Further reading

- [Protocol Buffers — Language Guide (proto3)](https://protobuf.dev/programming-guides/proto3/)
- [Protocol Buffers — Encoding](https://protobuf.dev/programming-guides/encoding/)
