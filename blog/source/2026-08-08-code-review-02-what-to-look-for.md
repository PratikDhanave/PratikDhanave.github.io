# What to Look For in a Code Review

*A reviewer's mental checklist ordered by leverage — design first, then correctness, then tests, then readability, with style and formatting handed off to the tools that were built for it.*

---

Opening a pull request and not knowing where to start is the most common way a review goes wrong. You scroll the diff top to bottom, leave a comment about an unused import, nudge a variable name, hit approve, and move on. The change ships. Two weeks later it turns out the new endpoint recomputes a permission check that another service already owns, and nobody caught it — because the review spent its attention on the import instead of the idea.

A good review has an order of operations. The things a human reviewer is uniquely good at sit at the top; the things a machine does better than any human sit at the bottom, and you should not be doing them at all. This post walks the checklist from highest leverage to lowest, with concrete examples of what a design smell and an edge-case miss actually look like in a diff — and how to phrase the comment.

The single most important habit: **review for design and correctness first, and let tools handle style.** Everything below is an expansion of that sentence.

---

## 1. Design: does this change belong here?

This is where a human reviewer adds the most value, and it is the hardest thing to add later. Code that is wrong can be fixed with a follow-up commit. An approach that is wrong — a feature wired into the wrong layer, a responsibility duplicated across two services, a synchronous call where the system expects a queue — becomes load-bearing the moment it merges, and every later change has to route around it.

Before you read a single line for correctness, ask the design questions:

- **Should this exist at all?** Does the change solve a real problem, or is it speculative generality — a configuration knob nobody asked for, an abstraction for a second case that may never arrive?
- **Does it belong here?** Is this the right module, the right service, the right layer? A validation rule buried in a controller that should live in the domain model will leak into every other controller that touches the same data.
- **Is it the simplest thing that works?** Not the cleverest, not the most extensible — the simplest. Complexity you add today is complexity every future reader and every future change has to pay for.
- **Does it fit what already exists?** Is there a helper, a pattern, or a service that already does most of this? Reinventing a retry loop next to three existing ones is a design problem, not a style one.

Here is a design smell that a line-by-line read misses but a design-first read catches immediately:

```go
// A new HTTP handler that reaches straight into the database
func (h *OrderHandler) Cancel(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")
    _, err := h.db.Exec(
        "UPDATE orders SET status = 'cancelled' WHERE id = $1", id)
    if err != nil {
        http.Error(w, "failed", 500)
        return
    }
    w.WriteHeader(204)
}
```

The SQL is correct. It compiles, it runs, the test (if there is one) passes. But cancelling an order is not an `UPDATE` — it should release inventory, stop a pending charge, and emit an event, all of which already live in `OrderService.Cancel`. The handler has quietly forked the business rule into the transport layer.

> **Review comment:** "This bypasses `OrderService.Cancel`, which also releases reserved inventory and cancels the pending payment authorization. A raw `UPDATE` here will leave orphaned inventory holds. Can the handler call the service method instead of writing SQL directly? That keeps cancellation logic in one place."

**The gotcha:** the most valuable review comment is often "should this exist?" or "is there a simpler approach?" — and it is only cheap to ask *early*. Once the author has built on the approach for two more days, that same question feels like you are asking them to throw away work, and it will land as an attack rather than a question. Skim the whole change for shape *before* you start commenting on lines. If the design is wrong, nothing below matters yet.

---

## 2. Correctness: does it do what it claims?

Once the approach is sound, verify the code actually does what the description says — and, more importantly, what it *doesn't* say. Authors write and test the happy path because that is the path they were thinking about. The reviewer's job is to read the paths the author wasn't thinking about.

Walk the inputs a hostile universe will send:

- **Empty and null.** Empty list, empty string, zero, `nil`, a missing map key. What does the code do when the collection it iterates is empty?
- **Boundaries.** First element, last element, off-by-one on a slice or loop, the exact size where a buffer fills.
- **Failure paths.** Every call that can error — does the error get handled, or swallowed? Does a partial failure leave state half-written?
- **Concurrency.** Shared state touched from more than one goroutine or thread, a check-then-act that isn't atomic, a map written without a lock.

Consider this innocent-looking helper:

```go
func Median(nums []int) int {
    sort.Ints(nums)
    mid := len(nums) / 2
    return nums[mid]   // panics on empty input; wrong for even counts
}
```

The happy-path test — `Median([]int{3, 1, 2})` returns `2` — passes. But `Median(nil)` panics with an index-out-of-range, and `Median([]int{1, 2, 3, 4})` returns `3` when the median of an even-length set should be the average of the two middle values. A small, "obviously fine" diff, and both failure modes are one edge case away.

