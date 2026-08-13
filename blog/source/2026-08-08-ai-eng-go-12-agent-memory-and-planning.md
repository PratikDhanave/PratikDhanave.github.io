# Agent Memory and Planning

*Give the hand-rolled Go agent from post 11 a memory it can carry between turns and a plan it can follow across many steps — a compacting conversation buffer, retrieval over the post-8 vector store, and a plan-then-execute-then-reflect loop, all built from scratch.*

---

In post 11 we built an `Agent` from parts: a tool registry, a `[]Message` history, and a `Run` loop that thinks, calls a tool, observes the result, and repeats until the model produces a final answer. It works, and for a single well-scoped request it's genuinely useful. But it has two holes you feel the moment you ask anything harder.

First, it forgets. The instant `Run` returns, the `[]Message` it built is gone. Ask a follow-up and the agent has no idea what you just discussed — the model is *stateless between calls*, so the only memory that exists is whatever you resend. Second, it improvises. The reason-act loop decides one step at a time with no view of the whole task, so on a multi-step job it wanders, backtracks, and burns turns rediscovering what it should have planned up front.

This post fixes both, from scratch in Go. Memory first — because planning without memory is just a longer way to forget — then planning on top of it.

---

## The core problem: the model remembers nothing

Every call to `client.Complete(ctx, ChatRequest)` is independent. The model doesn't retain your last conversation, your last turn, or even the tool result it just saw — unless that text is sitting in the `Messages` slice you send *this* call. "Agent memory" is not a feature of the model. It is a decision you make on every turn: **what do I put back into the context?**

And you can't put everything back, because the context window is finite (post 3). Every model has a hard token ceiling, and every token you spend on history is a token you can't spend on the current task — and one you pay for, on input, every single turn. So memory engineering is really *budget* engineering: choosing what earns its place in a fixed number of tokens.

There are three layers worth separating, and they map cleanly onto Go types:

| Layer | What it is | Lives where | Lifetime |
|---|---|---|---|
| Short-term (working) | the running message history | `[]Message` in the agent | one task / session |
| Long-term | past facts and interactions, retrievable | the post-8 `VectorStore` | across sessions |
| Scratchpad | notes the agent writes to itself | a field in the run state | one task |

---

## Short-term memory: a conversation buffer that compacts

Working memory is just the message history — the transcript of the current task or conversation. The naive version is one line: keep appending to `[]Message` and resend the whole thing every turn. It's correct, and it's a trap.

**The gotcha:** naive full-history grows unbounded, and because you resend *all* prior tokens on every turn, cost grows roughly *quadratically* over a long session. Turn 1 sends 1 message, turn 50 sends 50 — and the model re-reads turns 1 through 49 every time. A chatty agent that runs for an hour will blow past the context window and, long before that, past your budget. Unbounded history is not "memory," it's a leak.

The fix is to *manage* the buffer. Two strategies, and the good answer combines them:

- **Windowing** — keep only the last *N* turns, drop the oldest. Cheap and simple; it just forgets old context wholesale.
- **Summarization** — when the buffer gets too big, compress the oldest turns into a running summary and keep that summary in context in their place.

The sane design keeps the system prompt pinned, a running summary of everything old, and the *raw* recent turns verbatim. Here's a `ConversationBuffer` that compacts when it crosses a token threshold. `estimateTokens` is the rough counter from post 3 — a token is ~4 characters of English, close enough for a budget guard:

```go
package memory

// estimateTokens is post 3's rough heuristic: ~4 chars per token.
func estimateTokens(s string) int { return (len(s) + 3) / 4 }

// ConversationBuffer is working memory that stays under a token budget by
// summarizing old turns while keeping recent ones verbatim.
type ConversationBuffer struct {
	system     Message   // pinned; never dropped or summarized
	summary    string    // running summary of everything already compacted
	recent     []Message // raw, verbatim recent turns
	maxTokens  int       // budget for the whole rendered buffer
	keepRecent int       // always keep at least this many raw turns
	summarize  func(prior string, turns []Message) (string, error)
}

func (b *ConversationBuffer) Append(m Message) { b.recent = append(b.recent, m) }
```

`Messages` renders the buffer into the slice you actually send: the pinned system message, the summary (if any) as a system note, then the raw recent turns.

```go
func (b *ConversationBuffer) Messages() []Message {
	out := []Message{b.system}
	if b.summary != "" {
		out = append(out, Message{
			Role:    "system",
			Content: "Summary of earlier conversation:\n" + b.summary,
		})
	}
	return append(out, b.recent...)
}

func (b *ConversationBuffer) tokens() int {
	total := 0
	for _, m := range b.Messages() {
		total += estimateTokens(m.Content)
	}
	return total
}
```

