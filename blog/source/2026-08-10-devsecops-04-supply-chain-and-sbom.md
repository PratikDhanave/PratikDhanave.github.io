# Software Supply Chain Security and SBOMs

*Securing everything you didn't write — from finding known-vulnerable dependencies with SCA, to generating an SBOM you actually act on, to proving provenance with signatures and SLSA so you know and verify what you ship.*

---

Open any modern application and read the code you actually wrote. It's the small part. The rest — the framework, the HTTP client, the JSON parser, the crypto library, the logging shim, and the hundreds of packages *those* pull in — is code you inherited. A typical service ships thousands of third-party components, most of them arriving as **transitive dependencies**: the libraries your libraries depend on, several levels deep, that you never chose and often can't name.

That inherited code is your attack surface. Software supply chain security is the discipline of defending it — not by rewriting everything from scratch, but by knowing exactly what you ship, proving where it came from, and refusing to ship anything you can't account for. This post walks the full chain: finding vulnerable components (SCA), pinning and updating them, the threat model that makes this urgent, the SBOM that inventories it all, and the provenance and signing that let you *verify* rather than merely *hope*.

---

## The modern app is mostly dependencies

Software Composition Analysis (SCA) is the practice of inventorying your dependencies and matching them against known-vulnerability databases. When a CVE is published against a library — say a deserialization flaw in a widely used parser — an SCA scanner tells you whether that library is in your dependency graph, at what version, and whether a fixed version exists.

Three tools dominate the open-source SCA space:

- **Trivy** (Aqua Security) — scans filesystems, container images, and repositories for vulnerable OS packages and language dependencies, and flags license issues.
- **Grype** (Anchore) — a vulnerability scanner that pairs naturally with Syft's inventory output.
- **Dependabot** (GitHub) — runs continuously against your repository, opens pull requests to bump vulnerable or outdated dependencies, and surfaces alerts in the security tab.

A first scan is usually sobering. Run one against an established codebase and you'll see findings you didn't introduce and can't easily trace to code you wrote:

```bash
# Scan a container image for known-vulnerable packages and misconfigurations
trivy image myorg/payments-api:1.4.2

# Scan the current project's dependency manifests directly
trivy fs .

# Grype reading an image, filtered to fixable findings only
grype myorg/payments-api:1.4.2 --only-fixed
```

**The gotcha:** your transitive dependencies are your attack surface too. It's tempting to scan only your direct dependencies — the ones in your `package.json`, `go.mod`, or `requirements.txt` — but a vulnerability three levels deep still gets compiled into your binary and shipped in your image. The exploit doesn't care that you never typed the package name. SCA is only useful when it walks the *full resolved graph*, including everything the resolver pulled in on your behalf.

---

## Pinning, lockfiles, and updating discipline

Knowing what's vulnerable is step one. Step two is controlling *which exact versions* you build against — because "we depend on version 4.x" is not a fact, it's a range, and ranges float.

A **lockfile** records the exact resolved version (and usually a content hash) of every dependency, direct and transitive. `package-lock.json`, `poetry.lock`, `Cargo.lock`, `go.sum`, and `uv.lock` all serve this role: they turn "some compatible version" into "this precise version, verified by hash." Commit the lockfile, and every build — yours, your teammate's, your CI runner's — resolves to the identical graph.

Pinning creates an obvious tension with staying current. Pin too loosely and a malicious or broken update slips in silently; pin too tightly and you fall behind on security fixes. The resolution is **updating discipline**, not paralysis:

- Pin exact versions via lockfiles so builds are reproducible.
- Let Dependabot (or Renovate) propose upgrades continuously as small, reviewable PRs.
- Gate those PRs behind your test suite and SCA scan so a bump can't merge if it breaks tests or introduces a new CVE.
- Treat a security patch differently from a feature bump — the former is urgent, the latter can batch.

The goal is a codebase that updates *often and safely*, not one frozen out of fear or one that auto-merges everything blindly.

---

## The supply-chain threat model

