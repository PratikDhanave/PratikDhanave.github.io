# TLS and HTTPS

*The "s" in HTTPS is TLS, and it does three things at once that most engineers conflate: it encrypts the connection, verifies you're talking to the real server, and detects tampering. Understanding how — the handshake, the certificates, the chain of trust — demystifies the padlock icon and the certificate errors that block deploys, and it's foundational to every secure connection you make.*

DNS gave you the server's address; TCP will connect you; but over the open internet, anyone on the path can read or alter unencrypted traffic. **TLS (Transport Layer Security)** is what makes a connection private and authenticated — it's the layer that turns HTTP into HTTPS. This post covers what TLS guarantees, how the handshake establishes a secure channel, how certificates prove server identity, and the performance cost that connects back to the connection-reuse theme.

## What TLS guarantees

TLS provides three distinct security properties on a connection, and separating them clarifies a lot:

- **Encryption (confidentiality)** — data is encrypted in transit, so anyone intercepting the traffic (on the network, at a router, on shared Wi-Fi) sees only ciphertext, not your data. This is what people usually mean by "secure," but it's only one of the three.
- **Authentication (identity)** — TLS verifies you're talking to the *real* server you intended, not an impostor. This is the certificate's job (below), and it's what prevents a man-in-the-middle from impersonating the server. Encryption without authentication is useless — you'd have a private conversation with an attacker.
- **Integrity (tamper-detection)** — TLS detects if data was modified in transit, so an attacker can't silently alter the bytes. You receive exactly what was sent, or the connection fails.

All three matter together: encryption keeps it private, authentication ensures it's the right party, integrity ensures it wasn't changed. HTTPS is simply HTTP running over a TLS-secured connection, gaining all three. A common mistake is thinking HTTPS is "just encryption" — the *authentication* (are you really talking to your bank?) is equally essential.

## The handshake: establishing a secure channel

Before encrypted data flows, TLS performs a **handshake** to agree on how to secure the connection and to verify the server's identity. Conceptually:

```text
(after the TCP handshake completes)
Client → Server:  "Hello" — TLS versions and cipher suites I support, random data
Server → Client:  "Hello" — chosen version/cipher, the server's CERTIFICATE, random data
Client:           verifies the certificate (is this really the server? — below)
Both:             use key exchange to derive a shared SESSION KEY (without ever
                  sending it across the wire)
→ from here, all data is encrypted with the shared session key
```

The handshake accomplishes two things: **negotiation** (agreeing on the TLS version and cipher suite both support) and **key establishment** (deriving a shared symmetric session key via key exchange, so both sides can encrypt/decrypt without the key ever traveling the network). The clever part is asymmetric cryptography letting two parties who've never met agree on a secret key over a public channel — after which they switch to fast symmetric encryption for the actual data.

The cost: the handshake takes **round-trips**, adding latency *on top of* the TCP handshake. This is the compounding setup cost from the TCP post — an HTTPS connection pays the TCP handshake *and* the TLS handshake before any application data. Modern TLS (version 1.3) reduced this to about one round-trip (down from two), and session resumption can skip most of it for repeat connections — but the principle stands: **new HTTPS connections have real setup latency, so reusing connections matters even more with TLS.** This is a major reason keep-alive, connection pooling, and HTTP/2/3 (later posts) are so valuable.

## Certificates and the chain of trust

The *authentication* property hinges on **certificates**. A TLS certificate is a document, presented by the server during the handshake, that binds a domain name to a cryptographic public key and is *signed* by a trusted authority. It's how the client answers "is this really `example.com`?" The mechanism is a **chain of trust**:

```text
Root CA (trusted, pre-installed in your OS/browser)
   │ signs
Intermediate CA
   │ signs
Server certificate (for example.com)
   → client verifies the chain up to a root it already trusts
```

