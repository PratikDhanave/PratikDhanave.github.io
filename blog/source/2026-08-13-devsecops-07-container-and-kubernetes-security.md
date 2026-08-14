# Container and Kubernetes Security

*Securing the runtime platform end to end — hardened images, least-privilege workloads, default-deny networks, and admission control as the gate that decides what is ever allowed to run.*

---

Everything a DevSecOps pipeline does before deployment — scanning source, signing artifacts, writing policy — buys you nothing if the runtime happily accepts whatever shows up. The runtime platform is where an attacker actually lives: inside a running container, on a shared kernel, one misconfigured `securityContext` away from the node. This post walks the platform layer in the order it fails: the **image** you ship, the **container** it becomes, the **Kubernetes** workload that schedules it, the **admission gate** that decides whether it runs at all, and the **runtime detection** that catches what slips through.

The through-line is four verbs: **harden the image, least-privilege the workload, default-deny the network, enforce at admission.** Each layer assumes the one before it failed.

---

## Image security: ship the smallest thing that works

An image is your attack surface frozen in time. Every package, shell, and interpreter you bake in is something an attacker can use after they get code execution. The single highest-leverage move is to ship less.

**Minimal and distroless base images.** A full `ubuntu` or `debian` base carries a package manager, a shell, coreutils, and hundreds of libraries your app never calls — each a potential CVE and a ready-made toolkit for post-exploitation. Google's `distroless` images (`gcr.io/distroless/...`) strip all of that: no shell, no `apt`, just your runtime and its direct dependencies. `alpine` is a middle ground — tiny, but it still ships `busybox` and a shell. Fewer packages means fewer CVEs to scan, patch, and lose sleep over.

**Multi-stage builds.** Compile in a fat builder stage, then copy only the finished artifact into a minimal final stage. Your compiler, build tools, and source never reach production. For a Go binary this is nearly free; for interpreted languages you copy the app plus its resolved dependencies into a slim runtime.

**Run as non-root.** By default a container process runs as UID 0. If that process is compromised, the attacker is root *inside* the container — and root inside is far closer to root on the host than most people assume (more on that below). Create an unprivileged user and switch to it.

**No secrets baked in.** A secret in a `Dockerfile`, a build `ARG`, or a bundled config file is permanent — it lives in the image layers forever, readable by anyone who can `docker pull` and `docker history`. Inject secrets at runtime instead (covered in the secrets section).

Here is a hardened multi-stage image that pulls all of this together:

```dockerfile
# ---- build stage: has the toolchain, never ships ----
FROM golang:1.23 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
# static binary so the final stage needs no libc
RUN CGO_ENABLED=0 go build -o /out/app ./cmd/server

# ---- final stage: distroless, non-root, minimal ----
FROM gcr.io/distroless/static-debian12:nonroot
# the :nonroot tag runs as an unprivileged UID by default
COPY --from=build /out/app /app
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/app"]
```

**The gotcha:** pin base images by digest, not by a moving tag. `golang:1.23` and even `distroless/static-debian12:nonroot` are mutable — the same tag points at different bytes next week. An attacker (or a compromised upstream) who repoints a tag changes what you build without changing your `Dockerfile`. Pin the immutable digest — `FROM golang:1.23@sha256:<digest>` — so your build is reproducible and a poisoned tag can't silently swap your base out from under you. Update the digest deliberately, through review.

### Scan images for CVEs in CI and at the registry

A pinned, minimal image still contains dependencies with known vulnerabilities — and new CVEs get published for images you built months ago. Scan continuously with a real scanner: **Trivy** (Aqua) and **Grype** (Anchore) both read the image's package manifest and OS metadata, match it against vulnerability databases, and report CVEs by severity. This is the recap of the supply-chain post (post 4): the scan belongs in CI so a vulnerable build never merges, *and* in the registry so newly disclosed CVEs in already-published images surface without a rebuild.

```bash
# fail the CI build if fixable HIGH/CRITICAL vulns are present
trivy image --severity HIGH,CRITICAL --ignore-unfixed \
  --exit-code 1 registry.example.com/app@sha256:<digest>

# Grype does the equivalent; both also read SBOMs and filesystems
grype registry.example.com/app@sha256:<digest>
```