`Compact` is the interesting part. When the rendered buffer exceeds the budget, peel off the oldest turns (everything past `keepRecent`), fold them into the summary with a cheap LLM call, and drop the raw copies:

```go
// Compact folds the oldest turns into the running summary until the buffer
// fits its token budget, always leaving keepRecent raw turns intact.
func (b *ConversationBuffer) Compact() error {
	for b.tokens() > b.maxTokens && len(b.recent) > b.keepRecent {
		// Take the oldest turns beyond the keep-window.
		cut := len(b.recent) - b.keepRecent
		old := b.recent[:cut]

		newSummary, err := b.summarize(b.summary, old)
		if err != nil {
			return err
		}
		b.summary = newSummary
		b.recent = append([]Message(nil), b.recent[cut:]...) // keep only recent
	}
	return nil
}
```

The `summarize` function is itself a model call — "here's the summary so far and some older turns, produce an updated summary that preserves decisions, facts, and open questions." You call `Compact` after each turn, before the next `Complete`.

**The gotcha:** summarization is lossy — a summary is a compression, and compression throws away detail you might need three turns from now ("wait, what account number did they give me?"). That's exactly why you keep `keepRecent` raw turns *and* a summary of the old ones, rather than summarizing everything. Recent context is where precision matters most; keep it verbatim and only compress the distant past.

---

## Long-term memory: recall from the vector store

Working memory dies with the task. Long-term memory outlives it: facts the agent learned, decisions it made, things the user told it last week. You already built the machinery for this in posts 7 and 8 — embeddings and a `VectorStore` with `Add` and `Search`. Long-term memory is *RAG pointed at the agent's own history*: write memories in as embeddings, and retrieve the relevant ones back into context on demand.

A thin wrapper turns the vector store into a memory:

```go
package memory

import (
	"time"

	"example.com/vstore"
)

// MemoryStore persists facts as embeddings and recalls relevant ones on demand.
type MemoryStore struct {
	store *vstore.VectorStore
	embed func(string) []float32 // post 7's embedding step
	clock func() time.Time
}

// Remember embeds a fact and stores it with a timestamp, so recall can
// prefer newer memories when two disagree.
func (m *MemoryStore) Remember(id, fact string) error {
	stamped := m.clock().UTC().Format(time.RFC3339) + " | " + fact
	return m.store.Add(id, stamped, m.embed(fact))
}

// Recall returns the k memories most relevant to the query text.
func (m *MemoryStore) Recall(query string, k int) []vstore.Result {
	return m.store.Search(m.embed(query), k)
}
```

Wiring it into the agent is one extra step at the start of a run — the *recall* step. Embed the incoming task, search memory, and inject the hits as a context message before the reason-act loop starts:

```go
// recallInto adds relevant long-term memories to the buffer as context.
func recallInto(buf *ConversationBuffer, mem *MemoryStore, task string) {
	hits := mem.Recall(task, 4)
	if len(hits) == 0 {
		return
	}
	note := "Relevant things you remember (most similar first):\n"
	for _, h := range hits {
		note += "- " + h.Text + "\n"
	}
	buf.Append(Message{Role: "system", Content: note})
}
```

Note that the stored text carries a timestamp, and the embedding is of the *fact* alone — you don't want the date polluting the semantic match, only informing the model once retrieved.

**The gotcha:** retrieved long-term memories can be stale or flatly contradict the current state of the world. The agent "remembers" the user's address from six months ago, or a preference they've since reversed. Retrieval finds *similar* text, not *true* text — similarity has no sense of time. Timestamp every memory (as above), surface the timestamp to the model, and instruct it to prefer the most recent when memories conflict. Better still, when a fact is superseded, write the correction as a new memory so recency and relevance point the same way.

---

## Scratchpad: state the agent writes for itself

The third layer is the smallest: a place the agent records intermediate conclusions *within* a single task. The reason-act trace from post 11 is already a scratchpad — each "thought" the model emits is a note to its future self, resent as context on the next iteration. It's worth making one bit explicit: a plain field the run can write structured intermediate results into (a tally, a partial list, the current plan) so they survive independent of the chatty transcript and don't get lost when the buffer compacts.

```go
// RunState is the agent's scratchpad for a single task.
type RunState struct {
	Task    string
	Plan    []Step   // the current plan (below)
	Results []string // outcomes of completed steps
	Notes   string   // free-form working notes the model maintains
}
```