- **Certificate Authorities (CAs)** are organizations trusted to vouch for identities. Your operating system and browser ship with a set of trusted **root CA** certificates pre-installed — the anchors of trust.
- **The server's certificate is signed** (directly or via intermediates) by a CA. During the handshake, the client verifies the signature chain up to a root it already trusts, confirming the certificate is legitimate and issued for this domain.
- **This is what defeats impersonation** — an attacker can't present a valid certificate for `example.com` because they can't get a trusted CA to sign one for a domain they don't control.

This chain of trust is why **certificate errors matter and must never be ignored**: an invalid, expired, self-signed, or wrong-domain certificate means the *authentication* guarantee is broken — you might be talking to an impostor. The browser warning ("your connection is not private") is TLS refusing to proceed because it can't verify identity. Two everyday realities follow:

- **Certificate expiry causes outages.** Certificates have validity periods and *expire*; a lapsed certificate breaks HTTPS for everyone, instantly. Expired certs are a shockingly common, entirely preventable cause of outages — automate renewal (e.g. via ACME/Let's Encrypt) so it never happens.
- **Don't disable certificate verification.** The tempting "just skip the cert check" to make an error go away discards the authentication guarantee entirely, opening you to man-in-the-middle attacks. Fix the certificate instead.

## TLS in practice for backend engineers

TLS shows up in day-to-day backend work in a few recurring ways:

- **Terminate TLS deliberately.** Often TLS is *terminated* at a load balancer or reverse proxy (the next-but-one post), which handles certificates and encryption, then forwards to backends — sometimes over plain HTTP inside a trusted network, sometimes re-encrypted. Know where in your architecture TLS ends.
- **Automate certificate management.** Use automated issuance and renewal (ACME/Let's Encrypt or your cloud's certificate manager) so certificates never silently expire — the single highest-value TLS operational practice.
- **Keep TLS versions current.** Use modern TLS (1.3, or at least 1.2) and disable old, insecure versions and ciphers; outdated TLS is a real vulnerability.
- **Reuse connections.** Because the TLS handshake adds setup latency, connection reuse and session resumption materially cut cost — reinforcing the connection-pooling lesson.
- **HTTPS everywhere.** Encrypt all traffic, not just "sensitive" pages — mixed HTTP/HTTPS leaks data and enables downgrade attacks, and there's no good reason to serve anything over plain HTTP today.

TLS is the security layer that makes the web trustworthy — private, authenticated, tamper-proof connections — at the cost of handshake latency that (again) rewards connection reuse. With a secure connection established, the next post covers what actually flows over it and how it evolved: HTTP, from 1.1 to 2 to 3.

## Key takeaways

- TLS provides three guarantees together — encryption (confidentiality), authentication (you're talking to the real server), and integrity (tamper detection); HTTPS is HTTP over TLS, and treating it as "just encryption" misses the equally vital authentication.
- The TLS handshake negotiates version/cipher and establishes a shared session key via asymmetric key exchange (the key never crosses the wire), then switches to fast symmetric encryption — costing round-trips on top of the TCP handshake (reduced but not eliminated in TLS 1.3).
- Authentication relies on certificates and a chain of trust: a CA-signed certificate binds a domain to a public key, and the client verifies the signature chain up to a pre-trusted root CA — which is what defeats server impersonation.
- Certificate errors must never be ignored (they mean the authentication guarantee is broken); expired certificates are a common preventable outage cause, so automate renewal (ACME/Let's Encrypt) and never disable verification to silence an error.
- In practice: know where TLS terminates (often at a load balancer/proxy), automate certificate management, keep TLS versions modern, reuse connections to amortize handshake latency, and serve HTTPS everywhere.

## Further reading

- [DNS (previous post)](/blog/posts/net-04-dns.html)
- [MDN — Transport Layer Security](https://developer.mozilla.org/en-US/docs/Web/Security/Transport_Layer_Security)
- [Web Identity: securing identity — TLS in the broader security picture](/blog/posts/identity-08-securing-identity.html)
