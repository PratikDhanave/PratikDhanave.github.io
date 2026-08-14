# Why Code Review

*The first post in a practical series on code review — what the practice is actually for, what it is not, and why treating it as a collaboration rather than a gate is what makes it worth the time it costs.*

---

Somewhere between writing code and shipping it, another engineer reads what you wrote and says something back. That exchange is code review, and it is one of the highest-leverage habits a team can build — or one of the most quietly demoralizing, depending entirely on how the team frames it. Over years of reviewing and being reviewed, I've come to believe the mechanics (the tool, the diff, the approve button) matter far less than the intent behind them. This series is about doing code review well; this opening post is about being clear on *why* we do it at all, because almost every bad review habit traces back to a fuzzy answer to that question.

Let me start with a claim that sounds obvious but rarely gets acted on: **the primary purpose of code review is not to find bugs.** Bugs are one output, and a valuable one, but if catching defects were the whole story we'd lean harder on tests and static analysis and skip the human step. Review earns its cost because a second person builds *understanding* of the change — and understanding is the thing that compounds.

---

## What review is actually for

When I approve a change, I'm signing my name to several outcomes at once. Naming them makes it easier to review with purpose instead of skimming for typos.

**Catching defects early.** A logic error found in review costs a comment. The same error found in production costs an incident, a rollback, and a postmortem. Review is the cheapest place in the pipeline to catch a class of problems that tests miss — the ones where the code is correct against the tests but wrong against reality, or where the tests themselves encode the wrong assumption.

**Improving design and maintainability.** This is where review pays its largest dividend and where it's most often skipped. The question isn't only "does this work?" but "will the next person who touches this understand it?" A reviewer who has never seen the change comes to it with fresh eyes — the same fresh eyes the future maintainer will have. If the reviewer is confused, that confusion is a signal, not a personal failing.

**Sharing knowledge and context.** Every review spreads know-how in two directions. The reviewer learns a corner of the system they didn't own. The author learns a pattern, an API, or a piece of history the reviewer carries. Over months this is how a team stops having single points of failure — the person who "is the only one who understands billing" becomes two people, then four.

**Consistency.** Not cosmetic consistency (a formatter handles that) but conceptual consistency: this codebase solves this kind of problem this way. New code that follows the grain of the existing system is easier to read, easier to change, and less surprising at 2 a.m.

**Collective ownership.** Once I've reviewed and approved your change, it is partly mine. That shift is subtle and important. It means the code belongs to the team, not to whoever typed it, and it means nobody has to be afraid to modify code they didn't originally write.

---

## What review is not for

Just as important is naming the goals review should *not* serve, because these are the failure modes that make people dread the review queue.

**It is not a gate to prove you can be trusted.** Review is a default collaboration, not a hazing ritual or a checkpoint where senior engineers decide whether juniors are worthy. When review feels like passport control, people start writing smaller, safer, less honest changes just to get through — and the whole point is lost.

**It is not a stage for proving you're the smartest person in the room.** A review comment that exists mainly to demonstrate the reviewer's cleverness costs the author time and morale and rarely improves the code. If a comment doesn't make the change better or teach something useful, it probably shouldn't be written.

**It is not the place to bikeshed style a linter should own.** Arguing about tabs, import ordering, or brace placement in a review is a waste of two engineers' attention. If a rule can be automated, automate it and let the machine be the bad guy. Human review time is expensive; spend it on the things only a human can judge — clarity, design, correctness of intent.

**The gotcha:** the most common way review goes wrong isn't harshness, it's *aimlessness* — a reviewer skimming for something to comment on because leaving no comments feels like not doing the job. An approval with "this looks good, I traced the concurrency path and the lock ordering holds" is a far better review than fifteen nitpicks about variable names. Silence after genuine understanding is a valid, valuable review.

---

## The dual nature: technical and human

Here's the part that trips up strong engineers. Code review is a technical practice wrapped inside a communication practice, and the communication layer is doing more work than the technical layer.

Consider the same substantive point delivered two ways. The change reaches for a value that might not be there:

```diff
- user := lookup(id)
- return user.Plan.Tier
+ user, ok := lookup(id)
+ if !ok {
+     return "", fmt.Errorf("no user for id %q", id)
+ }
+ return user.Plan.Tier, nil
```

A reviewer could write: *"This will panic. Obviously you need to handle the missing case."* Or they could write: *"If `lookup` misses, `user` is the zero value and `user.Plan` will nil-panic. Want to return an error here so the caller can decide?"* The technical content is identical. The second one gets the fix made and keeps the author willing to send you their next change. The first one gets the fix made and quietly teaches the author to route around you.

This is why the human side isn't soft-skills garnish on top of the "real" engineering. The whole mechanism depends on people continuing to submit honest work and continuing to read feedback with an open mind. Both of those are trust behaviors, and trust is spent or built with every comment.

The framing I keep coming back to: **the reviewer and the author are on the same side, and the code is the thing being examined — not the author.** "This function is confusing" puts the code on the table. "You wrote this confusingly" puts the person on the table. Same observation, completely different relationship. We'll spend two full posts of this series on this, one from each chair.

---

## Cost, benefit, and collaboration

Review is not free. It interrupts the reviewer, it adds latency between "done" and "merged," and a slow review queue is a real drag on a team's throughput. Pretending it's costless leads to the two opposite dysfunctions: teams that skip review entirely to move fast, and teams that turn it into a multi-day bureaucratic ordeal.

The way through is to treat cost and benefit honestly and design norms that maximize the ratio. That's mostly about *size and speed*. A 40-line change gets a careful, fast, genuinely useful review. A 2,000-line change gets a rubber stamp, because no human reviews 2,000 lines well — they skim, approve, and hope. Small changes reviewed quickly is the single highest-leverage norm a team can adopt, and it's a shared responsibility: authors keep changes small, reviewers respond promptly.

