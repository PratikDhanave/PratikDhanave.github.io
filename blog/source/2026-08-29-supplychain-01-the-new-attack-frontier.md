# The Software Supply Chain: The New Attack Frontier

*You don't just ship the code you wrote — you ship the code your dependencies wrote, and their dependencies, and the build system that assembled it all. That entire chain is your attack surface, and attackers have noticed. Software supply chain attacks target the trusted process by which software is built and delivered, and they've become one of the most damaging classes of breach precisely because they weaponize trust. This series is about defending that chain.*

Most security effort goes into the code a team writes. But in a modern application, the code you wrote is a thin shell over a vast mass of code you didn't — open-source dependencies, their transitive dependencies, base images, build tools, CI plugins. The **software supply chain** is everything and everyone that touches your software on its way from source to production, and it is now a primary target. This opening post explains why, and frames the defenses the rest of the series builds.

## What the supply chain is

Your software's supply chain includes far more than your source code:
- **Direct dependencies** — the libraries you explicitly import.
- **Transitive dependencies** — the dependencies of your dependencies, often hundreds deep, most of which you've never heard of.
- **Base images and system packages** — the OS layers and tools your containers build on.
- **Build tools and CI/CD** — compilers, package managers, the pipeline itself, its plugins and actions.
- **The people and infrastructure** — maintainers, package registries, artifact stores, signing keys.

A vulnerability or compromise *anywhere* in that chain can end up in your production software. And the chain is enormous: a typical application's dependency tree pulls in code from thousands of contributors you've never vetted, running with your application's privileges. You are, in effect, trusting all of them.

## Why it's the new frontier

Attackers follow the path of least resistance and highest leverage, and the supply chain offers both:

- **Leverage: compromise one, hit thousands.** Instead of breaking into one target, an attacker compromises a widely-used dependency or a build system and rides it into *every* downstream user. One poisoned package can reach thousands of organizations at once. This asymmetry — one compromise, mass impact — is why supply chain attacks are so attractive.
- **Trust: the attack rides your trusted process.** Your build pipeline is *supposed* to pull dependencies and produce artifacts you trust. A supply chain attack turns that trusted machinery into the delivery mechanism, so the malicious code arrives through the front door, signed and shipped by your own systems. It bypasses defenses aimed at outside attackers because it's not coming from outside — it's coming from your dependencies and tools.
- **Blind spots: you can't see what you don't inventory.** Most teams can't fully answer "what's actually in our software?" — which transitive dependencies, which versions. You can't defend an attack surface you can't enumerate, and the supply chain is mostly invisible by default.

The result is a class of attack that's high-impact, hard to detect, and aimed at a surface most teams have never mapped.

## The attacks that changed the conversation

A few landmark incidents made supply chain security a board-level concern (referenced here as the widely-documented cases they are):

- **SolarWinds** — attackers compromised the *build system* of a widely-used IT-management product and injected a backdoor into a legitimate, signed update, which then shipped to thousands of organizations, including government agencies. The lesson: the build pipeline itself is a target, and a signed artifact is only as trustworthy as the process that built it.
- **Log4Shell (Log4j)** — a critical vulnerability in a ubiquitous logging library meant countless applications were exploitable through a dependency most teams didn't even know they had, several layers deep. The lesson: you can't respond to a dependency vulnerability you don't know you're using — inventory is a prerequisite for defense.
- **Package-registry attacks** — typosquatted and dependency-confusion packages, and compromised maintainer accounts, have repeatedly injected malicious code into npm, PyPI, and other ecosystems. The lesson: the open-source registries you pull from are themselves an attack surface.

Each pushed the industry toward the same conclusion: securing your own code isn't enough when most of your software — and the process that assembles it — comes from elsewhere.

## The shape of the defense

The rest of this series works through the layered defense these attacks demand, and it maps to three questions you must be able to answer about your software:

1. **What's in it?** — dependency security and the **SBOM** (Software Bill of Materials): a complete inventory so you can answer "are we affected?" the moment a new vulnerability drops (posts 3–4).
2. **Where did it come from and how was it built?** — **provenance and attestation** (in-toto, SLSA): tamper-evident records of the source and build process, so you can verify an artifact was built the way you expect (post 5).
3. **Is it authentic and untampered?** — **signing and verification** (Sigstore): cryptographic proof that an artifact came from your pipeline and wasn't altered (post 6).

Around those, you harden the build system itself (post 7) and assemble it all into a program (post 8). The unifying principle, echoing the pipeline-security post in the CI/CD series: **shift from trusting your supply chain implicitly to verifying it explicitly.** You stop assuming your dependencies, builds, and artifacts are trustworthy and start producing and checking evidence that they are.

The mental shift to carry through: supply chain security isn't a scanner you bolt on. It's a change in stance — from "we trust what our build produces" to "we can prove what our build produced, from what sources, containing what components." Everything ahead is about generating and verifying that proof.

## Key takeaways

- The **software supply chain** is everything that touches your software from source to production — direct and (mostly invisible) transitive dependencies, base images, build tools, CI/CD, registries, and maintainers — and all of it is your attack surface.
- It's the **new attack frontier** because of leverage (compromise one widely-used dependency or build system, hit thousands of downstream users), trust (the attack rides your own trusted build/delivery process through the front door), and blind spots (you can't defend a dependency tree you've never inventoried).
- Landmark incidents reframed it: **SolarWinds** (the build system is a target; a signed artifact is only as trustworthy as its build process), **Log4Shell** (you can't respond to a vulnerability in a dependency you didn't know you had), and **registry attacks** (typosquatting/dependency-confusion/compromised maintainers make the registries themselves an attack surface).
- The defense answers three questions about your software: **what's in it?** (SBOM/dependency security), **where did it come from and how was it built?** (provenance/attestation, SLSA), and **is it authentic and untampered?** (signing/verification, Sigstore).
- The core stance shift is **from implicit trust to explicit verification** — stop assuming your dependencies, builds, and artifacts are trustworthy and start producing and checking cryptographic evidence that they are.

## Further reading

- [CISA — Software Bill of Materials (SBOM)](https://www.cisa.gov/sbom)
- [SLSA — Supply-chain Levels for Software Artifacts](https://slsa.dev/)
- [Supply chain attack — overview](https://en.wikipedia.org/wiki/Supply_chain_attack)
