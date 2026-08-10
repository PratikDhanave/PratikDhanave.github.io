# Trajectory Evaluation in Go

*How to score what an agent *did*, not just what it *said* — building trajectory metrics in Go from an exact-match baseline up to arg-aware, order-tolerant scoring, with a human-readable diff of expected vs. actual.*

---

When you evaluate an agent, the final answer is only half the story. Two agents can both reply "Your order ships Thursday" — one after cleanly calling `lookup_order` then `get_shipping_estimate`, the other after calling `refund_order` by mistake, catching the error, and stumbling into the right answer. Same text, very different behaviour. **Trajectory evaluation** scores the *path*: the ordered sequence of tool calls the agent made on its way to the answer.

Google's Agent Development Kit (ADK) formalizes this with a metric it calls `tool_trajectory_avg_score` — an exact-match comparison of the actual tool-call sequence against an expected one, defaulting to a perfect score of `1.0` when they match. ADK ships that for Python. The Go SDK (`google.golang.org/adk/v2`) has no evaluation package, so if you are building agents in Go, you build the scorer yourself. This post does exactly that: an original, dependency-free `TrajectoryScore` in Go, from the strict baseline outward to the metrics you actually want in a test suite.

---

## 1. What a trajectory is

A trajectory is the ordered list of tool invocations an agent emitted during a run. Strip away the prose and the intermediate model tokens and you are left with something like:

```
lookup_order(id="A-1029")
get_shipping_estimate(zip="94016")
```

Two things vary in how much you capture:

- **Tool names only** — the sequence `[lookup_order, get_shipping_estimate]`. Coarse, but often enough to catch the agent taking a wrong turn.
- **Names plus arguments** — did it look up the *right* order id? Arguments are where an agent quietly goes wrong while looking superficially correct.

We model a single step as a struct and a trajectory as a slice:

```go
package trajectory

// ToolCall is one tool invocation in a trajectory.
type ToolCall struct {
	Name string
	Args map[string]any
}

// Trajectory is the ordered sequence of tool calls from one agent run.
type Trajectory []ToolCall
```

The evaluation question is: given an **expected** trajectory (what a correct agent should do) and the **actual** trajectory (what this run did), produce a score in `0..1` and enough detail for a human to see *where* it diverged.

---

## 2. Exact-match scoring: the ADK baseline

The strictest metric asks a yes/no question: is the actual sequence of tool calls identical to the expected one? ADK's `tool_trajectory_avg_score` is built on exactly this comparison — each step must match, and the run scores `1.0` only when the whole sequence lines up.

Here it is as an original Go function. Two calls match when their names are equal and their argument maps are deeply equal:

```go
import "reflect"

// callsEqual reports whether two tool calls match on name and arguments.
func callsEqual(a, b ToolCall) bool {
	if a.Name != b.Name {
		return false
	}
	return reflect.DeepEqual(canonArgs(a.Args), canonArgs(b.Args))
}

// ExactMatch returns 1.0 iff actual equals expected step-for-step, else 0.0.
func ExactMatch(expected, actual Trajectory) float64 {
	if len(expected) != len(actual) {
		return 0
	}
	for i := range expected {
		if !callsEqual(expected[i], actual[i]) {
			return 0
		}
	}
	return 1
}
```

(`canonArgs` normalizes arguments before comparison — we define it in section 5.)

The ADK metric is the **average** of this per-case score across an eval set. If nine of ten cases match exactly, the trajectory score is `0.9`. That averaging is the "avg" in the name; the per-case verdict is binary.

**Why start here:** exact match is unambiguous, cheap, and a great regression tripwire. If a refactor changes which tools your agent calls, an exact-match suite goes red immediately. Use it as a gate on trajectories you consider *fully specified*.

---

## 3. Why exact match is brittle

The trouble with a binary all-or-nothing score is that it punishes harmless variation as harshly as real errors:

- **A single extra call tanks the score.** An agent that calls `lookup_order`, then redundantly calls it again, then answers correctly scores `0.0` — identical to one that called `delete_account`.
- **Order that doesn't matter is treated as if it does.** If a task needs `get_weather("SF")` and `get_weather("NYC")` and the order between them is irrelevant, exact match still fails when the agent picks the other order.
- **It gives no partial credit.** A trajectory that gets four of five steps right is indistinguishable from one that got zero right. During development that hides whether you are getting warmer or colder.
- **Argument nitpicks become failures.** `{"zip": "94016"}` vs. `{"zip": 94016}` (string vs. number) fails a naive deep-equal even though both are the same postcode.

