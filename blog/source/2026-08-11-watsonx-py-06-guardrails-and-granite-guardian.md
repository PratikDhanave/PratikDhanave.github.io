# Guardrails and Granite Guardian

*Adding safety to a watsonx app in Python with two complementary layers — the built-in HAP and PII moderations that watsonx.ai applies to generation, and IBM's dedicated Granite Guardian risk-detection models run as classifiers around your main model to catch harm, jailbreaks, and RAG hallucination before a response reaches a user.*

---

A model that answers well most of the time is not the same as a model you can safely put in front of users. Left alone, a generative model will happily repeat abuse it was baited into, echo personal data that leaked into a prompt, follow an instruction smuggled inside a retrieved document, or state a confident answer that the context never supported. Safety is not a single switch — it is a set of checks layered around the call, each catching a different failure the others miss.

watsonx gives you two complementary layers, and this post wires both into a Python app. The first is **built-in moderations** (also called guardrails): detection and filtering for hate/abuse/profanity and personal data that watsonx.ai can apply to what goes into and comes out of a generation. The second is **Granite Guardian**, IBM's family of open risk-detection models you run yourself as classifiers — screening the user's input, and crucially screening a RAG answer against its retrieved context for faithfulness. Together they form defense in depth on top of the input validation and least-privilege tools from earlier in this series.

---

## Layer 1: built-in moderations on the model call

watsonx.ai can screen generation for two categories of content without you deploying any extra model:

- **HAP** — hate, abuse, and profanity. A classifier scores text for toxic content.
- **PII** — personally identifiable information such as names, emails, phone numbers, and similar identifiers.

The important design point is *where* it runs: moderations apply to both the **input** you send and the **output** the model produces. That matters because the two catch different problems. Input screening stops a toxic or identity-laden prompt from ever reaching the model; output screening stops the model's own generation from returning something toxic, or from parroting PII that slipped through the prompt or the training data. You enable it by attaching a moderations configuration to the generation parameters, and the service applies it inline.

The exact parameter keys and threshold shapes live in the watsonx.ai documentation and shift between SDK versions, so treat the dictionary below as **illustrative structure, not a copy-paste contract** — confirm the current key names against the guardrails docs linked at the end before you ship it.

```python
# ILLUSTRATIVE ONLY — confirm exact keys/shape against the watsonx.ai guardrails docs.
# The real names may differ by SDK version; this shows the *shape* of the idea:
# an HAP block and a PII block, each with a detection threshold and an action.
moderations = {
    "hap": {
        "input":  {"enabled": True, "threshold": 0.5},   # screen what goes in
        "output": {"enabled": True, "threshold": 0.5},   # screen what comes out
    },
    "pii": {
        "input":  {"enabled": True},
        "output": {"enabled": True, "mask": True},        # mask detected PII in the reply
    },
}
```

You pass this alongside your usual generation parameters. Conceptually the call looks like the `ModelInference` usage from earlier posts, with a `moderations` (guardrails) configuration added:

```python
from ibm_watsonx_ai.foundation_models import ModelInference

model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",   # verify current id in the catalog
    credentials=credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)

# `guardrails`/`moderations` support is exposed on the generation call — check the
# SDK reference for the precise argument name and value shape in your version.
response = model.generate(
    prompt="Summarise this support ticket for the on-call engineer.",
    params={"max_new_tokens": 300},
    # guardrails=True or a moderations config dict — see the docs for the exact API.
)
```

### What a flagged response actually looks like

Here is the part teams get wrong. When moderations trip, **the response is not a normal completion** — it is a signal that content was blocked, filtered, or masked. If your code reads the generated text field blindly and hands it to the user, a masked or empty result flows through as if it were a real answer. The moderations output rides *alongside* the generated text: the response payload carries structured detail about what was detected, in which position, with what score, and whether it was masked or the generation was stopped.

So your reader has to branch on it:

```python
def extract_answer(response: dict) -> tuple[str, bool]:
    """Return (text, was_moderated). Inspect the moderation detail before trusting text."""
    result = response["results"][0]
    text = result.get("generated_text", "")

    # The moderation detail is attached to the result; the exact field name/shape
    # is documented with the guardrails API — verify it. The point is: check it.
    moderation = result.get("moderations") or result.get("moderation")
    was_moderated = bool(moderation)

    return text, was_moderated
```

