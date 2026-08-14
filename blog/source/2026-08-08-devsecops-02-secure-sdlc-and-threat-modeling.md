# Secure SDLC and Threat Modeling

*How to design security in from the first sketch instead of bolting it on before launch — mapping security work to every phase of the software lifecycle, grounded in the NIST Secure Software Development Framework, and using STRIDE-based threat modeling as the core design activity.*

---

The cheapest bug to fix is the one you designed out. A missing authorization check caught in a design review costs a conversation; the same gap caught in penetration testing costs a sprint; caught in production after a breach, it costs an incident, a disclosure, and trust you may not get back. "Shift left" is the industry's shorthand for this, but the phrase gets flattened into "run a scanner earlier in CI." The real leftmost shift happens *before there is any code to scan* — in requirements and design, where you decide what the system is allowed to do and who is allowed to do it.

This post is about that leftmost work: building a secure software development lifecycle (SDLC) where security is an activity in every phase, and about threat modeling — the highest-leverage design activity for finding the flaws that scanners never will. Scanners find *bugs* in code you wrote. Threat modeling finds *flaws* in decisions you made. Only one of them can be done on a whiteboard before a single line exists.

---

## What a secure SDLC actually is

A secure SDLC is not a separate process that runs alongside development. It is your normal lifecycle with a security activity attached to each phase, so that security is a property you build rather than a gate you pass. The phases are the familiar ones — the security work is what you add at each.

```text
Requirements  →  Design  →  Implement  →  Test  →  Deploy  →  Operate
     │             │            │           │         │          │
 security      threat      secure       SAST /     hardened   monitoring,
 requirements  modeling,   coding,      DAST,      config,    logging,
 + abuse       DFDs,       code         security   secrets    patching,
 cases         trust       review,      test       mgmt,      incident
               boundaries  SCA          cases      IaC scan   response
```

- **Requirements** — write security requirements and abuse cases alongside functional stories. Decide your data classification and compliance obligations here, because they constrain everything downstream.
- **Design** — threat model the architecture. Draw the data-flow diagram, mark the trust boundaries, and enumerate what can go wrong before the shape of the system is locked in.
- **Implement** — apply secure coding standards, run software composition analysis (SCA) on dependencies, and review code with the threat model open next to it.
- **Test** — turn each identified threat into a test. Run static analysis (SAST) and dynamic analysis (DAST). Verify the mitigations you promised actually exist.
- **Deploy** — ship with hardened configuration, managed secrets, and scanned infrastructure-as-code. The safest default beats the documented workaround.
- **Operate** — monitor, log, patch, and rehearse incident response. Feed what you learn in production back into requirements and the threat model.

The loop matters more than the line. Operations feed requirements; a production incident becomes a new abuse case; a new feature reopens the threat model.

---

## NIST SSDF: a vocabulary for the practices

If you want a vendor-neutral, framework-neutral checklist of what "doing security in the lifecycle" means, the NIST Secure Software Development Framework (SP 800-218) is the reference worth internalizing. It deliberately avoids prescribing tools or a specific methodology. Instead it organizes practices into four groups, described here in my own words:

- **Prepare the Organization (PO)** — make sure the people, process, and tooling are ready *before* a project starts. Define your security requirements once, assign roles and responsibilities, provide a toolchain, and set the criteria for what "secure enough to ship" means. This is the work that stops every team from reinventing security from scratch.
- **Protect the Software (PS)** — guard the code and its provenance. Protect source from tampering, verify the integrity of what you release so consumers can trust it, and archive the exact inputs to each build so you can reproduce and investigate later. This is the supply-chain half of the story.
- **Produce Well-Secured Software (PW)** — the design-and-build core. Threat model to identify risks, follow secure design practices, reuse vetted components rather than rolling your own crypto, write code to secure standards, review and test it, and configure secure defaults. Most of what this post covers lives here.
- **Respond to Vulnerabilities (RV)** — assume something will slip through. Have a way to receive vulnerability reports, analyze and remediate them, and — crucially — do root-cause analysis so the *class* of bug gets designed out, not just the one instance patched.

The value of SSDF is not the acronyms; it forces you to ask "do we have a practice for this?" in each group. A team strong on PW (they write careful code) but weak on RV (no disclosure channel, no root-cause loop) keeps re-shipping the same flaw. Read the four groups as a coverage map.

**The gotcha:** SSDF describes *what* practices to have, not *how* to implement them — that's intentional, and it's where teams stall. "Threat model to address risks" (practice PW.1) is one line in the framework; the rest of this post is how you actually do it. Treat SSDF as the outline and threat modeling as the method, not the other way around.

---

## Security requirements and abuse cases

Functional requirements say what the system should do for a cooperative user. Security requirements say what the system must *not* do for a hostile one — and what it must do *even when* someone is hostile. If you only write the former, security becomes whatever the implementer happened to remember on a Tuesday.