Exact match answers "is this perfect?" You usually also want "how close is this?" and "*where* did it go wrong?" That calls for softer metrics you compose alongside the strict one.

---

## 4. Softer metrics you can build

### In-order subset (did it do the required steps, in order?)

Sometimes the expected trajectory lists the *mandatory* steps, and extra calls are tolerable as long as the required ones appear in the right relative order. That is the classic subsequence check: walk both slices with two pointers, advancing the expected pointer only on a match.

```go
// InOrderSubset returns the fraction of expected calls that appear in actual,
// in the same relative order (extra actual calls are ignored).
func InOrderSubset(expected, actual Trajectory) float64 {
	if len(expected) == 0 {
		return 1
	}
	matched, e := 0, 0
	for a := 0; a < len(actual) && e < len(expected); a++ {
		if callsEqual(expected[e], actual[a]) {
			matched++
			e++
		}
	}
	return float64(matched) / float64(len(expected))
}
```

This gives partial credit and forgives extra work, while still enforcing that (say) `authenticate` happens before `transfer_funds`.

### Set overlap: precision and recall over tool calls

When order genuinely doesn't matter, treat the trajectories as *bags* of calls and borrow precision/recall from information retrieval:

- **Recall** — of the calls the agent *should* have made, how many did it? (Missing steps hurt recall.)
- **Precision** — of the calls the agent *did* make, how many were expected? (Spurious steps hurt precision.)
- **F1** — the harmonic mean, a single 0..1 number balancing both.

We match calls as an unordered multiset so duplicates count correctly:

```go
// setScores returns precision, recall, and F1 over tool calls, ignoring order
// but respecting multiplicity (a call expected twice must occur twice).
func setScores(expected, actual Trajectory) (precision, recall, f1 float64) {
	remaining := make([]bool, len(actual)) // false = still available to match
	tp := 0
	for _, want := range expected {
		for i, got := range actual {
			if !remaining[i] && callsEqual(want, got) {
				remaining[i] = true
				tp++
				break
			}
		}
	}
	if len(actual) > 0 {
		precision = float64(tp) / float64(len(actual))
	} else if len(expected) == 0 {
		precision = 1
	}
	if len(expected) > 0 {
		recall = float64(tp) / float64(len(expected))
	} else {
		recall = 1
	}
	if precision+recall > 0 {
		f1 = 2 * precision * recall / (precision + recall)
	}
	return
}
```

Precision/recall tells a richer story than a single number: low recall means the agent is *skipping* work; low precision means it is *thrashing*.

### Arg-aware comparison

All three metrics above route through `callsEqual`, so argument comparison is a knob, not a rewrite. You choose how strict to be:

- **Names only** — ignore `Args` entirely; useful when arguments are noisy or generated.
- **Exact args** — deep-equal on canonicalized argument maps (what we use by default).
- **Subset args** — the expected call names only the arguments that matter, and the actual call may carry extras. Handy when the model pads calls with optional fields.

A subset variant is a small change:

```go
// callArgsSubset matches when names are equal and every expected arg is present
// in actual with an equal (canonicalized) value; extra actual args are allowed.
func callArgsSubset(want, got ToolCall) bool {
	if want.Name != got.Name {
		return false
	}
	w, g := canonArgs(want.Args), canonArgs(got.Args)
	for k, wv := range w {
		gv, ok := g[k]
		if !ok || !reflect.DeepEqual(wv, gv) {
			return false
		}
	}
	return true
}
```

---

## 5. Normalizing trajectories

Soft metrics are only fair if two *semantically identical* calls compare equal. Two normalizations do most of the work.

**Canonicalize arguments.** JSON round-trips turn `94016` into a `float64`, config turns it into a string, and nested maps arrive with keys in arbitrary order. `canonArgs` coerces values into a comparable shape so `reflect.DeepEqual` behaves. Here we normalize numbers-as-strings and recurse into nested maps:

