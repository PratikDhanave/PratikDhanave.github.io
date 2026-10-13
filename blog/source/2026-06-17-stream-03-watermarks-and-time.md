# Watermarks — Reasoning About Time in an Out-of-Order Stream

*Post 2 ended on a hard problem: you need event-time results, but events arrive late and out of order, so you never know when you've seen everything for a given time. Watermarks are stream processing's elegant answer — a running estimate of how far event time has progressed, letting you decide when it's safe to produce a result. They're the mechanism that makes correct event-time computation possible over a messy, unbounded stream.*

Post 2 established the event-time/processing-time gap and the completeness-vs-latency tension. This post is the key mechanism for managing it: watermarks. Understanding watermarks is understanding how stream processors reason about time — and it's the concept that makes windowing (post 4) work correctly.

## The problem watermarks solve

Recall the core difficulty (post 2): to answer an event-time question ("transactions between 12:00 and 12:01"), you need all events in that event-time range — but events arrive out of order and late, so at any processing-time moment you can't be sure whether more events for that range will still show up. If you emit the result too early, you miss late events (incomplete/wrong); if you wait forever for possible stragglers, you never emit (infinite latency). You need a principled way to decide: *"event time has probably advanced far enough that I've seen essentially all events up to time T — it's safe to compute results for times ≤ T."*

That's exactly what a **watermark** is: a marker flowing through the stream that asserts *"event time has progressed to T — no (or few) events with event time earlier than T should still arrive."* A watermark of 12:01 means "I believe I've now seen all events that happened at or before 12:01, so I can finalize results for event-time windows up to 12:01." It's the stream processor's running estimate of event-time progress, derived from the event timestamps it has seen — a way to track "how complete is my knowledge of the past?" as the unbounded stream flows.

Watermarks turn the impossible ("wait until you've seen everything" — you never do) into the practical ("wait until event time has probably passed this point, then act"). They're how a processor decides *when* to produce event-time-correct results without waiting forever.

## How watermarks handle the completeness-latency tradeoff

The beauty of watermarks is that they make the completeness-vs-latency tradeoff (post 2) *explicit and tunable*, rather than hidden:

- **A watermark is an estimate, and estimates can be wrong.** The processor estimates event-time progress from the timestamps it's seen, but a straggler *could* still arrive with an event time before the watermark — a **late event** that arrives after the watermark already "closed" its window. How you handle these is a design choice (below).
- **Watermark aggressiveness is the tuning knob.** You choose how long to wait before advancing the watermark past a given time — effectively, how much lateness to tolerate. A watermark that advances aggressively (assumes few late events) → low latency (emit results quickly) but risks missing stragglers; a watermark that advances conservatively (waits longer, allows more lateness) → higher latency but more completeness. This is *exactly* post 2's tradeoff, now a concrete, adjustable parameter. You set it based on your data's real lateness characteristics and your latency needs.
- **The watermark typically trails the max event time seen** by some bound (e.g. "watermark = latest event time seen − 30 seconds"), encoding "I'll allow events up to 30 seconds late." This heuristic, tuned to observed lateness, is a common practical approach.

So watermarks don't magically solve the tension — they *operationalize* it: you decide, via watermark policy, how to trade completeness for latency, and the system acts on that decision consistently. That's a huge improvement over ad-hoc "wait a bit and hope," and it's why watermarks are central to modern stream processing (Flink and others build on them).

## Handling late events, and why this matters

Because watermarks are estimates, events can still arrive *after* their watermark has passed — **late events** — and a robust stream processor must decide what to do with them:

- **Drop them** — simplest; acceptable when a few missed late events don't matter (approximate real-time metrics).
- **Update the result** — revise the already-emitted result to include the late event (emit a correction). More correct but requires downstream consumers to handle updates, and ties into the completeness story.
- **Side-output them** — route late events to a separate channel for special handling (log them, process separately), so they're not silently lost.
- **Allow lateness up to a bound** — keep a window's state around for a grace period after the watermark, accepting late events within that grace period and only then finalizing. This explicitly extends the completeness window at a known latency cost.

The choice depends on how much correctness vs simplicity/latency your use case needs — the recurring streaming tradeoff. The deeper point: watermarks and late-event handling together let a stream processor produce **event-time-correct results from an out-of-order stream, with an explicit, tunable tradeoff between completeness and latency, and a defined policy for the stragglers that beat the estimate.** This is the principled machinery that replaces the naive (and wrong) "process events in the order they arrive." Without watermarks, you either compute on processing time (wrong answers, post 2) or wait forever (no answers); with them, you get correct-enough answers at a latency you control. That's why watermarks, abstract as they seem, are the quiet foundation of correct stream processing — and the thing that makes windowing (post 4) actually produce right answers.

The throughline: to produce **event-time-correct results** from a stream where events arrive **late and out of order**, you need to know *when it's safe to compute results for a time range* — and a **watermark** answers exactly that: a marker flowing through the stream asserting "event time has progressed to T; (almost) no earlier events will still arrive," so you can finalize results for times ≤ T. It turns the impossible ("wait until you've seen everything") into the practical ("wait until event time has probably passed T"). A watermark is an **estimate**, so its **aggressiveness is the tuning knob** that makes post 2's **completeness-vs-latency tradeoff explicit** (advance aggressively → low latency, risk missing stragglers; conservatively → more complete, higher latency; typically trail the max event time by a lateness bound). Because estimates can be beaten, **late events** need a policy — **drop**, **update the result**, **side-output**, or **allow lateness up to a grace bound** — chosen by your correctness/latency needs. Watermarks + late-event handling are the principled machinery replacing naive "process in arrival order," and the foundation that makes windowing (post 4) correct.

## Key takeaways

- The problem: to answer an **event-time** question you need all events in that range, but they arrive **late and out of order**, so you never know if more will come — emit too early (miss late events) or wait forever (infinite latency). You need a principled "it's safe to compute now" signal.
- A **watermark** is that signal: a marker flowing through the stream asserting **"event time has progressed to T — (almost) no events earlier than T will still arrive,"** so results for event-time windows ≤ T can be finalized. It's the processor's running **estimate of event-time progress** from observed timestamps — turning "wait until you've seen everything" (impossible) into "wait until event time has probably passed T" (practical).
- Watermarks make post 2's **completeness-vs-latency tradeoff explicit and tunable**: **aggressive** watermark advance → low latency but risks missing stragglers; **conservative** → more complete but higher latency; a common heuristic is **watermark = max event time seen − a lateness bound** (e.g. −30s), tuned to observed lateness and latency needs.
- Because watermarks are **estimates**, **late events** (arriving after their watermark) still happen and need a policy: **drop** (simple, approximate), **update/correct** the emitted result (correct, but consumers must handle updates), **side-output** (route for special handling, not silently lost), or **allow lateness up to a grace bound** (keep window state a bit longer — extends completeness at a known latency cost).
- Together, watermarks + late-event handling produce **event-time-correct results from an out-of-order stream with an explicit, tunable completeness/latency tradeoff and a defined straggler policy** — the principled machinery that replaces naive "process in arrival order," and the foundation that makes windowing (post 4) produce right answers.

## Further reading

- [Stream processing — event-time processing and watermarks](https://en.wikipedia.org/wiki/Stream_processing)
- [Event-driven architecture — the streams watermarks reason over](https://en.wikipedia.org/wiki/Event-driven_architecture)
