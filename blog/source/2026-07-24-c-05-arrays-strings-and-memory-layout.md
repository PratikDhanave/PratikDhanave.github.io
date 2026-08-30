# Arrays, Strings, and Memory Layout

*Arrays and strings in C are where the pointer model from the last post becomes concrete — and where C's most infamous security bugs live. An array is a contiguous block of memory whose name decays to a pointer; a string is just an array of characters with a null terminator and no length field. Understanding both, and the buffer overflows they invite, is essential C literacy.*

Pointers gave us the mechanism; now we apply it to the two most-used aggregate types. Arrays and C strings look simple but hide subtleties — array-to-pointer decay, the invisible null terminator, the total absence of bounds checking — that cause real bugs and real vulnerabilities. This post makes the memory layout explicit so those subtleties stop surprising you.

## Arrays are contiguous memory

An **array** in C is a fixed-size, contiguous block of elements of the same type, laid out back-to-back in memory:

```c
int nums[5] = {10, 20, 30, 40, 50};
// memory:  [10][20][30][40][50]  — five ints, adjacent
printf("%d\n", nums[2]);   // 30
```

`nums[i]` accesses the i-th element (indices start at 0). The contiguity is the whole point: elements are exactly `sizeof(int)` apart, which is why the type-aware pointer arithmetic from the last post walks an array perfectly. In fact, `nums[i]` is *defined* as `*(nums + i)` — indexing is pointer arithmetic in disguise.

The critical, dangerous fact: **C does not check array bounds.** `nums[10]`, or `nums[-1]`, compiles and runs — it reads or writes whatever memory happens to be there, past the end of your array. There's no exception, no error; just silent access to memory you don't own (undefined behavior). This absence of bounds checking is the source of a huge fraction of C's security vulnerabilities, and it's on *you* to stay in range.

## Array-to-pointer decay

Here's the subtlety that confuses everyone learning C: in most contexts, **an array's name "decays" to a pointer to its first element.** When you use `nums` in an expression (or pass it to a function), you get `&nums[0]` — a pointer — not the array as a whole.

```c
int nums[5] = {10, 20, 30, 40, 50};
int *p = nums;        // legal: nums decays to &nums[0]
printf("%d\n", *p);       // 10
printf("%d\n", p[2]);     // 30 — pointers can be indexed too
```

This decay has a major consequence for functions: **you cannot pass an array by value.** When you write a function taking `int arr[]`, what it *actually* receives is a *pointer* (`int *`) — a copy of the address, not a copy of the elements. So the function can modify the caller's array (it has the address), and — crucially — it *does not know the array's length*, because a pointer carries no size information:

```c
void printAll(int *arr, size_t len) {   // MUST pass length separately
    for (size_t i = 0; i < len; i++) printf("%d ", arr[i]);
}
int nums[5] = {10, 20, 30, 40, 50};
printAll(nums, 5);                       // pass array (decays) + its length
```

This is why C functions taking arrays *always* take a separate length parameter — the array itself has forgotten how big it is the moment it decayed to a pointer. (A related trap: `sizeof(arr)` inside such a function gives the size of the *pointer*, not the array. `sizeof` on the array only works where the real array type is in scope.)

## C strings: null-terminated character arrays

C has no dedicated string type. A **string** is simply an array of `char` ending with a **null terminator** — the byte `'\0'` (value 0) — that marks where the string stops:

```c
char greeting[] = "hello";
// memory: ['h']['e']['l']['l']['o']['\0']  — SIX bytes, not five
```

The string literal `"hello"` is five characters plus an automatically-added `'\0'`, so it occupies six bytes. This trailing null is how every C string function knows where the string ends — there's *no separate length field*. `strlen("hello")` returns 5 by scanning from the start until it hits `'\0'`. Two consequences flow from this design:

- **Length is O(n), not O(1).** Because there's no stored length, finding a string's length means scanning for the terminator. Repeatedly calling `strlen` in a loop is a classic performance trap.
- **The terminator is load-bearing and easy to lose.** If a string's `'\0'` is missing or overwritten, string functions run off the end into adjacent memory until they *happen* to find a zero byte — reading garbage or crashing. Every operation that builds a string must ensure the terminator is present.

The standard string functions live in `<string.h>`: `strlen` (length), `strcpy`/`strncpy` (copy), `strcmp` (compare), `strcat`/`strncat` (concatenate), `strchr`/`strstr` (search). They all rely on the null terminator.

## Buffer overflows: C's signature vulnerability

Combine "no bounds checking" with "strings have no length field" and you get the **buffer overflow** — writing past the end of a buffer into adjacent memory — the most notorious class of C bug and a foundational security vulnerability:

```c
char buf[8];
strcpy(buf, "this string is way too long");  // DISASTER: writes past buf[7]
```

`strcpy` copies until it hits the source's null terminator, with *no idea* that `buf` only holds 8 bytes. It happily writes past the end, corrupting whatever is next in memory — other variables, the function's return address on the stack, anything. At best it crashes; at worst, an attacker who controls the input can overwrite the return address and hijack execution (the classic "stack smashing" exploit). This single pattern is behind decades of security incidents.

The defenses are discipline, since the language won't help:

- **Use the bounded variants** — `strncpy`, `strncat`, `snprintf` — which take a maximum length and won't write past it. (Note `strncpy` has its own trap: it may *not* null-terminate if the source fills the buffer, so terminate manually.)
- **Always size buffers for content plus the terminator**, and track how much space remains.
- **Validate input length** before copying into a fixed buffer — never trust that input fits.

Modern C treats "never call an unbounded string function on untrusted input" as a firm rule. The vulnerability is inherent to the null-terminated, unchecked design; safety comes entirely from the programmer.

## The memory-layout view

Pulling it together, arrays and strings make C's memory model tangible: data is bytes laid out contiguously, an array name is really the address of the first byte, indexing is pointer arithmetic, and a string is that same byte array with a sentinel `'\0'` marking its end. Nothing tracks sizes for you — not array bounds, not string length — so you carry that information yourself (a length parameter, a known buffer size) and the discipline to stay within it. This is C's bargain in miniature: total control over memory layout, total responsibility for using it safely. The dynamic-memory post next takes this a step further, letting you allocate arrays whose size you decide at runtime — with the same responsibility, now including freeing what you allocate.

## Key takeaways

- An **array is contiguous memory** of same-type elements; `nums[i]` is defined as `*(nums + i)` (indexing *is* pointer arithmetic), and C performs **no bounds checking** — out-of-range access silently reads/writes memory you don't own.
- An array name **decays to a pointer** to its first element in most contexts, so you **can't pass an array by value** — functions receive a pointer (which carries no size), which is why C array functions **always take a separate length parameter** (and `sizeof` inside them measures the pointer, not the array).
- A **C string is a `char` array ending in a null terminator `'\0'`** with no separate length field — `"hello"` is 6 bytes — so `strlen` is O(n) (it scans for the terminator) and losing the terminator sends string functions running off the end.
- **Buffer overflows** — writing past a buffer's end because nothing checks bounds or length — are C's signature vulnerability (crashes at best, execution hijacking at worst); `strcpy` on oversized input is the classic trigger.
- Defend with **bounded functions** (`strncpy`, `snprintf`), sizing buffers for content **plus terminator**, and validating input length — the language provides no safety, so it's entirely the programmer's discipline.

## Further reading

- [cppreference — Array declarations](https://en.cppreference.com/w/c/language/array)
- [cppreference — Null-terminated byte strings](https://en.cppreference.com/w/c/string/byte)
