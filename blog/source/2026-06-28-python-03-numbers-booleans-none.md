# Numbers, Booleans, and None

*A working guide to Python's scalar types — arbitrary-precision integers, IEEE-754 floats and the 0.1 + 0.2 trap, when to reach for Decimal and Fraction, the operators that surprise you with negatives, why a boolean is secretly an integer, and how truthiness and None actually work.*

---

Most of the values a Python program moves around are scalars: a count, a price, a ratio, a flag, an "I don't have a value yet." Python gives you a small, sharp set of built-in types for these — `int`, `float`, `complex`, `bool`, and the singleton `None` — plus two precision-focused types in the standard library, `decimal.Decimal` and `fractions.Fraction`. The types are easy to name and easy to misuse. This guide is about the second part: the places where the obvious code quietly gives the wrong answer, and the idioms that keep you out of trouble.

Everything here is standard Python 3 (3.9+). No third-party packages.

---

## Integers don't overflow

Python's `int` has **arbitrary precision**. It is not a 32- or 64-bit machine word that wraps around at some maximum; it grows to hold whatever value you give it, limited only by memory. This is one of the genuinely pleasant things about the language — a whole category of bugs from C, Java, and Go simply does not exist here.

```python
x = 2 ** 100
print(x)                # 1267650600228229401496703205376
print(x * x)            # a 60-digit number, still exact
import math
print(math.factorial(50))   # 65-digit integer, no overflow, no rounding
```

There is no `MAX_INT` to guard against. A loop counter, a hash, a running total of integers — all exact, always.

**The gotcha:** the freedom is real for `int`, but the moment a value passes through `float` it inherits float's limits. `10**23` is an exact integer; `float(10**23)` is not, because it can no longer be represented exactly in a double (it exceeds 2^53), even though it's well within the range. Integer *division* with `/` also drops you into float land (see below). So arbitrary precision is a property of the `int` type, not a property of "numbers in Python" — keep the value an `int` and it stays exact.

---

## Floats are IEEE-754 doubles, and 0.1 + 0.2 is not 0.3

A Python `float` is a 64-bit IEEE-754 double — the same representation used by essentially every language's default floating-point type. It stores numbers in **binary**, and most decimal fractions have no exact binary representation, the same way 1/3 has no exact decimal representation. The result is the single most famous surprise in all of programming:

```python
print(0.1 + 0.2)              # 0.30000000000000004
print(0.1 + 0.2 == 0.3)      # False
```

Nothing is broken. `0.1`, `0.2`, and `0.3` are each stored as the nearest available double, and the tiny errors don't cancel. This is not Python-specific; it is how binary floating point works everywhere.

The correct way to compare floats is *approximately*, with `math.isclose`, never `==`:

```python
import math
print(math.isclose(0.1 + 0.2, 0.3))   # True
```

Floats also carry a few special values worth recognizing: `float('inf')`, `float('-inf')`, and `float('nan')` (not-a-number). `nan` has a property that trips people up — it is not equal to anything, *including itself*:

```python
nan = float('nan')
print(nan == nan)          # False
print(math.isnan(nan))     # True  — this is how you test for it
```

**The gotcha:** never test floats with `==`, and never test for `nan` with `x == float('nan')` — that is always `False`. Use `math.isclose(a, b)` for equality and `math.isnan(x)` for nan. And do not accumulate money, tax, or any exact-decimal quantity in floats — the errors are small individually but they compound, and "off by a cent" is a real bug.

---

## Money belongs in Decimal

Because floats can't represent `0.10` exactly, they are the wrong tool for currency. The standard library's `decimal.Decimal` stores numbers in **base 10**, so the values you type are the values you get, and you control rounding explicitly.

```python
from decimal import Decimal

# The float trap, in a form that costs real money:
print(0.1 + 0.2 + 0.3)                          # 0.6000000000000001

# Decimal keeps decimal values exact:
print(Decimal("0.1") + Decimal("0.2") + Decimal("0.3"))   # 0.6
```

