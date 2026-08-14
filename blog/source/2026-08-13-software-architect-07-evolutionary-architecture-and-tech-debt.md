# Evolutionary Architecture and Technical Debt

*Architecture is never finished. This post is about designing systems for the change you know is coming, guarding the characteristics you care about with automated fitness functions, and treating technical debt as an ongoing budget rather than a someday-rewrite.*

---

There is a fantasy that haunts a lot of architecture work: the belief that if you think hard enough up front, you can get the design *right* — once — and then simply build it. Requirements will hold still. The team will grow the way you predicted. The load will arrive in the shape you modeled. Under that fantasy, every later change is evidence you failed to think hard enough the first time.

The fantasy is wrong, and expensively so. Requirements move because businesses learn. Context shifts because the market, the regulations, the team, and the technology all shift under you. A design that was correct for last year's context can be a liability for this year's. The mature stance is not "get it right up front" but "make it *changeable*" — because change is the one requirement you can guarantee.

That stance has two halves, and this post is about both. The first is **evolutionary architecture**: optimizing for changeability, and using automated **fitness functions** to keep the important characteristics from eroding as the system grows. The second is **technical debt**: understanding it as a real financial metaphor, making it visible, and paying it down as a budgeted, incremental discipline rather than betting the company on a big rewrite.

---

## Evolutionary architecture: optimize for change, not for perfection

Big Design Up Front (BDUF) tries to specify the whole system before writing code. Its failure mode is that it commits you — in detail — to guesses made at the moment you knew the least about the problem. By the time reality contradicts the plan, the plan has already shaped the code, and the code fights back.

The equal-and-opposite failure is **no design at all**: start coding, let structure "emerge," and discover eighteen months later that the emergent structure is a mud ball where every change touches everything. "Emergent design" without any guardrails does not emerge into something good; it emerges into whatever was locally convenient at each keystroke.

Evolutionary architecture threads between these. You still make the significant, hard-to-reverse decisions deliberately — that never goes away. But for everything else, you optimize for the *ability to change your mind cheaply later*. Concretely that means:

- **Small, well-defined modules with clear boundaries**, so a change lands in one place instead of rippling everywhere.
- **Explicit contracts between parts** (an API, a message schema, an interface) so components can evolve independently as long as the contract holds.
- **Deferring one-way-door decisions** until you have the information to make them — and keeping two-way-door decisions genuinely reversible.
- **Automation you can trust**, so you can change things fast *and* prove you didn't break anything.

The goal is not zero design. The goal is a design whose *shape makes future change affordable*. You are trading a little up-front convenience for a lot of long-term optionality.

**The gotcha:** "we'll refactor it later" is not a design strategy — it is a wish. Changeability is a property you build in on purpose, through boundaries and tests, not a discount you can claim retroactively once the code has already fused into a single tangled mass. If nothing in your process actively protects the seams, they close.

---

## Fitness functions: guard the characteristics you care about

Earlier in this series I argued that an architecture is defined by its **quality attributes** — the -ilities: performance, security, modularity, testability, and the rest. A fitness function is the mechanism that keeps those attributes from silently decaying over the life of the project.

The term is borrowed from evolutionary computing, where a fitness function scores how close a candidate is to the goal. In architecture it means the same thing, made concrete: **an automated, objective check that a specific architectural characteristic still holds.** Not a paragraph in a wiki that says "modules must not depend on each other cyclically" — an *executable test* that fails the build when they do.

The value is that it turns an aspiration into a ratchet. Anyone can violate a rule that lives in a document; nobody can merge past a red pipeline. A few common shapes:

- **Dependency-direction checks.** Assert that your `domain` package never imports `infrastructure`, that the UI layer never reaches into the database layer directly, that no cycles exist between modules.
- **Performance budgets in CI.** A benchmark that fails if p99 latency of a critical path regresses past a threshold, or if a bundle exceeds a size limit.
- **Security and compliance gates.** A scan that fails on a known-vulnerable dependency or a secret committed to the repo — the DevSecOps "shift left" idea applied to architecture.
- **Coupling and complexity ceilings.** Fail the build if a module's afferent/efferent coupling or cyclomatic complexity crosses a line you agreed on.

