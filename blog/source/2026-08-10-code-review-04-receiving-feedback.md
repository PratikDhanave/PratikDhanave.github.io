# Receiving Feedback Well

*The author's side of code review — turning a pull request from an ego threat into a growth loop by separating your identity from your code, responding to every comment, and pushing back with reasoning instead of feelings.*

---

Most advice about code review is written for the reviewer: how to leave a good comment, how to be kind, how to spot bugs. This is the other half. When you open a pull request, you become the *author* under review, and how you receive feedback shapes both the code that ships and the engineer you become. The reviewer's comments are a gift with a bad reputation — they arrive looking like criticism and, if you let them, they feel like an attack. The whole skill is learning to receive them as what they usually are: free, careful attention to your work from someone who wants it to be good.

This post is about that skill. Not how to write comments, but how to read them, act on them, and disagree with them without the whole thing becoming about your pride.

---

## The single biggest unlock: the code is not you

You wrote the code, so a comment about the code feels like a comment about you. That reflex is the root of almost every bad review interaction, and naming it is most of the cure. When a reviewer writes "this is wrong," your nervous system hears "you are bad at your job." From there the defensive spiral starts: you explain, you justify, you look for reasons the reviewer is mistaken — anything but actually reading what they said.

The code you wrote yesterday is a snapshot of what you understood yesterday. It is an artifact, external to you, and it can be improved without any of that improvement being a verdict on your worth. A senior engineer with fifteen years of experience still gets "this has a race condition" comments, and the difference between them and a junior is not that they make fewer mistakes — it's that they don't flinch. They read "this has a race condition" as new information about the code, full stop.

Try a small reframe: the reviewer is not grading you, they are helping you ship something better than you could ship alone. Every comment is a place where two brains caught what one brain missed. That is the entire point of review.

**The gotcha:** reading "this is wrong" as "I am bad" triggers a defensiveness that literally blocks learning — you spend your attention defending instead of understanding, and the actual lesson slides right past. The code is not your identity. Once you internalize that critique of the code is not critique of you, the emotional charge drains out of the whole process and you can just... fix the code.

---

## Assume good intent

Text has no tone. A comment like "why is this here?" can read as genuinely curious or as a sneer, and your brain will supply whichever tone matches your current mood. Almost always, the sneer is invented. Your reviewer typed a fast question between two meetings; they were not composing an insult.

Default to the most generous reading. "Why is this here?" means "help me understand the reason for this line," not "this line is stupid." "Did you consider X?" means they want to know if X was on your radar, not that you're an amateur for missing it. When you assume good intent, you respond to the actual question instead of to the imagined attack, and the conversation stays technical.

If a reviewer genuinely *is* being hostile — condescending, sarcastic, dismissive — that is a real problem, but it's a problem to raise directly and calmly ("this comment came across as harsh, can we talk about it?") or take to a manager, not to litigate inside the PR thread. The vast majority of the time, the hostility was never there.

---

## Respond to every comment

This is the mechanical rule that prevents most friction: **reply to every single comment.** Not "read every comment" — reply. There are exactly two acceptable responses to a review comment, and silence is neither.

1. **Accept and do it.** Make the change, then reply "done" (or let the resolved thread speak for itself if your tool links commits to comments). The reviewer needs to know their comment landed.
2. **Explain why not.** If you're not making the change, say so and say why. "I left this as-is because the caller already validates the input — see line 40." Now the reviewer can agree, or push back with something you hadn't considered.

What you must never do is silently push a new commit that ignores a comment. From the reviewer's side, that's maddening: did you see it? Did you disagree? Are you going to address it later? They now have to re-read your whole diff to figure out what happened to their feedback, and trust erodes. A one-word "done" costs you three seconds and saves them that entire investigation.

**The gotcha:** silently pushing a change without replying to the comment leaves the reviewer genuinely unsure whether you even saw it — and a reviewer who isn't sure their feedback registered will either re-litigate it or stop bothering to leave it. Always respond, even if the response is just "done" or "disagree, because…". The reply is the receipt.

---

## How to push back — with reasoning, not ego

Sometimes the reviewer is wrong, or working from less context than you have. You've been living in this code for two days; they've been looking at it for ten minutes. You are allowed — encouraged — to push back. The question is *how*.

