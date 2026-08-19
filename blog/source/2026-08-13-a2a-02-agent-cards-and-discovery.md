# Agent Cards and Discovery

*Before one agent can delegate to another it has to find it and understand what it can do, and in A2A that self-description is a single structured document called the Agent Card.*

For agents to collaborate across organizational and framework boundaries, they first need a way to answer three questions about each other: who are you, what can you do, and how do I reach you? The Agent2Agent protocol (A2A) answers all three with one artifact — the **Agent Card**. This second post in the series covers what an Agent Card contains, how discovery works, and why treating the card as the contract keeps opaque agents genuinely interoperable.

## The Agent Card as a contract

An Agent Card is a structured document, published by an A2A server, that describes the agent's identity, capabilities, skills, service endpoint, and authentication requirements. It is the machine-readable "business card" a client agent reads to decide whether and how to work with a remote agent. Because A2A treats remote agents as opaque, the card is the *entire* public contract — a client agent knows nothing about the remote agent's internals, only what the card advertises.

That framing matters. Everything a client agent does — deciding the remote agent is relevant, formatting a request it will understand, authenticating correctly — flows from the card. A precise, honest card makes an agent usable; a vague one makes it ignored.

## What the card contains

An Agent Card carries several groups of fields. The important ones:

- **Identity** — an `id`, a human `name`, and a `description` of what the agent is for. A `provider` block names the organization behind it (name, URL, contact).
- **Capabilities** — protocol-level features the agent supports, such as `streaming` (real-time updates) and `pushNotifications` (webhook callbacks), plus whether it offers an `extendedAgentCard`.
- **Skills** — an array of `AgentSkill` entries describing the concrete things the agent can do. Skills are how a client agent decides *this is the agent for this subtask*, so they carry names, descriptions, and enough detail to route to.
- **Interfaces** — the service endpoint(s) and which transport binding each speaks (A2A supports more than one, covered later in the series).
- **Security** — `securitySchemes` and `security` declarations stating how a client must authenticate. Nothing about calling the agent is guessed; the auth requirements are declared here.
- **Signature** — an optional `signature` (an `AgentCardSignature`) so a client can verify the card's authenticity and integrity rather than trusting it blindly.
- **Extensions** — optional declared extensions the agent supports, so the protocol can grow without breaking base compatibility.

Conceptually, a card looks like this:

```json
{
  "id": "translation-agent",
  "name": "Translation Agent",
  "description": "Translates documents between supported languages.",
  "provider": { "name": "Example Corp", "url": "https://example.com" },
  "capabilities": { "streaming": true, "pushNotifications": true },
  "skills": [
    {
      "id": "translate-document",
      "name": "Translate a document",
      "description": "Translate a text document into a target language."
    }
  ],
  "interfaces": [ { "protocol": "jsonrpc", "url": "https://agents.example.com/a2a" } ],
  "securitySchemes": { "oauth2": { "type": "oauth2" } },
  "security": [ { "oauth2": [] } ]
}
```

The exact schema is normatively defined by the specification; the point to internalize is that one document tells a client agent everything it needs — what the agent does, where it lives, and how to authenticate.

## Skills: how routing decisions get made

Skills deserve special attention because they are where an orchestrating agent makes its choice. When a client agent needs a subtask done, it reads candidate agents' cards, matches the subtask against their declared skills, and delegates to the best fit. This is the agent-to-agent analogue of tool selection: just as a good tool description helps a model pick the right tool, a good skill description helps a client agent pick the right *agent*. Vague skills ("does stuff with text") produce bad routing; specific ones ("translate a document between supported languages," "summarize a legal contract") produce good routing. Write skills for the agent that will read them.

## Discovery

Discovery is the act of a client agent obtaining a remote agent's card. In practice, an A2A server publishes its Agent Card at a known, retrievable location so clients can fetch it over HTTPS, and organizations may also maintain registries or catalogs of agents for their systems to search. Once a client has the card, it has enough to authenticate and begin sending work.

A2A also supports the idea of an **extended Agent Card**. A public card can advertise that an authenticated, richer card is available (`capabilities.extendedAgentCard`); a client that authenticates can then retrieve additional skills or details it is authorized to see. This lets an agent show a limited public face to anyone and a fuller set of capabilities to trusted, authenticated callers — useful when some skills are sensitive or partner-specific.

## Why this design holds up

The Agent Card design is what makes opaque, cross-vendor collaboration work. Because the card is a stable, declared contract, a remote agent can change its model, prompts, tools, or implementation freely as long as the card's promises still hold. Clients depend on the advertised interface, not the internals — the same discipline that makes any good API durable, applied to autonomous agents. Get the card right, and everything downstream in A2A has a firm foundation.

## Key takeaways

- The Agent Card is a structured document an A2A server publishes to describe its identity, capabilities, skills, endpoint, and authentication — the entire public contract for an opaque agent.
- Key fields include identity/provider, protocol capabilities (streaming, pushNotifications), skills, interfaces (endpoints and transports), security schemes, an optional signature for authenticity, and extensions.
- Skills drive routing: an orchestrating agent matches a subtask against candidates' declared skills, so write them specifically, like good tool descriptions.
- Discovery is fetching an agent's published card over HTTPS (or via a registry); an extended Agent Card can reveal richer capabilities to authenticated callers.
- Because the card is a stable declared contract, remote agents can change internals freely while clients depend only on what is advertised — the foundation for durable cross-vendor collaboration.

## Further reading

- [A2A Protocol — official site](https://a2a-protocol.org)
- [Agent2Agent (A2A) on GitHub](https://github.com/a2aproject/A2A)
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)
