# Giving Feedback That Lands

*How to write code-review comments that improve the code and the relationship at the same time — commenting on the code not the coder, labeling severity so the author knows what blocks, asking instead of decreeing, teaching the why, and knowing when a thread belongs on a call.*

---

A code review is two documents at once. One is technical: does this change do what it claims, safely, and in a way the next reader can follow? The other is social: it is a written conversation between two people who will keep working together tomorrow. Most guidance on reviews obsesses over the first and quietly assumes the second takes care of itself. It doesn't. A review that finds every bug but leaves the author feeling attacked has failed at half its job — and the author who feels attacked writes worse code next time, not better.

The good news is that the skills overlap almost completely. Comments that are kind, specific, and clear about what's required happen to also be the comments that actually get the code fixed. This post is about how to write those comments. Every example below is a synthetic pull request I made up to illustrate a point — no real reviews, no real names — but the patterns are the ones I keep coming back to.

---

## Comment on the code, not the coder

The single highest-leverage change you can make to your review comments is grammatical: talk about the code, not the person who wrote it. "You didn't handle the nil case" and "this function doesn't handle the nil case" point at the exact same line, but they land in completely different places. The first is a verdict on a person. The second is an observation about an artifact — and an artifact can be changed without anyone losing face.

```text
Before:  You never close this file, so you're leaking a handle.
After:   This file handle is opened but never closed — looks like a
         leak on the early-return path. Adding a defer right after
         the open would cover every exit.
```

The rewrite drops "you" twice and gains a concrete fix. Notice it isn't softer in substance — it still says there's a leak — it's just aimed at the code. The author reading it doesn't have to defend themselves before they can engage with the problem.

**The gotcha:** "you" creeps in most when you're annoyed, which is exactly when it does the most damage. If a comment starts with "you keep..." or "you always...", stop and rewrite it around the code. The pattern you're frustrated by is real; naming it as a personal failing just guarantees the author reads the rest of your review defensively.

---

## Be specific and actionable

Vague praise is harmless. Vague criticism is a trap: it tells the author something is wrong without telling them what or how to fix it, so they either guess (and guess wrong) or come back to ask, burning a full round-trip. A useful comment answers three questions: **what** is the issue, **why** it matters, and — when you can — **how** to address it.

```text
Before:  This is confusing.
After:   The name `data` here makes it hard to tell what's in the map —
         it's actually user IDs to session counts. Renaming it
         `sessionsByUser` would let the loop below read on its own.
```

"This is confusing" makes the author defensive and gives them nothing to act on. The rewrite names the confusion (an opaque variable), explains the cost (the loop stops being self-documenting), and hands over a concrete fix. The author can accept it in ten seconds or push back with real information — either way the thread resolves fast.

You won't always know the fix, and that's fine. "This retry loop has no upper bound — is that intentional?" is specific about the *what* even though it offers no *how*. What you're avoiding is the empty gesture: a comment that registers displeasure without giving the author anywhere to go.

---

## Label severity so the author knows what blocks

Here is the failure mode that silently wrecks more pull requests than any bug: the author can't tell your must-fix from your idle musing. You leave twelve comments — one is a real correctness problem, eleven are style preferences — and because they all look alike, the author treats all twelve as change requests. Now a one-line fix is blocked behind eleven negotiations, and the PR sits for three days.

The fix is a convention that's been floating around the industry for years, most cleanly packaged by the **Conventional Comments** effort (conventionalcomments.org): prefix each comment with a label that states what *kind* of comment it is. You don't need their exact vocabulary — the value is in adopting *some* shared prefix set and using it consistently. The ones I reach for:

| Label | Means | Blocks merge? |
|---|---|---|
| `blocking:` | Must change before this merges — a bug, a security hole, a broken contract | Yes |
| `suggestion:` | I think this is better; I'd like you to consider it | Author's call |
| `nit:` | Trivial polish — spelling, spacing, a nicer name | No |
| `question:` | I don't understand something and might be missing context | Only if the answer reveals a problem |
| `praise:` | This is good and I want to say so | No |

With labels in place, the same twelve comments become legible at a glance: one `blocking:`, three `suggestion:`, eight `nit:`. The author fixes the blocker, weighs the suggestions, and sweeps the nits or defers them — no negotiation, no guessing. Be generous with `nit:` and, when it's genuinely optional, add "non-blocking" out loud. It costs you three words and buys the author permission to say no without wondering whether they've picked a fight.

