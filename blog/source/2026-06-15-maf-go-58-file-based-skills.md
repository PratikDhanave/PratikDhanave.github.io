# step01 · File-Based Skills

*Teach an agent a capability from a folder of files — a SKILL.md manifest, resources, and scripts — loaded on demand via progressive disclosure.*

---

## What this lesson demonstrates

A **skill** is a directory on disk, not hand-written Go tool functions. Drop a `SKILL.md` manifest, some reference documents, and runnable scripts into `skills/<name>/`, point a skills `ContextProvider` at that tree, and the agent gains the capability. Skills load lazily by **progressive disclosure**: the model first sees only each skill's *name + description*, then **loads** the full manifest when a task matches, then **reads** referenced resources and **runs** scripts — pulling in only what it needs, when it needs it. This lesson's skill is `unit-converter`, with a conversion table the model reads and a `convert.py` it runs once per conversion.

## The wiring

A file source scans the tree; the provider turns discovered skills into the agent's tools:

```go
func buildSkillsProvider(skillsRoot *os.Root) agent.ContextProvider {
	return skills.NewContextProvider(skills.ContextProviderOptions{
		Sources: []skills.Source{
			fsskills.NewSourceOptions(
				fsskills.SourceOptions{ScriptRunner: runSubprocessScript},
				skillsRoot.FS(),
			),
		},
	})
}
```

The provider is then attached to the agent via `agent.Config{ContextProviders: []agent.ContextProvider{skillsProvider}}`. That single wire gives the agent three tools — `load_skill`, `read_skill_resource`, `run_skill_script` — plus the advertise-only instructions.

## What to notice

- **A skill is files, discovered — not code.** `fsskills.NewSourceOptions(...)` scans the tree for `SKILL.md` files. Each becomes a `skills.Skill`: the manifest is loadable content, sibling `.md`/`.csv`/… files become **resources**, and `.py`/`.js`/`.sh`/`.ps1` files become **scripts**.
- **`os.OpenRoot` sandboxes the filesystem.** The skill tree is opened as an `*os.Root`, so materialization and reads can never escape the `skills` subtree — which is why you run the program from the lesson directory so the relative `skills` path resolves.
- **The `ScriptRunner` is where scripts actually execute.** `runSubprocessScript` copies the skill's files to a temp dir and runs the script in a subprocess, returning its stdout as the tool result. Without it, scripts are still *discovered* but error out if run.
- **Construction is factored out of `main`.** `buildSkillsProvider(...)` and `newAgent(...)` let the offline test build the identical wiring with a fake credential and assert both that the agent is named `UnitConverterAgent` and that the `unit-converter` skill (with its resource and script) is discovered from the files alone.

## How it maps to the Microsoft Agent Framework

Skills are a first-class integration point in the Agent Framework Go SDK, wired through the *same* `ContextProviders` slot other context providers use — so they compose cleanly with the rest of an agent's configuration. Progressive disclosure keeps the model's context lean: the advertise → load → read → run sequence means only the manifest headers are always present, and heavy resources or scripts enter the conversation only when a task actually calls for them.

## Run it

`cd tutorial/02-agents/skills/step01_file_based_skills && go run .` (needs `az login`, `FOUNDRY_PROJECT_ENDPOINT`, and `python` on PATH). The offline tests cover wiring, skill discovery, and the script runner; the `python` end-to-end test skips when `python` is absent, and the live model call is gated behind `AF_LIVE=1`.

---

Next: [02 · Code-Defined Skills](/blog/posts/maf-go-59-code-defined-skills.html)
