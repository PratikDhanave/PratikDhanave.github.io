# Key Management: The Hardest Part

*Every cryptographic guarantee in this series ultimately rests on one thing: the key stays secret and available to exactly the right parties. That's not a math problem — it's an operational one, and it's where real systems fail. A perfect algorithm with a key committed to a Git repo, hardcoded in an image, or never rotated is worthless. Key management is the unglamorous discipline that decides whether all the cryptography actually protects anything.*

Kerckhoffs's principle told us all secrecy lives in the key. This post is about the consequence: **key management** — generating, storing, distributing, rotating, and destroying keys — is the hardest and most important operational part of applied cryptography. The algorithms are solved; managing keys well is where systems succeed or fail. Most real-world crypto breaches trace to key mismanagement, not broken algorithms.

## Why key management is the whole game

If everything secret lives in the key, then the key's lifecycle *is* the security. This reframes where an engineer should focus:

- **The algorithm is not the weak point.** AES and RSA aren't going to be broken on your watch. The realistic failure modes are all about keys: a leaked key, a weak key, a key that's never rotated after a suspected compromise, a key accessible to the wrong people. Attackers don't break the cipher; they steal the key.
- **Keys leak in mundane ways.** The classic disasters are operational, not cryptographic: an API key or private key committed to a Git repository (and living forever in history), hardcoded in source or a container image, printed in logs, pasted in a ticket, or left in an environment variable readable by every process. These are the *actual* ways crypto fails in practice.
- **Availability matters too.** Key management isn't only about secrecy — it's also about *not losing* keys. Lose the key that decrypts your backups and the data is gone as surely as if it were deleted. Key management must balance "no one unauthorized can access it" against "authorized users reliably can."

So the engineer's cryptographic responsibility is mostly key management: choosing where keys live, who can reach them, how they're rotated, and how they're protected — because that, not the algorithm, is what an attacker will target and what an operational mistake will expose.

## The key lifecycle

Keys have a lifecycle, and each stage has requirements:

