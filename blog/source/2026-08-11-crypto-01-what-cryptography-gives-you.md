# What Cryptography Actually Gives You

*Most engineers reach for cryptography wanting "make this secure," but crypto doesn't provide "secure" — it provides four specific, separable guarantees, and using the wrong one (encrypting when you needed to authenticate, hashing when you needed to encrypt) is how most real-world crypto failures happen. This series is about using cryptography correctly as an engineer who builds on top of it, not about inventing it.*

Cryptography is one of the few areas where a small mistake — a reused nonce, a missing authentication tag, a comparison that leaks timing — silently destroys the entire guarantee while the code still appears to work. This series is a practical, engineer's tour of applied cryptography: what the primitives are, what each actually guarantees, how they combine into systems like TLS, and the pitfalls that turn correct-looking code into broken security. This first post frames the whole thing: what cryptography gives you, and the mindset that keeps you from misusing it.

## The four guarantees

"Secure" is not a cryptographic concept. Cryptography provides four distinct guarantees, and being precise about which one you need is the first skill:

- **Confidentiality** — no one but the intended party can *read* the data. This is what "encryption" gives you: the data is unintelligible to anyone without the key. It's the guarantee people usually mean by "encrypt it," but it's only one of four — and often not even the one they actually need.
- **Integrity** — the data hasn't been *altered*. You can detect any modification, whether accidental (corruption) or malicious (tampering). Confidentiality without integrity is dangerous: an attacker who can't read your data may still be able to flip bits in it in meaningful ways.
- **Authenticity** — the data really came from *who it claims to be from*. You can verify the origin, not just that the data is intact. Integrity and authenticity travel together (a MAC or signature gives both) but are conceptually distinct: integrity says "unchanged," authenticity says "unchanged *and* from this sender."
- **Non-repudiation** — the sender *cannot later deny* having sent it. This is stronger than authenticity and requires asymmetric signatures (only the sender's private key could have produced the signature, so they can't claim someone else did it). Symmetric authentication (a shared-key MAC) gives authenticity but *not* non-repudiation, because either party could have produced it.

The single most common applied-crypto mistake is conflating these. "I encrypted it, so it's safe" ignores integrity and authenticity — encryption alone doesn't stop tampering. "I hashed the password, so it's secure" confuses hashing (integrity/verification) with the actual requirement (slow, salted password storage). Naming the guarantee you need — confidentiality? integrity? authenticity? all three? — is the first and most clarifying step, and the rest of this series maps primitives onto these guarantees.

## The tools that provide them

Each guarantee maps to specific primitives (the rest of the series covers each in depth):

