# 02 · Multi-turn with Server Conversations

*How to keep a conversation's history on the Foundry service instead of in local memory, so the client never resends the transcript.*

---

## What this lesson demonstrates

The previous lesson kept history in a client-side session. This one moves it to the **server**: you create a Foundry project *conversation* once, bind its ID into an `agent.Session`, and pass that session to every run. Because the transcript lives in the service, turn 2 ("add emojis…") and turn 3 ("another joke, but a ninja") remember the earlier turns without the client ever resending them.

## Binding a session to a server conversation

The distinctive move is creating the project conversation and wiring its ID into the session with `agent.WithServiceID`:

```go
// (1) Create a server-side project conversation and bind a Session to its ID.
conversationID, err := createProjectConversation(ctx, endpoint, cred)
// ...
session, err := a.CreateSession(ctx, agent.WithServiceID(conversationID))
// ...

// (2) Turn 1 — establish a joke; the server now keeps the transcript.
resp, err := a.RunText(ctx, "Tell me a joke about a pirate.",
	agent.WithSession(session)).Collect()
```

From here every `RunText` threads the same `session`. The last turn even switches to streaming (`agent.Stream(true)`) over the identical server conversation, proving the transport doesn't care whether you collect or stream.

## What to notice

The project conversation is created directly against the OpenAI-compatible endpoint. `createProjectConversation` builds an `openai.NewClient` pointed at `{endpoint}/openai/v1/` with `azure.WithTokenCredential` and the scope `https://ai.azure.com/.default`, then calls `client.Conversations.New`. That returns a conversation `ID` — the thing you hand to `WithServiceID`.

The gotcha: **this whole flow is live**. Creating the project conversation is itself a network call, so unlike the client-side session lesson, there's no way to exercise the real path offline. The structural test still builds the agent with a fake credential and asserts the logging middleware is attached, but the server-conversation path is gated behind `AF_LIVE=1`.

Watch the OAuth scope, too. The provider's own model calls use one credential path, but the conversations client explicitly requests the `https://ai.azure.com/.default` resource scope — get that wrong and conversation creation fails with an auth error even though model calls would succeed.

## How it maps to Foundry

Server-side conversations are Foundry's answer to "I don't want to ship the whole history on every request." The service owns the transcript; the client sends only the new turn plus the conversation ID. That's cheaper on the wire, survives client restarts, and is the foundation the persisted-conversation and observability lessons build toward.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step02_2_multiturn_with_server_conversations
```

Needs `az login` and `FOUNDRY_PROJECT_ENDPOINT`; the live path is gated behind `AF_LIVE=1`.

---

Next: [step03 · Function Tools (Foundry)](/blog/posts/maf-go-42-function-tools.html)
