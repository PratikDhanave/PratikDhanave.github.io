# Controllers and the Reconciliation Loop

*Controllers are where Kubernetes's core idea — declarative desired state plus reconciliation — becomes machinery. A controller is a loop that watches "what you want" versus "what exists" and acts to close the gap, forever. Self-healing, scaling, and zero-downtime rollouts are all just controllers doing that one thing. This is the engine of Kubernetes.*

The first post named declarative-desired-state-plus-reconciliation as Kubernetes's core idea; the pod post noted pods are managed by higher-level objects. This post covers those objects — **controllers** — and the **reconciliation loop** that is Kubernetes's engine. A controller continuously drives actual state toward desired state, and the workload controllers (Deployments, ReplicaSets, and others) are how you actually run applications. Understand controllers and you understand how Kubernetes *does* everything.

## The reconciliation loop

A **controller** is a control loop that watches some part of the cluster's state and works to make *actual* match *desired* — the concrete implementation of the core idea. Every controller runs the same loop, forever:

```text
loop forever:
    observe   — what is the ACTUAL state? (what pods exist, are they healthy?)
    compare   — how does actual differ from DESIRED? (you want 3, there are 2)
    act       — take action to close the gap (create 1 more pod)
    (repeat)
```

- **Observe** — the controller watches the current state via the API server (which pods exist, their health, etc.).
- **Compare** — it computes the difference between actual and the *desired* state you declared.
- **Act** — it takes corrective action to reduce the difference (create/delete pods, update things).
- **Repeat** — continuously, so the system is *always* being driven toward desired, adapting to any change or failure.

This loop is the engine of Kubernetes. It's *level-based*, not edge-based: the controller doesn't react to *events* ("a pod died") so much as continuously compare *state* ("desired 3, actual 2, fix it") — which is more robust, because it self-corrects toward the desired level regardless of what happened or whether it missed an event. This is why Kubernetes is resilient: even if something is missed or the controller restarts, the next loop iteration re-observes actual vs desired and corrects. The reconciliation loop *is* how declarative desired state becomes reality, continuously.

## ReplicaSets: keeping N pods running

The most fundamental workload controller is the **ReplicaSet**, whose job is simple and illustrative: **keep exactly N copies (replicas) of a pod running.** You declare "I want 3 replicas of this pod," and the ReplicaSet's reconciliation loop ensures 3 are always running:

- If a pod crashes or its node dies (actual drops to 2), the ReplicaSet notices (observe → compare) and creates a new pod (act) — this is **self-healing**, and it's just reconciliation.
- If you change desired to 5, the ReplicaSet creates 2 more — this is **scaling**, also just reconciliation.
- If somehow 4 exist when you want 3, it deletes one.

The ReplicaSet is pure "keep actual replica count == desired replica count," forever. This single controller gives you self-healing (crashed/lost pods are replaced) and scaling (change the number) — both falling directly out of the reconciliation loop. You rarely use ReplicaSets directly, though; you use Deployments, which manage ReplicaSets to add rollouts.

## Deployments: rollouts and rollbacks

The **Deployment** is the controller you'll use most for stateless applications. It manages ReplicaSets to provide not just "keep N pods running" but **controlled rollouts and rollbacks** of new versions:

```text
Deployment (desired: version v2, 3 replicas)
  → manages ReplicaSets to roll from v1 to v2 gradually:
     create v2 pods, wait until healthy, remove v1 pods, step by step
     → zero-downtime rolling update; roll back if v2 is unhealthy
```

- **Declarative app management** — you declare the desired state of your app (this image/version, N replicas, this config) in a Deployment, and its controller makes it so.
- **Rolling updates** — when you change the version (new image), the Deployment *gradually* replaces old pods with new ones (create new, verify healthy, remove old, incrementally), so the app updates with **zero downtime** — there are always healthy pods serving. This is a rollout, done by reconciliation toward the new desired state.
- **Rollbacks** — if the new version is broken, you roll back to the previous version, and the Deployment reconciles back to it. Because it keeps the history, rollback is declarative and fast.
- **Self-healing and scaling** — inherited from the ReplicaSets it manages: crashed pods are replaced, and you scale by changing the replica count.

