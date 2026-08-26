# Services and Networking

*Pods are ephemeral and get new IPs every time they're replaced, so how does anything reliably reach them? The Service — a stable address and load balancer in front of an ever-changing set of pods. Kubernetes networking looks intimidating, but it's a few clear layers solving one problem: stable communication over unstable pods.*

The pod post established that pods are ephemeral with changing IPs; the controller post showed pods constantly created and replaced. So the obvious question: **how do you reliably communicate with pods that keep changing?** The answer is the **Service** — Kubernetes's stable networking abstraction — plus the networking model underneath. This post covers the cluster network model, Services and their types, service discovery via DNS, and Ingress for external traffic. It's how stable communication works over unstable pods.

## The Kubernetes network model

First, the ground rules of Kubernetes networking, which are simpler than they look:

- **Every pod gets its own IP address** — pods are first-class network citizens with their own IP (from their network namespace, the containers post), not sharing the host's IP.
- **Pods can reach each other directly by IP** — the cluster network is *flat*: any pod can talk to any other pod's IP across nodes, without NAT between them. (How this flat network is implemented is the job of a *CNI plugin* — a networking layer — but the *model* you rely on is "every pod has an IP and can reach every other pod.")
- **The problem: pod IPs are ephemeral** — because pods are constantly created and destroyed (the pod post), their IPs change. So you can *reach* a pod by IP, but you can't *rely* on any particular IP, because the pod behind it may be gone in a moment.

This is the core networking problem: the flat network lets pods communicate, but pod IPs are unstable, so you need something *stable* to communicate *through*. That something is the Service.

## Services: a stable address over changing pods

A **Service** provides a *stable* network identity (a stable IP and DNS name) in front of a *dynamic* set of pods, load-balancing traffic across them. It's the answer to "how do I reliably reach pods that keep changing":

```text
Service "orders" (stable IP + DNS name)
   → selects pods by label (e.g. app=orders)
   → load-balances traffic across the CURRENT set of matching pods
   → as pods come and go, the Service tracks them; its own address stays stable
```

The mechanism:

- **A Service selects pods by label** — you define a Service with a *selector* (e.g. `app=orders`), and it dynamically tracks *all pods matching that label*, whatever their current IPs. As pods are created/destroyed, the set updates automatically.
- **The Service has a stable address** — a stable ClusterIP and DNS name that *don't change* even as the backing pods churn. Clients talk to the Service's stable address, and it routes to a healthy backing pod.
- **It load-balances** — traffic to the Service is distributed across the current matching pods, so the Service is also your in-cluster load balancer.

This decouples clients from the ephemeral pods: you talk to `orders` (stable), and Kubernetes routes to whichever pods currently implement it, load-balanced, self-healing (unhealthy pods drop out). The Service is the stable layer over unstable pods — the direct solution to pod ephemerality (post three). Under the hood, `kube-proxy` (or equivalent) on each node programs the routing that makes the Service's virtual IP forward to real pods, but the *abstraction* you use is simply "a stable name that reaches my pods."

## Service types

Services come in types, for different exposure needs:

- **ClusterIP** (the default) — the Service is reachable only *inside* the cluster, at a stable internal IP/DNS name. This is for pod-to-pod (service-to-service) communication *within* the cluster — the common case for internal microservices. Most Services are ClusterIP.
- **NodePort** — exposes the Service on a port on *every node*, so it's reachable from outside the cluster via any node's IP + that port. A basic way to expose a service externally (often used as a building block, not directly in production).
- **LoadBalancer** — provisions an *external* load balancer (via the cloud provider) that routes to the Service, giving a stable external IP. This is the standard way to expose a service to the internet on a cloud, and it builds on NodePort/ClusterIP underneath.
- **(Headless)** — a Service with no ClusterIP, used when you want direct pod DNS (e.g. for StatefulSets where clients address individual stable pods).

The progression ClusterIP → NodePort → LoadBalancer is internal-only → node-exposed → cloud-external. You pick based on who needs to reach the service: internal microservices use ClusterIP; something exposed to the internet uses LoadBalancer (or, more commonly for HTTP, Ingress — below).

## Service discovery via DNS

How do pods *find* Services? **DNS.** Kubernetes runs an internal DNS service, and every Service automatically gets a **DNS name**, so pods reach a Service by name rather than IP:

```text
A pod can reach the "orders" Service in namespace "shop" at:
   orders.shop.svc.cluster.local   (or just "orders" from within the same namespace)
```

