# Public-Key Cryptography

*Symmetric encryption has a chicken-and-egg problem: to share a secret key securely, you seem to need a secure channel — which is what you were trying to build. Public-key cryptography is the astonishing idea that broke that loop: two mathematically-linked keys where knowing the public one doesn't reveal the private one. It's the foundation of key exchange, digital signatures, and essentially all secure communication over the open internet.*

Symmetric encryption and MACs both assume the parties already share a secret key — but establishing that key over an insecure network is the hard part. **Public-key (asymmetric) cryptography** solves it with a key *pair*: a public key anyone can know and a private key kept secret. This post covers what asymmetric crypto is, the main flavors (RSA, elliptic curve), key exchange (Diffie-Hellman), and how it combines with symmetric crypto in the hybrid model that real systems use.

## Two keys instead of one

Asymmetric cryptography uses a **mathematically-linked key pair**:

- A **public key**, which can be shared freely with anyone.
- A **private key**, which is kept secret by its owner.

The magic is the asymmetry: **what one key does, only the other can undo**, and knowing the public key doesn't let you derive the private key (it rests on math problems that are easy one way, infeasible to reverse). This enables two distinct capabilities depending on *which* key you use:

- **Encryption for confidentiality** — anyone can encrypt *to you* using your **public** key, and only you can decrypt with your **private** key. This solves confidential delivery to someone you've never shared a secret with: publish your public key, and anyone can send you something only you can read.
- **Signing for authenticity** — you sign with your **private** key, and anyone can verify with your **public** key. Since only you have the private key, a valid signature proves it came from you (and gives non-repudiation). This is digital signatures, the next post's topic.

This two-key structure is what breaks symmetric crypto's key-distribution deadlock: parties can establish trust and secrecy *without* a pre-shared secret, using freely-publishable public keys. It's one of the most consequential ideas in computing — essentially all internet security depends on it.

## RSA and elliptic curves

Two families of asymmetric crypto dominate, both public standards you use via libraries:

- **RSA** — the classic, based on the difficulty of factoring the product of two large primes. RSA can do both encryption and signatures and is widely deployed and well-understood. Its drawback is that security requires *large* keys (2048-bit or 3072-bit and up), which makes it comparatively slow and produces large keys/signatures.
- **Elliptic Curve Cryptography (ECC)** — based on the elliptic-curve discrete-logarithm problem, ECC achieves equivalent security with *much smaller* keys (a 256-bit ECC key is roughly comparable to a 3072-bit RSA key). Smaller keys mean faster operations and less data to transmit/store, so ECC is the modern preference — **ECDH** for key exchange and **ECDSA/EdDSA** (e.g. Ed25519) for signatures are standard in TLS 1.3 and modern systems.

You don't need to implement or deeply understand the math — you need to know that both are vetted standards, ECC is generally preferred today for efficiency, and key *size* matters (small RSA keys are broken; use recommended sizes). And critically, note what asymmetric crypto is *not* good for: it's **slow** and suited only to *small* amounts of data. You never encrypt a large file directly with RSA/ECC — which is exactly why the hybrid model exists.

## Key exchange: agreeing on a secret in the open

One of asymmetric crypto's most important uses isn't encrypting data directly — it's **key exchange**: two parties agreeing on a shared symmetric key over an insecure channel, without an eavesdropper learning it. **Diffie-Hellman** is the foundational algorithm:

- **The idea.** Each party generates a key pair and exchanges *public* values. Through the mathematics, each can combine their own private value with the other's public value to compute the *same* shared secret — but an eavesdropper who sees only the public values *cannot* compute it. Two parties derive a common secret in full view of an attacker, who can't reconstruct it.
- **It establishes a symmetric key.** The shared secret from Diffie-Hellman becomes the symmetric key used for fast AEAD encryption of the actual data. So DH solves the key-distribution problem: it *bootstraps* a symmetric key over an open network.
- **Ephemeral DH gives forward secrecy.** Modern protocols use *ephemeral* Diffie-Hellman (ECDHE) — a fresh key pair per session — so each session's key is independent. This gives **forward secrecy**: even if a long-term private key is later compromised, past sessions' keys can't be recovered (they were derived from ephemeral values that no longer exist). This is a major reason TLS 1.3 mandates ephemeral key exchange, and the TLS post revisits it.

