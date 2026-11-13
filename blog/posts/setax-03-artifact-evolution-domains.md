<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/setax-03-artifact-evolution-domains.html -->

# Where Artifact Evolution Works: The Verifier Spectrum

*Artifact evolution's track record is strangely lumpy: superhuman results on matrix-multiply schedules and scheduling heuristics, respectable results on general code optimization, and little to show on "write me a better product strategy." The lumpiness isn't mysterious — it traces exactly one variable: how good a verifier the domain affords. This post organizes the application domains along that spectrum, from exact checkers to vibes, and reads off where the loop is trustworthy, where it needs guardrails, and where it quietly becomes fiction.*

[Post 2](/blog/posts/setax-02-artifact-evolution-loop.html) ended on the claim that the evaluator is the system. Take that seriously and the question "where does artifact evolution work?" reduces to "where can you build an honest evaluator?" — which is a question about domains, not about models.

## The spectrum, strong end first

- **Exact verification.** Mathematics and formal methods sit at the top: a construction either achieves the stated bound or doesn't; a proof either checks or doesn't ([automated theorem proving](https://en.wikipedia.org/wiki/Automated_theorem_proving) made the checker the foundation of the field long before LLMs arrived). An evaluator here cannot be fooled, only mis-specified. Search can run unsupervised for millions of candidates, and a single success is a permanent, human-checkable artifact — which is why combinatorial constructions and algorithm-discovery results were the loop's first headline wins.
- **Measured execution.** Performance engineering — kernels, query plans, compiler flags, scheduling heuristics — has a near-exact evaluator: run it, time it, check outputs match a reference. Two cracks appear: **measurement noise** (timing variance lets lucky candidates win; the fix is statistical discipline, repeated runs and significance thresholds, or evolution optimizes the noise) and **environment overfit** (the artifact is genuinely faster *on the benchmark machine, benchmark sizes, benchmark data* — the evaluator was honest about a narrow world; the fix is evaluating across a held-out spread of environments). Both are manageable, which is why this tier is where artifact evolution earns money today.
- **Test-suite verification.** General software — "make this function faster/cleaner/pass these tests" — drops to a *sampled* verifier: the test suite covers a sliver of behavior, and evolution is an adversary with a thousand tries at the sliver's gaps. The classic failure is the patch that passes every test by special-casing them. Mitigations are about *widening the sampled slice faster than the search exploits it*: mutation-hardened suites, property-based tests, held-out tests the generator never sees, and human review as the final gate. Workable, but the evaluator is now a security boundary and must be engineered like one.
- **Scored approximation.** Scientific hypotheses, molecules, designs: the true objective (works in the lab, synthesizes cheaply, pleases users) is unavailable at search time, so a *proxy* — simulator, predictive model, learned scorer — stands in. Now Goodhart is not a risk but a guarantee: with enough search pressure, candidates maximize the proxy precisely where it diverges from reality. The honest pattern treats search output as *candidate generation for a real-world filter* — the loop proposes, the wet lab disposes — and budgets for the fact that proxy-score rank and real-world rank correlate weakly at the optimized tail.
- **Judged quality.** Prose, strategy, "better" agent behavior: the evaluator is a rubric-wielding LLM judge. This tier powers useful *harness* loops (post 4) where a rough signal beats none, but for high-pressure artifact search it is the weakest link — judges have exploitable preferences (length, confident tone, format), and a thousand-round search *will* find them. Honest practice here caps search pressure, ensembles judges, and anchors on spot-checked human agreement — or accepts that what's being optimized is "what the judge likes," which is sometimes fine and should be said out loud.

## Reading the spectrum

Three rules fall out. **Search pressure must not exceed verifier strength** — the amount of optimization a signal can absorb before it stops meaning anything is finite and ordered exactly as above; thousand-round searches belong on exact and measured verifiers, judge-scored domains tolerate only gentle pressure. **The verifier, not the generator, is where engineering effort compounds** — a better test suite or a denoised benchmark improves every future search; a cleverer prompt improves one. **Verifier quality is a property of the domain you choose, partly under your control** — the highest-leverage move in applying artifact evolution is often reshaping the problem until it affords a stronger verifier: extracting a checkable kernel from a vague goal, adding a reference implementation, formalizing the acceptance criterion. The domains where self-evolving AI "mysteriously works" are the domains someone did that reshaping first.

The takeaway: artifact evolution's successes map one-to-one onto **verifier strength** — exact checkers (math, formal proofs) at the trustworthy end, timed execution and test suites in the engineerable middle, proxy scores and LLM judges at the fragile end where Goodhart stops being a risk and becomes the expected outcome. Match search pressure to verifier strength, invest in the verifier before the generator, and reshape problems toward checkability — that discipline, not model choice, decides whether the loop produces results or fiction.

## Key takeaways

- The verifier spectrum: **exact → measured → test-sampled → proxy-scored → judge-scored**, with trustworthy unsupervised search only at the strong end.
- Each tier's signature failure: mis-specification (exact), noise and environment overfit (measured), test-gap exploitation (sampled), guaranteed proxy divergence (scored), judge-preference gaming (judged).
- **Pressure budget**: the weaker the verifier, the less optimization it absorbs before Goodhart dominates — cap rounds accordingly, and treat weak-verifier output as candidates for a real filter, not answers.
- The highest-leverage engineering move is **reshaping the problem for a stronger verifier** — checkable kernels, reference implementations, formalized acceptance — because verifier quality compounds and generator cleverness doesn't.

## Further reading

- [Automated theorem proving — the exact-verifier end of the spectrum](https://en.wikipedia.org/wiki/Automated_theorem_proving)
- [Software testing — the sampled verifier most real systems live on](https://en.wikipedia.org/wiki/Software_testing)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-08
Canonical: https://pratikdhanave.com/blog/posts/setax-03-artifact-evolution-domains.html
Attribution: please link the canonical URL when citing or quoting this post.
