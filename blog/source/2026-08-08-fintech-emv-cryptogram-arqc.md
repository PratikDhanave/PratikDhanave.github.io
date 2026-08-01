# EMV Cryptograms: ARQC, ARPC, and Offline Data Authentication

*How a chip card proves it is genuine on every single transaction — and why a cloned magstripe never could.*

The magnetic stripe was a static secret. Whatever was encoded on track 2 was the same on the tenth swipe as on the first, so anyone who read it once could replay it forever. EMV chip cards changed the security model entirely: instead of presenting a fixed secret, the chip *computes a fresh proof* for each transaction. That proof is the **cryptogram**, and understanding how it is built, validated, and defended against replay is the core of card-present payment engineering.

This post walks the transaction from the engineer's side: key derivation, the exact inputs to the cryptogram, offline data authentication, terminal risk management, and the online round trip that produces an ARPC.

## The cryptogram is a MAC, not a signature

An **ARQC** (Authorization Request Cryptogram) is a symmetric MAC — typically Triple-DES or AES in CBC-MAC mode — computed by the chip over the transaction data using a secret key that only the card and the issuer share. It is not a public-key signature; it is fast, small (8 bytes), and verifiable only by a party holding the same key. That party is the issuer.

The issuer never actually stores a unique key per card in a giant table. Instead it holds one **Issuer Master Key (IMK)** and *derives* each card's key on the fly.

## Key derivation: master key to card to session

There are two derivation layers, and both matter for replay resistance:

1. **Card master key (MK).** At personalization the issuer derives the card's key from the IMK and the PAN plus PAN sequence number:
   `MK_card = KDF(IMK, PAN || PSN)`. Every card gets a distinct key, but the issuer only guards the IMK inside an HSM.
2. **Session key (SK).** For each transaction the card derives a per-transaction key from `MK_card` and the **ATC** (Application Transaction Counter), a monotonic counter the chip increments and never reuses:
   `SK = KDF(MK_card, ATC)`.

The ATC is the linchpin of freshness. Because the session key changes every transaction and the counter only moves forward, two transactions can never produce the same cryptogram, and a captured ARQC cannot be replayed — the issuer tracks the ATC and rejects a value it has already seen or one that has gone backwards.

## What goes into the cryptogram: the CDOL

The chip does not decide which fields to sign. The terminal and card negotiate this through the **CDOL1** (Card Risk Management Data Object List) — a template the card publishes that tells the terminal exactly which data elements to concatenate and hand back in the `GENERATE AC` command. Typical CDOL1 inputs include:

- **Amount, Authorized** and **Amount, Other** (cashback)
- **Terminal Country Code** and **Transaction Currency Code**
- **Terminal Verification Results (TVR)** — the terminal's own risk findings
- **Transaction Date** and **Transaction Type**
- **Unpredictable Number (UN)** — a random nonce the terminal generates
- **ATC** — supplied by the card itself

The MAC is computed over this concatenation with the session key. Two properties fall out immediately. First, the **amount and currency are cryptographically bound** to the cryptogram, so a man-in-the-middle cannot alter the value without invalidating it. Second, the **Unpredictable Number** injects terminal-side randomness, so even a replayed set of card inputs won't match unless the fraudster can also predict the terminal's nonce.

