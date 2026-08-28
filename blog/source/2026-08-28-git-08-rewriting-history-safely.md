# Rewriting History Safely

*Git lets you rewrite history — amend a commit, squash a messy branch, drop a secret that was committed by mistake. But "rewrite" is a misnomer: you never edit a commit, you replace it with a new one and move a pointer. Once you understand that, the rules for doing it safely become obvious, and the one genuine danger — rewriting history other people are building on — comes into sharp focus. This closing post turns the whole series into a working discipline.*

We've assembled the entire model: immutable content-addressed objects, mutable refs into a DAG, the index that builds commits, merge and rebase, packfiles, the reflog, and remotes. This final post applies all of it to the operation people find most nerve-wracking — changing history — and extracts the small set of rules that make it safe.

## You never edit a commit

Start from the bedrock fact of post 1: a commit is named by the hash of its content, so *its bytes can never change*. Every "history-rewriting" command therefore does the same thing under the hood: it **creates new commit objects and moves a ref to point at them**, abandoning the originals (which linger, unreachable, protected by the reflog and the gc grace period — posts 5 and 6).

- **`git commit --amend`** doesn't modify the last commit. It builds a *new* commit from the current index with a new hash — usually reusing the old commit's parent and message — and moves the branch to it. The original is now unreachable, recoverable from the reflog.
- **Interactive rebase** (`git rebase -i`) replays a range of commits, letting you reorder, edit, drop, or **squash** them. Every commit from the first changed one onward is recreated with a new hash (its parent changed, so its hash must — post 4).
- **History surgery** (`git filter-repo`, the modern replacement for the slow, error-prone `filter-branch`) rewrites *many* commits to purge a file or fix an email across all of history, producing an entirely new object graph.

In every case the pattern is identical: new objects, moved pointer, orphaned originals. "Rewriting history" is really "writing new history and re-aiming a ref."

## Why rewriting shared history hurts

If rewriting is just new-commits-and-a-pointer-move, why the dire warnings? Because of what it does to *other people's* repositories.

Suppose you and a teammate both have commit `D` on `feature`. You rebase, turning `D` into `D'` (new hash), and force-push. Now the remote's `feature` points at `D'`. But your teammate's local `feature` still points at `D`, and their reflog and in-progress work are built on `D`. When they next fetch, the histories **diverge**: their `D` and your `D'` are different commits with the same changes, and Git sees two lines of history. Their attempt to push or pull turns into confusing conflicts, duplicated commits, and — if they force-push back — a tug-of-war that can lose commits. You didn't just change your history; you invalidated the foundation everyone downstream was standing on.

This is the entire reason for the golden rule.

## The golden rule

> **Rewrite private history freely. Never rewrite shared history.**

Concretely: a commit is safe to rewrite as long as *no one else has based work on it* — which in practice means it hasn't left your machine, or lives only on a personal branch nobody else pulls. Rewriting is a *cleanup* tool for your own work *before* you share it:

- **Before pushing / opening a PR** — squash "wip", "fix typo", "actually fix it" into coherent commits; reorder; reword messages. This is local, private, and exactly what interactive rebase is for.
- **On `main`, release branches, or any branch teammates track** — never rewrite. Integrate with *new* commits instead: `git revert` creates a *new* commit that undoes a bad one, leaving history intact and safe for everyone. Revert is the "undo" for public history; reset/rebase are the "undo" for private history.

The one blurry case is a personal feature branch you've pushed for backup or review but that *no one else has pulled*. Rewriting it is fine — you just need to safely replace the remote copy, which is what `--force-with-lease` from the previous post is for: it republishes your rewritten branch but refuses to clobber commits you haven't seen. Use it instead of a bare `--force`, always.

## A practical workflow

Putting the series together, a safe rhythm for real work:

1. **Commit early and often, messily.** Uncommitted changes are the only thing with no object to recover (post 6), so get work into commits. Ugly history is fine — it's raw material.
2. **Keep your branch current with rebase.** `git fetch`, then rebase your feature branch onto the updated `origin/main` so it stays linear and conflicts surface in small batches — all while the branch is still private.
3. **Clean up before sharing.** Interactive-rebase your local commits into a readable sequence: squash noise, split unrelated changes, reword messages. This is your last chance to rewrite freely.
4. **Publish with `--force-with-lease`** if the cleanup rewrote already-pushed personal commits; otherwise a normal push fast-forwards.
5. **Integrate into shared branches with merges (or PR merges), never rewrites.** Once it's public, only *add* — merge to record integration, `revert` to undo. The shared history becomes append-only.
6. **When something goes wrong, reach for the reflog before panicking.** Almost every local mistake is one `git reflog` and one ref-move away from undone.

## The whole model, in one picture

Every command in this series reduces to two verbs: **create immutable objects** and **move mutable refs**. Commit creates a snapshot and advances a branch. Branch and tag add pointers. Merge and rebase create commits and re-aim a branch. Fetch and push move objects and update refs across repositories. Reset, amend, and rebase-i move refs to new or existing commits; the reflog remembers every such move so you can undo it. Nothing is ever edited in place, because content-addressing forbids it — and *that* single constraint is what gives Git its integrity, its cheap branching, its fearless recovery, and its clear rules for collaboration. Learn the objects and the pointers, and the hundred commands collapse into one coherent system you can reason about instead of memorize.

## Key takeaways

- **No command edits a commit** — content-addressing makes commits immutable, so amend, interactive rebase, and `filter-repo` all *create new objects and move a ref*, abandoning the originals (recoverable via the reflog until gc prunes them).
- Rewriting **shared** history is harmful because it makes everyone else's repository diverge from yours: their work is built on commits you replaced, producing duplicate commits, conflicts, and potential lost work.
- The **golden rule**: rewrite private history freely (squash, reorder, reword *before* sharing), but never rewrite history others track — undo public mistakes with **`git revert`** (a new, safe commit) instead of reset/rebase.
- For a **personal branch you've pushed but no one has pulled**, rewriting is fine — republish it with **`--force-with-lease`**, never a bare `--force`, so you can't clobber commits you haven't seen.
- The entire system reduces to **two operations — create immutable objects and move mutable refs** — so commit early (only uncommitted work is truly unrecoverable), rebase and clean up while private, integrate with merges when public, and trust the reflog to undo local mistakes.

## Further reading

- [Pro Git — Git Tools: Rewriting History](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History)
- [Pro Git — Git Branching: Rebasing (The Perils of Rebasing)](https://git-scm.com/book/en/v2/Git-Branching-Rebasing)
