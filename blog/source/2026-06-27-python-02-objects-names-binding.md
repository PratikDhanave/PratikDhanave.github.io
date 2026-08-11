# The Data Model: Objects, Names, and Binding

*The single mental model that explains most of Python's surprises — everything is an object with an identity, a type, and a value; a name is a reference bound to an object, not a box that holds one; and assignment binds, it never copies.*

---

Most confusion in Python — "why did changing this list also change that one?", "why does `==` work but `is` doesn't?", "why does my function remember the last call?" — traces back to a single idea that other languages let you ignore. In Python, a variable is **not a container that holds a value**. It is a **name** that refers to an **object**. Assignment attaches a name to an object; it never copies the object. Once you internalize that, the surprises stop being surprises and start being predictions.

This post builds that model from the ground up: what an object actually is, what a name actually does, how to test for identity versus equality, and why the mutable-versus-immutable distinction is the hinge the whole thing turns on. The code is short on purpose — run each snippet yourself, because the point is to *see* the behavior, not to take my word for it.

---

## Everything is an object, and every object has three things

In Python, every value you can name — an integer, a string, a list, a function, a class, even a module — is an object. And every object carries exactly three properties, fixed for its lifetime except one:

- **Identity** — a unique, unchanging label for *this particular object*, readable via `id()`. Think of it as the object's address; no two live objects share it.
- **Type** — what kind of object it is, readable via `type()`. The type is fixed at creation and determines what the object can do.
- **Value** — the data the object holds. For some objects this can change (mutable); for others it never can (immutable).

```python
x = 256
print(id(x))     # e.g. 4304183024 — a unique integer for this object
print(type(x))   # <class 'int'>
print(x)         # 256
```

Identity and type are permanent. Value is the only one that *might* change, and whether it can is the single most important fact about any object you touch. Note that `id()` returns an implementation-defined number — in CPython it happens to be the memory address, but you should treat it purely as "an opaque identity token," never as an address you can do arithmetic on.

---

## A name is a reference, not a box

Here is the model that separates Python from languages like C, C++, Java (for primitives), or Go, where a variable names a *storage location* that holds a value. In those languages, `b = a` copies `a`'s bits into `b`'s box.

Python does not have boxes. A name is a **label tied to an object**. When you write `a = [1, 2, 3]`, Python creates one list object and points the name `a` at it. When you then write `b = a`, Python does **not** copy the list — it points a second name at the *same* object.

```python
a = [1, 2, 3]
b = a            # b is now another name for the SAME list object
print(id(a) == id(b))   # True — one object, two names

b.append(4)
print(a)         # [1, 2, 3, 4]  — a "changed" because a and b ARE the same list
```

Nothing was copied. `a` and `b` are two labels on one object, so a mutation seen through one label is visible through the other. This is the crux of the whole model. If you came from a value-semantics language, this is the exact spot where intuition betrays you — there, `b = a` followed by editing `b` would leave `a` untouched.

**The gotcha:** "assignment copies" is the wrong mental model and it will mislead you for years if you keep it. Assignment **binds a name to an object**. The right question is never "what value is in this variable?" but "which object does this name point at, and does anyone else point at it too?"

---

## Rebinding versus mutating

Two operations look similar on the page but are fundamentally different. **Rebinding** points a name at a *different* object. **Mutating** changes the object a name already points at.

```python
a = [1, 2, 3]
b = a

a = [9, 9, 9]    # REBIND: a now points at a brand-new list; b is untouched
print(b)         # [1, 2, 3]

a = b            # both names back on the same object
a.append(4)      # MUTATE: changes the shared object in place
print(b)         # [1, 2, 3, 4]  — b sees it
```

Rebinding (`a = something`) only ever affects the one name on the left. Mutating (`a.append(...)`, `a[0] = ...`, `a.sort()`) affects the object itself, and therefore *every* name pointing at it. Learning to read a line and instantly classify it — "is this rebinding a name or mutating an object?" — is most of the skill.

---

## `is` versus `==`: identity versus equality

Because names and objects are distinct, Python gives you two different comparisons, and they answer different questions:

- `==` asks **"do these two objects have equal values?"** — it calls the objects' `__eq__` method.
- `is` asks **"are these two names pointing at the exact same object?"** — it compares identity, equivalent to `id(x) == id(y)`.

