# Building a Dunning and Retry Engine for Failed Payments

*How decline-code classification, backoff scheduling, retry budgets, and network-token refresh recover subscription revenue without hammering the rails.*

For any business that bills on a recurring schedule, a meaningful slice of charges fail on the first attempt. Cards expire, balances dip below the amount for a day, issuers throttle a merchant they have not seen in a month. Most of that revenue is recoverable, but only if you retry intelligently. Retry blindly and you burn processing fees, trip issuer velocity limits, and train the network to treat you as suspicious. A dunning and retry engine is the component that decides *whether*, *when*, and *how many times* to try again, and what to tell the customer while it does.

The whole system turns on one early decision: is this decline permanent or transient? Everything downstream branches off that classification.

```
 charge attempt
      |
   declined ----> classify decline code
                        |
          +-------------+--------------+
          |                            |
      hard decline                 soft decline
          |                            |
   dunning + cancel            schedule retry (backoff)
                                       |
                                  retry attempt
                                  /          \
                             recovered     exhausted
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-dunning-retry-engine.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Not all declines are equal

Processors return a decline reason with every failed authorization, and the single most important thing your engine does is map that reason into a policy class. A **hard decline** means the instrument is fundamentally unusable: `pickup_card`, `stolen_card`, `revoked_authorization`, `invalid_account`. Retrying a hard decline is not just useless, it is counterproductive — some of these codes signal fraud or a closed account, and repeated attempts can flag the merchant. A **soft decline** is transient: `insufficient_funds`, `issuer_unavailable`, `try_again_later`, `do_not_honor` (the ambiguous catch-all that is usually worth one or two retries).

Do not hard-code raw processor strings across your codebase. Build a classification table that normalizes each processor's dialect into your own internal taxonomy, and give every entry a policy:

```python
# decline classification -> retry policy
DECLINE_POLICY = {
    "insufficient_funds": Policy(kind="soft", max_retries=4, strategy="funds_aware"),
    "issuer_unavailable":  Policy(kind="soft", max_retries=3, strategy="short_backoff"),
    "do_not_honor":        Policy(kind="soft", max_retries=2, strategy="standard"),
    "expired_card":        Policy(kind="soft", max_retries=1, strategy="require_updater"),
    "stolen_card":         Policy(kind="hard", max_retries=0, strategy="cancel"),
    "invalid_account":     Policy(kind="hard", max_retries=0, strategy="cancel"),
}

def classify(raw_code: str) -> Policy:
    normalized = NORMALIZE.get(raw_code, "unknown")
    # unknown codes get a conservative single retry, never a hard cancel
    return DECLINE_POLICY.get(normalized, Policy("soft", 1, "standard"))
```

The `unknown` fallback matters. Processors add codes, and treating an unrecognized decline as a permanent failure silently cancels paying customers. Default to a single cautious retry and alert so the mapping can be extended.

## Scheduling retries without hammering the rail

Once a decline is classed as soft, the engine schedules the next attempt rather than looping immediately. The scheduling policy has three levers.

**Backoff spacing.** Retrying an `insufficient_funds` decline sixty seconds later is pointless — the balance has not changed. Effective spacing follows the *reason for the decline*, not a generic exponential curve. Funds-related declines want retries aligned to likely deposit events: a few days out, ideally near a common payday cadence. Issuer-availability declines want short backoff, because the issuer may recover in minutes.

**Retry windows.** Attempts should land when authorizations are most likely to succeed — typically business hours in the cardholder's timezone, avoiding weekends and month boundaries where balances run thin. The scheduler snaps each computed retry time into the nearest allowed window.

**Retry budget.** Every instrument gets a hard ceiling on attempts, and often a *global* budget across a billing period so a single dunning cycle cannot fire ten authorizations. When the budget is exhausted, the branch flips to hard-fail: notify, then cancel or suspend.

```python
def next_retry_at(policy, attempt, now):
    if attempt >= policy.max_retries:
        return None                      # exhausted -> hard-fail branch
    base = {
        "funds_aware":   [3, 5, 7, 7],   # days, aligned to deposit cadence
        "short_backoff": [0.02, 0.5, 2], # ~30 min, 12 h, 2 days
        "standard":      [1, 3, 5],
    }[policy.strategy]
    delay_days = base[min(attempt, len(base) - 1)]
    return snap_to_window(now + timedelta(days=delay_days))
