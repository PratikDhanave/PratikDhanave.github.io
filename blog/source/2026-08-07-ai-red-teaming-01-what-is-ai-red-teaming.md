# What AI Red Teaming Is

*The opening post of a hands-on series for builders: what it means to systematically stress-test an AI system — model, prompts, retrieval, tools, and guardrails — to surface its failures before adversaries or ordinary users do, how that differs from pentesting and robustness testing, and the frameworks and ethics that keep the work rigorous.*

---

You shipped an assistant. It refuses the obvious "ignore your instructions" prompt, so the demo looks safe. Then a support ticket arrives: a user pasted a web page into the chat, the page contained hidden text, and your agent followed it — booked a refund, emailed a stranger, summarized a document it should never have opened. Nobody attacked you in the classic sense. The system simply did what the words told it to, and the words came from the wrong place.

**AI red teaming** is the practice of finding that failure on purpose, before it finds you. You take the deployed system — not the raw model, the *whole* pipeline — and you attack it the way a motivated adversary or a careless user would, methodically, under authorization, so that every failure you provoke becomes a bug you can fix. This series is written for the people who build these systems and are responsible for hardening them. It is defensive from the first line to the last.

This companion note is worth stating up front: the site already has an [AI Security Engineering series](/blog/tags/ai-security/), whose finale, [AI Red-Teaming and Testing](/blog/posts/ai-security-08-red-teaming-and-testing.html), turns that series' attacks into a CI regression suite. This new series starts where that post's summary ends and goes deeper — a dedicated arc on the discipline itself, its taxonomy, its tooling, and its measurement. Where the earlier post gives you a test file, this series gives you a program.

---

## What "red teaming" means when the target is a model

The term is borrowed from military and security practice: a red team plays the adversary so the blue team can improve its defenses. Applied to AI, the target is unusual, and three properties make it its own discipline rather than a rebranding of penetration testing.

**The target is probabilistic, not deterministic.** A SQL injection either works or it doesn't; the same payload against the same endpoint gives the same result every time. A prompt-injection payload against a language model might succeed on the first try, fail on the next four, and succeed again on the sixth — same input, different sampled output. This changes everything about how you test. A single passing run proves nothing. You have to think in *attack success rate* over many trials, across temperatures and phrasings, which is a statistical claim, not a boolean.

**The model itself is part of the attack surface.** In a normal application the code is trusted and the input is suspect. In an AI application the boundary blurs: instructions and data arrive through the same channel — natural language — and the model has no reliable, built-in way to tell "this is my policy" from "this is content a user pasted." That confusion *is* the vulnerability class. You are not just testing code that surrounds a model; you are testing the model's own judgment under adversarial pressure.

**The harms extend past confidentiality, integrity, and availability.** Classic security lives in the CIA triad. AI systems fail in additional dimensions that a port scanner has no concept of:

```text
Traditional security harms        AI-system harms (in addition)
--------------------------        -------------------------------
Confidentiality  -> data leak     Safety    -> harmful/illegal content
Integrity        -> tampering     Bias      -> discriminatory outputs
Availability     -> outage        Privacy   -> training-data / PII leakage
                                  Misuse    -> weaponization, fraud aid
                                  Truth     -> confident fabrication
```

A red-team engagement that only checks whether the model leaks secrets has skipped most of what makes AI risk distinctive.

**The gotcha:** because outputs are non-deterministic, "I couldn't reproduce it" is not the same as "it's fixed." Treat a single failed reproduction as weak evidence. Re-run the attack dozens of times, vary the wording, and report a rate — otherwise you will close bugs that are still live in production.

---

## How it differs from pentesting and from robustness testing

It is easy to file AI red teaming under two things it resembles. Both comparisons are instructive precisely because of where they break down.

**Versus traditional penetration testing.** A pentest of your AI product is still necessary — the application is a web application first, with auth, sessions, dependencies, and infrastructure that all need the usual scrutiny. But a pentest targets the plumbing; AI red teaming targets the *cognition* layered on top. The most damaging AI vulnerabilities live in the seams a pentester never inspects: the system prompt, the retrieval step that pulls in untrusted documents, the tool bindings that let the model take actions, and the code that consumes the model's output. You need both. Running only a pentest and declaring the AI safe is the most common mistake teams make.