```python
a = [1, 2, 3]
b = [1, 2, 3]    # a separate list that happens to hold equal values
c = a

print(a == b)    # True  — equal values
print(a is b)    # False — two distinct objects
print(a is c)    # True  — same object, two names
```

Reach for `==` almost always: you usually care whether two things are *equal*, not whether they are the *same object*. Reach for `is` only when identity is genuinely the question — and the canonical case is comparing against the singletons `None`, `True`, and `False`:

```python
if result is None:      # correct: there is exactly one None object
    ...
```

Use `is None`, never `== None`. `None` is a true singleton, so identity is the precise test — and it can't be fooled by a class that defines a misleading `__eq__`. The linters (`flake8`, `pylint`) will flag `== None` for exactly this reason.

**The gotcha:** never use `is` to compare values — numbers, strings, or freshly built collections. `x is 256` may print `True` on your machine and `False` for the same-looking value elsewhere, because whether two equal values are the *same object* depends on interning, which is an implementation detail (see below). (Python 3.8+ even emits a `SyntaxWarning` when you write `is` against a literal like `x is 256`, precisely because the result is unreliable.) If you want "same value," you want `==`. If you find yourself writing `is` against anything other than `None`/`True`/`False` (or a sentinel object you created on purpose), stop and reconsider.

---

## Interning: why `is` on small numbers "sometimes works"

You may discover by experiment that `is` *appears* to work on small integers, and conclude it's fine. It isn't — you've just stumbled onto an optimization.

```python
x = 256
y = 256
print(x is y)    # True  — but only because of interning

# Build the ints at runtime so the compiler can't fold them into one constant:
x = int("257")
y = int("257")
print(x is y)    # False in a script or function — two distinct int objects
```

Beware that this second result is not even stable across *how* you run the code: at an interactive REPL prompt, `x = 257` / `y = 257` on separate lines often prints `False`, but the identical lines inside a script or a function print `True`, because the compiler dedups equal literal constants within a single code block. That inconsistency is the whole point — the lesson is **never rely on interning**, and building the values at runtime (as above with `int("257")`) makes the demo behave the same everywhere.

CPython pre-creates and caches the integers from `-5` to `256` at startup, so every reference to `256` reuses one shared object. Ask for `257` twice and you may get two different objects. A similar caching happens for some short strings that look like identifiers ("string interning"):

```python
a = "hello"
b = "hello"
print(a is b)         # often True — compile-time interned

c = "".join(["h", "e", "l", "l", "o"])
print(a is c)         # often False — built at runtime, not interned
print(a == c)         # True — values are equal, which is what you actually care about
```

The lesson is not the boundaries of the cache — those are unspecified and vary by version and build. The lesson is: **interning is invisible and unreliable, so never let your program's correctness depend on it.** Compare values with `==`. The moment your code "works" because two equal values happen to be the same object, it is one Python release away from a baffling bug.

---

## Mutable versus immutable: the distinction that decides everything

Objects split into two camps, and which camp an object is in tells you whether the aliasing behavior above can bite you.

- **Immutable** objects can never change value after creation: `int`, `float`, `bool`, `str`, `bytes`, `tuple`, `frozenset`, and `None`. Any "modification" actually produces a new object.
- **Mutable** objects can change in place: `list`, `dict`, `set`, and most instances of your own classes.

```python
s = "abc"
print(id(s))
s += "d"          # NOT a mutation — builds a new string, rebinds s
print(id(s))      # different id: the original "abc" was never touched

nums = [1, 2, 3]
print(id(nums))
nums += [4]       # a real mutation — same object, extended in place
print(id(nums))   # same id
```

Watch what `+=` does: on the immutable string it silently rebinds `s` to a brand-new object; on the mutable list it mutates the existing object. Same operator, opposite consequences — driven entirely by whether the left operand is mutable.

Immutability is why sharing a string or a number between two names is always safe: nobody can change it out from under you, so aliasing is invisible. Sharing a list or dict is where aliasing becomes something you must *think* about.