So the Deployment is the practical unit for running a stateless service: declare what you want (version, replicas), and it handles keeping it running, updating it safely, and rolling back — all via reconciliation. The layering is: **Deployment manages ReplicaSets manages Pods** — each a controller reconciling toward desired state, composing into safe, self-healing, updatable application management.

## The other workload controllers

Deployments are for stateless apps; Kubernetes has other workload controllers for other shapes, each a reconciliation loop for a different need:

- **StatefulSet** — for *stateful* applications that need stable identities and stable storage (databases, clustered systems). Unlike a Deployment (interchangeable pods), a StatefulSet gives each pod a stable name and its own persistent storage that survives rescheduling — for workloads where pods aren't interchangeable (the storage post returns to this).
- **DaemonSet** — ensures a copy of a pod runs on *every* node (or a subset) — for node-level agents like log collectors, monitoring agents, or networking components. Reconciliation here means "one pod per node," adjusting as nodes join/leave.
- **Job** — runs a pod (or pods) to *completion* — for batch/one-off tasks (a data migration, a batch computation) that should run once and finish, not run forever. The controller ensures it completes successfully.
- **CronJob** — runs Jobs on a *schedule* — for periodic tasks (nightly reports, scheduled cleanups).

Each is a controller applying the reconciliation loop to a different workload shape: N interchangeable replicas (Deployment), stable-identity replicas (StatefulSet), one-per-node (DaemonSet), run-to-completion (Job), on-a-schedule (CronJob). Choosing the right one is choosing the reconciliation behavior your workload needs — stateless service → Deployment, stateful → StatefulSet, node agent → DaemonSet, batch → Job/CronJob.

## Controllers as the engine

The takeaway: controllers are Kubernetes's engine — each a reconciliation loop (observe → compare → act, forever) that drives actual state toward the desired state you declared, level-based and self-correcting. The workload controllers turn this into application management: ReplicaSets keep N pods running (self-healing + scaling), Deployments add zero-downtime rollouts and rollbacks (the workhorse for stateless apps), and StatefulSets/DaemonSets/Jobs/CronJobs handle stateful, per-node, and batch/scheduled workloads. Everything Kubernetes *does* for your workloads — keep them running, scale them, update them safely, run them on schedule — is a controller reconciling toward desired state. This is the core idea (post one) made into machinery. The next post covers how these ever-changing pods are reached over the network: services.

## Key takeaways

- A controller is a reconciliation loop — observe actual state, compare to desired, act to close the gap, repeat forever — and it's the concrete engine of Kubernetes's declarative-desired-state model; it's level-based (continuously compares state) not edge-based (reacting to events), which makes it robust and self-correcting.
- The ReplicaSet keeps exactly N pod replicas running: replacing crashed/lost pods (self-healing) and adjusting to a changed count (scaling) — both falling directly out of the reconciliation loop.
- The Deployment (the workhorse for stateless apps) manages ReplicaSets to add controlled rolling updates (gradually replace old pods with new, zero downtime) and rollbacks (reconcile back to a previous version), plus inherited self-healing and scaling — you declare version + replicas and it handles the rest.
- The layering is Deployment → ReplicaSet → Pod, each a controller reconciling toward desired state, composing into safe, self-healing, updatable application management.
- Other workload controllers apply reconciliation to other shapes: StatefulSet (stable identity + storage for stateful apps), DaemonSet (one pod per node for agents), Job (run to completion for batch), CronJob (scheduled) — choose the controller whose reconciliation behavior matches your workload.

## Further reading

- [Pods: the atom of Kubernetes (previous post)](/blog/posts/k8s-03-pods.html)
- [Kubernetes documentation — Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [What problem does Kubernetes solve? — the reconciliation core idea](/blog/posts/k8s-01-what-problem-does-kubernetes-solve.html)
