# Integrating 3-D Secure 2 Without Breaking Your Checkout

*Wiring the 3DS Server, Directory Server, and issuer ACS into a handshake that produces a cryptogram your authorization message can carry.*

---

## Why 3DS2 is an engineering problem, not a checkbox

3-D Secure 2 sits between "customer pressed Pay" and "we send an authorization to the network." Its job is to let the card issuer authenticate the cardholder before money moves, and — when authentication succeeds — to shift chargeback liability for fraud away from the merchant. The first version bolted a full-page redirect onto every transaction and taxed conversion badly. The second version replaces that with a data-rich, mostly invisible exchange: the merchant collects device and transaction context up front, the issuer scores it, and only genuinely risky payments get an interactive challenge.

For an engineer the hard parts are not conceptual. They are the state you have to hold between an asynchronous browser flow and a synchronous authorization call, the three server roles that each own a slice of the protocol, and the small set of fields — ECI, CAVV/AAV, and the transaction identifier — that must survive from authentication into the auth message intact. Get the plumbing wrong and you either lose the liability shift you paid for, or you strand a customer on a spinner.

## The three roles and the message vocabulary

Four actors carry the protocol. The **3DS Server** (also called the 3DS Requestor Environment) is yours, or your PSP's — it packages the authentication request. The **Directory Server (DS)** is run by the card scheme; it routes the request to the correct issuer by BIN range. The **Access Control Server (ACS)** belongs to the issuer and makes the actual authentication decision. The cardholder's browser or app is the fourth.

The messages between them are compact and worth memorizing:

```
  Browser        3DS Server            DS (scheme)         ACS (issuer)
    |   device data  |                     |                    |
    |--------------->|                     |                    |
    |                |------ AReq --------->|------ AReq ------->|
    |                |                      |                    | risk score
    |                |<----- ARes ----------|<----- ARes --------|
    |                |                                           |
    |   [frictionless: ARes carries CAVV/ECI -> go authorize]    |
    |                |                                           |
    |   [challenge: browser -> ACS CReq/CRes -> RReq/RRes]       |
    |<===== 3DS Method + Challenge UI (iframe) ================>|
    |                |<---- result (RReq/RRes) --- ACS ----------|
    |  authenticated: ECI + CAVV + dsTransID -> authorization    |
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-3ds2-authentication-flow.html)** — pan, zoom, and trace every step (light/dark, self-contained).

`AReq`/`ARes` is the authentication request and response. `CReq`/`CRes` carry the interactive challenge between the browser and the ACS. `RReq`/`RRes` deliver the final challenge result back to your 3DS Server out of band. The whole point of 2.x is that most transactions stop after `ARes` — that is the frictionless path.

## Device data collection and the 3DS Method

Before you can send an `AReq`, the ACS wants a fingerprint of the shopping device. This is the **3DS Method**: during page load you render a hidden iframe pointing at a `threeDSMethodURL` the DS hands you for that BIN. The ACS drops a script that harvests screen size, timezone, browser characteristics, and prior-session signals, then posts a completion notification back.

The engineering catch is timing. The 3DS Method runs asynchronously and can take a few hundred milliseconds, but you should not block the customer on it. The clean pattern is to fire the method invisibly at the moment the customer reaches the payment page — well before they click Pay — so the fingerprint is already collected by authentication time. Give it a bounded timeout (10 seconds is the common ceiling); if it does not complete, you send the `AReq` with `threeDSCompInd=N` and let the ACS decide with less data rather than stall checkout.

The richer the `AReq` payload — billing/shipping address, prior transaction count, account age, cardholder email — the more likely the issuer returns a frictionless approval. Treat these fields as a conversion lever, not boilerplate.

## Frictionless versus challenge: the fork that decides everything

When the `ARes` comes back it carries a `transStatus`. That single field is your control flow:

| transStatus | Meaning | What you do |
|---|---|---|
| `Y` | Authenticated (frictionless) | Read CAVV + ECI, go authorize |
| `C` | Challenge required | Render the ACS challenge |
| `A` | Attempted (non-participating) | Liability may still shift; authorize |
| `N` | Not authenticated | Decline or route without shift |
| `R` / `U` | Rejected / unavailable | Fall back per your policy |

On `C`, you post the browser to the ACS's challenge URL inside an iframe — an OTP prompt, a banking-app push, or a biometric step the issuer controls entirely. You never see the customer's credentials. When the ACS finishes it POSTs a `CRes` to your notification URL and, separately, sends the authoritative `RReq` to your 3DS Server. Trust the `RReq` result, not the browser-delivered `CRes`, because the browser channel is attacker-reachable.

A crucial resilience rule: the challenge is a detour, not a new transaction. Persist the full cart, amount, and `threeDSServerTransID` keyed to the pending authentication so that when the challenge result lands — possibly seconds later, possibly after the customer switched to a banking app and back — you can resume the exact original authorization. Losing that context is the most common way teams silently drop authenticated payments.

## Carrying the proof into authorization

Authentication is worthless if its output never reaches the network. A successful 3DS2 flow yields three fields you must inject into the authorization message:

```
  ECI    -> Electronic Commerce Indicator (e.g. 05/02 = authenticated)
  CAVV   -> Cardholder Authentication Verification Value (the cryptogram)
  dsTransID -> Directory Server transaction id, ties auth back to authn
```

The CAVV (Visa) or AAV (Mastercard) is a cryptographic proof the issuer generated during authentication. Your acquirer places it, the ECI, and the DS transaction id into the appropriate authorization fields. The issuer's authorization system recomputes and validates the cryptogram; a mismatch or missing value means no liability shift even though your customer completed the challenge. In practice, wire and assert these fields end to end in a test harness against the scheme's sandbox before launch — a dropped CAVV is invisible in the happy path and only surfaces months later as lost chargebacks.

```python
def build_auth_request(cart, authn):
    # authn is the frozen 3DS2 result you persisted before authorizing
    req = base_authorization(cart)
    if authn.trans_status in ("Y", "A"):
        req.eci = authn.eci                 # authentication outcome
        req.cavv = authn.cavv               # issuer cryptogram
        req.three_ds_trans_id = authn.ds_trans_id
        req.three_ds_version = "2.2.0"
    return req
```

## Operational edges worth designing for

Three failure modes deserve explicit handling. First, **ACS unavailability**: if the issuer's ACS times out or returns `U`, you decide per risk appetite — proceed without a shift, or decline. Encode that as policy, not an exception handler. Second, **version negotiation**: not every BIN supports 2.2; your DS lookup tells you the supported range, and you must degrade to 2.1 fields or a non-3DS authorization cleanly. Third, **data-only and decoupled flows**: some regions let the issuer authenticate out of band and confirm later, so your state machine needs a "pending, resolve asynchronously" branch rather than assuming every authentication resolves within the checkout session.

Treat the whole thing as a small distributed transaction with one durable piece of state — the pending authentication keyed by `threeDSServerTransID` — and both the frictionless and challenge paths become the same resumable flow with different latencies. That framing, more than any field-level detail, is what keeps a 3DS2 integration from quietly leaking conversion or liability.
