# Applied Cryptography: Pitfalls and a Decision Guide

*The primitives in this series are unbreakable in practice — and yet crypto keeps failing in the real world. That's the paradox of applied cryptography: almost every vulnerability is a misuse of a sound primitive, not a broken one. A predictable random number, a comparison that returns early, a reused nonce, a missing authentication check — each is a one-line mistake that silently voids the guarantee. This closing post catalogs the pitfalls that matter and distills the whole series into a decision guide.*

We've covered the primitives (encryption, hashing, MACs, public-key crypto, signatures) and the systems that compose them (TLS, PKI, key management). This final post steps back to the failure modes — the **pitfalls** where correct primitives get misused — and provides a **decision guide** mapping needs to tools. Because in applied crypto, knowing the pitfalls is as important as knowing the primitives: the primitives rarely break, but their misuse constantly does.

## Randomness: the silent foundation

Cryptography depends utterly on **unpredictable randomness** — keys, nonces, IVs, salts, tokens all must be unguessable — and weak randomness is a catastrophic, silent failure:

- **Use a CSPRNG, never a regular RNG.** A cryptographically secure pseudo-random number generator (CSPRNG) produces output an attacker cannot predict. A regular random function (the default `random()` in many languages, seeded predictably) is *not* secure — its output can be predicted, so keys or tokens generated from it can be guessed. Using the wrong RNG for security is a classic, invisible bug: the output *looks* random, but an attacker can reproduce it.
- **Where to get it.** Use your platform's cryptographic RNG (`/dev/urandom`, the OS CSPRNG, your language's `secrets`/`crypto`-grade random API), or let your crypto library/KMS generate keys and nonces. Never build keys, session tokens, password-reset tokens, or nonces from a non-cryptographic RNG or a predictable seed (like the current time).
- **Why it's so dangerous.** Weak randomness undermines *everything* downstream — a perfect cipher with a predictable key is trivially broken; unguessable tokens become guessable. And nothing about the output reveals the flaw. Predictable-randomness failures have caused real, serious breaches (predictable session tokens, guessable keys).

Randomness is the silent foundation under every other guarantee. Getting it wrong breaks the strongest algorithm invisibly — so always use a CSPRNG, and prefer letting vetted libraries handle key/nonce generation for you.

## Timing attacks and constant-time comparison

A subtle but real class of pitfall: **side channels**, where secret information leaks not through the algorithm's output but through its *behavior* — most commonly *timing*:

- **The classic: comparing secrets with early-exit equality.** A normal string/byte comparison returns *as soon as it finds a difference*. If you compare a user-supplied MAC/token against the correct one this way, the comparison takes slightly *longer* the more leading bytes match — and an attacker measuring these tiny timing differences can recover the correct value byte by byte. A one-line `==` can leak a secret.
- **The fix: constant-time comparison.** For comparing secrets (MACs, tokens, password hashes' outputs), use a **constant-time comparison** function that always takes the same time regardless of where/whether bytes differ. Crypto libraries provide these (e.g. `hmac.compare_digest`, `crypto.timingSafeEqual`, `subtle.ConstantTimeCompare`) — use them for any secret comparison, never a plain equality operator.
- **Beyond comparison.** Side channels extend to timing in the crypto operations themselves (which is another reason to use vetted library implementations that are written to be constant-time) and, in extreme threat models, to power/cache side channels. For most engineers, the actionable rule is: use library implementations, and use constant-time comparison for secrets.

Timing attacks epitomize applied crypto's subtlety: the algorithm is correct, the output is correct, and yet a secret leaks through *how long the code runs*. It's why "compare the token" must be a constant-time compare, and why you use vetted implementations.

## A catalog of common misuses

Beyond randomness and timing, a handful of misuse patterns cause a large share of real crypto vulnerabilities — worth internalizing as an anti-pattern checklist:

- **Encryption without authentication.** Using a confidentiality-only cipher (or a bare mode like CBC) without integrity protection, allowing tampering and padding-oracle attacks. *Fix: use AEAD (AES-GCM, ChaCha20-Poly1305).*
- **Nonce/IV reuse.** Reusing a (key, nonce) pair, which breaks AEAD confidentiality and authentication. *Fix: unique nonces (random from CSPRNG, or counter), ideally library-managed.*
- **Fast hashing for passwords.** Using SHA-256 (fast, crackable) instead of a slow salted password hash. *Fix: Argon2/scrypt/bcrypt with per-password salts.*
- **Bare hash where a MAC is needed.** Trusting a hash for authenticity when an attacker can change both data and hash. *Fix: HMAC with a secret key.*
- **Weak/legacy algorithms.** MD5, SHA-1, DES, RC4, ECB mode, small RSA keys, old TLS versions — all broken or weak. *Fix: modern standards (SHA-256+, AES-GCM, TLS 1.3, adequate key sizes).*
- **Rolling your own.** Custom algorithms, custom protocols, or hand-assembled primitive combinations. *Fix: vetted algorithms via vetted libraries and standard protocols.*
- **Key mismanagement.** Hardcoded/committed keys, no rotation, weak key generation (the key-management post). *Fix: KMS/secret managers, rotation, CSPRNG generation.*
- **Not verifying certificates.** Disabling TLS certificate validation (a shockingly common "fix" for connection errors) — which silently allows man-in-the-middle attacks. *Fix: always validate certificates; never disable verification in production.*

Nearly every item is a *misuse of a sound primitive*, which is the core lesson: the primitives are strong; the vulnerabilities are in how they're used. Recognizing these anti-patterns — and their fixes — is most of practical crypto security.

## The post-quantum horizon

One forward-looking note worth an engineer's awareness: **quantum computing** threatens current *public-key* cryptography. A sufficiently powerful quantum computer could break RSA and elliptic-curve crypto (via Shor's algorithm), undermining today's key exchange and signatures. The state of things:

