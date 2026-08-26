# What Problem Does Kubernetes Solve?

*Kubernetes is famously complex, and most explanations start with its parts — pods, deployments, services — which is exactly backwards. Start with the problem: you have containers, you have many machines, and you need something to run the right containers on the right machines and keep them running as things fail. Kubernetes is a control loop for that, and once you see it that way, the complexity becomes comprehensible.*

Kubernetes has a reputation for being bewilderingly complex, and it earns it if you learn it as a pile of features. This series learns it *from first principles* — starting with the problem it solves, then containers, then Kubernetes's objects as answers to specific needs. This first post is about the *why*: what problem Kubernetes exists to solve, and its core idea (declarative desired state plus continuous reconciliation) that every later concept is an instance of. Get the why, and the parts stop being arbitrary.

## The problem: containers at scale

Assume you already have **containers** (the next post explains what they really are). A container packages an application with its dependencies into a portable, isolated unit that runs the same everywhere. Containers solved "it works on my machine" — but they created a new problem: **running many containers across many machines, reliably.** Once you have more than a few containers and more than one server, hard questions pile up:

- **Placement** — which machine should each container run on? How do you use your machines efficiently?
- **Failure recovery** — a container crashes, or a whole machine dies. Something must notice and restart/reschedule the affected containers, automatically.
- **Scaling** — traffic spikes; you need more copies of a container, spread across machines. Traffic drops; you scale down.
- **Networking** — containers need to find and talk to each other, even as they move between machines and their addresses change.
- **Rollouts** — deploying a new version without downtime, and rolling back if it's broken.
- **Configuration and secrets** — getting config and credentials to containers safely.

Doing all this by hand — SSHing to machines, starting containers, restarting them when they die, updating a load balancer as things move — is impossible at any real scale. You need a system that *manages* containers across a fleet of machines automatically. That system is a **container orchestrator**, and Kubernetes is the dominant one. The problem Kubernetes solves, in one line: **run containers across a cluster of machines, and keep them running correctly as the world changes.**

## The core idea: declarative desired state + reconciliation

Here is the single most important concept in Kubernetes, and the one that makes everything else fall into place. Kubernetes is built on **declarative desired state and continuous reconciliation**:

- **You declare the desired state** — you tell Kubernetes *what you want*, not how to achieve it: "run 3 copies of this container, exposed on this port, with this config." You describe the destination.
- **Kubernetes continuously reconciles actual state toward desired state** — it constantly compares what's *actually* running against what you *declared*, and takes action to close any gap. If you want 3 copies and only 2 are running (one crashed), it starts a third. If a machine dies, it reschedules its containers elsewhere. If you change the desired state (want 5 copies now), it creates two more.

```text
You declare:   "I want 3 replicas of this app"
Kubernetes:    observes actual (2 running) → acts (start 1 more) → observes → acts → ...
               continuously, forever, keeping actual == desired despite failures/changes
```

This is a **control loop** (like a thermostat: you set the desired temperature, and it continuously acts to reach and maintain it, regardless of the weather). Kubernetes is a control loop for your containers: you set the desired state, and it works continuously to make reality match, forever, adapting to failures and changes. This is *why* Kubernetes can self-heal (restart crashed containers), scale, and roll out changes — they're all just "change the desired state (or the world changes), and reconciliation makes actual match desired." Every Kubernetes object and behavior you'll learn is an instance of this one pattern. If you internalize declarative-desired-state-plus-reconciliation, the rest of Kubernetes is details.

This is also the **GitOps** connection (from the platform-engineering series): GitOps stores the desired state in git, and Kubernetes reconciles to it — GitOps is desired-state-plus-reconciliation extended to git as the source of truth.

## The shape of a cluster

To make the reconciliation idea concrete, know the basic anatomy of a Kubernetes cluster:

