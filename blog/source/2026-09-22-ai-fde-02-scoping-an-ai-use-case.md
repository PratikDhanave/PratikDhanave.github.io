# Scoping an AI Use Case

*The most important decision an AI forward deployed engineer makes happens before any code: which problem to point the model at. Choose a problem AI is genuinely suited for, with real value and a clear way to measure it, and the engagement can succeed. Choose AI theater — impressive-sounding but ill-fit — and no amount of engineering saves it. Scoping is where AI deployments are won or lost.*

The general FDE discipline of discovery and problem framing (covered in the [foundational series](/blog/series/forward-deployed-engineering/)) still applies: understand the real problem before building. But AI adds a specific, decisive question on top: *is this a problem AI should solve at all, and if so, which slice of it first?* Getting that wrong is the most common way AI engagements fail, so this post is about scoping specifically for AI.

## The trap: AI theater

The AI era produces enormous pressure to "use AI" — executives want it, competitors claim it, budgets demand it. This pressure pushes teams toward **AI theater**: deploying AI where it looks impressive but doesn't actually fit, producing a flashy pilot that quietly dies because it never did a real job. The AI FDE's first duty is to resist this and find a problem where AI genuinely earns its place.

The discipline is to evaluate a candidate use case on two axes, honestly:
- **Is AI a good fit for this problem?** (feasibility / suitability)
- **Does solving it create real, measurable value?** (value)

Only problems that score well on *both* are worth deploying. High-value but poor-fit is a trap that wastes months; good-fit but low-value is a toy that no one funds. You want high-value and good-fit — and among those, the one that proves value *fastest*.

## When AI is a good fit

AI (especially LLMs) is genuinely well-suited to a recognizable class of problems. Look for these signatures:
- **Unstructured language or data in the loop** — the task involves reading, summarizing, extracting from, classifying, or generating text (documents, tickets, emails, transcripts, code). This is where LLMs shine and traditional software struggles.
- **Fuzzy, judgment-like tasks with tolerance for imperfection** — the task doesn't demand a single provably-correct answer, and a good-enough answer that a human can verify is valuable. AI fits tasks where approximate is useful, not tasks that require exactness.
- **A human is currently doing tedious cognitive work at volume** — reading hundreds of documents, drafting repetitive responses, triaging, first-pass analysis. AI excels at augmenting or accelerating this, especially with a human checking the output.
- **The knowledge needed exists in retrievable data** — the task can be grounded in the customer's documents/data (post 4), so the model reasons over real facts rather than hallucinating.

## When AI is a poor fit

Equally important — and where an honest FDE earns trust — is naming when *not* to use AI:
- **Exactness is mandatory and errors are costly/unrecoverable** — anything where a wrong answer causes real harm and can't be caught by a human. Probabilistic systems are the wrong tool for tasks that demand determinism and where you can't tolerate the failure mode.
- **Simple deterministic logic already solves it** — if rules, a query, or conventional software does the job reliably and cheaply, AI adds cost, latency, and non-determinism for nothing. Don't use a model where an `if` statement suffices.
- **The needed knowledge doesn't exist anywhere the system can access** — if the answer isn't in any data you can retrieve and isn't in the model's training, the model will confabulate. No grounding, no reliable AI.
- **There's no way to measure whether it's working** — if you can't define success and evaluate it (post 5), you can't deploy responsibly. An unmeasurable use case is unscopeable.

Being the person who says "AI isn't the right tool here, but here's what is" is one of the fastest ways to build the customer trust the whole engagement depends on. Recommending against AI when it doesn't fit is a feature of a good FDE, not a failure.

## Focusing on value, not capability

A recurring scoping mistake is to scope around what the model *can do* rather than what the customer *needs*. The model can do a thousand impressive things; the question is which one moves a real business outcome. Anchor scoping in the customer's outcomes using an outcomes lens: what job is someone trying to get done, what does success look like in *their* terms, and what is that worth? A use case tied to a measurable outcome — hours saved, backlog cleared, response time cut, decisions made faster — is fundable and defensible. A use case tied to "it's cool that the AI can..." is not.