There's a well-known industry study of a large code review program at Cisco, run by SmartBear in the mid-2000s, whose most-cited finding is a practical ceiling: reviewer effectiveness drops off sharply once a single review runs past a few hundred lines of code, and past an hour of continuous reviewing. I don't cite it for a precise number — the exact figures are specific to that study's context — but the shape of the result matches everything I've seen: attention is finite, and a giant diff spends it all on the first screen. The lesson is behavioral, not numeric. Keep changes small enough that a reviewer can hold the whole thing in their head.

---

## What review does not replace

A recurring mistake is loading all quality expectations onto review, as if a human reading the diff could stand in for everything else. It can't, and expecting it to makes reviews slower and worse. Review *complements* the rest of the pipeline; it doesn't substitute for any of it.

| Concern | Owned by | Review's role |
|---|---|---|
| Formatting, style rules | Formatter / linter | Should never come up in review |
| Regression safety | Automated tests + CI | Confirm tests exist and match intent |
| Broad architecture decisions | Design review / RFC | Enforce the agreed design, not relitigate it |
| Type and contract correctness | Compiler / type checker | Spot-check the human-judgment gaps |
| Clarity, intent, maintainability | Code review | Its irreplaceable job |

The row that matters most is the last one. Tests tell you the code does what the tests say; they can't tell you whether a future engineer will understand it, whether the abstraction fits the problem, or whether the change quietly contradicts a decision made in a design doc six months ago. That judgment is exactly what a human reviewer is for. Let the machines own everything a machine can own, so the human review can spend all its attention on what only a human can judge.

And note the architecture row: review is the wrong venue to relitigate a decision that a design review already settled. If the design is wrong, that's a conversation to have in the design forum, not a surprise ambush in a pull request three weeks later. Review enforces the agreed design; it doesn't reopen it.

---

## Setting healthy norms

None of this happens by accident. Teams with good review culture have usually made a few choices explicit:

- **Review is a default, not an exception.** Every non-trivial change gets a second set of eyes. When review is normal, nobody reads a review request as an accusation.
- **Changes are small by default.** Authors do the work of splitting large efforts into reviewable pieces. This is a gift to the reviewer and, ultimately, to the author who gets faster, better feedback.
- **Turnaround is fast.** A review sitting for two days blocks a teammate and invites context-switching costs on both sides. Many strong teams treat responding to reviews as something you do within a business day, ahead of starting new work.
- **Comments distinguish blocking from optional.** "This is a correctness bug" and "nit: I'd name this differently" should never look the same. Labeling intent keeps small suggestions from masquerading as gates. We'll get concrete about this vocabulary later in the series.
- **The author decides on judgment calls, within reason.** Once correctness and agreed standards are satisfied, minor preferences default to the author. Endless back-and-forth on taste is how reviews die.

---

## Where this series is going

This post set the frame. The rest of the series gets specific, roughly in this order:

1. **Why code review** (this post) — purpose, dual nature, cost/benefit, and norms.
2. **What to look for** — a reviewer's mental checklist: correctness, design, naming, tests, edge cases, and the difference between "wrong" and "not how I'd do it."
3. **Giving feedback** — writing comments that get acted on: tone, specificity, the blocking/optional vocabulary, and knowing when to stop.
4. **Receiving feedback** — reading review without defensiveness, when to push back, and how to disagree productively.
5. **The author's craft** — making your change easy to review: small diffs, good descriptions, self-review, and telling the story of the change.
6. **Security and performance review** — the specialized lenses: input handling, secrets, authz, allocations, and hot paths — and knowing when to pull in an expert.
7. **Review at scale** — keeping review healthy across large teams and repos: ownership, SLAs, batching, and avoiding reviewer burnout.
8. **AI-assisted review** — where automated reviewers genuinely help, where they mislead, and how to keep a human accountable for the approval.

---

## Key takeaways

- **Review's core value is shared understanding, not bug-catching.** Bugs are a welcome side effect; the compounding payoff is design quality, spread knowledge, and collective ownership.
- **Name what review is not for.** It is not a gate, a stage for cleverness, or a place to argue style a linter should own. Aimless nitpicking is the most common failure mode.
- **It's a communication practice as much as a technical one.** Same technical point, different framing, opposite effect on trust — put the code on the table, not the person.
- **Review complements the pipeline; it replaces none of it.** Let formatters, tests, CI, type checkers, and design review own what they own, so human attention goes to clarity and intent.
- **Healthy norms are deliberate:** review as a default, small changes, fast turnaround, and comments that separate blocking issues from preferences.

The reviewer and the author want the same thing — code the whole team can trust and maintain. Every other post in this series is downstream of that one idea.

---

## Further reading

- [Google's Code Review Developer Guide (eng-practices)](https://google.github.io/eng-practices/review/) — Google's public, opinionated guidance on the reviewer's and author's responsibilities, review speed, and how to navigate disagreement.
- [The SmartBear / Cisco code review case study](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/) — SmartBear's write-up of a large-scale peer review program at Cisco, including the practical limits on review size and duration before effectiveness drops.
- [M. E. Fagan, "Design and code inspections to reduce errors in program development" (IBM Systems Journal, 1976)](https://www.computer.org/csdl/magazine/so/2002/04/s4032/13rRUwbs2gz) — the origin of formal software inspection, which established that structured peer examination catches defects far earlier than testing alone.
- [Martin Fowler on Refactoring and code quality](https://martinfowler.com/tags/refactoring.html) — Fowler's ongoing writing on why readable, well-factored code is an economic decision, which is the lens most useful in review.
