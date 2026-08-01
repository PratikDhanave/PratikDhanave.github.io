# Interbank mTLS and Message Signing

*Securing bank-to-bank and scheme connectivity with mutual TLS, detached JWS signatures for non-repudiation, and replay protection built from nonces and timestamps.*

---

When two banks exchange a payment instruction, "is the channel encrypted?" is the least interesting question. TLS gives you a private pipe, but a private pipe to *whom*, carrying a message that *who* signed, and can the receiver prove months later that the sender actually sent it? Interbank connectivity answers those questions with two independent layers that are easy to conflate and expensive to conflate wrong: transport authentication (mutual TLS) and message authentication (detached signatures). This post is about building both, and about the replay window that sits between them.

## Two layers doing two different jobs

Transport security and message security protect against different adversaries, and a common architecture mistake is assuming one covers the other. mTLS authenticates the *connection endpoint* — it proves the socket on the other end holds a private key matching a certificate you trust. Message signing authenticates the *payload* — it proves a specific business message was produced by a specific signing identity and has not been altered by a single byte.

They diverge the moment a message crosses more than one hop. A payment that traverses a gateway, a queue, and a core ledger is decrypted and re-encrypted at every TLS termination. The transport guarantee evaporates at each boundary; the signature rides the payload the whole way and can be re-verified at rest, in an audit, or in a dispute.

```
   Transport layer (mTLS)          Message layer (detached JWS)
   ┌───────┐   TLS   ┌───────┐     signature travels with payload,
   │Bank A │◄═══════►│Gateway│     survives every TLS termination
   └───────┘         └───┬───┘
                         │ TLS (re-encrypted)
                     ┌───▼───┐     verify signature at rest,
                     │ Core  │     in audit, and in dispute
                     └───────┘
   protects: the pipe            protects: the message, end to end
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-interbank-mtls-message-signing.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Treat them as orthogonal. Never let a valid TLS session imply an authenticated message, and never let a valid signature imply the caller was allowed on the socket. Enforce both, independently, on every request.

## The mutual TLS handshake and certificate discipline

Ordinary TLS authenticates the server to the client. Mutual TLS adds the reverse: the server demands a client certificate and validates it before the application layer sees a single request. On the handshake, the receiving bank checks the presented client certificate against a small, explicitly enrolled trust set — not the public web PKI. Correspondent connectivity is a closed community, so the trust anchor is a private CA or a pinned set of leaf certificates you onboarded deliberately.

Two knobs matter more than the rest:

- **Certificate pinning.** Public CA validation says "some CA vouches for this name." That is far too permissive for a payment counterparty. Pin either the counterparty's issuing CA or the exact leaf certificate fingerprint, so a mis-issued certificate from an unrelated CA is rejected even though it chains to a public root.
- **Certificate-to-identity binding.** A valid certificate is not an authorization. Extract the subject (or a SAN, or the fingerprint) and map it to an enrolled counterparty identity in your own registry. If the socket presents a technically valid certificate that maps to no enrolled party — or to a party not permitted on this endpoint — reject before any parsing.

```python
def authorize_connection(peer_cert, endpoint):
    fp = sha256(peer_cert.der)
    party = registry.lookup_by_fingerprint(fp)   # pinned, not CA-trust
    if party is None:
        raise Reject("unenrolled certificate")
    if not party.enabled or endpoint not in party.allowed_endpoints:
        raise Reject("party not permitted here")
    if peer_cert.not_after - now() < RENEWAL_GRACE:
        alert("counterparty cert nearing expiry", party.id)
    return party        # transport identity, distinct from signing identity
```

Note the transport identity returned here is deliberately separate from the signing identity established next. The certificate that terminated the connection and the key that signed the message do not have to be the same, and modeling them as one field is a bug waiting to surface during a rotation.

## Detached signatures for non-repudiation

The transport layer is now trustworthy, but nothing about it proves *who authored the payment*. That is the job of a message signature, and the useful form is a **detached** signature: the signature is computed over the payload but transmitted alongside it rather than wrapped around it. The payload stays byte-for-byte identical, which matters because the receiver's parser, canonicalizer, and archive all want the original bytes, not a re-serialized copy.

A detached JWS carries the protected header and signature in an HTTP header while the JSON or XML body travels untouched. The signing input is the concatenation of the header and the exact payload bytes, so verification must operate on those exact bytes — re-serializing the parsed object first is the classic way to break an otherwise-correct signature.

```
   header.<base64url(payload)>.signature   ← what gets signed
   ─────────────────────────────────────
   Signature: eyJhbGc...   (in HTTP header)
   Body:      {"amount": ..., "uetr": ...}  (untouched on the wire)
```

Sign over content that includes the anti-replay fields (below) so the signature covers not just *what* was requested but *when* and *once*. The response is signed too: the receiver signs its acknowledgement so the originator holds durable, verifiable proof of the outcome. Non-repudiation is bidirectional or it is theatre — a signed instruction with an unsigned "accepted" gives you no evidence of what the counterparty committed to.

## Replay protection: nonce plus timestamp

A correctly signed message is still dangerous, because a *captured* correctly-signed message replays perfectly. An attacker who records one valid `pacs.008` and re-sends it has re-sent a genuine, fully-signed payment. Signing alone cannot stop this; the message is authentic every time. You need freshness and uniqueness, and the standard pairing is a timestamp plus a nonce, both inside the signed content.

The timestamp bounds *how old* a message may be. Reject anything outside a tight acceptance window — a couple of minutes typically — to cap the replay surface and bound how much state you must keep. The nonce guarantees *exactly once* within that window: cache every accepted nonce for at least the window length plus clock-skew slack, and reject any repeat.

```python
def check_freshness(msg):
    skew = abs(now() - msg.timestamp)
    if skew > ACCEPT_WINDOW:                 # e.g. 120s
        raise Reject("stale or future-dated")
    if not nonce_cache.put_if_absent(msg.nonce, ttl=ACCEPT_WINDOW + SKEW):
        raise Reject("replay: nonce already seen")
    # nonce TTL >= window, so no replay can outlive the timestamp check
```

The two checks are load-bearing together. Without the timestamp you would have to remember every nonce forever; without the nonce a message replayed inside the window sails through. Size the cache TTL to at least the acceptance window plus your worst-case clock skew so a message can never pass the timestamp check after its nonce has been evicted.

## Putting the verification order right

Order matters because each stage is cheaper and safer than the next, and you want to spend nothing on a bad request. Reject at the connection on an unenrolled or unpinned certificate. Then check freshness — timestamp window and nonce — before any cryptographic verification, so a replay flood costs you a cache lookup rather than a signature check. Then verify the detached signature against the enrolled signing key for the transport-identified party, confirming the two identities are consistent. Only then does the message reach business validation and the ledger.

Log the decision at every gate with the transport fingerprint, the signing key id, the nonce, and the outcome. When a dispute lands six months later, that trail — plus the counterparty's signed acknowledgement — is the difference between "we can prove what happened" and "we think it was fine." The cryptography is standard; the discipline of keeping the two identities separate, verifying in the cheap-to-expensive order, and signing both directions is what makes an interbank channel defensible.