Scanning tells you what's wrong. It does not stop a vulnerable image from running — that's a job for admission control, later in this post.

---

## The container isolation model: a container is not a VM

This is the mental model that everything else depends on. A container is **not** a security boundary in the way a virtual machine is. A VM has its own kernel and is isolated by the hypervisor. A container is just a normal Linux process on the host, dressed up by two kernel features:

- **Namespaces** give the process an isolated *view* — its own PID space, network interfaces, mount table, hostname. It sees a private world.
- **cgroups** limit what it can *consume* — CPU, memory, PIDs, I/O.

Both are enforced by the **host's single, shared kernel**. Every container on a node runs against the same kernel as the host and every other container. That is the crucial difference from a VM: there is no second kernel between the container and the machine.

**The gotcha:** because the kernel is shared, a **privileged or root container that escapes owns the node** — and often the cluster. A `--privileged` container, a container with dangerous Linux capabilities, or one that mounts the host filesystem or Docker socket has a short path from "code execution in the container" to "root on the host." A kernel vulnerability that a normal process couldn't reach becomes exploitable from inside a container with enough privileges. Treat container escape as a *when*, not an *if*, and make the escaped process as weak as possible.

You weaken it with four levers, all available in the container runtime and in Kubernetes:

- **Drop capabilities.** Linux splits root's power into ~40 capabilities. Most workloads need none of them. Drop `ALL`, then add back only what you truly need (rarely anything).
- **Read-only root filesystem.** If the process can't write to its own filesystem, an attacker can't drop a binary, tamper with config, or persist. Mount specific writable paths (a temp dir) as `emptyDir` volumes.
- **No privilege escalation.** Set `allowPrivilegeEscalation: false` so a child process can't gain more privileges than its parent via setuid binaries.
- **Seccomp and AppArmor/SELinux.** Seccomp filters which *syscalls* the process may make — the `RuntimeDefault` profile blocks dozens of dangerous ones. AppArmor (or SELinux) adds mandatory access control on files and capabilities. Together they shrink the kernel surface an escaped process can attack.

---

## Kubernetes: least-privilege the workload

Kubernetes doesn't change the isolation model — it orchestrates it at scale, which means every weak default is now a weak default replicated across a fleet. Four areas need deliberate hardening.

### Pod Security Standards

Kubernetes defines three built-in **Pod Security Standards** that codify the container levers above:

- **Privileged** — no restrictions. Never for application workloads.
- **Baseline** — blocks the widely-known bad stuff: no privileged containers, no host namespaces, no host ports. A sane floor.
- **Restricted** — the hardened target: non-root, `allowPrivilegeEscalation: false`, drop `ALL` capabilities, `seccompProfile: RuntimeDefault`, read-only where possible.

The built-in **Pod Security Admission** controller enforces these per-namespace via labels, in three modes: `enforce` (reject violating pods), `audit` (log them), and `warn` (return a warning to the user). Start with `warn`/`audit` to find violations, then flip to `enforce`.

Here is a Deployment pod spec that satisfies the **restricted** standard:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  selector:
    matchLabels: { app: app }
  template:
    metadata:
      labels: { app: app }
    spec:
      automountServiceAccountToken: false   # don't hand every pod an API token
      serviceAccountName: app-sa            # a dedicated, least-privilege identity
      securityContext:                      # pod-level defaults
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: registry.example.com/app@sha256:<digest>   # pinned by digest
          securityContext:                  # container-level hardening
            allowPrivilegeEscalation: false
            privileged: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:                        # cgroup limits — cap blast radius
            requests: { cpu: "100m", memory: "128Mi" }
            limits:   { cpu: "500m", memory: "256Mi" }
          volumeMounts:
            - { name: tmp, mountPath: /tmp } # writable scratch, since root FS is RO
      volumes:
        - name: tmp
          emptyDir: {}