One rule matters above all: **construct `Decimal` from a string, not a float.** `Decimal(0.1)` faithfully captures the float's error and hands it right back to you; `Decimal("0.1")` is exactly one tenth.

```python
print(Decimal(0.1))       # 0.1000000000000000055511151231257827021181583404541015625
print(Decimal("0.1"))     # 0.1
```

Rounding is explicit and controllable, which is exactly what accounting requires:

```python
from decimal import Decimal, ROUND_HALF_UP

price = Decimal("19.99")
tax = price * Decimal("0.075")                        # 1.49925
total = (price + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
print(total)                                          # 21.49
```

**The gotcha:** `Decimal(0.1)` and `Decimal("0.1")` are different numbers — always quote the literal. Decimal is slower than float and is the right default for money, billing, and anything where a human will audit the cents; it is the wrong default for scientific computing, where float is faster and precision-to-the-penny is not the point.

---

## Exact ratios belong in Fraction

When you need exact rational arithmetic — thirds, sevenths, repeating fractions that both float and Decimal round — `fractions.Fraction` stores a numerator and denominator as integers and keeps them exact.

```python
from fractions import Fraction

third = Fraction(1, 3)
print(third + third + third)      # 1  (exact — no 0.9999… )
print(Fraction(1, 10) + Fraction(2, 10))   # 3/10, exact

# Fractions auto-reduce to lowest terms:
print(Fraction(6, 8))             # 3/4
```

Fraction is the honest answer when the *ratio* is the truth and any decimal expansion is a lie. It interoperates with `int` cleanly and is invaluable in exact-math contexts — probability, unit conversions with awkward factors, geometry — where accumulated rounding would drift.

---

## complex is built in

Python has native complex numbers, written with a `j` suffix on the imaginary part. You rarely need them outside signal processing, control systems, and some math-heavy code, but they're a first-class built-in, not a library:

```python
z = 2 + 3j
print(z.real, z.imag)     # 2.0 3.0
print(abs(z))             # 3.605551275463989  (magnitude)
print(z * (1 - 1j))       # (5+1j)
```

The components are floats, so complex numbers inherit float's precision characteristics.

---

## The operators: `/` vs `//` vs `%`, and the negatives twist

Three division-family operators behave differently, and the difference matters:

```python
print(7 / 2)      # 3.5   true division  → ALWAYS a float, even for 8 / 2
print(7 // 2)     # 3     floor division → rounds toward negative infinity
print(7 % 2)      # 1     modulo         → the remainder
print(2 ** 10)    # 1024  exponentiation
```

`/` always produces a float — `8 / 2` is `4.0`, not `4`. `//` gives the floor, and `%` gives the remainder. For positive operands they behave the way school arithmetic taught you. The surprise is **negative operands**, where Python differs from C, Java, and Go.

Python's `//` rounds *toward negative infinity* (floor), not toward zero (truncation), and its `%` follows the sign of the **divisor**:

```python
print(-7 // 2)    # -4   (floor of -3.5, NOT -3)
print(-7 % 2)     # 1    (result takes the divisor's sign → positive)
print(7 % -2)     # -1   (divisor negative → result negative)
```

The invariant that ties them together always holds: `(a // b) * b + (a % b) == a`. Python guarantees `a % b` has the same sign as `b`, which is genuinely useful — `-1 % 12` is `11`, so modulo does clock/wraparound arithmetic correctly without an extra `+ n) % n` dance. If you want C-style truncation-and-remainder instead, `math.fmod` and `math.trunc` give it to you.

**The gotcha:** `-7 // 2` is `-4`, not `-3`, because Python floors instead of truncating, and `-7 % 2` is `1`, not `-1`, because the result matches the divisor's sign. If you're porting an algorithm from a language that truncates, the negative cases will silently disagree. And keep in mind `/` always returns a float, so `10 / 2` is `5.0` — use `//` when you want an integer result.