Here is the smallest useful example: a Go test that enforces a dependency-direction rule. The `domain` layer must not import anything from `infrastructure`. If someone wires a database driver straight into the domain model, this test goes red before the pull request merges.

```go
package arch_test

import (
	"go/parser"
	"go/token"
	"path/filepath"
	"strings"
	"testing"
)

// Fitness function: the domain layer must stay free of infrastructure.
// Encoding the rule as a test means a violation FAILS THE BUILD,
// instead of drifting past review as it would if it only lived in a wiki.
func TestDomainDoesNotImportInfrastructure(t *testing.T) {
	const forbidden = "myapp/internal/infrastructure"

	files, _ := filepath.Glob("../internal/domain/**/*.go")
	fset := token.NewFileSet()

	for _, path := range files {
		f, err := parser.ParseFile(fset, path, nil, parser.ImportsOnly)
		if err != nil {
			t.Fatalf("parse %s: %v", path, err)
		}
		for _, imp := range f.Imports {
			if strings.Contains(imp.Path.Value, forbidden) {
				t.Errorf("architectural rule violated: %s imports %s "+
					"(domain must not depend on infrastructure)", path, forbidden)
			}
		}
	}
}
```

It is fifteen lines and it does more to protect your architecture than fifteen pages of guidelines, because it runs on every commit and it cannot be politely ignored.

**The gotcha:** architectural rules that live only in a wiki, an onboarding doc, or a senior engineer's head *will* be violated — not out of malice, but because a rule nobody's tooling enforces is invisible at 4pm on a Friday during an incident. If a characteristic matters, encode it as a fitness function in CI so drift fails the build instead of accumulating quietly until someone notices the smell.

Two cautions. First, fitness functions guard characteristics you have *chosen*; keep the set small and meaningful, because a suite of noisy, flaky checks gets disabled and then protects nothing. Second, they are a floor, not a ceiling — they catch regression against known rules, they do not do your thinking for you.

---

## Guarding boundaries as the system grows

Boundaries are where evolvability lives or dies. Early on, everything is small and every part can see every other part, and that feels efficient. But every casual reach across a boundary — a UI component querying the database directly, a "quick" import from a module that was supposed to be internal — is a future dependency you did not intend to sign up for. Multiply that by two years and a dozen engineers and the boundaries dissolve.

The defense is to make boundaries *load-bearing and checkable*. State the direction dependencies are allowed to flow (typically: outer layers depend on inner ones, never the reverse). Give each module a deliberate public surface and keep the rest genuinely private. Then back the intent with a fitness function like the one above, so the boundary is enforced by the build rather than by everyone remembering the rule. A boundary that is only a convention is a boundary that is already halfway gone.

---

## Technical debt: the metaphor, done right

Ward Cunningham coined the **technical debt** metaphor to explain to non-technical stakeholders why a team would spend time reworking code that already "works." His actual point is subtler than the way the phrase is often used. Shipping code you don't yet fully understand is like taking on debt: it lets you *move now* and *learn from the market* sooner. That can be a smart trade — as long as you pay the loan back by refactoring as your understanding improves. Debt taken deliberately, and repaid, accelerates you. Debt left to compound buries you.

The crucial and most-misused idea in the metaphor is **interest**. The one-time cost of a shortcut is not the problem; the problem is the *ongoing* cost it imposes on every future change. Debt makes the code harder to modify, so every feature after it costs a little more, ships a little slower, and carries a little more risk. That drag — paid over and over, on work that has nothing to do with the original shortcut — is the interest. A system can be so heavily leveraged that the team spends all its energy servicing interest and none delivering value. The real cost of technical debt is *slowed change*, forever, until you pay down the principal.

### Not all debt is the same: Fowler's quadrant

Martin Fowler extended Cunningham's metaphor into a **quadrant** that separates debt along two axes — was it *deliberate* or *inadvertent*, and was it *prudent* or *reckless*? The four corners behave very differently, and lumping them together is why "tech debt" conversations so often go nowhere.

