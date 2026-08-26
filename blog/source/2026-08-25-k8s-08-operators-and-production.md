# Operators and Kubernetes in Production

*Kubernetes's deepest idea isn't its built-in objects — it's that the reconciliation model is extensible. You can teach Kubernetes new concepts and automate operating them, which is what operators do. This closing post covers that extension model, the realities of running Kubernetes in production, and the honest verdict on when its power is worth its complexity.*

The series built Kubernetes from the reconciliation core up through pods, controllers, networking, config/state, and scheduling. This final post covers two things: the **extension model** (Custom Resources and operators — how Kubernetes grows beyond its built-in objects) and the **production realities** of running it. It closes with the honest fit question the series opened with. Understanding that Kubernetes is *extensible* — and what operating it actually demands — completes the picture.

## The extension model: Custom Resources

Kubernetes's built-in objects (pods, deployments, services…) are not a fixed set — the API is *extensible*. **Custom Resource Definitions (CRDs)** let you add your *own* object types to Kubernetes, which the API server then treats like any built-in resource:

- **A CRD defines a new kind of object** — e.g. a `Database`, a `Certificate`, a `KafkaCluster` — with its own schema. Once defined, you can create instances of it declaratively (`kind: Database`) via the same API, `kubectl`, and GitOps as built-in objects.
- **Custom resources declare desired state for your concept** — just as a Deployment declares "3 replicas," a custom `Database` resource could declare "a Postgres database, version 15, 100Gi, with backups." You've extended the *vocabulary* of desired state Kubernetes understands.

But a CRD alone is just *data* — declaring `kind: Database` doesn't create a database. Something must *reconcile* it. That something is a **controller for your custom resource** — which combined with the CRD is an **operator**.

## Operators: automating operations

An **operator** is a custom controller that reconciles a custom resource — encoding *operational knowledge* about running a specific application into software. It's the reconciliation model (post four) applied to *your* concept, automating the work a human operator would otherwise do:

```text
CRD:       defines "kind: Database" (the new desired-state vocabulary)
Operator:  a controller that watches Database resources and reconciles them —
           provisions the DB, configures replication, takes backups, handles failover,
           does upgrades — the operational tasks a human DBA would do, automated
```

