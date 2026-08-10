# Closures and Scope: LEGB, nonlocal, and global

*How Python decides what a name means — the LEGB lookup rule, what a closure actually captures, the late-binding loop trap and its fixes, and when you genuinely need `nonlocal` or `global`.*

---

Almost every confusing Python bug that isn't a typo comes down to one question: *when I write a name here, which binding does Python find?* Scope is the set of rules that answers that question, and closures are what happen when a function outlives the scope it was defined in but keeps a live connection to it. Get these two ideas right and a whole category of "why is this variable the wrong value?" mysteries disappears.

This guide builds up from name resolution to closures to the two keywords — `global` and `nonlocal` — that let you rebind names you'd otherwise only be able to read. Everything below is standard CPython behaviour with no external dependencies; paste any snippet into a REPL and watch it run.

---

## 1. LEGB: the order Python searches for a name

When Python evaluates a bare name like `x`, it doesn't guess — it searches four scopes in a fixed order and stops at the first match. The mnemonic is **LEGB**:

- **L — Local:** names assigned inside the current function.
- **E — Enclosing:** the local scopes of any functions wrapping this one, innermost first.
- **G — Global:** names at the top level of the module.
- **B — Built-in:** names Python provides everywhere (`len`, `print`, `range`).

```python
value = "global"          # G

def outer():
    value = "enclosing"   # E (relative to inner)

    def inner():
        value = "local"   # L
        print(value)      # finds Local first -> "local"

    inner()

outer()
```

Delete the local `value = "local"` line and `inner` prints `"enclosing"`; delete the enclosing one too and it prints `"global"`. Each removal makes the lookup climb one rung up the LEGB ladder.

The critical detail: **a name is local to a function if it is *assigned anywhere* in that function's body** — Python decides this once, when it compiles the function, not while it runs. Assignment includes `=`, `for x in ...`, `with ... as x`, function/class definitions, and imports.

```python
count = 10

def show():
    print(count)   # UnboundLocalError, not 10
    count = 5
```

**The gotcha:** because `count = 5` appears later in the body, `count` is local for the *entire* function — including the `print` above it. Python doesn't fall back to the global `count`; it sees a local that hasn't been assigned yet and raises `UnboundLocalError`. Scope is a compile-time property of the whole function, not something that changes line by line.

---

## 2. What a closure actually is

A **closure** is a nested function that refers to a name from an enclosing function's scope, packaged together with a live link to that name so it keeps working after the outer function has returned.

```python
def make_multiplier(factor):
    def multiply(n):
        return n * factor   # factor comes from the enclosing scope
    return multiply

double = make_multiplier(2)
triple = make_multiplier(3)

print(double(10))   # 20
print(triple(10))   # 30
```

`make_multiplier` has already returned by the time we call `double`, yet `factor` is still available. That's the closure: `multiply` closed over `factor`. CPython stores these captured names as **cell objects**, and you can inspect them:

```python
print(double.__closure__[0].cell_contents)   # 2
print(triple.__code__.co_freevars)           # ('factor',)
```

The captured name is called a *free variable* — free because it's neither local to `multiply` nor global; it lives in the enclosing frame. Closures are how decorators, callbacks, and factory functions carry state without a class.

---

## 3. The late-binding trap: closures capture the variable, not the value

Here is the single most common closure mistake in Python, and it follows directly from how closures work.

```python
functions = []
for i in range(3):
    functions.append(lambda: i)

print([f() for f in functions])   # [2, 2, 2] — not [0, 1, 2]
```

Every reasonable person expects `[0, 1, 2]`. The reason it's `[2, 2, 2]` is the heart of this whole topic: **a closure captures the variable, not the value at the moment of definition.** All three lambdas close over *the same* `i` — the one loop variable — and by the time you *call* them, the loop has finished and `i` is stuck at its final value, `2`. This is called **late binding**: the free variable is looked up when the function runs, not when it's created.

Two idiomatic fixes, both of which give each function its *own* binding.

**Fix 1 — default argument (bind the value at definition time):**

```python
functions = [lambda i=i: i for i in range(3)]
print([f() for f in functions])   # [0, 1, 2]
```

Default arguments are evaluated *once, when the function object is created*, so `i=i` snapshots the current value into a fresh per-function parameter. It no longer relies on the shared free variable at all.

**Fix 2 — a factory function (a fresh scope per iteration):**

```python
def make_returner(value):
    return lambda: value

functions = [make_returner(i) for i in range(3)]
print([f() for f in functions])   # [0, 1, 2]
```

Each call to `make_returner` creates a brand-new local `value`, so each closure captures a distinct cell. This is the clearer choice when the captured logic is more than a trivial expression.

**The gotcha:** late binding isn't a bug — it's the *same* mechanism that makes `make_multiplier` work. There, each call gets its own `factor`, so late binding is invisible. In the loop, one shared `i` is reused, so late binding bites. The rule to remember: closures created in a loop over the same variable all see its final value unless you deliberately give each one its own binding.

---

## 4. `nonlocal`: rebinding a name in the enclosing scope

Reading an enclosing name works automatically. **Rebinding** one does not — because, as we saw in section 1, assigning to a name makes it local. So a counter written the obvious way fails:

```python
def make_counter():
    count = 0
    def increment():
        count += 1        # UnboundLocalError: count is treated as local here
        return count
    return increment
```

