# The FIX Protocol: Engineering a Session and Order Gateway

*The 40-year-old tag=value protocol still carrying most of the world's equity orders — and how to build an engine that survives a dropped connection.*

If you send an equity, futures, or FX order into an exchange or a broker, there is a good chance it travels as a FIX message. The Financial Information eXchange protocol dates to the early 1990s, and yet it still moves an enormous share of the world's electronic order flow. Newer transports exist — binary encodings, proprietary APIs, market-data multicast — but the plain FIX 4.2/4.4 tag=value session remains the lingua franca between counterparties who have never shared a codebase. If you build order infrastructure, you will meet it, and you will eventually have to build or operate an engine that speaks it correctly.

## What FIX is, and why it persists

A FIX message is almost embarrassingly simple on the wire: a flat list of `tag=value` pairs separated by the ASCII SOH character (0x01). A tag is just an integer with an agreed meaning — `35` is the message type, `49` is the sender, `56` is the target, `34` is the sequence number. There is no JSON, no XML, no schema negotiation at runtime. Both sides agree on a dictionary in advance and parse positionally-agnostic key/value pairs.

That minimalism is exactly why it survives. The protocol is trivial to parse in any language, cheap to log, and human-readable enough to debug with `grep`. More importantly, decades of counterparties have already certified their engines against each other. Nobody rips out a working FIX connection to save a few bytes. The protocol persists because the cost of change is enormous and the cost of keeping it is nearly zero.

FIX splits cleanly into two layers, and understanding that split is the whole job.

## The session layer: sequence numbers are the whole game

The session layer guarantees one thing: **ordered, gap-free, exactly-once-observed delivery of messages between two parties.** Everything else in the session exists to protect that guarantee.

Every message carries a sequence number (tag `34`). Each side maintains two counters: the next number it will *send*, and the next number it *expects to receive*. The session begins with a **Logon** (`35=A`), which establishes the connection, agrees a heartbeat interval, and — critically — anchors the sequence numbers. From there:

- **Heartbeat** (`35=0`) is sent when a side has been idle for the negotiated interval. It proves the link is alive.
- **TestRequest** (`35=1`) is sent when you *haven't* heard from the other side in time. It demands a heartbeat carrying a specific token. No timely reply means the session is dead and should be dropped.
- **Gap detection** happens on every inbound message. If you expect sequence 108 and receive 111, three messages vanished. You do not process 111 out of order. You send a **ResendRequest** (`35=2`) for the range 108–110.
- **ResendRequest / gap-fill** is the recovery mechanism. The counterparty replays the missing messages from its store, or sends a **SequenceReset** (`35=4`) gap-fill to skip administrative messages that don't need replay.
- **Logout** (`35=5`) closes the session cleanly, ideally with both counters in agreement.

The mental model that matters: the session layer is a reliable, ordered pipe built on top of a TCP connection that will absolutely be dropped, reset, and reconnected. TCP gives you bytes; FIX sequence numbers give you *application-level* delivery guarantees that survive a full disconnect.

## The application layer: an order's message flow

On top of that pipe rides the business content. For an order gateway the core vocabulary is small:

- **NewOrderSingle** (`35=D`) — "buy 500 shares, limit 42.10, day order." It carries a client-assigned `ClOrdID` (tag `11`), the instrument, side, quantity, and order type.
- **ExecutionReport** (`35=8`) — the workhorse response. The *same* message type reports every state transition: order acknowledged (`New`), partially filled, fully filled, rejected, canceled, expired. Tag `39` (OrdStatus) and `150` (ExecType) tell you which. One order typically produces several execution reports over its life.
- **OrderCancelRequest** (`35=F`) and **OrderCancelReplaceRequest** (`35=G`) — amend or pull a resting order, referencing the original `ClOrdID`.

A clean happy path looks like this: the client sends `35=D`, the engine acknowledges with an ExecutionReport carrying OrdStatus `New`, and later — when the book crosses — one or more ExecutionReports carrying `Fill` or `Partial Fill`. The ASCII sketch below shows that flow plus a recovery after a gap:

