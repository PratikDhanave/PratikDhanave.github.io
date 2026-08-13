# Agents from Scratch

*Building a real agent loop in Go by hand — an LLM in a loop that picks tools, runs them, reads the results, and repeats until the task is done — so you can see there is no magic behind LangGraph, MAF, or ADK.*

---

"Agent" is the most oversold word in this field. Vendors sell it as an emergent capability, a leap beyond the plain chat calls we made in post 4. It is not. An agent is a small, boring control loop wrapped around the exact tool-calling round-trip we built by hand in post 5. The model does not "become autonomous" — you write a `for` loop that calls the model, runs whatever tools it asks for, feeds the results back, and calls it again until it stops asking. That loop is the whole trick.

This post builds that loop in Go, with no framework. By the end you will have an `Agent` struct with a tool registry, a `Run(task)` method containing the reason-act loop, an iteration budget so a confused model can't bankrupt you, and honest error handling so a failing tool teaches the model instead of crashing your program. We reuse the `net/http` client from post 4 and the `Message`/`Tool`/`ToolCall` types from post 5 verbatim — the point of this series is that each layer is a thin, legible addition to the last.

---

## What an agent actually is

Strip away the marketing and the definition is precise: **an agent is an LLM placed in a loop, given a goal and a set of tools, that repeatedly chooses an action, observes its result, and continues until the goal is met.**

Three parts do all the work:

- **A goal.** Stated in the system prompt, along with the tools the model is allowed to use.
- **Actions.** The model expresses an action by emitting a `tool_call` — the same mechanism from post 5. "Reasoning" is just the model's own text; "acting" is a tool call.
- **Observations.** You run the real Go function and hand the result back as a `role: "tool"` message. The model reads it and decides what to do next.

This alternation — think, act, observe, think again — is the pattern the literature calls **ReAct** (reason + act). It is not an algorithm you implement; it is a description of what the loop *looks like* from the outside. Our job in Go is to run the loop and keep it honest.

```text
system: goal + available tools
   |
   v
[ call model with full conversation + tool schemas ]
   |
   +-- returns tool_calls? --> run each tool, append observations --> loop
   |
   +-- returns a final answer? --> stop, return it
```

That diagram is the entire post. Everything below is filling it in with real Go.

---

## The tool registry

In post 5 we dispatched tools with a hand-written `switch` statement. That works for one tool; it rots the moment you have five. An agent needs a *registry* — a lookup from tool name to the Go function that implements it, sitting next to the JSON schema the model sees.

We pair the two in a `ToolSpec`: the `Tool` schema (from post 5) that advertises the tool to the model, and a handler that takes raw JSON arguments and returns a string result.

```go
// Handler runs a tool. It receives the raw JSON arguments the model produced
// and returns a string observation. A tool that fails returns an error —
// the loop turns that into an observation, it does not crash.
type Handler func(args json.RawMessage) (string, error)

type ToolSpec struct {
	Schema  Tool    // the JSON-schema advertisement (post 5)
	Handler Handler // the real Go code behind it
}
```

The registry is just a map keyed by tool name. Registering a tool adds one entry:

```go
type Agent struct {
	client   *Client
	model    string
	tools    map[string]ToolSpec
	maxSteps int
	log      *log.Logger
}

func NewAgent(c *Client, model string) *Agent {
	return &Agent{
		client:   c,
		model:    model,
		tools:    map[string]ToolSpec{},
		maxSteps: 10, // hard ceiling — see the guard section
		log:      log.New(os.Stderr, "agent ", log.LstdFlags),
	}
}

func (a *Agent) Register(spec ToolSpec) {
	a.tools[spec.Schema.Function.Name] = spec
}
```

Keying by the schema's own `Function.Name` guarantees the name the model sees and the name we dispatch on are the same string — there is no second place to keep in sync.

**The gotcha:** the model can hallucinate a tool name or call one you never registered. **Always** look the name up in the registry before running anything — never trust the model's `tc.Function.Name` to be real. A missing key is a normal branch (return an error observation so the model can pick a real tool), not a panic. Treating the model's output as adversarial input is the difference between an agent and an exploit.

---

