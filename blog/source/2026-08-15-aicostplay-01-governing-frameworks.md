# The Four Governing Frameworks

*Before any tactic, know the map. Four cloud and industry frameworks now govern AI cost — AWS, Azure, Google, and the FinOps Foundation — and they converge more than they differ. Every specific lever in this playbook sits underneath one of them, so starting with the constitutional documents is what turns a bag of cost tricks into a coherent discipline.*

This is a detailed, vendor-grounded companion to the [AI Cost Optimization](/blog/series/ai-cost-optimization/) series — where that series reasons in durable principles, this playbook works through the concrete levers the major vendors document and measure. A note on numbers throughout, borrowed from the honest framing every vendor uses: **every percentage quoted is the vendor's own measured or advertised figure on the vendor's own benchmark. They are directional, not guarantees — measure on your own workload before committing.** Anthropic states this explicitly about its own numbers, and the same caution applies to AWS, Google, and Microsoft figures. With that framing set, this first post covers the four frameworks that govern everything else.

## Why start with frameworks

It's tempting to jump straight to "how do I cut my bill." But the tactics only cohere if you know which principle they serve — otherwise you optimize randomly, miss whole categories, and can't explain your choices. The major cloud vendors and the FinOps Foundation have each published a cost-optimization framework, and they function as the *constitutional* layer: broad design principles under which every specific lever (caching, batching, model selection, commitments) is a tactic. Learn the four, and the rest of the playbook organizes itself.

The reassuring finding: **they converge.** Where AWS and Azure differ, it's emphasis, not substance. So you're not choosing one framework over another — you're learning one shared model with four vendor accents.

## The four frameworks

| Framework | What it gives you |
|---|---|
| **AWS Well-Architected — Cost Optimization pillar** | Five design principles; the original and most-copied model. |
| **AWS Well-Architected — Generative AI Lens** | The only vendor framework that treats GenAI cost as its own pillar (its GENCOST practices). |
| **Azure Well-Architected — Cost Optimization** | Five design principles plus a design-review checklist you can run as a gate. |
| **Google Cloud Well-Architected — Cost Optimization + AI/ML perspective** | Business-value framing; its AI/ML perspective is a strong MLOps-cost source. |
| **FinOps Foundation — FinOps for AI** | The vendor-neutral operating model; treats AI as a first-class cost domain. |

The standout is the **AWS Generative AI Lens** — it's the only major vendor framework that carves out *GenAI cost* as its own set of practices (the GENCOST01–05 practices this playbook keeps returning to), rather than folding it into general cloud cost. That's why AWS's material is the most specific about *inference* cost, and why several later posts map directly onto its GENCOST practices.

## The design principles converge

Lay the AWS and Azure cost principles side by side and the convergence is obvious — the same ideas in different words:

| AWS (Cost Optimization pillar) | Azure (Cost Optimization pillar) |
|---|---|
| Implement Cloud Financial Management | Develop cost-management discipline |
| Adopt a consumption model | Design with a cost-efficiency mindset |
| Measure overall efficiency | Design for usage optimization |
| Stop spending on undifferentiated heavy lifting | Design for rate optimization |
| Analyze and attribute expenditure | Monitor and optimize over time |

These aren't five different philosophies twice — they're one shared model: manage cost as a discipline, pay only for what you use, measure efficiency, don't pay for undifferentiated work, and attribute and monitor spend over time. Internalizing these five ideas gives you the lens to place every tactic: caching and batching are "adopt a consumption model" and "rate optimization"; model selection is "measure overall efficiency"; cost attribution is "analyze and attribute expenditure."

**Google's cost pillar adds two framings** the other two under-emphasize, and they're worth adopting explicitly:

- **Align cloud spending with business value** — optimize toward value delivered, not just lowest cost. The cheapest system that fails the business is not optimized.
- **Foster a culture of cost awareness** — cost decisions belong to the engineers making them, not to a central team that reports after the fact. This is the cultural half of cost optimization, and it's the one most teams neglect.

That second point — cost awareness as an engineering-culture property, not a finance-team afterthought — is the through-line that makes the FinOps framework matter.

## Why AI cost is its own discipline

The FinOps Foundation's position is the most important framing for this playbook: **AI spend is different enough to warrant its own treatment.** The reasons are specific and worth holding, because they explain why general cloud-cost habits are necessary but not sufficient for AI:

- **Token-based pricing** — AI is billed per token, a unit most FinOps practice wasn't built around, with cost driven by prompt and output sizes rather than provisioned resources.
- **Volatile, experimental consumption** — AI workloads are often experimental with unpredictable, spiky usage, unlike the steadier consumption of traditional cloud services.
- **A fragmented, multi-vendor landscape** — cost lives across many model providers and platforms, harder to see and attribute than a single cloud bill.
- **GPU/TPU scarcity forcing commitments against uncertain forecasts** — scarce accelerators push you to commit capacity ahead of demand you can't yet forecast well — a genuinely hard planning problem.

And a non-technical one the Foundation flags pointedly: **the low barrier to "AI developer" means people with no FinOps background are now provisioning spend.** Anyone can call an API and run up a bill; the people making cost decisions often have no cost-management training. That's precisely why cost awareness has to be built into engineering culture (Google's point) and why AI needs its own explicit cost discipline rather than being left to general habits.

## How the playbook maps onto the frameworks

Everything ahead sits under these frameworks, and it helps to see the map:

- **Inference levers** (caching, batching, token hygiene, model selection, effort tuning, budgets, commitments) — these are mostly the AWS Generative AI Lens's GENCOST practices made concrete, under "adopt a consumption model" and "measure overall efficiency."
- **Cloud infrastructure fundamentals** — the non-AI layer, under the three cloud cost pillars' rate/usage/waste principles.
- **Measurement and unit economics** — "measure overall efficiency" and "analyze and attribute expenditure," plus FinOps's operating model.
- **Culture and attribution** — Google's "foster a culture of cost awareness" and FinOps's whole premise.

So the playbook isn't a random list — it's the four frameworks' principles, instantiated as specific, measured levers. The next post starts with the single largest of those levers, the one every vendor agrees on: prompt caching.

## Key takeaways

- Four frameworks govern AI cost — AWS Well-Architected Cost pillar, AWS Generative AI Lens, Azure Well-Architected Cost, Google Cloud Well-Architected Cost + AI/ML perspective, and FinOps for AI — and they converge, so you learn one shared model with four accents rather than choosing between them.
- The AWS Generative AI Lens is unique in treating GenAI cost as its own pillar (its GENCOST practices), which is why AWS is the most specific about inference cost and why later posts map onto those practices.
- The design principles are one shared model: manage cost as a discipline, adopt a consumption model, measure efficiency, stop paying for undifferentiated work, and attribute/monitor spend — the lens for placing every tactic.
- Google adds two under-emphasized framings worth adopting: align spending with business value (not just lowest cost) and foster a culture of cost awareness (cost decisions belong to engineers, not a central team reporting after the fact).
- AI cost warrants its own discipline (FinOps for AI) because of token-based pricing, volatile experimental consumption, a fragmented multi-vendor landscape, GPU/TPU scarcity forcing commitments against uncertain forecasts, and the low barrier that puts spend in the hands of people without FinOps background.

## Further reading

- [AWS Well-Architected — Cost Optimization pillar](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html)
- [FinOps Foundation](https://www.finops.org/)
- [AI Cost Optimization series — the principle-level companion](/blog/series/ai-cost-optimization/)