```diff
 func Median(nums []int) (float64, error) {
-    sort.Ints(nums)
+    if len(nums) == 0 {
+        return 0, errors.New("median of empty slice")
+    }
+    sorted := append([]int(nil), nums...)  // don't mutate the caller's slice
+    sort.Ints(sorted)
     mid := len(nums) / 2
-    return nums[mid]
+    if len(nums)%2 == 1 {
+        return float64(sorted[mid]), nil
+    }
+    return float64(sorted[mid-1]+sorted[mid]) / 2, nil
 }
```

> **Review comment:** "Three edge cases here: `Median(nil)` panics — should it return an error? For even-length input this returns the upper-middle element, not the average of the two middle values, which is what most callers will expect from 'median'. And `sort.Ints` mutates the caller's slice in place — worth copying first so we don't surprise the caller. Can we add tests for empty, even-length, and single-element inputs?"

**The gotcha:** approving because the diff is small and "looks fine" is how edge cases ship. Small diffs get the least scrutiny and cause a disproportionate share of incidents precisely because everyone waves them through. Read the failure paths, not just the happy path — the value you add is proportional to the cases the author *didn't* consider, and those are never in the lines they wrote most confidently.

---

## 3. Tests: do they protect the right behavior?

Tests are how correctness stays true after you stop looking. So review them as carefully as the code, and ask three separate questions.

**Do they exist?** New behavior with no test is a regression waiting to happen. This doesn't mean every line needs coverage, but every branch a user can reach — and especially every edge case from section 2 — should have one.

**Do they test behavior, not implementation?** A test that asserts *what the code does* survives refactoring; a test that asserts *how it does it* breaks the moment you change the internals, even when the behavior is identical. The tell is a test that mocks the module's own internals and then asserts those mocks were called.

```python
# Implementation test — passes, protects nothing
def test_checkout():
    cart = Cart()
    cart._apply_discount = Mock(return_value=90)   # mocking our own internal
    cart._tax = Mock(return_value=9)
    total = cart.total()
    cart._apply_discount.assert_called_once()       # asserts a call, not a result

# Behavior test — survives refactors, catches real bugs
def test_checkout_applies_discount_then_tax():
    cart = Cart(items=[Item(price=100)], discount=0.10, tax_rate=0.10)
    assert cart.total() == 99.0                      # 100 - 10% = 90, +10% tax = 99
```

The first test passes even if `total()` returns the wrong number — it never checks the number. It also fails the instant you rename `_apply_discount`, so it costs you maintenance while protecting nothing. The second pins the actual contract: given these inputs, the total is 99.

**Do they cover the failure paths?** A test suite that only exercises success tells you the code works when nothing goes wrong — which is not the interesting case. Look for tests that assert the error is returned, the transaction rolls back, the retry gives up after N attempts.

**The gotcha:** tests that assert implementation details — mocks of internals, call-count checks on private methods — go green and give everyone confidence while guaranteeing nothing about behavior. When you review a test, ask "if the code returned the wrong answer, would this test fail?" If the answer is no, the test is decoration. Check what the tests actually *guarantee*, not whether the file has tests in it.

---

## 4. Readability: will someone understand this in a year?

Code is read far more often than it is written, and the next reader is usually the author, a year later, with no memory of the context. Readability is a real correctness concern on a long enough timescale — code nobody understands is code nobody can safely change.

What to look for:

- **Names that carry meaning.** `d`, `tmp`, `data2`, and `handleData` tell the reader nothing. `remainingRetries`, `pendingInvoices`, `parseUTCTimestamp` tell them what they're holding. A good name removes the need for a comment.
- **Cohesion.** A function that does one thing is easy to name and easy to test. If you can't name it without "and," it's probably doing too much.
- **Comments that explain *why*, not *what*.** The code already says what it does. A comment earns its place by explaining the reason a reader can't see: a workaround for a known bug, a non-obvious ordering constraint, a business rule with no local justification.

```go
// WHAT — noise; the code already says this
i++ // increment i
count = count + len(batch) // add batch length to count

// WHY — worth its weight
// Stripe rejects idempotency keys older than 24h, so we regenerate
// rather than reuse the one persisted on the original attempt.
key := newIdempotencyKey()
```

> **Review comment:** "`tmp` and `d` here made me re-read the loop twice to work out that `d` is a per-customer delta. Could we name them `pendingDelta` and `customerBalance`? And the `sleep(200)` on line 40 — is 200ms load-bearing (a rate limit?) or arbitrary? A one-line comment on the *why* would save the next reader the guess."

**The gotcha:** the comment that says `// increment i` above `i++` is worse than no comment, because it can drift out of sync with the code and then actively lies. Flag comments that restate the code, and ask for comments where the *reason* is invisible — the ordering that must not change, the magic number that came from a vendor's rate limit. Review the WHY, delete the WHAT.

---

## 5. Security and performance, at a glance

You are not doing a full security audit or a profiling run in a normal review (that depth gets its own treatment later in this series), but a reviewer should keep a lightweight radar running for the cheap-to-spot, expensive-to-miss classes:

- **Security:** untrusted input flowing into a query or shell without parameterization; secrets or tokens hard-coded or logged; a missing authorization check on a new endpoint; user data in an error message.
- **Performance:** a database query inside a loop (the classic N+1), an unbounded result set loaded fully into memory, an allocation in a hot path, a lock held across an I/O call.

You are pattern-matching for the obvious landmines, not measuring. If something looks expensive and sits on a hot path, ask — but ask for a measurement rather than assuming, since guessed performance is usually wrong.

```diff
- for _, id := range userIDs {
-     u, _ := db.Query("SELECT * FROM users WHERE id = $1", id) // N queries
-     users = append(users, u)
- }
+ users, _ := db.Query(
+     "SELECT * FROM users WHERE id = ANY($1)", pq.Array(userIDs)) // one query
```

> **Review comment:** "This runs one query per user ID — with a few hundred IDs that's a few hundred round trips. Could we fetch them in a single `WHERE id = ANY(...)`? Also, the error from `db.Query` is being discarded with `_`; a failure mid-loop would silently return a partial list."

---

## 6. Consistency with the codebase

A change can be correct, well-tested, and readable and still be wrong for *this* codebase because it ignores local convention. Consistency is not conformity for its own sake — a codebase where every module handles errors, structures packages, and names things the same way is one a reader can navigate without relearning it in each corner.

Look for: does error handling match the surrounding style (wrapped errors vs. sentinel values), does the package layout follow the existing shape, does it use the project's logging and config helpers rather than rolling its own? When the change deliberately breaks a convention, that is worth a conversation — sometimes the convention is wrong and this is the start of fixing it — but it should be a *decision*, not an accident.

The line to walk: flag genuine inconsistencies that will confuse future readers; do not impose personal preference where the codebase has no established rule. "We do it this way elsewhere" is a reason; "I'd have done it differently" usually isn't.

---

## 7. What to leave to the tools

Here is the other half of "review for design first": there is a large category of things you should **never** be commenting on, because a machine does them faster, more consistently, and without bruising anyone's ego. Formatting, indentation, import ordering, quote style, trailing whitespace, line length, and most stylistic lint rules belong to a formatter and a linter running in CI — not to a human reading a diff.

| Priority | What to review | Who does it |
|---|---|---|
| 1 — highest | Design: does it belong, is it the simplest approach that fits? | Human (highest leverage) |
| 2 | Correctness: edge cases, error paths, concurrency, boundaries | Human |
| 3 | Tests: exist, test behavior not internals, cover failures | Human |
| 4 | Readability: names, cohesion, comments explaining *why* | Human |
| 5 | Security & performance at a glance | Human (deep audit later) |
| 6 | Consistency with codebase conventions | Human + linter |
| 7 — lowest | Formatting, imports, style, whitespace, line length | **Tools — not humans** |

Wire a formatter (`gofmt`, `black`, `prettier`) and a linter into CI so the diff arrives already clean. Then the review is free to spend its entire budget on the top of the table, where a human is the only thing that can help.

**The gotcha:** bikeshedding over formatting and style that a linter should own is the single most common way reviews waste their value. It burns the reviewer's limited attention on the lowest-leverage row of the table, and it reads to the author as nitpicking — which trains them to dread your reviews and to skim past your comments, including the important ones. Automate style so thoroughly that it never reaches the review, and spend the attention you save on whether the change should exist at all.

---

## Key takeaways

- **Design is the highest-leverage thing you review.** Ask "should this exist?" and "is this the simplest thing that fits the system?" *first*, before reading a single line for correctness — it is the cheapest to fix early and the most expensive to fix late.
- **Read the failure paths, not the happy path.** Empty, null, boundary, concurrent, error — the value you add is proportional to the cases the author didn't consider, and small "looks fine" diffs hide the most.
- **Review what the tests guarantee, not that tests exist.** A test that mocks internals and asserts call counts goes green while protecting nothing. Ask: if the code returned the wrong answer, would this test fail?
- **Comments should explain *why*, not *what*.** Flag comments that restate the code; ask for comments where the reason is invisible.
- **Automate style; review design.** Formatting, imports, and lint belong to tools in CI. Every minute spent bikeshedding whitespace is a minute stolen from the questions only a human can answer.

A review is a budget of attention. Spend it top-down: design, then correctness, then tests, then clarity — and hand everything below that line to the machines built to enforce it.

---

## Further reading

- [Google's Code Review Developer Guide — "What to look for in a code review"](https://google.github.io/eng-practices/review/reviewer/looking-for.html) — a widely-cited, freely available reference on how a reviewer should prioritize design, functionality, tests, and naming.
- [Google's guide on the standard of a code review](https://google.github.io/eng-practices/review/reviewer/standard.html) — on approving changes that improve overall code health rather than holding out for perfection.
- ["Modern Code Review: A Case Study at Google" (Sadowski et al., ICSE-SEIP 2018)](https://research.google/pubs/pub47025/) — an empirical study of how review actually functions at scale, including what reviewers spend their time on.