## The Run loop

Here is the heart of it. `Run` seeds the conversation with the system prompt and the task, then loops: call the model with every registered tool, and if the reply contains tool calls, execute them and continue; if it doesn't, the model has answered and we're done.

```go
func (a *Agent) Run(ctx context.Context, task string) (string, error) {
	// Advertise every registered tool to the model.
	schemas := make([]Tool, 0, len(a.tools))
	for _, spec := range a.tools {
		schemas = append(schemas, spec.Schema)
	}

	msgs := []Message{
		{Role: "system", Content: a.systemPrompt()},
		{Role: "user", Content: task},
	}

	for step := 1; step <= a.maxSteps; step++ {
		resp, err := a.client.Complete(ctx, ChatRequest{
			Model: a.model, Messages: msgs, Tools: schemas,
		})
		if err != nil {
			return "", fmt.Errorf("step %d: model call failed: %w", step, err)
		}

		reply := resp.Choices[0].Message
		msgs = append(msgs, reply) // keep the assistant turn (incl. its tool_calls)

		if len(reply.ToolCalls) == 0 {
			a.log.Printf("step %d: final answer", step)
			return reply.Content, nil // the model is done
		}

		// The model wants to act. Run every requested call this turn.
		a.log.Printf("step %d: %d tool call(s)", step, len(reply.ToolCalls))
		for _, tc := range reply.ToolCalls {
			obs := a.dispatch(tc)
			msgs = append(msgs, Message{
				Role:       "tool",
				ToolCallID: tc.ID, // ties this observation to that specific call
				Name:       tc.Function.Name,
				Content:    obs,
			})
		}
	}

	return "", fmt.Errorf("agent gave up after %d steps without answering", a.maxSteps)
}

func (a *Agent) systemPrompt() string {
	return "You are a task-solving agent. Use the available tools to gather " +
		"facts before answering. Call a tool when you need real data; do not " +
		"guess at arithmetic, the current time, or document contents. When you " +
		"have enough information, reply directly with the final answer."
}
```

Compared to post 5's `runWithTools`, the only structural change is that dispatch goes through the registry instead of a `switch`, and we log each step. The transport-vs-content error split from post 5 still holds: a failed HTTP call (`err`) aborts the whole run, because retrying a broken endpoint inside this loop just hammers it. A failing *tool* is handled differently — that is the next section.

---

## Multiple tool calls in one turn

A capable model will ask for several tools at once — "convert 100 EUR to USD *and* tell me the time" comes back as two entries in a single `tool_calls` array. The loop above already handles this: it iterates every `tc` in `reply.ToolCalls` and appends one `role: "tool"` message per call. The critical detail is the pairing.

```go
func (a *Agent) dispatch(tc ToolCall) string {
	spec, ok := a.tools[tc.Function.Name]
	if !ok {
		// Hallucinated tool name — tell the model, don't crash.
		return fmt.Sprintf(`{"error": "unknown tool %q; not in registry"}`,
			tc.Function.Name)
	}

	// Arguments arrive as a JSON *string* (post 5); hand the raw bytes
	// straight to the handler, which decodes into its own typed struct.
	result, err := spec.Handler(json.RawMessage(tc.Function.Arguments))
	if err != nil {
		a.log.Printf("tool %s failed: %v", tc.Function.Name, err)
		return fmt.Sprintf(`{"error": %q}`, err.Error())
	}
	return result
}
```

**The gotcha:** when the model makes N calls in one turn, you must return N observations, each tagged with the `tool_call_id` that matches the `id` the model sent (exactly the rule from post 5, now load-bearing). The provider matches results to calls by that id, not by order. Drop one, or reuse an id, and the next model turn sees an incomplete tool batch — most providers reject the request outright, and the loop breaks with a cryptic 400. One call in, one observation out, correctly labelled.

---

## When a tool fails, feed the error back

The instinct from ordinary Go is to propagate an error up the stack and abort. Inside an agent that is a bug. A tool error is not a program failure — it is *information the model can act on*. If the calculator gets a divide-by-zero, or retrieval finds nothing, the right move is to hand that fact back as an observation and let the model adjust: retry with different arguments, try another tool, or explain the limitation to the user.

