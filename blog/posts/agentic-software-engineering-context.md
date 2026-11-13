<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-context.html -->

# Agentic Software Engineering in Go: Context Engineering

*The foundation that makes everything else work*

---

## The Problem: Unconstrained Agent Behavior

When an LLM generates code without constraints, it operates on its statistical baseline — the most probable output given its training distribution. This produces code that:

- Uses `console.log` instead of structured logging
- Omits error handling for "happy path" scenarios
- Hardcodes values that should be configurable
- Ignores organizational standards and architectural decisions

The result? **Technical debt compounding from day one**. Every agent-generated artifact becomes a maintenance burden because there were no boundaries.

## The Solution: Context Engineering

**Context Engineering** is the discipline of deliberately designing the information architecture that an agent operates within. It answers: *What does the agent know, and how is that knowledge constrained?*

### Two Modes of Agent Execution

| Mode | Description | Outcome |
|------|-------------|---------|
| **Open-Loop** | Prompt the agent with no context constraints | Agent generates statistically probable output. Issues: No structured logging, no health endpoints, no graceful shutdown |
| **Closed-Loop** | Inject ADR constraints and organizational standards | Agent output is rigidly constrained. Benefits: Structured logging, health endpoints, graceful shutdown, observability |

### The Architecture Decision Record (ADR) Pattern

ADRs are the primary mechanism for context engineering. They are formal markdown documents that record:

1. **Context** — Why this decision needs to be made, what problem is being solved
2. **Decision** — What was decided
3. **The Absolute Constraint** — Machine-readable rules the agent MUST follow (using MUST/MUST NOT language)
4. **Consequences** — Trade-offs of the decision

### Go Example: ADR-Driven Context Loading

```go
// pkg/context/context.go — Load ADRs and specs into agent context
engine := context.NewContextEngine(workingDir)
items, err := engine.LoadContext(ctx)

fmt.Printf("Loaded %d context items\n\n", len(items))

// Categories by priority
// ADRs (priority: 100) — absolute constraints
// Specs (priority: 90) — machine-readable specifications  
// Code (priority: 50) — source code patterns and examples
```

### Open-Loop vs Closed-Loop Demonstration

```go
// Open-Loop: Agent with no context
fmt.Println("=== OPEN-LOOP BEHAVIOR (No Context) ===")
fmt.Println("Prompt: 'Build a basic HTTP server in Go that listens on port 8080'")
fmt.Println()
fmt.Println("Expected agent output (statistical baseline):")
fmt.Println(`  http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello, World!")
  })
  http.ListenAndServe(":8080", nil)`)
fmt.Println()
fmt.Println("Issues: No structured logging, no health endpoint, no graceful shutdown")
fmt.Println()

// Closed-Loop: Agent with ADR context
fmt.Println("=== CLOSED-LOOP BEHAVIOR (With ADR Context) ===")
fmt.Println("Prompt: 'Build a basic HTTP server in Go that listens on port 8080'")
fmt.Println("Context: ADR-001-Logging.md requires structured JSON logging with zap")
fmt.Println()
fmt.Println("Expected agent output (constrained by ADR):")
fmt.Println(`  logger, _ := zap.NewProduction()
  defer logger.Sync()

  http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
  })

  http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
    logger.Info("request received",
      zap.String("method", r.Method),
      zap.String("path", r.URL.Path),
      zap.String("remote", r.RemoteAddr),
    )
    fmt.Fprintf(w, "Hello, World!")
  })

  server := &http.Server{Addr: ":8080"}
  go func() { server.ListenAndServe() }()
  // Graceful shutdown handling...`)
fmt.Println()
fmt.Println("Benefits: Structured logging, health endpoint, graceful shutdown, observability")
```

### The Context Pipeline

```mermaid
flowchart TD
    repo[Repository] -->|Read Files| context_engine[Context Engine]
    context_engine -->|Load ADRs| adr_loader[ADR Loader (priority: 100)]
    context_engine -->|Load Specs| spec_loader[Spec Loader (priority: 90)]
    context_engine -->|Load Code| code_loader[Code Loader (priority: 50)]
    adr_loader -->|Inject Constraints| agent_context[Agent Context Window]
    spec_loader -->|Inject Intent| agent_context
    code_loader -->|Inject Patterns| agent_context
```

### Why Context Engineering Matters

| Metric | Open-Loop | Closed-Loop |
|--------|-----------|-------------|
| Structured logging | ❌ No | ✅ Yes |
| Health endpoint | ❌ No | ✅ Yes |
| Graceful shutdown | ❌ No | ✅ Yes |
| Observability | ❌ No | ✅ Yes |
| Technical debt | Compounds silently | Prevented at source |

### Quick Start

```bash
# Initialize a project with ADR context
asf init

# Load and display context
asf context

# See how many context items are loaded
# Configure ADRs in docs/ directory
# Re-run to see closed-loop behavior
```

### Next: Specification Engineering

In the next post, we'll explore **Specification Engineering** — how to replace vague English prompts with precise, machine-readable specifications using the Plan-Build-Verify cycle. We'll introduce the `pkg/spec` package and demonstrate how specifications serve as the single source of truth for agent generation.

---

*All code examples are in Go 1.23+. Diagrams use white-background Archify for presentation-ready architecture visualizations.*

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-03
Canonical: https://pratikdhanave.com/blog/posts/agentic-software-engineering-context.html
Attribution: please link the canonical URL when citing or quoting this post.
