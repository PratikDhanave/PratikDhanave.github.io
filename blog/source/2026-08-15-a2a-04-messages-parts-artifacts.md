# Messages, Parts, and Artifacts

*Agents need to exchange more than plain strings — instructions, files, images, structured data, and finished deliverables — and A2A's content model handles all of it with three composable objects.*

Once two agents have found each other and framed work as a task, they need a way to actually communicate: to send instructions and data back and forth, and to return finished outputs. The Agent2Agent protocol (A2A) models this with three objects — **Message**, **Part**, and **Artifact**. This fourth post in the series covers the content model, how multi-modal content is represented, and the important distinction between the conversation and its deliverables.

## Messages: the turns of the conversation

A **Message** is a single communication turn between a client agent and a remote agent. Its key fields:

- `messageId` — a unique identifier for the message.
- `role` — who sent it: `ROLE_USER` (the client agent, acting on the user's behalf) or `ROLE_AGENT` (the remote agent).
- `parts` — the actual content, as one or more Parts (below).
- `contextId` and `taskId` — which conversation and task the message belongs to.
- `referenceTaskIds` — references to other tasks this message relates to, letting an agent point at prior work.

Messages are how the two sides talk during a task. The client sends a message to kick off or advance the work; the remote agent replies with messages as it asks questions, reports progress, or delivers results. The `role` field keeps the direction unambiguous, and the `taskId`/`contextId` keep each message anchored to its task and broader conversation. A task's `history` is, in effect, the sequence of these messages.

## Parts: the multi-modal content unit

A Message's content is not a bare string — it is a list of **Parts**, and each Part is one piece of content of a specific kind. This is how A2A stays multi-modal. A Part is one of:

- **text** — a string, the common case for instructions and natural-language content.
- **raw** — binary data (bytes, base64-encoded when serialized as JSON), for files, images, audio, or any binary payload passed inline.
- **url** — a reference to content by URL, for when data is better fetched than embedded (large files, resources hosted elsewhere).

Because a Message holds an array of Parts, a single turn can mix modalities — a text instruction alongside an image, or a description alongside a link to a document. And because Parts distinguish inline binary (`raw`) from referenced content (`url`), agents can choose the efficient representation: embed small payloads, link to large ones. The content model does not privilege text; it treats it as one Part kind among several, which is what lets A2A carry the messy, multi-modal inputs and outputs real agent work involves.

Conceptually, a message with mixed parts:

```json
{
  "messageId": "m-102",
  "role": "ROLE_USER",
  "taskId": "t-55",
  "parts": [
    { "text": "Translate the attached contract into French." },
    { "url": "https://files.example.com/contract-en.pdf" }
  ]
}
```

## Artifacts: the deliverables

Messages carry the conversation; **Artifacts** carry the *results*. An Artifact is an output the task produces — the finished translation, the generated report, the computed dataset. Its fields:

- `id` — a unique identifier for the artifact.
- `parts` — the artifact's content, using the same Part model as messages (so artifacts are multi-modal too).
- `metadata` — additional structured data about the output.

Artifacts live on the Task (its `artifacts` field), not inside a single message. This separation is deliberate and worth dwelling on: the *conversation* about the work is distinct from the *products* of the work. A long task might exchange many messages — clarifications, progress notes — and produce one or several artifacts at the end. Keeping deliverables as first-class Artifacts on the task means a client can retrieve the outputs cleanly by fetching the task, without parsing them out of a chat log, and a task can accumulate multiple outputs (a report plus its supporting data) as distinct, addressable results.

## Messages versus artifacts: the mental model

The distinction is the key idea of this post, so make it concrete:

- **Messages** are the *dialogue* — turns between the agents while the work is underway. They are ephemeral in purpose: instructions, questions, answers, status.
- **Artifacts** are the *deliverables* — the durable outputs the client actually wanted, attached to the task.

A remote agent that translates a document exchanges messages ("what target language?", "working on it") and then produces an Artifact (the translated file). Reusing the same Part model for both keeps the content representation uniform, while separating the two keeps "what was said" distinct from "what was produced." When you design an A2A agent, decide deliberately which outputs are conversational messages and which are true artifacts — the latter are what clients will retrieve and depend on.

## Key takeaways

- A2A's content model has three objects: Messages (conversation turns), Parts (the content units), and Artifacts (the deliverables).
- A Message has a `messageId`, a `role` (ROLE_USER or ROLE_AGENT), `parts`, and `taskId`/`contextId` anchors; a task's history is the sequence of its messages.
- A Part is one of text, raw (inline binary, base64 in JSON), or url (referenced content); a Message holds an array of Parts, so a single turn can be multi-modal and choose inline vs referenced data.
- Artifacts are task outputs — `id`, multi-modal `parts`, and `metadata` — attached to the Task rather than buried in a message.
- The core distinction: Messages are the dialogue about the work, Artifacts are the products of the work; both reuse the Part model, but keeping them separate lets clients retrieve deliverables cleanly.

## Further reading

- [A2A Protocol — official site](https://a2a-protocol.org)
- [A2A protocol specification](https://a2a-protocol.org/latest/specification/)
- [Agent2Agent (A2A) on GitHub](https://github.com/a2aproject/A2A)
