# The Git Object Model

*Git looks like a tool for tracking changes, but underneath it is something simpler and stranger: a small content-addressed key-value store. Four object types — blob, tree, commit, tag — are all it keeps, each named by the hash of its own bytes. Once you see that everything else (branches, history, staging) is a thin layer over these four objects, Git stops being a bag of memorized commands and becomes a system you can reason about.*

Most people learn Git as a list of incantations: `add`, `commit`, `push`, and a prayer before every `rebase`. That works until it doesn't — until a detached HEAD, a lost commit, or a mangled merge sends you to Stack Overflow to copy a command you don't understand. This series takes the other road. We start at the bottom, with the storage model, and build up. By the end, the porcelain commands you type every day will read as obvious consequences of a design you can hold in your head.

## Git is a content-addressed store

At its core, Git is a key-value database where **the key is the hash of the value**. You hand Git some bytes; it computes a hash of those bytes, stores them under that hash, and hands the hash back. Give it the same bytes again and you get the same key — so identical content is stored exactly once, no matter how many files or commits reference it.

Historically that hash is SHA-1 (a 40-character hex string); newer repositories can use SHA-256. The choice matters for security, not for the mental model. What matters is the consequence: **an object's name is derived from its content**, so you cannot change an object's bytes without changing its name. This one property is where Git's integrity comes from — tamper with any byte anywhere in history and every hash from that point forward no longer matches.

You can watch this happen with Git's low-level *plumbing* commands (as opposed to the *porcelain* commands like `commit` that humans use):

```bash
$ echo 'hello' | git hash-object --stdin
ce013625030ba8dba906f756967f9e9ca394464a
```

That hash is not random and not a timestamp — it is a function of the bytes `hello\n` plus a small header. Anyone, anywhere, hashing the same content gets the same 40 characters. That is what "content-addressed" means.

## The four object types

Everything Git stores is one of four object types. Each is just a header (`<type> <size>\0`) followed by content, zlib-compressed, and written to `.git/objects/` under its hash.

- **Blob** — the contents of a file, and *only* the contents. A blob has no name, no path, no permissions, no timestamp. Two files with identical bytes — in different directories, in different commits, ten years apart — are the *same* blob, stored once. The blob doesn't know it's called `README.md`; that knowledge lives elsewhere.
- **Tree** — a directory. A tree is a list of entries, each pairing a *mode* (file permissions, or "this entry is a subtree"), a *name* (`README.md`, `src`), and the *hash* of the object it points to (a blob for a file, another tree for a subdirectory). Trees are how Git records structure: filenames, layout, and the shape of your project at one moment.
- **Commit** — a snapshot plus context. A commit points to *one* tree (the complete state of the project at that moment), to zero or more *parent* commits, and carries the author, committer, timestamp, and message. Crucially, a commit references a whole tree, not a diff.
- **Tag** — an annotated tag object: a pointer to another object (usually a commit) with its own message and, optionally, a cryptographic signature. This is the heavyweight tag; lightweight tags are just refs, which we'll meet in the next post.

Four types. That's the entire vocabulary. A repository's whole history is a graph of these objects pointing at each other by hash.

## Snapshots, not diffs

Here is the idea that trips up people coming from older version-control systems: **Git stores snapshots, not differences**. Each commit records the *complete* tree — the full state of every tracked file — at that point. It does not store "line 12 changed."

That sounds wasteful, but content-addressing rescues it. If a commit changes one file out of a thousand, the new tree reuses the 999 unchanged blob hashes and the unchanged subtree hashes verbatim; only the objects on the path from the root to the edited file are new. So a "snapshot" of a large project after a one-line edit costs a handful of new objects, not a full copy. You get the *conceptual* simplicity of snapshots with the *storage* efficiency of sharing — because identical content collapses to one object automatically.

This is why "what did this commit change?" is a *computed* answer in Git, not a stored one: it diffs two snapshots on demand. And it's why Git can show you the diff between *any* two commits equally cheaply — there's no privileged chain of deltas to walk.

## Peeking inside

You can dismantle a real commit by hand with plumbing commands. `git cat-file -t` prints an object's type; `-p` pretty-prints its content:

```bash
$ git cat-file -t HEAD
commit

$ git cat-file -p HEAD
tree 9d4e2c8a...          # the snapshot this commit points to
parent 4b7a1f0e...        # the commit before it
author  Pratik <p@x> 1724...
committer Pratik <p@x> 1724...

Fix the retry backoff

$ git cat-file -p 9d4e2c8a       # the tree
100644 blob a1b2...    README.md
040000 tree c3d4...    src
```

Follow the hashes and you walk the entire graph: commit → tree → subtrees → blobs, and commit → parent → parent back to the beginning. There is no hidden state. The `.git/objects` directory *is* the database, and these four object types are its only rows.

## Key takeaways

- Git is fundamentally a **content-addressed key-value store**: you store bytes, Git names them by the hash of their content, and identical content is stored exactly once.
- Because an object's name is derived from its bytes, **you cannot alter history without changing every downstream hash** — this is the root of Git's integrity guarantees.
- There are exactly **four object types**: blobs (file contents, nameless), trees (directories mapping names+modes to hashes), commits (a pointer to one tree plus parents and metadata), and tags (annotated pointers to objects).
- Git stores **full snapshots, not diffs** — each commit references a complete tree — but content-addressing makes this cheap, since unchanged blobs and subtrees are reused by hash across commits.
- Plumbing commands (`hash-object`, `cat-file`) let you inspect the raw objects directly, revealing that the porcelain you use daily is a thin layer over this object graph.

## Further reading

- [Pro Git — Git Internals: Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- [Pro Git — Git Internals: Plumbing and Porcelain](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain)
