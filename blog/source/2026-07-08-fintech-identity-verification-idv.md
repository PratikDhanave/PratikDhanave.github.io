# Designing an Identity Verification Pipeline

*A document and liveness pipeline that emits a graded pass, refer, or fail instead of a coin-flip yes/no.*

---

Identity verification (IDV) is the gate every regulated fintech puts in front of onboarding: prove a person is who they claim before you open an account, issue a card, or let money move. It is tempting to treat it as one vendor call that returns a boolean. In practice it is a short pipeline of independent checks, each producing a signal, and the interesting engineering is in how those signals combine into a decision you can defend to a regulator and to the customer sitting on the other side of a spinner.

This post walks the data path from a photographed document to a graded outcome, and calls out the failure modes that only show up once real users hit it.

## The pipeline at a glance

The flow is linear on the happy path and fans out only at the end, where a score maps to one of three outcomes.

```
 capture        extract          verify              decide
┌────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌──────────┐
│document│──▶│ OCR/MRZ  │──▶│authenticity│──▶│ liveness │──▶│  risk    │
│ + selfie│  │ extract  │   │  checks   │   │ + match  │   │  score   │
└────────┘   └──────────┘   └───────────┘   └──────────┘   └────┬─────┘
                                                                │
                                          ┌─────────┬───────────┼───────────┐
                                          ▼         ▼           ▼
                                       [ pass ]  [ refer ]   [ fail ]
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-identity-verification-idv.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The important property is that every stage is *fail-cheap and independent*. If OCR confidence is too low, you do not spend money calling the biometric vendor; you route the user back to re-capture. Ordering the stages from cheapest to most expensive is a cost decision as much as a correctness one.

## Capture and extraction

The first stage is the one you control least. A user is holding a phone in poor light, and the single most common cause of a failed verification is not fraud but glare, blur, or a thumb over the document number. Guiding capture on the client — edge detection, a brightness check, a hold-steady prompt — removes more downstream failures than any server-side model.

Once you have a clean image, extraction pulls the structured fields. For passports and most national IDs this means the Machine Readable Zone (MRZ): those two or three fixed-width lines at the bottom encoded to a strict standard. The MRZ is a gift to engineers because it carries its own check digits.

```python
def mrz_check_digit(field: str) -> int:
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(field):
        if ch.isdigit():
            v = int(ch)
        elif ch.isalpha():
            v = ord(ch.upper()) - 55   # A=10 ... Z=35
        else:
            v = 0                       # filler '<'
        total += v * weights[i % 3]
    return total % 10
```

Validating the document number, birth date, and expiry against their embedded check digits catches most OCR misreads before they poison the rest of the pipeline. Treat the MRZ as authoritative and the visually printed fields as a cross-check: when they disagree, that disagreement is itself a signal.

## Authenticity checks

Extraction tells you *what* the document says. Authenticity checks ask *whether the document is real*. This is a bundle of independent tests, and none of them is decisive alone:

- **Structural**: does the layout, font, and field placement match a known template for that issuing country and document version? Template libraries are the unglamorous core of every serious IDV product.
- **Security features**: holograms, optically variable ink, and microprint that behave in predictable ways across the capture frames.
- **Tamper detection**: has the photo been swapped, or a field digitally edited? Compression artifacts and edge inconsistencies betray copy-paste jobs.
- **Cross-field consistency**: the MRZ-versus-printed comparison above, plus sanity on the dates — an expiry before the issue date is not a subtle forgery.

Each test emits a confidence, not a verdict. The mistake is to short-circuit on the first weak signal. A slightly soft hologram reading on an otherwise pristine document is noise; the same reading alongside a mismatched MRZ is a pattern.

## Liveness and selfie match

Now you know the document is probably genuine. The remaining question is whether the person presenting it is its owner and is physically present. This is two checks that people conflate:

- **Liveness** defends against a photo of a photo, a screen replay, or a mask. Passive liveness analyzes a single frame for the artifacts of re-capture; active liveness asks the user to turn or blink. Passive is lower friction, active is harder to spoof, and mature systems run passive by default and escalate to active only when the passive score is marginal.
- **Face match** compares the live selfie against the photo extracted from the document, returning a similarity score. This is the step that actually binds the human to the identity.

Both return continuous scores. Liveness is a spoof-versus-genuine probability; match is a similarity distance you threshold. Neither should be flattened to a boolean before the final stage — you want the raw numbers so the scoring layer can reason about a strong match with weak liveness differently from the reverse.

## Scoring and the graded decision

Here is where the design pays off. Instead of ANDing a pile of booleans, you feed every signal — extraction confidence, each authenticity score, liveness, face-match distance — into a scoring layer that produces one calibrated risk score, then map that score to three bands:

```
score    outcome    action
─────    ───────    ──────────────────────────────
high     pass       auto-approve, open the account
mid      refer      queue for human review
low      fail       decline, offer a re-attempt path
```

The middle band is the whole point. A two-outcome system forces a threshold where every borderline case is either a rejected good customer or an admitted fraudster. The `refer` band routes ambiguity to a human analyst who sees the same signals and makes a judgment. Tune the two thresholds to trade auto-approval rate against manual-review cost and fraud loss — three levers instead of one.

A few engineering rules keep this honest:

- **Persist every signal, not just the outcome.** When a regulator or a chargeback asks why an account was opened, "the vendor said yes" is not an answer. Store the scores, the model versions, and the images with a retention policy.
- **Make the decision reproducible.** Pin the thresholds and model versions per decision so you can replay why a given user passed six months ago.
- **Design the re-attempt loop deliberately.** A `fail` on a blurry photo and a `fail` on a detected mask are the same outcome but call for opposite treatment — one invites a retry, the other should not.

## What actually breaks in production

The models are rarely the problem. What breaks is the plumbing around them: retries that double-charge a per-check vendor bill, timeouts that leave a user stranded mid-capture, and thresholds calibrated on one country's documents then applied globally. Instrument the funnel stage by stage — capture, extract, authenticity, biometric, decision — and watch the *drop-off* at each, not just the final pass rate. A sudden spike in extraction failures usually means a client update broke the capture UI, not that fraud went up.

Treat IDV as a pipeline of cheap-to-expensive, independently scored stages feeding a graded decision, and it stays observable, tunable, and defensible. Treat it as a black-box boolean, and every hard question a regulator asks becomes a research project.
