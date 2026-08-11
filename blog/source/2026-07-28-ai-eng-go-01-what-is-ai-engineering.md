# What AI Engineering Is

*The opener to a from-scratch series on building applications on top of foundation models in Go — what AI engineering actually is, how it differs from traditional ML and from ordinary software, and why Go is a serious language for the systems around the model.*

---

For most of the last decade, "doing machine learning" meant one thing: you collected a dataset, labelled it, chose an architecture, trained a model on your own hardware, and shipped the weights. The model *was* the product of your work. If you wanted a sentiment classifier, you trained a sentiment classifier. If the domain shifted, you retrained.

That is not what this series is about.

**AI engineering** is the discipline of building applications *on top of* foundation models you did not train — large language models and their multimodal cousins, exposed to you as an API. The model already exists. Someone else spent the compute to train it on a broad slice of the internet, and now it sits behind an HTTP endpoint that takes text (or images, or audio) and returns text. Your job is no longer to produce the model. Your job is to build a reliable, useful, affordable *system* around it.

That shift sounds small. It is not. It moves almost all of the engineering value from the model layer to the application layer — and the application layer is exactly where a language like Go earns its place.

---

## The old shape and the new shape

It helps to name the two workflows side by side, because the vocabulary overlaps but the work does not.

Traditional ML, roughly:

```text
collect data → label → pick architecture → train → evaluate → deploy weights → monitor drift → retrain
```

The hard, expensive, differentiating step is *train*. Most of your team's time goes into data pipelines, feature engineering, and the training loop. The deployed artifact is a model file.

AI engineering, roughly:

```text
pick a model (API) → prompt it → give it context (retrieval) → let it act (tools/agents)
    → evaluate outputs → optimize latency/cost → ship and monitor
```

There is no training step in the critical path. The model is a dependency you *call*, the way you call a database or a payment gateway. What you build is everything around that call: how you phrase the request, what information you put in front of the model, what it's allowed to do, how you check its answer, and how you keep the whole thing fast, cheap, and correct in production.

**The gotcha:** the word "model" now means two very different things depending on who's talking. To an ML researcher it's an artifact you produce. To an AI engineer it's a commodity you consume. This series lives entirely in the second world — we treat the model as a well-documented, occasionally unreliable external service, and we spend our effort on the code that surrounds it.

---

## Why the value moved to the app layer

When any single component becomes a commodity — cheap, interchangeable, available from several vendors behind near-identical APIs — the durable engineering value moves to whatever is *not* commoditized. With foundation models, three things stayed hard:

- **Getting the right context in front of the model.** A model knows a lot about the world in general and nothing about your data, your user, or the document they're looking at right now. Retrieval — fetching the right facts and injecting them into the prompt — is where most real applications live or die.
- **Making the output trustworthy.** The model will confidently produce something plausible even when it's wrong. Turning "plausible text" into "a JSON object my code can act on, that I've checked" is an engineering problem, not a prompting trick.
- **Running it in production at a sane cost and latency.** Each call costs money and takes hundreds of milliseconds to seconds. A naive app makes ten sequential calls where three concurrent ones would do, and pays for tokens it didn't need to send.

Notice that none of these are about the model's internals. They're about *systems*: caching, concurrency, retries, validation, data plumbing, observability. That's ordinary backend engineering wearing a new hat — and it's the reason a systems language belongs in this conversation at all.

---

## What's the same as normal software — and what isn't

If you've built backend services, most of your instincts transfer directly. A call to a model is an outbound network request to an unreliable dependency. It can time out, rate-limit you, return a 500, or come back slower than usual. You already know how to handle that: timeouts, retries with backoff, circuit breakers, structured logging, metrics. All of it applies unchanged.

What's genuinely new is that **the dependency is non-deterministic and it speaks natural language.** Two things follow from that, and they're the through-line of this whole series:

First, *the same input can produce different outputs.* You cannot write a test that asserts exact string equality against a model's response and expect it to pass tomorrow. Correctness becomes statistical — you evaluate over a set of cases and measure a pass rate, rather than asserting a single golden value. That's why "evaluation" gets its own post later; it replaces the unit test as your primary safety net for model behavior.

