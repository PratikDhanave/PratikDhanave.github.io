# Merge and Rebase, Demystified

*Merge and rebase are where Git's DAG earns its keep — and where most fear lives. Both integrate one line of work into another; they differ only in the shape of history they leave behind. Merge preserves the fork and records a convergence; rebase rewrites your commits as if you'd started later, producing a straight line. Neither is magic. Once you know what a merge base is, both become predictable.*

We have commits (immutable snapshots), refs (movable pointers), and the index (the staging area that builds commits). Now we combine lines of work. Integration is the operation people most want to understand and most fear breaking. This post takes merge and rebase down to their mechanics.

## The merge base

Both merge and rebase start by finding one thing: the **merge base** — the most recent commit reachable from *both* branch tips. It's the point where the two lines of history diverged, the fork in the DAG.

```
        A---B---C   (main)
             \
              D---E   (feature)
```

Here `B` is the merge base of `main` and `feature`: the newest commit that's an ancestor of both `C` and `E`. Git finds it by walking parent edges from both tips until it meets. Everything after `B` on each side is what needs reconciling. Get this concept and the rest follows — merge and rebase are just two strategies for combining "what `main` did since `B`" with "what `feature` did since `B`."

## Fast-forward: the trivial case

Sometimes there's nothing to reconcile. If you branched `feature` off `main` and `main` hasn't moved since, then `main`'s tip *is* the merge base — `feature` is simply ahead:

```
   A---B   (main)
        \
         D---E   (feature)
```

Merging `feature` into `main` here doesn't need a new commit. Git just slides the `main` pointer forward to `E`. This is a **fast-forward merge** — no merge commit, no reconciliation, just a pointer move (remember, moving refs is nearly all Git ever does). History stays linear because it never actually diverged. `git merge --no-ff` forces a merge commit anyway when you want the branch to be visible in history.

## Three-way merge

The interesting case is real divergence — both branches advanced past the base, as in the first diagram. Git performs a **three-way merge**, using three inputs: the merge base (`B`), your branch tip (`C`), and their branch tip (`E`).

For each file, Git compares the base version against both sides:

- Changed on **one** side only → take that change. No conflict; the intent is unambiguous.
- Changed on **both** sides *identically* → take it once.
- Changed on **both** sides *differently* → **conflict**. Git can't know which you meant, so it stops and asks.

When there's no conflict, Git builds a new **merge commit** with *two* parents (`C` and `E`) — a convergence node stitching the fork back together. Its tree is the reconciled result. History now records, truthfully, that two lines existed and were joined. The modern default strategy is called *ort* (it replaced the older *recursive* strategy); both handle the subtle case where the two branches have more than one merge base by merging the bases first.

## Conflicts are a question, not a failure

A conflict is not Git breaking. It's Git refusing to guess. When both sides changed the same region differently, Git writes both versions into the file with markers and pauses:

```
<<<<<<< HEAD
timeout := 30 * time.Second
=======
timeout := 10 * time.Second
>>>>>>> feature
```

Your job is to decide the correct result, remove the markers, and stage the resolved file (`git add`) — recording, in the index, the blob you want for that path. Then `git commit` (or `git merge --continue`) completes the merge commit. The conflict lived entirely in the index and working directory; once you stage a resolution, the three-way merge proceeds as normal. Nothing was corrupted, and `git merge --abort` returns you to exactly where you started.

## Rebase: replaying commits

Rebase reaches the same goal — `feature` incorporating `main`'s progress — by a different route. Instead of joining the branches with a merge commit, it **replays your commits on top of the other branch**, as if you had started from there.

Rebasing `feature` onto `main`:

```
before:                    after:
  A---B---C  (main)          A---B---C        (main)
       \                              \
        D---E  (feature)               D'---E'  (feature)
```

Git takes each commit unique to `feature` (`D`, `E`), computes its diff, and re-applies it on top of `main`'s tip `C`, creating **new commits** `D'` and `E'`. The result is a straight line: `main`'s history followed by your work, with no fork visible.

The critical word is *new*. `D'` is not `D`. It has a different parent (`C` instead of `B`), and since a commit's hash depends on its parent, `D'` has a **different hash**. Rebase does not move commits — it *rewrites* them, creating fresh objects and abandoning the originals (which linger, unreachable, until garbage collection). This is why rebase belongs to the family of history-rewriting operations we'll examine in a later post, and why it's dangerous on shared branches: anyone who has the old `D` and `E` now disagrees with you about what `feature` is.

## Choosing between them

They produce the same *files* and differ only in the *history* they leave:

- **Merge** preserves the true shape: it records that two lines existed and converged, keeping every original commit unchanged. History is accurate but bushier — merge commits accumulate. Safe on shared branches because it never rewrites existing commits.
- **Rebase** produces a clean, linear history that's easy to read and bisect, at the cost of *rewriting* commits (new hashes). Ideal for tidying up *your own local* work before sharing; hazardous on branches others have pulled.

A common workflow captures both: **rebase your local feature branch** to keep it current and clean while you work, then **merge it** (often `--no-ff`) into the shared branch so the integration is recorded once. The rule of thumb that prevents disasters: *rebase private history, merge public history.* We'll make that rule precise when we cover force-pushing safely.

## Key takeaways

- Both merge and rebase begin by finding the **merge base** — the most recent common ancestor of the two branch tips — which marks where history diverged; everything after it on each side is what gets reconciled.
- A **fast-forward** merge happens when one branch hasn't moved since the fork: Git just slides the pointer forward, leaving linear history and no merge commit (`--no-ff` forces one).
- A **three-way merge** compares the base against both tips per file, auto-resolving changes made on only one side and creating a **merge commit with two parents**; it stops with a **conflict** only when both sides changed the same region differently.
- A **conflict is Git asking you to decide** — you edit the marked region, stage the resolution into the index, and continue; `git merge --abort` safely undoes everything.
- **Rebase replays your commits as new objects** on top of another branch, producing linear history but **different hashes** — so it rewrites history and must be reserved for private, unshared work; merge preserves and is safe for shared branches.

## Further reading

- [Pro Git — Git Branching: Rebasing](https://git-scm.com/book/en/v2/Git-Branching-Rebasing)
- [Pro Git — Git Branching: Basic Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging)