That is why `dispatch` never returns a Go `error`. Both a hallucinated tool name and a handler failure come back as a JSON `{"error": ...}` string, which becomes a normal `role: "tool"` observation. From the model's side, "that tool failed because X" is just another thing it observed on the way to the goal.

**The gotcha:** if a tool panics or you `return err` from the loop on the first tool failure, you have thrown away the agent's entire reason for existing — its ability to recover. Wrap handlers so a panic becomes an error string, feed every tool failure back as an observation, and let the model self-correct. The only errors that should abort `Run` are transport failures (the model itself is unreachable) and the iteration budget running out.

---

## Guarding the loop: the iteration budget

The `maxSteps` ceiling is not a nicety; it is the single most important safety property of the whole design. An LLM has no built-in sense of "I am stuck." A confused model will happily call the same tool with the same bad arguments forever, or ping-pong between two tools, and every iteration is another paid round-trip to the provider. Without a cap, one malformed task can drain a budget overnight.

The guard is the `for step := 1; step <= a.maxSteps; step++` bound. When it trips, we return an explicit error rather than a partial answer, so the caller knows the agent gave up rather than succeeded.

**The gotcha:** ALWAYS cap iterations, and set the cap deliberately. Too low and you truncate legitimate multi-step work; too high and a thrashing model burns real money before you notice. Pair the numeric cap with the step logging above so you can *see* thrashing in the logs — a run that hits ten steps and repeats the same tool call is a prompt problem, not a reason to raise the ceiling. The budget is a circuit breaker, not a performance tuning knob.

---

## Giving it real tools

An agent with no tools is just a chat call. Let's register three real ones. Each handler decodes its own arguments from `json.RawMessage` into a typed struct — the defensive second decode from post 5 — and returns a compact JSON string.

A calculator, so the model stops guessing at arithmetic:

```go
var calculatorTool = ToolSpec{
	Schema: Tool{Type: "function", Function: ToolFunction{
		Name:        "calculator",
		Description: "Evaluate a basic arithmetic operation on two numbers.",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"a":  map[string]interface{}{"type": "number"},
				"b":  map[string]interface{}{"type": "number"},
				"op": map[string]interface{}{"type": "string", "enum": []string{"+", "-", "*", "/"}},
			},
			"required": []string{"a", "b", "op"},
		},
	}},
	Handler: func(raw json.RawMessage) (string, error) {
		var in struct {
			A, B float64 `json:"a"`
			Op   string  `json:"op"`
		}
		if err := json.Unmarshal(raw, &in); err != nil {
			return "", fmt.Errorf("bad arguments: %w", err)
		}
		var out float64
		switch in.Op {
		case "+":
			out = in.A + in.B
		case "-":
			out = in.A - in.B
		case "*":
			out = in.A * in.B
		case "/":
			if in.B == 0 {
				return "", errors.New("division by zero")
			}
			out = in.A / in.B
		default:
			return "", fmt.Errorf("unsupported op %q", in.Op)
		}
		return fmt.Sprintf(`{"result": %g}`, out), nil
	},
}
```

A clock, because the model has no idea what time it is:

```go
var clockTool = ToolSpec{
	Schema: Tool{Type: "function", Function: ToolFunction{
		Name:        "current_time",
		Description: "Return the current time in RFC3339 format. No arguments.",
		Parameters:  map[string]interface{}{"type": "object", "properties": map[string]interface{}{}},
	}},
	Handler: func(_ json.RawMessage) (string, error) {
		return fmt.Sprintf(`{"now": %q}`, time.Now().Format(time.RFC3339)), nil
	},
}
```

And a retrieval tool that reaches into the RAG pipeline from post 9. This is the payoff of composing our own layers: retrieval is just another tool. Assume `retrieve(query string) ([]string, error)` is the top-k search over our vector store from post 9.