**Versus ML robustness testing.** Robustness testing — adversarial examples, perturbation studies, distribution-shift evaluation — asks whether a *model* stays accurate when its inputs are nudged. That is a model-quality question, usually run by the team that trained or fine-tuned the model, against the model in isolation. Red teaming asks whether the *deployed system* can be made to do something harmful, run against the integrated pipeline including the tools and data it touches at runtime. A model can be admirably robust in isolation and still be trivially exploitable once you wire it to a database and feed it a poisoned document. The vulnerability lives in the integration, and only integrated testing finds it.

| Dimension | Pentesting | ML robustness testing | AI red teaming |
|---|---|---|---|
| Unit under test | Infrastructure & app | Model in isolation | Deployed pipeline (model + prompts + RAG + tools + guardrails) |
| Determinism | Deterministic | Mostly deterministic | Probabilistic — needs repeated trials |
| Primary harms | CIA triad | Accuracy under perturbation | CIA plus safety, bias, privacy, misuse |
| Typical owner | Security team | ML / research team | Security + ML + safety, jointly |
| Verdict | Exploitable / not | Accuracy delta | Attack success rate over trials |

---

## The scope: security *and* safety

A narrow reading of red teaming stops at security — can an attacker steal data or hijack the agent? That is essential, and much of this series covers it. But responsible AI red teaming has a wider remit, because the people harmed by an AI system are not only the ones an attacker targets. Four scope areas sit alongside classic security:

- **Harmful content.** Does the system produce dangerous, illegal, or abusive output when coaxed — through role-play, hypothetical framing, or incremental escalation? This is where jailbreaks and safety guardrails live.
- **Bias and fairness.** Does it treat users differently along protected attributes — refusing, stereotyping, or degrading quality based on names, dialects, or demographics inferable from the prompt?
- **Privacy leakage.** Does it emit personal data — from its training corpus, from another user's session, or from retrieved documents it should not surface?
- **Misuse and dual use.** Can an ordinary user, not an attacker, bend the system toward fraud, harassment, or manipulation at scale?

These are not soft concerns bolted onto the "real" security work. A model that leaks another customer's PII has failed on both privacy and confidentiality at once. Scope your engagements to cover the safety dimensions deliberately, or you will ship a system that is hard to hack and easy to misuse.

---

## Who does it, and when

Red teaming is not a one-time gate before launch, and it is not one team's job. It works best as a collaboration and a habit.

**Who.** Effective engagements pull together security engineers who think in attack trees, ML engineers who understand the model's behavior, and safety or domain specialists who know what "harmful" means for *this* product. A medical assistant, a coding agent, and a children's education tool have wildly different harm profiles; the domain expert is what keeps the test set honest.

**When.** Two rhythms, both necessary:

```text
Pre-deployment            Continuous (post-deployment)
----------------          -----------------------------
Before each launch        Scheduled re-runs in CI
On major prompt changes   After model/version upgrades
On new tool integrations  On new data sources for RAG
Baseline the risk         Watch for regressions & drift
```

The pre-deployment pass establishes a baseline. The continuous cadence catches the reality that your risk changes without your code changing — a provider ships a new model version, a retrieval source starts ingesting user-generated content, a prompt tweak quietly reopens a jailbreak you had closed. The [AI Security finale](/blog/posts/ai-security-08-red-teaming-and-testing.html) shows the mechanics of wiring these checks into a build; this series will deepen the continuous side considerably.

---

## The frameworks this series builds on

Three primary sources give the work its structure. None is a tool you run; each is a taxonomy you test against, and this series draws on all three — in its own words, from the primary documents, never copied.

**OWASP Top 10 for LLM / Generative AI Applications.** A community-maintained catalog of the most significant risk categories for LLM-backed software — prompt injection, sensitive information disclosure, insecure output handling, excessive agency, supply-chain and data-poisoning risks, and more. Think of it as the checklist for *what* to test: it tells you the categories of failure that recur across real deployments, so your test plan has coverage rather than blind spots.

**MITRE ATLAS.** An ATT&CK-style knowledge base of adversary tactics and techniques observed against AI systems — reconnaissance, model access, poisoning, evasion, exfiltration, and impact. Where OWASP names the risks, ATLAS describes *how* an attack actually unfolds, stage by stage, so you can reason about realistic kill chains rather than isolated tricks.

