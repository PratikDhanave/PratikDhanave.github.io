# The Author's Craft: Making Code Easy to Review

*Half of review quality is decided before the reviewer ever opens the diff — by the author. Small focused PRs, a description that states what and why, a self-review pass, and clean commits are how you optimize the one resource a review really spends: the reviewer's attention.*

---

Most advice about code review is aimed at the reviewer — how to give good feedback, how to be kind, how to spot bugs. That is half the story. The other half happens earlier, on the author's side, before a review request is ever sent. A change that arrives small, self-explained, and already read by its own author gets a *real* review: someone reasons about the logic and finds the thing that matters. A change that arrives as a 2,000-line wall with a one-word title gets a rubber-stamp.

The framing that makes this click: **you are not submitting code, you are spending someone else's time and attention.** That is a finite, expensive resource. Everything the author does — how the change is sized, described, and structured — either conserves that attention or squanders it. This post is about conserving it.

---

## Small, focused PRs: one logical change

The single highest-leverage habit an author has is keeping a pull request small and focused on **one logical change**. Not one file, not one commit — one *idea*: add the rate limiter, fix the timezone bug, extract the parser. If you cannot describe the change in a single sentence without the word "and," it is probably two changes.

Small diffs get better reviews for a mechanical reason, not a moral one. A reviewer can hold a few hundred lines in their head at once. They can trace every branch, question every edge case, and imagine how the code fails. Past some threshold — different for everyone, but real — that stops being possible. The reviewer skims. They check the shape, trust the tests, and approve. The review still happens on paper; it just stops happening in anyone's mind.

```text
Small PR (≈120 lines, one concern)
  → reviewer reads every line, questions edge cases, catches the off-by-one
  → 1 round of comments, merged same day

Large PR (≈1,800 lines, five concerns tangled together)
  → reviewer skims, approves the shape, misses the race in file 14
  → "LGTM" in 20 minutes for work that needed 3 hours
```

Small PRs also move faster, which feels backwards until you have lived it. A big PR is a big commitment of reviewer time, so it sits in the queue waiting for a free afternoon that never comes. A small PR is a five-minute favor someone can do between meetings. Ten small PRs reviewed promptly beat one giant PR that marinates for a week and then merges half-understood.

**The gotcha:** a 2,000-line PR does not get a review, it gets a rubber-stamp. No human deeply reviews two thousand lines of unfamiliar code in one sitting — attention runs out long before the diff does, and the tail gets waved through. If your change is genuinely that big, the fix is not a better reviewer or a longer deadline. It is to split it.

---

## How to split a big change

"Make it smaller" is easy to say and hard to do when the feature is genuinely large. A few concrete techniques:

**Stacked / incremental PRs.** Break the feature into an ordered chain of PRs, each building on the last, each independently reviewable. PR 1 adds the data model. PR 2 adds the service that uses it. PR 3 wires up the endpoint. PR 4 adds the UI. Each one is small, each merges (or at least gets reviewed) on its own, and the reviewer always sees a coherent slice instead of the whole iceberg. Tools like Graphite, `git` branch chains, or your platform's stacked-PR support make the plumbing bearable; even without tooling, sequential branches off each other work.

**Separate the refactor from the behavior change.** This is the most valuable split there is. If your feature needs you to first rename a function, move a file, or reshape an interface, do that in its own PR (or at least its own commit) with *no behavior change*. Then the behavior change lands on top of already-clean code, and its diff shows only the lines that actually change what the program does.

**Split by layer or by concern.** Backend and frontend can often go separately behind a feature flag. Validation logic and the happy path can go separately. A widely-used utility and its first caller can go separately. Look for the seams where one part could be reviewed and merged without the other being present.

```text
Instead of:  one PR — "Add CSV export"  (refactor + new feature + UI, 1,600 lines)

Ship as:
  PR 1  refactor: extract ReportWriter interface        (no behavior change, 200 lines)
  PR 2  feat: CSV writer implementation + unit tests     (400 lines)
  PR 3  feat: /export endpoint wiring                     (150 lines)
  PR 4  feat: export button + download UX                 (250 lines)
```

Each of those four is a change a reviewer can actually reason about. The sum is the same feature, delivered in pieces that get real scrutiny instead of a collective shrug.

**The gotcha:** mixing a refactor with a behavior change hides the one line that matters in a sea of moved code. When a diff shows 500 lines of "renamed and reindented" alongside three lines of new logic, the reviewer's eye glazes over the churn and the three lines slip through unexamined — which is exactly where bugs hide. Move the furniture in one PR, change the behavior in another.