**The gotcha:** a moderation-flagged response is not an error and not a normal answer — it is a third state your code must handle explicitly. PII masking rewrites the text in place (a name becomes a placeholder), and HAP filtering can truncate or withhold the generation. If you branch only on "did the call succeed," a masked or withheld reply sails straight through to the user. Read the moderation detail on every response and decide deliberately: return the masked text, return a safe refusal, or log and retry.

---

## Layer 2: Granite Guardian as a classifier

Built-in moderations are broad and cheap, but they cover a narrow slice of risk: toxicity and personal data. They do not tell you whether a prompt is a jailbreak attempt, whether an answer is grounded in its sources, or whether a tool call the model wants to make is safe. For that, IBM ships **Granite Guardian** — a family of open safety models (available on Hugging Face and in the watsonx catalog) trained specifically to *detect risk* rather than to chat.

A Granite Guardian model is a classifier you run like any other model, via `ModelInference`. You give it the content plus a **risk definition**, and it returns a short verdict — a `Yes`/`No`-style judgment that the content exhibits that risk. The risks it can assess span several families:

| Risk family | What it flags |
|---|---|
| General harm | Content that is harmful, dangerous, or unsafe overall |
| Social bias | Prejudice or unfair generalisation about people |
| Profanity / harmful language | Abusive or offensive language |
| Jailbreak / prompt injection | Attempts to subvert instructions or safety |
| Groundedness (RAG) | Whether an answer is supported by the provided context |
| Answer relevance (RAG) | Whether the answer actually addresses the question |
| Function-call safety | Whether a proposed tool call is safe/appropriate |

The exact set of supported risks and the recommended prompt format are documented on the model card — the values you pass for the "risk name" must match what the model was trained to recognise, so read the card rather than inventing risk labels.

### Screening the input

The first place to use it is on the user's input, before your main model ever sees the prompt. You ask Guardian a single question: *does this text exhibit the jailbreak risk?*

```python
guardian = ModelInference(
    model_id="ibm/granite-guardian-3-8b",   # confirm the current Guardian id in the catalog
    credentials=credentials,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)

def guardian_flags(text: str, risk: str, context: str | None = None) -> bool:
    """Ask Granite Guardian whether `text` exhibits `risk`. Returns True if flagged.

    The prompt/chat format and the accepted `risk` names come from the model card —
    the structure below is faithful to how Guardian is used (content + risk -> verdict),
    but confirm the exact template for your version.
    """
    user_content = text if context is None else f"Context:\n{context}\n\nResponse:\n{text}"
    messages = [
        {"role": "system", "content": risk},      # the risk definition/name Guardian checks
        {"role": "user", "content": user_content},
    ]
    result = guardian.chat(messages=messages)
    verdict = result["choices"][0]["message"]["content"].strip().lower()
    return verdict.startswith("yes")
```

Guardian answers with a label (a `Yes`/`No` verdict, and depending on the version a confidence or probability alongside it). Parse it defensively — normalise case and whitespace, and decide how you treat an unexpected answer. A safe default is fail-closed on the checks that matter: if you cannot parse a clear "no," treat it as flagged.

**The gotcha:** Granite Guardian is a **separate model call** — real latency and real cost on every check. Wrapping a single user turn with an input check, an output check, and a groundedness check triples your inference calls. Budget for that and choose which checks each route actually needs. A public-facing chatbot probably wants jailbreak screening on input; an internal summariser over trusted documents may not. Do not reflexively run every risk on every request.

### Screening the output for groundedness

The second, and for RAG the most valuable, use is checking the *answer* — specifically whether it is **grounded** in the retrieved context. This ties directly to the retrieval pipeline from the embeddings and RAG posts: you retrieved passages, you stuffed them into the prompt, the model answered. Groundedness checking asks whether that answer is actually supported by those passages or whether the model wandered off into a confident hallucination.

The critical detail: **groundedness is not free-floating hallucination detection.** Guardian cannot tell whether a claim is true in the abstract — it checks the answer *against the context you pass in*. So you must hand it both the retrieved context and the generated answer. No context, no groundedness verdict.

```python
def is_grounded(answer: str, retrieved_context: str) -> bool:
    """True if the answer is supported by the retrieved context (per Guardian)."""
    # `guardian_flags` returns True when the *risk* fires; groundedness risk fires
    # when the answer is NOT grounded, so a True verdict means "hallucinated".
    hallucinated = guardian_flags(answer, risk="groundedness", context=retrieved_context)
    return not hallucinated
```

**The gotcha:** groundedness checking needs the retrieved context passed in — it is comparing the answer to a source, not consulting world knowledge. If you forget to pass the context, or you pass the wrong chunks, the verdict is meaningless. And read the polarity carefully: the groundedness *risk* firing means the answer is **un**grounded, so invert it when you decide whether to return the answer.

