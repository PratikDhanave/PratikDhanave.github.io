# The Reflog: Git's Safety Net

*"I lost my commits" is almost never true. A bad reset, a botched rebase, a deleted branch — the commits are usually still there, sitting unreachable in the object store, waiting out their grace period before garbage collection. The reflog is the log of everywhere your refs have been, and it's the tool that turns "I destroyed my work" into a thirty-second recovery. Knowing it exists changes how fearlessly you can use Git.*

By now we can explain what most commands *do*: they create objects and move refs, changing reachability. That power to move refs is also the power to *lose* things — point a branch somewhere else and its old commits may become unreachable. This post is about the mechanism that makes that reversible, and why "lost" in Git rarely means "gone."

## Unreachable is not deleted

Recall two facts from earlier posts. First, commits are immutable content-addressed objects — nothing edits them in place. Second, `git gc` only removes objects that are *both* unreachable *and* past a grace period. Put those together and a reassuring conclusion falls out: **when an operation "loses" commits, it doesn't delete them — it just stops any ref from pointing at them.**

A `git reset --hard HEAD~3` doesn't erase three commits. It moves your branch pointer back three commits. The three you "removed" still exist as objects; they're simply no longer reachable by walking parents from any branch. They sit in `.git/objects`, intact, until `gc` eventually prunes them — which, by default, won't happen for about two weeks, and not while the reflog still references them. The window to recover is wide, and the reflog is how you find the way back in.

## What the reflog records

Every time a ref's value changes, Git appends a line to that ref's **reflog** — a local log under `.git/logs/`. There's one for HEAD (`.git/logs/HEAD`) and one per branch (`.git/logs/refs/heads/main`). Each entry records the *old* hash, the *new* hash, who changed it, when, and a short description of the operation:

```bash
$ git reflog
e5f6a7b (HEAD -> main) HEAD@{0}: reset: moving to HEAD~3
1a2b3c4 HEAD@{1}: commit: add retry backoff
9d8e7f6 HEAD@{2}: commit: parse config
b4c5d6e HEAD@{3}: rebase finished: returning to refs/heads/main
```

The syntax `HEAD@{n}` means "where HEAD pointed *n* moves ago." `HEAD@{1}` is where it was before the most recent change; you can also use time expressions like `HEAD@{yesterday}`. This is fundamentally different from `git log`. **`git log` walks the commit DAG via parent edges** — it shows ancestry. **`git reflog` is a chronological journal of pointer movements** — it shows *where your refs have been*, including commits that are now unreachable and would never appear in `log`. When a commit has fallen off the graph, the reflog is often the only remaining name for it.

## Recovering lost work

The recovery pattern is always the same: find the lost commit's hash in the reflog, then point a ref at it to make it reachable again.

**Undoing a bad reset.** You ran `git reset --hard HEAD~3` and want it back:

```bash
$ git reflog                       # find the pre-reset tip
1a2b3c4 HEAD@{1}: commit: add retry backoff
$ git reset --hard HEAD@{1}        # move the branch back to it
```

The branch pointer returns to `1a2b3c4`, and the three commits are reachable — and therefore safe — once more.

**Recovering a deleted branch.** Deleting a branch removes the ref file, but HEAD's reflog still holds the commits you made on it:

```bash
$ git reflog                       # locate the branch's last tip
7f8a9b0 HEAD@{5}: commit: feature work
$ git branch recovered 7f8a9b0     # re-anchor it with a new branch
```

**Rescuing a botched rebase.** A rebase rewrites commits (post 4) and abandons the originals — but the reflog recorded where the branch was *before* the rebase started. `git reset --hard HEAD@{...}` at that pre-rebase entry restores the original commits exactly.

In every case you're doing the same thing: the object is alive but unreferenced; the reflog gives you its hash; you attach a ref and reachability makes it permanent again.

## The reflog is local and expiring

Two properties are worth internalizing so you neither over-trust nor under-trust it:

- **The reflog is local and per-clone.** It records *your* ref movements in *this* repository. It is never pushed or fetched — a fresh clone has an empty reflog. So the reflog can rescue *your* local mistakes, but it won't help a teammate recover what you rewrote, and it won't survive re-cloning. It is a personal undo history, not shared history.
- **Reflog entries expire.** By default, reachable-from-reflog entries are kept ~90 days and unreachable ones ~30 days, after which they're eligible for expiry and their objects for pruning. The safety net is wide but not infinite: recover promptly rather than assuming a months-old mistake is still retrievable.

## Why this changes how you work

The deepest lesson of the reflog is psychological. Beginners treat Git operations as irreversible and approach `reset`, `rebase`, and branch deletion with dread. But given the object model — immutable objects, reachability-based collection, a grace period, and a journal of every ref movement — **almost every local operation is reversible.** The commits you're afraid of losing are one `git reflog` away from being found.

This is why experienced engineers use Git's sharper tools without fear: they know the floor is padded. `reset --hard`, interactive rebase, history surgery — all become routine once you trust that the reflog remembers where you were. The one genuine way to lose work is to operate on content you *never committed at all* (uncommitted working-directory changes have no object, so there's nothing to recover) — which is the best argument for committing early and often. Everything you've committed, the reflog can find.

## Key takeaways

- Operations that seem to delete commits (`reset --hard`, rebase, branch deletion) only make them **unreachable, not deleted** — the immutable objects persist until `gc` prunes them after a grace period, so there's a wide window to recover.
- The **reflog** (`.git/logs/`) is a local, chronological journal of every change to a ref's value — old hash, new hash, and operation — addressable as `HEAD@{n}` ("where HEAD was n moves ago").
- **`git log` shows ancestry** by walking parent edges, while **`git reflog` shows pointer history** — including now-unreachable commits that `log` can't see, which is exactly what you need to recover.
- Recovery is always the same move: **find the lost hash in the reflog, then attach a ref to it** (`git reset --hard HEAD@{1}`, `git branch recovered <hash>`), restoring reachability.
- The reflog is **local, per-clone, and expiring** (~90 days reachable / ~30 unreachable) — it rescues your own recent mistakes but isn't shared and won't help with work you never committed, so commit early and often.

## Further reading

- [git reflog — reference documentation](https://git-scm.com/docs/git-reflog)
- [Pro Git — Git Internals: Maintenance and Data Recovery](https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery)
