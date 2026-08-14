# Discovery and Problem Framing

*The problem a customer first describes is almost never the problem worth solving — an FDE's first job is to dig until the real one surfaces.*

A customer says "we need a dashboard." An FDE who builds a dashboard has done their job badly. The dashboard is a *guess at a solution* to a problem the customer hasn't articulated — maybe the real issue is that three teams can't agree on a number, or that a report takes four days to assemble, or that a decision keeps getting made too late. Discovery is the discipline of getting from the stated request to the actual problem, and it is where forward deployed work most often succeeds or fails before a line of code is written.

## Why the stated problem is usually wrong

People describe problems in terms of the solutions they already know. A user who has only ever seen spreadsheets asks for a better spreadsheet. A manager frustrated by slow reports asks for faster reports, when the real cost is the decision the slow report delays. This isn't dishonesty — it's the natural human move of jumping to a familiar answer. The FDE's value is refusing to accept the first answer and instead asking *why* until the underlying need is visible.

**The gotcha:** building exactly what the customer asked for feels safe and cooperative, but if you built the wrong thing, "but you asked for this" is cold comfort — the solution won't get used and the engagement stalls. Your job is to deliver the outcome they need, not the artifact they named.

## The tools of discovery

Discovery is mostly asking good questions and watching real work happen.

- **Ask "why" and "what happens then."** "Why do you need that report?" → "To decide reorder quantities." → "What happens if it's wrong?" → "We overstock and eat the holding cost." Now you know the real target is inventory decisions, not a report.
- **Watch people do the actual job.** What they *say* they do and what they *actually* do diverge constantly. Sit with the analyst who exports to Excel and re-keys numbers at 6pm — the workaround *is* the requirement.
- **Follow the pain and the workarounds.** The manual step someone dreads, the shared spreadsheet everyone secretly depends on, the "don't touch that, only Priya knows how it works" — these mark where value is.
- **Find the decision.** Most enterprise problems reduce to a decision made too slowly, with too little confidence, or by too few people. Name the decision and you've found the problem.

## The jobs-to-be-done lens

A useful reframing: people don't want your software, they "hire" it to make progress on a job. "I need a dashboard" becomes "when the quarter is closing, I need to trust the revenue number without three days of reconciliation, so I can commit to the board." That sentence tells you the trigger, the outcome, and the constraint — and it rules out a hundred features that don't serve it. Framing the problem this way keeps everyone honest about what "done" means.

```text
STATED:  "We need a dashboard."
   │  ask why / watch the work / find the decision
   ▼
REAL:    "At quarter close, finance spends 3 days reconciling revenue
          across 3 systems before they trust the number to report."
JOB:     Trustworthy revenue figure, fast, at close.
```

## Map the stakeholders

The person who asked for the work is rarely the only one who matters. There's an **economic buyer** (who pays and cares about ROI), the **end users** (who live with what you build — and can quietly kill it by not using it), a **champion** (your inside ally who wants you to succeed), and often a **skeptic or blocker** (the person whose toes you're stepping on). Discovery includes learning this map, because a technically perfect solution the end users resent, or that threatens the wrong person, will not survive contact with the org.

**The gotcha:** the loudest voice in the kickoff meeting is often not the person whose adoption determines success. Talk to the people who'll actually use the thing daily — their quiet "this doesn't fit how I work" outweighs the executive's enthusiasm.

## Constraints are part of the problem

A problem definition isn't complete without its constraints, and in a customer environment they're brutal and non-negotiable: the data lives in a system you can't change, security forbids the tool you'd reach for, a regulation dictates how records are handled, procurement won't approve a new vendor, the go-live is tied to a fiscal date. Surfacing these early prevents the classic FDE heartbreak — a working prototype that can never be deployed because it violates a constraint nobody mentioned. Ask explicitly: *what can't change? what can't we touch? what would make this impossible to roll out?*

## Framing and confirming

Once you believe you understand the problem, write it down in one or two plain sentences — the problem, the job, the top constraints, and what success looks like — and reflect it back to the customer. This does three things: it catches your own misunderstanding cheaply (before you've built anything), it makes the customer feel heard, and it creates a shared definition of "done" you can point to later when scope drifts. A short written problem frame, agreed by the champion and ideally the buyer, is the single highest-leverage artifact an FDE produces in week one.

**The gotcha:** skipping the written, confirmed problem frame means every stakeholder holds a slightly different idea of what you're building — and you'll discover the mismatch at the demo, the worst possible moment. Five minutes writing it down and reading it back saves weeks.

## Discovery never fully stops

Framing the problem up front is essential, but the understanding keeps deepening as you build — a prototype (post 3) is itself a discovery tool, because showing someone something concrete surfaces reactions that no interview could. Hold your problem frame firmly enough to make progress and loosely enough to update it when the work teaches you something new.

## Key takeaways

- The **stated problem is a guess at a solution** — dig with "why" and "what happens then" until the real need surfaces.
- **Watch real work** and follow the workarounds; the dreaded manual step *is* the requirement.
- Most enterprise problems reduce to a **decision** made too slowly or with too little confidence — name it.
- Use a **jobs-to-be-done** frame (trigger + outcome + constraint) to define what "done" means and rule out noise.
- Map the **stakeholders** — buyer, users, champion, skeptic — because adoption, not correctness, decides success.
- Surface **hard constraints** (data, security, regulation, procurement) early or risk a prototype that can't ship.
- Write a **one-paragraph problem frame and confirm it** — the highest-leverage week-one artifact.

## Further reading

- [Steve Blank — Customer Development / "get out of the building"](https://steveblank.com/) — the foundational discipline of discovery.
- [Clayton Christensen — Jobs to Be Done](https://www.christenseninstitute.org/jobs-to-be-done/) — framing needs as jobs, not features.
- [The Mom Test (Rob Fitzpatrick)](https://www.momtestbook.com/) — how to ask questions that get honest answers about real problems.
