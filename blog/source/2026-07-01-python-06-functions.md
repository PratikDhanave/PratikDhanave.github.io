# Functions: Arguments, *args, **kwargs, and Defaults

*A working guide to Python's function signatures — positional and keyword arguments, default values and the mutable-default trap, packing with *args/**kwargs, unpacking at call sites, keyword-only and positional-only parameters, and treating functions as first-class values.*

---

A function is the first real abstraction you build in Python: a named block of behavior you can call from anywhere, hand different inputs, and reuse without repeating yourself. The `def` statement is easy to learn — but Python's *parameter system* is unusually rich, and most of the bugs juniors hit live there, not in the function body. This guide walks the whole signature surface: how arguments bind to parameters, how defaults work (and where they bite), how `*args`/`**kwargs` absorb the unknown, and how the same star syntax spreads a collection back out at the call site.

Every example below is plain Python 3.9+ and runs as-is. The goal is not to memorize syntax but to build an accurate mental model of *what happens when you call a function*.

---

## Defining and returning

`def` binds a name to a function object and lists its parameters. `return` hands a value back to the caller and ends the call immediately.

```python
def area(width, height):
    return width * height

print(area(3, 4))   # 12
```

A function without a `return` — or with a bare `return` and nothing after it — still returns something: the value `None`. This is silent, and it is a common source of confusion when a function *prints* a result but a caller tries to use its return value.

```python
def show(x):
    print(x)        # displays x, but returns nothing

result = show(5)    # prints 5
print(result)       # None
```

**The gotcha:** printing and returning are different acts. `print` sends text to the console; `return` produces a value the calling code can capture. A function that only prints returns `None`, so `total = show(5)` leaves `total` as `None`. When a function is meant to *compute*, `return` the result and let the caller decide whether to print it.

---

## Positional vs keyword arguments

Arguments can be passed by position (matched left to right) or by keyword (matched by name). Keyword arguments make a call self-documenting and free you from remembering parameter order.

```python
def connect(host, port, timeout):
    return f"{host}:{port} (timeout={timeout}s)"

connect("db.internal", 5432, 30)                          # all positional
connect("db.internal", port=5432, timeout=30)             # mixed
connect(port=5432, host="db.internal", timeout=30)        # all keyword, any order
```

The one rule: once you start using keywords in a call, every following argument must also be a keyword. `connect("db.internal", port=5432, 30)` is a `SyntaxError` because the positional `30` comes after a keyword.

**The gotcha:** at the call site, `connect(host="db", 5432, 30)` fails — a positional argument can never follow a keyword one. Keep all positional arguments first, then switch to keywords and stay there.

---

## Default parameter values

A parameter can declare a default, making it optional at the call site. Parameters with defaults must come after those without.

```python
def greet(name, greeting="Hello", punctuation="!"):
    return f"{greeting}, {name}{punctuation}"

greet("Ada")                       # 'Hello, Ada!'
greet("Ada", "Hi")                 # 'Hi, Ada!'
greet("Ada", punctuation=".")      # 'Hello, Ada.'
```

Defaults let a function grow options without breaking existing callers — old calls keep working, new callers opt into the extra parameters. This is the backbone of stable, extensible APIs.

---

## The mutable default argument trap

This is the single most infamous Python footgun, and it follows directly from one fact: **a default value is evaluated exactly once, when the `def` statement runs — not each time the function is called.** For an immutable default like `0` or `"Hello"` that is invisible. For a *mutable* default like a list or dict, that one object is shared across every call that relies on the default.

```python
def append_item(item, bucket=[]):     # bucket is created ONCE, at def time
    bucket.append(item)
    return bucket

print(append_item("a"))   # ['a']
print(append_item("b"))   # ['a', 'b']  <- surprise: the SAME list persists
print(append_item("c"))   # ['a', 'b', 'c']
```

Each call that omits `bucket` reuses the identical list object created when the function was defined, so it accumulates across calls that were meant to be independent. The fix is the **`None` sentinel**: default to `None`, then build a fresh object inside the body.

```python
def append_item(item, bucket=None):
    if bucket is None:
        bucket = []               # a new list on every defaulted call
    bucket.append(item)
    return bucket

print(append_item("a"))   # ['a']
print(append_item("b"))   # ['b']  <- independent, as intended
```

**The gotcha:** never use a mutable value (`[]`, `{}`, `set()`, or an object holding state) as a default. Use `None` as a sentinel and construct the real default in the body. The same rule applies to any default whose value is computed at import time — if it must be fresh per call, build it inside the function.