---

## A great PR description

The diff shows *what changed*. It never shows *why*, and "why" is what a reviewer needs to judge whether the change is correct. A description that states intent turns the reviewer from an archaeologist into an evaluator.

A strong description covers, briefly:

- **What** — one or two sentences on what this change does.
- **Why** — the problem, the bug, the requirement. Link the issue or design doc.
- **How to test** — the steps you ran, or the command, or what to click. Let the reviewer verify without guessing.
- **Screenshots / output** — for anything visual or user-facing, show before and after.
- **Risk and focus** — call out the parts you are unsure about, and tell the reviewer where to spend their attention.

That last point is underrated. You know your own change better than anyone. If there is a gnarly concurrency bit, or a place where you made a judgment call, *say so* and ask the reviewer to look there. You are directing their limited attention to where it pays off most.

```text
--- Bad PR description -----------------------------------
Title: fixes
Body:  (empty)
---------------------------------------------------------

--- Good PR description ---------------------------------
Title: fix: prevent double-charge on retried checkout

What
  Makes the checkout POST idempotent using the client-supplied
  Idempotency-Key header. Repeated requests with the same key
  now return the original result instead of charging again.

Why
  Closes #482. Users on flaky mobile connections were retrying
  the request and getting billed twice. Repro in the issue.

How to test
  1. POST /checkout twice with the same Idempotency-Key
  2. Second response is 200 with the first charge's id, no new charge
  3. `go test ./billing/... -run Idempotency`  (new tests included)

Risk / please focus on
  The Redis key TTL is 24h — I picked that somewhat arbitrarily.
  Please sanity-check billing/idempotency.go:41 for the
  race between "check key" and "write key" under concurrent retries.
---------------------------------------------------------
```

The good version costs the author five minutes and saves the reviewer thirty. That trade is the whole game.

**The gotcha:** a PR with no description forces the reviewer to reverse-engineer intent from the diff — and a reviewer who has to guess *why* you changed something cannot tell whether you changed it *correctly*. They will either ask you (a slow round-trip) or assume (a missed bug). State what, why, and how to test, every time, even for changes that feel obvious to you.

---

## Self-review first

Before you click "request review," read your own diff — the whole thing, top to bottom, as if someone else wrote it. This single habit catches an astonishing share of what reviewers would otherwise flag, and it costs you a few minutes.

Reading your own diff in the review UI (not your editor) changes what you see. Out of the flow of writing, in the same view your reviewer will use, the leftover `console.log`, the commented-out block, the debug print, the file you didn't mean to commit, the function whose name no longer matches what it does — they jump out. You wrote all of it and never noticed; seeing it framed as a *diff* makes it obvious.

Self-review is also where you leave the reviewer breadcrumbs. Use inline PR comments on your own diff to explain a non-obvious choice: "extracted this into a helper because it's reused in PR 3," or "this looks redundant but the SDK requires the second call — see their issue #99." A well-placed author comment answers the question the reviewer was about to ask, and it turns a "why on earth did they do this?" into a nod.

**The gotcha:** skipping your own self-review ships the typos, the debug prints, and the stray file straight to the reviewer, who now spends their scarce attention catching things you could have caught in two minutes. Worse, every trivial nit they file is a full round-trip of latency, and a diff full of obvious junk trains them to skim — so they are primed to miss the real bug when it comes. Self-review protects the reviewer's attention *and* your own credibility.

---

## Keep the noise out

A behavior-change PR should contain the behavior change and almost nothing else. Auto-formatter reflows, import reordering, whitespace fixes, a `black`/`gofmt`/`prettier` sweep across untouched lines — all of it is *noise* relative to the change under review, and every noisy line dilutes the signal.

The problem is signal-to-noise in the diff. If your PR touches 12 meaningful lines but the diff shows 400 because your editor reformatted the whole file on save, the reviewer has to visually filter 388 lines of nothing to find the 12 that matter. Most will not filter carefully. They will scroll, see mostly-formatting, and approve.

If a file genuinely needs reformatting, do it in a separate, clearly-labeled "format only, no behavior change" PR that a reviewer can approve at a glance precisely *because* they know none of it changes behavior. Keep those sweeps out of the PR where the actual thinking happens.

| Put in the PR | Keep out of the PR |
|---|---|
| The logic that implements the change | Formatter reflows of untouched code |
| Tests for the new behavior | Unrelated import reordering |
| Comments explaining the *why* | Renames that could be their own PR |
| Doc updates for the changed API | Drive-by fixes to nearby code |

