# step09 · Dependency Injection

*How Go's constructor-over-an-interface idiom lets you inject a real Foundry agent into a service — and a fake into its test — through the same seam.*

---

## What this lesson demonstrates

The upstream one-liner is "register an Agent and use it from a hosted service with a user-input chat loop." .NET and Python reach for a DI container for that; Go has no such thing, and doesn't need one. This lesson expresses the same idea with the native Go idiom: define a **narrow interface** for the single capability the service needs, have the service depend on that interface, and hand the concrete agent in through a constructor.

The service here is a `ChatService` that owns a stdin/stdout chat loop but knows nothing about Foundry, `azcore`, or credentials. All it holds is a `ChatAgent` — a two-method port (`Name`, `RunText`). `*agent.Agent` satisfies that port for free, so `main` injects the real Joker agent and the test injects a fake, and `ChatService` cannot tell the difference.

## The core: depend on a port, inject the concrete

```go
type ChatAgent interface {
    Name() string
    RunText(ctx context.Context, msg string, options ...agent.Option) agent.ResponseStream
}

type ChatService struct{ agent ChatAgent }

func NewChatService(a ChatAgent) *ChatService {
    return &ChatService{agent: a}
}
```

`NewChatService` is the whole injection point. `main` builds the concrete Foundry agent in `newJoker(...)` and passes it in; the test passes a `fakeAgent` through the exact same constructor.

## What to notice

- **The interface is deliberately tiny.** A two-method port is easy for any implementation — the real agent or a fake — to satisfy with zero adapters.
- **Inject the I/O too.** `Chat(ctx, r io.Reader, w io.Writer)` reads from any reader and writes to any writer, so the test drives the full loop with a `strings.Reader` and a `bytes.Buffer` — no terminal, no `os.Stdin`.
- **Construction is factored out of `main`.** `newJoker(...)` exists so the test builds the identical concrete agent with a fake credential and asserts its wiring (`a.Name() == "Joker"`) fully offline.
- **The gotcha:** `RunText` returns a streaming `agent.ResponseStream`, so `Ask` must `.Collect()` it into a finished `*agent.Response` before calling `.String()`.

## How it maps to the SDK

`foundryprovider.NewAgent` builds an agent bound to Azure AI Foundry via `ModelDeployment(model)`; because your service depends only on the `ChatAgent` interface, swapping the provider (or the whole model) never touches the service. This is the Go-native answer to "register and resolve": the interface is the registration, the constructor is the resolution, and testability falls out for free.

## Run it

```bash
echo "Tell me a joke about a pirate." | go run ./tutorial/02-agents/agents/step09_dependency_injection
```

Reads one question per line until Ctrl-D. The offline tests run anywhere; the live chat loop needs `az login` + `FOUNDRY_PROJECT_ENDPOINT`, and its live test is gated behind `AF_LIVE=1`.

---

Next: [step10 · Agent as an MCP Tool](/blog/posts/maf-go-20-as-mcp-tool.html)