```
 Client                         FIX Engine                    Matcher
   |                                |                            |
   |----- Logon 35=A (seq 1) ------>|                            |
   |<---- Logon 35=A accepted ------|                            |
   |----- Heartbeat 35=0 ---------->|                            |
   |                                |                            |
   |----- NewOrderSingle 35=D ----->|                            |
   |                                |-- persist inbound seq -->[store]
   |                                |------- route order ------->|
   |                                |<-------- accepted ---------|
   |<-- ExecReport 35=8 (New) ------|                            |
   |<-- ExecReport 35=8 (Fill) -----|                            |
   |                                |                            |
   |  (client detects seq gap)      |                            |
   |----- ResendRequest 35=2 ------>|                            |
   |                                |-- read seq range ------->[store]
   |<-- Resend 35=8 PossDup=Y ------|                            |
   |                                |                            |
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-fix-protocol-engine.html)** — the same FIX session and order flow as an explorable sequence diagram with logon, execution reports, and gap recovery.

## Building the engine: store, persistence, replay

A FIX engine is really two components wearing one coat, and keeping them separate is the single best architectural decision you can make.

**The session component** owns sequence numbers, heartbeats, logon/logout state, and resend logic. It knows nothing about orders. Its job is to hand the application clean, in-order messages and to guarantee that anything it sent can be re-sent.

**The application component** owns order state and business logic. It never touches sequence numbers.

Between them sits the piece that makes recovery possible: the **message store**. Every outbound message must be persisted with its sequence number *before* it goes on the wire. This is not optional. When a counterparty sends `ResendRequest` for sequences 108–110, you must be able to reproduce those exact messages byte-for-byte — including their original sequence numbers — even if your process crashed and restarted in between. Equally, inbound sequence state must be persisted so that after a restart you know precisely what you last processed.

Concretely, a resilient store persists three things durably: the outbound message log (indexed by sequence number), the last-sent sequence number, and the last-received sequence number. On reconnect, the engine reads those counters, re-establishes the session with a fresh Logon, and lets the normal gap-detection machinery replay anything the other side missed. Reconnect is not a special code path bolted on afterward — it is just logon plus the resend mechanism you already built.

A common and dangerous shortcut is to keep sequence state in memory only. It works perfectly until the first crash mid-session, at which point your counters reset, the counterparty sees numbers it has already processed, and the session wedges. Persist before send, always.

## Pitfalls that bite in production

**Sequence resets.** `SequenceReset` (`35=4`) has two modes: gap-fill (advance the expected number, skipping replayed admin messages) and the far more dangerous *reset* mode that forcibly sets the counter. An incorrectly issued reset can silently skip real orders. Treat any reset that lowers a sequence number with deep suspicion.

**PossDup and PossResend.** When you replay a message during a resend, you must set `PossDupFlag=Y` (tag `43`) so the receiver knows it may have seen this before and can deduplicate on `ClOrdID`. `PossResendFlag` (tag `97`) signals the *content* may be a resend of an already-actioned order. Ignore these flags and you risk double-executing an order — an expensive bug in this domain.

**Slow consumers and heartbeat starvation.** If your application layer blocks — a slow database write, a lock, a GC pause — the session layer can't send heartbeats, the counterparty fires a TestRequest, and eventually drops you. The session loop must never be blocked by business logic. Decouple them with a queue and let the session thread stay responsive no matter what the application is doing.

**Clock and reset-at-logon policies.** Many venues reset sequence numbers daily at a fixed time. If your engine and the venue disagree on whether today is a fresh session, you will spend the morning in a resend storm. Codify the reset policy per counterparty; don't assume.

## What to remember

FIX is old, plain, and stubbornly alive because it solves one problem well: reliable, ordered message delivery between parties who share only a dictionary. Build the engine as two layers — a session that obsesses over sequence numbers and a persistent store, and an application that never sees them. Persist every outbound message before it leaves, treat reconnect as ordinary logon-plus-resend rather than an exception, and respect PossDup so a replay never becomes a double execution. Get those invariants right and a dropped connection becomes a non-event instead of an incident.
