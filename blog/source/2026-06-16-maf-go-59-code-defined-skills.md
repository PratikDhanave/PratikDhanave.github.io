# 02 · Code-Defined Skills

*An Agent Skill — on-demand instructions, resources, and scripts — defined entirely in Go, with no SKILL.md files on disk.*

---

## What this lesson demonstrates

A *skill* is a bundle the model reaches for only when a task calls for it: an **instruction body** (the "how to use me"), **resources** it can read, and **scripts** it can run. In step01 those lived in files. Here everything is a Go value or closure — the lookup table, a rounding *policy generated at read time*, and a `convert` script that runs in-process. No `SKILL.md`, no directory of assets. A `skills.ContextProvider` exposes them to the agent as the same three tools: `load_skill`, `read_skill_resource`, `run_skill_script`.

## The wiring

The skill is a struct of closures. Notice one resource is static and the other is generated on every read:

```go
Resources: []skills.Resource{
	{
		Name: "conversion-table",
		Read: func(context.Context) (any, error) { return conversionTable, nil },
	},
	{
		Name: "conversion-policy",
		Read: func(context.Context) (any, error) {
			return fmt.Sprintf("# Conversion Policy\n\n**Generated at:** %s",
				time.Now().UTC().Format(time.RFC3339)), nil
		},
	},
},
```

`newConverterAgent` then wraps the skill in `skills.NewContextProvider(skills.ContextProviderOptions{Skills: []*skills.Skill{skill}})` and attaches it via `agent.Config{ContextProviders: ...}` — the in-memory analogue of step01's file `Source`.

## What to notice

- **A skill is just a struct of closures.** `GetContent`, each `Resource.Read`, and the `Script.Run` are Go functions. No files, no subprocess — `convert` does its arithmetic in-process.
- **Resources can be static or dynamic.** `conversion-table` returns the same Markdown every time; `conversion-policy` is built with `time.Now()` *at read time*, so the model sees a fresh "generated at" stamp on every call. Same `Resource` shape, different behavior — a nice illustration that a resource is a function, not a file.
- **Script args are positional strings.** `run_skill_script` hands the closure a `[]string` exactly as the model formats it (`["26.2","1.60934"]`); a `numberArg` helper parses them, mirroring how a file-based script receives CLI arguments.
- **The pure parts are unit-testable offline.** Because `convert`'s body is plain arithmetic (`multiplyConversion` / `numberArg`), the test asserts `26.2 * 1.60934` rounds to `42.1647` and that bad args error — with no model. A separate wiring test builds the agent with a fake credential and checks `a.Name() == "UnitConverterAgent"`.

## How it maps to the Microsoft Agent Framework

Code-defined and file-based skills are two front-ends onto the same `skills.Skill` shape in the Agent Framework Go SDK — the provider, the three tools, and the `<available_skills>` catalog it injects are identical. Defining a skill in Go is the natural choice when its knowledge is dynamic (computed at read time), when you want in-process scripts with no subprocess or `python` dependency, and when you want the skill's logic covered by ordinary Go unit tests.

## Run it

`go run ./tutorial/02-agents/skills/step02_code_defined_skills` (needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`). The offline tests exercise the skill shape, the pure `convert` math, and the wiring; the live end-to-end run is gated behind `AF_LIVE=1`.

---

Next: [step03 · Mixed Skills](/blog/posts/maf-go-60-mixed-skills.html)
