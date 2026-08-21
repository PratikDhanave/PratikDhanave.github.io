# KYC and Identity Verification

*Before you can serve a customer in a regulated business, you have to answer a deceptively hard question: are they really who they claim to be? KYC turns that question into an engineering pipeline — collect, verify, screen, risk-assess — and getting it right means balancing legal rigor against an onboarding experience that doesn't drive legitimate customers away.*

Every regulated customer relationship starts with **KYC (Know Your Customer)** — the obligation to verify a customer's identity before (and during) doing business with them. It exists to stop criminals, fraudsters, and sanctioned parties from using your service, and it's the first compliance system a customer encounters. This post covers KYC as an engineering problem: the verification pipeline, the risk-based approach, the perpetual tension between rigor and friction, and why KYC is never truly "done."

## What KYC is and why it exists

KYC is the set of processes for **establishing and verifying who your customer is**. In financial services it's a legal requirement — you cannot open accounts for unverified or prohibited parties — and its purpose is to prevent your service from being used for fraud, money laundering, terrorist financing, or sanctions evasion. The formal umbrella is often **CDD (Customer Due Diligence)**: understanding who the customer is and the risk they pose. KYC is the front door of compliance — if you don't correctly know who your customers are, every downstream control (AML monitoring, sanctions screening, reporting) is built on sand.

For engineers, KYC is a *pipeline*: take the identity information and documents a customer provides, verify them against authoritative sources, screen the person against watchlists, assess their risk, and record every step — turning a legal obligation into a sequence of automated (and sometimes manual) checks.

## The verification pipeline

A KYC flow typically moves through stages, each an engineering task:

```text
1. Collect     → gather identity data + documents (name, DOB, address, ID document, selfie)
2. Verify      → confirm the identity is real and belongs to this person
3. Screen      → check against sanctions/PEP/adverse-media lists (next posts)
4. Risk-assess → assign a risk level (drives how much scrutiny)
5. Decide      → approve, reject, or escalate to manual review
6. Record      → log every input, check, and decision immutably (auditability)
```

- **Collection** — capturing the required identity attributes and documents. The design tension starts here: every field and document you require adds friction, so you collect what's *needed* for the risk level, no more.
- **Verification** — the core technical challenge: confirming the identity is genuine and belongs to the applicant. Techniques include validating the identity against **authoritative data sources**, checking **document authenticity** (is this a real, unaltered ID?), and **biometric/liveness** checks (does the selfie match the ID, and is it a live person not a photo?) to prevent impersonation. This is increasingly automated, often with specialized verification providers.
- **Screening and risk assessment** feed the decision (below and next posts).
- **Decisioning** — approve clear cases automatically, reject clear failures, and **escalate ambiguous ones to human review**. Not every case can be decided by machine; a good KYC system routes the uncertain ones to trained reviewers.
- **Recording** — logging the entire process immutably, because you must later *prove* you verified this customer properly (auditability, the recurring meta-requirement).

The engineering goal is to automate as much as possible (for scale and speed) while routing genuine uncertainty to humans, and to record everything.

## The risk-based approach

A defining principle from the last post: KYC is **risk-based, not uniform.** Regulation generally expects you to apply *more* scrutiny to higher-risk customers and *less* to lower-risk ones, rather than treating everyone identically. This means KYC comes in graduated levels:

- **Simplified due diligence** — lighter checks for low-risk customers/products.
- **Standard due diligence** — the normal level for typical customers.
- **Enhanced due diligence (EDD)** — deeper investigation for high-risk cases: high-risk jurisdictions, unusual activity, or **politically exposed persons (PEPs)** (people in prominent public positions, who carry higher corruption/bribery risk and warrant extra scrutiny). EDD might involve verifying source of funds, additional documentation, and closer ongoing monitoring.

For engineers, this means the KYC system is *not* a single fixed flow — it's a **risk-scoring engine** that assesses each customer and applies the appropriate level of due diligence. You build a system that computes risk (from geography, product, customer type, behavior) and branches the verification depth accordingly. This graduation is central: it focuses effort where risk is, and applying uniform heavy checks to everyone is both wasteful and worse for legitimate low-risk customers.

## The rigor-versus-friction tension

KYC embodies the balance principle acutely: it must be **rigorous enough to satisfy regulators and stop bad actors, yet frictionless enough not to drive legitimate customers away.** These pull hard against each other:

- **Too much friction** — onerous verification (many documents, slow manual review, repeated requests) causes legitimate customers to **abandon onboarding**. In a competitive market, a painful KYC flow is a real business cost — customers leave for a smoother competitor. Onboarding conversion is a metric KYC directly affects.
- **Too little rigor** — lax verification lets fraudsters and prohibited parties in, causing compliance failures, fraud losses, and penalties.

The engineering art is maximizing rigor *per unit of friction*: use automation to verify quickly and invisibly where possible (instant checks against data sources, seamless document capture), reserve heavy friction for genuinely higher-risk cases (the risk-based approach), and make the necessary friction as smooth as possible. A well-engineered KYC flow verifies most legitimate customers in moments while catching and scrutinizing the risky ones — that's the target, and it's a genuine product-and-compliance co-design problem, not a pure legal one.

## KYC is ongoing, not one-time

A crucial and often-missed point: **KYC is not just an onboarding gate — it's continuous.** Verifying a customer once at signup isn't enough, because circumstances change:

- **Ongoing monitoring** — you must keep watching whether a customer's activity matches their profile and re-screen them against updated watchlists (a person can *become* sanctioned or a PEP after onboarding). This connects KYC to the AML transaction monitoring of the next post.
- **Periodic review / refresh** — re-verifying customer information on a schedule (more often for higher-risk customers, per the risk-based approach), because identities and risk profiles drift over time.
- **Trigger-based review** — re-assessing when something changes (a large unusual transaction, a change of address to a high-risk jurisdiction).

So KYC engineering isn't a one-shot pipeline but a *lifecycle*: verify at onboarding, then continuously monitor, periodically refresh, and re-screen. Designing for the whole lifecycle — not just the signup form — is what makes KYC genuinely compliant. With customers verified and continuously known, the next question is watching what they *do*: AML and transaction monitoring.

## Key takeaways

- KYC (Know Your Customer) is the legal obligation to verify who your customers are before and during business, to keep out fraudsters, launderers, and prohibited parties — it's the front door of compliance on which every downstream control depends.
- Engineered as a pipeline: collect identity data/documents → verify (authoritative sources, document authenticity, biometric/liveness) → screen → risk-assess → decide (auto-approve/reject or escalate uncertain cases to humans) → record immutably.
- It's risk-based, not uniform: apply simplified, standard, or enhanced due diligence (EDD for high-risk cases and politically exposed persons) via a risk-scoring engine that branches verification depth — focusing effort where risk is.
- KYC embodies the rigor-vs-friction tension: too much friction makes legitimate customers abandon onboarding (a real business cost), too little lets bad actors in — so maximize rigor per unit of friction with automation and risk-based scrutiny.
- KYC is a lifecycle, not a one-time gate: ongoing monitoring, periodic refresh, and trigger-based re-review (people can become sanctioned or PEPs after onboarding) — design for the whole relationship, not just signup.

## Further reading

- [Compliance as software (previous post)](/blog/posts/regtech-01-compliance-as-software.html)
- [Wikipedia — Know Your Customer](https://en.wikipedia.org/wiki/Know_your_customer)
- [The Fintech Engineering Handbook series](/blog/series/the-fintech-engineering-handbook/)