Keep it small. The scratchpad is working memory with a schema, not a second transcript.

---

## Why one reason-act step isn't enough

That's memory. Now planning — the second hole. The post-11 loop decides the *next* action from the current state and nothing else. For "what's the weather in Pune?" that's perfect: one tool call, done. For "compare our Q1 and Q2 refund rates and draft a summary email" it flails, because success depends on *order and structure* the model can't see one step at a time. It'll fetch Q1, forget why, fetch something unrelated, and burn turns rediscovering the goal.

The fix is to make the plan explicit: decide the shape of the whole task before executing, then execute against that plan — and revise it when reality disagrees.

---

## Plan-then-execute

The first pattern is the simplest: ask the model to decompose the task into an ordered list of steps *before* doing anything, then walk the list. This is structured output (post 5) — you ask for JSON and decode it into a `[]Step`.

```go
type Step struct {
	N       int    `json:"n"`
	Goal    string `json:"goal"`        // what this step achieves
	Tool    string `json:"tool"`        // suggested tool, or "" to reason
	Done    bool   `json:"-"`
}

// plan asks the model to decompose a task into ordered steps.
func (a *Agent) plan(ctx context.Context, task string) ([]Step, error) {
	req := ChatRequest{
		Model: a.model,
		Messages: []Message{
			{Role: "system", Content: "Break the user's task into 2-6 ordered, " +
				"concrete steps. Reply as JSON: {\"steps\":[{\"n\":1,\"goal\":\"...\"," +
				"\"tool\":\"...\"}]}. Use tool \"\" for a pure reasoning step."},
			{Role: "user", Content: task},
		},
		ResponseFormat: jsonObject(), // post 5's structured-output request
	}
	resp, err := a.client.Complete(ctx, req)
	if err != nil {
		return nil, err
	}
	var out struct{ Steps []Step `json:"steps"` }
	if err := json.Unmarshal([]byte(resp.Choices[0].Message.Content), &out); err != nil {
		return nil, err
	}
	return out.Steps, nil
}
```

Executing the plan reuses post 11's `Run` — each step becomes a scoped sub-run of the reason-act loop, focused on one goal instead of the whole sprawling task:

```go
func (a *Agent) executePlan(ctx context.Context, st *RunState) error {
	for i := range st.Plan {
		step := &st.Plan[i]
		prompt := fmt.Sprintf("Overall task: %s\nCurrent step %d: %s",
			st.Task, step.N, step.Goal)
		result, err := a.Run(ctx, prompt) // post 11's reason-act loop
		if err != nil {
			return fmt.Errorf("step %d (%s): %w", step.N, step.Goal, err)
		}
		step.Done = true
		st.Results = append(st.Results, result)
	}
	return nil
}
```

The win is focus: each `Run` sees a small, concrete goal, so its tool selection is sharper and it can't wander. The cost is real too — you've added a whole model call up front just to make the plan, before any work happens.

---

## Re-planning and reflection

A plan made before any observations is a guess, and guesses go stale. Step 2 returns "no data for Q1" and steps 3 through 6 — all built on Q1 data — are now dead. Blindly executing a dead plan is worse than having no plan.

So after each step (or a batch of them), let the agent *reflect*: look at the plan and the results so far, judge whether it's still on track, and revise the remaining steps. This is the core idea behind Reflexion (Shinn et al.) — an agent that critiques its own trajectory and adjusts, rather than barreling ahead.

```go
// reflect asks the model to critique progress and return a revised plan for
// the remaining work. It returns the (possibly rewritten) remaining steps.
func (a *Agent) reflect(ctx context.Context, st *RunState) ([]Step, error) {
	var b strings.Builder
	fmt.Fprintf(&b, "Task: %s\n\nResults so far:\n", st.Task)
	for i, r := range st.Results {
		fmt.Fprintf(&b, "%d. %s\n", i+1, r)
	}
	b.WriteString("\nAre we on track? If a result contradicts the plan, rewrite " +
		"the REMAINING steps. Reply as JSON {\"steps\":[...]} — same shape as before.")

	resp, err := a.client.Complete(ctx, ChatRequest{
		Model:          a.model,
		Messages:       []Message{{Role: "system", Content: b.String()}},
		ResponseFormat: jsonObject(),
	})
	if err != nil {
		return nil, err
	}
	var out struct{ Steps []Step `json:"steps"` }
	err = json.Unmarshal([]byte(resp.Choices[0].Message.Content), &out)
	return out.Steps, err
}
```

