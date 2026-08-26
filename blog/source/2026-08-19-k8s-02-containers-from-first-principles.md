# Containers from First Principles

*A container feels like a lightweight virtual machine, but it isn't one — there's no guest OS, no hypervisor, no virtualization. A container is just a normal process that the Linux kernel has been told to isolate and constrain. Understanding that — namespaces for isolation, cgroups for limits, images for packaging — demystifies containers and everything Kubernetes builds on them.*

Kubernetes orchestrates *containers*, so before going further, understand what a container actually *is* — because the common mental model ("a lightweight VM") is wrong and obscures how everything works. A container is not a virtual machine; it's a **normal process isolated and constrained by Linux kernel features**. This post covers the three primitives that make containers — **namespaces** (isolation), **cgroups** (resource limits), and **images** (packaging) — so containers stop being magic and Kubernetes's foundation is solid.

## Containers are not virtual machines

The first thing to unlearn: a container is *not* a lightweight VM. The distinction is fundamental:

- **A virtual machine** virtualizes *hardware*: a hypervisor runs a full *guest operating system* (its own kernel) on virtualized hardware, and your app runs inside that guest OS. VMs are heavyweight (a whole OS per VM) and strongly isolated (separate kernels).
- **A container** virtualizes nothing at the hardware level. It's a *normal process* running on the *host's* kernel — the same kernel as every other process on the machine — that the kernel has been told to *isolate* (make it see only its own files, processes, network) and *constrain* (limit its CPU/memory). There's no guest OS, no hypervisor, no second kernel.

```text
VM:        [ app ][ guest OS + kernel ] on [ hypervisor ] on [ host OS + hardware ]   — heavy
Container: [ app process, isolated + constrained by the HOST kernel ]                 — light
```

This is why containers are so lightweight and fast: starting a container is essentially starting a *process* (milliseconds), not booting an operating system (seconds). A machine can run *many* containers because they share one kernel, versus few VMs (each a full OS). The trade-off: containers share the host kernel, so isolation is weaker than a VM's separate-kernel boundary (a kernel vulnerability could cross containers) — which is why security-sensitive multi-tenant setups sometimes still use VMs, or lightweight VMs, around containers. But for packaging and running applications, the container's "just an isolated process" model is what makes it fast and dense. So: **a container is a process the kernel isolates and constrains.** Now, *how* does the kernel do that — the two primitives:

## Namespaces: isolation

**Namespaces** are the Linux kernel feature that gives a container its *isolation* — making a process see only its own slice of the system, as if it had the machine to itself. The kernel provides several kinds of namespace, each isolating one type of resource:

- **PID namespace** — the container sees only its own processes (its main process appears as PID 1), not the host's or other containers'. It can't see or signal processes outside it.
- **Network namespace** — the container has its own network stack: its own interfaces, IP address, ports, routing. It sees only its own network, isolated from others.
- **Mount namespace** — the container has its own filesystem view (its own root filesystem — from the image), isolated from the host's and other containers' files.
- **UTS, IPC, user namespaces** — isolate hostname, inter-process communication, and user/group IDs respectively.

Together, namespaces make a process *believe* it's alone on the machine: its own processes, network, filesystem, hostname. That illusion of isolation — "this process sees only its own world" — *is* containment. A container is a process (or group) placed in a set of namespaces so it's isolated from everything else, even though it's running right alongside other processes on the same kernel. Namespaces are *what* isolates a container.

## Cgroups: resource limits

Isolation (namespaces) says "you can only *see* your own stuff." **Cgroups** (control groups) say "you can only *use* this much." Cgroups are the kernel feature that *constrains* a container's resource consumption:

