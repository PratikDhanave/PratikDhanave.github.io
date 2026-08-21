# Metrics

*Metrics are the cheapest, most efficient telemetry you have — a handful of numbers that summarize millions of events and tell you, at a glance, whether your system is healthy. Their power is aggregation; their trap is cardinality; and knowing which numbers to watch (and how to read percentiles) is the difference between a dashboard that warns you and one that lies to you.*

The last post named metrics as the pillar that answers "is something wrong, and how much?" This post goes deep: what metrics are, the main types, the percentile trap that fools teams into thinking they're fine, the cardinality problem that blows up costs, and the frameworks (RED, USE) for choosing what to measure. Metrics are where observability usually starts, because they're cheap to collect and superb at *detection*.

## What a metric is

A **metric** is a numerical measurement tracked over time — a **time series** of values with a timestamp. "Requests per second," "error count," "memory used," "request latency" are metrics. Their defining property is **aggregation**: a metric doesn't record every individual event, it records *summaries* (counts, sums, distributions) at intervals. This is exactly why metrics are so efficient — a single number can represent millions of underlying events, so metrics are cheap to store, fast to query, and ideal for dashboards and trends over long time ranges.

The trade-off of aggregation is *lost detail*: a metric tells you the error *rate* jumped, but not *which* requests failed or *why* (that's logs and traces). So metrics are the *detection and trend* layer — great for "something is wrong, here's how much, here's the trend," and deliberately not for "here's exactly what happened." Play to that strength.

## The metric types

Most metric systems (Prometheus-style) have a few fundamental types, and using the right one matters:

- **Counter** — a value that only ever *increases* (or resets to zero on restart): total requests, total errors, bytes sent. You don't read a counter's raw value; you read its *rate of change* ("errors per second"), which is what's meaningful. Counters answer "how many, how fast."
- **Gauge** — a value that goes *up and down*, a snapshot of a current state: memory in use, active connections, queue depth, temperature. You read a gauge's current value directly. Gauges answer "how much right now."
- **Histogram** — records the *distribution* of values across buckets, so you can compute percentiles: request latency, response sizes. This is the type behind latency percentiles (below), and it's essential because averages lie. Histograms answer "what's the distribution."
- **Summary** — a related type that computes quantiles client-side; similar goal to histograms with different trade-offs.

Choosing correctly: counters for things that accumulate (requests, errors), gauges for current levels (memory, connections), histograms for anything where the *distribution* matters (latency, sizes). Using a gauge where you need a rate, or an average where you need percentiles, produces misleading dashboards.

## The percentile trap: why averages lie

The most important practical lesson about metrics: **do not measure latency (or any user-experience metric) with averages — use percentiles.** An average latency hides the tail, and the tail is where users suffer:

```text
100 requests: 99 take 50ms, 1 takes 5000ms
  average latency = ~100ms   ← looks fine!
  p99 latency     = 5000ms   ← one in a hundred users waited 5 seconds
```

The average says 100ms and looks healthy; meanwhile 1% of users had a terrible experience. **Percentiles** tell the truth: p50 (median) is the typical case, p95/p99 are the tail — what your *worst-served* users experience. At scale, "1% of requests" is a lot of real, unhappy users, and often includes your most active ones (more requests = more chances to hit the tail). Always dashboard and alert on p95/p99 latency, not averages — averages are the single most common way metrics dashboards lull teams into thinking a struggling system is fine. This is why histograms matter: they're what let you compute percentiles at all.

## The cardinality trap: why metrics blow up

Metrics get powerful when you attach **labels** (dimensions) — tag a metric by endpoint, status code, region, so you can slice it ("error rate *for the checkout endpoint* in *us-east*"). But this is also metrics' main danger: **cardinality**. Each unique combination of label values creates a *separate* time series, and the count multiplies:

```text
requests{endpoint, status, region}
  10 endpoints × 20 statuses × 5 regions = 1,000 time series   ← fine
  ...add user_id (1,000,000 users) → 1,000,000,000 time series ← catastrophe
```

The killer mistake is putting **high-cardinality values in labels** — user IDs, request IDs, email addresses, full URLs with parameters. Each unique value spawns a new time series, and unbounded label values (like a user ID) create effectively infinite series, exploding storage and cost and often crippling the metrics system. The rule: **labels must be low-cardinality** — bounded sets like endpoint, status class, region, not unbounded identifiers. High-cardinality data (which request, which user) belongs in *logs and traces*, not metric labels. Cardinality is the number one way teams accidentally make their metrics bill (and their metrics database) explode.

## What to measure: RED and USE

Rather than measuring randomly, two well-known frameworks tell you *which* metrics matter:

- **The RED method** (for **services / request-driven** systems) — for each service, track:
  - **Rate** — requests per second.
  - **Errors** — failed requests per second.
  - **Duration** — latency distribution (percentiles!).
  These three tell you almost everything about a service's health from the *user's* perspective, and they're the default starting set for any request-handling service.

- **The USE method** (for **resources** like CPU, memory, disks, queues) — for each resource, track:
  - **Utilization** — how busy it is (% used).
  - **Saturation** — how much extra work is queued/waiting.
  - **Errors** — error count.
  This catches resource exhaustion (a saturated disk, a full queue) before it takes the service down.

Together: use RED for your services (the request path users experience) and USE for the resources underneath them. Starting from these frameworks means you measure the things that actually indicate health, rather than a random pile of metrics that look busy but don't tell you when users are hurting.

## Using metrics well

- **Pick the right type** — counters for accumulating totals (read as rates), gauges for current levels, histograms for distributions (latency, sizes).
- **Always use percentiles for latency** (p50/p95/p99), never averages — the tail is where users suffer and averages hide it.
- **Keep label cardinality low** — bounded dimensions only; never user/request IDs in labels (those go in logs/traces).
- **Instrument with RED (services) and USE (resources)** as your baseline, then add domain-specific metrics.
- **Remember metrics detect, they don't explain** — a metric tells you *that* and *how much*; pivot to traces and logs for *where* and *why*.

Metrics are the efficient front line of observability — cheap, fast, and perfect for detection and alerting. But when a metric tells you something's wrong, you need the granular story, which is the next pillar: logs.

## Key takeaways

- A metric is an aggregated numerical time series; aggregation makes metrics cheap, fast, and ideal for detection and trends — at the cost of lost detail (they tell you *that* and *how much*, not *what* or *why*).
- Use the right type: counters (ever-increasing, read as rates), gauges (current up/down levels), histograms (distributions, enabling percentiles) — the wrong type gives misleading dashboards.
- Never measure latency with averages — averages hide the tail; use percentiles (p50/p95/p99) because at scale the p99 is many real, often high-value, unhappy users, and histograms are what make percentiles possible.
- Beware cardinality: each unique label-value combination is a separate time series, so high-cardinality labels (user/request IDs, full URLs) explode storage and cost — keep labels low-cardinality and put per-request/per-user detail in logs and traces.
- Measure what matters with RED (Rate, Errors, Duration for services) and USE (Utilization, Saturation, Errors for resources) as your baseline, and remember metrics detect while traces/logs explain.

## Further reading

- [What observability is (previous post)](/blog/posts/observ-01-what-is-observability.html)
- [Prometheus — metric types](https://prometheus.io/docs/concepts/metric_types/)
- [Google SRE Book — monitoring distributed systems](https://sre.google/sre-book/monitoring-distributed-systems/)