```go
func retrievalTool(retrieve func(string) ([]string, error)) ToolSpec {
	return ToolSpec{
		Schema: Tool{Type: "function", Function: ToolFunction{
			Name:        "search_docs",
			Description: "Search the internal knowledge base for passages relevant to a query.",
			Parameters: map[string]interface{}{
				"type": "object",
				"properties": map[string]interface{}{
					"query": map[string]interface{}{"type": "string"},
				},
				"required": []string{"query"},
			},
		}},
		Handler: func(raw json.RawMessage) (string, error) {
			var in struct {
				Query string `json:"query"`
			}
			if err := json.Unmarshal(raw, &in); err != nil {
				return "", fmt.Errorf("bad arguments: %w", err)
			}
			hits, err := retrieve(in.Query)
			if err != nil {
				return "", fmt.Errorf("retrieval failed: %w", err)
			}
			if len(hits) == 0 {
				return `{"passages": [], "note": "no relevant documents found"}`, nil
			}
			out, _ := json.Marshal(map[string]interface{}{"passages": hits})
			return string(out), nil
		},
	}
}
```

Wiring it all together is three `Register` calls and a `Run`:

```go
agent := NewAgent(client, "gpt-4o-mini")
agent.Register(calculatorTool)
agent.Register(clockTool)
agent.Register(retrievalTool(retrieve)) // retrieve from post 9

answer, err := agent.Run(ctx,
	"How many days until our compliance deadline, and what does our policy say about it?")
```

Faced with that task, the model can call `search_docs` to find the policy and its date, `current_time` to learn today's date, and `calculator` to subtract — three tools across a few loop iterations — then compose one grounded answer. Notice that the RAG tool means retrieval only happens *when the model decides it needs documents*, not on every turn. That is the difference between an agent and a fixed pipeline.

---

## This is exactly what the frameworks do

Look back at what we built. A loop. A map of tools. A step counter. Defensive JSON decoding. That is the entire mechanism, and it is precisely what LangGraph, Microsoft Agent Framework, and Google's ADK formalize — each of which has its own series on this site. They add real value on top: durable state across runs, human-in-the-loop approval gates, parallel branches, retries with backoff, tracing, and multi-agent orchestration. But the core they wrap is the loop you just wrote by hand.

| | Our hand-rolled agent | What a framework adds |
|---|---|---|
| Reason-act loop | `for` loop over `Complete` | Graph of nodes / durable steps |
| Tool registry | `map[string]ToolSpec` | Decorators, MCP servers, hosted tools |
| Iteration cap | `maxSteps` | Recursion limits + resumable checkpoints |
| Error recovery | error string → observation | Structured retries, fallbacks, approvals |
| Observability | `log.Printf` per step | Spans, traces, replay, eval hooks |

Knowing the loop is not magic changes how you use those frameworks. When an agent misbehaves — loops, thrashes tools, ignores an observation — you now know the exact mechanism to inspect, because you have written it. The abstraction is a convenience, not a mystery.

---

## Key takeaways

- **An agent is an LLM in a loop.** Goal in the system prompt, actions as tool calls, results as observations, repeat until it answers. That's the whole thing.
- **The tool registry replaces the switch.** A `map[string]ToolSpec` pairs each JSON schema with its Go handler and keys on the same name the model sees.
- **Cap the iterations, always.** A confused model loops forever and every loop costs money. The step budget is a circuit breaker, and step logging is how you spot thrashing.
- **Feed tool errors back, don't crash.** A tool failure is an observation the model can recover from; only transport failures and the budget should abort the run.
- **Validate tool calls against the registry.** The model can hallucinate a tool name or malformed arguments — look up the name and decode arguments defensively before running anything.
- **Parallel calls each need their `tool_call_id`.** N calls in a turn means N labelled observations back, or the next turn breaks.
- **The frameworks formalize this loop — they don't replace it.** LangGraph, MAF, and ADK add durability, approvals, and tracing on top of the same mechanism you now understand end to end.

Next in the series we give this agent a memory that outlives a single `Run`, so it can carry context across tasks instead of starting from an empty conversation each time.

---

## Further reading

- [ReAct: Synergizing Reasoning and Acting in Language Models — Yao et al., 2022](https://arxiv.org/abs/2210.03629)
- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic — Tool use (function calling)](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Anthropic — Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- [Go — `encoding/json` package documentation](https://pkg.go.dev/encoding/json)
