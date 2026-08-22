# Capacity Commitments and Cloud Fundamentals

*The last inference lever is the classic cloud play in AI clothing: commit to capacity for the steady, predictable part of your load and pay less per unit. And underneath all the AI-specific tactics sits the ordinary cloud bill, where most of a mature estate's money actually lives — governed by the same rate, usage, and waste principles for decades.*

Two things here: the eighth inference lever, **capacity commitments** (provisioned throughput), and the **cloud infrastructure fundamentals** that sit beneath all AI-specific optimization. The commitments lever is the AI instance of the classic reserved-capacity trade; the cloud fundamentals are where most mature estates' spend still sits. Figures are vendors' own directional numbers; verify on your workload.

## Capacity commitments: the reserved-capacity play for AI

For steady, predictable, high-volume inference, **commitment pricing beats consumption pricing** — the AI-specific instance of the classic Reserved-Instance play. Instead of paying per token on demand, you commit to (and pay for) a block of capacity, getting a lower effective rate for predictable load:

- **Azure Provisioned Throughput Units (PTUs)** — billed hourly per PTU regardless of tokens consumed. Microsoft's guidance is blunt: "hourly billing isn't appropriate for production deployments" scaled up and down — a reservation-sized deployment is typically cheaper than continuous hourly billing. And PTU sizing is driven by *request shape* — the output-to-input token ratio (output tokens cost more capacity) and your cache rate — not just raw volume. Azure Reservations give significant discounts on committed PTUs.
- **Google Vertex AI Provisioned Throughput** — covers predictable, mission-critical baseload with an availability SLA; a longer-term purchase gives ~26% discount over monthly, and it can be switched across models.
- **AWS Bedrock Provisioned Throughput** — for steady-state workloads where throttling must be avoided, and for serving custom models.

The mechanism and its caveat: commitment pricing trades *flexibility* for a *lower rate*, so it wins only for load that's genuinely steady and predictable enough to keep the committed capacity busy. Committing to capacity you don't use is worse than on-demand — the same fixed-vs-marginal trade as reserved instances (and the [managed-vs-self-host](/blog/posts/ai-decisions-06-managed-vs-selfhost.html) decision). A subtlety specific to AI: because PTU sizing depends on the output-to-input ratio and cache rate, your *other* optimizations (caching, output control) change how much committed capacity you need — the levers interact.

## The pattern all three describe

The three providers converge on one architecture for mixing pricing models, and it's the key takeaway of the commitments lever:

```text
  commitment (provisioned throughput) → the PREDICTABLE baseload
  consumption (on-demand)             → the SPIKY remainder
  batch (50% off)                     → the DEFERRABLE tail
```

**Commit for the predictable baseload, use consumption/on-demand for the spiky remainder, and batch the deferrable tail.** Rather than picking one pricing model, you *segment your workload* by its predictability and latency-tolerance, and apply the cheapest appropriate pricing to each segment: reserved capacity for the steady base you can keep busy, on-demand for unpredictable spikes, and half-price batch for anything that can wait (the batching post). This three-way split is how mature AI estates get the commitment discount *without* over-committing — you only reserve the part you're sure of, and handle variability with on-demand and batch. It directly reflects the FinOps-for-AI challenge from the first post (GPU/TPU scarcity forcing commitments against uncertain forecasts): commit only the baseload you can forecast confidently, and absorb the uncertain part with flexible pricing.

## The cloud layer: where most money still sits

The inference levers are the AI-specific story, but underneath them is the ordinary **cloud infrastructure bill** — and for a mature estate, *most of the money still sits there*, not in inference. This layer is governed by the same three cost pillars (AWS, Azure, Google) covered in the first post, and while it's not AI-specific, ignoring it while optimizing tokens is optimizing the small number. The three areas:

### Rate optimization — pay less per unit

Azure's "design for rate optimization," AWS's "adopt a consumption model":

- **Prepurchase for stable, predictable usage** — Reserved Instances, Savings Plans, Committed Use Discounts (the same commitment logic as provisioned throughput, for compute/storage). Azure adds a point most teams miss: **keep your licensing team informed of projected investment**, because forecasts can influence the organization's whole price sheet, not just your workload.
- **Avoid additional licensing** where possible — hybrid-use rights, preproduction subscription pricing.
- **Deploy to lower-cost regions** — evaluating each environment separately; production may need a specific region, preproduction usually doesn't.
- **Prefer higher density** — fewer resources per workload cuts both unit and management cost (watch the security-boundary tradeoff).
- **Co-locate workloads** to share centrally-managed capacity.

