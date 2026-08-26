# Symmetric Encryption and Authenticated Encryption

*Symmetric encryption is the workhorse of confidentiality — the same fast primitive protecting your disk, your database fields, and every byte inside a TLS connection. But "encrypt this" is a trap: raw encryption alone doesn't stop tampering, block ciphers need a mode of operation, and modes need nonces that must never repeat. The single right answer for almost every case is authenticated encryption, and this post explains why.*

The previous post established that confidentiality comes from encryption. This post covers **symmetric encryption** — one shared key both encrypts and decrypts — which is fast, handles bulk data, and underlies nearly all practical confidentiality. But using it correctly means understanding block ciphers, modes of operation, nonces, and above all **authenticated encryption (AEAD)**, the misuse-resistant default. Getting this right (and knowing why the tempting shortcuts are broken) is core applied crypto.

## One key, both ways

Symmetric encryption uses a **single secret key** shared by both parties: encrypt with the key, decrypt with the *same* key. Its defining properties:

- **Fast.** Symmetric ciphers are extremely efficient — often hardware-accelerated (AES-NI instructions on modern CPUs) — so they encrypt gigabytes cheaply. This is why *bulk* data (files, disks, network streams) is always encrypted symmetrically, even in systems that also use public-key crypto.
- **The key-distribution problem.** The catch is inherent: both parties need the *same* secret key, so how do they agree on it without an eavesdropper learning it? You can't just send it over the wire. This problem is exactly what public-key cryptography (a later post) solves — asymmetric key exchange establishes a shared symmetric key, then symmetric encryption does the bulk work. That hybrid is how TLS and most real systems work.

The dominant symmetric cipher is **AES** (Advanced Encryption Standard) — a public, standardized, heavily-analyzed block cipher, hardware-accelerated, and the default choice. **ChaCha20** is a strong modern stream cipher, often preferred on platforms without AES hardware acceleration (some mobile/embedded). Both are excellent; you don't choose between them by security but by platform. And per "don't roll your own," you use these standard ciphers via a library — never invent one.

## Block ciphers need a mode

AES is a **block cipher**: it encrypts fixed-size blocks (16 bytes) at a time. But real data is longer than one block, so you need a **mode of operation** that defines how to encrypt many blocks. The mode matters enormously — and the naive one is catastrophically broken:

- **ECB (Electronic Codebook) — never use it.** ECB encrypts each block independently with the same key, so *identical plaintext blocks produce identical ciphertext blocks*. This leaks structure: an image encrypted with ECB still shows its outline, because repeated patterns stay visible. ECB is the canonical example of "encryption that doesn't actually hide the data." Never use ECB.

```text
ECB's flaw: same plaintext block → same ciphertext block, always
   plaintext:  [AAAA][BBBB][AAAA]  →  ciphertext: [X][Y][X]   ← repeats visible!
   an attacker sees where the data repeats — structure leaks
```

- **Modes need an IV/nonce.** Secure modes add a **nonce** or **IV** (initialization vector) — a value that makes each encryption unique, so encrypting the *same* plaintext twice yields *different* ciphertext (no pattern leakage). The nonce doesn't need to be secret, but it has a critical rule discussed below.

The lesson: you never just "AES-encrypt" data — you use AES *in a mode*, and the mode must randomize output via a nonce so identical plaintext doesn't reveal itself. And the right mode isn't a bare confidentiality mode at all — it's an *authenticated* one.

## Encryption alone is not enough: AEAD

Here's the crucial insight most "encrypt it" advice misses: **confidentiality without integrity is dangerous.** Plain encryption stops an attacker from *reading* the data, but often not from *modifying* it in meaningful ways. An attacker who flips bits in ciphertext can, with some modes, cause predictable changes in the decrypted plaintext — without ever knowing the key. And unauthenticated decryption can leak information through error behavior (padding oracle attacks). So you almost always need confidentiality *and* integrity/authenticity together.

The solution is **AEAD — Authenticated Encryption with Associated Data** — a single primitive that encrypts *and* authenticates:

- **It encrypts and produces an authentication tag.** On decryption, the tag is verified first; if the ciphertext was tampered with (even one bit), verification *fails* and decryption is refused. So you get confidentiality (can't read) *and* integrity/authenticity (can't tamper undetectably) from one operation.
- **"Associated data" is authenticated but not encrypted.** You can bind extra context (headers, metadata) to the ciphertext — it's not hidden, but it's protected from tampering and tied to this specific ciphertext.
- **The standard AEAD ciphers: AES-GCM and ChaCha20-Poly1305.** These are the modern defaults. AES-GCM (Galois/Counter Mode) is the most common; ChaCha20-Poly1305 pairs the ChaCha20 stream cipher with the Poly1305 authenticator. Both are what TLS 1.3 uses.