```
  Chip card                Terminal (POS)              Issuer host
     |                          |                          |
     |<----- SELECT AID --------|                          |
     |-- records + SDA/DDA ---->|  (offline data auth)     |
     |                          |                          |
     |<-- GENERATE AC (CDOL1) --|  amount|UN|TVR|ATC ...   |
     |                          |                          |
   [ SK = KDF(MK_card, ATC) ]   |                          |
   [ ARQC = MAC(SK, CDOL data)] |                          |
     |----- ARQC + ATC -------->|                          |
     |                          |--- online auth (ARQC) -->|
     |                          |            [ recompute ARQC in HSM ]
     |                          |            [ ARPC = f(ARQC, RC) ]
     |                          |<--- ARPC + response ------|
     |<- EXTERNAL AUTH (ARPC) --|                          |
   [ verify ARPC ]              |                          |
     |----- TC (2nd AC) ------->|  (settle for clearing)   |
     v                          v                          v
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-emv-cryptogram-arqc.html)** — the same ARQC/ARPC exchange with offline authentication and the online round trip, rendered as an explorable sequence.

## Offline data authentication: SDA, DDA, CDA

Before any cryptogram is generated, the terminal wants to know the card data itself is genuine — especially important when the terminal may decide to approve **offline** without contacting the issuer at all. This is **Offline Data Authentication (ODA)**, and it comes in three flavours of increasing strength, all built on a public-key chain rooted in a scheme **Certificate Authority public key** stored in the terminal.

- **SDA (Static Data Authentication).** The issuer signs a fixed block of card data at personalization. The terminal verifies that signature with the issuer's certificate, which is itself signed by the CA. SDA proves the data was issued legitimately — but the signed block is *static*, so a fraudster who copies it onto a counterfeit card can pass SDA. SDA alone does not stop cloning.
- **DDA (Dynamic Data Authentication).** The card carries its own RSA key pair. The terminal sends a challenge (a nonce), and the card signs it with its private key. Because the private key never leaves the chip and the response is dynamic, a copied data dump can't produce valid DDA responses. This defeats simple cloning.
- **CDA (Combined DDA/Application Cryptogram).** DDA and the cryptogram are computed together: the card's dynamic signature covers the ARQC itself. This closes a gap where an attacker relays a valid DDA but tampers with the cryptogram or the amount. CDA is the strongest and is now the default for contactless and high-value flows.

The engineering takeaway: SDA is authentication of *data*, DDA/CDA is authentication of the *card*, and only the cryptogram authenticates the *transaction*.

## Terminal risk management: when to go online

The terminal is not a passive pipe. It runs its own checks and records them in the **TVR**, then decides whether the transaction can be approved offline or must go online:

- **Floor limits** — amounts above a configured threshold force an online authorization.
- **Random transaction selection** — even small amounts are sometimes sent online to sample for fraud.
- **Velocity checks** — the card's own counters (lower and upper consecutive offline limits) push a transaction online once too many offline approvals accumulate.
- **Offline PIN** — the PIN can be verified by the chip locally (plaintext or enciphered) without the issuer, distinct from online PIN which is sent in a PIN block to the host.

The terminal expresses its decision by asking the card for a specific cryptogram type in `GENERATE AC`: a **TC** (Transaction Certificate) to approve offline, an **ARQC** to go online, or an **AAC** to decline. The card, applying its own risk rules, can refuse to grant a stronger outcome than the terminal requested — for instance downgrading an offline approval to an online request.

## The online round trip and the ARPC

When the ARQC is sent to the issuer, the host reconstructs the same session key from the IMK, PAN, and ATC inside an HSM, recomputes the MAC over the received data, and compares. A match proves the card is genuine and the data untampered.

The issuer then returns an **ARPC** (Authorization Response Cryptogram) — commonly the ARQC combined (XOR) with a 2-byte Authorization Response Code and MACed again with the session key. The card verifies the ARPC on receiving `EXTERNAL AUTHENTICATE`, confirming the response genuinely came from the issuer and not a spoofed host. This is mutual authentication: the ARQC proves card-to-issuer, the ARPC proves issuer-to-card.

Finally the card issues a second `GENERATE AC`, producing a **TC** that becomes the settlement record submitted during clearing.

## Why replay and cloning lose

Put the pieces together and the defences compose:

- **Replay** fails because the ATC advances every transaction and the issuer rejects stale or reused counters; the session key and therefore the cryptogram are never repeated.
- **Amount tampering** fails because the amount and currency are inside the MACed CDOL data.
- **Host spoofing** fails because the ARPC forces the issuer to prove key possession back to the card.
- **Cloning** fails under DDA/CDA because the card's private key and its ability to compute a fresh cryptogram cannot be copied from a static data read.

The static magstripe secret became a moving target: a fresh, key-bound, counter-protected proof computed on-card for every tap and dip. That single shift — from presenting a secret to computing a proof — is why chip payments hold up.
