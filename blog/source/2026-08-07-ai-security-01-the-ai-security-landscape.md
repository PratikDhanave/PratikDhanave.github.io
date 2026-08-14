# The AI Security Landscape

*Why LLM and agent applications open a genuinely new attack surface, the mental models to reason about it (OWASP Top 10 for LLM Applications, MITRE ATLAS, NIST AI RMF), and how to threat-model an AI system before you write a line of defensive code.*

---

For twenty years the security discipline has organized itself around a stable assumption: **code is trusted, data is not**. You validate input at the boundary, escape it before it reaches an interpreter, and the executable logic of your application stays firmly under your control. SQL injection, XSS, and command injection are all variations on one failure — untrusted data crossing into a trusted execution context.

Large language models break that assumption at the foundation. An LLM does not have separate channels for "instructions" and "data." It reads one undifferentiated stream of tokens and predicts the next one. Your carefully written system prompt, the user's question, a paragraph retrieved from a document, and the JSON a tool returned all arrive as *the same kind of thing*. The model has no reliable, built-in way to tell which tokens are supposed to command it and which are merely supposed to inform it.

Bolt tools onto that model — the ability to send email, query a database, call an API, run code — and you have handed real-world power to a component that treats every input as potentially authoritative and produces **non-deterministic** output. That combination is what makes AI security a new field rather than a footnote to web security. This series is about engineering defenses for it. This first post sets the mental models we'll use throughout.

---

## Three properties that create the new attack surface

Everything downstream follows from three characteristics of LLM-based systems.

**1. Instructions and data share one channel.** There is no `parameterized_query()` equivalent for prompts. If an attacker can get text in front of the model — directly in a chat box, or indirectly through a web page you scrape, a PDF you summarize, or an email you triage — that text can attempt to redirect the model's behavior. The industry name for this is *prompt injection*, and it is the defining vulnerability class of the field precisely because it has no clean architectural fix.

**2. Tools convert text into action.** A model that can only emit text is a limited liability. The moment you give it function calling — "book the meeting," "issue the refund," "delete the record" — a successful injection stops being a curiosity and becomes an incident. The blast radius of a compromised prompt equals the union of permissions granted to the model's tools.

**3. Output is non-deterministic and untrusted.** The same prompt can yield different completions. More importantly, the output is attacker-influenceable and must be treated like any other untrusted data. If your application takes model output and renders it as HTML, feeds it to `eval`, or splices it into a shell command, you have recreated classic injection with a new source.

Hold these three together and a rule falls out that governs the whole series:

**The gotcha:** in a traditional app you secure the code and trust it thereafter. In an AI system there is no trusted core to defend behind — the model itself is an untrusted, manipulable component sitting *inside* your trust boundary. You are no longer securing code; you are securing a whole system made of data, model, prompts, tools, and outputs, none of which you can fully trust.

---

## Threat-modeling an LLM application

Good security starts with a threat model, not a checklist. Three questions: what are the trust boundaries, what are the assets, and who are the adversaries.

### Trust boundaries: everything flowing to the model is untrusted

A trust boundary is any point where data crosses from a less-trusted zone into a more-trusted one. In a RAG-plus-tools agent, the boundaries are not where intuition puts them. Consider the data sources that reach the model:

```text
  [ user message ]        <-- untrusted (obvious)
  [ retrieved docs ]      <-- untrusted (a poisoned document is an injection vector)
  [ tool / API output ]   <-- untrusted (the API may be compromised or return attacker data)
  [ prior conversation ]  <-- untrusted (may contain earlier injected content)
        |                        |                   |
        v                        v                   v
  +-----------------------------------------------------------+
  |                     THE MODEL                             |
  |   treats all of the above as one instruction stream       |
  +-----------------------------------------------------------+
        |
        v
  [ model output ]        <-- untrusted (attacker-influenceable)
        |
        v
  +-----------------------------------------------------------+
  |  YOUR CODE: parsers, renderers, tool dispatch, DB writes  |
  |  <-- the real trust boundary you control lives HERE       |
  +-----------------------------------------------------------+
```

The lesson of that diagram is where the enforceable boundary actually sits. You cannot make the model trustworthy. What you *can* control is the code on either side of it: what you allow to reach the model, and — far more importantly — what you allow the model's output to do. Guardrails and validation belong at those two edges, not inside the model's head.

### Assets: what an attacker wants

