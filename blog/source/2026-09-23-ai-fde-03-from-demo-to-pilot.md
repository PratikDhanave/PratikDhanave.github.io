# From Demo to Pilot

*An AI demo is the easiest impressive thing to build and the most misleading. It runs on hand-picked inputs, in a clean environment, with the failures edited out — and it convinces everyone the problem is nearly solved when the real work has barely begun. The AI forward deployed engineer's job in this phase is to use the demo to win belief, then walk the customer honestly across the chasm to a pilot that survives real data.*

Scoping (post 2) picked the wedge. Now you build. The general FDE practice of rapid prototyping — build the thinnest slice that tests the riskiest assumption — still holds (see the [foundational series](/blog/series/forward-deployed-engineering/)). But AI has a peculiar, dangerous property that reshapes this phase: the distance from a working demo to a working pilot is far larger than it looks, and the demo actively hides that. This post is about crossing that gap without losing the customer's trust along the way.

## The AI demo is a trap dressed as a triumph

With a frontier model, you can build a genuinely amazing demo in an afternoon: point it at a few example inputs, tune the prompt until the outputs look great, and present it. Everyone in the room is dazzled. The problem is that the demo is a *best case*, and AI's best case and typical case diverge wildly:
- **It ran on cherry-picked inputs.** You chose examples the model handles well. Real inputs are messier, weirder, and more varied — and the model's quality on them is unknown until you try.
- **The failures were edited out.** In a demo you re-run until it looks good. In production every input gets one shot, including the ones that make the model confidently wrong.
- **It wasn't grounded in real data.** The demo used clean sample data or the model's general knowledge; the real system needs the customer's messy, permissioned, incomplete data (post 4).
- **Nothing was measured.** "It looked great in the demo" is an anecdote, not a reliability number. You have no idea how often it's right until you evaluate (post 5).

So the demo creates a dangerous illusion: it makes a 5%-done thing look 90% done. If you let the customer believe the demo *is* the product, you've set an expectation you cannot meet, and the gap between their belief and reality becomes your problem. This is the single most important dynamic to manage in an AI engagement.

## Use the demo for what it's actually good for

The demo isn't useless — it's just misunderstood. Its real job is not to prove the system works; it's to **win belief and align on direction**:
- **Show the art of the possible.** The demo makes an abstract idea concrete, so the customer can react to something real and confirm you're aiming at the right thing.
- **Generate momentum and sponsorship.** A compelling demo unlocks the budget, access, and attention the real work needs. That's valuable — as long as you convert the excitement into a commitment to do the real work, not a belief that it's done.
- **Surface hidden requirements.** The moment people see it, they say "but it needs to handle X" — which is discovery you couldn't get any other way.

The skill is to ride the demo's persuasive power while immediately, explicitly resetting expectations: "This shows what's possible. Here's the real work between this and something you can rely on, and here's how we'll prove it works." Naming the gap out loud, at the moment of maximum excitement, is what separates an FDE who builds lasting trust from one who over-promises and burns it.

## The chasm: why demo-to-pilot is the hard part

The gap between a demo and a pilot that real users touch with real data is where most AI projects stall or die. Crossing it means confronting everything the demo hid:
- **Real inputs at real variety.** You must handle the long tail of messy, unexpected inputs — not the five you picked. This usually means the naive prompt that aced the demo needs grounding, structure, examples, and fallback handling.
- **Real data, grounded.** The pilot must reason over the customer's actual data, which means building retrieval/grounding against messy internal sources (post 4). This is often the bulk of the work and is entirely invisible in the demo.
- **Measured reliability.** You need an evaluation harness and a number: how often is it right, on real examples, by the customer's definition of right (post 5)? Without this you're flying blind and can't earn trust.
- **The unhappy paths.** What happens when the model is unsure, wrong, or the input is out of scope? The demo never showed a failure; the pilot must handle them gracefully (guardrails, human-in-the-loop — posts 5 and 6).

