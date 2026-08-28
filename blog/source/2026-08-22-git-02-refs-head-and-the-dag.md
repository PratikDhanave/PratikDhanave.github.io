# Refs, HEAD, and the Commit DAG

*If commits are content-addressed and immutable, how does anything ever move forward? The answer is refs: tiny mutable files, most of them containing nothing but a 40-character hash. A branch is not a copy of your work or a container for commits — it is a single sticky note pointing at one commit. Understanding that branches are pointers, and history is a graph, dissolves most of the confusion around Git.*

The previous post left us with a pile of immutable objects named by their hashes. That's a database, not a version-control system. What turns it into one is a thin layer of *mutable* pointers — refs — laid over the immutable object graph. This post is about that layer: branches, tags, HEAD, and the shape of history itself.

## A ref is just a name for a commit

Object hashes are perfect for machines and miserable for humans. Nobody wants to type `4b7a1f0e2c...` to check out yesterday's work. A **ref** (reference) solves this: it is a human-readable name that points to a commit hash. That's the whole idea.

Refs live as plain files under `.git/refs/`. A branch named `main` is literally the file `.git/refs/heads/main`, and its entire contents are one line — a hash:

```bash
$ cat .git/refs/heads/main
4b7a1f0e2c3d5a6b7c8d9e0f1a2b3c4d5e6f7a8b
```

That's it. A branch is a **41-byte file** (40 hex characters plus a newline). It is not a folder that holds commits, not a copy of your files, not a timeline. It is a single pointer to one commit. This is the most important sentence in this whole series, so it bears repeating: **a branch is a movable pointer to a commit.**

Tags live under `.git/refs/tags/`. A *lightweight* tag is exactly like a branch file — a name pointing at a commit — except Git never moves it automatically. An *annotated* tag points instead at a tag object (from the previous post), which in turn points at the commit. Branches move as you work; tags stay put. That difference in *mobility* is most of what distinguishes them.

## Why branching is instant

Because a branch is one small file, creating a branch means writing 41 bytes. That's why `git branch feature` is instantaneous even in a repository with a million commits — it copies a hash into a new file. Nothing is duplicated, nothing is scanned. Deleting a branch deletes that file (the commits it pointed to may become unreachable, but they aren't erased — more on that when we reach the reflog).

Compare this to systems where a "branch" is a directory copy on the server. Git's branches are cheap precisely because they are pointers, not containers. The commits exist once in the object store; branches are just different fingers pointing into the same graph.

## HEAD: the pointer to your current branch

If a branch points to a commit, what points to your *current* branch? That's **HEAD**. The file `.git/HEAD` almost always contains not a hash but a *symbolic reference* — a pointer to a pointer:

```bash
$ cat .git/HEAD
ref: refs/heads/main
```

HEAD says "you are currently on `main`." When you commit, Git creates the commit object, then updates whatever HEAD points to — here, `main` — to the new commit's hash. So the sequence is: **HEAD → current branch → current commit.** Committing advances the branch under HEAD; HEAD comes along for the ride because it points *at the branch*, not at the commit directly.

**Detached HEAD** is simply the case where `.git/HEAD` contains a raw hash instead of `ref: refs/heads/...`. You've checked out a commit directly, so HEAD points at a commit with no branch in between. It's not an error state — it's a perfectly valid configuration. The only risk is that commits you make there are pointed to by *nothing but HEAD*; move HEAD elsewhere and they can become unreachable. Create a branch before you leave, and they're anchored.

## History is a directed acyclic graph

Now zoom out. Each commit points to its parent(s). Follow those parent links and you trace history backward. This structure — nodes (commits) connected by parent edges — is a **directed acyclic graph (DAG)**:

- **Directed** — edges have a direction: child → parent. A commit knows its parents; a parent does not know its children. History only points backward, which is why "what came after this commit?" is a search, while "what came before?" is a walk.
- **Acyclic** — there are no loops. A commit's parent existed before it (its hash was known at creation), so you can never cycle back to yourself. Time only moves one way through the graph.
- **A graph, not a line** — a commit can have *multiple* parents (a merge commit has two or more), and multiple commits can share the *same* parent (two branches diverging). So history is a web of divergence and convergence, not a straight timeline.

```
        A---B---C   (main)
             \
              D---E   (feature)
```

Here `C` and `D` both have `B` as parent — the branch point. `main` points at `C`, `feature` at `E`. There is no third structure recording "the branches"; the branches *are* those two pointers, and the shape is implied entirely by the parent edges. Merging `feature` into `main` will create a new commit with two parents (`C` and `E`), stitching the fork back together — a convergence node in the DAG.

## Reachability is the organizing idea

Once you see history as a DAG with refs pointing into it, a single concept explains an enormous amount of Git's behavior: **reachability**. A commit is "reachable" if you can get to it by starting at some ref and walking parent edges. Reachable commits are your history; they're safe. Unreachable commits are candidates for garbage collection.

This reframes almost every Git operation as "move a pointer and change what's reachable." `git commit` extends a branch to a new tip. `git reset` moves a branch pointer to a different commit. `git merge` and `git rebase` create new commits and repoint a branch at them. `branch` and `tag` add new entry points into the graph. Nothing ever edits a commit in place — it can't; commits are immutable and content-addressed. Instead, **Git moves the cheap, mutable refs and lets reachability do the rest.**

## Key takeaways

- A **ref is a human-readable name pointing at a commit hash** — a branch is literally a ~41-byte file under `.git/refs/heads/` containing one hash, which is why branching is instant and free.
- **Branches move, tags stay** — both are pointers, but Git advances a branch as you commit while leaving tags fixed (lightweight tags point at a commit; annotated tags point at a tag object).
- **HEAD points to your current branch** (`ref: refs/heads/main`), so committing advances that branch; a **detached HEAD** just means HEAD holds a raw commit hash with no branch in between.
- History is a **directed acyclic graph** of commits linked by parent edges — directed (child→parent), acyclic (no cycles), and branching/merging (commits can have multiple parents and multiple children).
- **Reachability** — what you can reach by walking parents from some ref — is the unifying concept: nearly every Git command is "create objects and move a mutable ref," changing which commits are reachable rather than editing anything in place.

## Further reading

- [Pro Git — Git Internals: Git References](https://git-scm.com/book/en/v2/Git-Internals-Git-References)
- [Pro Git — Git Branching: Branches in a Nutshell](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell)
