# SAST, DAST, and Security Testing in CI

*How the four families of automated security tests — static analysis, dynamic analysis, secret scanning, and instrumented runtime testing — fit together across a pipeline, and why tuning signal-to-noise matters more than adding scanners.*

---

Security testing that lives in a spreadsheet, run once a quarter by a specialist, catches problems long after they're expensive to fix. DevSecOps moves that work left — into the same pipeline that already runs your unit tests — so a vulnerability is caught in the pull request that introduced it, not in a pen-test report six months later.

But automating security testing is where most teams get the details wrong. They bolt on three scanners, each fires hundreds of findings, engineers learn to click past the red X, and the pipeline is now theater. The hard part isn't running the tools. It's placing each one where its strengths pay off, and tuning it so the findings people see are the findings that matter.

This post walks the four families of automated security tests — **SAST**, **DAST**, **IAST**, and **secret scanning** — what each one actually sees, where it belongs in the pipeline, and how to turn raw findings into things a developer will act on.

---

## SAST: reading the code without running it

**Static Application Security Testing** analyzes your source code (or compiled bytecode) without executing it. It parses the code into an abstract syntax tree, follows how data moves through the program, and flags patterns that match known vulnerability classes: user input flowing into a SQL query without parameterization, a hardcoded credential, an unsafe deserialization call, a path built from untrusted input.

The appeal is that SAST runs early and sees everything. It doesn't need a deployed environment or a request to trigger a code path — it reads the whole tree, including the error branch that only fires once a year. That breadth makes it the natural first gate: it can run on a developer's laptop and again on every pull request.

Real SAST tools worth knowing:

- **Semgrep** — pattern-based, rules written in a syntax that mirrors the code itself; fast, easy to author custom rules, strong for polyglot repos.
- **CodeQL** — GitHub's engine that treats code as a database you query; deep data-flow analysis, excellent for tracing taint from source to sink.
- **gosec** — focused on Go, catches Go-specific issues like unhandled errors on security-relevant calls and use of weak crypto.
- **Bandit** — the standard for Python, scans for common insecure patterns like `subprocess` with `shell=True` or use of `pickle` on untrusted data.

The weakness is the mirror image of the strength. Because SAST reasons about code paths abstractly, it can't know what's reachable at runtime, what's already sanitized by a framework it doesn't model, or which config makes a "vulnerable" call safe. That produces **false positives** — findings that are technically a match but not exploitable. It also produces false negatives on anything that only manifests through runtime behavior: a misconfigured load balancer, a broken auth check that depends on a session token, a logic flaw in how two services trust each other.

**The gotcha:** SAST has false positives and DAST has false negatives — neither one alone tells you the truth. SAST flags code that may never run; DAST only tests the paths it happens to reach. Treat them as complementary layers, not competitors. A finding confirmed by both is high-confidence; a finding from one is a lead to investigate.

---

## DAST: attacking the running app from outside

**Dynamic Application Security Testing** takes the opposite approach: it ignores the source entirely and tests the application while it's running, from the outside, the way an attacker would. It sends crafted HTTP requests — malformed inputs, injection payloads, tampered parameters — and watches how the deployed app responds.

The most widely used open-source DAST tool is **OWASP ZAP** (Zed Attack Proxy). It can spider an application to discover endpoints, then run active scans that probe those endpoints for issues like reflected cross-site scripting, injection, and missing security headers. Because it observes real responses from a real server, its findings carry runtime context that SAST can't have: it knows the endpoint actually exists, actually returned the payload unescaped, actually accepted the request without auth.

That runtime grounding means DAST typically produces **fewer false positives** for the classes it covers — if it demonstrably got XSS to reflect, that's real. The trade-off is coverage. DAST only finds what it can reach: endpoints it discovered, inputs it thought to send, code paths a request can trigger. Anything behind a feature flag, an unusual state, or a workflow the scanner didn't navigate stays invisible. That's the false-negative problem — a clean DAST run means "I didn't find anything on the paths I tried," not "the app is safe."

**The gotcha:** DAST needs a running target, so it does not belong in the unit-test stage — there's nothing deployed there to attack. Run it against a deployed **staging** environment that mirrors production config, typically on a nightly or scheduled cadence because a full active scan is slow. Wiring ZAP into the fast PR loop just makes the PR loop slow and flaky.

---

## IAST and SCA: the other two you'll hear about

