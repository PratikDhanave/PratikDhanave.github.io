# Rapid Prototyping

*An FDE's superpower is turning a vague problem into something the customer can see and touch within days — because a rough working demo teaches more than a month of meetings.*

Once you've framed the real problem (post 2), the temptation is to design the proper solution. Resist it. The forward deployed engineer's most valuable early move is to build the smallest thing that makes the problem — and a candidate solution — *concrete*, fast. A prototype is not a small version of the final product; it's an instrument for learning, persuasion, and momentum. This post is about building it well.

## Why prototype first

Three reasons, each decisive:

- **It resolves ambiguity that talk can't.** People react to something real in ways they never articulate in interviews. Put a rough screen or a working query in front of them and you'll hear "oh, but it needs to handle the returns case" — a requirement that would never have surfaced in the abstract.
- **It builds trust and momentum.** A customer who sees their own data flowing through something by the end of week one believes you can help them. Slides don't do that; a live demo does.
- **It de-risks the real build.** The prototype is where you discover the data is filthier than promised, the integration is harder than assumed, or the approach doesn't work — cheaply, before you've committed to building it "properly."

**The gotcha:** the goal of a prototype is *learning per day*, not code quality. Every hour spent on abstractions, tests, and polish that don't change what you learn this week is an hour stolen from the loop that actually reduces risk. Optimize for speed of insight.

## What to build (and what to fake)

The art is choosing the thinnest slice that proves the risky assumption. Ask: *what's the one thing that, if it doesn't work, kills the whole idea?* Build that; fake everything else.

- **Hard-code, stub, and mock aggressively.** Use one real example record end-to-end rather than a general pipeline. Fake the parts that are merely tedious; make real only the part that carries the risk.
- **Use whatever's fastest, not whatever's "right."** A notebook, a script, a spreadsheet with a macro, a no-code tool, a single-file app. The prototype's stack is disposable.
- **Show real customer data.** Nothing lands like the customer seeing *their own* records. Even a small, hand-cleaned sample beats synthetic data for persuasion and for surfacing reality.
- **Prefer vertical slices over horizontal layers.** One workflow working end-to-end (even ugly) teaches and persuades far more than a beautiful data model with no UI.

```text
Don't build:  [ full ingestion ][ general model ][ polished UI ][ auth ][ tests ]
Do build:     one real record ─► the risky step (real) ─► a rough view the user reacts to
```

## The demo loop

FDE prototyping runs on a tight cadence: build a slice, show it to the customer, watch their reaction, adjust, repeat — ideally weekly or faster. The reaction is the data. Watch where they lean in, where they frown, what they immediately try to do that you didn't build. Demo early and demo unfinished; a wobble you explain ("this part's faked for now") is fine and actually builds credibility, because it shows the seams honestly.

**The gotcha:** a demo that's too polished sets the wrong expectation — the customer thinks you're nearly done when you've validated one slice, and they'll be confused when "the rest" takes real time. Be explicit about what's real and what's scaffolding.

## Managing the prototype's lifespan

Here is the danger unique to FDE prototyping: the prototype works, the customer loves it, and now they want to *use it* — in production, on Monday. The disposable notebook you built to learn is suddenly load-bearing. Two failure modes bracket this moment:

- **Shipping the prototype as-is** into production, where its hard-coded assumptions, absent error handling, and mocked pieces become incidents.
- **Throwing it all away** and rebuilding from scratch, losing weeks and the momentum you earned.

The healthy path is deliberate: decide *consciously* which parts of the prototype graduate to real code and which were always scaffolding, and be honest with the customer about the difference between "it demoed" and "it's production-ready" (integration and hardening are post 4). Treat the prototype as a *spec you can run* — it captured the real requirements — and rebuild the risky parts properly while keeping the validated shape.

**The gotcha:** "it works in the demo" and "it's ready for production" are separated by exactly the work customers can't see — real data volumes, error paths, edge cases, security, deployment. A prototype pushed straight to prod because it looked done is the most common way FDE goodwill turns into a 2am incident.

## Keep the throwaway from becoming permanent

Even while moving fast, a little discipline pays off: keep the prototype in version control, jot down the assumptions you hard-coded (so you know what to revisit), and note which shortcuts are safe to keep versus which are load-bearing lies. This isn't building it "properly" — it's leaving yourself a map for when the prototype inevitably outlives its intended lifespan, which it usually does.

## When the prototype says "no"

Sometimes the prototype's most valuable outcome is proving the idea *doesn't* work — the data can't support the analysis, the model isn't accurate enough, the workflow doesn't fit. That's a win, discovered in days instead of months. An FDE who can say "we tried it, here's what we learned, here's the better direction" builds more trust than one who ploughs ahead. Failing fast and honestly is a feature of the role, not a failure of it.

## Key takeaways

- A prototype is an **instrument for learning and persuasion**, not a small final product — optimize for insight per day.
- Build the **thinnest slice that tests the riskiest assumption**; hard-code, stub, and fake everything else.
- Use **real customer data** and **vertical slices** — they persuade and surface reality far better than synthetic data or horizontal layers.
- Run a **tight demo loop**; the customer's reaction is the data, and honest wobble builds credibility.
- Be explicit that **"it demoed" ≠ "it's production-ready"** — the gap is the invisible work (post 4).
- Decide **consciously what graduates** from prototype to real code; treat the prototype as a runnable spec, not something to ship blindly or discard wholesale.
- A prototype that proves the idea **won't work** is a fast, valuable win.

## Further reading

- [Tom Chi — rapid prototyping / "maximize the rate of learning"](https://en.wikipedia.org/wiki/Tom_Chi) — the philosophy behind fast, cheap prototypes.
- [IDEO — design thinking and prototyping](https://designthinking.ideo.com/) — building to think and to test.
- [Eric Ries — The Lean Startup (MVP / build-measure-learn)](http://theleanstartup.com/) — the validated-learning loop an FDE runs at customer scale.