A useful reframing at requirements time is the **abuse case**: a user story written from the attacker's point of view. For every "As a user, I can reset my password by email," write the shadow story:

```text
User story:  As a customer, I can reset my password via an emailed link
             so that I can regain access when I forget it.

Abuse case:  As an attacker, I request password resets for an email I
             don't own, hoping to (a) enumerate which emails have accounts,
             (b) reuse a leaked reset link, or (c) flood the victim's inbox.

Derived security requirements:
  - Reset responses are identical whether or not the account exists.
  - Reset tokens are single-use, high-entropy, and expire within N minutes.
  - Reset requests per account and per IP are rate-limited.
  - Every reset request and completion is logged with source and timestamp.
```

Notice how the abuse case *generates* concrete, testable requirements. That is its job. "Be secure" is not a requirement anyone can build or verify; "reset responses are identical whether or not the account exists" is both.

**The gotcha:** security requirements you don't write down don't get built, and they don't get tested. An implicit expectation living only in a security engineer's head is not a requirement — it's a hope. If it isn't in the backlog with acceptance criteria, assume it won't exist in the product.

---

## Threat modeling: the four questions

Threat modeling is the structured practice of examining a design to find what can go wrong before you build it. Strip away the frameworks and it comes down to four questions, popularized by the threat-modeling community as the spine of any session:

1. **What are we building?** Draw the system as it actually is — components, data stores, the flows between them, and where trust changes hands. A shared, accurate picture is half the work.
2. **What can go wrong?** Walk the picture and enumerate threats. This is where a structured lens like STRIDE keeps you from only imagining the attacks you already fear.
3. **What are we going to do about it?** For each credible threat, decide: mitigate, eliminate (remove the feature/data), transfer (push the risk to a provider), or knowingly accept it.
4. **Did we do a good job?** Review the model against the built system. Are the mitigations real? Did the design change and leave the model stale?

The fourth question is the one teams skip, and it's the one that turns threat modeling from a document into a practice.

---

## STRIDE: a structured lens for "what can go wrong"

STRIDE is a mnemonic from Microsoft that gives question 2 some rigor. Each letter is a category of threat, and each is the violation of a security property you presumably want. Pointing STRIDE at each element of your diagram is a systematic way to surface threats you wouldn't brainstorm on your own.

| Threat | What it means | Property it violates |
|---|---|---|
| **S**poofing | Pretending to be someone or something you're not | Authentication |
| **T**ampering | Modifying data or code in transit or at rest | Integrity |
| **R**epudiation | Denying an action with no evidence to prove otherwise | Non-repudiation |
| **I**nformation disclosure | Exposing data to those not entitled to it | Confidentiality |
| **D**enial of service | Exhausting or degrading a resource so others can't use it | Availability |
| **E**levation of privilege | Gaining capabilities beyond what you were granted | Authorization |

You don't apply all six to everything with equal weight. External entities are mostly about spoofing and repudiation; data stores draw tampering, information disclosure, and denial of service; processes are exposed to all six. The letters are prompts — "could someone spoof this? tamper with that?" — walked element by element.

**The gotcha:** STRIDE is a prompt to think, not a checklist to rubber-stamp. The value isn't a grid with a checkmark in every cell — it's the conversation the grid provokes. A team that fills in "S: N/A, T: N/A" down the column in ten minutes has performed the ritual and skipped the point. The finding you didn't expect is worth more than the six you did.

---

## Data-flow diagrams and trust boundaries

You can't reason about threats against a picture you don't have. The workhorse artifact of threat modeling is the data-flow diagram (DFD): external entities, processes, data stores, and the flows between them. The single most important thing you add to it is the **trust boundary** — the line where the level of trust changes, and therefore where data must be validated and identity must be checked.

Here is a deliberately small example: a web app with an API and a database, plus a third-party payment provider.

```text
      ┌─────────── trust boundary: public internet ───────────┐
      ╎                                                        ╎
  [ Browser ] ──(1) HTTPS request──▶ [ Web / API server ]     ╎
   external                                │    ▲              ╎
      ╎                                    │    │              ╎
      └────────────────────────────────────────────────────────┘
                                           │    │ (2) SQL over
      ┌──── trust boundary: private network ────┐  private link
      ╎                                    ▼    │             ╎
      ╎                             [ Application DB ]         ╎
      ╎                                  data store            ╎
      └─────────────────────────────────────────────────────────┘
                                           │
                          (3) HTTPS + API key
                                           ▼
                              [ Payment provider ]  ← external, another trust domain
```

Every flow that *crosses* a boundary is where you focus. Flow (1) crosses from the untrusted internet into your server — that's where authentication, input validation, and TLS live. Flow (2) stays inside the private network but still crosses from application to data store — that's where least-privilege DB credentials and parameterized queries live. Flow (3) leaves your trust domain entirely for a third party — that's where you protect the API key and validate what comes back, because you don't control the other end.