---

## bool is a subclass of int

Here is the one that catches everyone eventually: **`bool` is a subclass of `int`.** `True` *is* the integer `1` and `False` *is* the integer `0`, not merely equal to them — they participate in arithmetic:

```python
print(True == 1)          # True
print(False == 0)         # True
print(True + True)        # 2
print(isinstance(True, int))   # True
```

This is occasionally a feature. Summing an iterable of booleans counts how many are true — a clean idiom:

```python
votes = [True, False, True, True, False]
print(sum(votes))         # 3  — counts the Trues
```

But it's also a source of quiet bugs, because a bool works anywhere an int does — including as a **sequence index** and a **dict key**:

```python
data = ["zero", "one"]
flag = True
print(data[flag])         # "one"  — True indexed as 1, probably not intended

d = {0: "a", False: "b"}  # collapses to ONE key, because 0 == False
print(d)                  # {0: 'b'}  — the second entry overwrote the first
```

**The gotcha:** because `True == 1` and `False == 0` as genuine integers, a boolean silently indexes sequences and collides with `0`/`1` as a dict key — `{True: "x", 1: "y"}` has a single entry. Summing bools to count truthy items is a deliberate, readable idiom; using a bool as an index or key almost never is. When you mean a flag, branch on it (`if flag:`); don't arithmetic with it unless counting is the actual intent.

---

## Truthiness: what counts as false

Every Python object has a truth value, so `if x:` works on any object, not just booleans. The set of **falsy** values is small and worth memorizing — everything else is truthy:

- `False`, `None`
- zero of any numeric type: `0`, `0.0`, `0j`, `Decimal(0)`, `Fraction(0)`
- empty containers and sequences: `""`, `[]`, `{}`, `()`, `set()`, `range(0)`

```python
for value in [0, 0.0, "", [], {}, None, "no", [0], " "]:
    print(repr(value), "→", bool(value))
# 0 → False, 0.0 → False, '' → False, [] → False, {} → False, None → False,
# 'no' → True, [0] → True, ' ' → True
```

Note the last three: the string `"no"` is truthy (any non-empty string is), `[0]` is truthy (a non-empty list, even though its one element is falsy), and `" "` — a single space — is truthy. Emptiness, not content, decides.

The idiomatic way to test a container is to lean on truthiness directly:

```python
items = []
if not items:             # idiomatic — empty list is falsy
    print("nothing here")

# Prefer this over len(items) == 0 or items == []
```

**The gotcha:** truthiness and identity are different questions, and conflating them causes real bugs. `if x:` is false for `0`, `0.0`, `""`, and `[]` — so a function argument that legitimately might be `0` or `""` gets mishandled if you write `if not x: x = default`. When you specifically mean "was no value supplied," test `if x is None:`, not `if not x:` — the next section is exactly about that distinction.

---

## None is the one true null

`None` is Python's null: a single sentinel object meaning "no value." It is the default return of a function that doesn't `return` anything, the natural "not set yet" placeholder, and the conventional signal for "absent." Crucially, there is **exactly one** `None` in a running program — it's a singleton — so you test for it with **identity** (`is`), not equality (`==`):

```python
def find_user(user_id):
    ...
    return None           # convention: "no such user"

result = find_user(42)
if result is None:        # correct — identity check
    print("not found")
```

Why `is None` and never `== None`? Two reasons. First, there is only one `None`, so identity is the precise question and it's faster. Second, `==` can be overridden — a class can define `__eq__` to return `True` when compared to `None` (or to raise), so `== None` is not guaranteed to mean what you think. `is` checks object identity and cannot be fooled.

