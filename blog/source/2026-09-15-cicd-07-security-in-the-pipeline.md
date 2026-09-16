# Security in the Pipeline

*The CI/CD pipeline is one of the most privileged systems in an engineering organization — it has access to source code, secrets, and the keys to production — which makes it a prime target. Worse, it can become the delivery mechanism for an attack: compromise the pipeline and you compromise everything it ships. This post is about securing the pipeline itself and building security into it, the heart of DevSecOps.*

Earlier posts built a fast, reliable, version-controlled pipeline. This one hardens it. Pipeline security has two faces: **securing the pipeline** (it's a high-value target) and **security in the pipeline** (shifting security checks left, into the flow). Both matter, and the recent wave of software-supply-chain attacks has made them urgent rather than optional.

## The pipeline is a privileged target

Step back and consider what the pipeline can touch: it reads all your source code, holds credentials to deploy to production, often has access to cloud accounts, package registries, and signing keys. It is, in effect, a machine with the combined privileges of your whole engineering org — and it runs code automatically on every commit.

That makes it an attacker's dream. If an attacker can influence what the pipeline runs — by compromising a dependency, a build tool, a pipeline config, or a token — they can inject malicious code into your builds, steal your secrets, or deploy their code to your production. This is the **software supply chain** attack surface, and it has produced some of the most damaging breaches of recent years precisely because it turns your trusted delivery system into the attacker's delivery system. Securing the pipeline is therefore not a nice-to-have; the pipeline's privilege makes it a first-class part of your attack surface.

## Securing the pipeline itself

Protecting the pipeline as the privileged system it is:

- **Least privilege for pipeline credentials.** The pipeline should hold the *minimum* access each job needs, scoped and short-lived. Prefer short-lived, workload-identity-based credentials (OIDC federation to your cloud) over long-lived static keys. A deploy job needs deploy rights; a test job needs none — don't give every job god-mode.
- **Secrets management, never secrets in code.** Credentials belong in a secrets manager or the CI system's encrypted secret store, injected at runtime — *never* committed to the repo (where they live in git history forever) and never printed in logs. Scan the repo and build output for leaked secrets.
- **Protect the pipeline definition.** Since the pipeline is code (post 6), changes to it must go through review and branch protection — an attacker who can silently edit `.github/workflows` can do anything the pipeline can. Require reviews on pipeline files specifically.
- **Pin and control dependencies.** Pin actions/images to specific digests (not moving tags), so a compromised upstream tag can't silently change what your pipeline runs. Be especially careful with third-party actions — they run with your pipeline's privileges.
- **Isolate and harden runners.** Untrusted code (e.g. from fork PRs) should run with no secrets and in isolation, so a malicious PR can't exfiltrate credentials. Ephemeral runners that are destroyed after each job limit persistence.

The theme mirrors the guardrails principle from AI security: assume a job *could* be compromised and limit what it can reach — least privilege, isolation, short-lived credentials.

## Shifting security left: security in the pipeline

The other half is building automated security *checks* into the pipeline so vulnerabilities are caught early — "shifting left," moving security from a late manual audit to an automated early gate:

- **SAST (Static Application Security Testing)** — scan your source code for security bugs (injection, unsafe patterns) on every change, like a security-focused linter.
- **SCA (Software Composition Analysis) / dependency scanning** — check your dependencies for *known vulnerabilities* (CVEs). Since most code in a modern app is third-party dependencies, this catches a huge share of real risk. Run it on every build and fail on critical vulnerabilities.
- **Secret scanning** — detect credentials accidentally committed, before they reach a shared branch.
- **DAST (Dynamic Application Security Testing)** — test the running application for vulnerabilities (typically against a staging deploy), catching issues static analysis can't.
- **Container/IaC scanning** — scan container images and infrastructure-as-code definitions for misconfigurations and vulnerable base images.

The value of putting these in the pipeline is that security becomes *continuous and automatic* rather than a rare manual gate — every change is checked, and problems are found when they're cheap to fix (at authoring time) rather than after release. The discipline point: tune these to fail on genuine high-severity findings and surface the rest as warnings, or alert fatigue makes developers ignore them — the same fail-safe-but-usable balance from guardrails.

## Supply chain integrity: provenance and signing

The frontier of pipeline security is proving that what you shipped is what you built — **supply chain integrity**:

- **SBOM (Software Bill of Materials)** — a complete inventory of everything in your artifact (every dependency and version). When a new CVE drops, an SBOM lets you instantly answer "are we affected?" instead of scrambling. Generate one for every build.
- **Artifact signing** — cryptographically sign your build artifacts (tools like Sigstore/cosign) so consumers can verify they came from your pipeline and weren't tampered with. Signing turns "trust me" into "verify it."
- **Provenance / attestation** — generate a tamper-evident record of *how* an artifact was built (which source, which pipeline, which steps). Frameworks like **SLSA** define levels of supply-chain assurance built on exactly this: verifiable provenance so a consumer can confirm an artifact was built from the expected source through the expected process.

Together these let you *prove* the integrity of your delivery, not just assert it — the direct defense against the supply-chain attacks that make the pipeline such a tempting target. They're increasingly expected (and in some sectors, required), and they're the natural endpoint of taking pipeline security seriously: not just guarding the pipeline, but producing cryptographic evidence of what it did.

## Key takeaways

- The pipeline is one of your **most privileged systems** (source, secrets, production keys, run automatically on every commit) — which makes it a prime target and a potential *delivery mechanism* for supply-chain attacks (compromise it and you compromise everything it ships).
- **Secure the pipeline**: least-privilege, short-lived (OIDC) credentials per job; secrets in a manager/encrypted store never in code or logs; review-protected pipeline definitions; pinned action/image digests; isolated/ephemeral runners with no secrets for untrusted (fork) code.
- **Shift security left** by building automated checks into the pipeline — **SAST** (source), **SCA/dependency scanning** (known CVEs — huge share of real risk), secret scanning, **DAST** (running app), and container/IaC scanning — so security is continuous and problems are caught when cheap to fix.
- Tune security gates to **fail on genuine high-severity findings** (warn on the rest) or alert fatigue makes developers ignore them.
- **Supply-chain integrity** is the frontier: generate an **SBOM** (instant "are we affected?" for new CVEs), **sign artifacts** (Sigstore/cosign — verify, don't trust), and produce **provenance/attestation** (SLSA levels) to cryptographically *prove* what you shipped was built from the expected source and process.

## Further reading

- [GitHub — Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [SLSA — Supply-chain Levels for Software Artifacts](https://slsa.dev/)
- [OWASP DevSecOps Guideline](https://owasp.org/www-project-devsecops-guideline/)
