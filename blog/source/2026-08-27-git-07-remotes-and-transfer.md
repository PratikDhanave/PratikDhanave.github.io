# Remotes, Refspecs, and How Fetch and Push Work

*Collaboration in Git is the same object model, stretched across two repositories. A remote is just a named URL; a remote-tracking branch is just a local pointer that remembers where the other side was; fetch and push are just object transfers plus ref updates, governed by a small syntax called the refspec. Nothing new is invented for the network — it's the graph and the pointers, reaching across a wire.*

Everything so far has been about one repository. But Git is distributed: every clone is a full repository, with the complete object graph and its own refs. Collaboration is how two such repositories exchange objects and reconcile pointers. This post shows that "the network" adds almost no new concepts — it's the same objects and refs, moved between repos.

## A remote is a named URL

A **remote** is nothing but a saved name for another repository's location. `origin` is a convention, not a keyword — the default name Git gives the repository you cloned from. It maps to a URL (HTTPS or SSH) plus a rule for how its branches map into yours:

```bash
$ git remote -v
origin  git@github.com:you/project.git (fetch)
origin  git@github.com:you/project.git (push)
```

That configuration lives in `.git/config`. A remote holds no objects locally by itself; it's an address plus a mapping. The objects arrive when you fetch.

## Remote-tracking branches

When you clone, Git copies the other repo's objects and creates a special kind of ref for each of its branches: a **remote-tracking branch**, named `origin/main`, `origin/feature`, and so on. These live under `.git/refs/remotes/` and follow one rule: **they are your local record of where the remote's branches were the last time you talked to it.**

This is the key distinction people blur. `main` is *your* branch — you commit to it, it moves when you work. `origin/main` is a **read-only snapshot of the remote's `main` as of your last fetch** — you never commit to it; only fetching updates it. It's a cache, a bookmark of the other side's state. The gap between `main` and `origin/main` is precisely "what I've done that they haven't seen" versus "what they've done that I haven't pulled" — and that gap is what `git status` reports as *ahead* and *behind*.

## Refspecs: the mapping rule

How does Git know that the remote's `main` becomes your `origin/main`? A **refspec** — the small mapping syntax that governs all transfer. The default fetch refspec, written in `.git/config`, is:

```
+refs/heads/*:refs/remotes/origin/*
```

Read it as `<source>:<destination>`: "take every branch under `refs/heads/*` on the remote and write it to `refs/remotes/origin/*` locally." The leading `+` means "update even if it's not a fast-forward" — safe here because remote-tracking branches are just a mirror of the other side, so forcing them to match is correct. Refspecs are also what let you push a local branch to a differently-named remote branch (`git push origin local:remote`), or fetch just one branch. Most of the time the defaults are invisible; knowing they exist explains *why* fetch lands where it does.

## Fetch: download objects, move tracking refs

`git fetch` is deliberately conservative and does exactly two things:

1. **Negotiate and transfer objects.** Git and the remote compare what each has — the client says which commits it already holds, the server computes the missing objects and sends them as a single delta-compressed **packfile** (post 5). Only objects you lack cross the wire.
2. **Update remote-tracking branches.** Per the refspec, Git advances `origin/*` to match the remote's current branch tips.

What fetch does *not* do is touch *your* branches or your working directory. After a fetch, `origin/main` may have moved forward but your `main` is exactly where you left it. Your work is never disturbed by downloading. This is why fetch is always safe to run — it's pure information-gathering.

**Pull is fetch plus integrate.** `git pull` is a convenience: fetch, then merge (or, with `--rebase`, rebase) `origin/main` into your `main`. Because the second step modifies your branch and can conflict, `pull` is exactly as risky as the merge or rebase it performs — while `fetch` alone never is. Fetching first and looking before you integrate is often the calmer habit.

## Push: upload objects, ask the remote to move a ref

`git push` is fetch's mirror image, and it carries one crucial safety rule:

1. **Transfer objects the remote lacks** — the same negotiation and packfile, in the other direction.
2. **Ask the remote to update its branch** to your commit — *but only if it's a fast-forward.*

That last condition is the guardrail. Git refuses a push that would make the remote branch lose commits — i.e., where the remote's tip is *not* an ancestor of what you're pushing. This is the familiar rejection:

```
 ! [rejected]  main -> main (non-fast-forward)
```

It means: someone pushed commits you don't have, so accepting yours would orphan theirs. The remote protects its history by requiring your push to *extend* its branch, not replace it. The correct response is to `git fetch`, integrate their work (merge or rebase onto the updated `origin/main`), and push the reconciled result — which now *does* fast-forward.

## Force-push and its safe form

Sometimes you *intend* to replace the remote branch — typically after rebasing your own feature branch (post 4), which rewrote commits and so can't fast-forward. `git push --force` overrides the check. But a blunt `--force` will happily overwrite commits a teammate pushed in the meantime — the same orphaning the guardrail existed to prevent.

The disciplined tool is **`git push --force-with-lease`**. It force-pushes *only if* the remote branch is still where you last saw it (your `origin/main` matches the real remote `main`). If someone else pushed since your last fetch, the lease is broken and the push is refused — so you overwrite *your own* rewritten history without clobbering work you never saw. This is the precise, safe expression of "rebase private history, merge public history": force-with-lease lets you republish a rebased *personal* branch while refusing to trample a *shared* one. We'll build the full rule for rewriting shared history in the final post.

## Key takeaways

- A **remote is just a named URL** (`origin` is a convention) plus a mapping rule; it holds no objects itself until you fetch.
- **Remote-tracking branches** (`origin/main`) are your local, read-only record of where the remote's branches were at your last fetch — a cache you never commit to; the gap between `main` and `origin/main` is exactly your "ahead/behind."
- A **refspec** (`+refs/heads/*:refs/remotes/origin/*`) is the source:destination mapping that governs transfer, explaining where fetched branches land and enabling custom push/fetch mappings.
- **`git fetch`** only downloads missing objects (as a negotiated packfile) and advances `origin/*` — it never touches your branches or working tree, so it's always safe; **`git pull`** adds a merge/rebase and inherits that step's risk.
- **`git push`** uploads objects and asks the remote to update its branch, but **only if fast-forward** — a non-fast-forward rejection means fetch-and-integrate first; when you truly must rewrite a shared ref, use **`--force-with-lease`**, which refuses to clobber commits you haven't seen.

## Further reading

- [Pro Git — Git Internals: The Refspec](https://git-scm.com/book/en/v2/Git-Internals-The-Refspec)
- [Pro Git — Git Branching: Remote Branches](https://git-scm.com/book/en/v2/Git-Branching-Remote-Branches)
