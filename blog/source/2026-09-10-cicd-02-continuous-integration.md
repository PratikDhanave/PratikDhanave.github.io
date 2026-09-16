# Continuous Integration in Depth

*Continuous Integration is the least glamorous and most important half of CI/CD. It's also the most misunderstood — teams install a build server, call it "CI," and miss the actual practice, which is a discipline about how often you merge, not which tool runs your tests. This post is about the real thing: integrating small, integrating often, and keeping the mainline always green.*

The previous post defined CI as integrating everyone's work frequently, each merge auto-verified. This post goes deep on what that actually requires, because CI is where most teams either succeed or quietly fail at CI/CD. The tooling is easy; the discipline is the hard part, and the discipline is the point.

## CI is a practice, not a server

The most common misconception: "we have CI because we have a build server that runs tests on pull requests." That's necessary but not sufficient. **Continuous Integration is the practice of every developer integrating into a shared mainline frequently** — the automated build is what *supports* the practice, not what *constitutes* it.

Here's the tell: a team can have a fancy CI server and still not do CI, if developers work on branches for two weeks before merging. They've automated the build but kept integration hell. Conversely, a team merging to main several times a day *is* doing CI even with a modest setup. CI is measured by **integration frequency**, not tooling sophistication. Get this straight and the rest follows.

## The mainline and merging often

CI centers on a **shared mainline** (call it `main`) that everyone integrates into frequently — the single source of truth for "the current state of the software." The rule is to merge small changes into it continuously, keeping your divergence from mainline small at all times.

Why small and often beats large and rare, concretely:
- **Conflicts stay trivial.** If you're never more than a few hours out of sync with mainline, merge conflicts are tiny or nonexistent. Long-lived branches accumulate divergence that turns merging into a bug-generating ordeal.
- **Feedback is immediate.** Integration problems (your change breaks someone else's, or vice versa) surface within hours, while the code is fresh, not weeks later when nobody remembers the context.
- **Bugs are easy to trace.** When mainline breaks, the culprit is one of a handful of recent small commits, not one of hundreds of changes in a giant merge.

This is why **trunk-based development** — developers working in short-lived branches (hours to a day or two) that merge back to trunk quickly, or committing to trunk directly behind feature flags — is the branching model most aligned with CI. Long-lived feature branches are, by design, the opposite of continuous integration: they *delay* integration, which is the exact thing CI exists to prevent. (We'll see how feature flags let you merge incomplete work safely.)

## The build must be fast and reliable

For CI to work, the automated build (compile + test) that runs on every integration must have two properties, and neglecting either quietly kills the practice:

- **Fast.** If the build takes 45 minutes, developers stop waiting for it, stop integrating frequently, and batch changes to avoid the wait — which reintroduces the large-rare-merge problem. A CI build should ideally finish in minutes. Speed isn't a nicety; it's what *enables* the frequency that defines CI. Techniques (next post) include parallelization, caching, and running only fast tests in the first stage.
- **Reliable.** The build's pass/fail signal must be *trustworthy*. If tests are **flaky** — failing randomly without a real bug — developers learn to ignore red builds ("just re-run it"), and a red build stops meaning anything. Once the signal is untrusted, CI is dead even if it's technically running. A flaky test is worse than no test, because it erodes trust in the whole system.

These two properties are load-bearing. A slow build destroys frequency; an unreliable build destroys trust. Protecting both is ongoing work, not a one-time setup.

## Keep the mainline green

The cardinal rule of CI: **the mainline is always in a working state** — it always builds and passes tests ("green"). A broken mainline is a team-wide emergency, because everyone integrates against it: if `main` is red, everyone who pulls gets broken code, and everyone who integrates can't tell if *their* change is the problem. A red mainline blocks the whole team.

So the discipline is:
- **Don't merge on red.** Changes only merge to mainline when the build passes (enforced by branch protection / required status checks).
- **Fixing a broken build is the top priority.** If mainline goes red, the team stops and fixes it before doing anything else — because everyone is blocked until it's green.
- **Never go home on a red build.** Leaving mainline broken overnight blocks the next day's work.

This "always green" discipline is what makes the mainline trustworthy as the shared foundation. It's a cultural commitment as much as a technical one.

## Pull requests, reviews, and the CI tension

Modern CI usually runs through **pull requests**: you push a branch, open a PR, CI runs the build/tests on it, a colleague reviews, and it merges to main on green + approval. This is good — it combines automated verification with human review.

But there's a real tension with CI's "integrate frequently" goal: if PRs sit in review for days, you've reintroduced delayed integration through the back door. The resolution is to keep PRs **small and review fast**. Small PRs are easier to review (so they merge faster), easier to verify, and safer to merge — the same small-batch principle that drives all of CI/CD, applied to code review. A team that lets PRs languish for a week isn't really doing continuous integration, however green their builds are. Keeping changes and their reviews small is the habit that makes the whole thing continuous.

## Key takeaways

- **CI is a practice, not a server**: it's measured by *integration frequency* (merging into a shared mainline many times a day), and a fancy build server with two-week branches is *not* CI.
- Merge **small and often** into a shared mainline so conflicts stay trivial, feedback is immediate, and bugs are easy to trace — which is why **trunk-based development** (short-lived branches, feature flags) fits CI and long-lived feature branches fight it.
- The automated build must be **fast** (a slow build kills the frequency that defines CI — developers batch to avoid the wait) *and* **reliable** (flaky tests destroy trust in the signal, and an untrusted build is a dead build — a flaky test is worse than no test).
- **Keep the mainline green**: never merge on red, treat a broken build as a top-priority team-wide emergency (everyone integrates against mainline), and never leave it red overnight.
- Run CI through **small, fast-reviewed pull requests** — letting PRs languish in review reintroduces delayed integration, defeating the "continuous" in CI.

## Further reading

- [Martin Fowler — Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html)
- [Martin Fowler — Patterns for Managing Source Code Branches](https://martinfowler.com/articles/branching-patterns.html)