- **The system prompt and its logic** — proprietary instructions, business rules, hidden context.
- **Sensitive data in context** — anything in the prompt, retrieved documents, or conversation history (PII, secrets, internal knowledge).
- **The tools' capabilities** — the model's function-calling powers are an asset an attacker wants to hijack.
- **The model and its behavior** — availability (a model that can be forced into expensive loops) and integrity (a model steered into harmful output that damages users or brand).

### Adversaries: who is attacking

- **The direct user**, trying to jailbreak restrictions, exfiltrate the system prompt, or abuse tools for their own ends.
- **A third party via indirect injection**, who never talks to your app but plants instructions in content your app will later ingest — a comment on a page, text in a shared document, a crafted email.
- **A supply-chain adversary**, who compromises a model, a dataset, a package, or an MCP/tool server *upstream* of you.

---

## Mental model 1: the OWASP Top 10 for LLM Applications

The OWASP GenAI Security Project maintains the **OWASP Top 10 for LLM Applications**, the field's most widely used taxonomy of risk. The current (2025) list is the vocabulary we'll use across this series. Named faithfully:

| ID | Risk | One-line meaning |
|---|---|---|
| LLM01 | Prompt Injection | Crafted input overrides intended instructions, directly or indirectly. |
| LLM02 | Sensitive Information Disclosure | The model leaks PII, secrets, or proprietary context in its output. |
| LLM03 | Supply Chain | Compromised models, datasets, plugins, or dependencies. |
| LLM04 | Data and Model Poisoning | Tampered training or fine-tuning data corrupts model behavior. |
| LLM05 | Improper Output Handling | Downstream code trusts model output (XSS, SSRF, code/command execution). |
| LLM06 | Excessive Agency | Too much autonomy, permission, or tool power granted to the model. |
| LLM07 | System Prompt Leakage | Secrets or security-relevant logic placed in the system prompt get exposed. |
| LLM08 | Vector and Embedding Weaknesses | Attacks on the RAG layer — poisoned embeddings, retrieval manipulation, cross-tenant leakage. |
| LLM09 | Misinformation | Confident, plausible, wrong output that users overrely on. |
| LLM10 | Unbounded Consumption | Resource-exhaustion and cost/denial-of-service attacks, plus model theft. |

