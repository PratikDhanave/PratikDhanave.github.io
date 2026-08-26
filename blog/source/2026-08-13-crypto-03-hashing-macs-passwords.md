# Hashing, MACs, and Storing Passwords

*"Just hash the password" is advice that's simultaneously right and dangerous — right that you never store plaintext, dangerous because a fast cryptographic hash like SHA-256 is exactly the wrong tool for passwords. Hashing, message authentication, and password storage are three different jobs that all involve hashing, and confusing them is a classic source of real breaches.*

The integrity guarantee comes from hashing. This post covers **cryptographic hash functions**, how they combine with a key to give authenticity (**MACs/HMAC**), and the special, frequently-botched case of **password storage** — where ordinary hashing is actively wrong and you need deliberately-slow password hashing. These are distinct tools that share the word "hash," and telling them apart is essential applied crypto.

## Cryptographic hash functions

A **cryptographic hash function** takes any input and produces a fixed-size output (a *digest* or *fingerprint*) — SHA-256 produces 256 bits regardless of input size. Its security properties are what make it cryptographic (not just any hash like a CRC):

- **Deterministic** — the same input always produces the same digest, so you can verify data by recomputing and comparing.
- **One-way (preimage resistance)** — given a digest, it's infeasible to find an input that produces it. You can't "reverse" a hash to recover the input. (This is why hashing is *not* encryption — there's no key and no decryption; it's a one-way fingerprint, not a reversible transformation.)
- **Collision resistant** — it's infeasible to find two *different* inputs with the *same* digest. This is what lets a digest stand in for the data: if the digest matches, the data is (practically) unchanged.
- **Avalanche effect** — a tiny change in input (one bit) produces a completely different digest, so any modification is obvious.

Use **SHA-256** (or SHA-3, or BLAKE2/BLAKE3) — standard, vetted hashes. **Do not use MD5 or SHA-1** for security; both are broken (practical collisions found) and survive only in legacy non-security contexts. Hashes give *integrity*: publish a file's SHA-256, and anyone can verify the file wasn't altered by recomputing it. They're also the building block for MACs, signatures, and more. But note a bare hash's limit: it detects *accidental* change and lets you verify against a *trusted* digest — but if an attacker can change *both* the data and the published hash, a bare hash proves nothing. Closing that gap needs a key.

## From integrity to authenticity: MACs and HMAC

A bare hash gives integrity only if the digest itself is trustworthy. To get *authenticity* — proof the data came from someone who holds a secret — you combine a hash with a **secret key**, producing a **MAC (Message Authentication Code)**:

- **A MAC is a keyed fingerprint.** The sender computes a tag over the message using a shared secret key; the receiver, holding the same key, recomputes and checks it. Only someone with the key can produce a valid tag, so a matching tag proves both **integrity** (unchanged) *and* **authenticity** (from someone with the key). An attacker without the key can't forge a valid tag for altered data.
- **HMAC is the standard construction.** You don't build a MAC by naively concatenating key and message and hashing (that has subtle flaws). **HMAC** is the proven standard way to turn a hash (HMAC-SHA256) into a secure MAC — use it rather than inventing your own keyed-hash scheme (again: don't roll your own).
- **MAC vs signature.** A MAC uses a *shared* secret, so it gives authenticity but *not* non-repudiation — either party could have produced the tag. A digital signature (later post) uses a *private* key, so only one party could have produced it, adding non-repudiation. Choose based on whether you need "provably from this specific party who can't deny it" (signature) or just "from someone with our shared key" (MAC).

