# 21 · Shell with Environment

*How a real shell tool lets the model run commands, and an environment provider tells it which shell it is driving.*

---

## What this lesson demonstrates

The model gets one tool — `run_shell` — and actually executes commands on your machine. On top of that, an `EnvironmentProvider` probes the shell once (family, OS, working directory, installed CLIs) and injects a summary as instructions, so the model uses `export NAME=value` on POSIX but `$env:NAME = 'value'` on PowerShell.

The lesson also contrasts two shell **modes**: *stateless* spawns a fresh shell per call (a `cd` in one call does not affect the next), while *persistent* reuses one long-lived shell so `cd` and exported variables carry across calls. Both are built by the same constructor — only the `mode` argument changes.

> This program runs real commands on your machine. It sets `AcknowledgeUnsafe: true` to disable the approval prompt so the demo runs unattended. In a real app, keep approval on (the default) or run the shell inside a container.

## The core: shell tool plus environment provider

```go
shell, err := shelltool.NewLocal(shelltool.LocalConfig{
    Mode:              mode,
    AcknowledgeUnsafe: true, // demo runs unattended; keep approval ON in real apps
})
// ...
envProvider := shelltool.NewEnvironmentProvider(shell, shelltool.EnvironmentProviderConfig{})
// ... then in agent.Config:
Tools:            []tool.Tool{shell},
ContextProviders: []agent.ContextProvider{envProvider},
```

The provider holds a reference to the *same* shell it probes, so after the run `envProvider.CurrentSnapshot()` replays exactly what it observed — which `printSnapshot` renders.

## What to notice

- **The environment provider is a `ContextProvider`.** It runs on every invocation but probes the shell only once, turning the result into instructions via `DefaultShellEnvironmentInstructions` — the same mechanism from the additional-AI-context lesson, specialized for "describe the shell you're in."
- **Modes are the observable difference.** In stateless mode the offline formatters and the live demo show `cd` not carrying over; in persistent mode the `cd` and a `DEMO_TOKEN` variable both survive across calls.
- **Approval is the real safety boundary.** By default `run_shell` reports `ApprovalRequired() == true`; opting out with `AcknowledgeUnsafe: true` removes that gate. Don't do it without an independent sandbox.
- **Construction is factored out.** `newShellAgent(...)` returns the agent, the provider, and the shell, so the test builds the identical wiring with a fake credential and asserts the tool is named `run_shell` and `ApprovalRequired()` is false — with no shell execution.

## How it maps to the SDK

`shelltool` gives a Foundry-backed agent genuine local execution, and its `EnvironmentProvider` plugs into the standard `ContextProviders` slot to make the model shell-aware. The pure snapshot formatters (`valueOrUnknown`, `DefaultShellEnvironmentInstructions`) are testable offline for both POSIX and PowerShell, so you validate the instruction text without probing a shell.

## Run it

```bash
go run ./tutorial/02-agents/agents/step21_shell_with_environment
```

The offline test runs anywhere; the live path needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`, runs real commands, and is gated behind `AF_LIVE=1`.

## Key takeaways

- **`shelltool.NewLocal` gives the model a real `run_shell` tool** that executes commands on your machine, paired with an `EnvironmentProvider` that probes the shell once (family, OS, cwd, installed CLIs) and injects a summary so the model uses `export` on POSIX but `$env:` on PowerShell.
- **Modes are the observable difference.** *Stateless* spawns a fresh shell per call (a `cd` doesn't carry over); *persistent* reuses one long-lived shell so `cd` and a `DEMO_TOKEN` variable survive across calls — same constructor, only the `mode` argument changes.
- **Approval is the real safety boundary.** `run_shell` reports `ApprovalRequired() == true` by default; the demo opts out with `AcknowledgeUnsafe: true` to run unattended — don't do that without an independent sandbox or container.
- The pure snapshot formatters are testable offline for both POSIX and PowerShell, so you validate the instruction text without probing a shell.

## Further reading

- [step22 · Foundry Memory](/blog/posts/maf-go-26-foundry-memory.html) — another context provider, this one backed by a Foundry memory store.
- [step04 · Function Tools with Approvals](/blog/posts/maf-go-43-function-tools-with-approvals.html) — the human-in-the-loop consent mechanism the shell tool's approval gate builds on.
- [step18 · Compaction Pipeline](/blog/posts/maf-go-24-compaction-pipeline.html) — a context provider that rewrites history rather than describing the environment.

---

Next: [step22 · Foundry Memory](/blog/posts/maf-go-26-foundry-memory.html)
