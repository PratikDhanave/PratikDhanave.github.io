# From Bespoke to Product

*Every forward deployed engineer builds one-offs to win the customer in front of them — the ones who last turn those one-offs into product instead of drowning in them.*

The forward deployed model has a built-in tension (introduced in post 1): to move fast and delight a specific customer, you build bespoke solutions; but a pile of bespoke solutions is a maintenance swamp and a business that doesn't scale. The FDE who only ships custom work becomes a very expensive consultant whose output can't be reused. The FDE who insists everything be general moves too slowly to win anyone. Living well in this tension — and feeding the product — is what separates a strategic FDE org from a services shop with delusions of being a product company. This post is about that transition.

## Why bespoke is the right *start*

Don't over-correct into premature generalization. Building something specific first is correct because:

- **You don't yet know what to generalize.** The first customer's solution is a hypothesis about the problem. Generalizing before you've seen the pattern repeat is guessing.
- **Speed wins the customer.** A bespoke solution delivered this month beats a general one delivered next year — and the trust you earn funds everything else.
- **The bespoke work *is* the research.** Each custom engagement teaches you what the real problem looks like across contexts. That knowledge is the raw material for the product.

**The gotcha:** generalizing on a sample size of one is how you build a "flexible platform" that fits no one — over-engineered abstractions for variation you imagined instead of observed. Earn the right to generalize by seeing the pattern recur.

## The signal: the same thing, three times

The practical rule most FDE orgs converge on: **build it bespoke the first time, note it the second time, productize it the third.** When three customers need the same capability — even in different clothing — you've found a real pattern, not a coincidence, and it's worth the cost of making it general. Before that threshold, resist; after it, the recurring bespoke work is a tax you keep paying.

```text
customer A ──► bespoke solution ──┐
customer B ──► bespoke (again?) ──┤──► pattern recognized ──► PRODUCT FEATURE
customer C ──► bespoke (yes!) ────┘        (build once, reuse for D, E, F…)
```

## The feedback loop is the whole point

Bespoke work only justifies itself if it flows back into the product. That requires a *deliberate mechanism*, not hope:

- **Capture patterns, not just code.** After each engagement, record what the customer really needed, what you built, what was custom vs. reusable, and what you'd want the product to do so you never build this by hand again.
- **Close the loop with the product team.** FDEs are the product's richest source of ground truth — they see the real problems before the roadmap does. That insight must reach the people who own the core product, structurally (regular syncs, a shared backlog, FDEs who file real feature requests with customer evidence).
- **Make generalization someone's job.** Whether it's the FDE, a platform team, or product engineering, someone must own turning recurring bespoke work into product capability — or it never happens and the swamp grows.

**The gotcha:** bespoke work with no feedback path is pure liability — you pay to build it and pay again to maintain it, and the product learns nothing. An FDE org without a structural bespoke-to-product loop slowly converts its best engineers into maintenance staff for one-offs.

## Design bespoke work for graduation

You can make the eventual transition cheaper while still moving fast. Even in a custom build, separate the *genuinely customer-specific* parts (their data formats, their branding, their one weird rule) from the *probably-general* core (the workflow, the model, the logic). Configuration over hard-coding where it's cheap; a clean seam between "the pattern" and "this customer's specifics." This isn't premature generalization — it's leaving the pattern extractable so that when the third customer arrives, graduating it to product is a refactor, not a rewrite.

## Manage the portfolio of one-offs

At any moment an FDE (and an FDE org) holds a portfolio of bespoke solutions in various states: throwaway prototypes, live custom deployments, and candidates for productization. Left untracked, this portfolio quietly becomes an unmaintainable liability — dozens of slightly-different forks, each depending on the one engineer who built it. Track it explicitly: what's live, who owns it, what it depends on, and what should be sunset, merged, or graduated. Deliberately *retire* bespoke solutions once the product absorbs their capability, rather than maintaining both forever.

**The gotcha:** the failure mode isn't any single one-off — it's the accumulation. Fifty bespoke deployments, each 90% the same but individually maintained, is a company-ending maintenance load that crept in one reasonable decision at a time. Watch the pile, not just each piece.

## The strategic payoff

Done right, the bespoke-to-product loop is a flywheel: FDEs win customers with fast custom work, that work reveals real patterns, the product absorbs the patterns, and the stronger product makes the *next* engagement faster and more general — so FDEs win the next customer more cheaply and reach the productizable pattern sooner. This is how companies like Palantir framed the model: forward deployed work isn't a cost center bolted onto a product; it's the sensing organ that tells the product what to become. An FDE who understands this is not just delivering to a customer — they're steering the product.

## Key takeaways

- **Bespoke is the right start** — you can't generalize a pattern you haven't seen recur; speed wins the customer and funds the rest.
- Use the **"third time, productize"** rule: build custom, note the repeat, generalize on the third occurrence.
- The **feedback loop from bespoke work to the product is the whole point** — capture patterns (not just code), and make generalization someone's explicit job.
- **Design custom work for graduation**: a clean seam between the general pattern and the customer-specific parts turns a future rewrite into a refactor.
- **Track and prune the portfolio of one-offs** — accumulation, not any single one-off, is what sinks an FDE org.
- Done right it's a **flywheel**: custom work → patterns → stronger product → faster next engagement.

## Further reading

- [Palantir — the forward deployed model and product feedback](https://blog.palantir.com/) — how bespoke deployments feed the platform.
- [Geoffrey Moore — Crossing the Chasm](https://www.geoffreyamoore.com/) — moving from bespoke early wins to a repeatable product.
- [Martin Fowler — on the cost of duplication and premature abstraction](https://martinfowler.com/bliki/Yagni.html) — balancing YAGNI against the "rule of three."
