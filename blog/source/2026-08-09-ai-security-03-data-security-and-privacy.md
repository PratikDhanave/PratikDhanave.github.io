# Data Security and Privacy

*Part three of the AI Security Engineering series: protecting the data that flows through an LLM system — how sensitive information leaks out of prompts, logs, and retrieval, and the engineering controls (redaction, data minimization, per-user retrieval authz, residency choices) that actually stop it.*

---

Most of the damage in an LLM system is not the model saying something rude. It is *data going where it should not* — a support agent surfacing another customer's phone number, an API key that ends up in a trace, a RAG pipeline that hands one tenant a document belonging to another. OWASP tracks this as **LLM02: Sensitive Information Disclosure**, and it is consistently one of the most common and most expensive failure modes in production.

The uncomfortable truth is that the model is rarely the root cause. The pipeline around it is: what you put *into* the context, what you *log* along the way, and what you *retrieve* on the user's behalf. This post is about defending those three surfaces. Everything below is provider-agnostic — the controls hold whether you call a hosted API or run a model yourself.

---

## Where sensitive data actually leaks

A model can reveal data from three places, and it helps to name them precisely because each has a different fix:

1. **The context you gave it.** Anything in the system prompt, the user turn, tool outputs, or retrieved documents is fair game for the model to repeat. If you paste a secret into the prompt, assume it can come out.
2. **Its training data.** Foundation models memorize fragments of what they were trained on. With the right prompt they can regurgitate snippets — sometimes PII, sometimes copyrighted text. You don't control this directly; you control it by *choosing* and *evaluating* the model.
3. **Other users' data — through your plumbing.** This is the one teams cause themselves: shared caches, shared vector stores, logs that mingle tenants, or a fine-tuning set built from real user conversations.

**The gotcha:** "the model won't repeat secrets" is false. There is no privileged region of the context the model treats as confidential — the system prompt is not a vault. Anything you place in the context window can surface in an output, whether coaxed by a crafted prompt or spilled by accident. The engineering rule follows directly: *don't put a secret in the prompt if you'd be harmed by it appearing in the reply.* Give the model a reference or a scoped tool, not the raw credential.

---

## PII in prompts, logs, and traces

Here is the mistake almost everyone makes at least once. You add observability — you log every request and response, you wire up tracing so you can debug agent runs, you sample conversations into a dataset for evals. All good practice. And every one of those systems just became a copy of your users' personal data, sitting in a place with weaker access controls than your primary database.

**The gotcha:** your logs and traces are the sneakiest leak of all. The model output might be fine, but the raw prompt — full name, email, the paragraph the user pasted from a medical report — is now in your log aggregator, your tracing backend, and three months of retained snapshots, readable by anyone with a debugging login. Redact *before* the data is written, not after. "We'll scrub the logs later" is not a control; the data was exposed the moment it was written unredacted.

So the redaction step has to sit on the path *into* the model and *into* the logs, before either sees raw text.

---

## Redaction and anonymization

Detecting and masking PII is its own small discipline. You can build a regex baseline for well-structured identifiers (emails, credit-card-shaped numbers, national IDs with checksums), but names, addresses, and free-form context need a proper recognizer. A widely used open-source option is **Microsoft Presidio**, which combines named-entity recognition with pattern recognizers and configurable anonymization operators. Presidio splits the job into two libraries — `presidio-analyzer` finds entities, `presidio-anonymizer` transforms them — and its exact API surface evolves, so treat the sketch below as the shape and confirm signatures against the current Presidio docs before you ship.

Start with a regex baseline so the concept is unambiguous and dependency-free:

```python
import re

# Deliberately conservative patterns — a baseline, not a complete PII catalogue.
_PATTERNS = {
    "EMAIL": re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    "PHONE": re.compile(r"\b(?:\+?\d[\d ().-]{7,}\d)\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}

def redact_baseline(text: str) -> str:
    """Mask obvious structured PII. First line of defence, not the last."""
    for label, pattern in _PATTERNS.items():
        text = pattern.sub(f"[{label}]", text)
    return text
```

For anything beyond structured identifiers, hand the text to a recognizer. The Presidio-style flow looks like this:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def redact(text: str, language: str = "en") -> str:
    """Detect PII entities, then replace each with a typed placeholder."""
    findings = analyzer.analyze(text=text, language=language)
    result = anonymizer.anonymize(
        text=text,
        analyzer_results=findings,
        # Replace with a label per entity type; 'replace' is one of several
        # operators (others include hash, mask, encrypt) — check the docs.
        operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})},
    )
    return result.text
```

Now put redaction on *both* edges — the request path and the logging path — so raw PII never reaches the model or the log store:

```python
import logging

logger = logging.getLogger("llm.audit")