This also drives the standard "optional argument" pattern. You cannot use a mutable default like `[]` safely (it's shared across calls), so `None` is the sentinel:

```python
def append_to(item, target=None):
    if target is None:        # fresh list per call
        target = []
    target.append(item)
    return target
```

**The gotcha:** always compare to `None` with `is` / `is not`, never `==`. And don't collapse "is None" into "is falsy": `0`, `0.0`, `""`, and `[]` are all falsy but are *not* `None`. `if not count:` fires when `count` is `0`; `if count is None:` fires only when no count was supplied. Choose the one that matches the question you're actually asking.

---

## Numeric literals: underscores and other bases

Two small conveniences make numeric code more readable. First, you can put **underscores** between digits as visual separators — the interpreter ignores them entirely:

```python
budget = 1_000_000            # same as 1000000, easier to read
pi_ish = 3.141_592_653
card = 0xFF_FF_FF             # grouping works in any base
```

Second, integer literals can be written in other bases with a prefix: `0x` for hexadecimal, `0o` for octal, `0b` for binary. These are just alternate spellings of ordinary ints — the value is identical, only the source form differs:

```python
print(0xFF)       # 255   hex
print(0o17)       # 15    octal
print(0b1010)     # 10    binary
print(0xFF == 255)   # True — same int, different notation
```

You can go the other direction with `hex()`, `oct()`, `bin()`, or with formatted strings (`f"{255:#x}"` → `0xff`). The base is a presentation choice; the underlying value is one arbitrary-precision integer.

**The gotcha:** underscores are cosmetic and must sit *between* digits — `1_000` is fine, but a leading, trailing, or doubled underscore (`_100`, `100_`, `1__0`) is a syntax error. The base prefixes only apply to integer literals, and they produce plain ints, so `0b1010` and `10` are the same object-equal value — the prefix buys readability, not a new type.

---

## Quick reference: which numeric type when

| You need | Use | Why |
|---|---|---|
| Counting, indexing, exact integers | `int` | Arbitrary precision, never overflows |
| General real-number math, science | `float` | Fast IEEE-754 double; use `math.isclose` to compare |
| Money, billing, anything audited to the cent | `Decimal` | Base-10 exact; explicit rounding — build from strings |
| Exact ratios, repeating fractions | `Fraction` | Keeps numerator/denominator exact, auto-reduces |
| Complex-plane math | `complex` | Native `j` literals; components are floats |
| A yes/no flag | `bool` | But remember it *is* an int |
| "No value" / "not set" | `None` | Unique sentinel; test with `is None` |

---

## Key takeaways

- **`int` never overflows, but `float` does have limits** — arbitrary precision is a property of the integer type, and it's lost the moment a value becomes a float.
- **`float` is binary IEEE-754**, so `0.1 + 0.2 != 0.3`. Compare with `math.isclose`, test nan with `math.isnan`, and never accumulate money in floats.
- **Reach for `Decimal` for money** (built from *strings*) and `Fraction` for exact ratios — both trade speed for exactness where exactness is the requirement.
- **`//` floors and `%` follows the divisor's sign**, so negatives differ from C/Java; `/` always returns a float.
- **`bool` is a subclass of `int`** — summing bools counts truths (a feature), but using a bool as an index or dict key is usually a bug.
- **Learn the falsy set** (`0`, `0.0`, `""`, `[]`, `{}`, `None`, …) and don't confuse "falsy" with "is `None`" — a `0` or `""` value is falsy but present.
- **`None` is a singleton sentinel** — always test it with `is None`, never `== None`, and use it as the safe default for optional arguments.

The through-line: Python's scalar types each make a promise — `int` promises exactness, `float` promises speed, `Decimal` promises decimal fidelity, `None` promises "nothing." Bugs come from asking a type to keep a promise it never made. Match the type to the promise you need and most of the surprises above disappear.

---

## Further reading

- [Built-in Types](https://docs.python.org/3/library/stdtypes.html) — the numeric types, boolean operations, truth-value testing, and `None` in the official Python documentation.
- [`decimal` — Decimal fixed-point and floating-point arithmetic](https://docs.python.org/3/library/decimal.html) — the module docs, including construction rules, rounding modes, and context precision.