```

### RBAC least-privilege

Kubernetes RBAC controls what identities can do against the API server. The recurring failure is convenience-driven over-permissioning: binding a ServiceAccount to `cluster-admin` because a narrower Role was annoying to write. Don't. Grant each ServiceAccount only the verbs (`get`, `list`, `watch`, `create`…) on only the resources it needs, scoped to a namespace with a `Role`/`RoleBinding` rather than a cluster-wide `ClusterRole` wherever possible. Most application pods need **no** API access at all — which is why the spec above sets `automountServiceAccountToken: false`. A stolen token that can do nothing is a much smaller problem than one that can create pods anywhere.

### NetworkPolicies: default-deny

**The gotcha:** the default Kubernetes network is flat — **any pod can reach any other pod** in the cluster, across namespaces, with no restriction. A single compromised pod can then scan and pivot to your database, your internal APIs, everything. The fix is a **default-deny** posture: apply a NetworkPolicy that denies all ingress and egress in a namespace, then add narrow allow-rules for the traffic that must flow. Egress deny matters as much as ingress — it's what stops a compromised pod from phoning home or exfiltrating data.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: payments
spec:
  podSelector: {}                 # every pod in the namespace
  policyTypes: ["Ingress", "Egress"]
  # no ingress/egress rules = deny everything; add explicit allows separately
```

Note that NetworkPolicies are only enforced if your CNI plugin supports them (Calico, Cilium, and others do; some do not). A policy with no enforcing CNI is a comment, not a control.

### Secrets handling

