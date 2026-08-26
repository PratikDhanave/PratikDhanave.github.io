# Configuration and State

*Pods are disposable — destroyed and recreated constantly — which raises two problems: how do you give a pod its configuration without baking it into the image, and how does any data survive a pod's death? ConfigMaps and Secrets answer the first; volumes and StatefulSets answer the second. This is how stateless-by-default Kubernetes handles config and the state it can't avoid.*

Pods are ephemeral (post three), which is fine for stateless apps but forces two questions: **configuration** (how to get config/secrets into pods without hardcoding them) and **state** (how data survives pods being destroyed). This post covers **ConfigMaps** and **Secrets** (externalized configuration), **volumes** (storage that outlives the container), and **StatefulSets/PersistentVolumes** (durable, identity-stable state). It's how Kubernetes handles the config every app needs and the persistent state that ephemeral pods otherwise can't keep.

## Externalizing configuration: ConfigMaps and Secrets

An application needs *configuration* — settings, feature flags, connection strings, credentials. Baking config into the container image is bad (you'd rebuild the image per environment, and can't change config without a new image — violating the build-once-run-anywhere and twelve-factor principles). Kubernetes externalizes config so the *same* image runs in any environment with different config injected:

- **ConfigMap** — holds *non-sensitive* configuration as key-value data (settings, config files, environment values). You define a ConfigMap and inject its values into pods, so config lives outside the image and can differ per environment.
- **Secret** — holds *sensitive* data (passwords, API keys, tokens, certificates). Functionally similar to a ConfigMap but meant for secrets, with additional handling (and it should be encrypted at rest and access-controlled — see the caution below).

Both are injected into pods two ways:

- **As environment variables** — the pod's containers get config values as env vars.
- **As mounted files** — the config is mounted into the container's filesystem as files (useful for config files, certificates).

```text
ConfigMap "app-config" (LOG_LEVEL=info, FEATURE_X=true)
Secret    "db-creds"   (DB_PASSWORD=...)
   → injected into the pod as env vars or mounted files
   → same image, different config per environment (dev/staging/prod)
```

This is the twelve-factor "config in the environment" principle realized: the image is environment-agnostic, and ConfigMaps/Secrets provide the environment-specific config, injected at runtime. It's also why the same Deployment can run in staging and prod with only the ConfigMap/Secret differing.

**A caution on Secrets:** by default, Kubernetes Secrets are only *base64-encoded* (not encrypted) in the datastore unless you enable encryption at rest — so "Secret" doesn't automatically mean "securely encrypted." For real secret security, enable encryption at rest for etcd, lock down access (RBAC), and often use an external secrets manager (a cloud secret store, Vault) integrated with the cluster. Treat Kubernetes Secrets as "the mechanism for injecting sensitive config," but ensure the *security* (encryption, access control) is actually configured — a common gap (connecting to the identity/security series' "don't assume it's secure" lesson).

## The state problem: volumes

Now the harder problem: **pods are ephemeral, so anything written to a container's filesystem is lost when the pod is destroyed.** For stateless apps that's fine, but many apps need data to *persist* beyond a pod's life. **Volumes** provide storage that a pod's containers can mount, decoupling data from the container's ephemeral filesystem:

- **A volume** is storage mounted into a pod's containers. Some volume types live only as long as the pod (useful for scratch space or sharing files between a pod's containers — the sidecar case). But for *persistence*, you need storage that outlives the pod entirely.
- **PersistentVolume (PV) and PersistentVolumeClaim (PVC)** — the abstraction for durable storage. A **PersistentVolume** is a piece of real storage in the cluster (backed by cloud disk, network storage, etc.); a **PersistentVolumeClaim** is a pod's *request* for storage ("I need 10Gi"). The pod mounts the PVC, Kubernetes binds it to a PV (often provisioned dynamically), and the data on that PV **survives the pod** — if the pod is destroyed and recreated, it can re-mount the same PV and its data is still there.

```text
Pod → mounts PersistentVolumeClaim ("I need 10Gi") → bound to a PersistentVolume (real disk)
   → pod destroyed and recreated → re-mounts the same PV → data persists
```

So volumes (specifically PV/PVC) are how state *survives* Kubernetes's disposable pods: the data lives in a PersistentVolume *outside* the pod's lifecycle, and pods attach to it. This is the answer to "pods lose their local state" (post three) — persistent data belongs in a PV, not in the pod. The PV/PVC split also decouples *what storage a pod wants* (the claim) from *how it's provisioned* (the volume), so developers request storage declaratively and the platform provides it (dynamic provisioning via StorageClasses).