Boundaries are where threats concentrate because they are where assumptions change. Inside a boundary you can assume some things about the caller; the instant a flow crosses one, those assumptions are the attacker's to break.

---

## From threats to tracked mitigations

Enumerating threats produces a list; the list is worthless until each entry has an owner, a mitigation, and a way to know the mitigation works. Walk each element of the DFD, apply STRIDE, and record the result in a small table. Here's a slice for the example above.

| Element / flow | STRIDE threat | Mitigation | Test |
|---|---|---|---|
| Browser → API (1) | Spoofing: attacker replays a stolen session | Short-lived signed session tokens; rotate on privilege change | Test that an expired/rotated token is rejected |
| Browser → API (1) | Tampering: malicious input in request body | Server-side validation + parameterized queries | Injection test cases in the CI suite |
| API → DB (2) | Elevation: app account can drop tables | DB user scoped to least privilege (no DDL) | Assert DDL statements fail under the app role |
| Application DB | Information disclosure: DB dump leaks PII | Encrypt sensitive columns at rest; restrict backups | Verify ciphertext at rest; audit backup ACLs |
| API → Payment (3) | Info disclosure: API key committed to source | Secret in a vault, injected at runtime; secret scanning | CI secret-scan blocks committed credentials |
| API process | Repudiation: user denies making a purchase | Append-only audit log with request id + identity | Test that each purchase writes an immutable log entry |

**The gotcha:** a threat with no tracked mitigation and no test is just a scary note in a document nobody opens again. The output of threat modeling is not the diagram or the STRIDE grid — it's a set of backlog items, each with a mitigation and a test, tracked like any other work. If the finding can't be traced from "what can go wrong" to a merged test, the model didn't change the software; it just decorated a wiki.

---

## Prioritizing with risk

You will find more threats than you can fix before the deadline. Prioritize with a simple risk estimate: **risk = likelihood × impact**. Likelihood folds in how exposed the element is, how skilled an attacker must be, and whether an exploit already exists in the wild. Impact folds in what's lost — data sensitivity, blast radius, regulatory consequence.

You don't need a five-decimal score. A 3×3 grid (low/medium/high per axis) is enough to sort the list into "fix now," "fix soon," and "accept and document." The goal is a defensible ordering, not false precision — an over-engineered scoring model just moves the arguing from "which is worse" to "what's the exact number."

Accepting a risk is a legitimate outcome — *if* someone with authority made the decision on purpose and wrote it down, with the reasoning and a review date. Silent acceptance (nobody decided; it just never got fixed) is how the worst incidents start.

---

## Make it continuous, not a one-time ceremony

The most common failure mode isn't a bad threat model — it's a good one done once, at kickoff, and never touched again. Systems evolve: you add an admin panel, a new integration, a caching layer, a mobile client. Each change can add a trust boundary or a flow the original model never considered.

Lightweight, continuous threat modeling beats a heavyweight annual one. Attach a small step to your existing design reviews and pull requests: when a change adds a trust boundary, a new external dependency, or touches authentication/authorization, spend fifteen minutes on the four questions for *that change*. Keep the DFD in the repo next to the code so it's a diff, not an archaeology project.

**The gotcha:** threat modeling done once at project start and never revisited goes stale exactly as fast as the architecture changes — which is to say, immediately. A threat model that describes last quarter's system gives false confidence about this quarter's. The practice is continuous or it's theater; make it small enough to actually repeat.

---

## Key takeaways

- **The leftmost shift is design, not tooling.** Running scanners earlier is good; deciding what the system may do — and who may do it — before there's code is where the cheapest fixes live.
- **SSDF is the coverage map, threat modeling is the method.** Use the four practice groups (Prepare, Protect, Produce, Respond) to check you have a practice for each concern; use threat modeling to satisfy the "produce well-secured software" core.
- **Write security requirements down as abuse cases.** An implicit expectation isn't a requirement. Turn each user story into its hostile shadow and derive testable constraints.
- **Answer the four questions, and use STRIDE as a prompt.** What are we building, what can go wrong, what do we do, did we do a good job — with STRIDE walked element by element to spark the discussion, not to fill a grid.
- **Draw the DFD and mark the trust boundaries.** Threats concentrate where assumptions change; every flow that crosses a boundary is a place to focus.
- **A finding without a tracked mitigation and a test is not done.** Prioritize with likelihood × impact, convert each accepted threat into backlog items, and make the model continuous so it never goes stale.

---

## Further reading

- [NIST SP 800-218: Secure Software Development Framework (SSDF)](https://csrc.nist.gov/pubs/sp/800/218/final) — the four practice groups in the primary source.
- [Microsoft: Threat Modeling and the STRIDE model](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats) — STRIDE categories and how Microsoft applies them.
- [The Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/) — the four questions, values, and principles from the practitioner community.
- [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html) — a practical, hands-on walkthrough of the process.
