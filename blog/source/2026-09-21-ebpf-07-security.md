# eBPF for Security

*Security is eBPF's third domain, and arguably its most natural fit: the kernel sees every syscall, every process, every file access and network connection, so an eBPF program in the kernel is perfectly positioned to watch for and stop malicious behavior in real time. This is why modern runtime-security tools — detecting and blocking threats on live systems — are increasingly built on eBPF.*

Observability watched the system; networking acted on packets. Security combines both: use the kernel's total visibility to *detect* threats, and its position in the action path to *enforce* policy. This post covers eBPF for runtime security — monitoring, detection, and enforcement — the domain where the kernel's all-seeing vantage becomes a defensive superpower.

## Why the kernel is the ideal security vantage

Security monitoring wants to see *everything* a system does — and the kernel does see everything. Every meaningful action a process takes goes through the kernel: opening a file, making a network connection, spawning a child process, executing a binary, changing permissions. These all happen via syscalls, and the kernel mediates them all.

That makes the kernel the ideal place to observe and control from a security standpoint:
- **Complete visibility** — you can see every security-relevant action, system-wide, from one vantage. Nothing a process does escapes the kernel's view.
- **The enforcement point** — because the kernel *mediates* these actions, it's not just a place to watch but a place to *intervene* — to allow or deny an action as it happens.
- **Hard to evade** — monitoring at the kernel is harder for malware to bypass than user-space monitoring, because the malware still has to go through the kernel to do anything meaningful.

Historically, getting security logic to this vantage meant kernel modules (dangerous, post 2), so kernel-level security tooling was heavyweight and risky. eBPF changes that: safe, programmable security logic at the kernel's ideal observation-and-enforcement point. That's why eBPF and runtime security fit so naturally.

## Detection: watching for malicious behavior

The first eBPF security capability is **detection** — using the observability foundation (post 5) to watch for suspicious or malicious activity in real time:
- **Syscall monitoring** — watch the syscalls processes make and flag anomalous patterns: a process suddenly reading `/etc/shadow`, spawning a shell, making unexpected network connections, or executing unusual binaries.
- **Process and execution monitoring** — track process creation, executions, and privilege changes to spot, say, a container spawning an unexpected process or a privilege escalation attempt.
- **File and network activity** — detect access to sensitive files, connections to suspicious destinations, or data exfiltration patterns.
- **Behavioral anomaly detection** — build a baseline of normal behavior and flag deviations, all from kernel-level events.

The canonical open-source example is **Falco**, a runtime-security tool that uses eBPF (among its instrumentation options) to monitor kernel events and raise alerts when behavior matches suspicious rules — e.g. "a shell was spawned in a container," "a sensitive file was read by an unexpected process." Falco and tools like it give real-time threat detection on live systems by watching exactly the kernel events eBPF can observe, with the low overhead that makes always-on monitoring practical. This is the observability domain pointed at security questions: *is anything malicious happening right now?*

## Enforcement: stopping malicious behavior

Detection tells you something bad happened; **enforcement** stops it from happening. Because the kernel mediates actions, eBPF can *deny* them, not just observe them — this is the more powerful (and more delicate) security capability:
- **LSM (Linux Security Modules) hooks** — the kernel has security hooks throughout, and **eBPF LSM** lets you attach eBPF programs to them to make allow/deny decisions on security-sensitive operations (file access, process operations, network actions). This turns eBPF into a programmable security policy engine *in the kernel*: write policy as an eBPF program that the kernel consults before permitting an action.
- **seccomp-style syscall filtering** — restrict which syscalls a process can make (the classic BPF-based seccomp mechanism), sandboxing processes by denying dangerous syscalls.
- **Network policy enforcement** — deny disallowed network connections at the kernel (connecting to the networking domain, post 6, and to Cilium's network policy).

The power here is real-time *prevention*: an eBPF LSM program can block a malicious action *as it's attempted*, before it succeeds — stopping an exploit rather than merely logging it after the fact. The delicacy is equally real: enforcement code that *denies* legitimate actions breaks the system, so enforcement demands careful policy (and the same fail-safe-vs-usable balance from the guardrails series applies — too strict breaks things, too loose misses threats). Many deployments start with detection (observe and alert) and move to enforcement (block) as they gain confidence in their policies.

## Why eBPF security is ascendant

eBPF-based security is growing fast because it uniquely combines several things:
- **The ideal vantage** — kernel-level visibility and the enforcement point, seeing and controlling everything.
- **Low overhead** — always-on monitoring that's light enough for production (the observability advantage), so you're not choosing between security and performance.
- **Safety** — the verifier means your security logic can't crash the kernel (post 4), so kernel-level security is now safe to deploy widely.
- **Programmability and portability** — express custom detection and policy as programs, updated at runtime, portable across kernels (CO-RE, post 8) — security that adapts without kernel rebuilds.

This is why the cloud-native security ecosystem (Falco, Cilium's security features, Tetragon, and commercial runtime-security products) is heavily eBPF-based: it's the safe, low-overhead, programmable way to do detection and enforcement from the kernel's uniquely powerful vantage. eBPF made real-time, kernel-level security accessible the same way it did observability and networking — by removing the danger and adding programmability.

The takeaway: security is eBPF's most natural domain because the kernel sees and mediates every meaningful action, making it the ideal point to *detect* threats (syscall/process/file/network monitoring, à la Falco) and *enforce* policy (eBPF LSM, seccomp, network policy) in real time — safely (the verifier), with low overhead (always-on), and programmably. It's the defensive application of everything the series has built: kernel visibility plus kernel action, made safe.

## Key takeaways

- The **kernel is the ideal security vantage**: every meaningful action (file access, network connection, process spawn, execution) goes through it, giving **complete system-wide visibility**, a natural **enforcement point** (it mediates the actions), and **evasion-resistance** — historically reachable only via dangerous kernel modules, now safe via eBPF.
- **Detection** applies eBPF observability to security: syscall monitoring (flag reading `/etc/shadow`, spawning shells, odd connections), process/execution and file/network monitoring, and behavioral anomaly detection — **Falco** is the canonical example, giving real-time, low-overhead threat detection on live systems.
- **Enforcement** goes further — *stopping* bad actions, not just logging them — via **eBPF LSM** hooks (programmable allow/deny policy in the kernel), **seccomp** syscall filtering (sandboxing), and **network policy** — enabling real-time *prevention* of an exploit as it's attempted.
- Enforcement is **delicate**: denying legitimate actions breaks the system, so it needs careful policy (the guardrails fail-safe-vs-usable balance) — many start with detection/alert and move to blocking as confidence grows.
- eBPF security is **ascendant** because it uniquely combines the ideal vantage, low overhead (always-on), safety (the verifier can't crash the kernel), and runtime programmability/portability — which is why Falco, Cilium, Tetragon, and commercial runtime-security tools are eBPF-based.

## Further reading

- [Falco — runtime security](https://falco.org/)
- [Cilium — eBPF networking, observability, and security](https://cilium.io/)
