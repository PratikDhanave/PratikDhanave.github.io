# Engineering EMVCo QR Payments

*Encode and decode EMVCo QR payloads (static vs dynamic), handle expiry, and reconcile QR-initiated payments.*

---

A QR-code payment looks trivial from the outside: point a camera at a square, confirm an amount, done. Underneath, the square is a strict little serialization format with a checksum, a currency, a merchant identity, and — if you designed it well — a handle you can reconcile against three days later when the money actually moves. Most of the pain in a QR payment system is not scanning; it is deciding what goes into the payload, whether the code is single-use, and how you tie a settlement record back to the intent that created it.

This post walks the encode/decode path for the EMVCo Merchant-Presented Mode (MPM) payload, contrasts static and dynamic codes, and works through the two problems that bite teams in production: expiry and reconciliation.

## The shape of the flow

```
 Merchant                Payer app             Acquirer / PSP          Ledger
 --------                ---------             --------------          ------
 build TLV   --QR-->   scan + decode   --init-->  authorize   --post-->  settle
 tags 00..63           verify CRC-16             match ref id           reconcile
 (static|dynamic)      confirm amount           debit payer            by QR id
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-qr-payments-emvco.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The merchant side owns encoding. The payer app owns decoding and validation. Everything to the right of the initiation is ordinary payment plumbing — the only thing that makes it *QR* plumbing is the reference you planted in the payload.

## The payload is a flat TLV string

An EMVCo QR is not JSON. It is a flat sequence of **tag-length-value** triples, each rendered as ASCII digits: a two-digit tag, a two-digit length, then exactly that many characters of value. Fields concatenate with no delimiter, because the length tells you where the next field begins.

A handful of tags carry most of the meaning:

- `00` Payload Format Indicator — always `01`
- `01` Point of Initiation Method — `11` static, `12` dynamic
- `26`–`51` Merchant Account Information — network-specific templates, themselves nested TLV
- `52` Merchant Category Code
- `53` Transaction Currency — ISO 4217 numeric (e.g. `356`, `840`)
- `54` Transaction Amount — omitted on static codes, present on dynamic
- `58` Country Code, `59` Merchant Name, `60` Merchant City
- `62` Additional Data — nested, holds the reference label / bill number
- `63` CRC — a checksum over everything before it

Encoding is a fold over ordered fields:

```python
def tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"

def build_payload(fields: list[tuple[str, str]]) -> str:
    body = "".join(tlv(tag, val) for tag, val in fields)
    # CRC is computed over the body PLUS the CRC tag+length header
    body += "6304"
    return body + f"{crc16_ccitt(body):04X}"
```

The subtlety is tag `63`: the checksum is calculated over the payload *including* the literal `6304` prefix but *excluding* the four hex characters it protects. Forget to append `6304` before running the CRC and every payer app will reject the code — a mistake that survives your unit tests if they also compute the CRC the wrong way.

## Static versus dynamic

The `01` tag draws the most important line in the format.

A **static** code omits the amount (`54`). The same square sits on a countertop for months; the payer types the amount into their own app. It is cheap to produce and impossible to make single-use, which has a direct consequence: the QR itself carries no per-transaction identity, so two customers paying the same merchant produce indistinguishable initiations. You reconcile on whatever the acquirer echoes back, not on anything you controlled.

A **dynamic** code is minted per transaction. It carries the amount, and — this is the part teams skip — a reference you generate and persist *before* rendering the image. That reference goes in the tag `62` additional-data template (commonly the reference label, `62-05`). It is your join key for the rest of the payment's life.

```python
ref = new_reference()                 # e.g. "INV-2026-8841-a1"
store_intent(ref, amount, currency, expires_at)
fields = [
    ("00", "01"), ("01", "12"),       # dynamic
    ("53", "356"), ("54", f"{amount:.2f}"),
    ("58", "IN"), ("59", "ACME STORE"), ("60", "PUNE"),
    ("62", tlv("05", ref)),           # reference label -> your join key
]
qr_string = build_payload(fields)
```

Rule of thumb: if you ever need to answer "did *this* customer pay *this* bill," you need a dynamic code with a reference you own. Static codes are fine for tip jars and donation boxes, not for invoices.

## Decode, then validate before you trust anything

Decoding is the inverse fold, but the order of checks matters. Verify the CRC *first* — a corrupted scan or a doctored code fails here, and you want to reject before parsing user-facing fields.

```python
def parse(s: str) -> dict:
    got = s[-4:]
    if f"{crc16_ccitt(s[:-4]):04X}" != got.upper():
        raise ValueError("CRC mismatch")
    out, i = {}, 0
    while i < len(s) - 4:            # stop before the CRC field
        tag, length = s[i:i+2], int(s[i+2:i+4])
        out[tag] = s[i+4 : i+4+length]
        i += 4 + length
    return out
```

After the CRC passes, the app still has to make a judgment call: does tag `01` say dynamic? Then honor the amount in `54` and do not let the user edit it. Static? Prompt for an amount. Reading the initiation method wrong is how you end up letting a customer overwrite a fixed invoice total.

## Expiry and idempotency

A dynamic code represents an *intent*, and intents go stale. EMVCo has no universal expiry tag, so expiry lives on your side: store `expires_at` with the reference, and reject an initiation whose reference has aged out or has already been consumed. Treat the reference as an idempotency key — the first successful authorization consumes it, and a replayed scan of the same image maps to the same intent rather than charging twice.

Static codes have no reference, so they cannot expire and cannot be made idempotent from the payload alone. That is not a bug to fix; it is the trade-off you accept when you print one square and walk away.

## Reconciliation keyed by QR id

Settlement arrives asynchronously, often batched hours later, and it is only useful if you can match each settled line back to an intent. For dynamic codes this is clean: the acquirer returns your tag `62` reference on the clearing record, you look up the stored intent, confirm the amount and currency agree, and mark it settled. Mismatches — a settled amount that differs from the intent, or a reference with no stored intent — go to an exceptions queue rather than silently closing the ledger entry.

For static codes you have no such key, so reconciliation degrades to matching on merchant id, amount, and timestamp windows, which is inherently fuzzy. The engineering lesson generalizes past QR entirely: the cheapest reconciliation is the identifier you chose to embed at initiation time. Plant a unique, persisted reference in the payload up front, and the settlement side becomes a lookup instead of a heuristic.