Two more acronyms round out the landscape.

**IAST** (Interactive Application Security Testing) instruments the application from the inside — agents inside the running process watch data flow through the actual code as tests exercise it. It's a hybrid: it has DAST's runtime grounding (it sees real requests) plus SAST's visibility into the code path (it sees exactly which line handled the tainted input). The catch is that it needs an instrumentation agent in your runtime and meaningful traffic to observe, usually driven by your existing integration or QA test suite. When you already have good functional test coverage against a running build, IAST turns that traffic into security signal for free.

**SCA** (Software Composition Analysis) scans your dependencies — the open-source libraries you pull in — against databases of known vulnerabilities, and checks license compliance. **Trivy** is a common choice here, scanning both dependency manifests and container images. SCA is a large enough topic that it gets its own treatment in the next post in this series; the point for now is that SAST covers *your* code and SCA covers the code you *imported*, and you need both.

---

## Secret scanning: the leak that outlives the commit

Separate from vulnerability scanning is **secret scanning** — detecting credentials, API keys, tokens, and private keys that shouldn't be in the repository at all. This deserves its own gate because a leaked secret is not a theoretical risk you triage later; it's a live credential someone can use right now.

Two tools dominate:

- **gitleaks** — fast, config-driven regex-and-entropy scanner; runs as a pre-commit hook, in CI, or across full history.
- **trufflehog** — known for verifying findings by actually testing whether a detected credential is live, which cuts noise dramatically.

Run secret scanning in two places. First as a **pre-commit hook**, so a key is caught before it ever leaves the developer's machine — the cheapest possible place to stop it. Second in **CI**, as a backstop for anyone who bypassed the hook (`git commit --no-verify` exists, and not everyone installs the hooks).

**The gotcha:** scanning only the current diff misses every secret already sitting in git **history**. A key committed six months ago and "removed" in a later commit is still fully retrievable by anyone who clones the repo — deleting a file or amending a commit does not un-leak it. Scan the full history (`gitleaks detect` over the whole repo, not just the diff), and treat any hit as a compromised credential: **rotate it immediately**. Rewriting history to purge the blob is cleanup, not remediation — assume the secret is already public the moment it hit a shared branch.

---

## Where each test runs in the pipeline

The single most important design decision is placement. Fast, high-confidence checks go early where feedback is cheap; slow or environment-dependent checks go later where they don't block a developer mid-flow.

| Stage | What runs | Why here |
|---|---|---|
| Pre-commit hook | Secret scan (diff), fast linters | Catch leaks before they leave the laptop; instant feedback |
| PR / CI | SAST, secret scan (full history), SCA | Gate the merge; every change reviewed automatically |
| Nightly / scheduled | DAST against staging, deep SAST | Needs a deployed target; too slow for the PR loop |
| Pre-release | Full DAST, IAST, manual review of findings | Last automated gate before production |

The principle: the closer to the keyboard, the faster and quieter the check must be. A pre-commit hook that takes 30 seconds gets uninstalled. A nightly scan that takes 40 minutes is fine because nobody's waiting on it.

---

## A CI gate: SAST plus secret scanning on every PR

Here's a GitHub Actions workflow that runs SAST and secret scanning as a merge gate. It illustrates the shape — pin real actions to versions when you adopt this, and check each tool's current docs for exact inputs rather than copying flags blindly.

```yaml
name: security-ci

on:
  pull_request:
    branches: [main]

jobs:
  sast:
    name: Static analysis (Semgrep)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Semgrep with a curated ruleset. Start narrow: high-confidence
      # security rules only, so the first runs don't drown the team.
      - name: Run Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit
        # Fail the job only on findings the ruleset marks high-severity;
        # everything else is reported but does not break the build.

  secrets:
    name: Secret scan (full history)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # full history, not just the PR diff

      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        # A verified secret finding should hard-fail the PR — a leaked
        # credential is not something to warn about and merge anyway.
```

Two deliberate choices are baked in. `fetch-depth: 0` pulls the full history so the secret scan sees old commits, not just the diff. And the two jobs have different failure policies: SAST warns broadly but breaks the build only on high-severity findings, while the secret scan hard-fails on any verified hit. That difference is the whole game — read on.

---

## Making findings actionable

A scanner that emits 500 findings with no triage is worse than no scanner, because it trains people to ignore red. Getting from raw output to acted-on findings takes deliberate work.

