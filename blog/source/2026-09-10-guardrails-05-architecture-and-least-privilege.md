# Architecture and Least Privilege: The Real Defense

*Everything before this post raised the probability barrier against injection. This post lowers the impact — and impact is what actually protects you. The load-bearing defense against prompt injection isn't a prompt or a filter; it's an architecture where a fully-hijacked model still can't do anything catastrophic, because it was never granted the power to.*

This is the most important post in the series. If you take one idea from all eight, take this one: **since you cannot stop the model from being fooled, design so that a fooled model is harmless.** Every technique so far reduces how often injection succeeds. Architecture reduces what success is worth to the attacker — and unlike the probabilistic prompt-level defenses, architectural limits are *enforced*, not persuaded.

## Least privilege: the core principle

The oldest principle in security applies directly: **grant the model the minimum capabilities it needs, and nothing more.** Before wiring any tool, data source, or permission to an LLM, ask the question from post 1 — "if the model executed the worst possible instruction right now, using this capability, what's the damage?" — and grant accordingly.

Concretely:
- **Read vs. write.** A model that can *read* your database and one that can *modify* it are worlds apart in risk. Default to read-only. Grant write access only where essential, and scope it tightly (specific tables, specific operations).
- **Scope every tool.** A "send email" tool that can email anyone is a data-exfiltration weapon in a hijacked model. A tool that can only email *the authenticated user* is far safer. A "run SQL" tool is dangerous; a "look up order by ID" tool is not. Prefer narrow, purpose-built tools over general, powerful ones — the narrowness *is* the security.
- **No ambient authority.** The model should never operate with broad standing credentials (an admin API key, root access) "just in case." It gets exactly the scoped tokens for the task at hand.

Least privilege turns injection from a catastrophe into an annoyance. If the worst a hijacked model can do is return a wrong answer or call a read-only lookup with odd arguments, injection stops being a security incident.

## The confused-deputy trap and privilege inheritance

Recall from post 2 that indirect injection is a confused-deputy attack: the model, acting with *someone's* authority, is tricked into misusing it. The critical design error is letting the model **inherit privileges the requester shouldn't be able to exercise through it.**

The rule: **the model should act with the privileges of the least-trusted party in the chain, not the most-trusted.** If a user asks the assistant to summarize a web page, and that page contains injected instructions, the assistant is now taking orders from the page's author — so it must not be able to do anything the page's author shouldn't be allowed to do. In practice:
- Actions the model takes on a user's behalf run with *that user's* permissions, never elevated ones — so injection can't cross a privilege boundary.
- When the model processes third-party content (retrieved docs, web pages, emails), treat any "instruction" in that content as coming from an *anonymous, untrusted* party — because it is.
- Never let content the model *read* silently expand what the model can *do*.

This is why "the model has an admin API key so it can help with anything" is the single most dangerous pattern in LLM applications: it hands the most-trusted authority to a component you've already established can be commandeered by the least-trusted party.

## Human-in-the-loop for consequential actions

For actions that are irreversible, costly, or sensitive — sending money, deleting data, emailing externally, publishing, executing code with side effects — the strongest control is simple: **require explicit human confirmation.**

A hijacked model can *propose* "transfer $10,000 to account X," but if a human must approve the transfer with the details shown clearly, the injection dies at the confirmation step. The human is the un-injectable check. Design confirmations so they:
- Show the *actual* action and its concrete parameters (the real recipient, the real amount), not a model-generated summary the model could also manipulate.
- Are required for the *consequential* actions specifically, so you don't train users to click through everything (confirmation fatigue defeats the control).

Human-in-the-loop is friction, so spend it where impact is high. But for genuinely dangerous actions, it is the most reliable defense there is, because it doesn't depend on the model resisting anything.

## The dual-LLM pattern: quarantine the untrusted

A powerful architectural pattern for cases where a model must process untrusted content *and* take privileged action: **split the work across two models with an enforced boundary between them** (an idea articulated by Simon Willison as the "dual LLM" pattern).

- A **privileged model** can use tools and take actions, but only ever sees *trusted* input (the user's actual request, your instructions). It never sees raw untrusted content.
- A **quarantined model** processes the untrusted content (the document, the web page), but has *no access to tools or actions*. It can read and summarize; it can't do anything.

The two communicate through a constrained interface controlled by your code, not by free text — the quarantined model returns structured, validated data (never instructions) that the privileged model consumes as *data*. Because the model that can act never reads attacker-controlled text, and the model that reads attacker text can't act, an injection in the content has nothing to hijack. It's more complex to build, but it's one of the few designs that genuinely contains indirect injection rather than just discouraging it.

Related patterns push the same idea further: generating code/plans in a sandbox with no network or secrets, having the model emit a *constrained action request* that deterministic code validates against a policy before executing, and keeping tool outputs (which can themselves carry injection) on the untrusted side of the boundary.

## Designing the whole system to contain injection

Pulling the architecture together, a system that stays safe under injection tends to have these properties:

- **Scoped, purpose-built tools** rather than general powerful ones — the model can only reach narrow, safe operations.
- **Privileges bounded by the least-trusted input** — no crossing security boundaries, no ambient admin authority.
- **Human confirmation** gating the consequential, irreversible actions.
- **A trust boundary between reading untrusted content and taking action** — dual-LLM, sandboxing, or code-mediated action requests.
- **Deterministic policy checks** in code (not in the prompt) on any action the model requests, so the final gate is enforced, not persuaded.

Notice what all of these share: **they don't require detecting the attack.** They keep you safe whether or not the injection is recognized, whether it came from the user or a document, whether the model was fooled or not. That is the whole game. Prompts and filters try to *recognize and resist* the attack, which can't be done reliably; architecture *removes the reward* for the attack, which can. Build the containment into the system, and the unsolvable model-level problem stops being your problem.

## Key takeaways

- The load-bearing defense is **architecture, not prompts**: design so a *fully hijacked* model can't do serious harm — architectural limits are enforced, not persuaded, and don't depend on detecting the attack.
- **Least privilege**: grant the model the minimum capabilities (default read-only, scope every tool to the narrowest safe operation, no ambient/admin authority) — narrow purpose-built tools beat general powerful ones because the narrowness *is* the security.
- Avoid the **confused-deputy/privilege-inheritance trap**: the model must act with the privileges of the *least-trusted party in the chain*, never elevated ones, and reading untrusted content must never expand what the model can do.
- **Human-in-the-loop** for irreversible/costly/sensitive actions is the most reliable control (the un-injectable check) — show the real action + parameters, and reserve it for genuinely consequential actions to avoid confirmation fatigue.
- The **dual-LLM pattern** contains indirect injection: a privileged model (acts, sees only trusted input) and a quarantined model (reads untrusted content, can't act) communicate through code-controlled structured data — so attacker text has nothing to hijack. All these defenses share one virtue: **they don't require detecting the attack.**

## Further reading

- [Simon Willison — The Dual LLM pattern for building AI assistants that can resist prompt injection](https://simonwillison.net/2023/Apr/25/dual-llm-pattern/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
