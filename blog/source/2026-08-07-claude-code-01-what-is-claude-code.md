# What Claude Code Is

*An agentic coding tool that lives in your terminal, reads and edits your real codebase, runs commands, and works through multi-step tasks — not an autocomplete, but a collaborator you delegate to.*

Most AI coding tools are autocomplete: they suggest the next few lines inside your editor. Claude Code is a different category. It's an *agentic* command-line tool that operates on your whole project — it reads files, edits them, runs your tests, uses git, searches the codebase, and works through a task in a loop until it's done, checking in with you along the way. This series is a practical guide to using it well; this first post is about what it actually is and the mental model that makes it click.

## The shift from autocomplete to agent

The key distinction: an autocomplete completes *your* keystrokes; an agent takes a *goal* and figures out the steps. You say "add rate limiting to the login endpoint and write tests for it," and Claude Code will locate the endpoint, read the surrounding code to match conventions, make the edits, add tests, run them, and report back — pausing for your approval on actions that matter. You're delegating an outcome, not dictating lines.

That reframes your job. You spend less time typing and more time *specifying, reviewing, and steering*. The skill that matters most becomes describing what you want clearly and judging what comes back — much closer to working with a capable junior engineer than to using a fancier IDE.

**The gotcha:** treating Claude Code like autocomplete — tiny, over-specified instructions — wastes it, while treating it like a mind-reader — "make my app better" — gets vague results. The sweet spot is a clear goal with enough context and constraints, then reviewing the work. Learning to pitch at that level is the core skill (post 2).

## Where it runs

Claude Code is a **terminal-native** tool. You run it in your project directory and it works against the real files on disk — the same ones your editor and git see. That has three consequences worth internalizing:

- **It's editor-agnostic.** It works alongside VS Code, JetBrains, Vim, or whatever you use; there are IDE integrations, but the core is the CLI. It also runs in the desktop and web apps and can be driven headlessly (post 8).
- **It has real tools, not just text.** It can read/write files, run shell commands, search, use git, fetch web pages, and call external tools via MCP (post 4). Its power comes from *acting*, not just suggesting.
- **It sees your project as context.** It explores the codebase to understand conventions rather than relying only on what you paste — which is why it can match your patterns.

## Permissions: you stay in control

Because the tool can edit files and run commands, control matters. Claude Code asks for approval before consequential actions — editing files, running commands — and you choose how much autonomy to grant: approve each step, allow certain safe actions automatically, or (deliberately, in the right context) let it run more freely. Permission modes and allowlists let you dial this to your comfort and the task's risk. The model is "powerful but supervised": it proposes, you approve, and you decide where to loosen the reins.

**The gotcha:** granting blanket auto-approval everywhere to save clicks is how an agent runs a command you didn't want on a repo you cared about. Match autonomy to reversibility — loosen it for a scratch branch or a sandbox, keep it tight on anything you can't easily undo.

## What it's genuinely good at

A realistic picture of where it shines:

- **Multi-file changes** that follow a pattern across a codebase.
- **Exploration** — "how does auth work in this repo?" — because it can read widely and fast.
- **Tedious-but-clear tasks** — refactors, boilerplate, migrations, writing tests, fixing a failing build.
- **Getting unstuck** — drafting an approach, explaining an error, proposing a fix.
- **Working through a loop** — make change, run tests, read failure, fix, repeat.

And where you stay firmly in charge: architectural decisions, whether the change is the *right* change, business-context correctness, and reviewing everything before it ships (the Code Review series' lesson applies doubly to AI-generated code).

## The mental model that makes it work

Think of Claude Code as a fast, tireless, broadly-capable collaborator who has read your whole codebase but doesn't share your context, your taste, or your accountability. That model predicts how to work with it: give it the context it lacks (post 3's CLAUDE.md), specify clearly (post 2), let it do the legwork, and review the result as you would a colleague's PR. It multiplies a good engineer; it doesn't replace the judgment.

## What this series covers

1. **This post** — what Claude Code is and the mental model.
2. **The core workflow** — how to prompt, steer, and iterate effectively.
3. **CLAUDE.md and configuration** — giving it durable project context.
4. **MCP** — connecting it to external tools and data.
5. **Subagents and parallel work** — delegating and fanning out.
6. **Hooks and automation** — deterministic control over its behavior.
7. **Skills and slash commands** — packaging repeatable workflows.
8. **Production workflows** — CI, headless, and best practices.

The throughline: Claude Code is a capable agent you *direct*. The value you get is proportional to how well you set it up, specify to it, and review it.

## Key takeaways

- Claude Code is an **agentic, terminal-native coding tool** — it takes a goal and executes multi-step work on your real codebase, not just autocomplete.
- Your job shifts to **specifying, steering, and reviewing** — much like working with a capable junior engineer.
- It **acts** (edits files, runs commands, uses git, searches, calls tools) — power comes from doing, not suggesting.
- **You stay in control** via permissions; match autonomy to how reversible the task is.
- It excels at **multi-file changes, exploration, tedious-but-clear tasks, and loops**; you keep architecture, correctness-against-intent, and final review.
- The right mental model: a **fast, broadly-capable collaborator who lacks your context and accountability** — set it up and review it accordingly.

## Further reading

- [Claude Code documentation](https://docs.claude.com/en/docs/claude-code/overview) — the official overview and setup.
- [Claude Code — best practices](https://www.anthropic.com/engineering/claude-code-best-practices) — how to get the most from agentic coding.
- [Anthropic — Claude Code product page](https://www.claude.com/product/claude-code) — what it is and where it runs.