- **Generation.** Keys must be generated from a **cryptographically secure random source** (CSPRNG) with adequate length. A predictable or low-entropy key is trivially broken regardless of algorithm — weak randomness is a real historical failure (the randomness post covers this). Let libraries/KMS generate keys; don't invent your own key-derivation from weak sources.
- **Storage.** This is the crux: keys must be stored where attackers can't reach them but authorized systems can. The rule is **never store keys in source code, config files in the repo, container images, or logs.** Instead use dedicated secret stores (below).
- **Distribution.** Getting keys to the systems that need them without exposure — solved cryptographically by key exchange (for session keys) and operationally by secret-management systems that deliver secrets to services at runtime rather than baking them in.
- **Rotation.** Keys should be **rotated** periodically and immediately on suspected compromise. Rotation limits the damage window: if a key is exposed, rotating it caps how long it's useful, and regular rotation limits how much data any single key protects. Designing systems so keys *can* be rotated without downtime is important (and often overlooked until a key must be rotated urgently).
- **Revocation and destruction.** Compromised keys and certificates must be revocable (the PKI post's CRL/OCSP), and retired keys securely destroyed so old copies don't linger as a liability.

Each stage is an operational discipline, and weakness at any stage undermines the whole. A strong key generated well but stored in a repo is compromised; a well-stored key never rotated after a breach stays a liability.

## Where keys should actually live

Since "don't put keys in code/config/images/logs" rules out the tempting places, where *do* they go? Purpose-built systems:

- **Secret managers / KMS.** Cloud **Key Management Services** (AWS KMS, Google Cloud KMS, Azure Key Vault) and secret managers (HashiCorp Vault, cloud secret managers) are dedicated systems for storing and controlling access to keys and secrets. They provide access control (only authorized identities can use a key), audit logging (who used which key when), and often *perform crypto operations without ever exposing the key* — you send data to be encrypted/decrypted and the raw key never leaves the service. This is far safer than handing keys to applications.
- **HSMs.** A **Hardware Security Module** is dedicated tamper-resistant hardware that generates and stores keys and performs crypto operations such that the key *never leaves the device* in plaintext. HSMs (backing many cloud KMS offerings) are the highest-assurance option for high-value keys — the key physically cannot be extracted.
- **Runtime secret injection.** Applications should receive secrets at *runtime* from a secret manager (via a secure API or injected into the environment by the platform), not have them baked into code or images. This keeps secrets out of source control and image layers and makes rotation possible without rebuilding.

The principle throughout: **minimize exposure of the raw key.** The best options (KMS/HSM) mean applications *use* keys without ever *holding* them — the key stays in a hardened service that does the crypto on request. When applications must hold keys, they get them at runtime from a managed store, never from committed code.

## Envelope encryption: a key pattern

A widely-used pattern that KMS enables, worth understanding, is **envelope encryption** — encrypting data with one key, and encrypting *that key* with another:

- **How it works.** You encrypt your data with a **data encryption key (DEK)** — a fast symmetric key. Then you encrypt the DEK itself with a **key encryption key (KEK)** that lives in a KMS/HSM and never leaves it. You store the encrypted data alongside the *encrypted* DEK. To decrypt, you ask the KMS to decrypt the DEK (using the protected KEK), then use the DEK to decrypt the data.

```text
Envelope encryption:
   data  --encrypt with-->  DEK (data key)      → stored: ciphertext
   DEK   --encrypt with-->  KEK (in KMS/HSM)    → stored: encrypted DEK
   decrypt: KMS decrypts the DEK with the KEK  →  DEK decrypts the data
   → the KEK never leaves the KMS; only the small DEK is sent for unwrapping
```

- **Why it's used.** It combines the strengths of both worlds: fast symmetric encryption of bulk data (with the DEK), while the *root of trust* (the KEK) stays locked in a KMS/HSM and is only ever used to encrypt/decrypt small data keys. Rotating the KEK re-protects all DEKs without re-encrypting all the data; each object can have its own DEK; and the KMS enforces access control and audit on every unwrap. This is how cloud storage encryption, database encryption, and many systems manage keys at scale.

Envelope encryption is the practical answer to "how do I encrypt terabytes with a key that never leaves an HSM?" — you don't; you encrypt the data with a data key and protect the *data key* with the HSM-bound key. It's the dominant real-world key-management pattern, and knowing it demystifies how cloud encryption works.

## Practical key management for engineers

Bringing it together, the operational discipline:

- **Never commit or hardcode keys.** No keys in source, repo config, images, or logs — the single most common and damaging mistake. Scan repos for accidentally-committed secrets; if a key ever touches a repo, treat it as compromised and rotate it.
- **Use a KMS/secret manager (or HSM for high-value keys).** Store keys in dedicated systems with access control and audit; prefer having the service perform crypto so the raw key never reaches your application. Inject secrets at runtime.
- **Generate keys properly and rotate them.** Use CSPRNG-based generation via libraries/KMS, adequate key lengths, and build rotation in from the start — including the ability to rotate without downtime and immediately on compromise.
- **Apply least privilege and audit.** Only the identities that need a key should be able to use it, and every use should be logged so you can detect and investigate misuse.
- **Don't lose keys.** Balance secrecy with recoverability — losing a key can mean losing data — via the durability guarantees of a managed KMS rather than ad-hoc copies.

Key management is the unglamorous discipline where cryptography meets operations, and it's where most real failures happen — not in the algorithms but in leaked, weak, unrotated, or lost keys. Generate properly, store in a KMS/HSM, inject at runtime, rotate, and never commit keys. The final post covers the remaining applied-crypto pitfalls — randomness, timing, and common mistakes — and a decision guide for the whole series.

## Key takeaways

- Because all secrecy lives in the key (Kerckhoffs), key management *is* the security — the realistic failure mode isn't a broken algorithm but a leaked, weak, unrotated, or lost key, so it's where engineers should focus.
- Keys leak in mundane operational ways — committed to Git (and stuck in history forever), hardcoded in source/images, printed in logs — so the absolute rule is never store keys in code, repo config, container images, or logs; and availability matters too (losing a key can mean losing data irrecoverably).
- The key lifecycle — generation (from a CSPRNG, adequate length), storage (in a dedicated store), distribution (runtime, not baked in), rotation (periodic and immediately on compromise), and revocation/destruction — each stage is an operational discipline where weakness undermines the whole.
- Keys should live in secret managers / cloud KMS (AWS KMS, Vault, etc.) or HSMs (tamper-resistant hardware where the key never leaves), which enforce access control and audit and often perform crypto so the raw key never reaches your app; applications get secrets injected at runtime.
- Envelope encryption is the dominant pattern: encrypt bulk data with a fast data key (DEK), encrypt the DEK with a key-encryption key (KEK) that never leaves a KMS/HSM, and store the encrypted DEK with the data — combining fast bulk encryption with an HSM-protected root of trust, easy KEK rotation, and per-object keys.

## Further reading

- [OWASP Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)
- [NIST SP 800-57: Recommendation for Key Management](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final)
- [TLS: where it all comes together (previous post)](/blog/posts/crypto-06-tls.html)
