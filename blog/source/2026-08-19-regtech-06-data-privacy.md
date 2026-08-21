# Data Privacy and Protection

*Compliance requires you to collect and keep a great deal of personal data; privacy law requires you to protect it, limit it, and sometimes delete it. Data privacy is the compliance domain that governs the data all the other controls depend on — and it turns "how you handle personal information" from a courtesy into a set of enforceable engineering obligations.*

KYC, AML, and screening all collect and process large amounts of **personal data**. Privacy regulation — GDPR and a growing set of similar laws worldwide — governs how you may lawfully handle it. This post covers data privacy as an engineering discipline: the core principles that shape system design, the individual rights you must be able to honor, and the tension with the compliance retention we met in the last post. Privacy is where "handle personal data responsibly" becomes concrete, buildable requirements.

## Why privacy is an engineering concern

Privacy laws (GDPR is the most influential, with many jurisdictions following similar models) grant individuals rights over their personal data and impose obligations on organizations that process it — backed by significant penalties. Crucially, these obligations are not satisfiable by a policy document; they require the *systems* to behave in specific ways: to collect only what's needed, to delete data on request, to export it, to secure it. That makes privacy an **engineering** concern — the way you model, store, process, and delete personal data must be *designed* to meet the obligations, which is the principle of **privacy by design**: building privacy into systems from the start rather than adding it later. Retrofitting privacy into a system that spread personal data everywhere with no way to find or delete it is enormously hard — so, like the other compliance domains, it must be built in.

## The core principles that shape design

A handful of privacy principles translate directly into system design decisions:

- **Lawful basis and consent** — you need a valid legal basis to process personal data, and where consent is the basis, it must be freely given, specific, and *recorded* (you must prove you have it). Engineering implication: track consent as data, per purpose, revocably.
- **Purpose limitation** — data collected for one purpose shouldn't be freely used for unrelated purposes. Implication: associate data with the purpose it was collected for, and don't repurpose it silently.
- **Data minimization** — collect and retain only the personal data you actually need. This is one of the most powerful principles for engineers because it *reduces risk and obligation at the source*: data you never collect can't be breached, can't be misused, and doesn't need to be deleted. Minimizing what you hold simplifies every other privacy obligation. (It also directly serves the audit-trail tension from the last post — minimize personal data in records.)
- **Storage limitation / retention** — don't keep personal data longer than necessary for its purpose. Implication: retention policies and the ability to delete data when its purpose (or legal retention period) ends.
- **Security** — protect personal data with appropriate technical measures (encryption, access control). A breach of personal data is both a privacy failure and often a reportable incident.
- **Accountability** — be able to *demonstrate* compliance with all of the above (the auditability theme, applied to data handling).

The standout for engineers is **data minimization**: the less personal data you collect and keep, the smaller your privacy risk and burden. It's the rare requirement that's also just good engineering hygiene — and it aligns neatly with the on-device/local-first privacy philosophy from the edge-AI series (data you never transmit can't leak).

## The individual rights you must honor

Privacy law grants individuals rights over their data, and your systems must be *able to execute* them — each is an engineering capability, not just a promise:

- **Right of access** — a person can request a copy of the personal data you hold about them. You must be able to *find and produce* all of it — which requires knowing where a person's data lives across your systems.
- **Right to erasure ("right to be forgotten")** — a person can request deletion of their data. You must be able to *actually delete* it across all systems — including backups and derived data — subject to the legal-retention exceptions.
- **Right to rectification** — correct inaccurate data.
- **Right to data portability** — provide their data in a portable, machine-readable format so they can take it elsewhere.
- **Right to object / restrict** — object to certain processing.

The hard engineering truth: **you can only honor these rights if your data architecture supports them.** "Find all of a person's data" and "delete all of a person's data" are trivial to promise and hard to deliver if personal data is scattered, duplicated, denormalized, cached, and copied into logs, analytics, and backups with no unified way to locate it. This is why privacy by design matters so much: systems designed to *track where personal data lives* and to *delete it comprehensively* can honor these rights; systems that weren't cannot, no matter the policy. The right to erasure in particular is a strong forcing function — being able to genuinely delete a person everywhere is a serious architectural requirement.

## The retention tension, revisited

The conflict flagged in the audit-trails post is fundamentally a privacy issue, so it's worth resolving clearly here: **the right to erasure collides with compliance retention obligations.** A customer may demand deletion, while AML/KYC rules *require* you to retain their records for years. Both are law. The resolution:

- **Legal obligation is a recognized basis to retain.** Privacy laws generally exempt data you're *legally required* to keep from erasure — you don't delete what regulation compels you to retain. So a customer's KYC/AML records required by law are retained despite an erasure request.
- **But only what's required.** The exemption covers the data under the retention obligation, *not everything*. Data not subject to a retention requirement should still be deleted on request. So you must distinguish must-retain-for-compliance data from other personal data and handle each correctly.
- **This requires knowing your data.** You can only apply the exemption precisely if you know which data is under which obligation — again pointing to designed, well-mapped data handling.

The engineering lesson: privacy and compliance retention are *both* binding and *sometimes opposed*, and the resolution isn't to pick one but to *precisely separate* data by its legal treatment — retain what's compelled, delete what isn't, and know which is which. Treating "delete everything" or "keep everything" as blanket policies violates one law or the other.

## Building privacy in

Practical guidance for engineering privacy:

- **Minimize first.** Collect and retain the least personal data that meets your needs — the highest-leverage privacy decision, reducing risk and obligation at the source.
- **Map your personal data.** Know *where* personal data lives across systems (databases, logs, caches, analytics, backups) — you can't honor access or erasure rights without this map.
- **Design for deletion and export.** Build the ability to find, export, and comprehensively delete an individual's data (respecting retention exceptions) as a first-class capability, not an emergency scramble.
- **Track consent and purpose as data** — recorded, per-purpose, revocable.
- **Secure personal data** — encryption and access control, and don't leak it into logs (the logging post's rule) or other places it shouldn't be.
- **Separate compliance-retained data** from erasable data so the retention tension is handled precisely.

Data privacy governs the raw material — personal data — that every compliance control operates on, and honoring it is an architectural commitment, not a policy statement. With who-you-serve, what-they-do, screening, audit, and privacy covered, the final building-block post is telling regulators what they require: regulatory reporting.

## Key takeaways

- Privacy laws (GDPR and similar) grant individuals rights over personal data and impose obligations backed by real penalties — and those obligations require *systems* to behave specific ways, making privacy an engineering discipline (privacy by design) that must be built in, not retrofitted.
- Core principles map to design: lawful basis/consent (track consent as data), purpose limitation, data minimization (collect/keep the least — reduces risk at the source), storage limitation/retention, security, and accountability.
- You must be able to *execute* individual rights — access (find and produce all of a person's data), erasure (comprehensively delete it), rectification, portability, objection — which is only possible if your data architecture is designed to locate and delete personal data across all systems, backups, and derived copies.
- The right to erasure collides with compliance retention; resolve it by retaining only what law *requires* (a recognized exemption) while deleting the rest — which demands precisely distinguishing must-retain-for-compliance data from other personal data.
- Build privacy in: minimize data first, map where personal data lives, make find/export/delete first-class capabilities, track consent and purpose, secure data (and keep it out of logs), and separate compliance-retained from erasable data.

## Further reading

- [Audit trails and immutability (previous post)](/blog/posts/regtech-05-audit-trails-and-immutability.html)
- [GDPR — the official regulation text](https://gdpr-info.eu/)
- [On-Device AI: privacy and local-first design](/blog/posts/edgeai-07-privacy-and-local-first.html)