- **Confidentiality → encryption.** Symmetric encryption (AES, ChaCha20 — same key both ways, fast, for bulk data) and asymmetric encryption (RSA, ECC — public/private key pair, slow, for small data and key exchange).
- **Integrity → cryptographic hashes.** A hash (SHA-256) produces a fixed-size fingerprint; any change to the input changes the hash, so you can detect modification. (But a bare hash alone doesn't stop an attacker who can change *both* data and hash — hence MACs.)
- **Integrity + authenticity → MACs and signatures.** A MAC (HMAC) uses a shared secret key to produce an authentication tag: only someone with the key can produce or verify it, so it proves integrity *and* authenticity. A digital signature does the same with a private key, adding non-repudiation.
- **The combined tool: AEAD.** Because you almost always want confidentiality *and* integrity/authenticity together, modern crypto provides **authenticated encryption** (AES-GCM, ChaCha20-Poly1305) — one primitive that encrypts *and* authenticates in a single, hard-to-misuse operation. This is the default you should reach for, and the symmetric-encryption post explains why.

So the primitives aren't a random toolbox — they map onto the four guarantees. Knowing "I need confidentiality and integrity for this message" tells you "use an AEAD cipher," and "I need to prove this came from me and I can't deny it" tells you "use a digital signature." Matching the guarantee to the primitive is the core applied-crypto skill.

## The cardinal rule: don't roll your own

The most important rule in applied cryptography: **don't invent your own cryptographic algorithms or protocols, and don't implement the primitives yourself.** Use well-vetted, standard algorithms (AES, SHA-256, etc.) via well-vetted, standard libraries. This isn't gatekeeping — it's hard-won experience:

- **Crypto fails silently.** A broken cipher still produces ciphertext that looks random; a subtly-flawed protocol still completes handshakes. Unlike most bugs, cryptographic weaknesses don't announce themselves with a crash or wrong output — the code *works*, and the security is simply absent. You can't test your way to confidence.
- **The attack surface is adversarial and subtle.** Security depends on resisting a motivated attacker exploiting mathematical structure, side channels (timing, power), and edge cases most engineers never consider. Standard algorithms have survived years of expert cryptanalysis; your homemade one hasn't.
- **Implementation is as dangerous as design.** Even implementing a *correct* algorithm correctly is treacherous — timing side channels, padding oracles, nonce reuse. This is why you use vetted *libraries*, not just vetted algorithms. "Don't roll your own" applies to implementation, not just invention.

The engineer's job is not to create cryptography but to *use it correctly*: choose the right standard primitive for the guarantee you need, use a reputable library, and avoid the misuse patterns this series covers. That's both humbler and harder than it sounds — most crypto vulnerabilities are misuse of good primitives, not broken primitives.

## Kerckhoffs's principle: secrecy lives in the key

A foundational idea, from the 19th century and truer than ever: **a cryptographic system should be secure even if everything about it except the key is public.** The algorithm, the protocol, the source code — all can be known to the attacker; only the *key* is secret. Its consequences shape everything:

- **No security through obscurity.** Relying on a secret *algorithm* is fragile — algorithms leak (reverse engineering, insiders, publication), and once known, an obscure algorithm is usually weak. Real security rests on the key being secret and the algorithm being strong *even when public*.
- **Public algorithms are a strength.** This is *why* standard algorithms are trustworthy: AES and SHA-256 are fully public and have been attacked by the world's best cryptographers for years without breaking. Public scrutiny is what earns trust — the opposite of hiding your design.
- **Key management becomes the whole game.** If all secrecy lives in the key, then generating, storing, distributing, and rotating keys correctly *is* the security. This is why key management (a later post) is the hardest and most important operational part of applied crypto — a perfect algorithm with a leaked or badly-managed key is worthless.

Kerckhoffs's principle reframes the engineer's focus: not "keep my method secret" but "use a strong public algorithm and protect the key." It's the reason this series trusts public standards and devotes a whole post to key management.

## The mindset for the rest of the series

Applied cryptography rewards a specific mindset, which this series builds:

- **Be precise about the guarantee.** Always ask *which* of confidentiality/integrity/authenticity/non-repudiation you need — that determines the primitive. Vagueness ("make it secure") is where misuse begins.
- **Prefer high-level, misuse-resistant tools.** Reach for AEAD (authenticated encryption) over raw ciphers, established protocols (TLS) over hand-rolled ones, and libraries designed to be hard to misuse. The best crypto API is one you *can't* use wrong.
- **Assume the attacker knows everything but the key.** Design and reason as if the algorithm and code are public (they effectively are). Protect keys above all.
- **Respect the subtlety.** Crypto punishes small mistakes catastrophically and silently. Nonce reuse, missing authentication, non-constant-time comparison — each is a one-line error that voids the guarantee. The pitfalls post catalogs these; the whole series is about avoiding them.

With this framing — four guarantees, matched to primitives, using public standards via good libraries, with keys as the real secret — the rest of the series can go deep on each primitive and how they combine. Next: symmetric encryption, the workhorse of confidentiality, and why authenticated encryption is the default you should reach for.

## Key takeaways

- Cryptography doesn't provide "secure" — it provides four distinct, separable guarantees: confidentiality (can't be read), integrity (can't be altered undetectably), authenticity (provably from the claimed sender), and non-repudiation (sender can't later deny it) — and choosing the right one is the core skill.
- The guarantees map to primitives: confidentiality → encryption (symmetric AES/ChaCha20, asymmetric RSA/ECC); integrity → hashes; integrity+authenticity → MACs/signatures; and confidentiality+integrity together → AEAD (authenticated encryption like AES-GCM), which is the default to reach for.
- The cardinal rule is don't roll your own — neither invent algorithms/protocols nor implement primitives yourself — because crypto fails *silently* (broken crypto still produces plausible output), the attack surface is adversarial and subtle, and vetted libraries guard against implementation traps like timing side channels.
- Kerckhoffs's principle: a system must be secure even if everything but the key is public — so there's no security through obscurity, public standard algorithms are a strength (scrutiny earns trust), and key management becomes the whole game.
- The applied-crypto mindset: be precise about the guarantee, prefer high-level misuse-resistant tools (AEAD, TLS, good libraries), assume the attacker knows everything but the key, and respect that small mistakes silently void the guarantee.

## Further reading

- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Kerckhoffs's principle (Wikipedia)](https://en.wikipedia.org/wiki/Kerckhoffs%27s_principle)
- [Web Identity: OAuth, OIDC, and SAML — where these guarantees get applied](/blog/series/web-identity-oauth-oidc-and-saml/)
