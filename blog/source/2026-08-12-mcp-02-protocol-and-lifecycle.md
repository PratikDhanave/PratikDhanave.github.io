# The MCP Wire Protocol: JSON-RPC and the Connection Lifecycle

*Underneath every tool call and resource read is a small, well-defined conversation in JSON-RPC that begins with a handshake and a negotiation over what each side can do.*

The Model Context Protocol (MCP) feels magical when a model discovers a tool it has never seen and calls it correctly. Underneath, there is no magic — just a disciplined exchange of JSON messages. This post opens the hood on that exchange: the message format MCP borrows, the handshake that starts every session, and the capability negotiation that keeps both sides honest. Once you can picture the raw messages, the rest of MCP stops being abstract.

## JSON-RPC 2.0, the message layer

MCP does not invent its own message format. It uses [JSON-RPC 2.0](https://www.jsonrpc.org/specification), a tiny, mature standard for remote procedure calls over any transport. There are exactly three message shapes, and everything in MCP is one of them.

A **request** expects a reply. It carries an `id`, a `method` name, and optional `params`:

```json
{ "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {} }
```

A **response** answers a request with the same `id`, and contains either a `result` or an `error` — never both:

```json
{ "jsonrpc": "2.0", "id": 1, "result": { "tools": [] } }
```

A **notification** is a request with no `id`. It is fire-and-forget: the sender expects no reply and the receiver must not send one.

```json
{ "jsonrpc": "2.0", "method": "notifications/tools/list_changed" }
```

That is the entire vocabulary. MCP's methods — `initialize`, `tools/list`, `tools/call`, `resources/read`, `prompts/get`, and so on — are just method names carried inside these shapes. Because requests carry an `id`, both sides can have multiple requests in flight and match each reply to its request. And because MCP is bidirectional, the *server* can also send requests to the *client* (for example, to ask the client's model to generate text), not just the other way around.

## The connection lifecycle

Every MCP session moves through three phases: initialization, operation, and shutdown. The first is the only one with mandatory choreography, and getting it right is what makes the rest work.

### The initialize handshake

Before any tools are listed or called, the client sends an `initialize` request. It states the protocol version it wants to speak, the capabilities it offers, and who it is:

```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "method": "initialize",
  "params": {
    "protocolVersion": "<negotiated-version>",
    "capabilities": { "roots": {}, "sampling": {} },
    "clientInfo": { "name": "example-host", "version": "1.0.0" }
  }
}
```

The server replies with the version it will actually use, its own capabilities, and its identity:

```json
{
  "jsonrpc": "2.0",
  "id": 0,
  "result": {
    "protocolVersion": "<agreed-version>",
    "capabilities": { "tools": {}, "resources": {}, "prompts": {} },
    "serverInfo": { "name": "notes-server", "version": "0.1.0" }
  }
}
```

Once the client has that response, it sends an `initialized` notification to signal that the session is ready:

```json
{ "jsonrpc": "2.0", "method": "notifications/initialized" }
```

Only now may normal requests flow. Sending `tools/list` before the handshake completes is a protocol error. Think of `initialize` as the point where both sides learn each other's shape so nobody assumes a feature the other lacks.

### Operation

After initialization, the session is in its long steady state. The client lists and calls tools, reads resources, and fetches prompts; the server responds and may push notifications (for example, that its tool list changed, or progress on a long call). Either side may also issue the requests its counterpart's capabilities allow. This phase lasts until someone ends it.

### Shutdown

Shutdown is deliberately undramatic: there is no special "goodbye" message. The side that owns the connection simply closes the transport — for a local subprocess server, the client closes stdin and lets the process exit; for a network server, the underlying connection is closed. Clean teardown is a transport concern, which is why the next post treats transports on their own.

## Capability negotiation

The heart of the handshake is capability negotiation. Neither side should assume the other supports a feature just because the spec defines it. So each declares, up front, what it actually offers.

A server that has tools and resources but no prompts advertises exactly that. A client that can let servers sample from its model, or that exposes filesystem "roots," says so. After the exchange, both sides know the intersection of what is possible and stay inside it. A client will not call `prompts/get` on a server that never advertised prompts; a server will not ask the client to sample if the client never offered sampling.

This is what lets MCP grow without breaking. New optional features can be added to the spec, and old peers simply do not advertise them — the negotiation degrades gracefully instead of erroring. Capabilities are the reason a five-year-old client and a brand-new server can still hold a sensible conversation about the subset they share.

## Protocol versioning

MCP is versioned with dated revisions, and the version is itself negotiated in the handshake. The client proposes a version; the server responds with the version it will use. If they can agree — typically the client accepts the server's supported version, or the connection is closed if there is no common ground — the session proceeds under that single agreed version for its whole lifetime. Pinning one version per session avoids the ambiguity of features drifting mid-conversation. The practical rule for implementers: read the version from the handshake and behave accordingly, rather than hardcoding assumptions about what any peer supports.

## The error model

Errors ride the JSON-RPC error object: a numeric `code`, a human `message`, and optional structured `data`.

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "error": { "code": -32602, "message": "Invalid params: 'repo' is required" }
}
```

JSON-RPC reserves a range of standard codes (parse error, invalid request, method not found, invalid params, internal error) and leaves room for application-specific ones. There is an important distinction MCP draws that we will return to in the tools post: a *protocol* error (the request was malformed or the method does not exist) is different from a *tool* error (the tool ran but failed — say, a 404 from the API it wraps). The former is a JSON-RPC error; the latter is a normal result that reports failure so the model can see it and react. Confusing the two makes tools that either crash sessions or hide failures.

## Key takeaways

- MCP rides on JSON-RPC 2.0, which has just three message shapes: requests (with an `id`), responses (matching that `id`, with `result` or `error`), and id-less notifications.
- Every session starts with an `initialize` request/response followed by an `initialized` notification; no other traffic is valid before that completes.
- Capability negotiation makes both sides declare what they support, so neither assumes an unsupported feature — this is what lets the protocol evolve without breaking old peers.
- The protocol version is negotiated in the handshake and fixed for the session; read it rather than hardcoding assumptions.
- Distinguish protocol errors (malformed request, unknown method) from tool errors (the tool ran and failed); they are surfaced differently.

## Further reading

- [Model Context Protocol — official site and docs](https://modelcontextprotocol.io)
- [MCP specification repository](https://github.com/modelcontextprotocol/modelcontextprotocol)
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)