- **CPU** — limit how much CPU a container can use (so one container can't starve others).
- **Memory** — limit how much memory it can use (and the kernel can kill it if it exceeds the limit — the OOM kill).
- **I/O and more** — limit disk/network I/O and other resources.

Cgroups are why you can safely pack many containers onto one machine: each is *bounded* in what it can consume, so a runaway or greedy container can't hog the whole machine and starve its neighbors. This is exactly the `requests` and `limits` you set in Kubernetes (a later post) — those become cgroup constraints on the container. So the pair is: **namespaces isolate (what a container can see), cgroups constrain (what it can use).** Together, a container is a process that's *isolated* (namespaces) and *resource-limited* (cgroups) by the kernel — no VM, no magic, just kernel features applied to a process.

## Images: packaging

The third piece is the **container image** — how a container's *filesystem and app* are packaged and distributed. An image is a *bundle* containing the application, its dependencies, libraries, and a minimal filesystem — everything the container needs to run, packaged into a portable artifact:

- **Layers** — images are built in *layers* (each instruction in a build adds a layer), and layers are *shared and cached* across images. This makes images efficient to build, store, and transfer: common base layers (e.g. a base OS userland) are stored once and reused across many images.
- **Immutable and portable** — an image is a fixed, immutable artifact identified by its content; the same image runs identically anywhere (the "works everywhere" promise), because it carries its own dependencies. You build an image once and run it on any machine with a container runtime.
- **Registries** — images are stored in and pulled from *registries* (like Docker Hub or a cloud registry), so building and distributing containers is: build image → push to registry → any machine pulls and runs it.

When a container runs, its **mount namespace** gives it the image's filesystem as its root — so the "isolated filesystem" a container sees *is* the image's contents. The image provides the *what to run* (app + filesystem), and namespaces/cgroups provide the *how it runs* (isolated + constrained). A running container = an image's filesystem, executed as a process, isolated by namespaces and limited by cgroups.

## Containers, demystified

Putting it together, a container is: **a process running the contents of an image (its packaged app + filesystem), isolated by namespaces (its own processes/network/filesystem view) and constrained by cgroups (bounded CPU/memory), all on the host's shared kernel — not a VM.** This is what Kubernetes orchestrates. When Kubernetes "runs a container," it's telling a node's container runtime to pull an image and start a process in appropriate namespaces with cgroup limits. Understanding this makes Kubernetes concrete: pods, resource limits, networking, and volumes (later posts) are all Kubernetes *managing* these container primitives across a cluster. Containers aren't magic — they're kernel features applied to processes, packaged as images. The next post covers Kubernetes's own atom, which wraps containers: the pod.

## Key takeaways

- A container is not a lightweight VM: a VM virtualizes hardware and runs a full guest OS/kernel (heavy, strong isolation), while a container is a normal process on the *host's* shared kernel that's isolated and constrained by kernel features (light, fast, dense, but weaker isolation than a VM's separate kernel).
- Namespaces provide isolation — making a process see only its own slice of the system: PID (own processes, main as PID 1), network (own IP/ports/stack), mount (own filesystem from the image), plus UTS/IPC/user — the illusion of being alone on the machine that *is* containment.
- Cgroups provide resource limits — constraining a container's CPU, memory (with OOM kill on excess), and I/O — which is what lets you safely pack many containers on one machine (none can hog it) and is exactly what Kubernetes `requests`/`limits` become.
- Container images package the app + dependencies + minimal filesystem into a portable, immutable, layered (shared/cached) artifact stored in registries; a running container gets the image's filesystem as its root (via the mount namespace), so build once → push → run anywhere identically.
- A container = an image's contents run as a process, isolated by namespaces and limited by cgroups on the host kernel (no VM, no magic) — this is what Kubernetes orchestrates, making pods, resource limits, networking, and volumes concrete rather than mysterious.

## Further reading

- [What problem does Kubernetes solve? (previous post)](/blog/posts/k8s-01-what-problem-does-kubernetes-solve.html)
- [Operating systems concepts — namespaces and cgroups are kernel features](https://kubernetes.io/docs/concepts/overview/what-is-kubernetes/)
- [On-Device AI — another place isolation and resource limits matter](/blog/series/on-device-ai-with-gemma-and-flutter/)