**The gotcha:** an unlabeled nit is indistinguishable from a demand. If you write "prefer `const` here" with no prefix, the author has no way to know it's optional, so they treat it as required — and every trivial preference you drop becomes another thing blocking the merge. The label isn't bureaucracy; it's the difference between a PR that merges today and one that dies of a thousand equal-weight comments.

---

## Ask questions when you might be missing context

You are reading a diff. The author has the whole design in their head, the ticket, the Slack thread where the approach was decided, and three constraints you've never heard of. When something looks wrong, there's a real chance the wrongness is in your understanding, not their code. A question respects that; a decree doesn't.

```text
Before:  This is wrong — you should be using a mutex here.
After:   question: Is this map accessed from more than one goroutine?
         If the handler and the background sweep both touch it, I
         think we'd need a mutex — but I might be missing how it's
         scoped.
```

If you were right, the question gets you there just as fast and the author fixes it without having been told they were "wrong." If you were missing something — say the map is confined to a single goroutine — the question saves you from confidently demanding a change that would've been pointless. Asking costs nothing when you're right and saves you from being wrong in writing.

There's a limit: don't sandbag a genuine bug as a coy question when you're certain. "Is it intentional that this deletes the user's data on every login?" is passive-aggressive if you *know* it's a bug. Reserve questions for real uncertainty; when you're sure, use `blocking:` and say plainly what's broken and why.

---

## Explain the why — a review is also teaching

"This is wrong" teaches nothing. The author changes the line to make you happy, learns nothing transferable, and writes the same thing again next month. A comment that explains *why* turns a single fix into a lesson the author carries forward — and it invites agreement instead of compliance, because now they can see the reasoning and either accept it or point out what you missed.

```text
Before:  Don't build the query with string concatenation.
After:   blocking: Building the query by concatenating `username` in
         lets a crafted username rewrite the SQL — classic injection.
         A parameterized query ($1 placeholder) keeps the input as
         data so it can't change the statement. Short write-up here:
         https://owasp.org/www-community/attacks/SQL_Injection
```

The rewrite explains the mechanism (input becomes executable SQL), gives the fix (parameterize), and links a canonical reference so the author can go deeper without you retyping the OWASP page. Linking to a shared standard also depersonalizes the ask — it's no longer *your* preference versus *theirs*, it's both of you pointing at an external source of truth.

**The gotcha:** "this is wrong" with no reasoning doesn't just fail to teach — it actively invites defensiveness, because from the author's chair it's indistinguishable from "I don't like it." Every unexplained decree is a small dare to push back. Explain the why or ask a real question; either gives the author something to reason with instead of something to resist.

---

## Praise the good parts

Reviews have a structural negativity bias: the tool exists to catch problems, so every comment is, by default, a complaint. If the only time you comment is to flag something, you train the author to dread your name in the reviewer field. A `praise:` comment costs you one line and changes the whole texture of the review.

```text
praise: This table-driven test is really clean — adding the next
        edge case is going to be a one-line diff. Nice.
```

Praise isn't flattery and it isn't padding. Point at something specific and real: a clean abstraction, a test that will age well, a tricky edge case handled without fuss. Specific praise also does quiet technical work — it tells the author which patterns you want more of, which is feedback just as much as a nit is. And it earns you credibility for the harder comments: an author who's seen you notice the good parts trusts that your `blocking:` is about the code, not about you needing to find fault.

---

## Pick your battles

You can find something to comment on in every line of every PR if you try. Don't. A review with forty comments doesn't read as forty times as thorough — it reads as noise, and the author can't tell which two comments actually matter. Worse, it signals that nothing will ever be good enough, which is how you teach people to stop asking you to review.

Before you submit, triage. What are the two or three things that genuinely need to change — the correctness bugs, the security issues, the choices that'll hurt in six months? Lead with those, unmistakably labeled `blocking:`. Everything else is optional, and you should say so: batch the small stuff as nits, and if there's a larger refactor you'd like but the PR is fine without it, name it as a follow-up rather than a gate.

**The gotcha:** forty equally-weighted comments and zero comments do the same thing — they leave the author with no signal about what matters. Volume isn't rigor. If a change has real problems, three sharp, prioritized comments move it further than forty scattered ones, because the author can actually see where to look.

---

## Know when to stop typing

