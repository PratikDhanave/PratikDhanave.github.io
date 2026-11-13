<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-workflow.html -->

# Agentic Software Engineering in Go: Developer Workflow

*From hand work to head work: the daily developer loop*

---

## The Problem: The Developer-Antagonist Loop

Most developers experience an **antagonistic relationship** with AI agents:

```
Developer: "Write this function"
Agent: [generates code]
Developer: "Not quite right, fix the imports"
Agent: [tries again]
Developer: "Wrong pattern, use this idiom"
Agent: [tries again]
Developer: "Gave up, just wrote it myself"
```

**The problem**: The developer spends more time managing the agent than doing meaningful work. The agent becomes a productivity drain rather than a multiplier.

**The root cause**: Lack of structured interaction model. Developers and agents operate without a shared framework, leading to:

- Vague prompts → vague code → revision cycle
- No clear success criteria → endless back-and-forth
- No constraints → agent ignores organizational standards
- No verification → unverified code reaches developer
- No handoff → developer must re-read and re-understand

## The Developer Workflow

**The Developer Workflow** replaces the antagonistic loop with a structured partnership where the developer moves from "hand work" to "head work."

### The Daily Developer Loop

```mermaid
flowchart TD
    A[Start Day] --> B[Pull Latest Changes]
    B --> C[Review Agent PRs from Overnight]
    C -->|Approve| G[Merge & Continue]
    C|Request| H[Request Agent Revisions]
    H -->|Agent Revises| B
    G --> I[Write Specs for New Features]
    I --> J[Let Agent Implement from Specs]
    J --> K[Run asf verify continuously]
    K -->|Pass| L[Commit when harness passes]
    L --> M[Push Changes]
    M --> N[Factory Runs Overnight Batch Jobs]
    N --> O[Review Results in Morning]
    O --> P[Next Day Repeat]
```

### Spec Authoring Patterns

**Good specs are**:

| Characteristic | Description |
|---------------|-------------|
| **Specific** | Clear, measurable success criteria |
| **Constrained** | Explicit anti-goals and boundaries |
| **Testable** | Verifiable outputs and behaviors |
| **Composable** | Reusable steps and patterns |

**Bad specs**:

| Anti-Pattern | Description |
|-------------|-------------|
| Vague | "Make it fast" |
| Unconstrained | No boundaries |
| Untestable | No clear outputs |
| Monolithic | Can't be decomposed |

### Prompt Engineering for Specs

**Instead of**: `Build a user service`

**Write a spec with**:

- **Goal**: "Implement user CRUD with email verification"
- **Constraints**: "Must use PostgreSQL, must hash passwords with bcrypt"
- **Anti-goals**: "No plain text passwords, no SQL injection"
- **Steps**: `[create schema, implement repo, add handlers, add tests]`

### The ASF CLI Workflow

```bash
# 1. Initialize project
asf init

# 2. Write specification
asf spec template specs/my-feature.yaml
# Edit specs/my-feature.yaml

# 3. Validate specification
asf spec validate my-feature

# 4. Generate agent prompt
asf spec generate my-feature
# The prompt is now the single source of truth

# 5. Run verification continuously
asf verify
# The harness runs build, test, lint in a loop

# 6. Run complete harness
asf harness run my-feature
# If pass: code is verified
# If fail: agent receives fix prompt → revises code

# 7. Commit when harness passes
asf factory submit generate my-feature

# 8. Overnight, factory runs batch jobs
# Review results in morning

# 9. Next day: repeat
```

### Prompt Patterns That Work

| Anti-Prompt | Why It Fails | Better Approach |
|------------|--------------|-----------------|
| "Build a user service" | Too vague, no constraints | Spec with goal, constraints, steps |
| "Make it fast" | Unmeasurable, subjective | "95th percentile latency < 100ms" |
| "Use React" | Framework lock-in, no flexibility | "Use Go with Gin framework" |
| "Fix the bug" | No context, no reproduction | "Fix NULL pointer in UserHandler at line 42" |
| "Optimize the query" | No baseline, no measurement | "Reduce query latency by 40%" |

### Spec Authoring Templates