def handle_request(user_text: str, call_model) -> str:
    # 1. Minimise + redact BEFORE the model sees the input.
    safe_input = redact(user_text)

    # 2. Log the redacted form only. The raw text is never written.
    logger.info("llm_request", extra={"prompt": safe_input})

    raw_output = call_model(safe_input)

    # 3. Redact the OUTPUT too — the model can emit PII it inferred,
    #    retrieved, or hallucinated. Log the safe version.
    safe_output = redact(raw_output)
    logger.info("llm_response", extra={"completion": safe_output})

    return safe_output
```

Two subtleties worth internalizing. First, redact the *output* as well as the input — a model can emit PII that came from a retrieved document or was inferred from context, so the response path is a leak surface too. Second, decide deliberately whether the *user* sees the redacted text or the original; often you redact only what goes to the model and the logs, and return the model's answer to the user unmodified. That is a design choice, not an accident — make it on purpose.

**The gotcha:** anonymization is lossy and, done naively, reversible. Masking the name and email is not enough when the remaining *quasi-identifiers* — ZIP code, birth date, gender, a rare job title — combine to re-identify a person. This is the well-documented re-identification problem behind k-anonymity and its successors. Detection recall is never 100% either: a recognizer will miss an unusual name or a novel ID format. Treat redaction as risk reduction, not a guarantee, and pair it with the access and retention controls below rather than leaning on it alone.

---

## Data minimization

The cheapest data to protect is the data you never sent. **Data minimization** — a core principle in GDPR (Article 5's "adequate, relevant and limited to what is necessary") and echoed in most modern privacy regimes — maps almost directly onto good LLM engineering: send the model only the fields the task actually needs.

If the task is "classify this support ticket's urgency," the model does not need the customer's account number, their full address, or the last four transactions. Build the prompt from a *projection* of the record, not the whole row:

```python
def ticket_features(ticket: dict) -> dict:
    """Project only what the urgency classifier needs. Everything else stays home."""
    return {
        "subject": ticket["subject"],
        "body": redact(ticket["body"]),          # free text, so still redact
        "product_area": ticket["product_area"],
        "account_age_days": ticket["account_age_days"],
        # deliberately omitted: name, email, account_number, billing_address, ...
    }
```

Minimization compounds with everything else: less data in the prompt means less to leak from the output, less to redact, less sitting in your traces, and a smaller blast radius if the provider's logs are ever exposed. When in doubt, leave the field out and add it back only when a real task needs it.

---

## Data residency, retention, and tenancy

Once data leaves your process for a model provider, two questions decide your compliance posture: *where is it processed* and *how long is it retained*.

- **Residency.** Regulated data (health records under HIPAA, EU personal data under GDPR) often must be processed in a specific region. Check whether your provider lets you pin the processing region, and whether that guarantee covers the model *and* any hosted tools (retrieval, code execution) you use alongside it.
- **Retention.** Many providers retain prompts for some window — for abuse monitoring, quality, or their own model improvement — unless you opt out. Several offer a **zero-retention** or no-training mode for eligible accounts, and enterprise agreements frequently exclude your data from training by default. Do not assume; read the data-processing terms and confirm what applies to *your* tier.
- **Tenancy.** In a multi-tenant product, the provider's data handling is one layer; the isolation *you* build is another. Shared prompt caches, a shared vector store, or a fine-tuning set drawn from all tenants' conversations can all leak data across tenant boundaries even if the provider behaves perfectly.

This is where the earlier posts in this series on **model providers and vendor selection** pay off. When residency or retention constraints are strict enough — regulated data, contractual data-locality requirements, an absolute no-third-party rule — the honest answer is often to **self-host an open-weights model** so the data never leaves your boundary at all. That trades operational burden for control. The right call depends on the sensitivity of the data, not on which option is fashionable.

**The gotcha:** "we turned off training on our data" and "our data never leaves the region" are *different* promises, and a vendor can honor one while breaking the other. Retention for abuse monitoring can still mean your prompts sit in the provider's storage for weeks; a hosted retrieval tool can process data in a different region than the base model. Verify each property independently, in writing, per feature you use.

---

## Retrieval data governance

RAG is where careful teams still leak data across users, because the vector store quietly bypasses your application's authorization.

Picture a company knowledge assistant. Your app enforces that a contractor can't open the executive-comp folder. But you embedded *every* document into one shared index, and at query time you retrieve the top-k most similar chunks for whatever the user asked. The retrieval layer has no idea who is asking — so a well-phrased question pulls the restricted chunk straight into the context, and the model helpfully summarizes it. The UI-level permission check never ran, because retrieval happened underneath it.

**The gotcha:** RAG bypasses application-layer authorization unless you filter retrieval by the caller's permissions. A shared vector store with no per-user filtering is a cross-tenant and cross-role leak waiting to happen — the model will surface any chunk that is semantically relevant, entitlement be damned. Authorization has to live *in the retrieval query*, not only in the UI or the API gateway.

The fix is to make the retrieval layer permission-aware. Tag every chunk with the access metadata that governs its source document, then constrain the similarity search to what the caller is allowed to see — enforced *before* results come back, not filtered in the application afterward (post-filtering can starve the result set and still pull restricted vectors into scoring):

```python
def retrieve(query: str, user, k: int = 5):
    """Filter by the caller's entitlements INSIDE the vector query, not after."""
    # Compute the caller's allowed audience from their identity — never trust
    # a value passed in from the client.
    allowed = user.group_ids | {"public"}

    query_vec = embed(query)

    # Metadata filter runs server-side in the vector store, so restricted
    # chunks are excluded from similarity scoring entirely.
    return vector_store.search(
        vector=query_vec,
        top_k=k,
        filter={"acl_group": {"$in": list(allowed)}},   # per-store syntax varies
    )