**The gotcha:** Kubernetes Secrets are **base64-encoded, not encrypted**. `base64` is an encoding, trivially reversible — anyone with read access to the Secret object, or to the underlying `etcd` datastore, reads the plaintext. By default etcd stores them unencrypted at rest. Two fixes, ideally both: enable **encryption at rest** for Secrets in the API server (backed by a real KMS provider — cloud KMS, HashiCorp Vault Transit — so the encryption key isn't itself sitting in the cluster), and pull secrets from a dedicated secrets manager using **External Secrets Operator** or the **Secrets Store CSI Driver** rather than committing Secret manifests to Git. This is the recap of the secrets post (post 5): the store is the source of truth, Kubernetes just projects a short-lived copy into the pod. Also lock down RBAC on Secret objects — `get`/`list` on secrets is a credential-theft primitive.

---

## Admission control: the policy-as-code gate

Here is the leak that undoes everything above. **The gotcha:** if you scan images in CI but let the cluster run whatever image is referenced, the gate leaks. Someone applies a manifest pointing at an unscanned, unsigned, or `:latest` image — or a pod with `privileged: true` — and CI never sees it. Enforcement has to live where pods are *actually admitted*: the Kubernetes API server's admission phase.

**Admission controllers** intercept every create/update request to the API server *before* the object is persisted, and can reject it. This is where policy-as-code (post 6) meets the runtime: instead of hoping every manifest author remembers the rules, you encode them as policy and the cluster enforces them uniformly. Two tools dominate:

- **OPA Gatekeeper** — a validating admission webhook built on Open Policy Agent. You write policies in **Rego** as reusable `ConstraintTemplate`s, then instantiate `Constraint`s. Powerful and expressive; Rego has a learning curve.
- **Kyverno** — a Kubernetes-native policy engine where policies are YAML `ClusterPolicy` resources. No new language; it can **validate**, **mutate** (inject secure defaults), and **generate** resources, and it has built-in image-verification for checking signatures.

Typical policies to enforce at admission, tying the whole post together:

- **No privileged / no root** — reject pods with `privileged: true`, `hostNetwork`, missing `runAsNonRoot`, or non-dropped capabilities. (Pod Security Admission covers much of this; Gatekeeper/Kyverno extend it to custom rules.)
- **Signed images only** — verify the image's cryptographic signature (Cosign/Sigstore, from post 4) against your trusted key. Unsigned image, rejected.
- **Scanned-clean images only** — require an attestation that the image passed scanning below your severity threshold, or restrict pulls to registries/digests known to be clean.
- **No mutable tags** — require images be referenced by digest, not `:latest`.

Conceptually, a Kyverno validate policy reads: *"for every Pod, `spec.containers[*].securityContext.privileged` must be `false` or absent; otherwise deny with this message."* A Gatekeeper equivalent is a `ConstraintTemplate` whose Rego emits a violation when the field is `true`. Run policies in `audit`/`warn` first to see what would break, then switch to `enforce`. The exact CRD fields differ between the two — consult the current docs rather than trusting a remembered snippet.

Admission control is the single most important runtime control because it's the *only* one that decides what is ever allowed to exist in the cluster. Every other control hardens what's already running; this one keeps the bad thing out.

---

## Runtime threat detection: assume something got through

Even a hardened, admission-gated cluster can be breached — a zero-day, a supply-chain compromise, a leaked credential. Runtime detection is your last layer: watching *behavior* and alerting when a running container does something it shouldn't. **Falco** (a CNCF project) is the standard open-source tool. It taps kernel syscalls (via eBPF or a kernel module) and evaluates them against rules, flagging things like:

- a shell spawned inside a container (`/bin/sh` in a distroless image should be impossible — a strong compromise signal),
- a process reading `/etc/shadow` or writing to a system binary directory,
- an unexpected outbound network connection,
- a write below a read-only path, or a container suddenly running as root.

Falco turns your hardening assumptions into detections: because you shipped distroless and read-only, *any* shell or unexpected write is high-signal, not noise. Wire its alerts into your incident response so a detection triggers a human, or an automated response (kill the pod, cordon the node), fast.

---

## The layered picture

| Layer | Control | What it stops |
|---|---|---|
| Image | Distroless, multi-stage, non-root, pin by digest | Bloated attack surface, poisoned base tags |
| Image | Trivy / Grype scan in CI + registry | Known CVEs shipping to prod |
| Container | Drop caps, read-only FS, no privileged, seccomp/AppArmor | A compromised process escaping to the node |
| Kubernetes | Pod Security Standards (restricted) | Insecure pod configs across the fleet |
| Kubernetes | RBAC least-privilege | A stolen token doing damage |
| Kubernetes | Default-deny NetworkPolicies | Lateral movement and exfiltration |
| Kubernetes | KMS encryption / External Secrets | Plaintext secret theft from etcd |
| Admission | OPA Gatekeeper / Kyverno | Unsigned, unscanned, privileged workloads running |
| Runtime | Falco | Post-breach behavior in a live container |

---

## Key takeaways

- **Ship the smallest image.** Distroless base, multi-stage build, non-root user, no baked-in secrets, pinned by digest. Less image is less attack surface and fewer CVEs.
- **A container is not a VM.** It's a process on a shared kernel, isolated only by namespaces and cgroups. Assume escape is possible and make the escaped process powerless — drop capabilities, read-only root FS, never privileged.
- **Least-privilege the workload.** Restricted Pod Security Standard, scoped RBAC (not `cluster-admin`), and a dedicated ServiceAccount with `automountServiceAccountToken: false`.
- **The network is flat by default.** Apply default-deny NetworkPolicies for both ingress and egress; egress control is what stops exfiltration.
- **Kubernetes Secrets are base64, not encrypted.** Enable KMS-backed encryption at rest and pull from a real secrets store via External Secrets.
- **Enforce at admission.** Scanning in CI without an admission gate leaks. Use OPA Gatekeeper or Kyverno to admit only signed, scanned-clean, non-privileged, digest-pinned images — this is policy-as-code where it counts.
- **Detect at runtime with Falco.** Assume something gets through; hardened images make anomalous behavior high-signal.

---

## Further reading

- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes) — consensus hardening checklist for clusters.
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker) — the equivalent for container hosts and images.
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) — official Baseline/Restricted definitions.
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/) — including default-deny examples.
- [Encrypting Confidential Data at Rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/) — enabling KMS-backed Secret encryption.
- [OPA Gatekeeper](https://open-policy-agent.github.io/gatekeeper/website/docs/) — policy-as-code admission with Rego.
- [Kyverno](https://kyverno.io/docs/) — Kubernetes-native validate/mutate/generate policies and image verification.
- [Falco](https://falco.org/docs/) — CNCF runtime threat detection.
- [Trivy](https://trivy.dev/) — image, filesystem, and IaC vulnerability scanning.
- [Distroless images](https://github.com/GoogleContainerTools/distroless) — minimal base images with no shell or package manager.
