# What a Forward Deployed Engineer Is

*Part software engineer, part consultant, part product manager — the forward deployed engineer works inside the customer's world to turn a hard problem into working software, then carries what they learn back to the product.*

Most engineering roles sit behind a backlog. Requirements arrive as tickets, someone else has already decided what to build, and success is shipping the thing as specified. The forward deployed engineer (FDE) works at the other end of that pipe — next to the customer, before anyone knows what to build, where the problem is still vague and the data is still messy. It is one of the most misunderstood roles in the industry, and one of the most valuable when the fit is right. This series is about doing it well.

## Where the role comes from

The title was popularized by Palantir, whose FDEs embedded with customers — governments, banks, hospitals — to bend a general platform around a specific, urgent problem. The pattern has since spread across enterprise software, data/ML platforms, and especially AI companies, where the gap between "the model can do impressive things in a demo" and "it solves *this* customer's workflow" is exactly the gap an FDE closes. Whatever the label (forward deployed engineer, solutions engineer, delivery engineer, applied engineer), the shape is the same: an engineer who operates *at the customer*, not just *for* them.

## What the job actually is

An FDE does three jobs that are usually held by three different people, and the blend is the whole point:

- **The engineer** builds real, working software — integrations, prototypes, pipelines, glue — often against unfamiliar systems and dirty data, under time pressure.
- **The consultant** discovers the *real* problem (rarely the one first stated), navigates the customer's org, and builds the trust that lets the work land.
- **The product manager** notices which bespoke solutions keep recurring and feeds them back so the core product absorbs them.

```text
        the FDE sits here ▼
customer problem  ──►  [ discover · prototype · integrate · earn trust ]  ──►  working solution
                                        │
                                        └──►  patterns fed back to the product
```

The reason the blend matters: each job alone fails at the customer. A pure engineer builds the wrong thing beautifully. A pure consultant produces slides no one can run. A pure PM has nothing to demo next week. The FDE compresses the loop — understand, build, show, adjust — inside the customer's context and on the customer's clock.

## How it differs from adjacent roles

| Role | Optimizes for | Distance from customer |
|---|---|---|
| Product SWE | Shipping the roadmap | Far (behind PM/backlog) |
| Sales/Solutions Engineer | Winning the deal (pre-sales demos) | Close, but pre-contract |
| Consultant | Advice/deliverables | Close, but often non-code |
| **Forward Deployed Engineer** | A working solution to *this* customer's problem, then product feedback | Closest — embedded, builds real code |

The FDE overlaps all of them but is defined by the combination: they *build* (unlike a consultant), they build *for a specific named customer* (unlike a product SWE), and they stay *after* the sale to make it actually work (unlike a pre-sales SE).

**The gotcha:** the FDE role is not "senior engineer who also talks to customers." The customer-facing half is not a soft-skills garnish on top of the coding — it is half the job, and the half that most often determines whether the work succeeds. Treating discovery and trust as optional is the fastest way to ship something technically correct that nobody adopts.

## The core tension: bespoke vs product

Every FDE lives on a knife-edge. Move fast and bespoke, and you delight *this* customer while creating a pile of one-off code nobody else can use (and that you now have to maintain). Insist on general, productized solutions, and you move too slowly to earn the customer's trust or hit the deadline. The craft is knowing when to hack something specific to prove value *now*, and when a pattern has recurred enough that it should graduate into the product. Getting this wrong in either direction is the classic FDE failure mode — and post 6 is entirely about navigating it.

**The gotcha:** every bespoke solution is a small debt you or the product team will service later. That debt is often worth taking to win trust and momentum — but only if someone is watching the pile and deciding what to generalize. Bespoke work with no feedback path is how an FDE org drowns in unmaintainable one-offs.

## Who thrives here

The role rewards a specific temperament: high tolerance for ambiguity and messiness, genuine curiosity about the customer's domain (you'll learn more about insurance claims or clinical trials or freight logistics than you expected), technical breadth over narrow depth (you touch data, backend, integrations, sometimes frontend and ops in one week), comfort being the least-knowledgeable person in the room about the domain and the most-knowledgeable about the software, and the resilience to demo something half-finished, watch it wobble, and iterate in front of the customer. If you need clean requirements, a stable stack, and a quiet backlog, this role will feel like chaos. If you're energized by dropping into a hard, undefined problem and making something real by Friday, it's one of the best seats in the industry.

## What this series covers

The rest of this series walks the arc of an FDE engagement and career:

1. **This post** — what the role is.
2. **Discovery and problem framing** — finding the real problem behind the stated one.
3. **Rapid prototyping** — building fast to validate before you build to last.
4. **Integration and deployment** — surviving real customer data and systems.
5. **Building trust and communication** — the relationship that makes the work land.
6. **From bespoke to product** — feeding learnings back without drowning in one-offs.
7. **The FDE toolkit** — the technical breadth the role demands.
8. **Thriving as an FDE** — career, growth, and the pitfalls to avoid.

The throughline: an FDE turns a vague, high-stakes customer problem into working software *and* into product knowledge. Both halves count.

## Key takeaways

- An FDE blends **engineer + consultant + product manager**, operating embedded at the customer rather than behind a backlog.
- The role was popularized by Palantir and is now central to enterprise and especially **AI companies**, where the demo-to-workflow gap is wide.
- It's defined by the **combination**: builds real code (unlike a consultant), for a specific customer (unlike a product SWE), and stays to make it work (unlike pre-sales).
- The customer-facing half is **half the job**, not a garnish — discovery and trust decide whether good code gets adopted.
- The central tension is **bespoke vs product**; managing that pile of one-offs (post 6) is what separates a healthy FDE org from a drowning one.
- The role suits people who thrive in **ambiguity, breadth, and building something real fast**.

## Further reading

- [Palantir — "A Day in the Life of a Forward Deployed Software Engineer"](https://blog.palantir.com/a-day-in-the-life-of-a-palantir-forward-deployed-software-engineer-45ef2de257b1) — the origin of the role, in its own words.
- [Martin Fowler — the value of embedded, close-to-the-user delivery](https://martinfowler.com/) — on tightening the build-measure-learn loop.
- [Steve Blank — Customer Development](https://steveblank.com/) — the discipline of getting out of the building to find the real problem.