### Usage optimization — use what you bought

Azure's "design for usage optimization," Google's "optimize resource allocation":

- **Use the full capabilities of the SKU you selected** — and conversely, don't select SKUs with features you don't need.
- **Dynamic scaling over pre-provisioning** — autoscale on CPU, memory, *and* job-queue length, with load balancing across replicas.
- **Prefer active-active over active-passive** where you've already paid for the resources — idle disaster-recovery capacity is pure waste that could be absorbing load.
- **Treat SDLC environments differently** — non-production doesn't need to simulate production (different SKUs, instance counts, even logging levels); create preproduction environments on demand and destroy them after.

### Waste elimination

Azure's "monitor and optimize over time":

- **Decommission underutilized, unused, obsolete, or replaceable resources**, and delete unnecessary data on a schedule (Azure Advisor and equivalents surface these automatically).
- **Data tiering** — align storage class to access frequency (hot/cool/cold/archive) with lifecycle policies doing the transitions automatically.
- **Hunt orphaned resources** — unattached disks, idle load balancers, unassociated IPs, stale snapshots — with compliance scans or cost-explorer recommendations on a cadence.

### Governance and visibility

AWS's "implement Cloud Financial Management" and "analyze and attribute expenditure," Azure's "develop cost-management discipline," Google's "foster a culture of cost awareness" — the attribution and culture layer that makes all the above stick.

## Fitting the layers together

The complete cost picture is two layers, both mattering:

- **The AI-specific inference layer** — caching, batching, token hygiene, model selection, effort tuning, budgets, and (this post) capacity commitments — segmented commit/consume/batch by predictability and latency-tolerance.
- **The cloud infrastructure layer** — rate optimization (pay less per unit via commitments and regions), usage optimization (use what you bought via scaling and right-sized SKUs), and waste elimination (decommission, tier, hunt orphans) — where most mature-estate spend actually sits.

Optimizing only one layer misses the other's money: token optimization without cloud hygiene ignores where most spend lives, while cloud hygiene without inference levers ignores the fastest-growing cost. The mature approach does both, under the same governing frameworks, with attribution and cost-aware culture tying them together. The next post covers the measurement discipline that makes all of it real — because none of these levers count until you're measuring the right unit economics.

## Key takeaways

- Capacity commitments (provisioned throughput) beat consumption pricing for steady, predictable, high-volume inference — Azure PTUs (billed per PTU/hour regardless of tokens; sizing driven by output-to-input ratio and cache rate), Google Vertex Provisioned Throughput (~26% for longer commitments, model-switchable, with an SLA), AWS Bedrock Provisioned Throughput — trading flexibility for a lower rate, so only worth it for load you can keep the committed capacity busy.
- The pattern all three describe: commit for the predictable baseload, use consumption/on-demand for the spiky remainder, and batch the deferrable tail — segment the workload by predictability and latency-tolerance and price each segment cheapest, which avoids over-committing against uncertain forecasts.
- Underneath the AI layer sits the ordinary cloud bill, where most of a mature estate's money still lives, governed by the same three cost pillars — ignoring it while optimizing tokens optimizes the small number.
- Cloud fundamentals: rate optimization (prepurchase/reserved, lower-cost regions, higher density, keep licensing informed), usage optimization (full SKU capabilities, dynamic scaling on queue length, active-active over idle DR, treat SDLC environments differently), and waste elimination (decommission, data tiering, hunt orphaned resources).
- The complete picture is both layers — AI inference levers and cloud infrastructure hygiene — under the same governing frameworks with attribution and cost-aware culture; optimizing only one misses the other's money.

## Further reading

- [Effort tuning, budgets, and the max_tokens trap (previous post)](/blog/posts/aicostplay-05-effort-budgets-caps.html)
- [Azure Well-Architected — Cost Optimization](https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/)
- [AI Architecture Decisions: managed vs self-hosting inference](/blog/posts/ai-decisions-06-managed-vs-selfhost.html)
