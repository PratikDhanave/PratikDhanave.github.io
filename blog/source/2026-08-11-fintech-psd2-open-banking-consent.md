# Engineering the Open Banking Consent Layer: SCA, Scopes, and Token Lifecycles

*How to build PSD2-grade open-banking APIs — strong customer authentication and its exemptions, the consent grant and its revocation, and the hard boundary between account-information and payment-initiation scopes.*

When a bank opens its data and payment rails to third parties, the interesting engineering is not the account or payment endpoints. Those are ordinary REST. The hard part is the machinery that sits in front of them: a consent object with a lifecycle, an authentication step you cannot skip without a defensible reason, and a token whose authority is bounded by exactly what the account holder agreed to. Get that layer wrong and you either leak data you had no permission to share, or you challenge users so often they abandon the flow. This post is about building that layer as a system rather than bolting it onto an OAuth server.

## Consent is a first-class object, not a token scope

The instinct from generic OAuth is to treat "consent" as a checkbox on the authorization screen and then forget about it once a token is issued. In open banking, consent is a durable, addressable resource with its own identifier, its own state machine, and a lifetime that is independent of any access token. A token expires in minutes; a consent for account-information access can live for months and be reused across many token refreshes.

Model it explicitly. A consent record carries the account holder (PSU) it belongs to, the third-party provider (TPP) it was granted to, the scope of what was permitted, a status, timestamps for creation, authorisation, and expiry, and — for payment initiation — the exact payment it authorises. The TPP creates a consent in an `AwaitingAuthorisation` state, redirects the user to the bank to authenticate and approve, and only then does the consent flip to `Authorised`. Everything downstream keys off that consent id, so you can revoke, audit, and reason about access without hunting through token stores.

```
  TPP                    ASPSP (Bank)              PSU
   │                        │                       │
   │ 1. create consent ─────▶ (AwaitingAuth)        │
   │◀──── consentId ────────│                       │
   │                        │                       │
   │ 2. redirect PSU ──────────────────────────────▶│
   │                        │◀── 3. authenticate ───│
   │                        │──── 4. SCA challenge ─▶│
   │                        │◀── 5. approve scope ──│
   │                        │  (consent Authorised)  │
   │◀──── 6. auth code ─────│                       │
   │ 7. exchange for token ─▶                        │
   │◀── access + refresh ───│                       │
   │                        │                       │
   │ 8. GET /accounts ──────▶ (scope + consent check)│
   │◀──── account data ─────│                       │
   │                        │                       │
   │ 9. DELETE consent ─────▶ (Revoked)              │
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-psd2-open-banking-consent.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The bank plays the role of authorization server. The consent id is minted before authentication happens, which is what lets you show the user a precise, itemised approval screen ("Share balances and 90 days of transactions for accounts A and B") rather than a vague grant.

## Scopes: account information versus payment initiation

The two regulated service types are not variations of one scope; they are different trust models and deserve different code paths. Account information (AIS) is read-only access to balances and transactions. Payment initiation (PIS) instructs the bank to move money. Confusing them is how you end up letting a data-aggregation token trigger a transfer.

Bind scope to the consent, then enforce it at the edge. An AIS consent grants read access to a fixed set of accounts and data clusters; it should never satisfy a payment endpoint. A PIS consent is narrower still — it authorises **one** specific payment (creditor, amount, currency, reference), not "payments" as a category. Once that payment is initiated, the consent is spent. Encode this so the authorisation check is not "does the token have the payments scope" but "does this consent authorise *this* payment for *this* creditor and amount."

```python
def authorize(request, consent):
    if consent.status != "Authorised":
        raise Forbidden("consent not in authorised state")
    if consent.expires_at and now() > consent.expires_at:
        raise Forbidden("consent expired")
    if request.kind == "account_info":
        if consent.type != "AIS":
            raise Forbidden("wrong consent type")
        if request.account_id not in consent.permitted_accounts:
            raise Forbidden("account outside consent")
    elif request.kind == "payment":
        if consent.type != "PIS":
            raise Forbidden("wrong consent type")
        # PIS consent authorises exactly one payment
        if (request.creditor, request.amount) != (consent.creditor, consent.amount):
            raise Forbidden("payment does not match consent")
```

The check runs on every call, cheaply, against the consent record — not against a decoded token claim that a client could have been over-granted.

## Strong Customer Authentication and its exemptions

SCA is the requirement that the account holder prove identity with at least two independent factors drawn from knowledge, possession, and inherence. Engineering it well means treating authentication as a pluggable step in the consent flow, not a hard-coded redirect to one OTP screen. You will support app-based approval, biometrics, hardware tokens, and fallbacks, and you will need to add more over time.

The subtlety is exemptions. Regulation allows you to skip the challenge in defined cases — low-value transactions, trusted beneficiaries the user has whitelisted, recurring payments of a fixed amount, transaction-risk analysis below a fraud-rate threshold. Build an exemption engine that runs *before* you challenge, evaluates the applicable rules, and returns either "exempt, proceed" or "challenge required." Crucially, log the exemption reason on the consent or payment record: when the fraud rate on your book rises past the threshold that let you claim the risk-analysis exemption, you must revoke that exemption automatically, and you can only do that if you know which transactions relied on it. Treat exemptions as revocable claims with an audit trail, never as a silent fast path.

## The consent lifecycle and revocation

A consent moves through a small set of states, and every transition is a place where something can be audited or can go wrong. Created in `AwaitingAuthorisation`, it becomes `Authorised` after successful SCA and approval, and from there ends in `Expired`, `Revoked`, or (for PIS) `Consumed`. The account holder can revoke at any time through the bank's own channel; the TPP can revoke through the API; and the bank can revoke for its own risk reasons. Any of those must immediately invalidate outstanding access and refresh tokens tied to that consent — revocation that only marks a database column but leaves live tokens working is a data-leak waiting to be found.

Two operational realities shape the design. First, long-lived AIS consents require periodic re-authentication — a fresh SCA on a defined cadence — so a consent granted once is not a permanent standing key. Build the "re-auth due" transition into the state machine and surface it to the TPP as a specific error that triggers a re-consent flow rather than a generic 401. Second, expiry and revocation should be enforced at read time and swept by a background job; do not rely on either alone. The background sweep catches consents whose expiry passed while idle; the read-time check catches the race where a consent is revoked mid-session.

## What to get right

- Make the consent a durable resource with its own id and state machine, decoupled from token lifetime, so you can audit and revoke access as a unit.
- Keep AIS and PIS as distinct trust models; enforce a PIS consent against the exact payment it authorised, not a broad scope claim.
- Treat authentication as a pluggable step and exemptions as logged, revocable claims — never a silent bypass.
- Propagate revocation and expiry to live tokens instantly, and back it with both a read-time check and a background sweep.

The account and payment endpoints behind this layer are the easy part. The consent object, the scope boundary, and the authentication decision are the system, and they are worth modeling with the same rigor you would give a ledger.
