# Dependency Security

*Most of your software is dependencies, so most of your risk is too. Dependency security is the practical, everyday discipline of controlling what you pull in, knowing when it's vulnerable, and updating without breaking — the highest-leverage supply chain work most teams can do. This post covers pinning, scanning, and the update discipline that keeps the dependency tree from becoming a liability.*

The attack taxonomy showed that the packages you depend on are the most common entry point. This post is the defense: managing dependencies as the security-relevant assets they are. It's less glamorous than cryptographic attestation (later posts) but higher-leverage, because dependency vulnerabilities and malicious packages are where most real-world supply chain incidents actually happen.

## Pin everything: lockfiles and reproducibility

The foundational practice is **pinning** — recording the exact version (and ideally the cryptographic hash) of every dependency, direct and transitive, so builds are reproducible and can't silently change.

Modern package managers do this with **lockfiles** — `package-lock.json`, `poetry.lock`, `Cargo.lock`, `go.sum`. A lockfile records the resolved version and a hash of *every* dependency in the full tree. Committing the lockfile and building from it means:
- **Reproducible builds** — everyone (and every CI run) gets the exact same dependency tree, not "whatever was latest today."
- **No silent malicious updates** — a compromised new version of a dependency can't slip into your build automatically, because you're pinned to a specific, hashed version until you deliberately update.
- **Hash verification** — the recorded hash means a tampered package (different bytes, same version number) is rejected.

The anti-pattern is floating version ranges (`^1.2.0`, `latest`) resolved fresh on every build — which is exactly how a compromised package update reaches you the moment it's published. Pin to specific versions with hashes, commit the lockfile, and update deliberately. This single practice neutralizes the "compromised legitimate package auto-upgrades into your build" attack from the last post.

## Scan for known vulnerabilities

Pinning stops *silent* changes but doesn't tell you when a version you're pinned to turns out to be vulnerable. That's what **SCA (Software Composition Analysis)** / dependency scanning does: it checks your dependency tree against databases of known vulnerabilities (CVEs, advisory databases) and flags affected packages.

Run it continuously:
- **In CI on every build** — so a newly-added vulnerable dependency is caught before merge, and fail the build on critical/high severity.
- **Continuously against your existing dependencies** — because vulnerabilities are *discovered over time*. A dependency that was clean when you added it becomes vulnerable the day a CVE is published against it. Continuous scanning (e.g. a daily job, or tools like Dependabot/Renovate that watch advisories) is what catches Log4Shell-style situations — a critical flaw in a dependency you've had for years.

The key insight: dependency risk is *not* a point-in-time property you check once at install. It changes as new vulnerabilities are discovered, so scanning has to be ongoing. Most SCA value comes from catching the CVE announced *after* you adopted the dependency.

## The update discipline: neither too fast nor too slow

Dependencies must be *updated*, and both extremes are dangerous:
- **Never updating** leaves you exposed to known vulnerabilities and makes eventual updates huge and risky (the "we can't upgrade, it's too far behind" trap).
- **Auto-updating instantly to the latest** exposes you to compromised-package attacks (you pull the malicious new version the moment it's published) and breakage.

The healthy middle is **regular, deliberate, tested updates**:
- Update on a cadence (and immediately for critical security patches), not never and not reflexively-instantly.
- Let CI's test suite (from the CI/CD series) verify each update doesn't break anything — this is where good tests pay off, making updates safe and routine.
- Consider a brief "cooldown" before adopting brand-new releases, so a compromised or broken version has time to be caught by the community before it reaches you.
- Automate the *proposal* of updates (Dependabot/Renovate open PRs) but keep a *review and test* gate before merging.

The goal is to stay current enough to be patched, but deliberate enough not to ingest malicious or broken releases blindly. Good tests are what make this balance achievable — they turn "scary upgrade" into "routine reviewed PR."

## Reduce and vet what you depend on

The cheapest dependency risk is the one you don't take:
- **Minimize dependencies.** Every dependency is trust extended to strangers and attack surface added. Before adding one, ask whether it's worth it — the classic "left-pad" problem is pulling a huge tree for trivial functionality. Fewer, well-chosen dependencies are easier to secure than many casual ones.
- **Vet before adopting.** For a significant new dependency, check signals of health and trustworthiness: is it actively maintained, widely used, from a reputable source, reasonably scoped? A one-maintainer package with three stars carries different risk than a foundation-backed one.
- **Prefer well-maintained over feature-rich.** A slightly less convenient but actively-maintained, widely-audited library is a better security bet than a feature-packed but abandoned one.
- **Guard against dependency confusion** (post 2): namespace internal packages and pin them to your private registry so a public package can't shadow them.

Every dependency you don't add is attack surface you don't have to defend, a package you don't have to scan, and a maintainer you don't have to trust.

## Key takeaways

- **Pin everything** with lockfiles (`package-lock.json`, `go.sum`, `Cargo.lock`) recording exact versions *and hashes* for the whole tree — giving reproducible builds, hash verification (tampered packages rejected), and no silent malicious auto-updates; floating ranges (`^1.2`, `latest`) are the anti-pattern.
- **Scan continuously** (SCA) — in CI on every build (fail on critical) *and* ongoing against existing dependencies, because vulnerability risk changes over time as new CVEs are discovered (a years-old dependency becomes vulnerable the day its CVE drops — the Log4Shell situation).
- Adopt an **update discipline** between the extremes: regular deliberate tested updates (immediate for critical patches), automated *proposals* (Dependabot/Renovate) with a review+test gate, and a brief cooldown on brand-new releases — good CI tests are what make upgrades routine instead of scary.
- **Reduce and vet dependencies**: every one is trust extended to strangers and attack surface added, so minimize them, vet significant ones for maintenance/reputation/scope, and prefer well-maintained over feature-rich.
- Dependency security is unglamorous but the **highest-leverage** supply-chain work, because dependency vulnerabilities and malicious packages are where most real incidents actually happen.

## Further reading

- [OpenSSF — Open Source Security Foundation](https://openssf.org/)
- [CISA — Software Bill of Materials (SBOM)](https://www.cisa.gov/sbom)
