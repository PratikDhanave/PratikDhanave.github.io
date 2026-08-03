# Confirmation of Payee: Checking the Name Before the Money Leaves

*Name-match the beneficiary before a push payment to stop authorized-push-payment (APP) fraud.*

---

## The gap that a name check closes

Most fraud controls assume the attacker is impersonating the account holder. Authorized push payment fraud inverts that: the genuine account holder, correctly authenticated, willingly instructs a transfer to an account they believe belongs to their landlord, their builder, or the tax office. The instruction is real, the credentials are real, the device is trusted. Every control tuned to detect a compromised account waves it through.

The weak point is that a bank transfer is routed purely on the account number and sort code (or IBAN). The payee *name* the customer types is decorative — historically it was never checked against the account it was paired with. A fraudster who tricks someone into changing the destination account only has to supply a plausible name; the payer's bank never compares it to the real account holder.

Confirmation of Payee (CoP) closes that gap with one pre-flight question, asked before the payment is confirmed: *does the name the payer entered actually match the holder of the destination account?* It is a small, synchronous name-verification call layered on top of the existing routing rails, and it is worth understanding as its own service because its correctness, latency, and failure behavior all sit directly in the payment critical path.

## A synchronous pre-flight check on the payment path

CoP runs while the customer is still looking at the confirmation screen — after they have entered the beneficiary details, before they press send. The payer's bank asks a shared lookup service to route a name query to the payee's bank, which compares the supplied name against its own record for that account and returns a graded verdict.

```
 Payer          Payer Bank        CoP Service        Payee Bank
   |  enter name +   |                 |                 |
   |  account/sort   |                 |                 |
   |---------------->|                 |                 |
   |                 |-- name query -->|                 |
   |                 |                 |-- route by ---->|
   |                 |                 |   sort/IBAN     | look up
   |                 |                 |                 | account
   |                 |                 |<-- verdict -----|  holder
   |                 |<-- match /      |    + reason     |
   |                 |    close /      |                 |
   |                 |    no-match ----|                 |
   |  warn or        |                 |                 |
   |<-- proceed -----|                 |                 |
   |                 |                 |                 |
   |  [proceed] -> normal transfer executes on the rail  |
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-confirmation-of-payee.html)** — pan, zoom, and trace every step (light/dark, self-contained).

Two properties of this shape matter for engineering. First, CoP is *advisory*: it does not move money and it does not, by itself, block a payment. Its output is a signal the payer's bank turns into a warning, a friction step, or — rarely — a hard stop. Second, it is strictly ordered *before* the payment instruction. That ordering is the entire value; a name check that happened after settlement would be a reconciliation report, not a fraud control.

## The four verdicts and what each one means

A well-designed CoP response is not a boolean. Collapsing it to match/no-match throws away the information the payer needs to make a good decision. Four outcomes cover the real cases:

| Verdict | Meaning | Typical UI treatment |
|---|---|---|
| `match` | Supplied name matches the account holder | Proceed silently |
| `close_match` | Near miss (typo, missing middle name) | Show the actual name, ask to confirm |
| `no_match` | Name does not match the account | Strong warning, add friction |
| `unavailable` | Payee bank did not answer in time | Proceed with a caveat, log it |

The `close_match` case is where most of the design effort goes, because it is both the most common and the most dangerous to get wrong. Return it too eagerly and you leak the real account holder's name to anyone probing accounts. Return `no_match` for a harmless "Rob" versus "Robert" and you train users to click through every warning, destroying the control. The response should include a machine-readable reason code (`name_mismatch`, `account_not_found`, `account_type_mismatch`) so the payer's bank can tune messaging per case rather than showing one generic scare screen.

## Building the matcher without leaking or over-blocking

The comparison itself is a name-normalization plus fuzzy-match problem, run entirely inside the payee's bank so the raw account-holder name never crosses the wire. The pipeline is small but every step earns its place.

```python
def match_name(supplied: str, on_record: str, account_type: str,
               requested_type: str) -> tuple[str, str]:
    if account_type != requested_type:
        return "no_match", "account_type_mismatch"

    a, b = normalize(supplied), normalize(on_record)
    if a == b:
        return "match", "exact"

    score = token_similarity(a, b)          # e.g. Jaro-Winkler on tokens
    if score >= 0.90:
        return "close_match", "name_mismatch"   # reveal on-record name
    return "no_match", "name_mismatch"          # reveal nothing

def normalize(name: str) -> str:
    name = name.casefold().strip()
    name = strip_titles(name)               # mr, mrs, dr, ltd, plc
    name = strip_punct_and_accents(name)
    return " ".join(sorted(name.split()))   # order-independent tokens
```

The details that separate a usable matcher from a rejected one: normalize away honorifics and legal suffixes (`Ltd`, `plc`) before comparing, because customers rarely type them; treat token order as insignificant so "Jane Smith" matches "Smith Jane"; and account for business versus personal accounts, where the "name" is a registered entity, not a person. The similarity threshold is a policy dial, not a constant — it should be tuned against a labeled corpus of real confirmed-good and confirmed-fraud transfers, and it will differ for personal and business accounts.

Crucially, the payee's bank should only *reveal* the on-record name on a `close_match`, never on a `no_match`. That single rule is what stops CoP from becoming an account-name enumeration oracle: a probe with a wrong name learns nothing except "wrong," while a genuine near-miss gets the correction it needs.

## Latency, availability, and the fail-open question

CoP is a blocking call on a screen the customer is actively staring at, so it lives under a tight latency budget — a few seconds at most before the confirmation screen must render something. That forces two decisions.

The first is a hard timeout with a defined fallback. If the payee's bank does not answer, you return `unavailable` and let the payment proceed with a logged caveat. Failing *open* is the deliberate, standard choice here: CoP is a fraud *signal*, and refusing to let people pay bills because a downstream directory was slow causes more harm than the fraud it would prevent. Fail-closed belongs to money movement, not to an advisory name check.

The second is caching, done carefully. You can cache the routing and reachability of a payee institution freely, but you must not cache the *verdict* for a given name-plus-account pair long enough to become a lookup service — account holders change, and a stale `match` is a liability. Cache the infrastructure, not the answer.

Finally, instrument the outcomes as first-class metrics: the ratio of `no_match` warnings that customers override and pay anyway is your leading indicator of active APP fraud campaigns, and the `unavailable` rate tells you which counterparties are degrading. CoP's real payoff is not the individual warning — it is that this stream of verdicts turns a silent, authorized transfer into an observable event you can reason about before the money is gone.
