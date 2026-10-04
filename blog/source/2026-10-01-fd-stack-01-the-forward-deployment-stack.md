# The Forward Deployment Stack

*The forward deployed engineer gets all the attention, but forward deployment is bigger than one role. It's a go-to-market operating model with three layers — build, scale, run — and seeing the whole stack is how AI companies turn embedded engineering from a heroic cost center into a repeatable engine.*

There is already a deep series on this site about the [Forward Deployed Engineer](/blog/series/forward-deployed-engineering/) and a second on [the AI version of the role](/blog/series/the-ai-forward-deployed-engineer/). This post zooms out. Because the longer you watch forward deployment work in the AI era, the clearer it becomes that "FDE" is only the first layer of something larger.

Forward deployment is not a job title. **It's a go-to-market operating model: you win by building value inside the customer's environment, not by demoing it to them.** And like any operating model, as it scales from one heroic engineer to a real function, it stratifies into layers — each with a different job, a different skill set, and a different failure mode.

I call it the Forward Deployment Stack. It has three layers.

## Why one role isn't enough

The FDE model is seductive because the first version is simple: send a brilliant engineer to embed with a customer, build the thing that wins the deal, and move on. It works — until it works too well.

Then you have ten FDEs, forty bespoke builds, no two alike, and a margin curve bending the wrong way. The heroics that won the early customers become the thing that stops you from scaling. The problem isn't the engineers. It's that "build the win" is only one of three jobs forward deployment actually requires.

## The three layers

```
   ┌─────────────────────────────────────────────┐
   │  RUN    Forward Deployed Leader (FDL)        │  the motion, the org, the economics
   ├─────────────────────────────────────────────┤
   │  SCALE  Forward Deployed Architect (FDA)     │  make the win repeatable, integrate, govern
   ├─────────────────────────────────────────────┤
   │  BUILD  Forward Deployed Engineer (FDE)      │  the first working win on real data
   └─────────────────────────────────────────────┘
        ▲ learning flows up      direction flows down ▼
```

**BUILD — the Forward Deployed Engineer.** Embeds with the customer and builds the first working win on their real, messy data. This is the established role, born at [Palantir](https://en.wikipedia.org/wiki/Palantir_Technologies) and now standard at the frontier AI labs. It owns one question: *can we make this actually work, here?*

**SCALE — the Forward Deployed Architect.** Takes the bespoke win and makes it survive the next ten customers: a reference architecture, security and governance that passes review, integrations that generalize, and a clear line between "reusable core" and "this-customer-only." It owns: *will this repeat without drowning us?*

**RUN — the Forward Deployed Leader.** Owns forward deployment as a business function — team design, engagement scoping, unit economics, and the decision of what graduates into product. It owns: *is this a scalable motion or a custom-dev shop wearing a software company's hoodie?*

## How the layers work together

The stack moves in two directions at once.

**Direction flows down.** Strategy (FDL) sets which customers and problems are worth embedding in; architecture (FDA) sets the patterns the engineer builds from; the engineer (FDE) builds the specific win.

**Learning flows up.** The FDE hits reality first — the edge case, the integration nobody anticipated, the feature customers keep asking for. That field signal flows up to the FDA, who turns recurring one-offs into reusable architecture, which flows up to the FDL, who decides what becomes product and funds it. This is the flywheel: *every deployment should make the next one cheaper.* Without the upward flow, forward deployment is just consulting.

## It's also a career ladder — and an org-maturity story

The three layers map onto a career: a strong FDE grows into an FDA as they start seeing patterns across deployments, and into an FDL as they start owning the economics and the team. They also map onto company maturity: you start with one FDE (build), add an FDA when bespoke work starts piling up (scale), and formalize an FDL when forward deployment becomes a real line of the business (run).

Most companies discover these layers the painful way — by hitting the wall each one solves. Naming them up front lets you see the wall coming.

## Where to start

You don't hire all three on day one. You start at the bottom:

1. **Build first.** One excellent FDE, one lighthouse customer, one real win. Prove the motion exists.
2. **Scale when the one-offs pile up.** The moment you're building the same thing twice, you need the architect layer — even if it's the same person wearing a second hat.
3. **Run when it's a business.** When forward deployment is influencing real revenue, it needs an owner who manages it as a function with its own economics.

The rest of this series takes the two layers that almost nobody writes about — the [Forward Deployed Architect](/blog/posts/fd-stack-02-the-forward-deployed-architect.html) and the [Forward Deployed Leader](/blog/posts/fd-stack-03-the-forward-deployed-leader.html) — and then gives founders a practical blueprint for [building the whole function](/blog/posts/fd-stack-04-building-a-forward-deployment-function.html).

The engineer who closes by building is where this starts. It is not where it ends.
