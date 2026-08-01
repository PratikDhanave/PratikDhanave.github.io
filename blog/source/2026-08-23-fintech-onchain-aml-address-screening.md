# On-Chain AML: Clustering and Risk-Scoring Blockchain Addresses

*Cluster and risk-score blockchain addresses for on-chain AML and sanctions exposure.*

Traditional AML works on identities: a name, a date of birth, a bank account. On a public blockchain you rarely have any of that. You have an address — a pseudonymous string — and a permanent, append-only ledger of everything it ever touched. The engineering problem is to turn that raw graph into a decision: can this deposit be credited, or does it carry sanctions or laundering exposure that forces a hold?

This post walks through the pipeline an exchange or custody platform builds to answer that question. The moving parts are address clustering, exposure analysis against a labeled entity set, a scoring function, and a routing decision into allow, block, or review. None of it is exotic, but each stage has failure modes that quietly break compliance if you get them wrong.

## The Screening Pipeline End to End

At a high level the flow is linear: an address or transaction arrives, we resolve it to a cluster of related addresses, we trace that cluster's exposure to known-risky entities, we collapse the evidence into a score, and we route on the score.

```
address / tx
     │
     ▼
[ ingest ]───▶[ clustering ]───▶[ exposure ]───▶[ score ]───▶ decision
  normalize     wallet graph      trace hops      weighted     allow
  dedupe        heuristics        vs. label set   + threshold  block
                                                               review
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-onchain-aml-address-screening.html)** — pan, zoom, and trace every step (light/dark, self-contained).

The subtlety is that every stage is *directional in confidence*. Ingest is deterministic. Clustering is heuristic and probabilistic. Exposure tracing is bounded by how many hops you are willing to walk. Scoring is a policy choice. By the time you reach the decision, you are combining a hard fact (this address received funds from a sanctioned cluster two hops back) with several soft inferences (these five addresses are probably one wallet). Keeping that provenance attached to the score is what lets an investigator later defend the decision.

## Address Clustering: One Entity, Many Addresses

A single custodial wallet or laundering operation controls thousands of addresses. Screening a lone deposit address in isolation tells you almost nothing; you have to resolve it to the entity behind it. That is clustering, and on UTXO chains the workhorse is the **common-input-ownership** heuristic: if two addresses appear as inputs to the same transaction, they are almost certainly controlled by the same party, because signing that transaction required all their private keys.

```
tx spends inputs {A, B, C} ─▶ A, B, C join one cluster
tx spends inputs {C, D}    ─▶ D joins the same cluster (via C)
                              cluster = {A, B, C, D}
```

A second heuristic is change-address detection: a payment usually has one output going to the counterparty and one going back to the sender as change. Identify the change output and you extend the cluster. On account-based chains the picture differs — there is no change output — so you lean on deposit-address reuse, funding patterns, and smart-contract interaction signatures instead.

The trap here is over-merging. Coinjoin and other privacy transactions deliberately violate common-input-ownership by combining inputs from unrelated parties. If your clustering engine ingests those naively, it will fuse a sanctioned wallet with hundreds of innocent ones and poison every downstream score. Production clustering therefore carries a **confidence weight** per merge and refuses to propagate high-risk labels across low-confidence edges.

```python
def merge_confidence(edge):
    if edge.type == "common_input" and not edge.is_coinjoin:
        return 0.95
    if edge.type == "change_detection":
        return 0.70          # heuristic, revisable
    if edge.type == "coinjoin_input":
        return 0.10          # do not propagate risk across this
    return 0.50
```

## Exposure Analysis: Tracing to Labeled Entities

Once you have a cluster, you measure its **exposure**: how much of its value can be traced to or from entities you have labeled as risky. Labels come from a maintained dataset — sanctioned addresses, known mixer contracts, darknet markets, ransomware wallets, and stolen-funds pools — each tagged with a category and severity.

Exposure is a graph traversal with two directions and a hop budget:

- **Inflow (source-of-funds):** walk backward from the cluster. Where did the money come from? Direct receipt from a sanctioned address is the strongest possible signal.
- **Outflow (destination):** walk forward. Where is the money going? Sending to a sanctioned entity is equally disqualifying.

Distance matters. Funds one hop from a mixer are far more suspicious than funds five hops away that have passed through legitimate exchanges. Most engines apply **decay by hop** and stop at a configured depth, because exposure fans out combinatorially and every address is within a few hops of *something* if you walk far enough.

```
sanctioned ──hop1──▶ mixer ──hop2──▶ hop3 ──▶ [ target cluster ]
   1.00              0.60           0.36        exposure contribution
   (direct)          (×0.6)         (×0.6²)     decays with distance
```

Two exposures with identical dollar amounts are not equal: direct receipt from a sanctions address is a hard block regardless of size, while faint indirect exposure to a market that closed years ago may be noise. The scoring stage is where that judgment gets encoded.

## Scoring and the Allow / Block / Review Decision

The score collapses all exposure evidence into one number plus a set of triggered reasons. A simple, defensible model is a weighted sum with hard overrides:

```python
def score(cluster):
    hard = any(e.category == "sanctions" and e.hops <= 1
               for e in cluster.exposures)
    if hard:
        return Decision("BLOCK", 100, reasons=["direct sanctions exposure"])

    total = sum(e.severity * e.value_share * decay(e.hops)
                for e in cluster.exposures)
    reasons = [e.category for e in cluster.exposures if e.severity >= 0.5]

    if total >= 0.75:
        return Decision("BLOCK",  round(total * 100), reasons)
    if total >= 0.30:
        return Decision("REVIEW", round(total * 100), reasons)
    return Decision("ALLOW",      round(total * 100), reasons)
```

Three routes come out of this, and each has an operational contract:

- **Allow** — credit the funds. Still logged, because a later label update can retroactively change the picture and you want the history.
- **Block** — reject or freeze. This must be reversible only through a documented process, and it must record the exact exposure path that triggered it.
- **Review** — hold and queue for a human analyst. This is the pressure-relief valve for the ambiguous middle band, and its sizing is a business decision: too low a threshold buries your investigators, too high lets risk through.

The reasons list is not optional decoration. When a regulator or an internal auditor asks why a transaction was blocked, "score was 82" is not an answer; "direct one-hop inflow from an OFAC-listed cluster totaling 40% of value" is. Attach the provenance to the decision at the moment you make it.

## Operational Realities That Bite

A few things separate a demo from a system compliance will sign off on.

**Labels change; history does not.** New sanctions designations and newly attributed hacks land constantly. An address you cleared yesterday can become toxic today. You need to re-screen retained clusters against label deltas, and you need clear policy on whether a fresh label triggers retroactive action on already-credited funds.

**Determinism for defensibility.** The same address screened twice must yield the same decision, or the block cannot be defended. That means pinning the label-set version and the clustering snapshot used for each decision, and storing both alongside the outcome.

**Latency budgets.** A hot deposit path cannot wait on a deep multi-hop graph walk. The usual split is a fast inline check (direct and one-hop exposure) that gates crediting in milliseconds, backed by a deeper asynchronous re-screen that can retroactively flag for review.

**Privacy-tool handling.** Mixers and privacy protocols are not automatically illicit, but they break the traceability the whole pipeline depends on. Treat funds emerging from them as an exposure category in their own right rather than pretending the trail simply ended.

Get these four right and the pipeline stops being a scoring toy and becomes something an investigator can stand behind — which, in the end, is the only property that matters.
