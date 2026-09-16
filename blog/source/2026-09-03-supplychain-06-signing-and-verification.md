# Signing and Verification

*Signing is how you turn "trust me, this artifact is authentic" into "verify it yourself." A cryptographic signature binds an artifact to its producer and proves it hasn't been tampered with since. But traditional signing has a painful key-management problem, and the modern answer — keyless signing with Sigstore — is what finally made artifact signing practical enough to be routine.*

Provenance says how an artifact was built; signing proves it's *authentically that artifact*, from the expected producer, unaltered. This post covers what signing gives you, the key-management problem that long kept it from being widely adopted, and how Sigstore's keyless model changed that — plus the verification half that makes signatures actually mean something.

## What signing proves

A **digital signature** on an artifact uses public-key cryptography to provide two guarantees (building on the cryptography-engineering fundamentals):
- **Integrity** — the artifact hasn't changed since it was signed. Any modification invalidates the signature. This directly defeats artifact/registry tampering (post 2): a swapped or altered artifact fails signature verification.
- **Authenticity** — the artifact was signed by a specific, identifiable producer (your pipeline, your organization). A consumer can verify it came from who it claims to.

The producer signs with a private key; anyone can verify with the corresponding public key. So "is this the real, unmodified artifact from the real producer?" becomes a cryptographic check, not a matter of trust. This is the integrity layer that complements SBOM (what's in it) and provenance (how it was built) — and note the SolarWinds lesson: signing alone isn't sufficient (a compromised build produces a signed-but-malicious artifact), which is why signing must be paired with provenance. Signing proves *authentic and unaltered*; provenance proves *built correctly*. You need both.

## The key management problem

Traditional signing has a well-known Achilles' heel: **managing the private keys**. To sign artifacts, you need signing keys, and those keys become a critical secret with hard problems:
- **Storage and access** — the key must be available to your pipeline to sign, but protected from theft. A stolen signing key lets an attacker sign malicious artifacts as you — catastrophic, because consumers *trust your signature*.
- **Rotation and revocation** — keys should rotate, and if one is compromised you must revoke it and re-establish trust, which is operationally painful.
- **Distribution** — verifiers need your public key, and must trust that it's *really* yours (a whole trust-establishment problem).

These frictions are why, for years, most software simply *wasn't* signed — the key management overhead wasn't worth it for most teams. The security control existed but adoption lagged because it was too painful. Solving that adoption problem is what the modern approach targets.

## Keyless signing with Sigstore

**Sigstore** is a project (with **cosign** as its signing tool) that made artifact signing dramatically easier by largely removing the long-lived-key problem — the "keyless" model:

- **Identity-based, ephemeral keys.** Instead of managing a long-lived signing key, you authenticate with an existing identity provider (an OIDC identity — your CI's workload identity, a developer's SSO). Sigstore issues a *short-lived* certificate tied to that identity, you sign with an ephemeral key, and the key is discarded. There's no long-lived secret to store, steal, rotate, or leak.
- **Transparency log.** Signatures are recorded in a public, append-only transparency log (Rekor). This provides a tamper-evident, auditable record that a given artifact was signed by a given identity at a given time — so you can detect if something was signed that shouldn't have been, and verify signatures against the log.
- **Ties signatures to identities, not keys.** Verification checks "was this signed by the expected *identity* (this GitHub Actions workflow, this org's CI)?" rather than "was this signed by this *key*?" — which is far more natural (you reason about *who*, not about key material) and eliminates the key-distribution trust problem.

The impact is adoption: by removing the key-management burden, Sigstore made signing something a pipeline can do automatically on every build, for free, without a key-management project. It turned signing from a rare, heavyweight practice into a routine one — which is what actually moves the needle on supply chain security, since a control nobody adopts protects nobody.

## Verification: the half that matters

Signing is only useful if someone *verifies*, and this is the step teams most often skip — producing signatures nobody checks. Verification is where the security actually happens:

- **Verify before use.** Consumers (your deploy step, your customers, downstream services) should verify the signature *before* trusting or running an artifact — checking it's signed by the expected identity and unaltered. An unverified signature is decoration.
- **Verify the identity, not just the presence of a signature.** "It's signed" is meaningless if you don't check *who* signed it. Verification must confirm the signer is the *expected* identity (your CI's workload identity), or an attacker's validly-signed-by-*someone* artifact passes. Policy: "only run artifacts signed by *our* pipeline's identity."
- **Enforce it as policy, in code.** Make verification a required, automated gate — a deployment admission check that rejects unsigned or wrongly-signed artifacts (e.g. cluster admission controllers verifying image signatures). Verification enforced by policy is what turns signing from a nice gesture into an actual control.
- **Verify the whole bundle.** Modern verification checks the signature *and* the attached attestations (provenance, SBOM from posts 4–5) together — confirming not just authenticity but that the artifact was built as expected and you know what's in it.

The maxim: **signing without verification is theater.** The value is entirely in the verify step — a signed artifact that nobody checks provides no protection. Build verification into your deploy gates and admission policies so every artifact is checked, automatically, before it runs.

## Key takeaways

- A **signature** gives **integrity** (unaltered since signing — defeats artifact tampering) and **authenticity** (from an identifiable producer), turning "is this the real, unmodified artifact?" into a cryptographic check — the integrity layer complementing SBOM (contents) and provenance (build process).
- Signing must be **paired with provenance**: signing alone is insufficient (a compromised build yields a signed-but-malicious artifact, the SolarWinds lesson) — signing proves *authentic/unaltered*, provenance proves *built correctly*.
- Traditional signing stalled on **key management** (storing/protecting, rotating/revoking, distributing long-lived signing keys) — which is why most software simply wasn't signed for years.
- **Sigstore/cosign** made signing routine via the **keyless model**: identity-based ephemeral keys (OIDC identity → short-lived cert, no long-lived secret), a public **transparency log** (Rekor) for auditable tamper-evidence, and verification against *identities* not keys — removing the adoption barrier.
- **Signing without verification is theater**: verify *before use*, verify the *expected identity* (not just "it's signed"), enforce it as an automated **policy gate** (e.g. admission control), and verify the whole bundle (signature + provenance + SBOM) — the security is entirely in the verify step.

## Further reading

- [Sigstore — keyless signing for software artifacts](https://www.sigstore.dev/)
- [SLSA — Supply-chain Levels for Software Artifacts](https://slsa.dev/)