| | **Prudent** | **Reckless** |
|---|---|---|
| **Deliberate** | "We'll ship the simple version now and revisit after we see real usage." A conscious, time-bought loan. | "We don't have time for design." Knowing better and skipping it anyway. |
| **Inadvertent** | "*Now* we understand what the design should have been." Debt you only see in hindsight after learning. | "What's layering?" Debt from simply not knowing what good looks like. |

The two prudent corners are healthy — even valuable. **Deliberate-prudent** debt is the smart loan: a conscious shortcut, taken to ship and learn, with an honest intent to repay. **Inadvertent-prudent** debt is unavoidable and even a good sign — it means the team learned something, and now knows a better design than was knowable at the start. The **reckless** corners are the mess: cutting corners you know you shouldn't (deliberate), or not knowing there were corners to cut (inadvertent, curable with mentoring and review).

**The gotcha:** not all debt is bad, and treating every shortcut as a moral failing is its own dysfunction — it makes engineers hide the debt they take instead of declaring it. A deliberate, prudent shortcut, taken openly to ship and learn faster, is *good engineering judgment*. The failure isn't taking the loan; it's taking it recklessly, or taking a prudent loan and then never paying it back.

---

## Make debt visible, then budget for it

The most dangerous property of technical debt is that it is *invisible*. Unlike a financial loan, no statement arrives each month. The interest is paid silently, as features that quietly take longer and estimates that keep creeping, and by the time anyone names it the balance is enormous. So the first job is to drag it into the light.

- **Keep a debt register.** A simple, living list of known debts, each with where it is, why it exists, what it's costing you (the interest), and a rough sense of the payoff to fix it. In-code markers are fine as long as something aggregates them. A tiny example — a note that ties a shortcut to the register so it is trackable rather than forgotten:

```go
// DEBT(register #142): rates hard-coded here to ship the MVP on time.
// Interest: every new currency needs a code change + redeploy (~1 dev-day each).
// Payoff: load from the pricing service; ~2 days. Deliberate/prudent — revisit Q3.
var fxRates = map[string]float64{"USD": 1.0, "EUR": 0.92, "GBP": 0.79}
```

- **Spend a debt budget.** Reserve a standing slice of each cycle — say 15–20% of capacity — for paying down debt. Not "when we have time" (you never will), but a line item that competes on equal footing with features.
- **Follow the boy-scout rule.** Leave each module a little cleaner than you found it. Small, continuous repayment on code you're already touching keeps the balance from ballooning between big efforts.
- **Prioritize by interest, not by ugliness.** The debt worth paying first is the debt in the code you change most often — that's where the interest actually accrues. Ugly code you never touch is charging you nothing; leave it.

Making debt visible turns an anxious, moralized topic into an ordinary engineering trade-off you can reason about, prioritize, and schedule.

**The gotcha:** debt you can't *see* compounds silently. Because no invoice ever arrives, an untracked shortcut feels free right up until the day the team is spending most of its time fighting the codebase and nobody can point to why. Write debt down, attach its interest cost, and give repayment a budget — an unmeasured balance only ever grows.

---

## The big rewrite is a trap; migrate incrementally

When the debt feels overwhelming, the seductive answer is the **big rewrite**: freeze the old system, build a shiny replacement from scratch, flip the switch. It almost never works, and it fails in predictable ways. The old system encodes years of accumulated bug fixes and hard-won domain knowledge — a thousand tiny corrections for edge cases nobody remembers — and a rewrite throws all of it away and rediscovers each one the hard way. Meanwhile the business will not stop for two years while you rebuild what it already has; requirements keep moving, so you're chasing a target while the old system keeps drifting ahead of your copy.

The disciplined alternative is the **strangler fig** pattern (named by Fowler after the vine that grows around a host tree and gradually replaces it). Instead of a rip-and-replace, you grow the new system *around* the old one and migrate slice by slice:

1. Put a facade or routing layer in front of the existing system.
2. Build one capability anew behind that facade and route just that slice of traffic to it.
3. Verify it in production, then retire the old code path for that slice.
4. Repeat, capability by capability, until the old system is fully strangled — and stop safely at any point, because the system is shippable the whole way.