---

## *args: packing extra positional arguments

Prefix a parameter with `*` and it collects all *extra positional* arguments into a tuple. This lets a function accept any number of arguments.

```python
def total(*numbers):
    running = 0
    for n in numbers:
        running += n
    return running

total()            # 0    -> numbers is ()
total(3)           # 3    -> numbers is (3,)
total(3, 4, 5)     # 12   -> numbers is (3, 4, 5)
```

The name `args` is only convention; `*numbers` is exactly as valid. What matters is the single `*`, which means "pack whatever positional arguments remain into a tuple." You can require some fixed parameters first, then let `*args` absorb the rest:

```python
def log(level, *messages):
    for msg in messages:
        print(f"[{level}] {msg}")

log("INFO", "starting", "loading config", "ready")
```

---

## **kwargs: packing extra keyword arguments

The double star `**` does the same for *keyword* arguments, collecting them into a dict.

```python
def make_tag(name, **attributes):
    attrs = "".join(f' {k}="{v}"' for k, v in attributes.items())
    return f"<{name}{attrs}>"

make_tag("a", href="/home", target="_blank")
# '<a href="/home" target="_blank">'
```

The full ordering of parameters in a definition is fixed: regular parameters, then `*args`, then keyword-only parameters, then `**kwargs`. A signature can use any subset, but always in that order.

```python
def handler(required, *args, flag=False, **kwargs):
    ...
```

**The gotcha:** `*args` gives you a **tuple** and `**kwargs` gives you a **dict** — those are the packed types inside the body, regardless of what the caller passed. And `**kwargs` only captures keyword arguments whose names don't match an existing parameter; a keyword that matches a named parameter binds to *that* parameter instead.

---

## Unpacking: spreading a collection at the call site

The same `*` and `**` symbols mean the opposite when used in a *call*: they spread a collection into individual arguments. `*` unpacks an iterable into positional arguments; `**` unpacks a mapping into keyword arguments.

```python
def point(x, y, z):
    return (x, y, z)

coords = [1, 2, 3]
point(*coords)                     # same as point(1, 2, 3)

params = {"x": 1, "y": 2, "z": 3}
point(**params)                    # same as point(x=1, y=2, z=3)
```

This is how you forward arguments from one function to another, a pattern you will see constantly in wrappers and decorators:

```python
def retry(func, *args, **kwargs):
    for _ in range(3):
        try:
            return func(*args, **kwargs)     # spread them back into func
        except Exception:
            continue
    raise RuntimeError("all attempts failed")
```

**The gotcha:** packing and unpacking share the `*`/`**` syntax but are distinguished by *position*. In a `def` header, the star means "collect into." In a call, it means "spread out from." Reading `f(*items)` as packing (or `def f(*items)` as spreading) is a frequent misreading — the location tells you which is which.

---

## Keyword-only arguments

A bare `*` in a signature marks a boundary: every parameter *after* it can only be passed by keyword, never by position. This is invaluable for optional flags whose meaning would be opaque as a positional `True`.

```python
def export(data, *, format="json", overwrite=False):
    return f"exporting {len(data)} rows as {format}, overwrite={overwrite}"

export([1, 2, 3], format="csv", overwrite=True)   # ok
export([1, 2, 3], "csv")                           # TypeError: too many positional args
```

Forcing `format` and `overwrite` to be keywords means a call site can never read as the cryptic `export(data, "csv", True)`. The reader always sees the parameter names.

---

## Positional-only arguments (PEP 570)

The mirror image, added in Python 3.8: a `/` in the signature marks every parameter *before* it as positional-only — callers cannot pass those by name. This is useful when a parameter name is an implementation detail you want the freedom to rename, or to match the behavior of built-ins like `len` and `pow`.

```python
def divide(a, b, /):
    return a / b

divide(10, 2)          # 5.0
divide(a=10, b=2)      # TypeError: got some positional-only arguments passed as keyword
```

You can combine both markers in one signature to precisely control each parameter's calling convention. Everything before `/` is positional-only, everything after `*` is keyword-only, and anything between them can be passed either way.

```python
def clamp(value, /, low=0, *, high=100):
    return max(low, min(value, high))

clamp(150)                     # 100  (value positional, high keyword-only)
clamp(150, 10, high=90)        # 90   (low passed positionally)
```

