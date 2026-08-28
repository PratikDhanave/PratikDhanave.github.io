# The Index: Git's Staging Area

*Every Git user meets the staging area on day one — `git add` puts things there, `git commit` takes them out — but almost nobody knows what it actually is. The index is a real file, a binary snapshot-in-progress that sits between your working directory and the object store. Understanding it turns `add`, `reset`, and the difference between "staged" and "modified" from memorized rules into a picture you can see.*

So far we have the object store (immutable snapshots) and refs (mutable pointers into them). But there's a third region Git manages constantly, one that explains the two-step `add`-then-commit dance: the **index**, also called the staging area or the cache. This post is about what it is and why it exists.

## Three trees

At any moment, Git is juggling three versions of your project — three "trees" in the loose sense:

- **HEAD** — the last commit. The snapshot of what you *last recorded*. This lives in the object store and is immutable.
- **The working directory** — the actual files on disk that your editor sees. This is the only region you touch directly; Git just watches it.
- **The index** — the *proposed next commit*. It holds a complete snapshot of what will be committed if you run `git commit` right now.

Most Git confusion comes from forgetting the index exists and imagining only two states (committed vs. not). There are three, and the index is the one in the middle. `git status` is really a report on the *differences* between these three: "Changes to be committed" is HEAD-vs-index; "Changes not staged for commit" is index-vs-working-directory.

## The index is a file

The index is not an abstraction — it is a concrete binary file at `.git/index`. It contains a sorted list of entries, one per tracked file, and each entry records the file's path, its mode, a set of timestamps and size, and — crucially — **the blob hash of the staged content**.

Read that last part again: when you stage a file, Git writes the file's content into the object store as a blob *immediately* and records that blob's hash in the index. Staging is not "marking a file for later." The content is hashed and stored the moment you `git add`. The index just remembers which blob represents each path in the pending commit.

You can see the index directly with the plumbing command `git ls-files --stage`:

```bash
$ git ls-files --stage
100644 a1b2c3d4... 0   README.md
100644 e5f6a7b8... 0   src/main.go
```

Mode, blob hash, stage number, path. That's the staging area — a flat list mapping paths to already-stored blobs. When you commit, Git turns this flat list into tree objects (one per directory), writes them to the object store, and creates a commit pointing at the root tree. **The index is the raw material a commit is built from.**

## Why `git add` after every edit

This clarifies a beginner's frequent surprise: you edit a file you already staged, and Git says it's *both* staged *and* modified. Now it makes sense. When you first `git add foo`, Git stored the then-current bytes as a blob and put that hash in the index. Your later edit changed the working-directory file but not the index entry. So:

- HEAD vs index differ → the file is "staged" (the earlier version).
- Index vs working directory differ → the file is also "modified" (the newer edit isn't staged).

`git add` again re-hashes the current content and updates the index entry to the new blob. The index always reflects a *specific snapshot*, frozen at the moment you last added — not a live view of your files. That's a feature: it lets you commit exactly the version you inspected, even if you keep typing.

## Staging is how you shape commits

Because the index is a separate, editable snapshot, you get precise control over *what* goes into each commit — independent of what you've changed on disk. This is the real payoff of a staging area, and it's why Git has one when simpler systems don't:

- **Partial commits.** You changed three unrelated things in one file; `git add -p` stages selected *hunks*, leaving the rest for a separate commit. The index holds a version that exists in neither HEAD nor your working tree — a deliberately curated snapshot.
- **Reviewing before recording.** `git diff` (no args) shows working-directory-vs-index — what you *haven't* staged yet. `git diff --staged` shows index-vs-HEAD — exactly what you're about to commit. Two different questions, two commands, because there are three trees.
- **Building a clean history.** The staging area lets you commit in logical units even when your working session was messy. You edit freely, then compose commits deliberately.

## Moving things between the three trees

Most of the commands people find slippery are just "move data between HEAD, index, and working directory." Seeing the target makes them obvious:

- `git add <file>` — copy working directory → index (stage).
- `git restore --staged <file>` (older: `git reset HEAD <file>`) — copy HEAD → index for that path, un-staging it. The working file is untouched; only the index entry reverts.
- `git restore <file>` (older: `git checkout -- <file>`) — copy index → working directory, discarding unstaged edits. This one *destroys* working changes, so it's the one to respect.
- `git reset --soft <commit>` — move the branch pointer only; leave index and working directory alone (your changes stay staged).
- `git reset --mixed <commit>` (the default) — move the branch and reset the index to match; working directory untouched (changes become unstaged).
- `git reset --hard <commit>` — move the branch, reset the index, *and* overwrite the working directory. This discards uncommitted work, which is why `--hard` deserves a pause.

The `--soft` / `--mixed` / `--hard` trio, which people often memorize as magic, is just *how far the reset reaches*: the branch pointer only, then the index too, then the working directory as well. Three trees, three depths.

## Key takeaways

- The **index (staging area / cache) is a real binary file** at `.git/index` that holds a complete snapshot of the *proposed next commit* — a flat, sorted list mapping each path to a blob hash and mode.
- Git manages **three trees**: HEAD (last commit, immutable), the index (proposed next commit), and the working directory (files on disk); `git status` and `git diff` are reports on the differences *between* them.
- **Staging stores content immediately** — `git add` hashes the file into the object store as a blob right away and records that hash in the index, so a later edit leaves a file both "staged" (old blob) and "modified" (new bytes) until you add again.
- The staging area exists to let you **shape commits deliberately** — partial (`add -p`) commits, reviewing `--staged` diffs, and composing clean history independent of your messy working state.
- `reset`'s **`--soft` / `--mixed` / `--hard`** modes simply choose how far a reset reaches — branch pointer only, then the index, then the working directory — so `--hard` is the only one that can destroy uncommitted work.

## Further reading

- [Pro Git — Git Tools: Reset Demystified](https://git-scm.com/book/en/v2/Git-Tools-Reset-Demystified)
- [Pro Git — Git Basics: Recording Changes to the Repository](https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository)