```yaml
# specs/template.yaml (Spec Template)
id: "spec-001"
version: "1.0"
title: "Example Specification"
description: "A brief description of what this achieves"
intent:
  goal: "Clear, measurable goal for the agent"
  context: "Background context and constraints"
  success_criteria:
    - "Criterion 1: measurable outcome"
    - "Criterion 2: another measurable outcome"
  anti_goals:
    - "What to explicitly avoid"
constraints:
  - id: "c1"
    type: "must"
    description: "Hard constraint the agent must follow"
    validator: "code to validate this constraint"
  - id: "c2"
    type: "must_not"
    description: "What the agent must not do"
inputs:
  input_name:
    type: "string"
    description: "Description of this input"
    required: true
    default: "default value"
outputs:
  output_name:
    type: "string"
    description: "Expected output"
steps:
  - id: "step1"
    name: "First Step"
    description: "What this step does"
    tool: "tool_name"
    inputs:
      key: "value"
    depends_on: []
    validation: "how to validate this step succeeded"
  - id: "step2"
    name: "Second Step"
    description: "What this step does"
    tool: "tool_name"
    inputs:
      key: "value"
    depends_on: ["step1"]
    validation: "how to validate this step succeeded"
```

### Developer Toolbox

```bash
# ASF CLI commands for daily developer loop
asf init                          # Initialize project
asf spec template specs/          # Create spec template
asf spec validate spec-id         # Validate specification
asf spec generate spec-id         # Generate agent prompt
asf verify                        # Run verification loop
asf harness run spec-id           # Run complete harness
asf factory submit generate spec  # Submit task to factory
asf mcp start                     # Start MCP server for API access
asf factory status                # Check factory status
asf security test-input "input"   # Test input sanitization
```

### Developer Commands Quick Reference

| Command | Purpose |
|---------|---------|
| `asf init` | Initialize project structure |
| `asf spec template` | Create spec from template |
| `asf spec validate` | Validate spec completeness |
| `asf spec generate` | Generate agent prompt |
| `asf verify` | Run build/test/lint verification |
| `asf harness run` | Execute complete harness |
| `asf factory submit` | Submit task to factory |
| `asf factory status` | Check factory status |
| `asf mcp start` | Start MCP server |
| `asf security test-input` | Test input sanitization |

### Why the Developer Workflow Matters

| Concern | Traditional Workflow | Developer Workflow |
|---------|---------------------|-------------------|
| **Prompt Management** | Ad-hoc, lost in chat history | Structured in specs/ directory |
| **Success Criteria** | Implicit, never verified | Explicit, verified continuously |
| **Agent Interaction** | Antagonistic, endless revisions | Structured, purposeful |
| **Code Quality** | Inconsistent, manual | Consistent, verified |
| **Handoff** | Difficult, re-read required | Seamless, spec-driven |
| **Onboarding** | 2-4 weeks, variable | 1 week, structured |
| **Productivity** | Agent drains productivity | Agent multiplies productivity |

### Why This Workflow Works

| Principle | How It Helps |
|-----------|----------------|
| **Specs as Source of Truth** | Eliminates "he said/she said" about what to build |
| **Continuous Verification** | Catches errors early, before they compound |
| **Autonomy Calibration** | Agent freedom adjusts based on task risk |
| **Structured Prompts** | Eliminates "vague prompt → vague code" cycle |
| **Handoff Clarity** | New developers read specs, not chat transcripts |
| **Quality Gate** | Harness passes before commit, not after |

### Quick Start

```bash
# 1. Initialize
asf init

# 2. Write your first spec
asf spec template specs/my-feature.yaml

# 3. Edit the spec to your needs
# The spec is now the single source of truth

# 4. Generate the agent prompt
asf spec generate my-feature

# 5. Run verification
asf verify

# 6. Run the harness
asf harness run my-feature

# 7. Submit to factory
asf factory submit generate my-feature

# 8. Repeat daily
```

### Next: Software Factory Orchestration

In the next post, we'll explore **Software Factory Orchestration** — designing always-on, self-sustaining Orchestrator-Worker-Validator systems that operate continuously, not just on-demand.

---

*All code examples are in Go 1.23+. Diagrams use white-background Archify for presentation-ready architecture visualizations.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-10
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-workflow.html
Attribution: please link the canonical URL when citing or quoting this post.
