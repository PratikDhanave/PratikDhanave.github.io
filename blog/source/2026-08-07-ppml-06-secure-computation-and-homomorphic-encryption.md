# Secure Computation and Homomorphic Encryption — Computing on Data You Can't See

*What if you could compute on data while it stays encrypted the entire time — never decrypting it, never seeing it, yet getting the correct result? It sounds impossible, but cryptography makes it real. Homomorphic encryption and secure multi-party computation let parties jointly compute on sensitive data that none of them can read, closing the one gap the other privacy techniques leave open: protecting data even during the computation itself. This post covers the most mathematically remarkable tools in the privacy toolkit.*

Posts 3–5 protected the model's output (differential privacy) and avoided centralizing data (federated learning), but both still compute on *cleartext* data somewhere. This post covers the techniques that protect data *while it's being used* — the cryptographic end of privacy-preserving ML. They're powerful, genuinely mind-bending, and bounded by real performance limits that decide where they fit.

## The gap: data is exposed during computation

Every technique so far has a moment where data is in the clear: differential privacy computes on real data then adds noise; federated learning trains on real local data then shares updates; even encrypted-at-rest data must be *decrypted to be used*. The exposure window is computation itself — to compute on data, you traditionally have to see it.

This matters whenever the party doing the computation shouldn't see the data:
- You want to use a cloud service's model on your sensitive input, but you don't want the cloud to see your input.
- Several hospitals want to compute a joint statistic over their combined patients without any hospital (or a coordinator) seeing the others' records.
- You want to outsource computation to an untrusted server without trusting it with your data.

**Secure computation** techniques close this window: they let computation happen *without* the computing party seeing the cleartext. Two main approaches do this very differently.

## Homomorphic encryption: math on ciphertext

**Homomorphic encryption (HE)** is the remarkable idea of performing computations *directly on encrypted data*, producing an encrypted result that, when decrypted, equals the result of doing the computation on the plaintext. The data goes in encrypted, is computed on while still encrypted, and comes out encrypted — the computing party never sees the cleartext at any point.

```
decrypt( compute( encrypt(a), encrypt(b) ) ) == compute(a, b)
```

The use case is clean: a client encrypts its sensitive input, sends the *ciphertext* to a server, the server runs a model (or any computation) on the ciphertext, and returns an encrypted result that only the client can decrypt. The server computed the answer *without ever seeing the input or the output*. For ML, this enables **private inference** — run a model on someone's encrypted medical data and return an encrypted diagnosis, with the model host learning nothing.

The catch is **performance**. "Fully homomorphic encryption" (supporting arbitrary computation) is extraordinarily expensive — orders of magnitude slower than computing on plaintext, sometimes by factors that make general use impractical. It has improved dramatically and is viable for *bounded* computations (simpler models, specific operations), and specialized/partial schemes are faster, but you can't naively run a large neural network under full HE at practical speed today. HE is the technique with the strongest "compute blind" guarantee and the steepest cost — so it fits narrow, high-value, latency-tolerant cases, not general ML workloads.

## Secure multi-party computation: split the secret

**Secure multi-party computation (SMPC / MPC)** attacks the same goal differently: it lets *multiple parties* jointly compute a function over their combined private inputs such that each party learns only the *result*, never the others' inputs. No single party ever holds the full data in the clear.

The intuition is **secret sharing**: a secret value is split into random "shares" distributed among the parties, where no individual share reveals anything about the secret, but the shares can be combined (through a cryptographic protocol) to compute on the underlying values. The parties run a protocol, exchanging messages, and arrive at the correct answer — with each having seen only meaningless shares, never the real inputs.

- **Use case:** several hospitals compute a joint model or statistic over their pooled patients where each hospital's records stay private even from the others and from any coordinator — the cross-silo collaboration of post 5, but with cryptographic (not just architectural) protection, so even the updates/intermediate values are hidden.
- **A key building block in federated learning:** **secure aggregation** (post 5) is an application of SMPC — the server combines participants' model updates such that it only ever sees the *sum*, never any individual update, closing federated learning's "leaky updates to the server" gap. This is SMPC's most common real deployment.
- **Trade-off:** SMPC's cost is primarily **communication** — the parties exchange many messages in rounds, so network latency and bandwidth dominate, and it needs multiple non-colluding parties. It's often more practical than full HE for the multi-party case and is genuinely deployed (secure aggregation at scale, private analytics), but it's still far heavier than plaintext computation.

