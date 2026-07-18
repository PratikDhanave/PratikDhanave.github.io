# step03 · Mixed Skills

*Compose three kinds of Agent Skill — code-defined, struct-based, and file-based — into a single agent through one skills context provider.*

---

## What this lesson demonstrates

The previous two lessons showed skills defined in code and skills discovered from files. This one wires **all three origins into the same agent** at once — and shows that a `skills.ContextProvider` doesn't care where a skill came from. The agent, `MultiConverterAgent`, sees one unified catalogue and one prompt asking for three conversions, then loads and runs only the skills each part needs.

| # | Origin | Skill | How its script runs |
|---|--------|-------|---------------------|
| 1 | code-defined | `volume-converter` (a `*skills.Skill` literal) | pure Go (`convertVolume`) |
| 2 | struct-based | `temperature-converter` (a value `skills.Skill`, passed by address) | pure Go (`convertTemperature`) |
| 3 | file-based | `unit-converter` (the `./skills` dir, via `fsskills`) | `python scripts/convert.py` subprocess |

## The wiring

One provider composes all three origins — in-memory skills via `Skills`, the disk-based one via `Sources`:

```go
func buildSkillsProvider(skillsRoot *os.Root) agent.ContextProvider {
	return skills.NewContextProvider(skills.ContextProviderOptions{
		Skills: []*skills.Skill{volumeConverterSkill, &temperatureConverterSkill},
		Sources: []skills.Source{
			fsskills.NewSourceOptions(
				fsskills.SourceOptions{ScriptRunner: runSubprocessScript},
				skillsRoot.FS(),
			),
		},
	})
}
```

## What to notice

- **One provider, three origins.** The agent sees a single skill catalogue and never knows (or cares) which skill came from code and which from disk. That is the composability payoff of routing skills through one `ContextProvider`.
- **Code-defined vs. struct-based is a spelling difference.** `volumeConverterSkill` is a `&skills.Skill{…}` pointer literal; `temperatureConverterSkill` is a value `skills.Skill` handed to the provider by address (`&temperatureConverterSkill`). Both carry inline instructions, an inline resource, and a Go closure script — the two forms exist only to show the field-literal styles side by side.
- **Only the file-based skill shells out.** Its `convert.py` runs via `runSubprocessScript`, which is why the live run needs `python` on PATH while the two Go skills need nothing.
- **`os.OpenRoot` sandboxes discovery**, and the script bodies (`convertVolume` / `convertTemperature`) are plain functions — so the offline test unit-tests the conversion math (including error paths like an unsupported temperature pair) directly, while a wiring test confirms `a.Name() == "MultiConverterAgent"` and that the on-disk `unit-converter` still resolves.

## How it maps to the Microsoft Agent Framework

This is the capstone of the skills trio: it shows that `skills.ContextProviderOptions` accepts both pre-built `Skills` and discovery `Sources` in the *same* provider, so a real agent can blend a hand-authored in-code capability with a library of file-based skills shipped separately. Because the model only ever sees `load_skill` / `read_skill_resource` / `run_skill_script` over a merged `<available_skills>` list, mixing origins is transparent to the prompt — the Agent Framework Go SDK unifies them behind one tool surface.

## Run it

`go run ./tutorial/02-agents/skills/step03_mixed_skills` (needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`, and `python` for the file-based skill). The offline tests cover wiring, file-based discovery, and both Go script bodies; the live model call is gated behind `AF_LIVE=1`.

---

Next: [01 · Streaming — your first workflow](/blog/posts/maf-go-61-01-streaming.html)
