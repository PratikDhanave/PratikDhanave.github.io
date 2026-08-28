# Packfiles and How Git Stays Small

*A snapshot-per-commit model sounds like it should balloon a repository to enormous size. It doesn't — a project with a decade of history often clones smaller than a single day's build artifacts. The trick is packfiles: Git periodically takes its loose objects, deltas the similar ones against each other, and compresses the result. This is where "Git stores snapshots" and "Git repositories are tiny" stop seeming contradictory.*

We said in the first post that every commit records a full snapshot, and that content-addressing keeps this cheap by sharing identical objects. That's true, but it only deduplicates *identical* content. What about a file edited a thousand times — a thousand *similar but distinct* blobs? Storing each in full would be wasteful. Packfiles are how Git solves the remaining problem.

## Loose objects vs. packed objects

When you make a commit, Git writes each new object as a **loose object**: one file per object under `.git/objects/`, its content zlib-compressed, named by its hash (the first two hex characters become a directory, the rest the filename):

```
.git/objects/a1/b2c3d4e5f6...
```

Loose objects are simple and fast to write — perfect for the moment of committing. But they have two costs at scale. Each is compressed *in isolation*, so a file and its slightly-edited successor are two separately-compressed full copies with no sharing between them. And thousands of tiny files stress the filesystem. Loose storage is a good *write* format and a poor *long-term* format.

## The delta idea

The insight behind packfiles: **similar objects can be stored as differences from one another.** If blob B is a small edit of blob A, Git can store A in full and store B as "take A, then apply these changes" — a *delta*. The delta is tiny compared to a full copy of B.

This is different from the snapshot-vs-diff distinction of post 1. Conceptually, every commit still references a *complete* tree — the *object model* is snapshots. Packfiles are a *storage-layer* optimization underneath that model: they choose, invisibly, to physically store some objects as deltas against others. The logical model (snapshots, content-addressed) is unchanged; only the bytes on disk get cleverer. You never see deltas in `git cat-file`; Git reconstructs the full object on demand.

Two subtleties make it work well:
- **Deltas can chain.** B is a delta of A, C is a delta of B, and so on — a *delta chain*. Git bounds the chain length so reconstruction doesn't require walking hundreds of steps.
- **Deltas point newest-to-oldest, by size.** Git generally stores the *larger* (usually newer) object in full and deltas the smaller against it, and it delta-compresses in the direction that keeps recent history fast to access.

## The packfile

Git bundles many objects into a single **packfile** — `.git/objects/pack/pack-<hash>.pack` — with a companion **index** file `pack-<hash>.idx`. The pack holds the objects (many as deltas, then everything zlib-compressed on top); the `.idx` is a lookup table mapping each object's hash to its byte offset in the pack, so Git can find any object without scanning.

To find an object, Git checks loose storage, then consults each pack's `.idx`. To *read* a packed object, it seeks to the offset and, if the object is a delta, walks its base chain applying deltas until it has the full content. All of this is invisible: `git show`, `git log`, `git checkout` reconstruct whole objects transparently. The packfile is purely a storage representation.

## When packing happens: gc

You don't pack manually. Git runs **`git gc`** ("garbage collect") automatically when loose objects accumulate — after commits, merges, and especially after a fetch. `gc` does two related jobs:

- **Packing.** It gathers loose objects, finds good delta pairings (comparing objects of similar type and size to pick effective bases), builds a packfile, and removes the now-redundant loose objects. Repacking can also consolidate several existing packs into one.
- **Pruning.** It removes objects that are both *unreachable* (post 2: not reachable by walking parents from any ref) *and* older than a grace period (default two weeks, and still protected by the reflog — the subject of the next post). This is when the abandoned originals from a rebase or an amended commit are finally deleted.

The two-week grace period and reflog protection are deliberate: they give you a window to recover "lost" commits before `gc` truly erases them. Reachability decides what's *kept*; the grace period decides *when* the unreachable is swept.

## Why clones are small and fast

Packfiles aren't just local housekeeping — they're also the *transfer* format. When you clone or fetch, the server doesn't send thousands of loose objects; it builds a packfile of exactly the objects you need and streams that. This means:

- **Delta compression across all of history** — a file's thousand revisions travel as one full copy plus 999 small deltas, not a thousand copies. This is why a long-lived repository clones far smaller than the sum of its historical file sizes.
- **One stream, not thousands of round-trips** — the pack is negotiated (the client and server agree on what the client already has, so only missing objects are packed) and sent as a single compressed stream.

So the apparent paradox — "Git keeps a full snapshot per commit" yet "Git repos are small and clone fast" — resolves cleanly. The *model* is snapshots for conceptual simplicity and integrity; the *storage and transport* are delta-compressed packfiles for efficiency. Two layers, each optimized for its job, and the seam between them is invisible in daily use.

## Key takeaways

- New objects are first written as **loose objects** (one compressed file each under `.git/objects/`) — fast to write, but each compressed in isolation with no sharing between similar versions.
- **Packfiles** store many objects together, representing similar objects as **deltas** (differences) against one another and zlib-compressing the whole, so a file's many revisions cost one full copy plus small deltas.
- Packfiles are a **storage-layer optimization**, not a change to the object model: commits still reference complete snapshots; Git reconstructs full objects from delta chains transparently, guided by the `.idx` hash→offset lookup.
- **`git gc`** runs automatically to pack loose objects and to **prune** objects that are both unreachable *and* past a grace period (default ~2 weeks, still reflog-protected) — which is when abandoned rebase/amend originals are finally removed.
- Packfiles are also the **transfer format**: clone and fetch send a single delta-compressed, negotiated packfile, which is why decade-long histories clone small and fast despite the snapshot model.

## Further reading

- [Pro Git — Git Internals: Packfiles](https://git-scm.com/book/en/v2/Git-Internals-Packfiles)
- [Pro Git — Git Internals: Maintenance and Data Recovery](https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery)