- **Services get DNS names** — a Service named `orders` in namespace `shop` is reachable at `orders` (same namespace) or `orders.shop` / the full `orders.shop.svc.cluster.local`. Pods just use the name.
- **This is service discovery** — a pod that needs the orders service connects to `orders`, Kubernetes DNS resolves it to the Service's stable ClusterIP, and the Service routes to a healthy pod. No hard-coded IPs, no manual discovery — the name is stable and always resolves to the right place.

So the full picture of in-cluster communication: a pod uses a *Service name* (DNS) → resolves to the Service's *stable IP* → the Service *load-balances* to a *healthy backing pod*. This is how microservices in Kubernetes reliably talk to each other despite constant pod churn — stable names over stable Service IPs over ephemeral pods, with discovery built in via DNS. This is the DNS-as-service-discovery pattern from the networking series, realized in Kubernetes.

## Ingress: HTTP routing from outside

For *external HTTP/HTTPS* traffic, a LoadBalancer per service is coarse (one external IP per service). **Ingress** provides smarter external HTTP routing — a single entry point that routes to multiple Services by host and path:

```text
Internet → Ingress (one external entry point)
   route by host/path:
     api.example.com/*       → api Service
     app.example.com/*       → frontend Service
     example.com/images/*    → images Service
```

- **Ingress routes external HTTP(S) traffic to Services** based on hostname and URL path — so one external entry point (and one IP/load balancer) can front many services, routing `/api` to one Service, `/app` to another, etc. This is L7 (application-layer) routing, the reverse-proxy/L7-load-balancer idea from the networking series, as a Kubernetes resource.
- **It handles TLS** — Ingress typically terminates HTTPS (managing certificates), so your services get TLS at the edge.
- **An Ingress controller implements it** — Ingress is a *desired-state* resource; an Ingress controller (nginx, or a cloud/gateway implementation) reconciles it into actual routing. (The newer *Gateway API* is the evolving successor with a richer model, but Ingress is the established concept.)

So the external-traffic story: **Ingress** (or a Gateway) is the smart HTTP front door routing by host/path to internal **Services**, which load-balance to **pods**. Combined, external users hit the Ingress, get routed to the right Service, and reach a healthy pod — stable, load-balanced, TLS-terminated — over the churning pods beneath.

## Networking, demystified

The takeaway: Kubernetes networking is a few layers solving one problem — *stable communication over ephemeral pods*. The flat network gives every pod an IP and lets pods reach each other, but pod IPs churn, so **Services** provide a stable address and load balancer over a label-selected, ever-changing set of pods; **DNS** makes Services discoverable by name (service discovery); **Service types** (ClusterIP/NodePort/LoadBalancer) control internal vs external exposure; and **Ingress** provides smart external HTTP routing (host/path, TLS) to Services. Each layer is an answer to "how do I reliably reach things that keep changing," which is the pod-ephemerality problem from post three. Master this and Kubernetes networking is comprehensible: stable names → stable Service IPs → load-balanced healthy pods. The next post covers giving those pods configuration and persistent state.

## Key takeaways

- Kubernetes networking solves one problem — stable communication over ephemeral pods: the network model gives every pod its own IP on a flat network (any pod can reach any pod), but pod IPs churn as pods are replaced, so you need a stable thing to communicate through.
- A Service provides a stable IP and DNS name in front of a dynamic, label-selected set of pods, load-balancing across the current healthy matching pods — decoupling clients from ephemeral pod IPs (the direct solution to pod ephemerality); kube-proxy programs the routing underneath.
- Service types control exposure: ClusterIP (internal-only, the default, for service-to-service), NodePort (exposed on every node's port), LoadBalancer (a cloud external load balancer with a stable external IP), and headless (direct pod DNS) — pick by who needs to reach the service.
- Service discovery is via DNS: every Service gets a DNS name (`orders`, `orders.shop.svc.cluster.local`), so pods reach services by name → resolves to the Service's stable IP → load-balanced to a healthy pod — no hard-coded IPs, the DNS-as-discovery pattern realized in Kubernetes.
- Ingress (or the Gateway API) provides smart external HTTP routing — one entry point routing by host/path to multiple Services, with TLS termination — implemented by an Ingress controller (L7 reverse-proxy as a Kubernetes resource); together Ingress → Services → pods give stable, load-balanced, TLS'd access over churning pods.

## Further reading

- [Controllers and the reconciliation loop (previous post)](/blog/posts/k8s-04-controllers-and-reconciliation.html)
- [Kubernetes documentation — Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Computer Networking for Backend Engineers — DNS, load balancing, L7 proxies](/blog/series/computer-networking-for-backend-engineers/)
