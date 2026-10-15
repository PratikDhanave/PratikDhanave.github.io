# Verification and Trust — How You Know the Agent's Code Is Right

*A coding agent can produce a confident, plausible change that's subtly wrong — and the whole value collapses if you can't tell. Verification is how you know the agent's code actually works, and trust is what you build (or lose) based on it. Because code is verifiable, coding agents can check much of their own work — but the human reviewer remains the final, accountable arbiter. This post is about verifying agent-written code and the trust that makes coding agents usable.*

Posts 2–5 built how the agent *produces* changes. This post is about knowing those changes are *correct* — the verification that both drives the agent's loop (post 2) and determines whether you can trust the result. It's where code's verifiability (post 1) pays off most, and where the engineer-as-reviewer role (post 1) lives.

## Verification is what makes coding agents work

Recall post 1's key point: code is special because it's *verifiable* — and verification is therefore central to coding agents in two ways:

- **It drives the agent's self-correction.** The agent verifies its own work as it goes (run the code, run the tests, check the output — post 2's loop), and uses failures to fix itself. This is how the agent *converges* to working code rather than producing a hopeful one-shot guess. The agent's ability to verify-and-fix is the engine of its reliability, so strong verification (good tests) makes the agent *much* better — it can tell when it's wrong and keep going until it's right.
- **It's how *you* know to trust the result.** When the agent says "done," verification (do the tests pass? does it work? is the change correct?) is how you — and the agent — *know* it's actually done. Without verification, "the agent finished" is just a claim; with it, it's a checkable fact. Verification turns agent output from "plausible" into "confirmed."

This is the deep reason coding agents are more reliable than agents in fuzzy domains: *they can verify*. A coding agent with a good test suite operates in a loop with an objective success signal, which is why it can autonomously reach correct solutions. The corollary is crucial: **a coding agent is only as reliable as its verification** — where tests are strong, it's trustworthy; where verification is weak or absent, it can confidently produce wrong code and neither it nor you will know. Verification is the foundation of the whole enterprise.

## The verification toolkit

Agent-written code is verified through a layered toolkit, from automatic to human:

- **Tests (the primary signal).** Running the test suite is the agent's main verification — objective, automatic, and rich (which tests fail, why). The agent runs tests continuously (post 2) and after a change to confirm it works and didn't break anything. Strong test coverage is the single biggest enabler of reliable coding agents, because it gives dense, trustworthy feedback. Weak coverage leaves the agent (and you) guessing.
- **The agent writing tests.** A powerful pattern: the agent *writes tests* for its change (or you ask it to), creating the verification signal where it was missing. Agent-written tests both improve the agent's own loop (more to verify against) and improve the codebase — though they carry a caveat (the agent could write tests that pass its own possibly-wrong code, so tests still need review).
- **Running and type-checking.** Beyond tests: does it compile/run without errors? Do type checkers and linters pass? These catch whole classes of errors cheaply and automatically — fast verification layers that complement tests.
- **Diff review.** The agent (and you) review the *diff* of what changed (post 4's version control) — a focused way to see exactly what the agent did, catching unintended changes, scope creep, or wrong approaches that pass tests but aren't right.
- **Human review (the final arbiter).** The engineer reviews the change for correctness, design, convention-adherence, and the things tests don't catch (is this the *right* solution? does it fit the architecture? is it maintainable?). Human review is the final, accountable verification — because the human owns the code, not the agent.

The pattern: *layered verification*, with cheap automatic checks (compile, lint, type-check, tests) catching most issues and freeing human review to focus on judgment (correctness of approach, design, the subtle things). The automatic layers make the human review *efficient* (less to check manually) but don't replace it.

## Trust: earned through verification, and the human stays accountable

The practical heart of using coding agents is *trust*, and verification is how it's calibrated:

- **Trust is earned through verification, not granted.** You trust an agent's change *because* you verified it (tests pass, you reviewed the diff) — not because the agent sounded confident (it always does). Calibrating trust to verification strength is the key skill: trust more where verification is strong (good tests you've checked), trust less and review harder where it's weak. An agent change with no verification deserves no trust regardless of how plausible it looks.
- **The human is the accountable reviewer.** This is the engineer's central role with coding agents (post 1): *verify and own* the agent's work. The agent does the work; the human is accountable for whether it's correct and gets merged. "The agent wrote it" is never an excuse for a bug — the human who accepted it owns it. This keeps responsibility where it belongs and is why human review is non-negotiable for consequential code.
- **Review scales with stakes.** Trivial, well-tested, reversible changes need light review; consequential, poorly-tested, or irreversible changes need heavy review. Match review effort to risk (the autonomy-by-stakes principle) — don't rubber-stamp a critical change because the agent seemed confident, and don't laboriously re-verify a trivial well-tested one.
- **Beware the confident-but-wrong trap.** The specific danger: an agent produces a change that's plausible, passes weak tests, and is *subtly wrong* — and an under-verifying human merges it on the agent's confidence. This is the main way coding agents cause harm, and it's defended against by *verification discipline* (don't trust without checking) and *strong tests* (so "passes tests" actually means something). The failure mode is human over-trust meeting weak verification.

