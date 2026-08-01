# HD Wallets and Deposit Sweeping

*How a custodial exchange hands every user a unique deposit address from a single seed, then safely consolidates the funds into treasury.*

A custodial exchange has a deceptively simple job: let a user send crypto to "their" address, notice it arrived, credit their balance, and move the money somewhere safe. Every word in that sentence hides an engineering decision. Where do the addresses come from? How many can you afford to make? When is a deposit real enough to credit? And how do you drain thousands of little addresses into cold storage without leaking keys or burning a fortune in fees? This post walks the full path, from key derivation to the final sweep.

## One seed, many addresses

The naive approach is to generate a fresh random keypair per user and store every private key in a database. That is an operational nightmare: your key material grows without bound, backups must capture every new key the instant it is created, and losing the database loses the funds.

Hierarchical-deterministic (HD) wallets solve this. The BIP-39 standard turns a single high-entropy secret into a human-transcribable mnemonic (the *seed*). BIP-32 then defines *child key derivation*: from one parent key you can deterministically compute a practically unlimited tree of child keys. BIP-44 gives that tree a meaningful shape with a five-level path:

```
m / purpose' / coin_type' / account' / change / index
m /    44'   /     60'    /    0'    /   0    /  1024
```

The trailing `index` is the lever we care about. User 1024 gets `.../0/1024`, user 1025 gets `.../0/1025`, and so on. To assign an address you increment a counter and derive; you never generate or store a new private key at deposit time. The whole address space is a pure function of `(seed, path)`.

The security payoff comes from *extended public keys* (xpubs). BIP-32 lets you derive all the public keys (and therefore all the receiving addresses) of a non-hardened branch from the xpub alone, without the private keys. So the hot deposit service holds only the account-level xpub. It can mint addresses all day, but it cannot spend a single satoshi. The seed and the private keys stay in an HSM or cold vault, brought online only to sign sweeps. A read-only breach of the deposit service leaks addresses, not money.

## Deriving addresses at scale

Per-user derivation looks cheap, but at scale the details bite. Two rules keep it sane. First, the `index` must be allocated atomically. Two concurrent signups that both read counter `N` and both derive `.../0/N` will hand two users the same address and merge their funds. Wrap allocation in a database sequence or a transactional `UPDATE ... RETURNING`. Second, persist the derived address and its path together the moment you allocate, so detection and later signing can map an incoming transaction back to the exact derivation path deterministically.

Watching is the other scaling axis. You are not watching one address; you are watching every address you have ever handed out. On UTXO chains you can register the whole address set with a full node's wallet or scan blocks against a bloom/compact filter. On account-based chains you subscribe to logs or poll balances for the address set. Either way, the watcher's working set is "all deposit addresses," which is why you keep them in a fast, indexed store keyed by address.

```
   SEED (cold)                          BLOCKCHAIN
      |  BIP-32/39/44                        |
      v  m/44'/coin'/acct'/0/i               |
  [ Derive addr ] --addr--> [ User deposits ]|
      ^ xpub only                            |
      |                                       v
      |                            [ Watcher: scan address set ]
      |                                       |  tx seen
      |                                       v
      |                            [ Confirm: wait N blocks ]
      |                              |                    |
      |                     final   |                    | needs gas
      |                             v                    v
      |                    [ Credit balance ]   [ Gas-fund address ]
      |                             |                    |
      |                             +-----> [ Sweep ] <--+
      |                                     batched, signed
      +-------------------------------------> COLD / TREASURY
```

> **▸ [Open the interactive diagram](/blog/diagrams/fintech-hd-wallet-deposit-sweeping.html)** — the deposit lifecycle from per-user derivation through confirmation, crediting, and a gas-funded batched sweep to cold storage.

## Detecting and confirming a deposit

Seeing a transaction in the mempool is a hint, not an event you can act on. Two hard rules govern crediting.

The first is *confirmation depth*. Blockchains reorganize: a block that looked final can be orphaned, and with it your "deposit." You credit only after the transaction is buried under `N` blocks, where `N` is tuned per chain to its reorg risk and block time. A high-value deposit may warrant a deeper wait than a small one. Getting this wrong is how exchanges get drained by double-spends: credit on zero confirmations, let the user withdraw, then watch the deposit vanish in a reorg.

The second is *idempotency*. The same transaction will be reported many times as it gains confirmations, and your watcher may restart mid-stream and reprocess a block. Key every credit on the on-chain transaction identifier (and output index, on UTXO chains) with a uniqueness constraint, so replaying an event can never double-credit. The crediting itself should be a double-entry ledger move: debit a "pending deposits" account, credit the user, so balances always reconcile against on-chain reality.

## Sweeping to treasury

Now the funds sit across thousands of per-user addresses. Leaving them there is a liability: each address holds a live balance protected by a key that must, at some point, come online to move it. Sweeping consolidates those balances into a small number of cold or treasury wallets.

The engineering problem is *batching*. Sweeping each address in its own transaction is simple and catastrophically expensive. On UTXO chains you instead build one transaction that spends many deposit outputs into a single treasury output, amortizing the per-transaction overhead and shrinking the fee. You batch on a schedule or a threshold (sweep when aggregate idle balance crosses some limit), balancing fee efficiency against how long value sits exposed. Signing happens in the secure boundary: the sweep service proposes the batch, the HSM or offline signer derives the needed private keys from the seed by path and signs.

Account-based chains add a wrinkle that surprises people the first time: **you cannot move a token without paying gas in the chain's native coin, and the deposit address holds only the token.** A user's address might hold a stablecoin balance but zero native coin, so there is nothing to pay the sweep's gas with. The fix is a gas-funding step: a treasury-controlled "fee" wallet first sends a small amount of native coin to the deposit address, and only then can the sweep transaction from that address broadcast. This is a branch off the main path, not the main path itself, and it costs real money, so you fund the exact estimated gas, sweep, and avoid stranding dust.

## Putting it together

The whole pipeline is a small set of invariants worth stating plainly. Addresses are a deterministic function of a cold seed, so the hot path never touches spendable keys. Indices are allocated atomically, so no two users ever collide. A deposit is only money after `N` confirmations, and it is credited exactly once. Sweeps are batched for fee efficiency, signed inside the secure boundary, and, on account chains, gas-funded before they can move. None of these pieces is individually hard. The discipline is in never letting a shortcut, an off-by-one index, a zero-confirmation credit, or an un-funded sweep, turn a routine deposit into a loss.
