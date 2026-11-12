<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/devprod-02-codemods-at-scale.html -->

# Codemods at Scale — Changing Ten Thousand Call Sites Before Lunch

*Every large codebase carries changes everyone wants and no one will do: the deprecated API with ten thousand call sites, the formatting standard half-adopted, the pattern that post-dates most of the code. By hand they're quarter-long projects that die in review; as codemods — programs that rewrite programs — they're an afternoon of transform engineering and an overnight run. The capability compounds: an organization that can safely change everything everywhere stops being afraid of its own codebase.*

Post [1](/blog/posts/devprod-01-devprod-as-a-discipline.html) called org-loop capability the sleeping leverage; this post builds its core tool — the one that posts 3 and 4 will drive at type systems and upgrades.

## Transform engineering: ASTs, not regexes

The foundational rule: **codemods operate on syntax trees, not text**. Regex rewrites break on the comment containing the pattern, the string literal resembling it, the formatting variant nobody anticipated — at ten thousand sites, "mostly right" is a cleanup project larger than the original task. The AST toolchain — parse, locate nodes semantically, transform the tree, print — brings the properties scale needs: **semantic targeting** (call sites of *this* function, not occurrences of this substring — with scope and import resolution distinguishing your `request` from the library's), **idempotency** (running twice changes nothing — the zdm-03 property, because reruns are inevitable), and **format preservation** (modern codemod frameworks preserve surrounding trivia; where the printer must reformat, pairing the codemod with the codebase formatter — post 5's territory — keeps diffs reviewable). The craft ladder runs from syntax-level transforms (most renames and signature changes) up to **type-informed transforms** that query the compiler's semantic model (needed whenever the rewrite depends on what an expression *is* — post 3's migrations live here). And the honest boundary: transforms handle the mechanical 95%; the gnarly residue — dynamic constructions, metaprogramming, the five sites that resist analysis — gets *detected and listed* by the codemod, then fixed by hand. A transform that knows what it can't transform is a finished tool; one that guesses is an incident.

## The delivery problem: landing ten thousand changes

Writing the transform is half the work; landing it against a living codebase is the other half, and it's a logistics discipline:

- **Shard by ownership.** One ten-thousand-file PR is unreviewable and unmergeable (every rebase conflicts with the whole org). The standard motion: shard the change along ownership boundaries, generate per-team PRs with a shared explanation, land them independently through the merge queue (tscale-07). Tooling tracks the fleet of PRs — landed, pending, conflicted, stale — because a hundred small PRs without fleet tracking is a hundred small abandonments.
- **Review the transform, spot-check the output.** The review-effort model inverts: humans deeply review the *codemod* (it's the thing that can be wrong ten thousand times) plus a stratified sample of its output; selection and CI (tscale-02) carry the per-shard verification. Teams that demand line-by-line review of generated diffs have chosen the quarter-long project with extra steps.
- **Race the treadmill.** The codebase changes while you land: new violations of the old pattern appear behind the codemod's back. The two-part answer: re-run the transform on stragglers (idempotency pays here), and **close the door** — land a lint rule (zdm-07's pattern) forbidding new instances *before* the migration finishes, so the job has a fixed endpoint instead of a decaying asymptote.
- **The atomic exception.** Some changes can't shard (a format-everything flag day, a breaking internal API with no compatibility window). The playbook: automate perfectly in rehearsal (run against repo snapshots until clean), coordinate a quiet window, land in one motion with merge-queue priority, and provide the rebase tool for every in-flight branch — because the flag day's real cost is everyone else's open work.

The capability, once built, changes the organization's relationship to its own code: deprecations actually complete (apiver-05's internal twin), patterns actually propagate, and the "we'd never be able to change that" class of decisions shrinks toward empty — which is the real product: **reversibility at codebase scale**.

The takeaway: codemods are programs that rewrite programs — **AST-based** (semantic targeting, idempotent, format-preserving, type-informed when the rewrite needs meaning), honest about their residue (detect-and-list, never guess). Landing them is logistics: **ownership-sharded PR fleets** with tracking, review effort on the transform plus sampled output, lint rules closing the door against the treadmill, and a rehearsed atomic playbook for the rare flag day. The compounding product is organizational: a codebase that can be changed everywhere, safely, before lunch — and therefore stops being feared.

## Key takeaways

- **Trees, not text**: regexes break at scale; AST transforms give semantic targeting (scope- and import-aware), **idempotency**, and format preservation — with type-informed transforms when rewrites depend on meaning.
- A finished codemod **lists what it can't transform** — the mechanical 95% automated, the residue surfaced for hands, nothing guessed.
- Landing is logistics: **shard by ownership** into tracked PR fleets, review the *transform* + stratified output samples, let selection/CI verify shards, **land the lint rule first** so the migration has an endpoint.
- Flag days are rehearsed: clean runs on snapshots, quiet-window atomic landing, rebase tooling for in-flight work.
- The real product is **reversibility at codebase scale** — the org stops fearing its own code.

## Further reading

- [Abstract syntax tree — the representation codemods operate on](https://en.wikipedia.org/wiki/Abstract_syntax_tree)
- [Code refactoring — the practice being industrialized](https://en.wikipedia.org/wiki/Code_refactoring)

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-10-31
Canonical: https://pratikdhanave.com/blog/posts/devprod-02-codemods-at-scale.html
Attribution: please link the canonical URL when citing or quoting this post.
