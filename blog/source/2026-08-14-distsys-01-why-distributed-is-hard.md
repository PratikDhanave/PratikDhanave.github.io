# Why Distributed Systems Are Hard

*A distributed system is one where a machine you've never heard of failing can stop your program from working. That single property — partial failure — is the root of almost everything that makes this field hard, and pretending it away is the most common and most expensive mistake in backend engineering.*

The moment your application runs on more than one machine, you've entered a different world with different rules. Code that is obviously correct on one computer becomes subtly, intermittently, maddeningly wrong across several. This series builds distributed systems up from first principles — consistency, time, replication, partitioning, consensus, and failure — but it starts here, with *why* the field is hard, because every technique later is a response to the problems in this post.

## What makes a system distributed

A **distributed system** is a set of independent computers that communicate over a network and appear to their users as a single coherent system. The definition sounds benign. The consequences are not, because three things are now true that weren't before:

- **The network is between you and everything.** Every interaction with another node is a message that can be delayed, reordered, duplicated, or lost — and you often can't tell which happened.
- **Nodes fail independently.** One machine can crash, freeze, or slow to a crawl while the others keep running. There is no global "off switch" and no shared fate.
- **There is no shared clock and no shared memory.** Each node has its own notion of time and its own copy of state. Nothing is instantaneously true everywhere.

On a single machine, a function call either happens or doesn't. Across a network, a request can happen, *not* happen, or — worst of all — happen without you ever finding out. That third outcome is the one that breaks intuitions.

## Partial failure: the root of everything

On one computer, failure is total: if the process dies, everything stops, and you know it. In a distributed system, failure is **partial** — some components work while others don't, and the working ones must decide what to do about the broken ones *without reliable information about their state*.

Here is the problem in its purest form. Node A sends a request to node B and gets no response. What happened?

- B never received the request (message lost on the way).
- B received it, did the work, but the reply was lost (message lost on the way back).
- B is slow and the reply is still coming.
- B has crashed.
- B is fine but a network partition separates A from B.

**A cannot distinguish these cases.** From A's perspective they are identical: silence. Yet the correct action differs for each — retrying a lost request is safe, but retrying one B already processed might charge a customer twice. This inability to tell "slow" from "dead," or "didn't happen" from "happened but I didn't hear," is the irreducible difficulty of distributed systems. Nearly every concept in this series — timeouts, retries, idempotency, quorums, consensus — exists to cope with it.

## The fallacies you must unlearn

Engineers new to distributed systems carry assumptions from single-machine programming that are quietly false at scale. The classic "fallacies of distributed computing" name them; the ones that bite hardest:

- **The network is reliable.** It isn't. Messages are lost and connections drop, routinely, at scale.
- **Latency is zero.** A remote call is *orders of magnitude* slower than a local one, and that changes what designs are viable — chatty designs that make many small calls collapse.
- **Bandwidth is infinite / the network is free.** Moving data costs time and money; the amount you move matters.
- **The topology is stable / there is one administrator.** Nodes come and go, deployments roll, and the system is never fully "at rest."
- **Transport is secure and homogeneous.** The network is a shared, adversarial, heterogeneous environment.

Believing any of these produces code that demos perfectly and fails in production under load, during a deploy, or when a switch hiccups — exactly when you can least afford it.

## Why do it at all, then?

If distributed systems are this hard, why build them? Because at some point a single machine can't meet your requirements, and the reasons are worth naming precisely:

- **Scale** — the workload (data volume, request rate) exceeds what one machine can hold or handle, so you must spread it across many.
- **Fault tolerance / availability** — one machine is a single point of failure; to keep serving through hardware failures, you need redundancy, which means multiple machines.
- **Latency** — users are geographically spread, and serving them from nearby locations means running in many places at once.

Notice the tension: you go distributed *for* availability and scale, but doing so *introduces* partial failure and coordination problems that can make the system less reliable if handled naively. Distribution is not free reliability — it's a trade of one machine's simple, total failure for many machines' complex, partial failure, taken on deliberately because the single machine couldn't do the job.

## The shape of the rest of the series

Every hard problem ahead traces back to this post. Because there's no shared clock, we need **consistency models** to define what "correct" even means and ways to reason about **time and ordering**. Because nodes fail, we need **replication** to keep copies alive, which forces the **CAP** trade-off between consistency and availability under partition. Because data outgrows one node, we need **partitioning**. Because independent nodes must still agree, we need **consensus**. And because failure is the normal case, we need explicit **failure detection and resilience** patterns. Keep partial failure in mind as the through-line: each technique is an answer to "how do we stay correct when we can't tell what's broken?"

## Key takeaways

- A distributed system is independent computers communicating over a network that appear as one — which introduces a network between everything, independent failures, and no shared clock or memory.
- Partial failure is the root difficulty: some parts work while others don't, and a node cannot distinguish a slow peer from a dead one, or "didn't happen" from "happened but I didn't hear back."
- Unlearn the fallacies of distributed computing — the network is not reliable, latency is not zero, bandwidth and topology are not free or stable — because assuming them produces code that fails precisely under production stress.
- We accept this complexity deliberately, for scale, fault tolerance/availability, and latency — distribution trades one machine's simple total failure for many machines' complex partial failure.
- Every technique in this series (consistency models, clocks, replication, CAP, partitioning, consensus, resilience) is an answer to the same question: how do we stay correct when we can't tell what's broken?

## Further reading

- [Fallacies of distributed computing (overview)](https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing)
- [Jepsen — analyses of real distributed systems under failure](https://jepsen.io/analyses)
- [System Design Fundamentals series](/blog/series/system-design-fundamentals/)