```go
import (
	"strconv"
	"strings"
)

// canonArgs returns a normalized copy of an argument map so that
// semantically-equal values compare equal under reflect.DeepEqual.
func canonArgs(in map[string]any) map[string]any {
	if in == nil {
		return map[string]any{}
	}
	out := make(map[string]any, len(in))
	for k, v := range in {
		out[k] = canonValue(v)
	}
	return out
}

func canonValue(v any) any {
	switch t := v.(type) {
	case string:
		s := strings.TrimSpace(t)
		if f, err := strconv.ParseFloat(s, 64); err == nil {
			return f // "94016" and 94016 both become float64(94016)
		}
		return s
	case int:
		return float64(t)
	case int64:
		return float64(t)
	case float64:
		return t
	case map[string]any:
		return canonArgs(t)
	default:
		return v
	}
}
```

Tune this to your domain — you might lowercase enum strings, drop a volatile `request_id`, or round floats. The point is that normalization is *policy*: encode what "the same call" means for your agent, once, in one place.

**Ignore ordering where it is legitimate.** Order matters between `authenticate` and `transfer_funds`; it does not between two independent `get_weather` lookups. Rather than hard-code that, pick the metric that matches the task: order-sensitive tasks use `ExactMatch` or `InOrderSubset`; order-free tasks use the set-based `setScores`. Trajectory scoring is not one number — it is a small family of them, and part of authoring an eval case is declaring which invariant the case cares about.

---

## 6. Bringing it together: a scored result with a diff

A score of `0.6` on its own doesn't help you fix anything. The scorer should return the number *and* a human-readable diff of expected vs. actual, so a failing test points straight at the divergence.

```go
import (
	"fmt"
	"strings"
)

// Mode selects how strictly a trajectory is scored.
type Mode int

const (
	ModeExact       Mode = iota // 1.0 iff identical step-for-step
	ModeInOrder                 // fraction of expected calls found in order
	ModeSet                     // F1 over tool calls, order-independent
)

// Result is a scored trajectory comparison.
type Result struct {
	Score     float64 // 0..1
	Mode      Mode
	Precision float64 // populated for ModeSet
	Recall    float64 // populated for ModeSet
	Diff      string  // human-readable expected vs. actual
}

// TrajectoryScore compares actual against expected under the given mode.
func TrajectoryScore(expected, actual Trajectory, mode Mode) Result {
	r := Result{Mode: mode, Diff: renderDiff(expected, actual)}
	switch mode {
	case ModeInOrder:
		r.Score = InOrderSubset(expected, actual)
	case ModeSet:
		r.Precision, r.Recall, r.Score = setScores(expected, actual)
	default:
		r.Score = ExactMatch(expected, actual)
	}
	return r
}

func formatCall(c ToolCall) string {
	parts := make([]string, 0, len(c.Args))
	for k, v := range canonArgs(c.Args) {
		parts = append(parts, fmt.Sprintf("%s=%v", k, v))
	}
	sort.Strings(parts) // stable output regardless of map iteration order
	return fmt.Sprintf("%s(%s)", c.Name, strings.Join(parts, ", "))
}

// renderDiff produces a side-by-side, step-aligned view of the two trajectories.
func renderDiff(expected, actual Trajectory) string {
	var b strings.Builder
	n := len(expected)
	if len(actual) > n {
		n = len(actual)
	}
	for i := 0; i < n; i++ {
		var e, a string
		if i < len(expected) {
			e = formatCall(expected[i])
		} else {
			e = "(none)"
		}
		if i < len(actual) {
			a = formatCall(actual[i])
		} else {
			a = "(none)"
		}
		marker := "  "
		if e != a {
			marker = "!!"
		}
		fmt.Fprintf(&b, "%s step %d: expected %-40s actual %s\n", marker, i, e, a)
	}
	return b.String()
}
```

`formatCall` sorts its argument parts so the diff is deterministic — map iteration order in Go is randomized, and a non-deterministic diff is useless in CI logs. (This needs `import "sort"` alongside the others.)

---

## 7. Tests

Trajectory scoring is exactly the kind of pure, deterministic logic that deserves table tests. These are original and cover the sharp edges: extra calls, reordering, and argument coercion.