Vulnerable dependencies are the accidental risk — a maintainer shipped a bug, someone found it, a CVE was filed. The *deliberate* risk is more interesting and harder to catch, because the attacker is targeting the path between the code and your build, not the code's logic. The main classes:

- **Typosquatting** — a malicious package published under a name a hair's breadth from a popular one (`reqeusts` for `requests`, a hyphen swapped for an underscore). One typo in a manifest and you install the attacker's package.
- **Dependency confusion** — an attacker publishes a package to a *public* registry using the name of one of your *internal* private packages. If your resolver checks the public registry and prefers the higher version number, it pulls the attacker's code instead of yours.
- **Compromised maintainer or package** — an attacker gains control of a legitimate, trusted package (through stolen credentials, a hijacked account, or social engineering into maintainer status) and ships malware in a routine-looking update. Everyone who upgrades inherits it.
- **Malicious install hooks** — package managers run scripts at install time (`postinstall`, `setup.py`). Code that runs *during installation* executes on developer laptops and CI runners with whatever privileges those have, before any of your tests get a chance to look at it.
- **Compromised build system** — the attacker doesn't touch the source at all. They subvert the machine that *builds* the artifact, injecting malicious code between clean source and the shipped binary. The published source stays innocent; the artifact is poisoned.

The last two categories are the ones that have produced the most consequential real-world incidents. The class of attack where a long-trusted, widely embedded component is quietly backdoored — as seen in the compromise of the **xz/liblzma** compression library — shows how a single trusted dependency deep in the stack can become a system-wide threat. And the class where a **build/distribution pipeline itself is subverted** — the pattern behind the **SolarWinds** compromise — shows that you can review every line of source and still ship malware, because the poison entered *after* the source was clean. These are categories worth internalizing, not incident post-mortems to recite: they're precisely why the rest of this post shifts from *detecting* bad code to *proving* good provenance.

---

## SBOM: a bill of materials for software

You can't secure what you can't enumerate. A **Software Bill of Materials (SBOM)** is a formal, machine-readable inventory of every component in a piece of software — names, versions, suppliers, hashes, and often license and relationship data. It's the "ingredients label" for your build.

Two standards dominate, and both are widely supported:

- **SPDX** — an ISO-standardized format originally focused on license compliance, now a general-purpose SBOM format.
- **CycloneDX** — an OWASP project designed from the start around security use cases, with strong support for vulnerability and dependency relationships.

You generate SBOMs from tools rather than by hand. **Syft** (Anchore) is a common choice — it inspects a filesystem or container image and emits an SBOM in either format:

```bash
# Generate a CycloneDX SBOM from a container image
syft myorg/payments-api:1.4.2 -o cyclonedx-json > sbom.cdx.json

# Or SPDX from the current source tree
syft dir:. -o spdx-json > sbom.spdx.json

# Then feed the SBOM straight into a vulnerability scan
grype sbom:sbom.cdx.json
```

Why the sudden urgency? Customers and regulators now *require* SBOMs. Enterprise procurement increasingly asks vendors for one before purchase, and public-sector guidance — notably the U.S. executive direction that drove NIST's secure-software work — has pushed SBOMs from nice-to-have toward baseline expectation. When the next `xz`-class disclosure lands, the organizations that can answer "are we affected, and where?" in minutes are the ones with SBOMs on file for everything they run.

**The gotcha:** an SBOM you generate but never scan or act on is compliance theater. A JSON file sitting in an artifact bucket does nothing. The value is realized only when you *feed it back* — re-scan stored SBOMs against fresh vulnerability data as new CVEs are published, so that a component which was clean at build time gets re-flagged the day a flaw in it goes public. An SBOM is a living query surface, not a checkbox you tick at release.

---

## Provenance and integrity: prove where it came from

Detection tells you whether *known* bad things are present. It says nothing about whether the artifact in your registry is the one your pipeline actually produced from your actual source. That's the job of **provenance** (a verifiable record of how and from what an artifact was built) and **integrity** (cryptographic proof the artifact hasn't changed since).

