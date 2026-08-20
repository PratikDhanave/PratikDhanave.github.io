# Security and Adversarial Robustness

*AI systems add attack surface that traditional security does not cover — the model, its prompts, its retrieved context, and its tools are all attackable — and the only way to know you're defended is to threat-model the whole surface and prove it with red-teaming.*

Every earlier phase assumed cooperative users. This one assumes adversaries. AI systems introduce attack surface that conventional application security does not address: the model can be manipulated through its inputs, its retrieved context can carry injected instructions, and its tools can be turned into a weapon. The control you cannot skip here is a **threat model plus red-teaming** — reasoning about how the system can be attacked, then actually attacking it. This post is Phase 7 of the roadmap.

## Threat-model the whole surface

Security has to cover the entire AI attack surface, not just the application layer. Reason about threats across four layers:

- **Data** — poisoning of training or retrieval data; sensitive data leaking through the model or its stores.
- **Model** — extraction, inversion, and adversarial inputs that manipulate behavior.
- **Application** — the classic web surface (authn/authz, injection, SSRF) plus AI-specific input/output handling.
- **Agent** — tools with side effects, excessive agency, and the confused-deputy problem where a trusted agent is tricked into misusing its authority.

The **OWASP Top 10 for LLM Applications** is the practical starting taxonomy — prompt injection, insecure output handling, training-data poisoning, model denial of service, supply-chain risks, sensitive-information disclosure, insecure plugin/tool design, excessive agency, overreliance, and model theft. Seed your risk register (from the governance phase) with it and work each item into a concrete threat and mitigation for your system.

## Prompt injection is the signature threat

The attack that most defines AI security is **prompt injection**: untrusted content — a web page, an email, a document, a database field written by someone else — carries instructions the model then follows. *Direct* injection is a user trying to override the system prompt; *indirect* injection is far more dangerous, because the malicious instruction hides in content the system retrieves or a tool returns, and the user never sees it. This is why the data phase insisted on treating retrieved content as untrusted, and why the serving phase put guardrails inline.

There is no single switch that eliminates injection. Defense is layered: treat all retrieved and tool-returned content as untrusted data rather than instructions, keep clear structural boundaries between instructions and data, constrain what the model is allowed to do (least privilege on tools and data), require human approval for consequential actions, and validate outputs before they act. The goal is to limit what a *successfully* manipulated model can actually reach, because you must assume some injection will succeed.

## Guardrails, least privilege, and blast radius

The recurring security principle across the roadmap is to bound the blast radius. Give the model and its agents only the tools, data, and credentials they genuinely need; scope credentials narrowly and make them revocable; isolate untrusted or third-party components (including MCP servers and tools) from sensitive context; and gate destructive or high-impact actions behind a human. An agent with broad standing authority is a breach waiting to be triggered; an agent with least privilege, whose worst-case action is bounded and reversible, survives a successful manipulation with limited damage.

## Prove it with red-teaming

A threat model is a hypothesis; red-teaming is the test. Actively attack the system — attempt jailbreaks and injections, probe for data leakage and bias, try to induce harmful content and to abuse tools — before adversaries do. Automated adversarial scans can run continuously as part of the evaluation pipeline (the routine safety evals from the evaluation phase), while deeper, creative, manual red-teaming is done periodically and before major releases. What red-teaming finds becomes new test cases in the golden set and new entries in the risk register, closing the loop. I've written a full [AI Red Teaming](/blog/series/ai-red-teaming/) series on the offensive craft, and an [AI Security Engineering](/blog/series/ai-security-engineering/) series on the defenses; the production point is that both the threat model and the red-team must exist and be re-run.

## Security is continuous, not a gate

The MANAGE function of a risk framework lives here: detect, respond, recover, and communicate. Security is not a launch checkbox but a continuous track — new attacks emerge, new models and tools change the surface, and dependencies (models, libraries, MCP servers) shift underneath you. Wire security monitoring into the observability of the next phase, keep the threat model current as the system evolves, and rehearse the incident response tied to the governance phase's notification duties. A system that was secure at launch and never re-examined is insecure by now.

## The gate and anti-patterns

Phase 7 is done when a threat model covers the data/model/application/agent surface, the risk register is seeded from the OWASP LLM Top 10 with concrete mitigations, injection defenses and least-privilege tool/data access are implemented, consequential actions require human approval, and red-teaming (automated in CI plus periodic manual) has been performed and its findings folded back in. Avoid the recurring failures: treating AI security as ordinary app security and missing the model/prompt/agent surface; trusting retrieved and tool content as if it were instructions; granting agents broad standing privilege; and never actually attacking your own system.

## Key takeaways

- AI adds attack surface conventional security misses — data, model, application, and agent layers are all attackable; threat-model all four.
- Use the OWASP Top 10 for LLM Applications as the starting taxonomy and seed the risk register with concrete, per-system mitigations.
- Prompt injection (especially indirect, via retrieved or tool-returned content) is the signature threat; defend in layers — untrusted content, structural boundaries, least privilege, human gates, output validation — and assume some injection succeeds.
- Bound the blast radius: least-privilege tools/data/credentials, isolation of untrusted components, and human approval for destructive actions.
- Prove defenses with red-teaming — automated scans in CI plus periodic manual attacks — and fold findings back into the eval set and risk register; security is a continuous track, not a launch gate.

## Further reading

- [OWASP Top 10 for LLM Applications](https://genai.owasp.org/)
- [AI Red Teaming series](/blog/series/ai-red-teaming/)
- [AI Security Engineering series](/blog/series/ai-security-engineering/)
