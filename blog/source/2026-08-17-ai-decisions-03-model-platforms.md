# Choosing a Model Platform: Bedrock vs watsonx vs NVIDIA NIM vs Vertex

*The model platform decision is usually decided before you compare models at all — by which cloud you're already on, what governance you need, and whether you're renting inference or running it — and getting that framing right matters more than any benchmark.*

Amazon Bedrock, IBM watsonx, NVIDIA NIM, and Google Vertex AI are the platforms teams use to actually run foundation models in production. They overlap enough to be confusing and differ enough that the wrong choice is costly. This third post in the AI Architecture Decisions series compares them on durable axes rather than a model-of-the-week leaderboard. (I've written deep series on Bedrock, watsonx, and NVIDIA's stack; this is the chooser.)

## The framing that decides most of it

Before comparing features, notice what usually settles this decision: **your existing cloud and data gravity.** These platforms are each embedded in an ecosystem, and moving data and workloads across clouds is expensive and slow. If your data and infrastructure live in AWS, Bedrock starts with a large, legitimate advantage; on Google Cloud, Vertex does; in an IBM or heavily-regulated enterprise context, watsonx does. Choosing a platform in a different cloud than your data means paying egress, latency, and integration costs on every call, forever. So the honest first question is not "which has the best models?" but "which fits where my data and team already are?"

## The four, by character

Each platform has a distinct center of gravity:

- **Amazon Bedrock** — a managed, multi-model API on AWS: access to a range of foundation models from multiple providers behind one API, with AWS-native integration, knowledge bases, guardrails, and IAM. Its strength is being the AWS-native way to consume many models without running infrastructure. (See [Amazon Bedrock in Go](/blog/series/amazon-bedrock-in-go/).)
- **Google Vertex AI** — Google Cloud's end-to-end ML/AI platform: Google's own models plus a model garden, tightly integrated with BigQuery, Vertex Search, and the GCP data stack. Strong when your data and analytics already live in Google Cloud.
- **IBM watsonx** — an enterprise/governance-forward platform: IBM's Granite models plus others, paired with watsonx.governance and Granite Guardian, aimed at regulated industries needing auditability, governance, and on-prem/hybrid options. Its differentiator is governance and enterprise fit, not raw model novelty. (See [IBM watsonx in Python](/blog/series/ibm-watsonx-in-python/).)
- **NVIDIA NIM** — inference *microservices*: containerized, optimized model-serving you run on NVIDIA GPUs (in your cloud, on-prem, or hybrid). It's a different category — not a managed API but a way to *self-host* optimized inference with control over where models run. Strong when you need performance, data residency, or to run open models on your own hardware. (See [NVIDIA AI Stack in Python](/blog/series/nvidia-ai-stack-in-python/).)

The key distinction: Bedrock, Vertex, and watsonx are largely **managed platforms you consume**; NIM is **infrastructure you run**. That maps onto the managed-vs-self-host decision (its own post in this series) and often reframes the whole comparison — NIM competes less with the others and more with "do we self-host at all?"

## The deciding axes

- **Ecosystem/data gravity** — as above, usually dominant. Match the platform to where your data and team already are.
- **Governance and compliance** — if you're in a regulated industry needing auditability, model governance, and hybrid/on-prem deployment, watsonx is built for exactly that, and NIM's self-hosting gives data-residency control. Bedrock and Vertex have governance features but within their cloud's model.
- **Control vs convenience** — managed platforms (Bedrock/Vertex/watsonx) minimize operational burden; NIM maximizes control (which models, where they run, how they're optimized) at the cost of running GPU infrastructure.
- **Model choice** — all offer multiple models; don't pick on today's specific model rankings, which change monthly. Pick on the platform, and keep the *model* swappable within it (the production-roadmap principle), so a better model next quarter is a config change.
- **Cost model** — managed platforms are largely pay-per-token opex; self-hosting via NIM is fixed GPU cost with low marginal cost, which pays off only at high, steady utilization (the fixed-vs-marginal shape from post 1).

## Don't decide on benchmarks or model hype

The trap unique to this decision: choosing a platform because it has "the best model" this month. Model leadership rotates fast, all major platforms offer strong models, and you should keep the model swappable regardless — so model rankings are the *weakest* basis for a platform choice, not the strongest. Decide on the durable factors (ecosystem fit, governance, control, cost model, operational burden), validate quality on *your* eval set, and treat which specific model you call as a decision you'll revisit often and cheaply.

## Pick this when

- **Amazon Bedrock** — your stack is on AWS and you want a managed, multi-model API without running inference infrastructure.
- **Google Vertex AI** — your data and analytics live in Google Cloud and you want tight integration with the GCP data stack.
- **IBM watsonx** — you're in a regulated/enterprise setting where governance, auditability, and hybrid/on-prem deployment are first-order needs.
- **NVIDIA NIM** — you need to *self-host* optimized inference for performance, data residency, or open-model control, and have (or want) the GPU/ops capability — really a managed-vs-self-host decision.

## Key takeaways

- The model-platform choice is mostly decided by existing cloud and data gravity: match the platform to where your data and team already are, or pay egress/latency/integration costs forever.
- Bedrock (AWS-native managed multi-model API), Vertex (GCP end-to-end, data-stack integrated), and watsonx (enterprise/governance-forward, hybrid) are platforms you *consume*; NVIDIA NIM is optimized inference you *run*.
- Decide on durable axes — ecosystem fit, governance/compliance, control vs operational burden, and cost model (opex per-token vs fixed GPU) — not on this month's model rankings.
- Keep the specific model swappable within whichever platform you choose; model leadership rotates, so it's the weakest basis for the decision.
- watsonx for regulated governance, Bedrock for AWS, Vertex for GCP, NIM when you genuinely need to self-host optimized inference.

## Further reading

- [Amazon Bedrock in Go series](/blog/series/amazon-bedrock-in-go/)
- [IBM watsonx in Python series](/blog/series/ibm-watsonx-in-python/)
- [NVIDIA AI Stack in Python series](/blog/series/nvidia-ai-stack-in-python/)