**SLSA** (Supply-chain Levels for Software Artifacts, pronounced "salsa") is a framework that grades build integrity in escalating levels. At an intuition level, rather than memorizing the exact tier definitions:

- **Lower levels** ask you to produce *provenance* — a signed statement describing what was built, from which source, by which builder.
- **Higher levels** demand that provenance be generated by the *build platform itself* (not something a developer can forge), on **hardened, isolated builders**, so the provenance is trustworthy and the build is resistant to tampering.

The direction of travel matters more than the numbers: you move from "we assert this is legit" toward "the platform cryptographically proves it, and a compromised individual can't fake it."

**Signing** is how integrity gets attached. **Sigstore** and its `cosign` tool let you sign artifacts and, notably, do it with **keyless signing** — short-lived certificates tied to an OIDC identity (your CI's workload identity, say) instead of a long-lived private key someone can steal:

```bash
# Sign a container image (keyless, using the pipeline's OIDC identity)
cosign sign myorg/payments-api@sha256:9f2a...c1

# Verify a signature before you deploy
cosign verify \
  --certificate-identity-regexp '.*@myorg\.com' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  myorg/payments-api@sha256:9f2a...c1
```

Notice both commands reference the image by its `sha256:` **digest**, not by a tag. That's deliberate.

**The gotcha:** pinning to a floating tag means your "verified" build can change under you. A tag like `:latest` — or even `:1.4` — is a mutable pointer; whoever controls the registry can repoint it at a different image after you've reviewed and signed the one you meant. Pin by **digest** (`@sha256:...`), which names the exact content and cannot be repointed, and verify the signature against that digest. This is the same lesson that runs through container and CI security generally: a name you can move is not an identity you can trust. Verify content, not labels.

---

## Harden the build system itself

Signing and provenance are only as trustworthy as the machine that produces them. If your build runner is long-lived, shared, and writable, an attacker who gets a foothold on it can sit and wait.

**The gotcha:** the build system is part of the supply chain — a compromised CI runner signs malware with your key. Once the attacker controls the environment where signing happens, every downstream verification *passes*, because the artifact really was signed by your legitimate identity. Your consumers can't tell the difference. The defense is to make the builder hard to compromise and impossible to persist in:

- **Ephemeral builders** — spin up a fresh, clean environment per build and destroy it after. Nothing an attacker plants survives to the next run.
- **Isolation** — builds shouldn't share mutable state, caches an attacker can poison, or network access they don't need.
- **Least privilege for signing identities** — use short-lived, workload-scoped credentials (the keyless model above) so there's no durable signing key to exfiltrate.
- **Provenance from the platform** — have the build platform, not a user-controllable step, emit the provenance, so a compromised job step can't forge a clean record.

This is exactly what SLSA's higher levels are pushing you toward, and it's why "we sign our artifacts" is a weaker claim than "we sign our artifacts on ephemeral, isolated builders with platform-generated provenance."

---

## Policy: fail the build

None of this helps if the results are advisory. The payoff comes from turning findings into **gates** — conditions that make the pipeline fail and stop a release. A reasonable baseline: fail on high-severity known-vulnerable dependencies, fail if the SBOM can't be generated, and refuse to deploy anything whose signature doesn't verify against the expected identity and digest.

Here's a CI sketch tying the pieces together — SCA scan, SBOM generation, and a signature-verify gate:

```yaml
# Illustrative CI pipeline — adjust tool invocations to your runners
jobs:
  build-and-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # 1. SCA gate: fail the build on high/critical known vulns
      - name: Scan source for vulnerable dependencies
        run: trivy fs --severity HIGH,CRITICAL --exit-code 1 .

      - name: Build image
        run: docker build -t myorg/payments-api:${{ github.sha }} .

      # 2. Generate an SBOM and keep it as a release artifact
      - name: Generate SBOM
        run: syft myorg/payments-api:${{ github.sha }} -o cyclonedx-json > sbom.cdx.json

      - name: Re-scan the SBOM against current vuln data
        run: grype sbom:sbom.cdx.json --fail-on high

      # 3. Sign the image by digest (keyless, via the pipeline identity)
      - name: Sign image
        run: cosign sign $(cat image.digest)

  deploy:
    needs: build-and-scan
    runs-on: ubuntu-latest
    steps:
      # 4. Verify gate: refuse to deploy anything unsigned or unexpected
      - name: Verify signature before deploy
        run: |
          cosign verify \
            --certificate-identity-regexp '.*@myorg\.com' \
            --certificate-oidc-issuer https://token.actions.githubusercontent.com \
            $(cat image.digest)
```

The exact flags vary by tool version — check the current docs rather than copying these verbatim — but the *shape* is the point: scan, inventory, sign by digest, and verify before deploy, with each step able to fail the pipeline.

---

## Provenance beats detection

If there's one idea to carry out of here, it's this: **provenance beats detection**. Scanning for known-vulnerable components is necessary and you should absolutely do it — but it's inherently a game of catch-up. It can only find the *known* bad, and it can't tell you whether the artifact in front of you is the one your pipeline actually built. A deliberate attacker, the xz or SolarWinds kind, produces something that looks clean to a scanner precisely because the badness was introduced outside the source a scanner reads.

Provenance flips the question from "is anything wrong with this?" to "can I prove this is exactly what I meant to ship, built the way I meant to build it, from the source I reviewed?" When you can answer that — SBOM in hand, signature verified against a pinned digest, provenance emitted by a hardened builder — you're no longer hoping the scanner caught everything. You *know and verify what you ship*.

| Layer | Question it answers | Tools |
|---|---|---|
| SCA | Do I ship any *known*-vulnerable components? | Trivy, Grype, Dependabot |
| Pinning / lockfiles | Am I building the *exact* versions I reviewed? | lockfiles, digest pinning |
| SBOM | *What*, precisely, is in this artifact? | Syft (SPDX / CycloneDX) |
| Signing / integrity | Has the artifact changed since I built it? | Sigstore / cosign |
| Provenance | *How and from what* was it built, provably? | SLSA, cosign attestations |
| Build hardening | Can the build itself be trusted? | ephemeral, isolated builders |

---

## Key takeaways

- **Most of your code is inherited, and all of it is attack surface.** Scan the full transitive graph, not just direct dependencies — a vuln three levels deep still ships.
- **Pin exact versions and update on discipline, not fear.** Lockfiles make builds reproducible; automated PRs gated by tests and SCA keep you current safely.
- **Know the deliberate threats.** Typosquatting, dependency confusion, compromised maintainers, malicious install hooks, and build-system compromise (xz-, SolarWinds-class) are why detection alone isn't enough.
- **An SBOM is only useful if you act on it.** Generate with Syft in SPDX or CycloneDX, and re-scan stored SBOMs as new CVEs land — otherwise it's compliance theater.
- **Pin by digest and verify signatures.** A floating tag can be repointed under you; sign and verify by `sha256:` digest so "verified" stays verified.
- **The build system is part of the supply chain.** Ephemeral, isolated builders and platform-generated provenance stop a compromised runner from signing malware with your key.
- **Provenance beats detection.** Prove what you ship; don't just scan for what you already know is bad.

---

## Further reading

- [SLSA — Supply-chain Levels for Software Artifacts](https://slsa.dev/) — the framework, levels, and provenance model.
- [Sigstore](https://www.sigstore.dev/) and [cosign](https://docs.sigstore.dev/cosign/signing/overview/) — keyless signing and verification of artifacts.
- [CycloneDX](https://cyclonedx.org/) and [SPDX](https://spdx.dev/) — the two dominant SBOM formats.
- [Syft](https://github.com/anchore/syft), [Grype](https://github.com/anchore/grype), and [Trivy](https://trivy.dev/) — SBOM generation and vulnerability scanning.
- [NIST Secure Software Development Framework (SSDF, SP 800-218)](https://csrc.nist.gov/Projects/ssdf) — the U.S. baseline for secure development and supply-chain practices.
- [OpenSSF](https://openssf.org/) — cross-industry open-source supply-chain security guidance and tooling.