Those drive-by fixes are tempting — you are right there, the typo in the neighboring function is *right there* — but each one widens the diff and blurs the change's story. Note it, file a follow-up, and keep this PR about one thing.

---

## Commit hygiene: atomic commits and the "why"

Even inside a single PR, commits matter — reviewers often walk a PR commit by commit, and the git history outlives the review by years. Two habits pay off.

**Atomic commits.** Each commit should be one self-contained step that builds and passes tests on its own. "Add validation, fix the flaky test it exposed, update the docstring" is three commits, not one blob. Atomic commits let a reviewer follow your reasoning in order, let `git bisect` actually find the bad change later, and let a bad step be reverted without dragging unrelated work with it.

**Messages that explain the why.** The diff already shows *what* the commit does; the message's job is *why*. "Update timeout to 30s" is worthless — the diff said that. "Raise timeout to 30s: p99 upstream latency is 22s, the old 10s tripped on every slow-region request" is a message that will answer someone's question two years from now, quite possibly your own.

```text
Weak:    fix bug

Better:  fix: guard against nil session in auth middleware

         The middleware assumed ctx always carried a session, but
         unauthenticated health-check requests reach it with none,
         causing a panic under load balancer probes. Return 401
         early when the session is absent. Closes #611.
```

Good commit messages and a good PR description reinforce each other: the description is the map, the commits are the route. Together they let the reviewer — and every future reader — reconstruct not just what you did but why it was the right thing to do.

---

## Make the tests visible

When you add or change behavior, make the tests part of the story rather than something the reviewer has to go dig for. Include the tests in the same PR as the behavior. Mention in the description what they cover — and, honestly, what they don't. If a path is hard to test and you tested it manually instead, say that too.

Visible tests do two jobs at once. They give the reviewer evidence that the change works, so the review can focus on design and edge cases instead of "did you even run this." And a well-named test doubles as documentation of intent: `TestCheckout_RetryWithSameKey_DoesNotDoubleCharge` tells the reviewer exactly what guarantee you believe you are providing, which is something they can then agree or disagree with. Tests are not a chore appended to the change; they are part of the argument that the change is correct.

---

## Responsiveness: keep the loop tight

The author's job is not done at "request review." A review is a conversation, and its total latency is dominated by round-trip time, not reading time. Small PRs and fast author replies compound: a 100-line PR the author responds to within the hour can be opened, reviewed, revised, and merged the same day. The same work as a 1,000-line PR with day-long gaps between replies takes a week and everyone loses the mental context in between.

So when comments come in, engage quickly while the change is still fresh in your head *and* the reviewer's. Answer questions, push fixes, and mark threads resolved so the reviewer can see what is left. If you disagree, say why — a review is a discussion, not a set of orders — but do it promptly. The reviewer gave you their attention; matching their pace is how you honor it and keep the loop tight.

---

## Key takeaways

- **You are spending the reviewer's attention.** Every author habit here exists to conserve that one finite resource — size, description, self-review, and clean diffs all buy back attention for the parts that matter.
- **Small, focused PRs get real reviews; big ones get rubber-stamps.** One logical change per PR. If it needs the word "and" to describe, split it.
- **Split by stacking and by separating refactor from behavior.** Move the furniture in one PR, change behavior in another, so the diff shows only the lines that change what the program does.
- **Write the description the reviewer needs:** what, why, how to test, and where to focus — including the risky parts you are unsure about.
- **Self-review first.** Read your own diff in the review UI, catch the obvious, and leave breadcrumb comments on the tricky lines before anyone else has to.
- **Keep formatting and drive-by noise out** of a behavior-change PR, write atomic commits whose messages explain the *why*, make tests visible, and reply fast.

None of this is about being a nicer person (though it reads that way). It is about mechanics: a review is only as good as the attention a human can bring to it, and the author controls how much of that attention survives contact with the diff.

## Further reading

- [Google Engineering Practices — Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) — the case for small changelists and how to split large ones, from Google's public code-review guide.
- [Google Engineering Practices — Writing good CL descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html) — what a first line and body should contain, with good and bad examples.
- [Graphite — Stacked pull requests](https://graphite.dev/guides/stacked-pull-requests) — a primer on breaking a large change into an ordered chain of small, independently reviewable PRs.
- [How to Write a Git Commit Message](https://cbea.ms/git-commit/) — Chris Beams's widely-cited guide to atomic commits and messages that explain the why.