```

## Refreshing the instrument, not just the timing

The highest-leverage recovery move is not a better backoff curve — it is fixing the credential itself. A large fraction of recurring failures are expired or reissued cards. Two mechanisms close that gap.

**Account Updater** services from the networks let you submit stored card references and receive updated expiry dates or replacement numbers when the issuer has reissued the card. Running a scheduled updater sweep before a dunning retry converts many guaranteed declines into first-try successes.

**Network tokens** raise the ceiling further. When a payment credential is stored as a network token rather than a raw PAN, the token's lifecycle is managed by the scheme: expiry and reissuance are handled behind the token, so the underlying card can change without the merchant ever seeing a new number. A retry engine that refreshes the token cryptogram before re-authorizing recovers charges that a PAN-based flow would simply lose. In practice, `expired_card` should route to an updater/token-refresh step *before* consuming a retry attempt.

## Making retries safe to replay

A dunning engine is, by nature, a system that issues the same charge more than once. Without discipline it will double-bill. Three invariants keep it correct.

**Idempotency per attempt.** Each scheduled retry carries a stable idempotency key derived from the invoice and attempt number, so a worker that crashes mid-authorization and re-runs does not create a second charge. The processor deduplicates on that key.

**Single owner of state.** The dunning state machine — `scheduled → attempting → recovered | retrying | exhausted` — must have exactly one writer per instrument. Use a row lock or a per-instrument queue partition so two workers never advance the same dunning cycle concurrently. A recovered payment must immediately cancel any still-scheduled retries.

**Ledger reconciliation.** A recovered charge posts to the ledger exactly once; an exhausted cycle transitions the subscription to a delinquent or canceled state with a corresponding entry. Every terminal transition should be reconcilable against the processor's own record, because a retry that succeeded at the network but timed out on your side is the classic source of a phantom double-charge.

## Operating the engine

Instrument the funnel, not just the endpoints. The metric that matters is *recovery rate by decline class and attempt number* — it tells you where retries are wasted and where an extra attempt would pay for itself. Watch attempt-1 recovery separately from attempt-4: if late attempts almost never succeed, tighten the budget and save the fees. Track updater/token-refresh hit rate as its own line, since it is usually the cheapest recovery lever you have.

A dunning engine is deceptively simple to sketch and easy to get wrong in ways that quietly lose money or annoy customers. The discipline is in the classification table, the reason-aware scheduling, and the replay safety — get those three right and the rest is tuning.

## Key takeaways

- The whole system turns on one early decision: is the decline hard (instrument fundamentally unusable — stop and dunning-cancel) or soft (transient — schedule a retry)? Never hard-code raw processor strings; normalize them into your own taxonomy with a per-entry policy, and give unknown codes a cautious single retry, never a hard cancel.
- Backoff spacing follows the *reason* for the decline, not a generic exponential curve — retry `insufficient_funds` near payday cadence, `issuer_unavailable` on short backoff — and snap each attempt into an allowed business-hours window.
- Enforce a per-instrument retry budget (often a global per-billing-period cap too) so one dunning cycle can't fire ten authorizations.
- The highest-leverage recovery move is fixing the credential, not the timing: run Account Updater and network-token refresh *before* consuming a retry attempt on `expired_card`.
- Replay safety rests on three invariants — idempotency per attempt, a single writer of dunning state, and ledger reconciliation — so a retry that succeeded at the network but timed out on your side can't become a phantom double-charge.

## Further reading

- [Account Updater and the Card-on-File Lifecycle](/blog/posts/fintech-account-updater-cof.html)
- [Network Tokenization and PCI Scope](/blog/posts/fintech-network-tokenization-pci-scope.html)
- [VRP and Subscription Billing](/blog/posts/fintech-vrp-subscription-billing.html)
- [Card Authorization, Capture, and Clearing](/blog/posts/fintech-card-auth-capture-clearing.html)