```go
package trajectory

import "testing"

func mk(name string, kv ...any) ToolCall {
	args := map[string]any{}
	for i := 0; i+1 < len(kv); i += 2 {
		args[kv[i].(string)] = kv[i+1]
	}
	return ToolCall{Name: name, Args: args}
}

func TestExactMatch(t *testing.T) {
	exp := Trajectory{mk("lookup_order", "id", "A-1029"), mk("get_shipping_estimate", "zip", "94016")}
	act := Trajectory{mk("lookup_order", "id", "A-1029"), mk("get_shipping_estimate", "zip", 94016)}
	if got := ExactMatch(exp, act); got != 1 {
		t.Fatalf("string vs numeric zip should canonicalize to a match, got %v", got)
	}
	extra := append(Trajectory{}, act...)
	extra = append(extra, mk("lookup_order", "id", "A-1029"))
	if got := ExactMatch(exp, extra); got != 0 {
		t.Fatalf("a spurious extra call must fail exact match, got %v", got)
	}
}

func TestInOrderSubset(t *testing.T) {
	exp := Trajectory{mk("authenticate"), mk("transfer_funds", "amt", 50)}
	act := Trajectory{mk("authenticate"), mk("check_balance"), mk("transfer_funds", "amt", 50)}
	if got := InOrderSubset(exp, act); got != 1 {
		t.Fatalf("required steps present in order should score 1.0, got %v", got)
	}
	wrong := Trajectory{mk("transfer_funds", "amt", 50), mk("authenticate")}
	if got := InOrderSubset(exp, wrong); got != 0.5 {
		t.Fatalf("out-of-order transfer should only match authenticate (0.5), got %v", got)
	}
}

func TestSetScores(t *testing.T) {
	exp := Trajectory{mk("get_weather", "city", "SF"), mk("get_weather", "city", "NYC")}
	act := Trajectory{mk("get_weather", "city", "NYC"), mk("get_weather", "city", "SF")}
	if _, _, f1 := setScores(exp, act); f1 != 1 {
		t.Fatalf("reordered independent calls should score F1=1.0, got %v", f1)
	}
	missing := Trajectory{mk("get_weather", "city", "SF")}
	p, r, _ := setScores(exp, missing)
	if p != 1 || r != 0.5 {
		t.Fatalf("one of two calls made: want precision 1.0 recall 0.5, got %v/%v", p, r)
	}
}

func TestDiffFlagsDivergence(t *testing.T) {
	exp := Trajectory{mk("lookup_order", "id", "A-1029")}
	act := Trajectory{mk("refund_order", "id", "A-1029")}
	res := TrajectoryScore(exp, act, ModeExact)
	if res.Score != 0 {
		t.Fatalf("wrong tool should score 0, got %v", res.Score)
	}
	if !strings.Contains(res.Diff, "!!") {
		t.Fatalf("diff should mark the diverging step, got:\n%s", res.Diff)
	}
}
```

Run them with `go test ./...`. Each test pins one design decision: canonicalization makes the string/number zip match, exact match rejects an extra call, in-order scoring gives half credit for a reordered required step, set scoring forgives reordering but not omission, and the diff marks divergence with `!!`.

---

## 8. Choosing a mode

| Task shape | Mode | What it rewards |
|---|---|---|
| Fully specified, order-critical (e.g. auth before write) | `ModeExact` | Exactly the right steps, exactly in order |
| Mandatory steps + tolerable extras, order matters | `ModeInOrder` | Required steps present, correct relative order |
| Independent calls, order irrelevant | `ModeSet` | Coverage (recall) and restraint (precision) |
| Noisy or model-generated arguments | any + names-only `callsEqual` | The right *tools*, ignoring arg churn |
| Optional args the model may pad | any + `callArgsSubset` | The arguments that matter, extras allowed |

---

## Key takeaways

- **Trajectory evaluation scores the path, not the answer** — the ordered tool calls an agent made, optionally with arguments.
- **Exact match is ADK's `tool_trajectory_avg_score` idea**: a binary per-case verdict (`1.0` on identical sequences) averaged across the set. It is a superb regression gate and a poor development signal.
- **Soften deliberately.** In-order subset gives partial credit and forgives extra work; set-based precision/recall/F1 drops the order constraint and tells you whether the agent is skipping or thrashing.
- **Normalization is policy.** Canonicalize arguments so semantically-equal calls compare equal, and pick an order-sensitive vs. order-free metric per case — trajectory scoring is a small family of metrics, not one number.
- **Always return a diff.** A score tells you *whether*; a step-aligned, deterministic diff tells you *where*, which is what turns a red test into a fix.

The Go ADK gives you agents but no eval package, so this scorer is yours to own and shape. Start with exact match as a tripwire, add in-order and set-based modes as your eval set grows, and keep the diff in every failure — it is the difference between a number and a lead.

---

## Further reading

- ADK evaluation concepts and the `tool_trajectory_avg_score` metric: [adk.dev/evaluate](https://adk.dev/evaluate/)
