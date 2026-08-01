# Building for Instant Payments: RTP, FedNow, and Request-for-Payment
*How to engineer for 24x7 irrevocable instant credit — synchronous ISO 20022 messaging, request-for-payment flows, and idempotent liquidity checks with no batch cutoff.*

Most payment code I have worked on assumes a batch. You accept an instruction, write it to a file or a queue, and a scheduled job flushes it at a cutoff. Failures are cheap because nothing is final until the batch settles, and you have hours to correct a bad row. Instant rails delete that comfort. On systems like RTP and FedNow a credit transfer is authorized, cleared, and made final in a couple of seconds, the money is irrevocable the moment the receiving bank accepts, and the rail runs every second of every day with no window to hide in. This post is about the engineering consequences of that model, not the marketing around it.

## From a deferred queue to a synchronous request

The first mental adjustment is that the payment is a synchronous request/response, not a fire-and-forget submission. When you send a credit transfer message you block on the answer. The rail will tell you, within its timeout budget, one of three things: the payment was accepted and is final, it was rejected, or — the dangerous case — you did not get an answer at all.

The messages themselves are ISO 20022 XML. A `pacs.008` carries the interbank credit transfer; the rail responds with a `pacs.002` payment status report whose `TxSts` field is the outcome, typically `ACCP`/`ACSC` for accepted-and-settled or `RJCT` with a reason code. Because everything is synchronous, your service is holding an open connection and an in-flight database transaction for the whole round trip. That reframes capacity planning: you size for concurrent in-flight payments and tail latency, not for nightly throughput.

## Anatomy of an instant credit transfer

The core happy path threads five actors. The payer instructs their bank, the sending bank screens the payment and hands a `pacs.008` to the clearing system, the clearing system routes it to the receiving bank, and the receiving bank must accept or reject within the rail's window. Only after the receiving bank's acceptance is the money final and the payee credited.

```
Payer      Sending Bank        Clearing (RTP/FedNow)      Receiving Bank     Payee
  |  init      |                        |                        |             |
  |----------->|  liquidity + fraud     |                        |             |
  |            |----check (hot path)     |                        |             |
  |            |  pacs.008              |                        |             |
  |            |----------------------->|   forward pacs.008     |             |
  |            |                        |----------------------->| accept?     |
  |            |                        |   pacs.002 ACCP        |<------------|
  |            |   settled (final)      |<-----------------------|  credit     |
  |            |<-----------------------|                        |------------>|
  |  confirmed |                        |                        |             |
  |<-----------|                        |                        |             |
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-rtp-fednow-instant-payments.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The key property to internalize: acceptance and finality happen at the far end, but your sending service learns about them second-hand through the clearing response. The gap between "receiving bank accepted" and "sending bank knows it accepted" is exactly where reliability engineering lives.

## Request-for-payment: pull without a mandate

Instant rails also support a pull-style flow, request-for-payment (RfP), which is easy to misunderstand. An RfP is not a direct debit and carries no standing mandate. It is a `pain.013` message asking a payer to send a credit transfer, and the payer's bank presents it for an explicit, per-request approval. Nothing moves until the payer says yes; when they do, the response is an ordinary credit transfer in the direction described above.

That distinction matters in your data model. An RfP is a first-class object with its own lifecycle — requested, presented, accepted, declined, expired — and it is only *linked* to the eventual payment, not the same record. A biller sends the RfP; the actual movement of funds is a separate `pacs.008` initiated by the payer's bank once approval lands. Conflating the two produces a schema where you cannot answer "was this request paid, and by which transfer" without guessing.

## Liquidity and fraud checks belong in the hot path

Because there is no batch, there is no later opportunity to reverse a bad decision. Every check that used to run as a nightly sweep now has to execute inside the two-second window, before you emit the `pacs.008`. Two checks dominate: does the debtor account actually have the funds and the bank the settlement liquidity, and does this payment look fraudulent.

Both are decisions you make under a latency budget while holding an open transaction, and both have to be idempotent, because the ugly reality of a synchronous rail is the ambiguous timeout. If you send a `pacs.008`, time out waiting for the `pacs.002`, and retry, the rail may have already processed the first attempt. The defense is that the message identity, not your retry loop, defines the operation. The end-to-end identifier is chosen once and reused on every retry, and the debit is guarded by it:

```python
def send_transfer(intent):
    # e2e_id is derived once and pinned to the intent, never regenerated
    e2e_id = intent.end_to_end_id
    with tx():
        if ledger.already_debited(e2e_id):
            return ledger.status_for(e2e_id)   # replay, do not double-debit
        reserve = liquidity.check_and_hold(intent.debtor, intent.amount, e2e_id)
        if not reserve.ok:
            return reject("AM04")              # insufficient funds
        if fraud.score(intent) > THRESHOLD:
            return reject("FRAD")
        ledger.debit(intent.debtor, intent.amount, ref=e2e_id)
    return rail.submit_pacs008(intent, e2e_id) # outcome reconciled by e2e_id
```

The rule is that a retry with the same end-to-end identifier is a no-op on anything that already happened. The liquidity hold, the ledger debit, and the rail submission all key off the same identifier so the second attempt observes the first attempt's effects instead of repeating them.

## Timeouts, uncertainty, and reversal

There is no clean "cancel" on an instant rail. Once the receiving bank accepts, the funds are the payee's, and any correction is a *new* payment — either a return initiated by the receiving side or a request to the payee to send the money back. Your code should never assume it can undo a settled transfer; it can only originate a compensating one.

The genuinely hard state is the unknown. When a `pacs.008` times out, the payment is in an indeterminate state: possibly settled, possibly never processed. You must not blindly resubmit and you must not blindly abandon it. The correct move is a status inquiry keyed on the end-to-end identifier — most rails expose a mechanism to ask "what happened to this UETR/e2e id" — and you resolve the ledger entry from the authoritative answer. Until that answer arrives, the debit stays in a pending-verification state, not booked as either success or failure. Treating a timeout as a failure is how you strand a customer's money.

## What actually changes in your architecture

Pulling it together, four assumptions from the batch world stop holding:

- **No cutoff means no idle window.** Deployments, migrations, and key rotations have to happen while the rail is live and irrevocable. Blue-green with connection draining replaces the maintenance window you used to rely on.
- **Finality is external and second-hand.** Your ledger's source of truth for "did this settle" is the rail's status response, not your own submission, so reconciliation against `pacs.002` outcomes is a first-class subsystem, not a nightly afterthought.
- **Idempotency is mandatory, not defensive.** The ambiguous timeout is a routine event at instant-payment volumes. Every mutation on the send path keys off the message identifier so retries converge instead of duplicating.
- **Risk moves into the request.** Liquidity and fraud decisions run inline under a hard latency budget, which pushes you toward precomputed limits, cached signals, and fast-failing checks rather than deep synchronous lookups.

None of this is exotic once you accept the core constraint: the money is final in seconds and the rail never sleeps, so correctness has to be established before you emit the message and reconciled from the rail's own answer afterward. Build for the ambiguous timeout and the irrevocable credit first, and the happy path takes care of itself.