A useful mental model: the demo tests *can the model ever do this?* The pilot tests *can the system reliably do this, on real data, often enough to trust?* Those are completely different questions, and the second is 90% of the engineering.

## Building the pilot: from prompt to system

The move from demo to pilot is largely the move from *a prompt* to *a system*. Concretely, the AI FDE typically has to add:
- **Grounding / retrieval** so the model works from the customer's real data (post 4).
- **Structure and constraints** — structured outputs, input validation, and prompt hardening so results are parseable and the system resists bad or adversarial input.
- **An evaluation set** — a collection of real, representative examples with known-good answers, drawn from the customer's own cases, so you can measure quality and catch regressions (post 5).
- **Guardrails and fallbacks** — checks on outputs, confidence handling, and a defined behavior for "the model shouldn't answer this" (post 5, post 6).
- **A thin but real integration** — enough connection to real systems and a real (small) group of users that the pilot exercises the actual workflow (post 6), not a sandbox.

Notice the demo's clever prompt is a small part of this. The pilot is mostly the unglamorous scaffolding around the model that turns a capability into a dependable job — which is exactly the AI FDE's value.

## Running the pilot

A pilot is an experiment with a hypothesis: *this system does the scoped job reliably enough to be worth expanding.* Run it like one:
- **Real users, real data, limited scope.** A small set of actual users doing actual work, so you learn the truth — bounded so failures are safe.
- **Measure against the success metric.** The metric you defined in scoping (post 2), evaluated continuously (post 5). "Do users find it useful and is it right often enough?" answered with data, not vibes.
- **Instrument failures.** Capture where and how it fails — those become your eval set additions and your next iteration's work. In AI, the failures *are* the roadmap.
- **A clear decision at the end.** Expand, iterate, or stop — decided against the metric, not against how impressive the demo was. A pilot that honestly says "not yet, here's what's needed" is a success; one that gets waved through on demo excitement and fails in production is not.

The takeaway: an AI demo is the easiest impressive thing to build and the most misleading — it runs on cherry-picked inputs with failures edited out, making a barely-started thing look nearly done. Use the demo for what it's genuinely good for (winning belief, momentum, and surfacing requirements) while explicitly resetting expectations at the peak of excitement, then do the real work of crossing the chasm: grounding in real data, measuring reliability, and handling the unhappy paths the demo never showed. The pilot answers the question the demo can't — *can the system reliably do this on real data, often enough to trust?* — and that question is 90% of the job.

## Key takeaways

- The **AI demo is a trap dressed as a triumph**: built in an afternoon on cherry-picked inputs with failures edited out and nothing grounded or measured, it makes a ~5%-done thing look ~90% done — creating an expectation you can't meet.
- Use the demo for its **real jobs** — showing the art of the possible, winning momentum/sponsorship, surfacing hidden requirements — while **explicitly resetting expectations** at the moment of peak excitement (naming the gap out loud builds the trust the engagement depends on).
- The **demo-to-pilot chasm** is where AI projects die: it forces confronting everything the demo hid — real input variety, grounding in messy real data, **measured** reliability, and the **unhappy paths** (unsure/wrong/out-of-scope).
- Crossing it is the move **from a prompt to a system**: grounding/retrieval, structured outputs + input validation + prompt hardening, an **eval set from the customer's own cases**, guardrails/fallbacks, and a thin-but-real integration — the clever prompt is a small part.
- Run the pilot as an **experiment**: real users/real data/limited scope, measured against the scoped success metric, with failures instrumented (the failures are the roadmap) and a clear expand/iterate/stop decision made on **data, not demo excitement**.

## Further reading

- [Minimum viable product — testing the riskiest assumption cheaply](https://en.wikipedia.org/wiki/Minimum_viable_product)
- [Customer Development — validating with real users before scaling](https://en.wikipedia.org/wiki/Customer_Development)
