# Consuming APIs and Handling Webhooks
*Talking to a payment rail is the least reliable part of your system. Treat every outbound call as fallible and every inbound webhook as hostile.*

Inside your own process, a function call either returns or throws, and you believe the answer. The moment a request leaves your machine for a payment rail, a KYC provider, or a card network, that certainty is gone. The network can drop the reply after the work was done. The far side can be mid-deploy. A load balancer can quietly hold your connection open for thirty seconds and then reset it. If you write integration code that assumes the happy path, production will teach you the rest of the state space one incident at a time. This chapter is about the two directions of that conversation: the calls you make out, and the events that come back in.

## Every outbound call is a bet

Start with the boring discipline, because it prevents the exciting outages. Every single outbound call gets an explicit timeout — connect and read, both bounded, both short. A payment authorization that has not answered in four seconds is not going to redeem itself at forty; it is just holding a goroutine, a thread, or a connection-pool slot that you will need when traffic spikes. The default timeout in most HTTP clients is effectively infinity, and infinity is how a single slow dependency turns into a cascading thread-pool exhaustion that takes down endpoints that never even touched that dependency.

When a call fails in a way that might be transient — a `503`, a connection reset, a timeout — you retry, but retries are where naive code does real damage. Two rules are non-negotiable. First, every retry carries an **idempotency key**: a stable token, usually a UUID you generate once per logical operation, sent as a header so the rail can recognize "this is the same payment you already saw" and return the original result instead of charging the customer twice. Second, retries back off exponentially *with jitter* — `1s`, `2s`, `4s`, each randomized within a window. Without jitter, a rail that blips for a moment gets a synchronized thundering herd from every one of your instances retrying in lockstep, and you become the reason it stays down. A little randomness spreads the load and lets it recover.

```
attempt 1 ──▶ timeout (4s)
     wait 1s ± jitter, same idempotency-key
attempt 2 ──▶ timeout
     wait 2s ± jitter, same idempotency-key
attempt 3 ──▶ 200 OK  (rail replays original result)
```

> **▸ [Open the interactive diagram](/blog/handbook-diagrams/webhook-handling.html)** — pan, zoom, and trace every step (light/dark, self-contained).

And you cap it. After N failures, or once the error rate to a dependency crosses a threshold, a **circuit breaker** trips: you stop calling for a cooling-off window and fail fast locally. Hammering a dependency that is already on the floor does not help it stand up, and it burns your own capacity generating requests that will only time out. An open breaker is a mercy to both sides — and it gives you a clean signal to degrade gracefully instead of stalling.

## The ambiguous result problem

Here is the part that separates people who have run money at scale from people who have not. A timeout does not mean the operation failed. It means *you do not know*. Your request may have reached the rail, debited the customer, and then the response got lost on the way back. If you treat that timeout as a failure and retry without an idempotency key — or worse, without checking — you can double-charge. If you treat it as a failure and give up, you can lose a payment the rail actually completed.

You cannot resolve ambiguity by guessing. You resolve it by asking the authoritative system what actually happened. The move is **reconcile, not blindly retry**: on an ambiguous outcome, call the rail's status endpoint for that idempotency key or reference and let the rail tell you the truth. Only act on what it reports. This is exactly the class of edge case that the [UPI integration spec quirks](/blog/posts/upi-integration-spec-quirks.html) will bite you on — deemed-approved states, pending-that-becomes-success, and status codes that mean something narrower than they appear.

```
your service ──charge (idempotency-key=K)──▶ rail
                        │
                   (timeout — no reply)
                        │
                UNKNOWN, not FAILED
                        │
your service ──GET status?key=K──────────▶ rail
              ◀── {status: SUCCEEDED} ─────
                        │
              record truth, move on
```

Practically, this means an operation is never "done" just because your code returned. It is done when authoritative state confirms it. Persist the intent *before* the call (`PENDING`), record the idempotency key, and run a reconciliation sweep that revisits anything stuck in an ambiguous state. That background job is not optional polish; it is the safety net under every timeout you will ever get.

## Webhooks are hints, not truth

The inbound direction inverts your trust model. A webhook is an HTTP request from the outside world hitting a public endpoint, and you must assume anyone on the internet can send you a forged one. Treat every payload as hostile until proven otherwise.

**Verify the signature first, before you parse anything meaningfully.** Rails sign each webhook with an HMAC over the raw request body using a shared secret. You recompute it and compare — with a constant-time comparison, not `==`, so you do not leak the secret through timing.

```python
import hmac, hashlib

def valid(raw_body: bytes, header_sig: str, secret: bytes) -> bool:
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_sig)
```

Note it hashes the *raw* bytes — if your framework parses and re-serializes the JSON first, the signature will not match, so capture the body before any middleware touches it.

Signature alone is not enough. A valid signed request can still be a **replay** — an attacker capturing a real webhook and resending it. Rails include a timestamp in the signed material; reject anything older than a few minutes, and track a nonce or event ID so the same event cannot be processed twice. Which leads to the two assumptions that break people: webhooks are **not ordered** and **not exactly-once**. You will receive `payment.succeeded` before `payment.created`. You will receive the same event twice. Both are normal. Your handler must be idempotent — keyed on the event ID — so a duplicate is a no-op and out-of-order arrivals converge to the right state regardless of sequence.

## Ack fast, process later

The last mistake is doing real work inside the webhook request. The sender has its own timeout, and if your handler spends eight seconds updating ledgers and calling downstream services before returning `200`, the rail concludes delivery failed and retries — so your slow handler manufactures the very duplicates you are trying to avoid. Instead: verify, dedupe, enqueue, and return `200` immediately. Do the actual processing asynchronously off a queue.

```
rail ──▶ POST /webhooks
           │ verify HMAC        (reject 401 if bad)
           │ check timestamp    (reject stale replays)
           │ dedupe on event-id (seen? ack + drop)
           │ enqueue raw event
           └─▶ 200 OK  (fast)          ▶ worker: process idempotently
```

And process the event the same way you handle an ambiguous outbound call: the webhook tells you *something changed* — it is a hint to go read authoritative state, not a fact to trust wholesale. Fetch the current status from the rail's API and act on that. This also gives you a clean seam for policy — the point where an event, once verified, gets acted on is exactly where logic like [routing NPCI rails with a human in the loop](/blog/posts/npci-rail-routing-with-hitl.html) belongs.

## Why it matters

Every rule here — timeouts, idempotency keys, jittered backoff, breakers, reconciliation, signature checks, replay rejection, fast acks, idempotent async handlers — exists because a real system moved real money into a state nobody could explain. The integration layer is where your clean internal model meets an unreliable, adversarial outside world, and it is the layer that determines whether a bad network day is a shrug or a support queue full of double charges. Assume the call can lie about whether it worked. Assume the webhook is forged, replayed, out of order, and doubled. Build so that none of that corrupts your books. Get this boundary right and everything upstream of it gets to stay simple.
