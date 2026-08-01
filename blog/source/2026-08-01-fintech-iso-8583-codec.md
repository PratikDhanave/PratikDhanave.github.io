# Building a Byte-Level ISO 8583 Codec for Card Authorization

*A field-by-field guide to decoding bitmaps, data elements, and MTI so a raw TCP frame becomes a typed auth request you can trust.*

If you have ever integrated with a card scheme, a switch, or a legacy acquiring host, you have met ISO 8583. It is the wire format underneath most card authorization traffic on the planet, and it predates every convenience you take for granted. There is no JSON, no self-describing schema, no field names on the wire. What arrives is a length-prefixed blob of bytes: a message type, a bitmap that tells you which fields are present, and then those fields packed back to back with no delimiters. Your codec has to know the shape of every field in advance. This post walks through how I build one that is deterministic, testable, and safe to run in an authorization path.

## The frame and the message type indicator

An ISO 8583 message on a TCP stream is almost never framed by the connection itself. TCP gives you a byte stream, not messages, so the first job is length framing. Most switch links prefix each message with a two-byte length header, either binary (big-endian) or four ASCII digits. You read the header, read exactly that many bytes, and hand the resulting slice to the parser. Getting this wrong is the classic source of "the parser worked in tests but corrupts under load" bugs, because two messages get concatenated or one gets split. Frame first, parse second, always.

Once you have a single message slice, the first four bytes (or four ASCII characters) are the Message Type Indicator, the MTI. It encodes version, message class, function, and origin. `0100` is an authorization request, `0110` its response, `0200` a financial request, `0210` its response, `0800` a network management message like an echo test. The MTI is not decorative: it tells your dispatcher which handler and which field dictionary to use, because different message types legitimately carry different fields.

```
+--------+----------------+------------------------------------------+
| 2-byte | 4-char MTI     |  primary bitmap (+ optional secondary)   |
| length |  e.g. "0100"   |  then packed data elements DE2..DE128    |
+--------+----------------+------------------------------------------+
        \__ frame here __/ \__ parse this region field by field ____/
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-iso-8583-codec.html)** — pan, zoom, and trace every step (light/dark, self-contained).

## Bitmaps are the routing table

Immediately after the MTI comes the primary bitmap: 8 bytes, 64 bits. Bit *n* set means data element *n* is present in the message, in order. Bit 1 is special: it does not mean "DE1 is present," it means "a secondary bitmap follows," giving you fields 65 through 128. So parsing begins by reading 8 bytes, checking bit 1, and conditionally consuming another 8 bytes for the secondary bitmap.

I always decode bitmaps into an explicit ordered set of present field numbers before touching any field data. Keeping the two phases separate — first *which* fields, then *what* they contain — makes the parser far easier to reason about and to fuzz. A subtle detail: bitmaps are conventionally transmitted as raw binary, but some hosts send them hex-encoded as ASCII, doubling their length. Your framing config has to say which, because there is no way to tell 8 binary bytes from 16 hex characters by inspection alone.

```python
def present_fields(bitmap: bytes) -> list[int]:
    fields = []
    for byte_index, b in enumerate(bitmap):
        for bit in range(8):
            if b & (0x80 >> bit):
                fields.append(byte_index * 8 + bit + 1)
    return fields  # e.g. [2, 3, 4, 7, 11, 39, 41, ...]
```

Note that field 1 will appear in this list when a secondary bitmap is present; the caller treats that as a signal, not a data field.

## The field dictionary is the whole game

Every data element has a fixed definition: its length discipline, its encoding, and its maximum size. There are three length disciplines. **Fixed** fields are always the same width (DE3 processing code is always 6 digits). **LLVAR** fields carry a two-digit length prefix, so up to 99 units. **LLLVAR** fields carry a three-digit prefix, up to 999 units. The prefix "units" may be digits, bytes, or characters depending on the field's encoding, which is its own axis: BCD-packed numerics squeeze two digits into a byte, ASCII numerics use a byte per digit, and binary fields are opaque bytes.

The codec is a table. I define each field once and drive both decode and encode from the same definition, so the two directions can never drift apart:

```python
FIELD_SPEC = {
    2:  Field("PAN",            LLVAR,  numeric, max=19),
    3:  Field("Processing",     FIXED,  numeric, size=6),
    4:  Field("Amount",         FIXED,  numeric, size=12),
    11: Field("STAN",           FIXED,  numeric, size=6),
    37: Field("RRN",            FIXED,  ansi,    size=12),
    39: Field("ResponseCode",   FIXED,  ansi,    size=2),
    41: Field("TerminalID",     FIXED,  ansi,    size=8),
}
```

Decoding then becomes a loop over the present fields in ascending order: look up the spec, read the length prefix if the discipline requires one, consume exactly that many raw units, and decode according to encoding. Because every field consumes a precise number of bytes, the parser advances a cursor deterministically and must land exactly on the end of the slice. If it overshoots or leaves trailing bytes, the message is malformed and you reject it rather than guessing.

The dangerous fields are the numeric-with-odd-length BCD cases. DE2, the PAN, can be an odd number of digits; packed BCD then needs a nibble of padding, and your decoder has to strip it using the declared length, not the byte count. This is exactly the kind of rule that belongs in the field spec, not scattered through parsing code.

## From bytes to a typed object

The output of decoding should never be a raw dictionary of strings that the rest of your system re-parses. Lift it into a typed structure at the boundary: PAN as a validated card-number value object (Luhn-checked, never logged in full), amount as a minor-units integer paired with the currency from DE49, STAN and RRN as correlation identifiers. DE39, the response code, maps to an enum so `"00"` becomes `Approved` and everything else routes to a specific decline reason.

Those correlation fields matter operationally. The **STAN** (System Trace Audit Number, DE11) and **RRN** (Retrieval Reference Number, DE37) are how a `0110` response is matched back to its `0100` request across an asynchronous link where responses may arrive out of order. Your dispatcher keeps an in-flight map keyed by STAN (scoped per terminal or per link, since STANs wrap around at 999999) and completes the pending future when the matching response lands. Reversals and repeats reference the original STAN too, so treating it as a first-class identifier, not just a logged string, is what makes the whole conversation coherent.

## What makes it production-safe

Three practices separate a demo codec from one you trust in the authorization path. First, make the field table the single source of truth and generate a round-trip test that encodes then decodes every message type, asserting byte-for-byte equality — this catches encoding and length-discipline mistakes instantly. Second, fuzz the decoder with truncated and oversized frames; a codec that indexes past the end of a slice on a malformed bitmap is a denial-of-service waiting to happen. Third, redact by construction: because PAN and track data flow through the typed layer, you attach masking to those value objects so no code path can accidentally emit a full PAN to logs. Build the codec as a pure function from bytes to a typed message and back, keep the framing separate, and let a declarative field dictionary do the rest.
