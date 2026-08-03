# Proof of Reserves: Merkle Attestations of Solvency
*How a custodian proves it holds what it owes, what the cryptography actually guarantees, and where the guarantee stops.*

When you deposit money with a custodian or trading venue, you are trusting a private ledger you cannot see. The balance shown in the app is a database row. Nothing about that row tells you whether the assets backing it still exist. Proof of Reserves (PoR) is an engineering pattern that turns "trust us" into "verify us," at least partially. It answers two questions with cryptography instead of a promise: *what do you owe customers?* and *what do you actually hold?* This post walks through building both halves, keeping customer privacy intact, and being honest about the guarantee's sharp edges.

## Two Sums That Must Balance

Solvency is a simple inequality: **reserves ≥ liabilities**. Liabilities are the total of every customer balance the custodian is on the hook for. Reserves are the total assets the custodian controls on-chain. A credible PoR must let an outside party confirm the inequality holds *and* let each customer confirm their own balance was counted on the liabilities side. If either half is unverifiable, the whole exercise collapses into a marketing claim.

The trick is doing this without publishing every customer's balance to the world, and without letting the custodian quietly drop unfavorable accounts from the liability total. A Merkle tree solves both problems at once.

```
                    Committed root  ─────────────►  published in attestation
                          H(AB|CD)
                        /          \
                 H(A|B)              H(C|D)
                /      \            /      \
            leaf A   leaf B     leaf C   leaf D
          H(salt,42) H(salt,17) ...      ...
              │
        customer A's balance: 42
        proof for A = [ leaf B , H(C|D) ]   ◄── siblings only
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-proof-of-reserves.html)** — sources (customer ledger, on-chain wallets) flow through aggregation into a committed root and solvency check, ending in a signed attestation and per-customer inclusion proof.

## Proof of Liabilities: A Merkle Tree of Balances

Every customer balance becomes a leaf. The naive leaf is just `hash(balance)`, but that leaks information and enables guessing: balances are low-entropy, so an attacker could brute-force which leaf is whose. Instead each leaf is `hash(salt || user_id || balance)`, where the salt is a per-user random nonce the custodian shares privately with that user. The salt makes leaves unguessable while still letting the owner reconstruct their own leaf.

Leaves are paired and hashed upward until a single 32-byte **root** remains. That root is a commitment: it is computationally infeasible to find a different set of balances that produces the same root, so once published, the custodian cannot retroactively edit any balance. The root is the liability side's fingerprint.

To let customer A verify inclusion, the custodian hands A a **proof path**: the sibling hashes needed to recompute the root from A's leaf. In the diagram above, A receives `leaf B` and `H(C|D)`. A recomputes `H(A|B)`, then `H(AB|CD)`, and checks it equals the published root. Crucially, A learns *nothing* about B, C, or D's actual balances, only their intermediate hashes. Privacy holds because a hash reveals nothing about its preimage.

A subtle but critical detail: interior nodes must also carry a running **sum** of balances, not just a hash. A tree that commits only to hashes proves inclusion but not that the leaves add up to the claimed total. The standard fix (a "summation Merkle tree") stores `(hash, sum)` at every node, and each parent asserts `parent.sum = left.sum + right.sum`. Now a verifier walking the proof path can confirm both that their leaf is included *and* that no negative or fabricated balances were smuggled in to shrink the total. Without the summing invariant, a custodian could insert a leaf with a negative balance to understate what it owes.

## Proof of Reserves: Signing With the Keys

The assets side is more direct because blockchains are already public. The custodian publishes the list of on-chain addresses it controls; anyone can read the current balance of each address directly from the ledger. The missing piece is *ownership*: reading an address balance proves the coins exist, not that this custodian controls them.

Ownership is proven by signatures. For each claimed address, the custodian signs a challenge message (often a well-known string plus the attestation date) with the address's private key. A valid signature over a fresh, dated message proves control at that moment without moving funds. The reserve prover verifies every signature, discards any address that fails, and sums only the verified balances. Addresses that cannot be signed for simply do not count.

This is where reserves and liabilities meet at the **solvency check**: verified reserve total on one side, summed liability root on the other. If reserves ≥ liabilities, the custodian is solvent for that snapshot, and the result is packaged into a signed attestation alongside the published root.

## Privacy Is a Design Constraint, Not an Afterthought

The privacy properties are worth stating precisely, because they are easy to break:

- **Leaves are salted** so balances cannot be brute-forced from published hashes.
- **Proof paths reveal only siblings**, and siblings are hashes, not balances. Your neighbor in the tree stays opaque.
- **The tree shape can leak the customer count**, so many implementations pad to a power of two with dummy zero-value leaves.
- **Repeated attestations can correlate** a user's leaf position over time; rotating salts and shuffling leaf order between snapshots mitigates this.

A common mistake is publishing the entire tree for "transparency." That defeats the point: with all leaves public, salted or not, an observer can often deanonymize by cross-referencing known deposit amounts. The correct posture is that only the root is public; proof paths are delivered privately to each account holder.

## The Limits That Matter

PoR is genuinely useful, but it is not a solvency guarantee, and pretending otherwise is dangerous. The honest caveats:

**It is point-in-time.** An attestation captures one instant. A custodian can borrow assets minutes before the snapshot, prove reserves, and return them after. Frequent, unpredictable attestations reduce this window but never close it. Continuous PoR is an unsolved operational problem, not a checkbox.

**It cannot prove the absence of hidden liabilities.** The Merkle tree proves the balances *the custodian chose to include* sum correctly. It says nothing about off-book debts: undisclosed loans, obligations to lenders, or customer accounts deliberately omitted from the tree. This is the deepest limitation. Inclusion proofs let *participating* customers detect their own omission, but only if enough customers actually check. If most users never verify, a custodian can drop accounts and likely go unnoticed.

**It does not prove the keys are still controlled.** A signature proves control at signing time. It does not prove the custodian will not lose or misuse the keys tomorrow, nor that the same coins were not pledged as collateral elsewhere.

**Shared addresses double-count.** If two custodians pledge the same reserve address, each can produce a valid signature. Cross-custodian PoR requires exclusive control, which signatures alone do not establish.

## Where This Is Heading

The engineering frontier is closing these gaps with stronger cryptography. Zero-knowledge proofs can attest that every included balance is non-negative and that the sum matches, without revealing any balance or even the customer count, replacing the trust in the summation tree's construction with a verifiable circuit. Combining a zk proof of liabilities with on-chain reserve verification gives a much tighter statement than a hash root and a spreadsheet.

But no amount of cryptography converts a point-in-time snapshot into a continuous guarantee, or reveals a debt the prover refuses to commit. Treat Proof of Reserves as what it is: a strong, verifiable *lower bound* on honesty that shifts real work from blind trust to arithmetic, while leaving governance, auditing, and the timing gap firmly in human hands.
