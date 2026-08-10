# Control Flow: if, for, while, and match

*How Python decides what runs next — conditionals and the ternary, for-each iteration done idiomatically, while loops, break/continue and the surprising loop-else, structural pattern matching with match/case, and where truthiness and comprehensions fit in.*

---

Control flow is the set of rules that decide *which* statements run and *how many times*. Every language has these constructs, but Python's have a distinct grain: its `for` iterates over things rather than counting, its `match` matches *structure* rather than switching on a value, and loops can carry an `else` clause that most people never learn exists. Learn the grain and your code stops fighting the language. This guide walks the whole toolkit — `if`, the conditional expression, `for`, `while`, `break`/`continue`, `match/case`, truthiness, and comprehensions — with an eye on the idioms that separate Python written *in* Python from Python written in the accent of C or Java.

---

## Conditionals: if / elif / else

The workhorse. An `if` statement runs a block when its condition is truthy, optionally chaining `elif` branches and a final `else`. There is no `switch` here — a chain of `elif` is the plain-conditional tool, and `match` (below) is the structural one.

```python
def grade(score: int) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    else:
        return "F"
```

Branches are tested top to bottom and the first truthy one wins, so order your conditions from most to least specific. Note there is no fall-through: exactly one branch of an `if/elif/else` chain executes.

**The gotcha:** Python has no block delimiters — indentation *is* the block. A misindented line silently joins (or leaves) a branch instead of raising an error. This is why mixing tabs and spaces is forbidden (`TabError`) and why a stray indent can change behavior without changing a single character you'd notice in review.

---

## The conditional expression (Python's ternary)

When you only need to *choose a value*, a full `if` statement is heavy. The conditional expression picks between two values inline:

```python
status = "adult" if age >= 18 else "minor"
```

Read it left to right: the value before `if` is returned when the condition holds, otherwise the value after `else`. Because it's an expression, it can go anywhere a value can — inside a function call, a list element, an f-string. The `else` is mandatory; an expression must always evaluate to something.

**The gotcha:** it's tempting to nest these (`a if p else b if q else c`), but a chained conditional expression reads worse than the `if/elif` statement it replaces. Reach for the ternary only when both outcomes are simple values and the whole thing fits comfortably on one line.

---

## for is for-each, not a counter

This is the single biggest adjustment for people arriving from C, Java, or JavaScript. Python's `for` does not increment a counter and test a bound — it walks an **iterable**, handing you each element in turn:

```python
for name in ["Ada", "Linus", "Grace"]:
    print(name)
```

There is no index variable, no `i++`, no length check. Anything iterable works the same way: lists, tuples, strings (character by character), dict keys, sets, generators, file objects (line by line). Once you internalize "for-each over an iterable," most loops write themselves.

The anti-pattern to unlearn is `for i in range(len(items))` followed by `items[i]`. It reintroduces a counter you don't need and an index you have to keep in sync. Python gives you three tools that cover almost every case where you *think* you need the index.

**Use `enumerate` when you genuinely need the index alongside the value:**

```python
for position, name in enumerate(names, start=1):
    print(f"{position}. {name}")
```

**Use `zip` to walk two (or more) sequences in lockstep:**

```python
for name, score in zip(names, scores):
    print(f"{name}: {score}")
```

**Use `range` only when you truly want numbers** — a fixed count of repetitions, or an arithmetic sequence:

```python
for _ in range(3):        # do something three times; value unused
    retry()

for n in range(0, 100, 10):  # 0, 10, 20, ... 90
    print(n)
```

**The gotcha:** `zip` stops at the *shortest* input and silently drops the tail of the longer one — a frequent source of quietly-lost data. If the inputs should be the same length, `zip(a, b, strict=True)` (Python 3.10+) raises `ValueError` on a mismatch instead of truncating. And `range(stop)` excludes `stop` itself: `range(3)` yields `0, 1, 2`.

---

## while: loop on a condition

Use `while` when you don't know the iteration count up front — you loop until some condition changes. Reading input until end-of-stream, polling until a state settles, retrying until success:

