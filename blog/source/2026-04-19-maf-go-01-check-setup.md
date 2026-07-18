# Check Setup

*The zero-network preflight that confirms your Foundry config and Azure credential chain exist before you run a single agent.*

---

## What this lesson demonstrates

Before the first live agent call, this lesson runs a tiny preflight that answers one question: **is my environment configured?** It does *not* call the model. It checks that a Foundry endpoint is set, prints the model deployment name, and confirms an Azure credential can be constructed from the SDK's auth chain. A green check here means "configured" — proving the token actually works is the job of the first live lesson.

This distinction matters. In the Microsoft Agent Framework Go SDK, an agent is wired from three ingredients: an endpoint, a model deployment, and a `TokenCredential`. This lesson verifies all three are *present* without spending a network round-trip or a token.

## The code

Everything routes through the shared `internal/demo` helpers, so config lives in one place across the whole tutorial:

```go
if demo.Endpoint() == "" {
    fmt.Println("✗ FOUNDRY_PROJECT_ENDPOINT is not set")
    ok = false
} else {
    fmt.Printf("✓ FOUNDRY_PROJECT_ENDPOINT = %s\n", demo.Endpoint())
}

fmt.Printf("✓ FOUNDRY_MODEL           = %s\n", demo.Model())

if _, err := demo.Credential(); err != nil {
    fmt.Printf("✗ credential: %v\n", err)
    ok = false
}
```

If any check fails, the program exits non-zero and points you at the setup README. On success it prints the exact next command to run.

## What to notice

- **Constructing a credential is not the same as using it.** `demo.Credential()` builds the Azure credential chain — it succeeds as long as the chain is *available*. It does not verify you're logged in. That's deliberate: the check stays offline and fast, and the comment even warns you to `az login` "if the first lesson 401s."
- **The gotcha is the false sense of security.** A fully green output does not guarantee a working token. It guarantees your configuration is complete. Auth failures surface on the first real request, not here.
- **One config surface.** Endpoint, model, and credential all come from `internal/demo`, so every later lesson inherits the same two environment variables: `FOUNDRY_PROJECT_ENDPOINT` and `FOUNDRY_MODEL`.

## How it maps to Azure AI Foundry

`FOUNDRY_PROJECT_ENDPOINT` is your Azure AI Foundry project URL; `FOUNDRY_MODEL` is a model *deployment* name inside that project. The credential is a standard `azcore.TokenCredential` — the same auth abstraction every Azure SDK uses, typically backed by `AzureCliCredential` (hence `az login`). Getting these three right once is what unlocks every subsequent lesson.

## Run it

```bash
go run ./tutorial/00-setup/check_setup
```

This lesson is fully offline — it never contacts the model. Later lessons build and test offline too, gating their live model calls behind `AF_LIVE=1`.

---

Next: [01 · Hello Agent](/blog/posts/maf-go-02-01-hello-agent.html)