The through-line: **verification is the foundation of coding agents** — it drives the agent's self-correction (converging to working code via the loop, post 2) *and* it's how you know to trust the result, which is why coding agents (verifiable) are more reliable than fuzzy-domain agents. A coding agent is **only as reliable as its verification**: strong where tests are strong, dangerous where they're weak. Verify through a **layered toolkit** — tests (the primary signal; agent-written tests extend it, with a review caveat), compile/type-check/lint, diff review, and **human review as the final accountable arbiter** — with cheap automatic layers making human judgment efficient, not replacing it. And **trust is earned through verification, not granted**: calibrate trust to verification strength, keep the **human accountable** for the agent's code ("the agent wrote it" excuses no bug), scale review to stakes, and guard against the **confident-but-wrong trap** (over-trust meeting weak verification — the main way coding agents cause harm).

## Key takeaways

- **Verification is central** in two ways: it **drives the agent's self-correction** (run code/tests, use failures to fix — how the agent converges to working code via the loop, post 2; strong tests make the agent *much* better) and it's **how you know to trust the result** (tests pass + reviewed = confirmed, not merely plausible).
- This is why coding agents are **more reliable than fuzzy-domain agents** — *they can verify* — with the crucial corollary: **a coding agent is only as reliable as its verification** (trustworthy where tests are strong; it can confidently produce wrong code where verification is weak/absent, and neither it nor you will know).
- Verify through a **layered toolkit**: **tests** (the primary, objective, automatic, rich signal — strong coverage is the single biggest enabler; weak coverage = guessing), **agent-written tests** (create the signal where missing — but review them, since the agent could test its own wrong code), **compile/type-check/lint** (cheap automatic error-catching), **diff review** (see exactly what changed — catch scope creep / wrong approaches that pass tests), and **human review** (the final, accountable arbiter for correctness, design, convention, maintainability).
- The pattern is **cheap automatic checks catch most issues, freeing human review for judgment** — the automatic layers make human review *efficient*, not optional.
- **Trust is earned through verification, not granted** (the agent always sounds confident — calibrate trust to verification strength); the **human is the accountable reviewer** ("the agent wrote it" excuses no bug — they own merged code); **review scales with stakes**; and the main danger is the **confident-but-wrong trap** (a plausible, weakly-tested, subtly-wrong change merged on the agent's confidence — defended by verification discipline + strong tests).

## Further reading

- [Software testing — the primary verification signal for agent code](https://en.wikipedia.org/wiki/Software_testing)
- [Code review — the human, accountable final verification](https://en.wikipedia.org/wiki/Code_review)
