# Webhook Security — Signatures, Replay Windows, and the Attack Surface Nobody Audits

*A webhook endpoint is a public URL that accepts POSTs and changes state in your systems — which is to say, it's an unauthenticated write API unless you make it otherwise. The security model is well understood and regularly skipped: verify signatures correctly (several popular ways to do it wrong), bound the replay window, and remember that on the provider side, delivering webhooks means making HTTP requests to arbitrary customer URLs — an SSRF machine by design. This post covers both directions of the attack surface.*

This post is the [API Security](/blog/series/api-security/) series' missing chapter for the callback direction — where the usual model (you authenticate callers) inverts into *you authenticate payloads*.

## Receiver side: authenticate the payload, not the caller

An unverified endpoint accepts state changes from anyone who learns the URL — and URLs leak (logs, config repos, browser history). Forged events are not exotic: a crafted `payment.succeeded` against an unverified endpoint is an order-for-free primitive. The defense stack:

- **HMAC signatures, verified correctly.** The provider signs each delivery (shared secret, typically HMAC-SHA256 over the raw body, carried in a header); the receiver recomputes and compares. The *correctly* carries weight, because the known failure modes recur everywhere: verify over the **raw bytes received**, not a re-serialized parse (serializers reorder keys and normalize whitespace — your recomputation diverges on legitimate payloads, and teams "fix" it by disabling verification); compare with a **constant-time function**, because early-exit string comparison leaks matching prefixes as a timing oracle; and parse the signature header's **scheme and version** rather than assuming one signature (providers rotate schemes, send multiple signatures during rotation).
- **Timestamps and the replay window.** A valid signed payload captured once is valid forever unless freshness is enforced. Providers include a signed timestamp; receivers reject deliveries older than a small tolerance (minutes). That bounds replay to a window — and post 3's dedup store closes even that: a replayed event ID is a duplicate, already harmless. Signature + timestamp + dedup is the full stack; any one alone has holes.
- **Secret lifecycle.** Webhook secrets are production credentials: stored in secret managers (not code, not dashboards' screenshot history), scoped per endpoint (one leaked secret shouldn't validate forgeries everywhere), and rotated — which requires the dual-signature overlap window above, so build verification to try a secret *list*, not a secret.
- **Fail closed, log the forgeries.** Verification failure is a 4xx and a security log line, not a warning-and-process. A spike in signature failures is either your bug (deploy diverged on raw-body handling) or someone probing — both worth knowing within minutes.

Defense in depth rounds it out: TLS always (the signature authenticates, but plaintext still leaks payloads), provider IP allowlists *as a layer* (brittle alone — ranges change), and the quiet rule that **the payload is untrusted input even after verification** — authenticity is not well-formedness; it still gets schema validation before touching your systems. And if your webhook consumers feed LLM-based automation, remember the [prompt-injection surface](/blog/series/guardrails-and-prompt-injection-defense/): a verified event body can still carry adversarial *content*.

## Provider side: you built an SSRF machine

Delivering webhooks means your infrastructure makes POSTs to URLs customers typed in — the textbook server-side request forgery setup. A malicious (or compromised) customer registers `http://169.254.169.254/latest/meta-data/` or `http://internal-admin:8080/` and your delivery workers obligingly probe your own network, from inside, with your egress identity. The defenses are specific: **resolve-then-validate** destination IPs against private/link-local/metadata ranges — and pin the validated IP for the actual connection, because DNS can change between check and connect (the classic rebinding TOCTOU); **egress-isolate** delivery workers in network segments with no route to internal services, so validation bugs fail safe; **bound the response handling** — tight timeouts, no redirect-following (or re-validation per hop), capped response reads, and never echoing response bodies back to the customer (that's a read-SSRF oracle); and **rate-limit per destination**, because your retry fleet (post 2) aimed at a victim URL is a small DDoS cannon with your reputation on it.

The takeaway: webhook security is payload authentication plus egress hygiene. Receivers verify **HMAC over raw bytes, constant-time, scheme-aware, against a rotatable secret list**, enforce a **signed-timestamp replay window** with dedup closing the remainder, treat secrets as production credentials, fail closed loudly — and still schema-validate, because authentic ≠ safe. Providers accept that webhook delivery is **SSRF by design** and contain it: resolve-validate-pin destinations, egress-isolated workers, bounded non-redirecting responses never echoed back, per-destination rate limits. Both sides audited, the public POST endpoint stops being the soft underbelly it usually is.

## Key takeaways

- An unverified endpoint is an **unauthenticated write API**; forged `payment.succeeded` is the canonical exploit.
- Signature verification fails in known ways: verify **raw received bytes** (never re-serialized), compare **constant-time**, parse **scheme/version**, support a **secret list** for rotation.
- Freshness stack: signed **timestamp window** (minutes) bounds replay; post 3's **dedup** closes it; secrets live in managers, scoped and rotated; failures are 4xx + security telemetry.
- Verified ≠ safe: schema-validate payloads, and treat event content feeding LLM automation as an injection surface.
- Provider side is **SSRF by design**: resolve-validate-**pin** IPs (rebinding), egress-isolated workers, bounded/no-redirect/no-echo responses, per-destination rate limits so the retry fleet can't be aimed.

## Further reading

- [HMAC — the keyed-hash construction webhook signatures use](https://en.wikipedia.org/wiki/HMAC)
- [Server-side request forgery — the provider-side attack class](https://en.wikipedia.org/wiki/Server-side_request_forgery)