**The gotcha:** the list evolved. If you learned the 2023 version you'll remember "Insecure Output Handling," "Training Data Poisoning," "Model Denial of Service," "Insecure Plugin Design," "Overreliance," and "Model Theft" as distinct entries. Those risks didn't vanish — they were renamed and reorganized (output handling became LLM05, poisoning became LLM04, DoS and theft folded into LLM10 Unbounded Consumption, plugin design merged into LLM06 Excessive Agency and LLM03 Supply Chain). When you read older material, translate to the current IDs. Always check [genai.owasp.org](https://genai.owasp.org/) for the version you're citing.

Notice how tightly these map to the three properties from earlier: LLM01/LLM07 are the shared-channel problem, LLM05/LLM06 are the tools-give-power problem, and LLM09 is the non-determinism problem wearing a human-factors hat.

---

## Mental model 2: MITRE ATLAS

Where OWASP catalogs *vulnerabilities*, **MITRE ATLAS** — Adversarial Threat Landscape for Artificial-Intelligence Systems — catalogs *adversary behavior*. It is a knowledge base of real-world tactics and techniques against AI-enabled systems, deliberately structured like MITRE ATT&CK: a matrix of **tactics** (the adversary's goal at a stage) filled with **techniques** (how they achieve it), backed by documented case studies.

The tactics read as a familiar kill-chain adapted for ML: reconnaissance, resource development, initial access, **ML model access**, execution, persistence, defense evasion, discovery, collection, **ML attack staging**, exfiltration, and impact. The AI-specific columns are what make it valuable — techniques like model evasion, model inversion, membership inference, and LLM prompt injection sit alongside conventional ones.

Use the two frameworks together and for different jobs:

- **OWASP** answers *"what could be wrong with my design?"* — reach for it during design review and threat enumeration.
- **ATLAS** answers *"how would a real adversary progress through my system, and what have others actually seen?"* — reach for it during red-teaming and detection engineering (a later post in this series).

---

## Mental model 3: NIST AI RMF (the governance layer)

OWASP and ATLAS are technical. The **NIST AI Risk Management Framework (AI RMF 1.0)** supplies the organizational scaffolding: how a team decides which risks matter, measures them, and manages them over a system's lifetime. Its four core functions are worth memorizing because they name the activities this series will keep circling back to:

- **Govern** — culture, policy, roles, and accountability for AI risk.
- **Map** — establish context and identify risks for a given system.
- **Measure** — analyze, benchmark, and track those risks (this is where red-teaming and evals live).
- **Manage** — prioritize and act on risks, with monitoring over time.

Security engineering supplies the technical controls; the AI RMF is the loop that decides where to point them and proves you did.

---

## The shift: from securing code to securing the system

Put the three models on one page and the paradigm shift is concrete. A traditional web-security checklist assumes a trust boundary you can harden and a deterministic core you can reason about. An AI system has neither, so the surface expands to five layers, each with its own controls:

- **Data** — what's in the prompt, the retrieval corpus, and the training/fine-tuning set. Untrusted content in any of these is an injection or poisoning vector.
- **Model** — availability, integrity, and provenance of the model itself, including where it came from (supply chain).
- **Prompts** — the system prompt is code *and* a target; never put a secret or a sole security control there.
- **Tools** — the model's hands. Every capability is granted power an attacker will try to borrow; least privilege is non-negotiable.
- **Outputs** — treat every completion as untrusted input to whatever consumes it.

No single control secures all five, which is why the tone of this series is **defense in depth**. A guardrail model, output validation, least-privilege tools, human-in-the-loop approval for sensitive actions, and monitoring are not alternatives to each other — they are layers, and you want an attacker to have to defeat all of them.

---

## The road map for this series

This opener is the map. The next ~8 posts each take one layer deep, with working Python where code clarifies the defense:

1. **The AI Security Landscape** (this post) — the attack surface and the mental models.
2. **Prompt Injection** — direct and indirect, jailbreaks, and why "just tell the model to ignore malicious instructions" is not a control (LLM01, LLM07).
3. **Data Security & Privacy** — PII in prompts and logs, minimization, retention, and preventing sensitive-information disclosure (LLM02).
4. **Insecure Output Handling & Excessive Agency** — treating output as untrusted, and constraining tool power to least privilege (LLM05, LLM06).
5. **RAG & Supply Chain Security** — poisoned documents, embedding/retrieval attacks, and vetting models, datasets, packages, and MCP/tool servers (LLM03, LLM04, LLM08).
6. **Guardrails** — input/output filtering, classification, and orchestration patterns that actually reduce risk (and their limits).
7. **Securing the Pipeline** — CI/CD for prompts and models, secrets, provenance, and monitoring in production.
8. **Red-Teaming AI Systems** — adversarial testing, using ATLAS to structure attacks, and measuring your defenses (NIST *Measure*).

---

## Key takeaways

- **The core assumption flipped.** LLMs read instructions and data on one channel, so "trusted code, untrusted data" no longer holds — the model is an untrusted component inside your boundary.
- **Three properties drive everything:** shared instruction/data channel, tools that turn text into action, and non-deterministic, attacker-influenceable output.
- **The enforceable trust boundary is in your code, not the model.** You control what reaches the model and what its output is allowed to do; place validation and guardrails at those two edges.
- **Use three frameworks for three jobs:** OWASP Top 10 for LLM Applications to enumerate vulnerabilities, MITRE ATLAS to reason about adversary behavior, NIST AI RMF to govern and measure.
- **Secure the whole system, defense in depth.** Data, model, prompts, tools, and outputs each need controls; no single layer is sufficient.

Security for AI is not web security with a new logo, and it is not a solved problem you can buy your way out of. It is systems engineering under the assumption that a powerful component in the middle of your architecture can be turned against you at any time. The rest of this series is about building so that when it is, the damage stops at the next layer.

---

## Further reading

- [OWASP Top 10 for Large Language Model Applications](https://genai.owasp.org/llm-top-10/) — the authoritative, versioned risk taxonomy from the OWASP GenAI Security Project.
- [OWASP GenAI Security Project](https://genai.owasp.org/) — companion guides on LLM and agentic security, including red-teaming and secure deployment.
- [MITRE ATLAS](https://atlas.mitre.org/) — the adversarial tactics-and-techniques matrix and case studies for AI systems.
- [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) — Govern / Map / Measure / Manage functions for AI risk.
- [NIST AI RMF Generative AI Profile (NIST AI 600-1)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) — GenAI-specific risk guidance layered on the core framework.
