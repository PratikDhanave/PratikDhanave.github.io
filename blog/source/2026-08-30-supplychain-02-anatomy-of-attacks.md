# The Anatomy of Supply Chain Attacks

*To defend the supply chain you have to know how attackers get in — and there are more doors than most teams realize. Malicious packages, hijacked dependencies, dependency confusion, compromised build systems, and poisoned maintainer accounts each exploit a different link in the chain. This post is a field guide to the attack patterns, because each one maps to a specific defense.*

The previous post argued the supply chain is a primary target. This post categorizes *how* it gets attacked. The attacks fall into a few structural families based on which link they exploit — the package you pull, the way you resolve it, or the system that builds it. Knowing the taxonomy is what lets you defend systematically rather than reactively.

## Attacks on the packages you pull

The most common attacks target the open-source packages your project depends on:

- **Malicious packages (typosquatting).** An attacker publishes a package with a name very close to a popular one — `reqeusts` for `requests`, `python-sqlite` for a real one — hoping you'll fat-finger the name or copy a bad install command. The package looks legitimate but runs malicious code on install or import. Whole campaigns of thousands of typosquatted packages appear regularly on npm and PyPI.
- **Compromised legitimate packages.** An attacker takes over a real, widely-used package — by phishing or stealing a maintainer's credentials, or by a maintainer going rogue — and pushes a new version containing malicious code. Because it's a *trusted* package you already depend on, the malicious update flows straight into your builds on your next dependency update. This is especially dangerous with unpinned dependencies that auto-upgrade.
- **Protestware / maintainer sabotage.** A maintainer intentionally sabotages their own popular package (to make a political point or out of frustration), breaking or attacking everyone who depends on it. Rare but real, and a reminder that "it's a trusted popular library" is not a guarantee of safety.

The common thread: the malicious code arrives as a package you *chose* to trust, so the defense is about *what and how* you trust — vetting, pinning, and scanning (post 3).

## Dependency confusion

**Dependency confusion** is a subtle, high-impact attack worth its own section. Organizations often use *internal* private packages (`@mycompany/auth-utils`) alongside public ones. If your package manager is configured to check *both* a private registry and the public registry for a name, an attacker can publish a **public** package with the *same name as your internal one* and a higher version number. The resolver, seeing a higher version on the public registry, pulls the *attacker's* package instead of your internal one — injecting their code into your build.

It's insidious because you didn't typo anything and didn't add a bad dependency; your *existing* internal dependency name got hijacked by the resolution rules. The defenses are specific: scope/namespace internal packages, explicitly pin internal packages to your private registry, and configure package managers so a public package can never shadow an internal name.

## Attacks on the build and delivery system

Higher up the chain, attackers target the machinery that assembles and ships your software — the most damaging category because it can inject code into a *legitimate, signed* release:

- **Build system compromise.** As in the SolarWinds case, an attacker who gets into your CI/CD or build environment can modify code *during* the build — after review, before signing — so the malicious code ends up in the shipped artifact while the source looks clean. This defeats source-code review entirely, because the tampering happens between source and artifact. (Defenses: hardening and hermetic builds, post 7; provenance, post 5.)
- **Compromised build dependencies.** The compiler, build plugins, CI actions, and base images are themselves dependencies — and running with the build's high privileges. A malicious CI action or a poisoned base image can compromise everything the pipeline produces. This is why the CI/CD security post stressed pinning actions to digests.
- **Artifact/registry tampering.** If an attacker can modify artifacts in your registry or artifact store after they're built, they can swap a good artifact for a bad one. (Defense: signing and verification, post 6.)

Build-system attacks are the apex threat because they turn your trusted, audited pipeline into the injection point, producing malicious output that carries all the legitimacy of a real release.

## Attacks on people and infrastructure

Underneath the technical attacks are the human and infrastructure links:
- **Account takeover** — phishing or credential theft against a maintainer or a developer with publish/deploy rights. Most package compromises start here. (Defense: MFA everywhere, hardware keys, least privilege.)
- **Registry / infrastructure compromise** — attacking the package registry or artifact host directly.
- **Social engineering the maintainer chain** — an attacker slowly gains trust and commit rights on an open-source project, then introduces a subtle backdoor (the pattern seen in the xz-utils incident). This is a long-game attack on the human trust that open source runs on, and it's the hardest to detect because the malicious contributor *is* a trusted maintainer by the time they strike.

These human-layer attacks are the foundation of many technical ones — most package and build compromises begin with a stolen or socially-engineered credential.

## Mapping attacks to defenses

The value of this taxonomy is that each family points to a specific defense the rest of the series covers:

| Attack family | Primary defense |
|---|---|
| Malicious/typosquatted packages | dependency vetting, scanning, lockfiles (post 3) |
| Compromised legitimate package | pinning, SBOM + fast vuln response (posts 3–4) |
| Dependency confusion | namespacing + registry configuration (post 3) |
| Build system compromise | hardened/hermetic builds + provenance (posts 5, 7) |
| Compromised build deps | pin actions/images to digests (post 7) |
| Artifact tampering | signing + verification (post 6) |
| Account/maintainer compromise | MFA, least privilege, human vigilance |

No single control covers all of them, which is why supply chain security is inherently defense-in-depth. You inventory what you depend on, verify how it was built, sign what you ship, harden the build, and protect the humans — because the attacker only needs one weak link, and there are many.

## Key takeaways

- Package-level attacks arrive as packages you *chose* to trust: **typosquatting** (near-miss names), **compromised legitimate packages** (hijacked maintainer accounts pushing malicious updates — dangerous with unpinned auto-upgrading deps), and maintainer sabotage.
- **Dependency confusion** hijacks your *internal* package names: an attacker publishes a public package with the same name and a higher version, and the resolver pulls theirs — defended by namespacing internal packages and pinning them to your private registry.
- **Build-system attacks are the apex threat** — compromising CI/CD (SolarWinds-style) injects malicious code between source and artifact, defeating code review and producing a *legitimate, signed* malicious release; compromised build deps (actions, base images) and artifact/registry tampering are related.
- Underneath the technical attacks are **human/infrastructure links** — account takeover (where most package compromises start), registry compromise, and long-game maintainer social engineering (xz-utils pattern) — the hardest to detect.
- Each attack family maps to a specific defense, so supply chain security is inherently **defense-in-depth**: vet/scan/pin dependencies, configure registries, harden builds, verify provenance, sign artifacts, and protect the humans — the attacker needs only one weak link.

## Further reading

- [Supply chain attack — overview](https://en.wikipedia.org/wiki/Supply_chain_attack)
- [SolarWinds compromise — overview](https://en.wikipedia.org/wiki/SolarWinds)
- [OpenSSF — Open Source Security Foundation](https://openssf.org/)