- **Asymmetric crypto is the concern; symmetric is largely fine.** Quantum attacks hit public-key crypto (RSA, ECC) hardest. Symmetric crypto (AES) and hashes are far more resistant — roughly, doubling key sizes addresses the (weaker) quantum speedup against them. So the disruption is concentrated in key exchange and signatures.
- **Post-quantum cryptography (PQC) is arriving.** New quantum-resistant algorithms have been standardized (NIST's post-quantum standardization selected algorithms like ML-KEM/Kyber for key exchange and ML-DSA/Dilithium for signatures), and adoption is beginning, including hybrid schemes that combine classical and post-quantum key exchange in TLS.
- **The "harvest now, decrypt later" motivation.** Because an attacker could record encrypted traffic today and decrypt it once quantum computers mature, there's real urgency for *forward-looking* protection of long-lived secrets — a reason the transition to PQC is already underway rather than deferred.

You don't need to act on this today for most systems, but you should *know* it's coming: current public-key crypto has a shelf life, PQC standards exist, and the migration will be a real engineering effort over the coming years. It's the one place where "use the current standard" comes with an asterisk about the future.

## The decision guide

To close the series, a practical mapping from *what you need* to *what to use* — the applied-crypto cheat sheet:

- **Encrypt data (confidentiality + integrity)** → **AEAD**: AES-GCM or ChaCha20-Poly1305, with unique nonces, via a library. (Not bare AES, never ECB.)
- **Verify data is unchanged (integrity)** → a cryptographic **hash** (SHA-256). Against untrusted parties who could change both → a **MAC (HMAC)**.
- **Store passwords** → a slow salted password hash: **Argon2** (preferred), scrypt, or bcrypt — never a fast hash.
- **Prove authenticity + non-repudiation** → a **digital signature** (Ed25519/ECDSA/RSA). For shared-secret authenticity without non-repudiation → **HMAC**.
- **Establish a shared key over a network** → **key exchange** (ephemeral ECDHE), giving forward secrecy — as inside TLS.
- **Secure a connection** → **TLS 1.3** (don't build your own secure channel); validate certificates.
- **Bind a public key to an identity** → **certificates + PKI**; obtain via a CA (Let's Encrypt/ACME).
- **Store/protect keys** → a **KMS/secret manager** (or HSM for high-value keys); envelope encryption for data at scale; never commit keys; rotate them.
- **Generate keys/nonces/tokens** → a **CSPRNG**, or let the library/KMS do it.
- **Compare secrets** → a **constant-time comparison**, never `==`.
- **Above all** → use **standard algorithms via vetted libraries and protocols**; don't roll your own; be precise about which guarantee you need.

That last line is the series in one sentence: cryptography gives four specific guarantees, delivered by standard primitives that are strong when used correctly and silently broken when misused — so the engineer's job is to name the guarantee, choose the standard tool, use a vetted library, and avoid the well-known pitfalls. Do that, and the cryptography actually protects what you meant it to.

## Key takeaways

- Almost every real crypto vulnerability is *misuse* of a sound primitive, not a broken primitive — so knowing the pitfalls matters as much as knowing the algorithms, and each pitfall is typically a one-line, silent failure.
- Randomness is the silent foundation: keys, nonces, salts, and tokens must come from a CSPRNG (or library/KMS), never a regular predictable RNG — weak randomness invisibly breaks even a perfect cipher and has caused real breaches.
- Side channels leak secrets through behavior, not output: comparing secrets (MACs, tokens) with early-exit `==` leaks them via timing, so use constant-time comparison functions, and use vetted library implementations written to be constant-time.
- Common misuses to avoid: encryption without authentication (use AEAD), nonce reuse, fast hashing for passwords (use Argon2/scrypt/bcrypt), bare hash instead of a MAC, weak/legacy algorithms (MD5/SHA-1/ECB/old TLS), rolling your own, key mismanagement, and disabling certificate validation (silent MITM).
- Quantum computing threatens current public-key crypto (RSA/ECC) but not symmetric crypto much; post-quantum standards (ML-KEM/Kyber, ML-DSA/Dilithium) now exist and migration is beginning, motivated by "harvest now, decrypt later" — know it's coming. Use the decision guide: name the guarantee, pick the standard tool (AEAD, HMAC, Argon2, signatures, ECDHE, TLS 1.3, KMS, CSPRNG, constant-time compare), and use vetted libraries.

## Further reading

- [NIST Post-Quantum Cryptography project](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Key management: the hardest part (previous post)](/blog/posts/crypto-07-key-management.html)