**Break the build vs. warn.** Don't gate the merge on everything. Pick a small set of high-confidence, high-severity rules that *must* be fixed — a verified secret, a SQL injection sink with a clear taint path — and fail only on those. Everything else is reported as a warning or an annotation the author can see but that doesn't block them. As the team's trust in a rule grows, you promote it from warn to break.

**Triage and suppress with justification.** False positives are inevitable. Every SAST tool supports inline suppression — a comment like `# nosec` for Bandit or a `nosemgrep` marker for Semgrep. The rule is: **a suppression must carry a reason**. "Suppressed because this input is validated upstream in `parseRequest`" is accountable and reviewable in the PR. A bare suppression with no comment is how real vulnerabilities get silently buried, so require the justification in code review.

**Deduplicate and track.** The same finding reappearing on every run is noise. Route findings through something that dedups by fingerprint and only surfaces what's new — GitHub's code-scanning integration (which ingests SARIF, the standard format most of these tools emit) does this natively, showing a finding once and tracking it until it's fixed or dismissed. For findings that need real work, open a ticket with a severity and an owner so it doesn't live only in a CI log that scrolls away.

**The gotcha:** a scanner that dumps hundreds of findings on day one gets muted within a week. Start with high-confidence rules only and break the build on a *small* set; let the warn-only tier carry the rest. It's far better to reliably catch ten real issues than to bury three real issues under two hundred false alarms nobody reads.

---

## The false-positive fatigue problem

This is the failure mode that quietly kills DevSecOps programs, so it's worth naming directly. Every false positive spends a little of your engineers' trust. Spend enough and the scanner becomes background noise — the red X that's "always red," the check everyone force-merges past. At that point the tool is actively harmful: it's giving management a green-dashboard sense of security while providing none.

The fix is not fewer scans; it's better tuning. Practically:

- **Tune the ruleset to your stack.** Disable rules that don't apply and rules that fire constantly on framework code that's actually safe. A curated ruleset that fits your app beats a maximal one that cries wolf.
- **Baseline the existing debt.** When you introduce SAST to an old repo, snapshot the current findings as an accepted baseline and gate only on *new* findings. Otherwise the first run buries the team and nothing gets fixed.
- **Measure the signal.** Track the ratio of findings that turn into real fixes versus findings dismissed as false positives. If a rule is mostly dismissed, tune or drop it. Treat your rule config as living code that gets reviewed and improved, not a one-time install.

The goal is a pipeline where a security finding is rare enough that a developer reads it and expects it to be real. That's the state where automation actually protects you.

---

## Key takeaways

- **Layer the test types — none is sufficient alone.** SAST reads code early and broadly but overreports; DAST tests real runtime behavior but only on the paths it reaches; IAST bridges the two when you have good test traffic; SCA covers your dependencies. Coverage comes from combining them.
- **Place each test where its cost fits.** Secret scanning and SAST are fast enough for pre-commit and PR gates; DAST needs a deployed target, so it belongs against staging on a schedule, not in the unit-test stage.
- **A committed secret is a compromised secret.** Scan git history, not just the diff, and rotate anything found — deleting the commit doesn't un-leak it.
- **Tune the signal or the scanner gets muted.** Break the build on a small set of high-confidence rules, warn on the rest, require justified suppressions, dedup, and baseline old debt. False-positive fatigue, not missing tools, is what kills these programs.

---

## Further reading

- [OWASP — Source Code Analysis Tools (SAST)](https://owasp.org/www-community/Source_Code_Analysis_Tools)
- [OWASP — Vulnerability Scanning Tools (DAST)](https://owasp.org/www-community/Vulnerability_Scanning_Tools)
- [OWASP ZAP — official documentation](https://www.zaproxy.org/docs/)
- [Semgrep documentation](https://semgrep.dev/docs/)
- [CodeQL documentation](https://codeql.github.com/docs/)
- [gosec — Go security checker](https://github.com/securego/gosec)
- [Bandit — Python security linter](https://bandit.readthedocs.io/)
- [gitleaks](https://github.com/gitleaks/gitleaks)
- [trufflehog](https://github.com/trufflesecurity/trufflehog)
- [Trivy](https://trivy.dev/)
- [NIST SP 800-218 — Secure Software Development Framework (SSDF)](https://csrc.nist.gov/pubs/sp/800/218/final)