- **Operators encode operational expertise** — the "how to run this system" knowledge (provisioning, scaling, backup, recovery, upgrades for a database, a message queue, a monitoring stack) is captured in the operator's reconciliation logic. You declare the desired state (`kind: Database, version: 15`), and the operator does the operational work to achieve and maintain it — continuously, like any controller.
- **This is powerful** — it means complex stateful systems can be run on Kubernetes *declaratively*: you declare what you want, and the operator (built by the system's experts) handles the intricate operations. Many databases, message brokers, and platforms ship operators so you can run them on Kubernetes with the operational knowledge built in.

The operator pattern is Kubernetes's deepest idea realized: because the platform is *reconciliation over declarative resources*, and that's *extensible*, you can teach Kubernetes to manage *anything* by defining a resource and writing a controller. Kubernetes becomes not just a container orchestrator but a *platform for building control planes* — which is why so much cloud-native software is built as operators. Understanding CRDs + operators is understanding that Kubernetes is extensible all the way down: its own built-in controllers and third-party operators are the *same* pattern.

## Kubernetes in production: the realities

Running Kubernetes in production is more than deploying pods; several realities matter (many connecting to earlier series):

- **Security** — Kubernetes has a large attack surface and needs deliberate hardening: **RBAC** (role-based access control — who can do what), **network policies** (which pods can talk to which — micro-segmentation), pod security standards (constraining what containers can do), secrets management (real encryption, from the config post), image scanning, and more. A default cluster is not a secure cluster; security must be configured (the DevSecOps and identity-series lesson).
- **Observability** — you must observe both your workloads *and the cluster itself* (nodes, control plane, resource usage) — metrics, logs, traces (the Observability series). Kubernetes is a distributed system you're operating, so you need to see inside it.
- **Resource management and cost** — right-sizing requests/limits and autoscaling (the scheduling post) directly drive cost; an unoptimized cluster wastes significant money (the FinOps theme). Cost management (utilization, bin-packing, scaling down idle capacity) is a real production discipline.
- **Upgrades and maintenance** — Kubernetes releases regularly, and you must upgrade the control plane and nodes, manage deprecations, and maintain the cluster — ongoing operational work.
- **Reliability of the cluster** — the cluster is critical infrastructure everything runs on, so it needs its own resilience (control-plane HA, node failure handling) — the platform-must-be-reliable point from the platform-engineering series.

This is why **managed Kubernetes** (GKE, EKS, AKS) is the common choice: the cloud provider operates the control plane, handles upgrades, and provides integrations, so you focus on your workloads rather than running the Kubernetes machinery yourself. Self-hosting Kubernetes means taking on all of the above; managed offerings remove much of it. For most teams, managed Kubernetes is the right call — you get the orchestration without operating the orchestrator.

## The honest verdict: when Kubernetes is worth it

Closing the fit question from the first post, honestly:

- **Kubernetes is worth its complexity when** you're running many containerized services at scale, need automated scaling/self-healing/rollouts, want a consistent deployment substrate across environments and clouds, and have (or can adopt) the operational maturity to run it (ideally via managed Kubernetes and a platform team). At that point its power — declarative reconciliation of a whole fleet — is genuinely transformative and hard to replicate otherwise. It's become the industry-standard cloud-native substrate for good reason.
- **Kubernetes is not worth it when** you have a simple app, few services, or modest scale — its complexity (the whole of this series) is a large cost you shouldn't pay without needing its scale-management power. Simpler options — a managed container service (Cloud Run, ECS, App Runner), a PaaS, or even a VM — are often the right, boring choice for small systems. Adopting Kubernetes prematurely is a common, expensive mistake: you get the complexity without the payoff.
- **Even when you use Kubernetes**, hide its complexity from most developers behind a platform (the platform-engineering series): developers should get golden paths and self-service, not raw Kubernetes. Kubernetes is best as the *substrate a platform is built on*, not something every developer wrestles directly.

The balanced framing: Kubernetes solves a real, hard problem with a powerful, extensible model, and it's the standard for cloud-native at scale — but that power is complexity to take on deliberately, ideally managed and platform-abstracted, only when your scale warrants it.

## The series in one arc

Kubernetes, end to end: it exists to solve **containers at scale**, via **declarative desired state plus continuous reconciliation** (post one) — the core idea everything instantiates. It orchestrates **containers** (isolated, constrained processes, not VMs — post two), wrapped in **pods** (co-located, ephemeral units — post three), managed by **controllers** running reconciliation loops (Deployments, StatefulSets, etc. — post four), reached via **Services and Ingress** (stable networking over ephemeral pods — post five), configured and made stateful with **ConfigMaps/Secrets and PersistentVolumes/StatefulSets** (post six), placed and bounded by the **scheduler and resource requests/limits** (post seven), and extended via **CRDs and operators** while operated with real production discipline (this post). The unifying thread is the reconciliation model — declare desired state, and controllers make and keep it real — which, being extensible, turns Kubernetes into a platform for building control planes. Learn it as instances of that one idea, use it (ideally managed and platform-abstracted) when scale warrants, and it becomes comprehensible rather than mysterious.

## Key takeaways

- Kubernetes is extensible: Custom Resource Definitions (CRDs) add your own object types (a `Database`, a `Certificate`) that the API treats like built-ins, extending the vocabulary of declarative desired state — but a CRD alone is just data; something must reconcile it.
- An operator is a custom controller that reconciles a custom resource, encoding operational expertise (provisioning, backup, failover, upgrades) into software — so complex stateful systems run declaratively on Kubernetes; this is the reconciliation model applied to your own concepts, making Kubernetes a platform for building control planes.
- Production Kubernetes demands real discipline: security (RBAC, network policies, pod security, secrets, image scanning — a default cluster isn't secure), observability (workloads *and* the cluster), resource management/cost (right-sizing + autoscaling), upgrades/maintenance, and cluster reliability.
- Managed Kubernetes (GKE/EKS/AKS) is the common choice because the provider operates the control plane, handles upgrades, and integrates services — you get orchestration without operating the orchestrator; self-hosting means taking on all the production realities.
- Kubernetes is worth its complexity for many services at scale needing automation and a consistent substrate (with operational maturity, ideally managed + platform-abstracted), but is overkill for simple/small systems (a common expensive mistake) — and even when used, its complexity should be hidden from most developers behind a platform's golden paths.

## Further reading

- [Scheduling and resources (previous post)](/blog/posts/k8s-07-scheduling-and-resources.html)
- [Kubernetes documentation — operator pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Platform Engineering — hiding Kubernetes behind golden paths](/blog/series/platform-engineering/)