Diffie-Hellman (today, elliptic-curve ECDHE) is how essentially every TLS connection agrees on its encryption key. It's the bridge between "we've never shared a secret" and "now we have a shared symmetric key" — the exact gap symmetric crypto couldn't cross alone.

## The hybrid model: best of both

Asymmetric and symmetric crypto have complementary strengths, so real systems combine them — the **hybrid model** underlying TLS and most secure systems:

- **Asymmetric crypto for establishment** — use public-key key exchange (ECDHE) to agree on a shared secret, and public-key signatures/certificates to authenticate the parties (prove you're talking to the real server, not an impostor — the PKI post's topic). This is done *once* per session and handles the hard problems: establishing a key without a pre-shared secret, and verifying identity.
- **Symmetric crypto for bulk data** — use the established shared key with a fast AEAD cipher (AES-GCM, ChaCha20-Poly1305) to encrypt all the actual data flowing back and forth. This is fast and handles arbitrary volume.

```text
Hybrid handshake (simplified):
   1. ECDHE key exchange  → both derive a shared symmetric key   (asymmetric, once)
   2. signature/certificate → verify the server's identity        (asymmetric, once)
   3. AES-GCM with that key → encrypt all the traffic             (symmetric, bulk)
```

This division of labor is why the hybrid model wins: asymmetric crypto does what only it can (key establishment and identity without pre-shared secrets) but is slow and small-data-only, so it's used sparingly; symmetric crypto is fast and handles bulk, so it does the actual encryption once a key is established. Understanding this split demystifies TLS: the expensive public-key work happens once in the handshake, then cheap symmetric encryption carries the conversation.

## What public-key crypto gives the engineer

Practically, asymmetric cryptography is what makes open-internet security possible, and as an engineer you rely on it constantly:

- **Secure connections without pre-shared secrets** — every HTTPS connection uses public-key key exchange to establish a symmetric key with a server you've never met. This is the everyday miracle asymmetric crypto enables.
- **Identity and trust** — public keys, wrapped in certificates (next posts), let you verify *who* you're talking to, not just encrypt to them — the basis of authentication on the web.
- **Use standards and correct key sizes** — prefer elliptic-curve algorithms (ECDHE, Ed25519/ECDSA) for efficiency, use RSA at recommended sizes if you use it, and always via vetted libraries. Never implement the math; do respect key-size guidance (undersized keys are broken).
- **Protect private keys above all** — the entire model rests on private keys staying private. A leaked private key means an attacker can impersonate you or decrypt to you — which is why key management (a later post) is critical.

Public-key cryptography is the idea that broke the key-distribution deadlock: two linked keys enabling key exchange (Diffie-Hellman → a shared symmetric key with forward secrecy) and signatures (identity and non-repudiation), combined with fast symmetric crypto in the hybrid model. Next: digital signatures and PKI — how public keys become verifiable *identities* through certificates and chains of trust.

## Key takeaways

- Public-key (asymmetric) cryptography uses a mathematically-linked key pair — a freely-shareable public key and a secret private key — where what one key does only the other undoes, and the public key doesn't reveal the private one, breaking symmetric crypto's key-distribution deadlock.
- It enables encryption (anyone encrypts to you with your public key; only your private key decrypts) and signing (you sign with your private key; anyone verifies with your public key — giving authenticity and non-repudiation); RSA (factoring-based, needs large keys) and elliptic curve (ECC — equivalent security with much smaller keys, the modern preference) are the two families.
- Asymmetric crypto is slow and small-data-only, so it's never used to encrypt bulk data directly; its key use is key *exchange* — Diffie-Hellman lets two parties derive a shared symmetric secret over an open channel that an eavesdropper can't compute.
- Ephemeral Diffie-Hellman (ECDHE — a fresh key pair per session) gives forward secrecy: compromising a long-term key later can't decrypt past sessions, which is why modern TLS mandates it.
- The hybrid model (TLS and most systems): asymmetric crypto establishes a key (ECDHE) and verifies identity (signatures/certificates) once per session, then fast symmetric AEAD encrypts all the bulk traffic — the expensive public-key work happens once, cheap symmetric encryption carries the conversation.

## Further reading

- [Diffie–Hellman key exchange (Wikipedia)](https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange)
- [Hashing, MACs, and passwords (previous post)](/blog/posts/crypto-03-hashing-macs-passwords.html)
- [Web Identity: OAuth, OIDC, and SAML — public keys underpin token signing](/blog/series/web-identity-oauth-oidc-and-saml/)