**The gotcha:** a plan made up front goes stale — so re-plan *when observations contradict it*, not on a blind timer and not never. Reflecting after every single step doubles your call count for little gain; never reflecting means executing dead plans to the bitter end. The trigger that actually earns its cost is a *surprise*: a step failed, returned empty, or contradicted an assumption the plan rested on. Reflect then.

---

## Task decomposition into sub-tasks

Plan steps and sub-tasks are the same idea at two scales. A step whose `Goal` is itself complex can be handed to a *fresh* agent run — its own plan, its own reason-act loop, its own scratchpad — and only the result bubbles back up. That recursion is how a top-level plan stays short (2-6 steps) while the real work fans out beneath it. In practice you cap the depth, because each level multiplies calls.

Be honest about the trade-off, because it's the whole game: **every layer of planning and reflection adds model calls and latency, and more autonomy means more ways to fail.** A one-shot answer can be wrong; a five-step autonomous plan can be wrong in five places, compound its own mistakes, and cost five times as much doing it. Add planning when a task genuinely needs structure the model can't hold in a single step — not because "agentic" sounds better than "a function that calls an API."

---

## Putting it together

Here's the shape of a planning agent with memory, extending the post-11 `Agent`. Recall long-term memory, plan, execute step by step through the reason-act loop with a compacting buffer, reflect when a step surprises us, and remember the outcome for next time:

```go
func (a *Agent) RunPlanned(ctx context.Context, task string) (string, error) {
	st := &RunState{Task: task}

	recallInto(a.buf, a.mem, task) // long-term memory → context

	plan, err := a.plan(ctx, task)
	if err != nil {
		return "", err
	}
	st.Plan = plan

	for i := 0; i < len(st.Plan); i++ {
		step := &st.Plan[i]
		result, err := a.Run(ctx, step.Goal) // reason-act loop
		if err != nil {
			return "", err
		}
		st.Results = append(st.Results, result)
		step.Done = true
		a.buf.Append(Message{Role: "assistant", Content: result})
		if err := a.buf.Compact(); err != nil { // keep working memory bounded
			return "", err
		}

		if surprising(result) { // failed / empty / contradicts the plan
			revised, err := a.reflect(ctx, st)
			if err != nil {
				return "", err
			}
			st.Plan = append(st.Plan[:i+1], revised...) // splice in new steps
		}
	}

	final := strings.Join(st.Results, "\n")
	_ = a.mem.Remember(task, "Completed: "+task+" → "+final) // long-term write-back
	return final, nil
}
```

Every piece here is something you already built: `Run` and the tool registry from post 11, the `VectorStore` from post 8, embeddings from post 7, structured output from post 5, the token budget from post 3. Memory and planning aren't new machinery so much as new *discipline* applied to the parts you have — deciding what goes back into a finite context, and deciding the order of the work before you start doing it.

---

## Key takeaways

- **The model is stateless; memory is what you resend.** Every `Complete` call is amnesiac. "Agent memory" is your decision, each turn, about what to put back into a finite context window.
- **Bound your working memory.** Naive full history re-sends every prior token every turn — cost grows quadratically. Window old turns or summarize them, but keep recent turns verbatim because summaries are lossy.
- **Long-term memory is RAG over the agent's own history.** Persist facts as embeddings in the post-8 vector store and recall the relevant ones on demand. Timestamp them, because retrieval finds similar text, not current text.
- **One reason-act step doesn't plan.** For multi-step tasks, decompose into an ordered `[]Step` first, then execute each as a scoped sub-run.
- **Re-plan on surprise, not on a schedule.** A stale plan is worse than no plan; reflect when a step fails or contradicts an assumption, and splice in revised steps.
- **Autonomy has a price.** Every planning and reflection layer adds calls, latency, and new failure modes. Add structure only when the task genuinely needs it.

---

## Further reading

- [Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning" (arXiv:2303.11366)](https://arxiv.org/abs/2303.11366) — self-critique and revision as a loop; the primary source for the reflection pattern above.
- [Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (arXiv:2210.03629)](https://arxiv.org/abs/2210.03629) — the reason-act loop post 11 is built on, and the baseline planning improves.
- [Anthropic — Context management and the context window](https://docs.claude.com/en/docs/build-with-claude/context-windows) — how a provider counts tokens and what falls out of the window.
- [Go `container/list` package](https://pkg.go.dev/container/list) — a doubly linked list handy for a sliding conversation window when you evict from the front often.