def index_document(doc):
    """At ingestion, carry the SOURCE document's ACL onto every chunk."""
    for chunk in split(doc.text):
        vector_store.upsert(
            id=chunk.id,
            vector=embed(chunk.text),
            metadata={
                "acl_group": doc.acl_group,     # inherited from the source
                "source_id": doc.id,
            },
        )
```

The exact filter syntax differs by vector database, and some deployments prefer physically separate indexes or namespaces per tenant over a shared store with metadata filters — a stronger boundary when tenants must never share infrastructure. Whichever you choose, the invariant is the same: *the set of chunks eligible for retrieval must be scoped to the caller before similarity scoring*, and the caller's entitlements must be derived from their authenticated identity, never from a parameter the client can set. And keep the chunk ACLs in sync with the source: when a document's permissions change or it is deleted, its vectors must be updated or purged, or you re-open the leak.

---

## Regulatory framing, at engineering altitude

You don't need to be a lawyer, but a few privacy-law concepts translate straight into system requirements:

- **Purpose limitation (GDPR Art. 5).** Data collected for one purpose shouldn't be silently repurposed. Reusing production conversations as a fine-tuning or eval dataset is a new purpose — it needs a lawful basis and usually explicit notice or consent. Don't quietly harvest user chats into training data.
- **Data-subject rights (GDPR / CCPA).** People can request access to, correction of, or **deletion** of their data. Engineer for this: if a user's data can land in prompts, logs, traces, *and* a vector store, a deletion request has to reach all of them. A shadow copy of personal data in an un-inventoried tracing backend is exactly what turns a routine deletion request into a compliance incident.
- **Data minimization and storage limitation.** Covered above — collect and retain the minimum, and set real retention limits (with automatic expiry) on logs, traces, and any conversation datasets.

The engineering takeaway: maintain a **data inventory** for your LLM system. Know every place personal data can come to rest — prompts, model-provider retention, logs, traces, caches, vector stores, eval sets — because that map is what makes redaction, deletion, and residency guarantees actually enforceable instead of aspirational.

---

## Redaction vs. access control vs. residency — what each one buys you

| Control | Stops | Doesn't stop | Where it lives |
|---|---|---|---|
| Redaction / anonymization | Raw PII reaching the model or logs | Re-identification via quasi-identifiers; recall gaps | Request + logging + output paths |
| Data minimization | Unnecessary fields ever being exposed | Leakage of the fields you *do* send | Prompt construction |
| Per-user retrieval authz | RAG surfacing chunks the caller can't see | Leaks from data you deliberately included | The vector query itself |
| Residency / zero-retention | Data being stored or processed in the wrong place | In-context leakage back to the same user | Provider config + contract |
| Self-hosting | Data leaving your boundary at all | Everything above still applies internally | Your infrastructure |

No single row is sufficient. Data security in LLM systems is the *composition* of these controls across the whole pipeline.

---

## Key takeaways

- **The model isn't the leak — the pipeline is.** Sensitive-information disclosure (OWASP LLM02) usually traces back to what you put in the context, what you log, or what you retrieve.
- **Anything in the context can come out.** There is no confidential region of the prompt; keep raw secrets out and pass scoped references or tools instead.
- **Redact before you log, not after.** Your traces and log stores are the sneakiest PII leak. Put redaction on the input, output, *and* logging paths, and treat it as risk reduction, not a guarantee — quasi-identifiers still re-identify.
- **Minimize what you send.** The safest data is the field you never included; project records down to what the task needs.
- **RAG needs its own authz.** Filter retrieval by the caller's entitlements inside the vector query, or a shared store leaks across roles and tenants.
- **Verify residency and retention independently, per feature** — and when constraints are strict enough, self-host so the data never leaves.
- **Engineer for data-subject rights.** Keep a data inventory so deletion, access, and residency promises can actually be honored.

---

## Further reading

- [OWASP Top 10 for LLM Applications — LLM02: Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/)
- [OWASP GenAI Security Project](https://genai.owasp.org/)
- [Microsoft Presidio — documentation](https://microsoft.github.io/presidio/)
- [Microsoft Presidio — GitHub repository](https://github.com/microsoft/presidio)
- [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework)
- [GDPR — Article 5: Principles relating to processing of personal data](https://gdpr-info.eu/art-5-gdpr/)
- [California Consumer Privacy Act (CCPA) — California Attorney General](https://oag.ca.gov/privacy/ccpa)