```python
def read_positive() -> int:
    value = -1
    while value < 0:
        raw = input("Enter a positive number: ")
        if raw.isdigit():
            value = int(raw)
    return value
```

If the loop is over a collection with a known length, prefer `for` — it's clearer and can't accidentally spin forever. Reserve `while` for genuinely condition-driven repetition.

**The gotcha:** a `while` loop whose condition never becomes false runs forever. The classic cause is forgetting to advance the state inside the body (never reassigning `value` above, say). Every `while` needs at least one path that moves the condition toward `False`, or an explicit `break`.

---

## break and continue

Two statements steer a loop from the inside. `break` exits the nearest enclosing loop immediately; `continue` skips the rest of the current iteration and jumps to the next one.

```python
def first_even(numbers):
    for n in numbers:
        if n % 2 != 0:
            continue      # skip odd numbers
        return n          # (a plain return also exits the loop)

def find_sentinel(lines):
    for line in lines:
        if line.strip() == "STOP":
            break         # stop scanning entirely
        process(line)
```

Both affect only the *innermost* loop. Python has no labeled break; to exit nested loops, factor the inner loop into a function and `return`, or use a flag.

---

## The loop-else clause

Both `for` and `while` accept an `else` clause, and its meaning surprises nearly everyone: **the `else` block runs only if the loop completed without hitting `break`.** It's really a "no-break" clause — read it as "if we searched the whole thing and never bailed out early."

This is exactly the shape of a search that must distinguish "found it" from "exhausted everything":

```python
def find_divisor(n: int) -> int | None:
    for candidate in range(2, n):
        if n % candidate == 0:
            print(f"{n} is divisible by {candidate}")
            break
    else:
        # only reached if the loop never broke — i.e. no divisor found
        print(f"{n} is prime")
        return None
    return candidate
```

Without loop-else you'd carry a `found = False` flag and check it after the loop; the `else` clause makes the intent explicit and removes the bookkeeping. It's genuinely useful in search loops — and genuinely confusing if the loop body is long, because the `else` sits far from the `break` it pairs with. Use it when the loop is short enough that the pairing is obvious.

**The gotcha:** the name is a historical mistake. `else` here has nothing to do with the loop condition being false — it fires on *normal completion*, and is skipped by `break`. If a loop has no `break` at all, its `else` always runs, which means the `else` is pointless. Only pair loop-else with a `break`.

---

## match / case: structural pattern matching

Added in Python 3.10 (PEP 634), `match` is not a C-style `switch`. It compares a subject against a series of *patterns* that describe **shape and structure**, and can bind pieces of the subject to variables as it matches. That makes it ideal for dispatching on parsed data — commands, JSON-like dicts, tagged tuples, class instances.

Start with a literal-and-capture example: dispatching a parsed command where the first word selects the action.

```python
def run(command: str) -> str:
    match command.split():
        case ["go", direction]:                 # capture: binds `direction`
            return f"Moving {direction}"
        case ["drop", *items]:                  # star pattern: rest into a list
            return f"Dropping {', '.join(items)}"
        case ["quit" | "exit"]:                 # or-pattern
            return "Goodbye"
        case []:
            return "Say something."
        case _:                                 # wildcard: the default
            return f"I don't understand: {command!r}"
```

Each `case` is a pattern. `["go", direction]` matches a two-element list whose first element is exactly `"go"` and binds the second to `direction`. `*items` captures the remaining elements. The `|` combines alternatives. And `_` is the **wildcard** — it matches anything and, unlike a normal name, binds nothing.

**Class patterns** match by type and can pull out attributes positionally or by keyword. Combined with a **guard** (an `if` after the pattern), you get expressive dispatch:

```python
from dataclasses import dataclass

@dataclass
class Circle:
    radius: float

@dataclass
class Rectangle:
    width: float
    height: float

def area(shape) -> float:
    match shape:
        case Circle(radius=r):
            return 3.14159 * r * r
        case Rectangle(width=w, height=h) if w == h:   # guard: only squares
            return w * w
        case Rectangle(width=w, height=h):
            return w * h
        case _:
            raise ValueError(f"Unknown shape: {shape!r}")
```