Every step ships value, every step is reversible, and you never bet the company on a two-year flip that has to work perfectly on the first try.

**The gotcha:** the big rewrite is the most expensive way to pay down debt and the one most likely to fail outright — you discard the accumulated fixes and domain knowledge baked into the old system, and the business won't wait two years for the replacement. Strangle the old system incrementally instead: each migrated slice delivers value and de-risks the next, and you can stop at any point with a working system.

---

## Erosion, drift, and knowing which lever to pull

Even a well-designed system decays. **Architectural erosion** (or drift) is the slow divergence between the architecture you *intended* and the architecture you actually *have* — each expedient shortcut, each boundary quietly crossed, each rule ignored under deadline pressure, moving the real system a little further from the design. Nobody decides to erode the architecture; it happens one reasonable-seeming exception at a time. This is precisely what fitness functions exist to catch: they measure the gap between intent and reality continuously, so drift shows up as a failing build the day it happens rather than as a crisis two years later.

When you find debt, you have three honest options, and the skill is choosing the right one:

- **Refactor** — the default. Improve the internal structure without changing behavior, incrementally, in the code you're already touching. This is how most debt should be repaid: continuously, in small pieces, under the cover of tests.
- **Rewrite** — the rare, deliberate exception. Reserve it for a bounded component (never the whole system) whose design is fundamentally wrong for what it now must do, where incremental refactoring genuinely can't get there. Even then, do it strangler-fig style, one slice at a time.
- **Live with it** — a legitimate choice, not a defeat. Debt in stable code you rarely touch charges almost no interest. Consciously deciding to leave it and spend your budget where the interest is high is good stewardship, as long as it's a *decision* and not neglect.

The through-line is that all three are choices to make on purpose, with the interest cost in view — not defaults you back into.

---

## Key takeaways

- **Architecture is never done.** Optimize for changeability, not up-front perfection — avoid both Big Design Up Front and no-design-at-all.
- **Guard characteristics with fitness functions.** Turn the architectural rules you care about into automated, objective checks in CI so drift fails the build instead of accumulating in a wiki nobody enforces.
- **Understand debt as interest, not principal.** The real cost of a shortcut is the ongoing drag on every future change — slowed change, paid forever until you repay the principal.
- **Not all debt is bad.** A deliberate, prudent loan taken to ship and learn is smart; reckless debt is the mess. Know which quadrant you're in.
- **Make debt visible and budget for it.** A debt register, a standing repayment budget, the boy-scout rule, and prioritizing by interest beat an invisible balance that compounds in silence.
- **Skip the big rewrite.** It discards accumulated fixes and domain knowledge and the business won't wait — migrate incrementally with the strangler fig instead.

The mindset shift is from *architecture as a finished artifact* to *architecture as a living system you steer*. Design for the change you know is coming, encode the rules you care about so the build defends them for you, and manage debt like a budget you actively spend — not a bill you keep hoping to pay off all at once, someday, in a rewrite that never ships.

## Further reading

- [Building Evolutionary Architectures](https://www.thoughtworks.com/en-us/insights/books/building-evolutionary-architectures) — Neal Ford, Rebecca Parsons, and Patrick Kua on fitness functions and designing for change (Thoughtworks).
- [Technical Debt Quadrant](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html) — Martin Fowler's deliberate/inadvertent × prudent/reckless framing.
- [Technical Debt](https://martinfowler.com/bliki/TechnicalDebt.html) — Fowler's overview of the metaphor and its interest.
- [StranglerFigApplication](https://martinfowler.com/bliki/StranglerFigApplication.html) — Fowler on incremental migration around a legacy system.
- [The WyCash Portfolio Management System](https://c2.com/doc/oopsla92.html) — Ward Cunningham's 1992 experience report, the origin of the debt metaphor.
- [Fitness function-driven development](https://www.thoughtworks.com/en-us/insights/blog/fitness-function-driven-development) — a practical look at putting architectural fitness functions in a pipeline.