Second, *the boundary between data and instructions blurs.* In a normal API, a string field is just data. In a prompt, a string a user supplied can be read by the model as an *instruction* — which is the root of prompt injection. Treating model input and output as untrusted, and validating everything the model hands back before your code acts on it, is a security posture you have to adopt deliberately.

**The gotcha:** the failure modes are new, but the discipline is old. Everything you know about defensive programming — validate at the boundary, never trust external input, fail closed — applies with *more* force here, not less, precisely because the dependency is fuzzy. AI engineering rewards paranoid, correctness-minded engineers.

---

## Why Go for AI systems

Most tutorials reach for Python, and for good reason: the research ecosystem, the notebooks, the training frameworks all live there. But remember the shift — we're not training. We're building the *system* around a model that's already trained and sitting behind an API. For that system, Go is an excellent fit, and often a better one.

**Concurrency for many model calls.** Real applications rarely make one model call. They make many — fan out a question across several documents, run three prompts and vote, embed a batch of a thousand chunks. Each call is mostly waiting on the network, which is exactly what goroutines are built for. Firing off dozens of concurrent calls and gathering the results is a handful of lines with a `sync.WaitGroup` or an `errgroup`, and the runtime schedules the waiting work for you without a thread per request.

```go
// Fan out one question across many documents, concurrently.
// (Illustrative — askModel is your own call into a provider's HTTP API.)
func summarizeAll(ctx context.Context, docs []Document) ([]string, error) {
    g, ctx := errgroup.WithContext(ctx)
    out := make([]string, len(docs))
    for i, d := range docs {
        i, d := i, d // capture per iteration
        g.Go(func() error {
            s, err := askModel(ctx, "Summarize:\n"+d.Text)
            if err != nil {
                return err
            }
            out[i] = s
            return nil
        })
    }
    return out, g.Wait()
}
```

That pattern — bounded concurrency over I/O-bound calls — is the backbone of an AI gateway, a batch embedder, or an agent that explores several branches at once. It's Go's home turf.

**Single-binary deployment.** `go build` produces one static binary with no interpreter and no dependency tree to reconcile at deploy time. For infrastructure that sits in the hot path of every model call — a gateway, a router, a caching proxy — that operational simplicity is worth a lot. You ship a binary, not an environment.

**Performance for AI infrastructure.** The pieces *between* your app and the model — rate limiters, token counters, request routers, streaming proxies, prompt caches — are latency-sensitive plumbing sitting in front of an already-slow model. You don't want to add avoidable milliseconds or a garbage-collection pause to something a user is waiting on. Go's low, predictable overhead and cheap concurrency make it a natural language for that layer, which is why several production LLM gateways and vector-database engines are written in it.

**Strong typing for reliable structured outputs.** This is the one people underrate. When you ask a model to return JSON, you want to unmarshal it straight into a struct and have the compiler enforce the shape. Go's static types and explicit error handling turn "the model returned something" into "the model returned a `CreditDecision`, or I have an error I must handle" — no silent `None` sneaking three layers deep before it explodes.

```go
type CreditDecision struct {
    Approved bool     `json:"approved"`
    Limit    int      `json:"limit"`
    Reasons  []string `json:"reasons"`
}

func parseDecision(raw string) (CreditDecision, error) {
    var d CreditDecision
    if err := json.Unmarshal([]byte(raw), &d); err != nil {
        return d, fmt.Errorf("model did not return valid decision JSON: %w", err)
    }
    return d, nil
}
```

The model is fuzzy; your boundary shouldn't be. Go pushes you to name the shape you expect and handle the case where you didn't get it — exactly the paranoia this domain demands.

Here's the honest comparison, without pretending Go wins everywhere:

| Concern | Where Go is strong | Where Python still leads |
|---|---|---|
| Calling model APIs at scale | Concurrency, low overhead | — |
| Deployment / ops | Single static binary | — |
| Structured, validated outputs | Static types, explicit errors | — |
| Training / fine-tuning models | Not practical | Full ecosystem |
| Notebooks / research iteration | Weak | Native |
| Data science / plotting | Weak | Native |

