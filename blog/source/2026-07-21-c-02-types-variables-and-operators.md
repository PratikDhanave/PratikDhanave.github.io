# Types, Variables, and Operators

*In C, a type is a promise about how many bytes a value occupies and how to interpret them. There's no hidden bignum, no automatic string, no safety rail — just fixed-width integers, floating-point, and the bit patterns underneath. Understanding C's types means understanding sizes, signedness, and the surprising rules of integer promotion, because in C the difference between `int` and `unsigned` can be the difference between correct and catastrophically wrong.*

The previous post compiled a program; now we look at the data it manipulates. C's type system is small and low-level: it's fundamentally about *how many bytes* a value takes and *how those bytes are interpreted*. This post covers the primitive types, their sizes and limits, the signed/unsigned distinction, and the integer-promotion rules that cause some of C's most notorious bugs.

## Types are about bytes

In a language like Python, an integer is an arbitrary-precision object. In C, an integer is a **fixed number of bytes** interpreted as a number. That's the mental shift: a C type tells the compiler *how much memory* to reserve and *how to read the bits*. The primitive types:

- **Integer types:** `char`, `short`, `int`, `long`, `long long` — increasing (or equal) in size. Plus `unsigned` variants of each.
- **Floating point:** `float` (single precision), `double` (double precision).
- **`char`** — one byte, used both for characters (via their numeric codes) and as the smallest integer.
- **`_Bool`** (via `<stdbool.h>` as `bool`) — true/false, added in C99.
- **`void`** — "no type," used for functions that return nothing and (crucially, later) for generic pointers.

A defining C quirk: **the sizes are not fixed by the language.** The standard guarantees only *minimums* and relative ordering (an `int` is at least 16 bits, a `long` at least 32, `long long` at least 64, and `char ≤ short ≤ int ≤ long`). On a typical modern platform `int` is 4 bytes and `long` is 8, but this varies. This is why portable C never assumes `int` is 4 bytes.

## Knowing the exact size and limits

Because sizes vary, C gives you tools to ask. The `sizeof` operator returns a type's size in bytes, and headers expose the limits:

```c
#include <stdio.h>
#include <limits.h>   // INT_MAX, INT_MIN, etc.
#include <stdint.h>   // fixed-width types

int main(void) {
    printf("int is %zu bytes\n", sizeof(int));
    printf("int max is %d\n", INT_MAX);

    int32_t exactly_32_bits = 1000000;   // guaranteed 32 bits, everywhere
    printf("%d\n", exactly_32_bits);
    return 0;
}
```

When you need a *guaranteed* width, use the **fixed-width types** from `<stdint.h>`: `int8_t`, `int16_t`, `int32_t`, `int64_t` and their `uint` counterparts. Modern C code that cares about exact sizes (protocols, file formats, hardware registers) uses these instead of the platform-dependent built-ins. It's a good default habit when precision matters.

## Signed vs. unsigned: a real hazard

Every integer type is either **signed** (can hold negatives) or **unsigned** (only non-negatives, but roughly double the positive range). This isn't a minor detail — it's a source of serious bugs, because the two behave very differently at their boundaries and *mixing* them triggers surprising conversions.

The classic trap:

```c
unsigned int u = 0;
if (u - 1 > 0) {           // TRUE — and probably not what you meant
    // u - 1 is not -1; it wraps to UINT_MAX (a huge positive number)
}

int  a = -1;
unsigned int b = 1;
if (a < b) { /* ... */ }   // a is converted to a huge UNSIGNED value; the
                           // comparison is likely FALSE, contradicting intuition
```

Unsigned arithmetic *wraps around* (modular arithmetic) rather than going negative — `0u - 1` is the largest unsigned value, not `-1`. And when you compare or combine a signed and an unsigned value, C converts the signed one *to* unsigned, so `-1` becomes an enormous positive number. This is why `size_t` (an unsigned type returned by `sizeof` and used for sizes/indices) in a loop counting *down* past zero is a famous infinite-loop bug. The lesson: know the signedness of your values, avoid mixing signed and unsigned in comparisons, and enable `-Wsign-compare` (part of `-Wextra`) to be warned.

## Integer promotion and conversion

C automatically converts between numeric types in expressions, following the **usual arithmetic conversions** — rules that are mostly invisible until they bite. The key ones:

- **Integer promotion:** types smaller than `int` (`char`, `short`) are promoted to `int` before arithmetic. So `char a = 100, b = 100; a + b` is computed as `int` (200), not as an overflowed `char`.
- **Common type:** in a binary operation, both operands are converted to a common type — generally the larger, and (as above) unsigned wins ties with signed of the same rank.
- **Truncation on assignment:** assigning a wider value to a narrower type *truncates* — `int x = 300; char c = x;` silently discards the high bits. No error, just wrong data.

These conversions are why C arithmetic sometimes produces baffling results, and why understanding your types' sizes and signedness (the earlier sections) is not academic. The rules are consistent, but they're not intuitive, and the compiler applies them silently.

## Operators and the "everything is bits" view

C has the arithmetic (`+ - * / %`), comparison (`== != < >`), and logical (`&& || !`) operators you'd expect, plus a set that reveals C's low-level nature: the **bitwise operators**. Because C exposes the actual bits, you can manipulate them directly:

- `&` (AND), `|` (OR), `^` (XOR), `~` (NOT) — operate bit by bit.
- `<<` and `>>` — shift bits left/right (a left shift by *n* multiplies by 2ⁿ, a fast and common idiom).

```c
unsigned int flags = 0;
flags |= (1u << 2);          // set bit 2
if (flags & (1u << 2)) { }   // test bit 2
flags &= ~(1u << 2);         // clear bit 2
```

This bit-twiddling — setting flags, packing data, masking — is everyday C, used in systems programming, protocols, and embedded work where you control individual bits of hardware registers. It's a direct expression of C's core idea: values are bit patterns, and you can operate on them at that level. A couple of caveats that connect to earlier sections: shifting a signed negative value or shifting by more than the type's width is undefined behavior (post 8), which is one more reason to use `unsigned` types for bit manipulation.

## Key takeaways

- In C a **type is a promise about byte-size and interpretation** — fixed-width integers and floats, no arbitrary-precision or hidden objects — so `sizeof` tells you the size and the mental model is "how many bytes, read how."
- **Type sizes aren't fixed by the language** (only minimums and ordering are guaranteed); use **`<stdint.h>` fixed-width types** (`int32_t`, `uint64_t`) when you need a guaranteed width for protocols, formats, or hardware.
- **Signed vs. unsigned is a real hazard**: unsigned arithmetic *wraps* (`0u - 1` is huge, not `-1`), and mixing signed/unsigned converts the signed operand to unsigned — a classic source of wrong comparisons and infinite `size_t` loops. Enable `-Wsign-compare`.
- **Integer promotion and conversions happen silently**: small types promote to `int` in arithmetic, operands convert to a common type, and assigning to a narrower type *truncates* — consistent rules, but unintuitive and applied without warning.
- C's **bitwise operators** (`& | ^ ~ << >>`) expose the actual bits for flags, masking, and packing — everyday systems/embedded C — reflecting C's core "values are bit patterns" model (use unsigned types to avoid shift-related undefined behavior).

## Further reading

- [cppreference — Arithmetic operators (conversions and promotion)](https://en.cppreference.com/w/c/language/operator_arithmetic)
- [cppreference — C language](https://en.cppreference.com/w/c/language)