Patterns are tested top to bottom and the first match wins, so put more specific patterns (the squared-`Rectangle` guard) before the general one. If no case matches and there's no `_`, the `match` simply falls through and does nothing — there is no error, so include a wildcard when you want exhaustiveness.

**The gotcha:** a bare name in a pattern is a **capture, not a comparison**. Writing `case status:` does *not* test whether the subject equals a variable named `status` — it matches *anything* and rebinds `status` to the subject, shadowing your variable. To match against a named constant you must make it a *dotted* name so the parser treats it as a value: put the constant on a class or enum (`case Color.RED:`, `case HTTPStatus.OK:`) or a module (`case status.ACTIVE:`). This is the number-one `match` surprise, and it's why enums pair so well with pattern matching.

---

## Truthiness drives the flow

Every condition above ultimately asks "is this truthy?" — and in Python that question extends far beyond `True`/`False`. Objects have an inherent truth value: `0`, `0.0`, `""`, `[]`, `{}`, `set()`, and `None` are all **falsy**; non-empty containers and non-zero numbers are **truthy**. So you write:

```python
if items:                # truthy iff the list is non-empty
    process(items)

name = user_input or "anonymous"   # falls back when user_input is falsy
```

The `and`/`or` operators return one of their *operands*, not a boolean — `a or b` yields `a` if it's truthy, otherwise `b`. That's what makes `or` a clean default-value idiom, and both operators short-circuit (they stop evaluating as soon as the result is decided).

**The gotcha:** `if items:` and `if items is not None:` are *not* the same test. An empty list is falsy but very much *not* `None`. When "empty" and "absent" mean different things — a supplied-but-empty config versus no config at all — test `is None` explicitly. Reaching for truthiness there will silently treat empty as missing.

---

## Comprehensions: control flow as an expression

When a loop exists only to build a list, dict, or set, a comprehension expresses the same control flow as a single expression — the `for` (and optional `if` filter) fold into the construction:

```python
squares = [n * n for n in range(10)]
evens = [n for n in range(20) if n % 2 == 0]
lengths = {word: len(word) for word in words}
```

These read as "the value, for each item, where the condition holds" — the loop and its filter are still there, just rearranged into a declarative shape. Prefer a comprehension when the goal is to *produce a collection*; keep an explicit `for` loop when the goal is to *perform side effects* (printing, writing, mutating external state), because a comprehension built for its side effects is both slower and misleading to read. We cover comprehensions — and generator expressions, their lazy cousin — in depth in the data-structures post.

---

## Choosing the right construct

| Situation | Reach for |
|---|---|
| Pick one of several branches on plain conditions | `if / elif / else` |
| Choose between two values inline | `x if cond else y` |
| Do something for each element of an iterable | `for item in iterable` |
| Need the position too | `enumerate(iterable)` |
| Walk several sequences together | `zip(a, b)` |
| Repeat a fixed number of times / arithmetic sequence | `range(...)` |
| Loop until a condition changes | `while` |
| "Did the search finish without finding anything?" | loop `else` (with `break`) |
| Dispatch on the *shape* of data | `match / case` |
| Build a collection from a loop | comprehension |

---

## Key takeaways

- **`for` is for-each.** Iterate the thing directly; use `enumerate`/`zip`/`range` instead of `for i in range(len(x))`.
- **The conditional expression chooses a value; `if` chooses a branch.** Don't nest ternaries — that's what `elif` is for.
- **`while` needs a way out.** Every loop must move its condition toward `False` or `break`, or it spins forever.
- **Loop-else is a "no-break" clause.** It runs on normal completion and is skipped by `break` — only ever pair it with a `break`.
- **`match` matches structure, not equality.** Capture patterns, class patterns, guards, `|`, and `_` make it powerful — but a bare name captures rather than compares, so use dotted/enum names for constants.
- **Truthiness is everywhere, and empty is not `None`.** Lean on it for defaults, but test `is None` when absence and emptiness differ.

---

## Further reading

- [Python tutorial — More Control Flow Tools](https://docs.python.org/3/tutorial/controlflow.html)
- [PEP 634 — Structural Pattern Matching: Specification](https://peps.python.org/pep-0634/)
