# Threat Modeling and the AI Attack Taxonomy

*Before you attack an AI system you need a map of it: the components an adversary can influence, the trust boundaries between them, and a taxonomy that sorts attacks by goal and stage so your red-teaming is systematic instead of a grab-bag of the attacks that happen to trend that week.*

---

Red-teaming an AI system without a threat model is like penetration-testing a building by trying the front-door handle and going home. You will find the obvious weakness, feel productive, and miss the loading dock that was propped open the whole time. The first post in this series argued that AI red-teaming is a discipline, not a party trick. This post gives you the two artifacts that make it a discipline: a **threat model** of your specific system, and a **taxonomy** that lets you reason about the full space of attacks rather than the handful you already know how to run.

The taxonomy here is derived from three public references — NIST's *Adversarial Machine Learning* taxonomy (NIST AI 100-2), the MITRE ATLAS knowledge base of real-world attacks on ML systems, and the OWASP GenAI/LLM Top 10. Everything below is expressed in my own words and framed for defenders. The point is not to memorize categories; it is to be able to look at *your* deployment and say "these four attacks are likely and high-impact for us, and these six are theoretically possible but irrelevant" — and then spend your time on the four.

---

## What an AI system actually is

The mistake beginners make is treating "the AI" as a single opaque box that either behaves or misbehaves. An AI *system* is a pipeline of components, and an attacker can influence far more of that pipeline than the model weights. Threat modeling starts by drawing every component and asking one question at each: **can an adversary reach this, directly or indirectly, and what happens if they can?**

- **The model** — the weights themselves, whether hosted (OpenAI, Anthropic, a Foundry endpoint) or self-hosted. For hosted models you inherit the provider's training-time posture; you cannot poison what you did not train.
- **The system prompt and prompt-construction logic** — the instructions, the templating, the way user input is concatenated with trusted text. This is where the boundary between "your instructions" and "their input" is drawn, and drawn badly it is where prompt injection lives.
- **Training / fine-tuning data** — only relevant if you train or fine-tune. If you fine-tune on data scraped from the web, user submissions, or a partner feed, that feed is an attack surface.
- **The RAG corpus and retrieval layer** — documents you index, plus the retriever that decides which chunks reach the model. Every document is content the model will read and partly trust.
- **Tools and plugins** — functions, API calls, code execution, MCP servers. Tools turn "the model said something wrong" into "the model *did* something wrong," which is a categorically worse failure.
- **Guardrails** — input/output filters, classifiers, moderation, allow/deny lists. These are controls, but they are also components that can be bypassed, and their presence can lull you into thinking a surface is covered when it is not.
- **The surrounding application** — auth, session handling, rate limiting, logging, the way tool outputs are rendered back to a user (an XSS sink in the chat UI is still your problem).

**The gotcha:** the attack surface is *everything an attacker can influence*, not just the text box the user types into. RAG and tools quietly widen it the most. The moment you retrieve an untrusted document or ingest the output of an external tool, that content flows into the model's context with some degree of trust — and an attacker who can plant a document in your corpus or control an API you call has an *indirect* injection path that never touches your prompt box. Teams draw their threat model around the chat input and forget the corpus.

---

## Trust boundaries: where influence crosses into the system

A trust boundary is any point where data or control passes from a less-trusted zone to a more-trusted one. Attacks happen at boundaries. Here is a minimal system with the boundaries marked.

```text
        UNTRUSTED                    |         YOUR SYSTEM (more trusted)
                                     |
  End user input ──────────────[ B1 ]──► Prompt construction ──► Model
                                     |         ▲                    │
  Web / 3rd-party docs ─────────[ B2 ]──► RAG corpus ──► Retriever ─┘
                                     |                              │
  External API / tool output ──[ B3 ]──────────────────► Tools ◄───┤
                                     |                              │
  Training / fine-tune feed ───[ B4 ]──► (only if you train)       ▼
                                     |                         Guardrails ─[ B5 ]─► App / user
                                     |
   B1  user prompt        → prompt injection, jailbreak
   B2  ingested documents → indirect prompt injection, poisoned RAG
   B3  tool/API responses → indirect injection, confused-deputy actions
   B4  training data       → data poisoning, backdoors (train-time only)
   B5  model output → app  → unsafe rendering, over-trusted tool calls
```

