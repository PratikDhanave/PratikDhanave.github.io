# Scheduling and Resources

*Kubernetes has to answer a question every time a pod is created: which machine should run it? The scheduler answers it, and the quality of that answer depends entirely on information you provide — resource requests and limits. Get those right and the cluster packs efficiently and stays stable; get them wrong and you get waste, evictions, and mysterious outages.*

The controllers create pods; something must decide *which node* each pod runs on. That's the **scheduler**, and its decisions hinge on **resource requests and limits** you declare. This post covers how scheduling works, requests vs limits (a crucial and often-misunderstood distinction), quality of service and eviction, and autoscaling. It's how Kubernetes places pods and manages the cluster's finite resources — and where small configuration mistakes cause real production problems.

## The scheduler: placing pods

When a controller creates a pod, the pod initially has no node — it's *Pending*. The **scheduler** watches for unscheduled pods and assigns each to a suitable node, via a two-step process:

- **Filtering** — eliminate nodes that *can't* run the pod: nodes without enough free resources (based on the pod's requests, below), nodes that don't match the pod's constraints (node selectors, affinity, taints/tolerations), etc. This yields the set of *feasible* nodes.
- **Scoring** — rank the feasible nodes by desirability (spreading pods for resilience, packing for efficiency, honoring affinity preferences) and pick the best. The pod is then bound to that node, and the node's kubelet runs it.

```text
Pending pod → scheduler:
   filter feasible nodes (enough resources? constraints met?)
   → score them (spread / pack / affinity)
   → bind pod to the best node → kubelet runs it
```

The critical input to filtering is the pod's **resource requests** — the scheduler can only place a pod on a node with enough *requested* resources free. This is why requests matter so much: they're how the scheduler knows what a pod needs and what a node has left. You can also *influence* placement with node selectors/affinity (run on nodes with certain labels — e.g. GPU nodes), taints and tolerations (reserve nodes for certain workloads), and pod affinity/anti-affinity (co-locate or spread pods). But the foundation is resources, which brings us to the most important and most misunderstood concept: requests vs limits.

## Requests vs limits: the crucial distinction

Every container can declare two things for CPU and memory, and confusing them causes real problems:

- **Request** — how much of a resource the container is *guaranteed* / needs. The scheduler uses requests to *place* the pod (it finds a node with that much free) and *reserves* it. A request is "this container needs at least this much."
- **Limit** — the *maximum* a container may use. The container is *capped* at its limit (enforced by cgroups — the containers post). A limit is "this container may use at most this much."

```text
request: guaranteed/reserved amount, used for SCHEDULING (find a node with this free)
limit:   maximum allowed, ENFORCED at runtime (cgroups cap the container)
```

The distinction matters, and the two resources behave *differently* at their limits — a key gotcha:

- **CPU is compressible** — exceeding the CPU limit *throttles* the container (it's slowed, not killed). Hitting CPU limit → the app runs slower.
- **Memory is not compressible** — exceeding the memory limit gets the container **OOM-killed** (terminated). Hitting memory limit → the container is killed and restarted.

This is why setting these wrong causes outages: too-low a memory limit → your container gets OOM-killed under load (a mysterious crash); too-low a CPU limit → your app is throttled and slow; no requests → the scheduler can't place pods well and nodes get overcommitted; requests far above actual use → wasted, reserved-but-idle capacity (paying for resources nobody uses). **Setting requests and limits correctly** — requests near actual typical usage (so scheduling and packing are accurate), limits high enough to handle spikes without OOM-kills — is one of the highest-impact Kubernetes tuning tasks, and getting it wrong is a leading cause of both waste and instability.

## Quality of service and eviction

Requests and limits also determine a pod's **Quality of Service (QoS) class**, which decides who gets **evicted** when a node runs low on resources (memory pressure):

- **Guaranteed** — requests == limits for all resources. Highest priority; evicted last. For critical workloads.
- **Burstable** — requests set but lower than limits (can burst above request up to limit). Medium priority.
- **BestEffort** — no requests or limits set. Lowest priority; **evicted first** when the node is under pressure.

When a node runs out of memory, Kubernetes *evicts* pods to reclaim resources, and it evicts *BestEffort first, then Burstable, protecting Guaranteed*. This is a crucial practical consequence: **a pod with no resource requests (BestEffort) is the first to be killed under pressure** — so critical workloads should set requests/limits (Burstable or Guaranteed) to avoid being evicted first. This ties directly to the previous point: setting requests/limits isn't just about scheduling and OOM-kills, it also determines your pod's survival priority when a node is stressed. Not setting them means your pod is both poorly scheduled *and* first to die — which is why "always set resource requests and limits on production workloads" is standard advice.

## Autoscaling: adjusting to load

Beyond placing a fixed set of pods, Kubernetes can *automatically adjust* capacity to load — the reconciliation idea applied to scale:

- **Horizontal Pod Autoscaler (HPA)** — automatically adjusts the *number of pod replicas* based on observed metrics (CPU, memory, or custom metrics like queue length). Load rises → HPA adds replicas; load falls → it removes them. This is auto-scaling your application horizontally, and it *depends on resource requests* (it scales based on utilization *relative to requests*), reinforcing why requests matter.
- **Vertical Pod Autoscaler (VPA)** — adjusts the *requests/limits* of pods (making them bigger/smaller) based on actual usage — helping right-size resources automatically (addressing the "set requests correctly" problem).
- **Cluster Autoscaler** — adjusts the *number of nodes*: when pods can't be scheduled for lack of node capacity, it adds nodes; when nodes are underused, it removes them. This scales the *cluster itself* to fit the workload.

Together: HPA scales pods to load, Cluster Autoscaler scales nodes to fit the pods, and VPA right-sizes pod resources — so the cluster automatically adapts capacity to demand (and cost, connecting to the FinOps theme: scale down when idle). Autoscaling is the reconciliation model applied to *capacity*: declare a target (e.g. keep CPU utilization ~60%), and the autoscaler continuously adjusts replicas/nodes to hit it.

## Scheduling and resources, in practice

The takeaway: the scheduler places each pod on a suitable node by filtering (feasible nodes, based on resource *requests* and constraints) and scoring (best choice), so accurate requests are what make placement work. **Requests** (guaranteed, used for scheduling) and **limits** (maximum, cgroup-enforced) are the crucial, often-misunderstood distinction — and getting them wrong causes real problems: too-low memory limits OOM-kill your app, too-low CPU limits throttle it, missing requests break scheduling and make your pod BestEffort (evicted first under pressure), and inflated requests waste money. Setting them correctly (and using autoscaling — HPA for pods, Cluster Autoscaler for nodes, VPA for right-sizing) is how the cluster runs efficiently and stably. This is where much Kubernetes operational pain — and its resolution — lives. The final post covers extending and operating Kubernetes in production.

## Key takeaways

- The scheduler places each Pending pod on a node in two steps: filtering (eliminate nodes that can't fit the pod based on its resource requests and constraints) and scoring (rank feasible nodes by spread/pack/affinity and pick the best) — so resource requests are the critical input that makes placement work.
- Requests vs limits is the crucial distinction: a request is the guaranteed/reserved amount used for scheduling; a limit is the enforced maximum (cgroup-capped) — and they behave differently at the limit: CPU is compressible (throttled) while memory is not (OOM-killed).
- Setting these wrong causes real problems: too-low memory limits → OOM kills (mysterious crashes), too-low CPU limits → throttling/slowness, missing requests → poor scheduling and overcommit, inflated requests → wasted reserved capacity — correct requests/limits are one of the highest-impact tuning tasks.
- QoS class (Guaranteed = requests==limits, Burstable = requests<limits, BestEffort = none) determines eviction order under node pressure: BestEffort is evicted first — so a pod with no requests is both poorly scheduled and first to die; always set requests/limits on production workloads.
- Autoscaling applies reconciliation to capacity: HPA scales pod replicas to load (based on utilization vs requests), Cluster Autoscaler scales nodes to fit pods, and VPA right-sizes pod requests/limits — together the cluster adapts capacity (and cost) to demand automatically.

## Further reading

- [Configuration and state (previous post)](/blog/posts/k8s-06-configuration-and-state.html)
- [Kubernetes documentation — managing resources for containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [The AI Cost Optimization Playbook — right-sizing and autoscaling for cost](/blog/series/the-ai-cost-optimization-playbook/)