## Stateful applications: StatefulSets

Stateless apps use Deployments (interchangeable pods). But some applications — databases, message brokers, clustered systems — are *stateful*: their pods aren't interchangeable, each needs a *stable identity* and its *own persistent storage*. The **StatefulSet** (introduced in the controllers post) is the controller for these:

- **Stable, persistent identity** — each pod in a StatefulSet gets a stable, ordinal name (e.g. `db-0`, `db-1`, `db-2`) that persists across rescheduling. Unlike a Deployment's interchangeable, randomly-named pods, a StatefulSet's pods have durable identities — which matters for stateful systems where "this is the primary, that is a replica" depends on stable identity.
- **Stable, per-pod storage** — each pod gets its *own* PersistentVolume that follows it: `db-0` always gets its volume, `db-1` gets its own, and if a pod is rescheduled, it re-attaches its *same* storage. So each stateful pod keeps its own durable data across restarts.
- **Ordered operations** — StatefulSets handle pods in order (for startup/scaling), which stateful systems often need (e.g. start the primary before replicas).

So a StatefulSet is a Deployment-like controller adapted for state: stable identities + stable per-pod storage + ordered management, for workloads where pods are *not* interchangeable. Databases and clustered stateful systems run as StatefulSets with PersistentVolumes.

**But a caveat worth stating:** running stateful systems (especially databases) *in* Kubernetes is genuinely harder than running stateless apps, because you're managing persistent data, replication, backups, and failover on an orchestrator designed around disposability. Many teams deliberately run their databases *outside* Kubernetes (using managed database services) and keep only stateless workloads in the cluster — a reasonable choice given the complexity. Kubernetes *can* run stateful workloads (StatefulSets + PVs exist for it), but "should you run your database in Kubernetes?" is a real decision, and "use a managed database, keep Kubernetes for stateless services" is a common, sensible answer.

## Config and state in Kubernetes

The takeaway: because pods are disposable, Kubernetes externalizes both configuration and state. **ConfigMaps** (non-sensitive) and **Secrets** (sensitive — but ensure real encryption/access control) inject configuration into pods as env vars or files, so the same image runs anywhere with environment-specific config (twelve-factor). **Volumes**, specifically **PersistentVolumes/Claims**, provide storage that *survives* pod destruction, so data persists outside the ephemeral pod. And **StatefulSets** give stateful apps stable identities and stable per-pod storage — though running stateful systems in Kubernetes is a real complexity you might avoid via managed services. Together these handle the config every app needs and the persistent state that ephemeral pods otherwise couldn't keep — completing the picture of running real applications, which need both. The next post covers how Kubernetes decides *where* to run pods and manages the cluster's resources: scheduling.

## Key takeaways

- Baking config into images is bad (rebuild per environment, can't change config without a new image), so Kubernetes externalizes it: ConfigMaps hold non-sensitive config and Secrets hold sensitive data, both injected into pods as environment variables or mounted files — so the same image runs anywhere with environment-specific config (twelve-factor).
- Secrets are only base64-encoded by default, not encrypted — "Secret" doesn't mean "secure"; enable encryption at rest, lock down access (RBAC), and often use an external secrets manager, ensuring the security is actually configured (a common gap).
- Pods are ephemeral, so container-filesystem data is lost on pod destruction; volumes provide storage mounted into pods, and PersistentVolumes/PersistentVolumeClaims provide *durable* storage that survives the pod — data lives in a PV outside the pod's lifecycle, and the PVC decouples requesting storage from provisioning it.
- StatefulSets run stateful apps (databases, clustered systems) whose pods aren't interchangeable: each pod gets a stable identity (db-0, db-1…) and its own persistent storage that follows it across rescheduling, with ordered operations — versus Deployments' interchangeable pods.
- Running stateful systems (especially databases) in Kubernetes is genuinely harder than stateless apps (managing data, replication, backups, failover on a disposability-oriented system); "use a managed database, keep Kubernetes for stateless services" is a common, sensible choice.

## Further reading

- [Services and networking (previous post)](/blog/posts/k8s-05-services-and-networking.html)
- [Kubernetes documentation — ConfigMaps and Secrets](https://kubernetes.io/docs/concepts/configuration/)
- [Web Identity: securing identity — why "encrypted" must be verified, not assumed](/blog/posts/identity-08-securing-identity.html)
