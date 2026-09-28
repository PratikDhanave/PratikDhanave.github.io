# Integrating AI into Real Workflows

*A technically excellent AI system that nobody uses has delivered zero value. The last mile of an AI deployment is not the model — it's fitting the system into how real people actually do their jobs, designing an interface that handles uncertainty honestly, and managing the human change of introducing AI into someone's work. This is where deployments succeed or quietly fail, and where the forward deployed engineer's non-technical skills matter most.*

By now the system is grounded (post 4) and measured (post 5). But a working model is not a working deployment. Value is realized only when the system is used, by real people, in real work — and getting there is a distinct discipline: workflow integration, AI-specific UX, and change management. This post is about the last mile, which is often the hardest mile precisely because it's about humans, not models.

## Value happens in the workflow, not the model

An AI system creates value only at the point where it changes what a person does — faster, better, or with less toil. That means the deployment's success depends less on the model's raw quality than on *where and how* it sits in the actual workflow:
- **Meet people where they work.** An AI capability bolted onto a separate tool that users must remember to visit will be ignored. Embedded into the system they already use, at the exact moment they need it, it gets adopted. Integration into the existing workflow — not a shiny standalone app — is usually what drives usage.
- **Fit the real process, not the idealized one.** The workflow on the whiteboard and the workflow people actually follow differ. The AI FDE has to observe the real process (the general FDE discovery skill) and slot the AI into it, including its exceptions and workarounds.
- **Reduce friction to near zero.** Every extra click, copy-paste, or context-switch between the user and the AI's value bleeds adoption. The best integrations make the AI's output appear where the work already happens.

The reframe: you're not deploying a model, you're changing a workflow. The model is one component; the workflow redesign around it is the deployment.

## Designing for uncertainty: the UX of imperfect AI

AI's probabilistic nature (post 5) isn't just an engineering problem — it's a UX problem, because the interface must help users work productively with a system that is sometimes wrong. Good AI UX is largely about handling uncertainty honestly:
- **Make the human the decider for anything consequential.** The pattern that makes AI deployable is usually **human-in-the-loop**: the AI proposes, drafts, or recommends; the human reviews and decides. This captures most of the value (the tedious cognitive work is done) while bounding the risk (a person catches the errors). Designing the right division of labor between AI and human is the core UX decision.
- **Show your work.** Surface citations and sources (post 4) so users can verify, and convey confidence so they know when to look harder. An answer with its sources is checkable; an answer without is a leap of faith users won't take for important decisions.
- **Make correction easy and capture it.** Users will edit and override AI output — make that frictionless, and capture the corrections as both an immediate fix and future eval/training data (post 5). A system that learns from being corrected earns trust; one that makes correction painful gets abandoned.
- **Fail visibly and gracefully.** When the system is unsure or out of scope, it should say so (abstention) rather than fake an answer. Users forgive a system that admits uncertainty far more than one that's confidently wrong — the honest failure preserves trust, the confident error destroys it.

The goal is **calibrated reliance**: users trusting the AI exactly as much as it deserves — leaning on it where it's strong, checking it where it's weak. An interface that encourages blind trust is dangerous; one that encourages blanket distrust is useless. Calibrated reliance, designed into the UX, is what makes an imperfect system genuinely valuable.

## Levels of autonomy

Where a deployment sits on the autonomy spectrum is a deliberate design choice, and it usually *moves over time*:
- **Assistive** — AI surfaces information or suggestions; the human does the work. Lowest risk, fastest to deploy.
- **Augmented (human-in-the-loop)** — AI does the work and drafts the output; the human reviews and approves. The sweet spot for most first deployments: high value, bounded risk.
- **Autonomous (human-on-the-loop or out)** — AI acts without per-case review, with humans monitoring in aggregate. Highest value and highest bar; justified only once evaluation and trust (post 5) support it.

The AI FDE typically **starts lower and earns the way up.** Begin assistive or augmented, prove reliability on real work, and expand autonomy as trust and measured performance justify it. Pushing for full autonomy before it's earned is how deployments blow up publicly and lose the customer; a system that starts as a trusted assistant can grow into an automation, but not the reverse.

## Change management: the human side

Introducing AI into people's work is a human change, and ignoring that is a leading cause of deployments that are technically fine but fail in practice:
- **Address the fear honestly.** People whose work the AI touches often fear being replaced or judged. Denying it breeds resistance; acknowledging it and framing the AI as removing toil (not people) — and involving them in shaping it — turns potential blockers into allies. The users who feel threatened can quietly kill a deployment; the ones who feel empowered champion it.
- **Involve the actual users early.** The people doing the work know its reality and its edge cases, and they're the ones who must adopt the system. Co-designing with them produces both a better fit and the ownership that drives adoption.
- **Train and support, don't just deploy.** Users need to learn what the AI is good and bad at (calibrated reliance again), how to verify and correct it, and when to escalate. A rollout without this produces either blind trust or abandonment.
- **Find and equip champions.** As in any FDE engagement, a respected user who adopts and advocates for the system pulls others along far more effectively than any top-down mandate.

The AI FDE's job here is as much sociotechnical as technical: you're not just installing software, you're helping a team change how they work and trust a new kind of tool. The engineers who succeed treat that human change as a first-class part of the deployment, not an afterthought.

The takeaway: the last mile of an AI deployment is fitting the system into how real people actually work, and it's where deployments succeed or quietly fail. Value happens in the workflow, not the model — so embed the AI where work already happens, with near-zero friction, into the real (not idealized) process. Design the UX for uncertainty honestly (human-in-the-loop for consequential decisions, citations, easy correction, graceful failure) to produce calibrated reliance. Choose a level of autonomy deliberately and earn your way up from assistive to autonomous. And manage the human change — address fear, involve users, train, and find champions — because introducing AI into someone's job is a sociotechnical change, not just a software install.

## Key takeaways

- **Value happens in the workflow, not the model**: embed the AI where people already work, at the moment they need it, with near-zero friction, fitting the **real** process (exceptions and all) — a great model in a separate tool nobody visits delivers zero value. You're changing a workflow, not deploying a model.
- Design the **UX for uncertainty honestly**: **human-in-the-loop** for consequential decisions (AI proposes, human decides — most of the value, bounded risk), **show sources/confidence**, make **correction frictionless** (and capture it as eval data), and **fail visibly** (abstain rather than confabulate).
- Aim for **calibrated reliance** — users trusting the AI exactly as much as it deserves (lean where strong, check where weak) — not blind trust (dangerous) or blanket distrust (useless).
- Autonomy is a **spectrum** (assistive → augmented/human-in-the-loop → autonomous); **start lower and earn the way up** as evaluation and trust justify it — a trusted assistant can grow into an automation, not the reverse.
- **Change management is first-class**: address the human **fear** honestly (AI removes toil, not people), **involve actual users** early (better fit + ownership), **train and support** (for calibrated reliance), and **find champions** — introducing AI is a sociotechnical change, not just a software install.

## Further reading

- [Human-in-the-loop — keeping people in the decision for consequential AI](https://en.wikipedia.org/wiki/Human-in-the-loop)
- [Change management — the human side of introducing new systems](https://en.wikipedia.org/wiki/Change_management)