**The gotcha:** `/` and `*` are markers, not parameters — you never pass a value for them. `/` closes the positional-only group (it comes *after* those parameters); `*` opens the keyword-only group (it comes *before* those parameters). Left to right, a full signature reads: positional-only, `/`, normal, `*`, keyword-only.

---

## Type-annotated signatures

You can annotate parameters and return values with their expected types. Annotations are documentation and tooling hints — Python does not enforce them at runtime — but they make signatures far easier to read and let tools like `mypy` catch mistakes before you run the code.

```python
def repeat(text: str, times: int = 2) -> str:
    return text * times

repeat("ab", 3)     # 'ababab'
```

The `times: int = 2` form combines an annotation and a default: the type comes first, the default after. We keep annotations light here; the full typing system (generics, `Optional`, protocols) is a topic of its own.

---

## Functions are first-class objects

In Python a function is an ordinary value. You can assign it to a variable, store it in a list or dict, pass it as an argument, and return it from another function. This is what makes callbacks, decorators, and higher-order functions possible.

```python
def shout(s):
    return s.upper()

def whisper(s):
    return s.lower()

# store functions in a dict and pick one at runtime
transforms = {"loud": shout, "quiet": whisper}
print(transforms["loud"]("hello"))     # 'HELLO'

# pass a function as an argument
def apply_twice(fn, value):
    return fn(fn(value))

print(apply_twice(shout, "hi"))        # 'HI'
```

A function that returns another function closes over the variables in scope where it was defined — the basis of factories and decorators:

```python
def multiplier(factor):
    def multiply(n):
        return n * factor          # 'factor' is captured from the enclosing call
    return multiply

triple = multiplier(3)
print(triple(10))                  # 30
```

---

## Docstrings

A string literal as the first statement in a function is its docstring: it documents the function's purpose and is available at runtime via `help()` and the `__doc__` attribute. Tools, IDEs, and the `@tool`-style schema extractors in agent frameworks all read it.

```python
def normalize(scores):
    """Scale a list of numbers to the 0..1 range.

    Returns a new list; the input is left unchanged. An empty
    input returns an empty list.
    """
    if not scores:
        return []
    low, high = min(scores), max(scores)
    span = high - low or 1          # avoid divide-by-zero when all equal
    return [(s - low) / span for s in scores]

print(normalize.__doc__.splitlines()[0])   # 'Scale a list of numbers to the 0..1 range.'
```

Write the first line as a short imperative summary, then add detail below after a blank line. This convention (PEP 257) is what documentation tools expect.

---

## Lambda, and when not to use it

`lambda` creates a small, anonymous function in a single expression. It is handy as a throwaway argument to functions like `sorted`, `map`, or `filter`.

```python
pairs = [("apple", 3), ("banana", 1), ("cherry", 2)]
pairs.sort(key=lambda pair: pair[1])       # sort by the second element
# [('banana', 1), ('cherry', 2), ('apple', 3)]
```

A lambda's body is limited to a single expression — no statements, no assignments, no multiple lines. That constraint is a feature: it keeps lambdas tiny.

**The gotcha:** don't assign a lambda to a name. Writing `add = lambda a, b: a + b` gives you a function whose repr is the unhelpful `<lambda>` and gains you nothing over `def add(a, b): return a + b`, which is clearer and shows a real name in tracebacks. Use `def` whenever the function has a name or does more than one trivial thing; reserve `lambda` for the inline, disposable case.

---

## Key takeaways

- **`return` produces a value; a function with no `return` yields `None`.** Printing is not returning — compute with `return` and let the caller display.
- **Keyword arguments make calls readable and order-independent**, but every argument after the first keyword must also be a keyword.
- **Default values are evaluated once, at definition time.** Never default to a mutable object; use `None` as a sentinel and build the real default in the body.
- **`*`/`**` pack in a definition and spread in a call** — position tells you which. `*args` is a tuple; `**kwargs` is a dict.
- **`*` and `/` shape the calling convention:** parameters after `*` are keyword-only, parameters before `/` are positional-only (PEP 570).
- **Functions are first-class values** — pass them, store them, return them — and `lambda` is only for the tiny, inline, unnamed case.

Master the signature and the rest of Python opens up: decorators, callbacks, and the tool schemas that agent frameworks build all rest on these same rules.

---

## Further reading

- [Defining Functions — the Python Tutorial](https://docs.python.org/3/tutorial/controlflow.html#defining-functions)
- [PEP 570 — Python Positional-Only Parameters](https://peps.python.org/pep-0570/)
