# The Verifier and Safety

*The verifier is the reason eBPF exists in its modern form. Running arbitrary code in the kernel would be reckless; running code the kernel has proven safe is not. The verifier is the static analyzer that stands between your program and the kernel, mathematically checking that it can't crash, hang, or misbehave — and understanding it explains both eBPF's safety and its constraints.*

Every previous post has leaned on "the verifier makes it safe." This post is that promise, examined. The verifier is eBPF's central innovation and the thing that turns a dangerous idea (run my code in the kernel) into a safe one. It's also the source of eBPF's programming restrictions, so understanding it explains *why* eBPF programs look the way they do.

## Why the verifier is necessary

Recall the stakes (post 2): kernel code runs with full privileges and no isolation. A bug that would merely crash a user-space app — a null-pointer dereference, an out-of-bounds access, an infinite loop — would, in the kernel, panic the *entire machine* or hang it. So "let users load programs into the kernel" is, on its face, an obviously terrible idea.

The verifier is what makes it a *good* idea. Its job is to guarantee, *before* a program is allowed to run, that it cannot do any of the catastrophic things kernel code could otherwise do. It shifts the safety model from "trust that the programmer wrote correct kernel code" (the fragile assumption behind kernel modules) to "the kernel proves the program is safe, and rejects it if it can't." That shift — from trust to proof — is the whole game. It's why an ordinary developer can safely write kernel-level logic: they don't have to *be* trusted to write flawless kernel code, because the verifier checks it.

## What the verifier proves

The verifier is a **static analyzer**: it examines the eBPF bytecode *without running it* and proves properties hold on every possible execution path. The key guarantees:

- **Termination — no infinite loops.** The program must be proven to finish. Historically eBPF forbade loops entirely (only bounded, unrollable ones); modern kernels allow bounded loops the verifier can prove terminate. Either way, the guarantee is that an eBPF program *cannot hang the kernel* by looping forever. This is essential — a kernel that hangs is as dead as one that crashed.
- **Memory safety — no invalid access.** The program can only access memory it's allowed to (its own stack, the context it was given, maps through the proper helpers). It can't read or write arbitrary kernel memory, dereference null or out-of-bounds pointers, or leak kernel memory to user space. The verifier tracks the possible values and bounds of every pointer and register to prove every access is valid.
- **No crashes / defined behavior.** By proving memory safety and termination on all paths, the verifier ensures the program can't cause a kernel panic or undefined behavior.
- **Bounded complexity.** The program must be small and simple enough for the verifier to analyze exhaustively — there are limits on size and on the number of paths, so verification itself terminates.

The method is essentially *symbolic execution / abstract interpretation*: the verifier walks all reachable paths, tracking what it knows about each register and pointer (its type, its possible range), and rejects the program if it can't prove every operation is safe on every path. If there's any path where an access might be out of bounds or a loop might not terminate, the program is rejected.

## Rejected means never runs

The critical property: **if the verifier can't prove a program is safe, the program is rejected and never loaded.** There's no "load it and hope." Safety is checked at load time, before the program can execute even once. A program that might crash the kernel simply isn't allowed to run — the failure mode is "your program won't load," not "your program crashed the machine."

This is why eBPF is genuinely safe rather than just careful: the guarantee is enforced by the kernel's own static analysis, not by developer discipline or testing. It's the same reason a type checker's guarantees are stronger than "we tested it" — the property is *proven* for all executions, not sampled on some. The cost, of course, is that the verifier must be *conservative*: if it *can't prove* safety, it rejects — even if the program would actually be fine. This leads to the famous experience of "fighting the verifier."

## Fighting the verifier: the constraints explained

If you've heard eBPF developers grumble about "fighting the verifier," this is why. Because the verifier must *prove* safety and is conservative, it imposes real constraints that shape how you write eBPF programs (the restrictions from post 3, now explained):
- **Restricted language.** No unbounded loops, limited program size and complexity, only approved helper functions, careful pointer handling — all so the verifier can analyze the program. You're writing in a subset designed to be verifiable.
- **Prove-it-to-the-verifier idioms.** You often must write code in a specific way to *convince* the verifier — e.g. explicitly bounds-checking before every memory access (even when you "know" it's safe), because the verifier needs the check to prove the bound. Missing a check the verifier demands means rejection.
- **Sometimes-cryptic rejections.** The verifier rejects programs it can't prove safe, and its reasons can be hard to decipher, leading to iterative "why won't this load?" debugging.

The reframing that makes this tolerable: **the verifier's strictness is the price of the safety.** Every constraint exists so the kernel can *guarantee* your program won't take down the machine. "Fighting the verifier" is really "collaborating with the prover" — writing code whose safety can be mechanically demonstrated. It's stricter than normal programming precisely because the guarantee is stronger. Modern tooling (post 8) smooths a lot of this, but the fundamental trade — accept restrictions, gain a safety guarantee — is inherent and worth it.

## Why this is the whole ballgame

Step back and the verifier is what separates eBPF from "kernel modules with nicer syntax." Kernel modules are unsafe because nothing proves them safe — a bug is catastrophic. eBPF is safe because the verifier proves each program safe before it runs, so a bug is *rejected*, not catastrophic. That single difference is why eBPF could democratize kernel programming: it removed the danger, so the power became accessible. Everything eBPF does — the observability, networking, and security applications in the coming posts — rests on the fact that you can run these programs in the kernel *without risk*, and the verifier is what earns that "without risk." It's the innovation that made a dangerous idea into foundational infrastructure.

## Key takeaways

- Running unverified code in the kernel is reckless (a bug panics/hangs the *whole machine*); the **verifier** makes it safe by shifting from "trust the programmer" to "**the kernel proves it safe** and rejects it if it can't" — the central innovation of eBPF.
- The verifier is a **static analyzer** that proves, without running the program, on *every* path: **termination** (no infinite loops — can't hang the kernel), **memory safety** (only allowed memory, no invalid/null/out-of-bounds access, no kernel-memory leaks), **no crashes**, and **bounded complexity** (small enough to analyze).
- **Rejected means never runs** — safety is checked at load time before the program executes once, so the failure mode is "won't load," not "crashed the machine"; the guarantee is *proven for all executions* (like a type checker), not sampled by testing.
- The verifier's necessary **conservatism** (reject if it can't prove safety) causes "**fighting the verifier**": a restricted language (no unbounded loops, limited size, approved helpers), prove-it idioms (explicit bounds checks even when "obviously" safe), and sometimes-cryptic rejections — the price of the safety guarantee.
- The verifier is **the whole ballgame**: it's what separates eBPF (bugs get rejected) from kernel modules (bugs are catastrophic), and it's what let eBPF **democratize kernel programming** — every application in the series rests on running programs in the kernel *without risk*.

## Further reading

- [Linux kernel BPF documentation (verifier)](https://docs.kernel.org/bpf/)
- [ebpf.io — What is eBPF? (verification)](https://ebpf.io/what-is-ebpf/)