| | Mutable (`list`, `dict`, `set`) | Immutable (`int`, `str`, `tuple`, `None`) |
|---|---|---|
| Can change in place? | Yes | No — operations return new objects |
| Aliasing can surprise you? | Yes — shared mutation is visible everywhere | No — safe to share freely |
| Usable as a `dict` key / `set` member? | No (unhashable) | Yes |
| Safe as a function default argument? | No — see below | Yes |

That "usable as a dict key" row is the practical payoff of immutability: dictionaries and sets require their keys to be hashable, and mutability and hashability are at odds, so only immutable objects (or objects that promise not to change their hash) qualify.

---

## The aliasing trap, and how to make a real copy

Because a bare assignment shares rather than copies, passing a mutable object around means every holder can mutate what the others see. When that is not what you want, make an explicit copy:

```python
original = [1, 2, 3]
shared = original           # NOT a copy — same object
independent = original[:]   # a shallow copy — a new list, same elements
also_copy = list(original)  # another shallow copy

original.append(4)
print(shared)        # [1, 2, 3, 4]  — followed along
print(independent)   # [1, 2, 3]     — genuinely separate
```

Note the word *shallow*. `original[:]` copies the outer list but not the objects inside it; if the list contains other lists, both copies still share those inner objects. When you need a fully independent clone all the way down, reach for `copy.deepcopy`. Choosing shallow versus deep is itself a design decision — shallow is cheaper and usually right; deep is for when nested mutation must be isolated.

---

## The mutable-default-argument trap (a preview)

One consequence of this model catches nearly everyone once. A function's default argument is evaluated **exactly once**, when the function is defined — not on each call. If that default is a mutable object, every call that relies on the default shares the *same* object, and mutations accumulate across calls:

```python
def add_item(item, basket=[]):     # the [] is created ONCE, at def time
    basket.append(item)
    return basket

print(add_item("a"))   # ['a']
print(add_item("b"))   # ['a', 'b']  — surprise: the same list persisted
```

The fix is the standard sentinel pattern — default to `None` (immutable, safe to share) and build a fresh object inside the function:

```python
def add_item(item, basket=None):
    if basket is None:             # note: `is None`, the correct identity test
        basket = []
    basket.append(item)
    return basket
```

This is the data model biting in a place people don't expect it — the default object is bound once and aliased across every call. The full treatment of argument passing and defaults belongs in the functions post; here it's enough to recognize *why* it happens: a mutable object, created once, shared by many calls.

---

## How this differs from value-semantics languages

If your background is C, C++, Go, or Java primitives, the reflex is "a variable is a box; assignment copies the bits into it." That model is correct there and wrong here. Python is uniformly reference-based: a name is a label, assignment re-labels, and nothing is copied unless you ask.

This is sometimes called "call by object reference" or "call by sharing," and it's why function arguments behave the way they do: passing an object to a function binds a new *local name* to the *same* object. Mutate the object inside the function and the caller sees it; rebind the local name inside the function and the caller does not. Same two rules — mutate versus rebind — applied across a function boundary. Once the object/name/binding model is solid, argument passing needs no new rules at all.

---

## Key takeaways

- **Everything is an object** with an identity (`id()`), a type (`type()`), and a value. Identity and type are fixed for life; value may or may not be.
- **A name is a reference, not a box.** Assignment *binds* a name to an object — it never copies. `b = a` gives one object two names.
- **Distinguish rebinding from mutating.** Rebinding (`a = ...`) moves one name; mutating (`a.append(...)`) changes the shared object and every name sees it.
- **`==` compares value; `is` compares identity.** Use `==` almost always; use `is` only for `None`/`True`/`False` and sentinels. `is None`, never `== None`.
- **Never rely on interning.** Small ints and some strings are cached, so `is` on equal values "sometimes works" — that's an implementation detail, not a guarantee.
- **Mutable versus immutable decides the danger.** Immutable objects are safe to share; mutable ones make aliasing something you must reason about. Copy explicitly (`[:]`, `list(...)`, `copy.deepcopy`) when you need independence.
- **The mutable default argument** is this model biting where you least expect it — default to `None` and build the object inside.

---

## Further reading

- [Python Language Reference — The standard type hierarchy and object model ("Data model")](https://docs.python.org/3/reference/datamodel.html) — the authoritative description of objects, identity, type, and value.