For each boundary, write down: who can put data across it, what validation exists, and what the model is allowed to *do* with what crosses. B1 is the one everyone tests. B2 and B3 are the ones that get real systems compromised, because the content arriving there looks trustworthy to the model and is often invisible to the human operator.

**The gotcha:** guardrails at B5 are not a boundary you can rely on alone. An output filter that catches slurs will not catch a model that was steered into leaking a customer record or calling a delete-account tool — the text looks benign. Defense has to sit at the boundary where the untrusted influence *enters* (B1–B4), not only where the answer leaves.

---

## The taxonomy: sort attacks by goal and by stage

Two axes make the attack space tractable. The **attacker's goal** tells you *what they want*, and the **lifecycle stage** tells you *when they strike*. NIST AI 100-2 organizes adversarial ML along essentially these lines; MITRE ATLAS maps them to observed tactics and techniques. Naming an attack by both axes ("an inference-time integrity attack via indirect injection") is more useful than a scary label, because it tells you where to defend.

### By attacker goal

- **Integrity** — make the system produce the *wrong* output while looking normal. Evasion, prompt injection that overrides instructions, poisoning that plants a specific wrong behavior. The output is confidently incorrect or attacker-chosen.
- **Availability** — deny service or blow up cost. Inputs crafted to trigger the most expensive path, unbounded tool loops, retrieval that fans out, or "sponge" prompts that maximize tokens/compute. For metered LLM APIs, availability attacks are often *cost* attacks — a denial-of-wallet.
- **Privacy / confidentiality** — extract something that should stay inside: training data (membership inference, memorized secrets), the system prompt, RAG documents the user should not see, or the model itself (extraction/distillation).
- **Abuse / safety** — get the system to produce harmful content or take harmful action it is supposed to refuse: disallowed instructions, harassment, or misuse of a tool to reach a downstream target. This is the "make it say/do the bad thing" bucket that most public jailbreak demos live in.

### By lifecycle stage

- **Training time** — the adversary influences the model *before* deployment. **Data poisoning** taints the training/fine-tuning set to shift behavior; a **backdoor** poisons it so the model behaves normally until a specific trigger appears, then flips. Requires influence over B4.
- **Inference time** — the adversary influences the model *at query time* through inputs and context. **Evasion** perturbs an input to get a wrong classification; **prompt injection** (direct at B1, indirect at B2/B3) overrides instructions; **jailbreaks** defeat safety training to elicit refused content. No access to weights needed.
- **Model theft / extraction** — the adversary targets the asset itself: repeated querying to reconstruct behavior (distillation), stealing weights via a leak, or inferring architecture/parameters. Part reconnaissance, part endgame.

### Goal × stage, with where each lands in this series

| | Training-time | Inference-time | Extraction / theft |
|---|---|---|---|
| **Integrity** | Data poisoning; targeted backdoors | Evasion; prompt injection (direct + indirect); jailbreak-to-misbehave | — |
| **Availability** | Poisoning to degrade accuracy broadly | Sponge / cost-amplifying inputs; unbounded tool or retrieval loops | — |
| **Privacy** | Planting memorizable secrets to exfiltrate later | Training-data extraction; system-prompt / RAG leakage | Model extraction / distillation; weight theft |
| **Abuse / safety** | Backdoor that unlocks harmful behavior on a trigger | Jailbreaks; indirect injection that drives harmful tool actions | — |

Posts 3–5 in this series are deep dives that map directly onto this table: **post 3** takes the inference-time integrity row — prompt injection (direct and indirect) and jailbreaks, the highest-likelihood attacks for almost every LLM deployment. **Post 4** takes the privacy column — system-prompt leakage, RAG/data exfiltration, and model extraction. **Post 5** takes the training-time row plus availability — poisoning, backdoors, and denial-of-wallet — the lower-frequency but high-consequence tail. Seeing the whole grid first is what keeps the deep dives from feeling like a random walk.

---

## Attacker knowledge: white, black, and gray box

The same goal is a different attack depending on what the adversary knows. This shapes both how *you* red-team and how realistic a given test is.

- **White-box** — full knowledge: weights, architecture, system prompt, guardrail logic. Enables gradient-based evasion and precise attacks. Realistic for open-weight models you ship, and the right assumption when you want a *worst-case* internal test.
- **Black-box** — query access only, like a normal user. Most external attackers live here; most prompt-injection and jailbreak work is black-box. This is the baseline threat for any public endpoint.
- **Gray-box** — partial knowledge: the model family is known, the system prompt has leaked, or error messages reveal tool names. Real attackers accumulate gray-box knowledge over time through probing, so treat black-box as a starting point that erodes.