```text
Control plane (the brain — runs the reconciliation):
  - API server   — the front door; you submit desired state here; everything goes through it
  - etcd         — the datastore holding the cluster's desired + actual state
  - scheduler    — decides which node each pod runs on
  - controllers  — the reconciliation loops (keep actual == desired)

Worker nodes (the muscle — run your containers):
  - kubelet      — the agent on each node that runs and reports on containers
  - container runtime — actually runs the containers
  - kube-proxy   — handles networking to the containers
```

- **The control plane** is the brain: you send your desired state to the **API server**, it's stored in **etcd**, the **scheduler** decides placement, and **controllers** run the reconciliation loops that make it happen. This is where "keep actual == desired" lives.
- **Worker nodes** are the machines that actually run your containers, each with a **kubelet** (the node agent) that runs containers and reports status back.

You interact with the cluster by submitting *desired state* to the API server (via `kubectl` or GitOps), and the control plane's controllers make it real on the nodes. You don't tell nodes what to do directly; you declare what you want, and the system figures out placement and execution. This architecture *is* the reconciliation model made physical — a brain (control plane) continuously steering the muscle (nodes) toward your declared state.

## Why (and why not) Kubernetes

Kubernetes is powerful but genuinely complex, so it's worth being honest about fit (the platform-engineering and architecture-decisions themes apply):

- **Kubernetes shines when** you're running many containerized services across multiple machines and need automated scaling, self-healing, rollouts, and a consistent deployment model — the container-orchestration problem it was built for. At real scale, its automation is transformative, and it's become the industry-standard substrate for cloud-native systems.
- **Kubernetes is overkill when** you have a simple app, a few containers, or low scale — its complexity outweighs its benefits, and simpler options (a managed container service, a PaaS, or just a VM) may serve better. Adopting Kubernetes for a small system is a common mistake: you pay its steep operational and cognitive cost without needing its scale-management power.
- **Managed Kubernetes** (GKE, EKS, AKS) removes much of the operational burden of running the control plane yourself, which is why most teams use managed offerings rather than self-hosting — you get the orchestration without operating the brain.

The honest framing: Kubernetes solves a *real and hard* problem (containers at scale) with a powerful, general model (declarative reconciliation), but that generality is complexity you should only take on when the problem warrants it. This series teaches Kubernetes so that *when* you need it, it's comprehensible rather than mysterious. The next post goes underneath Kubernetes to what it orchestrates: containers, from first principles.

## Key takeaways

- Containers solved "works on my machine" but created a new problem: running many containers across many machines reliably — placement, failure recovery, scaling, networking, rollouts, config — which is impossible to do by hand at scale and needs a container orchestrator; Kubernetes is the dominant one.
- The core idea is declarative desired state plus continuous reconciliation: you declare *what you want* (3 replicas, this config), and Kubernetes continuously compares actual to desired and acts to close the gap — a control loop (like a thermostat) that runs forever, adapting to failures and changes.
- This one pattern explains everything: self-healing (restart crashed containers), scaling, and rollouts are all "change desired state (or the world changes) → reconciliation makes actual match" — internalize it and the rest of Kubernetes is details; it's also the basis of GitOps (desired state in git).
- A cluster is a control plane (the brain: API server as the front door, etcd for state, scheduler for placement, controllers running reconciliation loops) plus worker nodes (the muscle: kubelet + runtime + kube-proxy running your containers) — you submit desired state to the API server and the control plane makes it real.
- Kubernetes shines for many containerized services at scale needing automation, but is overkill for simple/small systems (a common mistake) — and managed offerings (GKE/EKS/AKS) remove the burden of operating the control plane; take on its complexity only when the problem warrants it.

## Further reading

- [Kubernetes documentation — overview](https://kubernetes.io/docs/concepts/overview/)
- [Platform Engineering series — where Kubernetes fits](/blog/series/platform-engineering/)
- [Distributed Systems from First Principles — reconciliation and desired state](/blog/series/distributed-systems-from-first-principles/)