---

## Putting it together: a guarded generate wrapper

Now compose the layers into a single function. The shape is: screen the input with Guardian, call the main model (with built-in moderations on), then screen the output — for RAG, screen it for groundedness against the very context you retrieved — and only then return. Any failed gate short-circuits into a refusal instead of leaking an unsafe or unfounded answer.

```python
def guarded_generate(user_prompt: str, retrieved_context: str) -> str:
    # 1. Input gate: refuse obvious jailbreak / injection attempts up front.
    if guardian_flags(user_prompt, risk="jailbreak"):
        return "I can't help with that request."

    # 2. Main generation, with built-in HAP/PII moderations enabled on the call.
    prompt = (
        f"Answer the question using ONLY the context.\n\n"
        f"Context:\n{retrieved_context}\n\nQuestion: {user_prompt}"
    )
    response = model.generate(prompt=prompt, params={"max_new_tokens": 400})
    answer, was_moderated = extract_answer(response)

    # 3. Output gate: honour the built-in moderation signal...
    if was_moderated:
        return "I wasn't able to produce a safe response to that."

    # 4. ...and check the answer is grounded in the retrieved context (RAG hallucination).
    if not is_grounded(answer, retrieved_context):
        return "I don't have enough grounded information to answer that reliably."

    return answer
```

Notice how the two layers cover different gaps. The built-in moderations catch toxicity and PII in the generation cheaply and inline. Guardian catches the things moderations do not: an injection buried in the prompt, and an answer that reads fluently but is not supported by the sources. Neither alone is sufficient; together they close most of the practical gaps.

### Where this fits in defense in depth

These safety models complement — they do not replace — the controls from earlier posts. Your own input validation still matters: length caps, allow-listed routes, schema checks on structured input. Least-privilege tool design still matters: a Guardian function-call-safety check is a backstop, not a substitute for only exposing tools the agent is actually allowed to use. And remember from the RAG post that **retrieval content is untrusted** — a document in your corpus can carry an injected instruction, which is exactly why screening the assembled prompt (and the answer) matters even when the *user's* words looked innocent.

**The gotcha:** guardrails complement, never replace, your own validation. A model-based safety check is probabilistic — it will miss things and it will false-positive. Treat it as one layer in a stack that also includes deterministic input validation, least-privilege tools, output encoding, and human review for the highest-stakes actions. If your only defense is "we turned guardrails on," you have one probabilistic layer standing between users and every failure mode above.

---

## Key takeaways

- **Two layers, two jobs.** Built-in moderations screen HAP and PII inline on the watsonx.ai call, on both input and output; Granite Guardian is a separate classifier you run for the risks moderations do not cover — jailbreaks, groundedness, function-call safety.
- **A moderated response is a third state.** Not an error, not a normal answer. Read the moderation detail on every response and branch on it, or masked and withheld replies leak through.
- **Guardian is a real model call.** Latency and cost per check. Budget for it and pick which checks each route needs rather than running every risk on every request.
- **Groundedness needs the context.** It compares the answer to the passages you retrieved — pass them in, and mind the polarity (the risk firing means *ungrounded*). It is not magic, source-free hallucination detection.
- **Defense in depth.** Guardrails sit on top of your own input validation and least-privilege tools, and retrieved content stays untrusted. No single probabilistic layer is enough.

---

## Further reading

- [Removing harmful content with watsonx.ai guardrails (HAP & PII)](https://www.ibm.com/docs/en/watsonx/saas?topic=lab-avoiding-harmful-language) — how the built-in moderations detect and filter hate/abuse/profanity and personal data on input and output.
- [IBM Granite Guardian documentation](https://www.ibm.com/granite/docs/models/guardian/) — the risk families Guardian classifies and how to prompt it as a detector.
- [`ibm-granite/granite-guardian-3.2-5b` model card (Hugging Face)](https://huggingface.co/ibm-granite/granite-guardian-3.2-5b) — the exact prompt format, supported risk names, and verdict shape; confirm details here before wiring it in.
- [`ibm-watsonx-ai` Python SDK reference](https://ibm.github.io/watsonx-ai-python-sdk/) — `ModelInference`, the generation/chat parameters, and the guardrails/moderations arguments in your installed version.
- [IBM Granite Guardian on GitHub](https://github.com/ibm-granite/granite-guardian) — recipes and usage examples, including RAG groundedness and function-call checks.