**NIST AI 100-2, the adversarial machine learning taxonomy.** A rigorous, vendor-neutral vocabulary for attacks and mitigations across the ML lifecycle. It classifies attacks by the adversary's goal (availability, integrity, privacy, misuse), their capability, and their knowledge, and it spans both predictive and generative AI. When you need precise language for *what kind* of attack you are simulating — an evasion attack versus a poisoning attack versus a privacy-extraction attack — this is the reference. NIST's broader **AI Risk Management Framework** then supplies the govern / map / measure / manage cycle that turns scattered testing into a repeatable program.

Used together: OWASP scopes the checklist, ATLAS models the adversary, NIST AI 100-2 sharpens the vocabulary, and the AI RMF organizes the effort. Later posts lean on each in turn.

---

## Rules of engagement: this is defensive work

Everything in this series assumes you are testing systems you are authorized to test. That is not a disclaimer; it is the definition of the discipline. Red teaming without rules of engagement is just an attack. Four principles hold throughout:

- **Authorized.** You have explicit, written permission to test the target from someone who owns it. No permission, no engagement.
- **Scoped.** The systems, data, techniques, and time window are agreed in advance. You do not test production customer data because it was convenient, and you do not pivot to systems outside the scope.
- **Responsible disclosure.** Findings go to the people who can fix them, privately, with enough detail to reproduce and remediate — not to the public, and not to anyone who would weaponize them.
- **For builders, hardening their own systems.** The entire series is framed for teams strengthening the AI they operate. The techniques exist so you can close the holes, not open them elsewhere.

**The gotcha:** the same payload is either a defensive test or an attack depending entirely on authorization and intent. Keep the paper trail for every engagement. If you cannot point to who authorized a test, do not run it.

---

## What the rest of the series covers

Roughly eight posts, each going deeper than a single overview can. The arc moves from thinking to doing to measuring:

- **Threat modeling and the attack taxonomy** — mapping your specific system's assets, entry points, and adversaries against OWASP, ATLAS, and NIST categories.
- **Prompt injection and jailbreaks in depth** — direct and indirect injection, the reasons refusals leak, and why this remains the hardest category to close.
- **Data and model attacks** — poisoning, extraction, membership inference, and privacy leakage across the lifecycle.
- **Attacking agents and RAG** — the seams: tool bindings, excessive agency, and untrusted retrieved context as an injection vector.
- **Automated red teaming and tooling** — scaling from hand-crafted probes to generated attack suites and open-source frameworks.
- **Measuring and scoring** — attack success rate done honestly, judging non-deterministic outputs, and reporting that survives scrutiny.
- **Building a program** — cadence, ownership, disclosure, and standing red teaming up as a durable practice rather than a launch-day heroics.

By the end you should be able to threat-model an AI product, run a rigorous engagement against it, quantify what you found, and fix it — repeatably.

---

## Key takeaways

- **Red teaming targets the whole system.** The model, prompts, retrieval, tools, and guardrails together — not the model in isolation, where the most dangerous integration bugs stay hidden.
- **The target is probabilistic.** One passing run proves nothing; think in attack success rate over many trials, and never trust a single failed reproduction as a fix.
- **The harms are wider than CIA.** Safety, bias, privacy, and misuse sit alongside confidentiality, integrity, and availability — scope for all of them.
- **Frameworks give it rigor.** OWASP scopes *what* to test, ATLAS models *how* attacks unfold, NIST AI 100-2 sharpens the *vocabulary*, and the AI RMF *organizes* the program.
- **It is defensive by definition.** Authorized, scoped, responsibly disclosed, and aimed at builders hardening their own systems — that framing is what separates a red team from an attacker.

---

## Further reading

- [OWASP Top 10 for LLM Applications & Generative AI](https://genai.owasp.org/llm-top-10/) — the risk-category checklist for LLM-backed software.
- [MITRE ATLAS](https://atlas.mitre.org/) — adversary tactics and techniques observed against AI systems, ATT&CK-style.
- [NIST AI 100-2 — Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations](https://csrc.nist.gov/pubs/ai/100/2/e2025/final) — the vendor-neutral attack/mitigation taxonomy.
- [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) — the govern / map / measure / manage cycle for organizing the effort.
- [AI Red-Teaming and Testing](/blog/posts/ai-security-08-red-teaming-and-testing.html) — the AI Security Engineering series finale this series builds on.
