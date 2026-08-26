# Digital Signatures and Public-Key Infrastructure

*A public key lets anyone encrypt to you and verify your signatures — but it raises a new question: how do you know a public key really belongs to who it claims? If an attacker can substitute their own public key for the bank's, all the cryptography in the world protects your connection to the attacker. Solving "whose key is this?" is what certificates, certificate authorities, and chains of trust exist for — the plumbing that makes public keys into verifiable identities.*

The previous post showed that signing with a private key and verifying with the public key proves authenticity. This post goes deeper on **digital signatures** and the crucial problem they raise: **how do you trust that a public key belongs to the right entity?** The answer is **PKI** (Public-Key Infrastructure) — certificates, certificate authorities, and chains of trust. This machinery is what makes HTTPS, code signing, and secure identity actually work.

## Digital signatures

A **digital signature** proves that a message came from the holder of a specific private key and hasn't been altered. It works by combining hashing (integrity) with asymmetric crypto (authenticity):

- **Signing.** The signer hashes the message and transforms that hash with their **private key**, producing a signature attached to the message. Only someone with the private key can produce a valid signature.
- **Verifying.** Anyone with the signer's **public key** can verify: they hash the message themselves and use the public key to check the signature against that hash. If it matches, the message is *unaltered* (integrity — the hash matches) *and* came from the private-key holder (authenticity), and the signer *cannot deny* signing it (non-repudiation — only their private key could have produced it).

Signatures give the strongest combination — integrity, authenticity, and non-repudiation — which is why they're used for software distribution (verify a download came from the real vendor), documents, blockchain transactions, and, centrally, **certificates**. Standard signature algorithms are RSA signatures, **ECDSA**, and **EdDSA** (Ed25519) — the elliptic-curve ones preferred for efficiency. As always, use vetted libraries. The key distinction from a MAC (previous topic): a signature uses a *private* key (asymmetric), so it gives non-repudiation and anyone can verify with the public key; a MAC uses a *shared* key, so only key-holders verify and there's no non-repudiation.

## The trust problem: whose key is this?

Signatures and public-key encryption both assume you *have the right public key*. But that assumption hides the central problem of public-key crypto: **how do you know a public key actually belongs to who it claims?**

Consider connecting to your bank. The bank sends its public key; you use it to establish a secure connection. But what if an attacker intercepts and substitutes *their own* public key? You'd establish a perfectly secure, encrypted connection — to the attacker (a man-in-the-middle). The cryptography works flawlessly and you're still compromised, because you trusted the wrong key. **Encryption to the wrong party is worthless.**

So the hard problem isn't the math of signatures or encryption — it's **binding a public key to a real-world identity** in a way you can trust. You need some way to be confident that "this public key really belongs to yourbank.com," even though you've never met the bank and are talking over a network an attacker may control. This is exactly what PKI solves, through certificates and a chain of trust.

## Certificates and certificate authorities

A **digital certificate** binds a public key to an identity, vouched for by a trusted third party:

- **A certificate is a signed statement.** It says, in effect, "this public key belongs to this identity (this domain name / organization)," and it is **digitally signed by a Certificate Authority (CA)**. The certificate contains the subject's identity, their public key, validity dates, and the CA's signature over all of it. The standard format is **X.509** (what TLS certificates use).
- **A Certificate Authority (CA) is a trusted issuer.** CAs are organizations trusted to verify identities and issue certificates. Before issuing, a CA verifies the requester controls the identity (for a domain certificate, that they control the domain). By signing the certificate, the CA vouches: "I've verified this public key belongs to this identity."
- **Verification uses the CA's public key.** Because the certificate is *signed* by the CA, anyone with the CA's public key can verify the certificate's signature — confirming the CA really issued it and it wasn't forged or altered. So checking a certificate reduces to a signature verification (the previous section) against the CA's key.

This is the core mechanism: instead of trusting a bare public key, you trust a *certificate* that a CA has *signed*, binding the key to an identity. The MITM attack fails because the attacker can't produce a certificate for yourbank.com signed by a trusted CA — they don't control the domain, so no CA will issue them one, and they can't forge the CA's signature. But this just moves the question: how do you trust the CA?

## Chains of trust and root CAs

You trust a CA's signature only if you have the CA's authentic public key — which is the same "whose key is this?" problem one level up. PKI resolves it with a **chain of trust** anchored in **root CAs**:

- **Root CAs are trust anchors.** A small set of **root certificate authorities** have their certificates (**root certificates**) pre-installed in your operating system and browser — shipped by the vendor, trusted by default. These roots are the foundation: you trust them *a priori* because they came with your trusted software.
- **Chains link back to a root.** Root CAs don't sign every website certificate directly; they sign **intermediate CA** certificates, which sign the actual server ("leaf") certificates. So a server's certificate is signed by an intermediate, whose certificate is signed by a root you already trust. Verification walks this **chain**: leaf → intermediate → root, checking each signature, until it reaches a trusted root.

```text
Chain of trust:
   Root CA (pre-trusted in your OS/browser)
      └─ signs → Intermediate CA
                    └─ signs → yourbank.com's certificate (leaf)
   Verify each signature up the chain to a trusted root → trust the leaf's key
```

- **Trust is transitive from the root.** If every signature in the chain is valid and it terminates at a root you trust, you trust the leaf certificate — and therefore the public key it binds to the identity. The whole system's trust flows down from the pre-installed roots.

This is how your browser decides a site's certificate is legitimate: it validates the chain up to a trusted root, checks the certificate isn't expired, matches the domain, and hasn't been revoked. If all pass, the padlock appears; if not, you get a certificate warning. The chain of trust turns a handful of pre-trusted roots into the ability to verify millions of identities.

## PKI in practice, and its limits

PKI is what makes secure identity work at internet scale, and as an engineer you interact with it constantly:

- **HTTPS/TLS.** Every HTTPS site presents an X.509 certificate; your browser validates the chain to establish you're talking to the real server before encrypting. The TLS post (next) shows where this fits in the handshake.
- **Getting certificates.** You obtain certificates for your own services from a CA — today often free and automated via **Let's Encrypt** and the ACME protocol, which verifies domain control and issues short-lived certificates automatically. Certificate management (renewal, storage of the private key) is a real operational task.
- **Revocation and expiry.** Certificates expire (forcing periodic renewal) and can be **revoked** if a private key is compromised (via CRLs or OCSP). Expiry is a common outage cause — an unrenewed certificate breaks a site. Automate renewal.
- **The trust model's limits.** PKI's security depends on CAs being trustworthy and roots being genuinely trustworthy — a compromised or malicious CA can issue fraudulent certificates, a real risk that mechanisms like Certificate Transparency logs help detect. And it rests entirely on private keys staying private (key management, later). PKI is powerful but not magic: it's a chain of human and operational trust, not just math.

Digital signatures give integrity, authenticity, and non-repudiation; PKI uses them to solve "whose key is this?" — binding public keys to identities via CA-signed certificates validated through a chain of trust up to pre-installed roots. This is the identity foundation of the secure web. Next: TLS — how signatures, certificates, key exchange, and symmetric encryption all come together in the protocol securing nearly every connection you make.

## Key takeaways

- A digital signature (sign with a private key, verify with the public key) proves integrity, authenticity, *and* non-repudiation — only the private-key holder could produce it and they can't deny it — unlike a MAC (shared key, no non-repudiation); standard algorithms are RSA, ECDSA, and EdDSA/Ed25519.
- Public-key crypto's central problem is trust, not math: if an attacker substitutes their public key for the real party's, you establish a flawlessly-encrypted connection to the attacker (man-in-the-middle), so you must reliably bind a public key to a real identity.
- A certificate (X.509) binds a public key to an identity and is digitally signed by a Certificate Authority (CA) that verified the identity; you verify the certificate by checking the CA's signature, reducing trust-in-a-key to a signature verification against the CA's key.
- The chain of trust anchors in root CAs whose certificates are pre-installed and trusted in your OS/browser; roots sign intermediates which sign leaf (server) certificates, and verification walks leaf → intermediate → root, so trust flows down from a small set of pre-trusted roots to millions of identities.
- PKI powers HTTPS/TLS, code signing, and secure identity; in practice you get certificates from CAs (often free/automated via Let's Encrypt/ACME), must handle renewal (expiry causes outages) and revocation (OCSP/CRL), and rely on CAs being trustworthy and private keys staying private — it's a chain of operational trust, not just cryptography.

## Further reading

- [X.509 certificates (Wikipedia)](https://en.wikipedia.org/wiki/X.509)
- [Public-key cryptography (previous post)](/blog/posts/crypto-04-public-key-cryptography.html)
- [Web Identity: OAuth, OIDC, and SAML — signed tokens and trust](/blog/series/web-identity-oauth-oidc-and-saml/)