A useful default: red-team your **public** surfaces black-box first (that is what real users have), then escalate to gray/white-box to find the ceiling of what a determined, informed adversary could do.

---

## Prioritization: likelihood × impact for *your* system

The taxonomy is the menu; the threat model tells you what to order. Score each relevant attack by **likelihood** (how reachable is the surface, how much attacker skill/access is needed) times **impact** (what breaks if it succeeds — wrong answer, leaked data, real-world action, cost blowout). Then rank. Two systems built on the same hosted model can have opposite priorities.

| Factor | Public consumer chatbot | Internal RAG tool (authenticated staff) |
|---|---|---|
| Who can reach the input | Anyone on the internet | Vetted, authenticated employees |
| Highest-likelihood attacks | Jailbreaks, abuse/safety, cost/DoS | Indirect injection via ingested docs; privilege/data-scope errors |
| Privacy blast radius | System-prompt leak, brand damage | Cross-tenant / cross-department data leakage |
| Tool danger | Usually few or no write tools | Often real tools (tickets, records, actions) → confused deputy |
| Training-time risk | Low (hosted model) | Low–medium (higher if you fine-tune on internal/partner data) |

The public bot's nightmare is a viral jailbreak or a denial-of-wallet spike; its users are anonymous and its reputation is exposed. The internal tool's nightmare is an indirect injection buried in an uploaded PDF that makes the assistant leak another team's data or fire off a tool call — its users are trusted, but the *documents* are not, and the tools have teeth.

**The gotcha:** training-time attacks (poisoning, backdoors) are **low-likelihood-high-impact** for the large majority of teams, because you are calling a hosted model you did not train — there is no training set for you to poison. That calculus flips the instant you fine-tune on externally sourced data (scraped text, user submissions, a partner feed). Then B4 is live, the impact is a persistent backdoor rather than a single bad answer, and poisoning jumps up your priority list. Decide which regime you are in before you decide whether to test it.

**The gotcha:** do not copy someone else's test plan. A jailbreak checklist built for a public consumer bot will waste your week if your system is an internal RAG tool whose real exposure is untrusted documents and over-scoped tools — and vice versa. The published red-team writeups are excellent for *technique*; they are not a substitute for scoring *your* likelihood × impact. The threat model is what makes the taxonomy actionable for the system you actually run.

---

## Key takeaways

- **Model the system, not "the AI."** Enumerate every component — model, prompt logic, training data, RAG corpus, retrieval, tools, guardrails, surrounding app — and mark the trust boundaries where an adversary can inject influence (B1–B4), not just where output leaves (B5).
- **The attack surface is everything attacker-influenceable.** RAG documents and tool/API outputs widen it the most and are the boundaries teams most often forget.
- **Sort attacks by goal × stage.** Integrity, availability, privacy, and abuse across training-time, inference-time, and extraction covers the space NIST AI 100-2 and MITRE ATLAS describe — and tells you *where* to defend.
- **Attacker knowledge sets realism.** Test public surfaces black-box first (that is real users), then escalate to gray/white-box to find the ceiling.
- **Prioritize by likelihood × impact for your deployment.** A public chatbot and an internal RAG tool have opposite threat profiles; training-time attacks are low-likelihood until you fine-tune on external data, then they are not.
- **Know your specific threat profile before you start attacking.** Red-teaming without a threat model is just poking at the flashy stuff and missing what matters for you.

---

## Further reading

- [NIST AI 100-2 — Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations](https://csrc.nist.gov/pubs/ai/100/2/e2025/final)
- [MITRE ATLAS — Adversarial Threat Landscape for Artificial-Intelligence Systems](https://atlas.mitre.org/)
- [OWASP Top 10 for Large Language Model Applications](https://genai.owasp.org/llm-top-10/)
- [OWASP GenAI Security Project](https://genai.owasp.org/)
- [Microsoft — Lessons from red teaming 100 generative AI products](https://www.microsoft.com/en-us/security/blog/2025/01/13/3-takeaways-from-red-teaming-100-generative-ai-products/)
- [Google — Google's AI Red Team: the ethical hackers making AI safer](https://blog.google/technology/safety-security/googles-ai-red-team-the-ethical-hackers-making-ai-safer/)