Written async review is wonderful for a first pass and terrible for a debate. When a single thread has gone back and forth three times — you explain, they push back, you clarify, they still don't see it — that's not a comment thread anymore, it's a conversation trying to happen in the wrong medium. Each round takes hours of latency and loses a little more tone. Take it to a call, a pairing session, or a desk visit.

```text
(after the third reply on the same thread)

suggestion: I think we're talking past each other on this one and
a thread isn't helping. Got 15 minutes to hop on a call? Whatever
we land on, I'll summarize back here so the decision is recorded.
```

Two things make this work. First, moving to synchronous isn't a defeat — it's using the right tool; some disagreements need tone of voice and a shared screen to resolve in minutes what a thread can't in a day. Second, **write the outcome back into the PR**. The next person to read the review — including future you — needs the decision and the reasoning, and a call leaves no record unless you make one.

**The gotcha:** the third round-trip on one thread is the signal. Past that point each reply is more likely to harden positions than resolve them, because written text keeps stripping the warmth that would let either of you concede gracefully. When you notice the third lap, stop typing and start talking.

---

## Tone is lost in text — err warm

Everything above sits on top of one hard fact about written feedback: the reader supplies the tone, and a stressed reader supplies a hostile one. Spoken across a desk, a one-word "why?" is curious. Typed into a review at 6pm, it reads as an interrogation. You didn't mean it that way — but you're not in the room to prove it, so the words carry the whole message and the words are bare.

```text
Before:  Why?
After:   question: Curious about the choice here — what made a linked
         list better than a slice for this? Might be a constraint I'm
         not seeing.
```

The rewrite says the same thing — *justify this* — but a word of warmth ("curious"), the reasoning behind the ask, and an explicit admission that you might be wrong turn an accusation into an inquiry. It's three seconds of extra typing to remove a whole category of misread.

**The gotcha:** because text loses tone, terseness reads as hostility even when you feel neutral. The reviewer who thinks "I'm just being efficient" is often the one whose comments land as cold. The fix isn't gushing — it's a small deliberate surplus of warmth to offset the medium's built-in chill. Assume your comment will be read on the author's worst day, and write the version that survives that reading.

---

## Key takeaways

- **Aim at the code, not the coder.** "This function" instead of "you" points at the same line without putting a person on trial — and stays just as direct about the problem.
- **Say what, why, and how.** A comment that names the issue, explains the cost, and suggests a fix resolves in one round-trip; a vague one burns three.
- **Label severity, and be generous with "nit, non-blocking."** A shared prefix set (`blocking:` / `suggestion:` / `nit:` / `question:` / `praise:`) lets the author tell your must-fix from your preference at a glance. Unlabeled comments all read as demands.
- **Ask when you might be missing context.** A question costs nothing when you're right and saves you from a confidently wrong decree when you're not.
- **Explain the why and praise the good parts.** Reasoning turns a fix into a lesson and invites agreement; specific praise tells the author which patterns to repeat and earns trust for the hard comments.
- **Prioritize, and go synchronous on the third lap.** Three sharp comments beat forty scattered ones; three round-trips on one thread means it's time for a call — then write the outcome back into the PR.
- **Err warm, because text strips tone.** A terse "why?" reads as hostile; a word of warmth and the reasoning behind the ask cost seconds and prevent a misread.

Kind, specific, and clear about what's required — those three aren't in tension, they reinforce each other. The comment that respects the author is usually the same comment that gets the code fixed, because it gives them something to act on instead of something to resist. Write reviews for the person who has to read them on their worst day, and you'll write better ones for everyone.

---

## Further reading

- [Conventional Comments](https://conventionalcomments.org/) — the label-prefix convention (`nit:`, `suggestion:`, `question:`, and friends) that makes comment severity legible at a glance.
- [Google Engineering Practices: How to write code review comments](https://google.github.io/eng-practices/review/reviewer/comments.html) — a concise, battle-tested guide to courtesy, explaining reasoning, and balancing directness with the author's autonomy.
- [Google Engineering Practices: The standard of code review](https://google.github.io/eng-practices/review/reviewer/standard.html) — the companion piece on what a review is actually for, including mentoring and picking your battles.
- [Radical Candor](https://www.radicalcandor.com/our-approach/) — Kim Scott's framework for feedback that is simultaneously caring and direct, which is exactly the balance a good review comment strikes.