This is also where you separate the **value of automation** from the **value of augmentation**. Fully automating a task (no human) is high-value but high-risk and high-bar; augmenting a human (AI drafts, human decides) is lower-risk, faster to deploy, and often captures most of the value. For a first use case, augmentation is usually the smarter scope — it delivers value while sidestepping the trust and reliability barriers that block full automation early.

## Picking the wedge

Even a well-fit, high-value problem is usually too big to solve at once. The AI FDE picks a **wedge**: the smallest slice that proves real value and earns the right to expand. A good wedge has three properties:
- **Narrow enough to ship fast** — deliver something real in weeks, not quarters, so momentum and trust build early.
- **Real enough to matter** — it does an actual job someone cares about, not a toy demo, so success is meaningful and fundable.
- **Representative enough to generalize** — solving it teaches you about the customer's data, systems, and workflow, so it opens the door to the next use case rather than being a dead end.

The wedge strategy mirrors good product thinking: land a beachhead, prove value, expand. For an AI deployment specifically, the wedge should also be one where you can *measure* success clearly (post 5) and *ground* the model in available data (post 4) — because those are the two things that make AI deployable, and the wedge is where you prove you can do both.

## The scoping output

Scoping ends with a written, customer-confirmed frame that answers:
- **The problem and the outcome** — what real job, and what success looks like in the customer's terms and numbers.
- **Why AI fits** — the honest fit assessment, including where it *won't* be used.
- **The wedge** — the specific narrow slice to build first, and why it's representative.
- **How success will be measured** — the metric and how you'll evaluate it (the seed of post 5).
- **Automation vs augmentation** — the intended level of autonomy, and the human's role.

That frame is the contract for the engagement. Skipping it is how teams end up months in, arguing about whether the impressive-but-vague thing they built is what anyone wanted.

The takeaway: scoping an AI use case is the highest-leverage decision the AI FDE makes — evaluate candidates on *both* fit (is AI genuinely suited: unstructured/fuzzy/high-volume/groundable) and value (real, measurable outcome), resist AI theater by honestly naming when AI is the wrong tool, anchor in the customer's outcomes rather than the model's capabilities, prefer augmentation over automation for the first use case, and pick a narrow, real, representative, *measurable* wedge. Get scoping right and the engagement has a chance; get it wrong and no engineering can rescue it.

## Key takeaways

- Scoping is where AI deployments are **won or lost** — the highest-leverage decision, made before any code, and the most common point of failure; resist **AI theater** (impressive but ill-fit).
- Evaluate every candidate on **two axes**: **fit** (is AI genuinely suited?) and **value** (real, measurable outcome?) — deploy only what scores well on both, and among those pick the one that proves value **fastest**.
- **AI fits** unstructured-language / fuzzy-judgment / high-volume-cognitive tasks whose knowledge is **retrievable**; **AI is a poor fit** where exactness is mandatory, deterministic logic already works, the knowledge isn't accessible, or success can't be measured — and saying so **builds trust**.
- Anchor in the customer's **outcomes**, not the model's capabilities; prefer **augmentation** (AI drafts, human decides) over full **automation** for a first use case — most of the value, far less risk.
- Pick a **wedge**: narrow enough to ship fast, real enough to matter, representative enough to generalize — and specifically one you can **measure** (post 5) and **ground in data** (post 4); end with a written, customer-confirmed frame that is the engagement's contract.

## Further reading

- [Outcome-Driven Innovation — framing problems by the job and its measures](https://en.wikipedia.org/wiki/Outcome-Driven_Innovation)
- [Google — Rules of Machine Learning (best practices for ML engineering)](https://developers.google.com/machine-learning/guides/rules-of-ml)
