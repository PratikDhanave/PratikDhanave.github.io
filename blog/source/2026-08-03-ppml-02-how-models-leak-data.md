# How Models Leak Data — The Attacks That Make Privacy Necessary

*A trained model feels like a safe abstraction — it's just numbers, a learned function, surely it reveals nothing about the specific data it saw. That intuition is wrong, and a family of attacks proves it: models memorize their training data and can be made to give it up. Understanding these attacks is what turns privacy from a vague worry into a concrete threat you can defend against — and it's why the formal techniques in the rest of the series exist.*

Post 1 claimed that securing the data isn't enough because the *model* leaks. This post makes that concrete by walking the actual attacks. You defend against threats you understand, so before the defenses (differential privacy, federated learning), it's worth seeing exactly how a model betrays its training data — and why "it's just an aggregate" is false.

## Memorization: the root of the problem

The foundation of every privacy attack is a single fact: **models memorize their training data.** A model with enough capacity doesn't just learn general patterns — it also memorizes specific examples, especially rare or unusual ones and especially when a datapoint is seen many times. This is related to overfitting (ML series, post 5), but it happens even in well-generalizing models: large models in particular have been shown to memorize and regurgitate verbatim training examples.

This is most vivid in **large language models**, which have been demonstrated to emit verbatim chunks of their training data — someone's leaked personal information, a copyrighted passage, a secret key committed to a public repo — when prompted the right way. The model didn't "understand" it was private; it statistically memorized it and reproduced it. Memorization is not a bug you can fully eliminate without cost; it's an inherent tendency of high-capacity models trained to fit data, and it's the vulnerability every privacy attack exploits. If models didn't memorize, privacy would be easy; because they do, it's a discipline.

## The attack family

Researchers have developed a progression of attacks, each extracting more from the model, and together they define the threat model that privacy-preserving ML defends against:

- **Membership inference** — the most fundamental privacy attack: given a data record and access to the model, determine *whether that record was in the training set.* This sounds mild until you consider the context — knowing someone was in a dataset of "patients with a specific disease" or "people who visited a clinic" is itself a serious privacy violation, regardless of what else leaks. Membership inference works because models behave subtly differently on data they trained on (more confident, lower loss) than on data they didn't, and that difference is detectable. It's the canary: if a model is vulnerable to membership inference, it's leaking.
- **Model inversion / attribute inference** — reconstruct features of the training data or infer sensitive attributes. In the classic demonstration, researchers reconstructed recognizable images of people's faces from a facial-recognition model given only their name and access to the model. The model's parameters encoded enough about the training faces to partially *regenerate* them.
- **Training-data extraction** — the strongest: pull actual training examples back out of the model. For LLMs, carefully crafted prompts extract verbatim memorized sequences — real emails, phone numbers, and secrets that were in the training corpus. The model becomes an unintended database of its training data, queryable by anyone with access.
- **Model stealing / extraction** — adjacent: reconstruct the model itself (its parameters or behavior) through query access, which is an IP and security concern and can enable the other attacks.

The crucial point is the **access model**: many of these attacks work with only *black-box* access — the ability to query the model and see outputs — not access to its internals. So deploying a model behind an API does *not* protect its training data; the API is exactly the attack surface. And the attacks get stronger with *white-box* access (the parameters), which is why sharing or open-sourcing a model trained on sensitive data is especially risky.

## Why this changes everything

These attacks demolish the comfortable intuitions from post 1 and reshape how you must think about models trained on sensitive data:

- **The model is sensitive data.** A model trained on private data *is itself* a carrier of that private data — it must be protected, access-controlled, and treated with the same care as the raw data, because it can leak the raw data. "We only shipped the model, not the data" is not a privacy defense.
- **Aggregation isn't anonymization.** The hope that a model over millions of people reveals nothing about one person is false — memorization and membership inference reach individuals through the aggregate. This directly refutes post 1's naive "trust the aggregate."
- **Generalization helps but doesn't solve it.** Reducing overfitting (regularization, more data) reduces memorization and makes attacks harder, which is good practice — but it doesn't *guarantee* privacy, and well-generalizing large models still memorize. You cannot defend by hoping; you need techniques with *guarantees*.

This last point is the motivation for the rest of the series. Because memorization is inherent and the attacks work through normal access, ad-hoc defenses aren't enough — you need **differential privacy** (posts 3–4), whose guarantee is precisely "the model is provably almost the same whether or not any individual was in the training data," which is exactly the property that defeats membership inference and extraction at its root. The attacks define the threat; differential privacy is the principled answer. Seeing the attacks first is what makes the formal machinery feel necessary rather than academic.

The throughline: models **memorize their training data** — especially rare examples and in high-capacity models (LLMs demonstrably emit verbatim training data) — and that memorization is the root vulnerability behind a family of attacks: **membership inference** (detect whether a record was in training — serious even alone, e.g. "was this person in the disease dataset?"), **model inversion** (reconstruct features/faces or infer attributes), **training-data extraction** (pull verbatim examples back out), and **model stealing**. Critically, many work with only **black-box query access**, so putting a model behind an API doesn't protect its training data — the API *is* the attack surface. This refutes post 1's naive intuitions: **the model is sensitive data**, **aggregation isn't anonymization**, and **generalization helps but doesn't guarantee** privacy — which is exactly why you need formal techniques like **differential privacy** (posts 3–4), whose guarantee defeats these attacks at the root.

## Key takeaways

- The root vulnerability is that **models memorize training data** — especially rare examples and in high-capacity models; LLMs have been shown to emit **verbatim** training data (personal info, secrets, copyrighted text) — an inherent tendency of fitting data, not a bug you can fully remove for free.
- **Membership inference** (determine whether a record was in the training set) is the fundamental attack — serious even alone (membership in a sensitive dataset is itself a violation) — and works because models behave subtly differently (more confident) on data they trained on.
- Stronger attacks escalate: **model inversion** (reconstruct features/faces, infer attributes — famously regenerating training faces from a face-recognition model), **training-data extraction** (pull verbatim examples out, e.g. via crafted LLM prompts), and **model stealing** (reconstruct the model via queries).
- Many attacks need only **black-box query access**, so deploying a model behind an **API does not protect its training data** — the API is the attack surface; white-box (parameter) access makes attacks worse, so open-sourcing a model trained on sensitive data is especially risky.
- Consequences: **the model *is* sensitive data** (protect it like the raw data), **aggregation isn't anonymization**, and **generalization helps but doesn't guarantee** privacy — motivating formal defenses like **differential privacy** (posts 3–4), whose guarantee ("the model is provably ~the same with or without any individual") defeats these attacks at the root.

## Further reading

- [Information privacy — the privacy at stake in these attacks](https://en.wikipedia.org/wiki/Information_privacy)
- [Differential privacy — the formal defense the attacks motivate](https://en.wikipedia.org/wiki/Differential_privacy)
