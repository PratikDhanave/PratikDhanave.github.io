# AI-Assisted Code Review

*The series finale — where LLM reviewers genuinely help on every pull request, where they quietly fail, and how to build a human-plus-AI workflow that speeds review up without letting judgment or accountability leak away.*

---

Every post in this series has argued the same point from a different angle: code review is a human practice. It is a conversation about design, a negotiation about risk, and a slow-drip transfer of context between people who will maintain the code long after the pull request merges. So the arrival of AI reviewers that comment on a diff in seconds is worth being precise about. Used well, an LLM reviewer removes the drudgery that makes human reviewers slow and grumpy. Used carelessly, it manufactures noise, invites rubber-stamping, and lets a team ship code that no human ever actually read.

This post is the capstone: what AI review is genuinely good at today, where it falls short and needs a person, and the division of labor that gets you the speed without giving up the judgment. I'll talk about capabilities by category — LLM-based reviewers, IDE assistants, and PR-review bots — rather than naming products, because the categories are stable and the specific tools change every quarter.

---

## What AI review is genuinely good at

Start with the honest wins, because there are real ones. An LLM reviewer is tireless, instant, and unbothered by the hundredth pull request of the day — which changes the economics of the mechanical layer of review. An AI first pass is good at:

- **Running on every PR, immediately.** No waiting for a human to have a free half hour — a first pass lands within a minute of opening the PR, while the change is still fresh in the author's head.
- **Catching mechanical issues.** Off-by-one boundaries, an error path that returns before releasing a lock, a `nil`/`null` that isn't checked, a resource that isn't closed, a swapped argument order — exactly the small correctness slips human reviewers miss when skimming.
- **Surfacing missing tests and edge cases.** "This function has no test for the empty-slice case" or "what happens when `count` is negative?" — an LLM produces these well, pattern-matching against a huge corpus of similar functions and their failure modes.
- **Convention and boilerplate nits.** Naming that drifts from the surrounding file, a magic number that should be a constant, inconsistent error-wrapping. Low-value for a human to type out; fine for a machine to flag.
- **Explaining unfamiliar code.** Ask what a dense regex or a gnarly bit-manipulation function does and you get a plain-language summary you can verify — a huge accelerant when reviewing a subsystem you don't own.
- **Summarizing large diffs.** A 40-file refactor is exhausting to orient to; a generated "here's what changed and why" gives a reviewer a map before they start.
- **Drafting the PR description.** From the diff it proposes a first draft of the "what and why" that the author corrects, raising the floor on description quality across a team.

Notice the shape of all of these: they are the *cheap, high-volume, low-context* parts of review — precisely the work that, when a human does it, crowds out the expensive thinking. Offloading them is the point.

---

## Where it falls short and needs a human

The failures cluster in the areas this series has spent the most time on, which is no coincidence. The hard parts of review are hard *because* they require context the model doesn't have.

**Deep design and architecture judgment.** The highest-value questions from post 2 — is this the right abstraction, will this boundary hold as the system grows, is this coupling going to hurt in six months — depend on where the codebase is heading and what the team has decided *not* to do. An LLM sees the diff, not the roadmap or the two prior design debates. It can tell you a function is long; it cannot tell you the whole feature is a mistake.

**Whether the change should exist at all.** This is the highest-leverage review question and the one AI is worst at. Approving a well-formed change that solves the wrong problem is worse than blocking a scrappy one that solves the right problem. That call is about intent and priorities, and it lives with a human.

**Correctness against business intent.** A function can be flawless and still be wrong, because "correct" means "matches what the business needed" — and that spec lives in a person's head, a ticket, and three Slack threads, not in the diff. The model has no way to know that `net_amount` is supposed to exclude tax in your domain.

**Cross-file and system-level reasoning.** AI reviewers work best on the diff in front of them. They are weakest at reasoning that spans the change and the twelve call sites it affects, the migration that has to land first, or an invariant maintained in a file that isn't in the PR.

**Security bugs that need context.** Post 6 covered this: the dangerous vulnerabilities are the contextual ones. A broken-object-level-authorization (BOLA) bug — where an endpoint fetches a record by ID but never checks that the *caller* may see *that* record — looks like completely ordinary code. Nothing in the diff is syntactically wrong. Catching it requires knowing the authorization model, and that knowledge is a human's.

**Confident, plausible, wrong.** LLMs hallucinate. A reviewer bot will occasionally tell you, in a calm authoritative tone, that your code has a race condition it does not have, or cite an API that does not exist. The wrongness is not flagged as uncertain — it reads exactly like the correct comments do.

**It cannot own accountability.** When a change breaks production at 2 a.m., "the AI approved it" is not an answer. Sign-off is a person putting their name on a judgment. A model can advise; it cannot be accountable.

