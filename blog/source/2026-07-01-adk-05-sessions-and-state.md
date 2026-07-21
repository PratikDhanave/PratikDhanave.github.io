# Sessions & State in ADK: The Memory Inside a Conversation

*A `Session` is the conversation; `state` is the key-value bag agents and tools read and write — and the prefix on a key decides how long it lives.*

---

Every previous post in this series quietly read and wrote data that had to live *somewhere*. In Google's Agent Development Kit (ADK), that somewhere is a **Session**: an ordered list of **events** (the turns of a conversation) plus a **state** bag — a plain key-value store. State is the working memory an agent carries across turns within one conversation. It is not the model's context window and it is not long-term memory across conversations (that is a separate concept). It is the data structure your tools mutate and your instructions read.

The best part: sessions and state are *pure data*. You can learn the whole model with no LLM, no API key, and no network — which is exactly how the examples below run.

## The four scopes live in the key prefix

State keys carry an optional **prefix** that controls lifetime and visibility. This is the single most important idea in the whole topic, and it is the same in both SDKs:

| Prefix | Scope | Lives across… | Example |
|--------|-------|---------------|---------|
| *(none)* | **session** | turns of *this* conversation | `cart`, `current_step` |
| `user:` | **user** | *all* sessions of one user | `user:name`, `user:preferences` |
| `app:` | **app** | *all* users of the app | `app:model_version` |
| `temp:` | **temporary** | just this turn — never persisted | `temp:raw_api_json` |

There is no separate "scope" argument anywhere. The prefix *is* the API. `state["user:name"] = "Ada"` follows Ada into her next conversation; `state["cart"]` dies when this one ends; `state["temp:scratch"]` is stripped the instant the turn commits, which makes it ideal for scratch data (raw API payloads, intermediate math) you never want saved to history.

## How state actually changes: a delta on an event

You do **not** mutate the state map directly and expect it to persist. You attach a **state delta** to an event, and the `SessionService` applies that delta when the event is appended. Every change lands on the event log — auditable, replayable, and safe when parallel branches run concurrently.

Here is the whole scope model demonstrated in Python. Session #1 writes all four scopes; a fresh Session #2 for the same user shows what carried over:

```python
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService

APP, USER = "shop", "ada"
svc = InMemorySessionService()

s1 = await svc.create_session(app_name=APP, user_id=USER)
delta = {
    "cart": ["apple"],       # session — dies with this conversation
    "user:name": "Ada",      # user    — follows the user
    "app:version": "1.0",    # app     — shared by everyone
    "temp:scratch": "raw",   # temp    — stripped on commit
}
await svc.append_event(s1, Event(author="system", actions=EventActions(state_delta=delta)))

# A brand-new conversation for the same user:
s2 = await svc.create_session(app_name=APP, user_id=USER)
s2 = await svc.get_session(app_name=APP, user_id=USER, session_id=s2.id)
# s2.state has user:name and app:version, but NOT cart or temp:scratch.
```

The Go form is the same idea with request structs instead of keyword arguments, and named prefix constants instead of literal strings:

```go
import "google.golang.org/adk/v2/session"

svc := session.InMemoryService()
c1, _ := svc.Create(ctx, &session.CreateRequest{AppName: "shop", UserID: "ada"})

ev := session.NewEvent(ctx, "inv-1")
ev.Author = "system"
ev.Actions.StateDelta = map[string]any{
    "cart":                            []string{"apple"}, // session
    session.KeyPrefixUser + "name":    "Ada",             // user
    session.KeyPrefixApp + "version":  "1.0",             // app
    session.KeyPrefixTemp + "scratch": "raw",             // temp, stripped on commit
}
svc.AppendEvent(ctx, c1.Session, ev)
```

Note the idiom contrast: Python is `async` with keyword args (`create_session`, `append_event`); Go is synchronous with `CreateRequest` / `GetRequest` structs and a `session.KeyPrefixUser` constant where Python uses the literal `"user:"` (or `State.USER_PREFIX`). The semantics are identical.

## Reading state back into instructions

State is not just for tools. Agent instructions support `{state}` templating: a `{key}` in an instruction string is substituted with that key's value before the prompt reaches the model. So writing `state["user:name"]` in a tool and referencing `{user:name}` in an instruction is how personalization flows from your data into the prompt without string-concatenating it yourself. Because the substitution reads the same scoped map, a `user:` value set in a past conversation is available in this one's instruction.

## SessionService: where sessions live

The `SessionService` owns persistence, and swapping it never touches your agent code:

| Backend | Python | Go | Use for |
|---------|--------|-----|---------|
| In-memory | `InMemorySessionService()` | `session.InMemoryService()` | dev, tests |
| Database | `DatabaseSessionService(db_url=...)` | database service | self-hosted persistence |
| Vertex AI | `VertexAiSessionService(...)` | Vertex service | managed on Agent Engine |

Start in-memory. Graduate to a database when you need state to survive process restarts, or to Vertex when you want a managed store on Agent Engine. The scope prefixes mean the same thing everywhere; only the storage moves.

## Mental model: the cursor is just state

Once you internalize "state is a value committed as a delta on an event," a lot falls out for free. Reconstructing state *as of* an earlier event is a pure fold over the event log — replay each event's delta into a fresh map, stop at event N (later deltas overwrite earlier ones, exactly as the service applies them). Moving a session to another backend is the reverse: read its events, re-append them to the destination, and the deltas rebuild the state.

The same trick handles a corpus far larger than one turn. Keep a **cursor** — an ordinary session-scoped integer — and advance it each turn:

```python
def next_chunk(items, cursor, size):
    start = min(max(cursor, 0), len(items))
    return items[start:start + size], min(start + size, len(items))

# Each turn: read cursor from state, take the chunk, commit the advanced cursor.
cursor = s.state.get("scan_cursor", 0)
chunk, new_cursor = next_chunk(items, cursor, size)
await svc.append_event(s, Event(author="user",
    actions=EventActions(state_delta={"scan_cursor": new_cursor})))
```

The cursor is not a special API — it is `cart` with a different name. Point the driver at a database backend and the same scan resumes after a restart. That is the whole payoff of the delta-on-event discipline: your working memory, your resumable jobs, and your audit log are all one mechanism.

**Next in the series:** Memory — long-term recall *across* sessions, versus state, which lives within one.