The pattern is **disagree-and-explain**: state your position, then give the reasoning or the data that supports it. Not "I think this is fine" (that's a feeling) but "I benchmarked both approaches and the map version is 3x faster on the hot path — here are the numbers." Reasoning persuades; assertion just restarts the argument.

Compare a defensive reply with a constructive one. Same disagreement, completely different outcome.

```text
Defensive (ego-driven):

Reviewer: This function is doing too much — could we split
          the parsing out from the validation?

Author:   It's fine, I've written it this way plenty of times.
          Splitting it would just add more files for no reason.
          Let's not over-engineer this.
```

```text
Constructive (reasoning-driven):

Reviewer: This function is doing too much — could we split
          the parsing out from the validation?

Author:   Good call on the smell. I actually kept them together
          on purpose: the validation depends on partial parse
          state (the offset in `pos`), so splitting means threading
          that state through a second function. I think that's more
          coupling, not less. Open to it if you see a clean seam I'm
          missing — want to hop on a quick call?
```

The second reply disagrees just as firmly, but it grants the reviewer's point ("good call on the smell"), gives a concrete reason, and leaves a door open. Nobody's ego is on the table, so the conversation can actually resolve.

If two rounds of back-and-forth don't converge, stop typing. Text is a terrible medium for nuanced disagreement. **Escalate to a call**, where five minutes of talking usually dissolves what would've been twenty comments. If you *still* can't agree, bring in a third opinion — a tech lead or another engineer who knows the area — and let a tie-breaker decide.

And when the decision goes against you on something that isn't a correctness issue: **disagree and commit.** Say your piece once, clearly, with your reasoning. If the reviewer or the team still lands on the other side, accept it gracefully, make the change, and move on without resentment. "I still lean the other way, but it's not a hill worth holding — making the change." You keep your credibility for the disagreements that truly matter, and you don't become the person every PR has to route around.

**The gotcha:** pushing back with feelings ("I don't like it," "this feels wrong," "I've always done it this way") instead of reasoning or data almost never persuades — it just signals that your ego is engaged, and the reviewer digs in. Bring the *why*. A benchmark, a link to the ticket, a concrete failure case: those move people. Vibes don't.

---

## Nits, thanks, and the "just approve it" trap

Not every comment carries the same weight. Reviewers often prefix small stylistic suggestions with "nit:" — a nitpick, take-it-or-leave-it. These are the lowest-stakes comments in the whole review, and they're the ones most likely to sting, because they feel like the reviewer is picking at trivia. Don't take nits personally. Fix the easy ones (renaming a variable costs nothing and the reviewer clearly cares), push back on the ones you disagree with, and never let a nit trigger the defensive spiral. A nit is a reviewer being *thorough*, not a reviewer being *petty*.

Say thank you. Genuinely. Someone spent their time making your code better, catching a bug that would've paged you at 2 a.m., or teaching you a pattern you didn't know. "Good catch, thanks — fixed" costs nothing and makes people want to review your PRs carefully next time. Review is a repeated game; gratitude compounds.

Now the counter-pressure: the urge to make every requested change instantly just to get the approve and ship. This feels like being agreeable, but it's a trap. If you cave on a design decision you know is right merely to close the review faster, you ship a worse design and you teach yourself that convenience beats correctness. Speed is a real value, but not at the cost of silently accepting changes you believe make the code worse. Disagree-and-explain when you have real context; accept fast when you don't. The skill is telling those two situations apart.

**The gotcha:** caving to every comment just to earn the approve quickly can ship a genuinely worse design — you had context the reviewer didn't and you swallowed it for speed. When you actually know better, disagree-and-explain; save the fast yes for the (many) comments where the reviewer is simply right.

---

## Conflicting reviewers and truly optional comments

Two reviewers, two opposite requests. Reviewer A wants the config inlined; Reviewer B wants it extracted. Don't ping-pong between them, satisfying one and then the other. Surface the conflict openly: "@A and @B, you're pointing in opposite directions on the config — can you two settle on one so I implement it once?" Make the disagreement *theirs* to resolve, because it is. Your job is to write the code once, not to be the rope in a tug-of-war.

Learning to recognize a truly optional comment is its own skill. Signals that a comment is optional: the "nit:" prefix, hedging language ("maybe," "consider," "could"), or an explicit "non-blocking / feel free to ignore." Signals that it's *not* optional: anything about correctness, security, data loss, or a broken test. When in doubt, ask — "is this blocking or a nice-to-have?" A reviewer will happily tell you, and now you can prioritize instead of treating a style preference and a null-pointer bug as equally urgent.

| Comment type | Signal | Your move |
|---|---|---|
| Correctness / security | "this will crash," "race condition," failing test | Fix it, always |
| Design disagreement | "should we structure this differently?" | Disagree-and-explain, or accept with reasoning |
| Nit / style | "nit:", "consider," "maybe" | Fix if cheap, push back if not — never stress |
| Conflicting reviewers | two opposite requests | Surface it, let them resolve |
| Explicitly optional | "non-blocking," "feel free to ignore" | Your call; note your decision either way |

---

## Close the loop

A review isn't done when the code is merged — it's done when everyone knows what happened to their feedback. Mark threads resolved as you address them, so the reviewer sees a shrinking list instead of re-reading everything. When you push the batch of changes, leave a short summary comment: "Addressed all feedback — extracted the parser, added the null check, and left the validation coupled with a note explaining why." That one paragraph lets the reviewer re-review in two minutes instead of twenty, and it signals that you took the whole review seriously.

Closing the loop is the small courtesy that makes people want to work with you. It's the difference between "I threw my code over the wall and you deal with it" and "we built this together." Over a career, that difference is enormous.

---

## Key takeaways

- **The code is not you.** Separating your identity from your work is the single biggest unlock — critique of the code is not critique of you, and that reframe drains the emotion out of every review.
- **Assume good intent.** Text has no tone; your brain invents the hostile one. Read the generous version and answer the actual question.
- **Respond to every comment.** Accept and do it, or explain why not. Silence — pushing a change with no reply — is the fastest way to erode a reviewer's trust.
- **Push back with reasoning, not feelings.** Disagree-and-explain, bring data, escalate to a call or a third opinion if stuck, and disagree-and-commit once the decision is made.
- **Don't take nits personally, say thank you, and resist the "just approve it" pressure.** Accept fast when the reviewer is right; hold your ground with reasoning when you have context they don't.
- **Close the loop.** Resolve threads, summarize what changed, and make the reviewer's re-read cheap. Reviews make you better — treat them that way.

---

## Further reading

- [Douglas Stone & Sheila Heen, *Thanks for the Feedback*](https://www.stoneandheen.com/thanks-for-the-feedback) — the primary text on why receiving feedback is a distinct, learnable skill and how to separate the message from the relationship.
- [Google's Code Review Developer Guide — The CL author's guide](https://google.github.io/eng-practices/review/developer/) — the author-side companion to Google's reviewer guidance, covering how to handle reviewer comments and pushback.
- [Netflix's "disagree and commit" and the informed-captain model](https://igormroz.com/documents/netflix_culture.pdf) — how a high-trust team resolves disagreement without stalling on consensus.