`count += 1` is `count = count + 1`, an assignment, so `count` becomes local to `increment` — and reading it before assignment fails. `nonlocal` fixes this by telling Python "this name lives in an enclosing function scope; bind there, don't create a new local":

```python
def make_counter():
    count = 0
    def increment():
        nonlocal count
        count += 1
        return count
    return increment

c = make_counter()
print(c(), c(), c())   # 1 2 3
```

Now `increment` mutates the enclosing `count`, and its state persists across calls. `nonlocal` requires the name to already exist in an enclosing (non-global) scope — you can't create one with it, and it will not reach all the way out to module globals.

The distinction to internalise: you need `nonlocal` only to **rebind** (reassign) an enclosing name. If the captured object is *mutable* and you merely mutate it in place, no keyword is required, because you're not reassigning the name:

```python
def make_log():
    entries = []
    def add(msg):
        entries.append(msg)   # mutation, not rebinding -> no nonlocal needed
        return entries
    return add
```

---

## 5. `global`: rebinding a module-level name (and why you rarely should)

`global` is the same idea aimed at module scope: it lets a function *rebind* a name at the top level of the module rather than creating a local.

```python
counter = 0

def bump():
    global counter
    counter += 1

bump()
bump()
print(counter)   # 2
```

Without `global`, the `counter += 1` would raise `UnboundLocalError` for exactly the reason from section 1. With it, the assignment targets the module-level name.

Here's the honest advice: **you almost never need `global`.** Rebinding module state from inside functions creates action-at-a-distance — any function can change the value, so reasoning about the program means reading all of them. The two cleaner alternatives:

- **Return a value** and let the caller decide what to store. Functions that take inputs and return outputs are testable in isolation.
- **Encapsulate state in a class** (or a closure like `make_counter`) so the mutable state has one clear owner.

```python
class Counter:
    def __init__(self):
        self.value = 0
    def bump(self):
        self.value += 1
        return self.value
```

**The gotcha:** `global` and `nonlocal` are for *rebinding* only. Reading a global, or mutating a mutable global in place (`some_list.append(x)`, `some_dict[k] = v`), needs neither keyword. If you find yourself reaching for `global` to share state, that's usually the signal to return a value or introduce a class instead.

---

## 6. Two subtleties worth knowing

### Shadowing built-ins

The **B** in LEGB is the last rung, which means any name you define at a closer scope *shadows* the built-in of the same name. Assign `list = [...]` and you've lost the `list()` constructor for the rest of that scope:

```python
sum = 0
for row in data:
    sum = sum + row      # 'sum' the built-in is now shadowed
total = sum(values)      # TypeError: 'int' object is not callable
```

Python won't warn you — the built-in is simply invisible until the shadowing name goes away. Common casualties are `list`, `dict`, `id`, `sum`, `type`, `str`, and `input`. Pick a different name (`total`, `row_id`, `item_type`); if you truly need the built-in name for a local, a trailing underscore (`type_`, `id_`) is the conventional escape hatch.

### Comprehensions have their own scope

In Python 3, comprehensions and generator expressions run in their **own** local scope — the loop variable does not leak into the surrounding function:

```python
x = "outer"
squares = [x ** 2 for x in range(5)]
print(x)   # still "outer" — the comprehension's x is separate
```

This is a deliberate improvement over the old Python 2 behaviour, where the loop variable did leak. One consequence: because a comprehension is effectively a hidden nested function, it *closes over* names from the enclosing scope just like any closure — which is why the late-binding rules from section 3 apply to lambdas built inside comprehensions too.

| Construct | Creates a new scope? | Loop var leaks? |
|---|---|---|
| `for` loop (statement) | No | Yes — leaks to the function |
| List/set/dict comprehension | Yes | No |
| Generator expression | Yes | No |
| `def` / `lambda` | Yes | N/A |

---

## Key takeaways

- **Name resolution is LEGB — Local, Enclosing, Global, Built-in — searched in that order,** stopping at the first match.
- **Assignment anywhere in a function makes the name local for the whole function**, decided at compile time; that's the source of `UnboundLocalError`.
- **Closures capture the variable (a cell), not its value.** That's what makes factories work — and what causes the late-binding loop trap, fixed with a default argument (`i=i`) or a factory function.
- **`nonlocal` rebinds an enclosing name; `global` rebinds a module-level name.** You need them only to *reassign* — reading or mutating-in-place needs neither.
- **Prefer return values and classes over `global`.** Shared mutable module state is hard to reason about.
- **Don't shadow built-ins** (`list`, `sum`, `id`), and remember comprehensions get their own scope, so their loop variables don't leak.

---

## Further reading

- [Python Language Reference — Naming and binding (execution model)](https://docs.python.org/3/reference/executionmodel.html#naming-and-binding) — the authoritative rules for how names are bound and resolved, including the definition of free variables.
- [Python Language Reference — The `nonlocal` statement](https://docs.python.org/3/reference/simple_stmts.html#the-nonlocal-statement) and [the `global` statement](https://docs.python.org/3/reference/simple_stmts.html#the-global-statement).
- [Python FAQ — Why do lambdas defined in a loop with different values all return the same result?](https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result) — the official explanation of the late-binding closure trap and its fixes.