## Where cryptographic privacy fits

These techniques are the **strongest** privacy tools — they protect data even during use, against even the party doing the computation — and also the **most expensive**, which precisely defines where they belong:

- **Use them when the computing party is untrusted and the data can't be exposed to it** — private inference on a cloud model (HE), cross-organization joint computation without mutual trust (SMPC), secure aggregation in federated learning (SMPC). The guarantee is cryptographic, not statistical or architectural.
- **Don't reach for them when a cheaper technique suffices** — if differential privacy (output privacy) or federated learning (don't centralize) solves your threat, they're far more practical. Cryptographic computation is for the specific gap where data must be *used* by someone who mustn't *see* it.
- **They compose with the rest** — the full privacy stack layers them: federated learning (don't centralize) + secure aggregation/SMPC (hide the updates) + differential privacy (bound what the final model reveals), each closing a different gap. No single technique is complete; the system is.

The honest summary: homomorphic encryption and secure multi-party computation are the most *complete* privacy guarantees available — computation on data that is never revealed — bought at a real and sometimes prohibitive performance price. They're advancing fast and already production-real in bounded, high-value settings (secure aggregation especially), and knowing they exist reframes what's possible: "the server shouldn't see this data" is not a dead end but a solved problem, if you can pay for it. They complete this series' toolkit as the techniques for the hardest case — protecting data not just at rest, not just in output, but *in use*.

The throughline: every earlier technique leaves data **exposed during computation** (you traditionally must see data to compute on it). **Secure computation** closes that window. **Homomorphic encryption** computes *directly on ciphertext* — data goes in encrypted, is computed on while encrypted, comes out encrypted (the server never sees cleartext) — enabling **private inference**, but **fully** homomorphic encryption is **orders of magnitude slower**, so it fits narrow, bounded, high-value cases. **Secure multi-party computation** lets multiple parties jointly compute over combined private inputs via **secret sharing**, each learning only the result — its flagship deployment is **secure aggregation** in federated learning (server sees only the summed updates), bounded mainly by **communication cost**. These are the **strongest and most expensive** privacy tools — protecting data *in use*, against the computing party itself — so use them when the computing party is untrusted and cheaper techniques don't suffice, and **compose** them with federated learning + differential privacy into a complete stack.

## Key takeaways

- Earlier techniques leave data **exposed during computation** (DP and federated learning both compute on cleartext somewhere); **secure computation** protects data *while it's being used*, against even the party doing the computing.
- **Homomorphic encryption (HE)** computes **directly on encrypted data**, yielding an encrypted result that decrypts to the correct answer — the computing party never sees cleartext — enabling **private inference** (run a model on someone's encrypted data, learn nothing); its catch is **extreme performance cost** (fully-HE is orders of magnitude slower), so it suits bounded, high-value, latency-tolerant cases.
- **Secure multi-party computation (SMPC)** lets multiple parties jointly compute over combined private inputs via **secret sharing** (split secrets into meaningless shares), each learning only the **result** — never others' inputs; bounded mainly by **communication cost** and needing non-colluding parties.
- SMPC's most common real deployment is **secure aggregation** (post 5): the server combines federated updates but sees only the **sum**, closing federated learning's leaky-updates gap — cryptographic protection for cross-silo collaboration.
- These are the **strongest but most expensive** privacy tools — use them when the **computing party is untrusted and data can't be exposed to it** and cheaper techniques (DP, federated learning) don't fit; they **compose** into a full stack (federated learning + SMPC/secure aggregation + differential privacy), each closing a different gap.

## Further reading

- [Homomorphic encryption — computing on encrypted data](https://en.wikipedia.org/wiki/Homomorphic_encryption)
- [Secure multi-party computation — joint computation on private inputs](https://en.wikipedia.org/wiki/Secure_multi-party_computation)
