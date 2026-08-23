# Secure Code Execution

*The power of code agents comes with a sharp edge: you are executing code written by an LLM, and an LLM can be wrong, or manipulated into writing something harmful. Running that code unsandboxed is one of the most dangerous things you can do in an application, so sandboxing isn't optional for code agents — it's the price of admission.*

The previous posts made the case for code agents. This one covers the cost that comes with them: **security**. Executing model-written code is genuinely dangerous, and smolagents (and anyone using code agents) must run that code in a **sandbox**. This post explains the risk, why it's serious, and how code agents are made safe — because the code-agent advantage is only usable if you handle its security, and getting this wrong is catastrophic.

## The risk: executing model-written code

The code-agent approach means the framework *executes Python code written by the LLM*. That is inherently risky, for reasons that should give you pause:

- **The model can be wrong.** An LLM can generate code that does something unintended — delete files, make unwanted network calls, consume resources, corrupt data — not maliciously, just mistakenly. You're running unvetted, machine-generated code.
- **The model can be manipulated.** Prompt injection (the AI-security concern) means an attacker who influences the agent's input — a document it reads, a web page it fetches, a user message — could induce it to write *malicious* code. If the agent processes any untrusted content, that content can attempt to make it write harmful code.
- **Code has broad power.** Unlike a constrained JSON tool call (which can only invoke pre-defined tools with validated arguments), arbitrary code can do *anything the execution environment allows* — read the filesystem, access the network, run system commands, exhaust resources. The expressiveness that makes code agents powerful is exactly what makes executing their code dangerous.

Put bluntly: **running LLM-written code unsandboxed, in an environment with real access, is one of the most dangerous things you can do.** It's the difference between an agent that can only call your approved tools and one that can execute anything. The very generality that gives code agents their power (the last posts) is the source of the danger — you can't have arbitrary-code expressiveness without arbitrary-code risk. This is the non-negotiable cost of the approach.

## The solution: sandboxing

The answer is to **execute the model-written code in a sandbox** — an isolated, restricted environment where code runs *without* access to anything it could harm. Sandboxing is what makes code agents safe enough to use, and it's mandatory, not optional, for any code agent processing anything less than fully trusted input. The idea:

- **Isolation** — the code runs in an environment cut off from your real systems: no access to the host filesystem, no unrestricted network, no ability to affect the outside world beyond what you explicitly permit. Even if the model writes destructive or malicious code, it can only affect the sandbox.
- **Restriction** — limit what the code *can* do: which modules it can import, which operations it can perform, how much CPU/memory/time it can consume (so it can't exhaust resources or run forever).
- **Disposability** — the sandbox is ephemeral; you run the code, capture the result, and discard the environment, so nothing persists or escapes.

smolagents supports secure execution options — running code in a restricted local interpreter with limits, or (more securely) in isolated sandboxes (containerized or remote execution environments) — so that the code an agent writes runs safely. The strong guidance: **for anything beyond trusted, controlled input, use a proper sandbox** (an isolated container or remote execution service), not just a lightly-restricted local interpreter, because the stakes of a sandbox escape are severe. The more untrusted the input your agent processes, the stronger the isolation you need.

## Sandboxing as the enabler, not just a caveat

It's worth reframing sandboxing not as a burden but as the *enabler* of the whole code-agent approach:

- **Sandboxing is what makes code agents viable at all.** Without it, the code-agent advantage (the last posts) would be unusable in any real setting — the risk would be prohibitive. Sandboxing is what turns "powerful but dangerous" into "powerful and safe enough to deploy." So it's not an afterthought; it's a core part of the code-agent design.
- **It's a well-understood problem.** Executing untrusted code safely is a solved problem in principle — containers, restricted interpreters, and isolated execution services exist precisely for this. Code agents borrow that machinery. You're not inventing sandboxing; you're applying established isolation to a new source of untrusted code (the LLM).
- **It bounds the blast radius.** Good sandboxing means that even the worst case — the model writes maximally harmful code, whether by error or injection — is contained to a disposable environment. That containment is what lets you accept the model writing arbitrary code, because you've made "arbitrary code" safe to run.

So the mental model is: code agents trade JSON's *inherent* safety (a JSON tool call can only do pre-defined things) for code's *expressiveness*, and *recover* safety through sandboxing (isolate the execution so arbitrary code is contained). The expressiveness lives in the code; the safety lives in the sandbox. Both are necessary, and treating sandboxing as integral to the approach — not a bolt-on — is what makes code agents responsible to deploy.

## The security discipline for code agents

Practical guidance, tying it to the broader AI-security concerns:

- **Never execute model-written code unsandboxed** in any environment with real access. This is the cardinal rule; a local `exec` of LLM code against your systems is a serious vulnerability.
- **Match isolation to input trust** — the more untrusted content your agent processes (web pages, user documents, external data), the stronger the sandbox you need, because untrusted input is the injection vector for malicious code (the prompt-injection concern from the AI-security series).
- **Restrict capabilities** — limit imports, operations, network access, and resource/time budgets, so even permitted code can't do damage or run away.
- **Use proper sandboxes for real deployments** — isolated containers or remote execution services, not just a restricted interpreter, when the stakes or the untrustedness of input are high.
- **Treat it as part of the architecture** — sandboxing is a first-class design decision for a code agent, not an optional hardening step; design the execution environment before deploying.

Secure code execution is the price of the code-agent power, and it's a price worth paying *because* it's payable — sandboxing is established technology that contains the risk. Handle it well and code agents are both powerful and safe; ignore it and you've built one of the most dangerous things in software. The next post covers tools — how code agents are equipped with capabilities to call from within their code.

## Key takeaways

- Code agents execute Python written by the LLM, which is inherently dangerous: the model can be wrong (unintended harmful code), can be manipulated (prompt injection inducing malicious code, especially via untrusted input), and code has broad power (anything the environment allows) — unlike a constrained JSON tool call.
- Running LLM-written code unsandboxed in an environment with real access is one of the most dangerous things you can do — the expressiveness that makes code agents powerful is exactly what makes executing their code risky.
- The solution is sandboxing: run the code in an isolated (no real filesystem/network/host access), restricted (limited imports/operations/resources), disposable environment, so even destructive or malicious code is contained — mandatory, not optional, for code agents.
- Sandboxing is the enabler, not just a caveat: it makes code agents viable at all (turning powerful-but-dangerous into powerful-and-safe), it's a well-understood problem (containers, restricted interpreters, isolated execution services), and it bounds the blast radius to a disposable environment.
- Security discipline: never execute model code unsandboxed with real access, match isolation strength to input trust (untrusted input is the injection vector), restrict capabilities and resources, use proper sandboxes (containers/remote execution) for real deployments, and treat sandboxing as first-class architecture.

## Further reading

- [Why code actions win (previous post)](/blog/posts/smol-03-why-code-actions-win.html)
- [smolagents documentation — secure code execution](https://huggingface.co/docs/smolagents/index)
- [AI Security Engineering series — prompt injection and untrusted input](/blog/series/ai-security-engineering/)