MACs are why AEAD ciphers include an authentication tag (it's a MAC over the ciphertext), why API requests are often signed with HMAC, and how integrity+authenticity are enforced in countless protocols. When you need "this data is unchanged *and* from a trusted source," a MAC (HMAC) is the tool — not a bare hash.

## Passwords: where ordinary hashing is wrong

Now the frequently-botched case. You must never store passwords in plaintext — that's obvious. The trap is thinking "so I'll SHA-256 them." **A fast cryptographic hash is the wrong tool for passwords**, and here's why:

- **Fast is bad here.** SHA-256 is designed to be *fast* — which means an attacker who steals your hash database can try *billions* of password guesses per second on a GPU. Because real passwords have low entropy (people pick guessable ones), fast hashing lets attackers crack most of them quickly. The very speed that makes SHA-256 good for integrity makes it bad for passwords.
- **Unsalted hashes enable precomputation.** If you hash passwords without a unique **salt**, identical passwords produce identical hashes, and attackers can use precomputed tables (rainbow tables) to reverse common passwords instantly. A **salt** — a unique random value per password, stored alongside the hash — ensures identical passwords hash differently and defeats precomputation.

The correct approach: a **slow, salted password-hashing function** designed specifically for this:

- **Use a purpose-built password hash: Argon2, scrypt, or bcrypt** (Argon2 is the modern recommendation; bcrypt is a long-standing solid choice). These are deliberately *slow* and *resource-intensive* (memory-hard, in Argon2/scrypt's case), with a tunable **work factor** — so each guess costs an attacker real time and memory, turning "billions of guesses per second" into a trickle. They also handle salting for you.
- **Tune the work factor** so hashing takes a noticeable fraction of a second on your hardware — slow enough to cripple attackers, fast enough for legitimate logins — and raise it over time as hardware improves.

So password storage is *not* the integrity use of hashing — it's a distinct problem needing a distinct tool. "Hash the password" is right in spirit (never store plaintext, the operation is one-way) but wrong in specifics if you reach for SHA-256. The right answer is Argon2/scrypt/bcrypt with per-password salts and a tuned work factor.

## Three jobs, three tools

The through-line: hashing appears in three different jobs, and using the right variant matters:

- **Integrity / fingerprinting** → a fast cryptographic hash (SHA-256): verify data is unchanged against a trusted digest. Fast is good here.
- **Integrity + authenticity** → a keyed hash / MAC (HMAC-SHA256): prove data is unchanged *and* from someone with the shared secret. The key is what adds authenticity.
- **Password storage** → a slow, salted password hash (Argon2/scrypt/bcrypt): make each guess expensive so stolen hashes resist cracking. Slow is the entire point.

Confusing these is a classic failure: using SHA-256 for passwords (too fast, crackable), using a bare hash where you needed a MAC (no authenticity — attacker changes data and hash), or using a slow password hash for bulk integrity (needlessly slow). Match the job to the tool: fast hash for integrity, HMAC for authenticated integrity, deliberately-slow salted hash for passwords. Next: public-key cryptography, which solves the key-distribution problem that symmetric encryption and MACs both assume away.

## Key takeaways

- A cryptographic hash (SHA-256, SHA-3, BLAKE2/3) maps any input to a fixed-size, deterministic, one-way, collision-resistant digest with an avalanche effect — giving *integrity* (detect any change) — and it's not encryption (no key, no reversal). Avoid broken MD5/SHA-1 for security.
- A bare hash only proves integrity against a *trusted* digest; if an attacker can alter both data and hash it proves nothing — so authenticity requires a key.
- A MAC combines a hash with a shared secret key to give integrity *and* authenticity (only a key-holder can produce a valid tag); HMAC is the standard construction — don't invent your own keyed hash. A MAC gives authenticity but not non-repudiation (shared key), unlike a signature.
- Ordinary fast hashing is *wrong* for passwords: SHA-256's speed lets attackers try billions of guesses/sec on stolen hashes, and unsalted hashes enable rainbow-table precomputation — so use a per-password random salt and a purpose-built slow hash.
- Password storage needs Argon2 (modern), scrypt, or bcrypt — deliberately slow/memory-hard with a tunable work factor and built-in salting — tuned to take a noticeable fraction of a second; the three jobs (integrity → fast hash, authenticity → HMAC, passwords → slow salted hash) each need their own tool.

## Further reading

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Symmetric encryption and AEAD (previous post)](/blog/posts/crypto-02-symmetric-encryption.html)
- [Web Identity: OAuth, OIDC, and SAML — how authentication systems use these](/blog/series/web-identity-oauth-oidc-and-saml/)
