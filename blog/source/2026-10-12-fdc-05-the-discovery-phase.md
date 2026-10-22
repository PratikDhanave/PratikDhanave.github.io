# The Discovery Phase — Learning a Client's World Before You Build

*The temptation at the start of an engagement is to start building, because building is what you're good at. Almost every engagement I've seen go wrong went wrong here, by skipping the quiet work of understanding first. This is a defense of discovery.*

There's a particular kind of eagerness that good engineers bring to a new engagement. You can see the shape of the solution already; your hands itch to start. And the client, who is paying, is often just as eager to see something appear. So discovery — the unglamorous work of learning the client's world before writing much of anything — is the easiest phase to shortchange and the most expensive one to skip.

I want to make the case for taking it seriously, because almost everything good in an engagement traces back to having understood before building, and almost everything painful traces back to not.

## What discovery is actually for

Discovery is not requirements-gathering. Requirements-gathering assumes the client knows what they need and your job is to write it down. Discovery assumes the opposite: that the real problem is partly hidden, even from the people who have it, and your job is to find it with them.

Concretely, I'm trying to learn three things that a scope on paper never captures:

- **How the work really happens.** Not the official process, but the actual one — the spreadsheet everyone secretly relies on, the step that's always done by one person who just knows, the exceptions that are really the rule. Systems fail in production because they're built for the official process and deployed into the real one.
- **What the data is actually like.** Demos run on clean data. Reality is missing fields, inconsistent formats, three systems of record that disagree, and history nobody can explain. The gap between the data you were shown and the data you'll run on is often the entire difficulty of the engagement.
- **What "good enough to trust" means here.** The bar for a system people will actually rely on is set by this team, this domain, this risk tolerance — not by a benchmark. Discovery is where you learn how good is good enough, which quietly determines everything downstream.

## Discovery is also how you earn standing

There's a relational dimension that's easy to miss. The weeks you spend genuinely trying to understand a client's world are also the weeks you earn the right to have opinions about it. A recommendation from someone who has clearly done the homework lands completely differently from the same recommendation offered on day one. Understanding buys you credibility you can't get any other way.

It also protects the client from one of the most common failures of outside help: the expert who applies a template. When you've really looked, you stop pattern-matching their problem to the last one you solved and start seeing what's actually different about theirs. Clients can feel the difference between being understood and being processed, and it is the foundation of trust.

## How to keep discovery from becoming a stall

The honest risk is the opposite failure: discovery that never ends, analysis that becomes avoidance. A few things keep it bounded:

- **Time-box it explicitly.** Discovery is a defined phase with an end, not an open-ended mood. A week or two, agreed in advance, usually reveals the important things; the rest you'll learn by building.
- **Produce something at the end.** Discovery should output a concrete artifact — a sharpened [scope](/blog/posts/fdc-03-scoping-the-first-engagement.html), a map of the real workflow, a clear statement of the trust bar. If it produces only a vaguer sense of the problem, it wasn't discovery.
- **Build a small probe while you learn.** The best discovery often includes touching the real data with a throwaway prototype. You learn more about a dataset in an hour of actually querying it than a week of being told about it. Understanding and building aren't strictly sequential; they inform each other.

## The quiet confidence it produces

The payoff of real discovery is a kind of calm. When you finally start building in earnest, you're not guessing. You know where the hard parts are, what the data will do to you, and what the result has to achieve to be trusted. The build goes faster precisely because you were patient first.

I've never regretted spending more time understanding. I've often regretted spending less. In the next essay I'll stay in those first weeks but shift to the human side of them: how trust actually gets built early, and why it's the real deliverable of the beginning.