> **The gotcha:** an AI reviewer is confidently wrong sometimes, and its wrong comments look identical to its right ones. An unverified AI comment is a *suggestion*, not a verdict. Treat every one as "a smart colleague thinks maybe" and check it before you act — especially before you make the author act on it.

---

## The workflow: AI clears the noise, humans spend attention on judgment

The mistake is framing this as "AI review versus human review." The frame that works is **AI as the first-pass reviewer** whose job is to clear the mechanical layer so human attention — the scarce, expensive resource — is spent entirely on design and correctness.

Here's the flow that holds up in practice:

```text
1. Author opens PR (having already self-reviewed — see below).
2. AI bot posts a first pass within a minute:
     - a diff summary
     - mechanical nits and likely-missing tests
     - questions about edge cases
3. Author triages the AI pass BEFORE a human looks:
     - fixes the real nits
     - dismisses the false positives (with a one-line why)
4. Human reviewer arrives to a cleaned-up PR and spends
   their whole budget on: should this exist? is the design
   right? is it correct against intent? any contextual risk?
5. Human owns the approve/block decision.
```

The value is in steps 3 and 4. By the time a person opens the PR, the trivial stuff is already resolved, so their limited attention goes to the questions only they can answer. The AI didn't replace the reviewer — it removed the reasons reviewers procrastinate and skim. You make human review *better* by making it *cheaper to focus*.

---

## Calibrating trust: treat a noisy bot like a mis-tuned linter

The failure mode that kills AI review adoption is noise. A bot that posts fifteen comments per PR, ten of them wrong or trivial, trains everyone to stop reading it — the same way a linter with a hundred false positives gets globally disabled and takes its five real warnings down with it.

So calibrate deliberately:

- **Verify before you forward.** If you'll relay an AI comment to the author, confirm it's real first — your name is on it now.
- **Treat comments as suggestions, not gates.** An AI pass should inform a human decision, not block a merge on its own.
- **Tune for precision over recall.** A bot that says less but is right earns trust; one that says everything gets muted. Prune the rules that misfire on your codebase.
- **Watch the dismiss rate.** If your team dismisses most AI comments, that's the signal to retune — not to try harder to make people read them.

```diff
  // An AI comment worth keeping — specific, checkable, right:
- results := make([]Item, len(rows))
- for i := range rows {
-     results = append(results, convert(rows[i]))   // bug: double-length slice
- }
+ results := make([]Item, 0, len(rows))
+ for i := range rows {
+     results = append(results, convert(rows[i]))
+ }

  // An AI comment worth dismissing — confident and wrong:
  // "This map access is a data race."   (the map is local to the
  //  goroutine; no other goroutine can see it. False positive.)
```

> **The gotcha:** a noisy AI reviewer decays exactly like a mis-tuned linter — people don't argue with it, they mute it, and then it catches nothing. Tune for precision and prune false positives aggressively, or the whole tool quietly becomes decoration.

---

## Use AI as the author, too — self-review before you ask for a human

Post 5 was about the author's craft: the small PR, the clean history, the honest description, the self-review pass before you spend another person's time. AI is a genuine multiplier on every one of those. Before you request human review, run the diff through an AI pass yourself and act on it:

- Have it **draft the PR description** from the diff, then correct it — faster than a blank box, and it forces you to notice anything the diff does that your summary doesn't mention.
- Have it **flag your own mechanical slips** so a human never has to type "you forgot to close this."
- Have it **ask the edge-case questions** so you can either handle them or answer them pre-emptively in the description.

This is the highest-return use of AI in the whole loop, because the author has the most context and can instantly tell a real comment from a hallucinated one — you're using the model where verification is cheapest. The human reviewer then receives a PR that already survived a first pass, which is exactly the courtesy post 5 argued for, now automated.

---

## The risks, named plainly

The upside is real, and so are these. Each is a way a team can adopt AI review and end up worse off than before.

**Automation bias.** People trust an authoritative-looking machine verdict more than they should. A reviewer who sees "AI review passed ✓" is tempted to skim and approve — the failure that erases the entire point, since the human is there precisely to do the reading the AI can't.

> **The gotcha:** automation bias makes reviewers rubber-stamp an AI-approved PR — "the bot's happy, ship it." The AI pass clears the noise; it does not discharge the human's duty to read. If nobody with context actually read the change, it wasn't reviewed.

**AI approving AI-written code.** More and more PRs are AI-authored. If an AI reviewer then approves them with no human in the loop, you have a closed loop with no judgment anywhere in it — and errors compound instead of getting caught. Two models sharing the same blind spots do not check each other; they agree.

> **The gotcha:** AI reviewing AI-written code with no human in the loop is not review — it's two systems with correlated blind spots nodding at each other. Keep a person on the approve decision, especially for machine-authored changes.

**Privacy and IP.** Sending source code to an external model means your proprietary code left your building. Depending on the tool and the contract, it may be logged, retained, or used for training. For some code — regulated, secret, or contractually restricted — that's a real problem, not a hypothetical one.

