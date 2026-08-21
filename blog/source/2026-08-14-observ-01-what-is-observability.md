# What Observability Is

*Monitoring tells you whether the things you thought to check are okay. Observability lets you ask questions you never anticipated about a system you can't see inside. In a world of distributed services where failures are novel and emergent, that difference — between watching known dashboards and investigating unknown problems — is the difference between guessing and knowing.*

Every non-trivial system eventually breaks in a way nobody predicted, and when it does, the only thing that saves you is being able to *ask the system what's happening* and get an answer. That capability is **observability**. This series builds it up — metrics, logs, traces, OpenTelemetry, SLOs, and alerting — but it starts with what observability actually *is*, and why it's more than the monitoring dashboards teams already have. Get the concept right and the tools make sense as means to it.

## Observability vs monitoring

The terms are used interchangeably and shouldn't be. The distinction is about the *kinds of questions* you can answer:

- **Monitoring** watches for *known* problems — you decide in advance what to measure (CPU, error rate, latency), set thresholds, and get told when those cross. It answers questions you *already knew to ask*: "is the error rate high?" Monitoring is about **known-unknowns** — the failure modes you anticipated.
- **Observability** is the property of a system that lets you understand its *internal state from its outputs*, well enough to answer questions you *didn't* anticipate. It answers "why is *this specific* subset of requests slow, only for users in this region, since that deploy?" — a question no one predefined. Observability is about **unknown-unknowns** — the novel, emergent failures you couldn't have foreseen.

The crucial reframing: monitoring asks "is the system working?" against a fixed checklist; observability asks "*what* is the system doing, and *why*?" without a fixed checklist. A well-monitored system tells you *that* something is wrong; an observable system lets you figure out *what and why*, including for problems you never imagined. You need both, but observability is the deeper capability, and it's the one distributed systems make essential.

## Why modern systems demand observability

Observability isn't new fashion — it's a response to how systems changed. A single monolithic application on one server is relatively easy to reason about: attach a debugger, read the logs, hold it in your head. Modern systems broke all of those assumptions:

- **Distributed** — a request flows through many services (the distributed-systems series), so no single place holds the whole story. You can't debug what you can't see across service boundaries.
- **Failures are emergent and novel** — from partial failure, race conditions, and interactions between services, the failures are ones nobody wrote a check for. They're unknown-unknowns by nature.
- **You can't reproduce production** — the bug happens at scale, under real traffic, with real data, in a way you can't recreate locally. You have to understand it *from what the running system emits*.
- **Ephemeral and dynamic** — containers come and go, autoscaling shifts load; there's no stable machine to SSH into and inspect.

In this world, the old debugging model — reproduce it, step through it — often doesn't work. The only way to understand what happened is if the system *emitted enough information about its own behavior* to reconstruct the story after the fact. That's observability: designing systems to be *interrogable*, so you can investigate the failures you didn't predict. It's a property you build *in*, not a tool you bolt on.

## The three pillars

Observability is conventionally built on three types of telemetry — the "three pillars" — each answering a different question, and the middle posts of this series cover each in depth:

```text
  METRICS  → aggregated numbers over time   → "IS something wrong, and how much?"
  LOGS     → discrete records of events      → "WHAT exactly happened here?"
  TRACES   → the path of a request across    → "WHERE, across services, did it happen?"
             services
```

- **Metrics** — numerical measurements aggregated over time (request rate, error count, latency percentiles). Cheap, efficient, great for *detecting* that something's wrong and seeing trends. They tell you the *what/how-much* at a glance but not the *why*.
- **Logs** — timestamped records of discrete events, with detail. They tell you *what specifically happened* at a point — the granular story — but are voluminous and, alone, don't show how events connect across services.
- **Traces** — the record of a single request's journey through all the services it touched, broken into timed steps. They tell you *where* in a distributed system time went or a failure occurred — the connective tissue metrics and logs lack.

The pillars are complementary, not redundant: metrics detect the problem, traces localize *where* it is across services, logs reveal *what* happened at that spot. Real investigation moves between them — a spiking metric leads you to a slow trace which points you to the log line with the actual error. Observability emerges from using all three together, which is why the series covers each and then unifies them (OpenTelemetry).

## Beyond "three pillars": the goal is answering questions

A caveat worth planting early: the "three pillars" framing is useful but can mislead if you treat it as "collect three types of data and you're done." Observability isn't having metrics, logs, and traces — it's being able to *answer arbitrary questions about your system's behavior*. Three separate, disconnected data stores you can't correlate is worse than three that link together. The modern direction (which OpenTelemetry and correlated telemetry enable) is treating the pillars as connected views of the same events — jump from a metric to the traces behind it to the logs within those traces — so you can follow an investigation wherever it leads. Keep the *goal* — interrogability, answering the unanticipated question — above the mechanism.

## What the series builds toward

From here: each pillar in depth (metrics, logs, traces), then OpenTelemetry (the vendor-neutral standard that unifies them), then turning telemetry into reliability (SLIs/SLOs/error budgets) and actionable alerts (alerting done right), and finally instrumenting a real system and building an observability practice. The through-line is this post's idea: observability is the capability to understand and investigate a system you can't fully see, especially when it fails in ways you didn't predict — and everything ahead is in service of that.

## Key takeaways

- Monitoring watches for known problems against predefined checks (known-unknowns: "is the error rate high?"); observability lets you understand a system's internal state from its outputs well enough to answer questions you didn't anticipate (unknown-unknowns: "why is *this* slice slow since that deploy?").
- Monitoring tells you *that* something is wrong; observability lets you investigate *what and why* — including novel, emergent failures — so you need both, but observability is the deeper capability.
- Modern systems demand it because they're distributed (no single place holds the story), fail in emergent/novel ways, can't be reproduced locally, and are ephemeral — so you must understand them from what they emit, which means building them to be interrogable.
- The three pillars answer different questions: metrics (is something wrong, how much — detection/trends), logs (what exactly happened — granular detail), traces (where across services — the distributed path); they're complementary and investigation moves between them.
- The goal isn't collecting three data types but being able to answer arbitrary questions about behavior — so correlated, connected telemetry (jump metric → trace → log) beats three disconnected stores; keep interrogability above the mechanism.

## Further reading

- [OpenTelemetry — what is observability](https://opentelemetry.io/docs/concepts/observability-primer/)
- [Google SRE Book (free online)](https://sre.google/books/)
- [Distributed Systems from First Principles series](/blog/series/distributed-systems-from-first-principles/)