**The practical rule: for symmetric encryption, use an AEAD cipher (AES-GCM or ChaCha20-Poly1305) by default.** Don't use bare confidentiality-only modes (like AES-CBC) unless you have a specific reason and add a separate MAC correctly — and even then, AEAD is safer because it's one hard-to-misuse operation. AEAD embodies "prefer misuse-resistant tools": it makes the safe thing (authenticated encryption) the default thing.

## The nonce rule: never repeat

AEAD ciphers have one rule you must not break: **never reuse a nonce with the same key.** A nonce ("number used once") makes each encryption unique. Reusing a (key, nonce) pair is catastrophic — for AES-GCM, nonce reuse can leak plaintext relationships *and* completely break the authentication (allowing forgery). This is one of the most common and damaging real-world crypto mistakes:

- **Why it's dangerous.** The security proof of these modes *assumes* nonces never repeat under a given key. Break that assumption and the guarantees collapse — for GCM specifically, two messages under the same key+nonce can reveal the authentication key, letting an attacker forge messages.
- **How to get it right.** Either use a **random** nonce from a cryptographically secure RNG (safe as long as the nonce is large enough that random collision is negligible — GCM's 96-bit nonce is borderline for very high volumes), or use a **counter** that provably never repeats. Many good libraries handle nonces for you — prefer those. Never hardcode a nonce, never reuse one "because it's convenient," and never derive it from something that repeats.

The nonce rule is the archetype of applied crypto's subtlety: a correct algorithm, a correct library, and a single reused number silently destroys everything. Respecting it — and preferring libraries/APIs that manage nonces safely — is essential.

## Choosing and using symmetric encryption

Putting it together, the practical guidance:

- **Use AES-GCM or ChaCha20-Poly1305 (AEAD)** for almost all symmetric encryption — you get confidentiality and integrity in one misuse-resistant operation. AES-GCM where AES hardware acceleration exists (most servers/desktops); ChaCha20-Poly1305 where it doesn't (some mobile/embedded).
- **Never use ECB**, and avoid bare unauthenticated modes (CBC, CTR) unless you truly know why and pair them with a proper MAC — AEAD is the safer default.
- **Never reuse a nonce with the same key** — use random (from a CSPRNG) or counter nonces, ideally via a library that manages them.
- **Use a reputable library** (your language's standard crypto library, libsodium, the platform's Web Crypto / KMS) rather than assembling primitives yourself. The best APIs make nonce and tag handling automatic.
- **Remember the key still has to come from somewhere** — the key-distribution problem is real, solved by public-key crypto and key management (later posts). Symmetric encryption assumes you *have* a shared key; getting and protecting that key is the harder half.

Symmetric encryption is the fast engine of confidentiality, but "encrypt it" done right means AEAD with unique nonces via a good library — not raw AES, never ECB, never a reused nonce. Next: hashing, MACs, and the special case of storing passwords — where "just hash it" hides its own set of traps.

## Key takeaways

- Symmetric encryption uses one shared key to encrypt and decrypt; it's fast (hardware-accelerated AES, or ChaCha20 without AES hardware) and handles bulk data, but has the inherent key-distribution problem (both sides need the same secret) that public-key crypto solves.
- AES is a block cipher (16-byte blocks) that needs a *mode of operation*; ECB is broken because identical plaintext blocks produce identical ciphertext (structure leaks — the famous visible-image example), so secure modes use a nonce/IV to randomize output.
- Encryption alone is dangerous — confidentiality without integrity lets attackers tamper with ciphertext — so use AEAD (Authenticated Encryption with Associated Data): AES-GCM or ChaCha20-Poly1305 encrypt *and* authenticate in one operation, refusing to decrypt tampered data. This is the default to reach for.
- The nonce rule is absolute: never reuse a (key, nonce) pair — for AES-GCM, nonce reuse can leak plaintext and break authentication entirely (enabling forgery) — so use random (CSPRNG) or counter nonces, ideally managed by the library.
- Practical guidance: use AEAD by default, never ECB, never reuse a nonce, use a reputable library that handles nonces/tags, and remember the shared key must still be established and protected (the harder half, covered by public-key crypto and key management).

## Further reading

- [Authenticated encryption (Wikipedia)](https://en.wikipedia.org/wiki/Authenticated_encryption)
- [MDN: SubtleCrypto — the Web Crypto API for encryption in the browser](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto)
- [What cryptography actually gives you (previous post)](/blog/posts/crypto-01-what-cryptography-gives-you.html)