Go is the language for the *system*. Python remains the language for producing the model. This series is about the system.

---

## The honest note on training and fine-tuning

Let me be direct about a boundary, because it shapes everything that follows: **you will not train or fine-tune a model in Go in this series, and you mostly shouldn't try.** The training ecosystem — the frameworks, the GPU kernels, the tooling — lives in Python and C++, and there's no reason to fight that.

That's not a limitation of the approach; it's the whole point of it. AI engineering is *building with* models, not building models. Where fine-tuning genuinely matters — teaching a model a house style, a narrow domain vocabulary, or a specialized output format — we'll treat it two ways: conceptually, so you understand *when* it's the right tool versus when prompting or retrieval would have done the job for a fraction of the effort; and operationally, by calling a provider's fine-tuning API and then *using* the resulting model from Go exactly like any other endpoint. The Go code doesn't care whether the model behind the URL was fine-tuned or not.

**The gotcha:** reaching for fine-tuning is one of the most common early mistakes. It's expensive, it's slow to iterate on, and it goes stale. Most problems people try to solve with fine-tuning are better solved by writing a clearer prompt or by retrieving the right context at request time. We'll keep coming back to that ordering — prompt, then retrieve, then (rarely) fine-tune — throughout the series.

---

## What we'll build, from scratch

This is a build-it-yourself series. Rather than wrap a heavyweight framework, we'll construct the core pieces directly against provider HTTP APIs so you can see exactly what's happening. Over the coming posts we'll cover, roughly in this order:

- **Talking to a model from Go** — the raw HTTP request/response, streaming tokens, timeouts, retries, and a small client you actually own.
- **Prompting as engineering** — treating prompts as versioned, testable inputs rather than magic strings, and getting reliable structured output back.
- **Retrieval (RAG) from scratch** — embeddings, chunking, a vector search you write yourself, and injecting the right context into a prompt.
- **Tools and agents** — letting the model call your Go functions, and building the loop that turns a model into something that can act, safely.
- **Evaluation** — replacing the golden-value unit test with statistical evals you can run in CI.
- **Inference optimization** — caching, batching, concurrency, and cutting token cost without hurting quality.
- **Production reliability** — rate limits, fallbacks across providers, observability, and the security posture for untrusted model I/O.

Each post stands on its own and ends with runnable Go. By the end you'll have written, in plain Go and mostly standard library, the moving parts that the big frameworks hide.

---

## Key takeaways

- **AI engineering builds on top of models, it doesn't build them.** The model is an API you consume, like a database — the engineering value lives in the application layer around it.
- **The value moved because the model became a commodity.** Context (retrieval), trustworthy structured output, and cost/latency in production stayed hard — and none of them are about the model's internals.
- **Most of your software instincts transfer; two things are new.** Outputs are non-deterministic (so correctness is statistical, via evaluation) and input/output is untrusted (so validate at the boundary, always).
- **Go is a strong fit for the system around the model** — goroutines for many concurrent calls, single-binary deployment, low overhead for latency-sensitive AI infrastructure, and static types for reliable structured outputs.
- **We won't train in Go, and that's the point.** Fine-tuning is treated conceptually and via provider APIs; the default order of tools is prompt, then retrieve, then — rarely — fine-tune.

---

## Further reading

- **OpenAI API documentation** — the reference for chat/completions, structured outputs, and embeddings as a primary source for how a provider exposes a model.
- **Anthropic Claude API documentation** — messages, tool use, and streaming, useful for seeing where provider APIs converge and where they differ.
- **Google Gemini API documentation** — another primary-source view of multimodal inputs and function calling.
- **"Attention Is All You Need" (Vaswani et al., 2017)** — the transformer paper underneath every model this series calls; worth reading once for intuition, even though we never touch the architecture directly.
- **The Go standard library** — `net/http`, `encoding/json`, and `context` are, genuinely, most of the toolkit you need to build everything in this series.