> **The gotcha:** sending proprietary code to an external model has privacy and IP implications. Know your tool's data-handling terms — retention, training use, region — before you point it at a private repo. "It's just a review bot" is not a data-governance policy.

**Gaming.** Any metric becomes a target. If AI review coverage becomes a number someone reports, people will optimize the number — auto-approving, suppressing comments, or configuring the bot to be toothless — rather than the underlying quality. Measure outcomes (escaped defects, review latency), not review-tool activity.

---

## A healthy division of labor

Put it together and the split is clean — give each side the work it's actually good at.

| Concern | Best owner | Why |
|---|---|---|
| Mechanical nits, style, boilerplate | AI first pass | High volume, low context, tireless |
| Missing tests / edge cases surfaced | AI first pass | Strong pattern-matching against similar code |
| Diff summary, PR description draft | AI | Fast orientation; author corrects |
| Explaining unfamiliar code | AI (then verify) | Instant plain-language map |
| Should this change exist? | Human | Needs intent and priorities |
| Is this the right design? | Human | Needs the roadmap and system context |
| Correctness against business intent | Human | The spec lives in people, not the diff |
| Contextual security (e.g. BOLA) | Human | Needs the authorization model |
| The approve / block decision | Human | Only a person can own accountability |

The line is not "simple versus complex" — it's **context**. Where the judgment needs context the model doesn't have (intent, architecture, authorization, priorities), a human owns it. Everywhere else, let the machine take the load off.

---

## The series, tied together

This has been an eight-post arc telling one story:

- **Post 1 — why.** Code review is collaboration and knowledge transfer, not a gate.
- **Post 2 — what to look for.** Design and correctness first; style last.
- **Post 3 — giving feedback.** Comments are communication; tone and specificity decide whether they land.
- **Post 4 — receiving feedback.** Separate your identity from your code; respond to everything; push back with reasoning.
- **Post 5 — the author's craft.** Small PRs, honest descriptions, self-review — making your change easy to review is the author's job.
- **Post 6 — security and performance.** The dangerous bugs are contextual; you have to know the system to see them.
- **Post 7 — at scale.** Making all of this work across a large team without review becoming a bottleneck.
- **Post 8 — this one.** AI accelerates the mechanical layer so humans spend their attention where judgment lives.

The throughline is the thing to keep. Code review is a human communication and judgment practice. Every tool in this post makes it faster, cheaper, and less tedious — none makes it not-human. AI is the best assistant the reviewer has ever had; it is not the reviewer. Keep a person on design, correctness, and accountability, let the machine clear everything else, and you get review that's fast *and* thoughtful. That was the goal from post 1 — and it's more achievable now, because for the first time the tedious half is genuinely optional.

---

## Key takeaways

- **AI is excellent at the mechanical layer** — instant first pass on every PR, boundary/null/leak slips, missing tests, convention nits, diff summaries, and drafting the PR description.
- **AI is weak exactly where this series spent its effort** — design judgment, whether a change should exist, correctness against intent, cross-file reasoning, and contextual security bugs like BOLA.
- **It's confidently wrong sometimes.** An unverified AI comment is a suggestion, not a verdict — verify before you forward.
- **The workflow is AI-first-pass, human-final-judgment.** The bot clears noise so the human spends their whole budget on design and correctness. Use AI as the author too — self-review before you request a person.
- **Watch the human risks:** automation bias (rubber-stamping), AI approving AI-written code with no human in the loop, privacy/IP of sending code to an external model, and gaming any coverage metric.
- **The throughline:** code review is a human communication and judgment practice that AI accelerates but does not replace.

---

## Further reading

- [Google's Code Review Developer Guide (eng-practices)](https://google.github.io/eng-practices/review/) — the human standard this whole series leans on: reviewer and author responsibilities, review speed, and navigating disagreement. Read it as the definition of the job AI is assisting, not replacing.
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — a practical vocabulary for the trust, validity, and accountability questions that decide whether an AI reviewer helps or hurts.
- [Stanford HAI — AI Index Report](https://aiindex.stanford.edu/report/) — a sober, data-grounded read on where LLM capabilities and limitations actually stand, useful for calibrating how much to trust an automated reviewer.
- [OWASP Top 10 for Large Language Model Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — the risks that come with putting an LLM in your toolchain, including data exposure and over-reliance, directly relevant to sending code to a review model.
- [My AI Security series](/blog/posts/ai-security-01-the-ai-security-landscape.html) — the threat-model lens for LLM-in-the-loop systems, including data privacy and excessive agency, which is the framing you want before pointing an external model at a private repo.
- [My AI Engineering in Go series](/blog/posts/ai-eng-go-01-what-is-ai-engineering.html) — how LLMs actually work under the hood, which is the fastest way to build the intuition for *why* a reviewer bot hallucinates and where its confidence is unearned.
