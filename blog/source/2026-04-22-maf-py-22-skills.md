# Skills

*Packaging reusable agent capabilities that load lazily via progressive disclosure.*

---

## What this lesson demonstrates

A skill is a portable package of instructions, resources, and scripts that gives an agent a specialized capability on demand. Skills load lazily via "progressive disclosure": only the skill's name and description sit in the system prompt (~100 tokens each). The agent then calls the built-in `load_skill` tool to pull the full instructions, `read_skill_resource` to fetch a reference doc, and `run_skill_script` to execute a bundled script — each only when a task actually needs it. Skills reach the agent through a `SkillsProvider`, which is just a context provider you pass via `context_providers=[...]`.

## The core shape

This lesson uses code-defined skills (`InlineSkill`) so it stays fully self-contained:

```python
unit_converter_skill = InlineSkill(
    frontmatter=SkillFrontmatter(
        name="unit-converter",
        description="Convert between common units... Use when asked to convert miles, kilometers...",
    ),
    instructions="Use this skill when the user asks to convert between units. ...",
)

@unit_converter_skill.script(name="convert", description="Multiply a value by a factor")
def convert_units(value: float, factor: float) -> str:
    return json.dumps({"value": value, "factor": factor, "result": round(value * factor, 4)})
```

You then attach it with `SkillsProvider(unit_converter_skill)` in `context_providers`, and the `load_skill` / `read_skill_resource` / `run_skill_script` tools appear automatically.

## The gotcha

The frontmatter `description` is the only thing the model sees up front, so pack it with trigger keywords. Code-defined scripts run in-process as direct calls — no `script_runner` needed (that is only for file-based scripts). Gate risky scripts behind humans with `SkillsProvider(skill, require_script_approval=True)`, then drain `result.user_input_requests` and reply with `to_function_approval_response(...)`.

## The Azure / MAF mapping

The skills-enabled agent is a `FoundryChatClient`-backed `Agent` with `AzureCliCredential`. For file-based skills on disk, use `SkillsProvider.from_paths(...)` instead of `InlineSkill`.

## Run it

`uv run tutorial/02-agents/14_skills.py` — needs Foundry credentials via `az login`.

---

Next: [Harness](/blog/posts/maf-py-23-harness.html)
