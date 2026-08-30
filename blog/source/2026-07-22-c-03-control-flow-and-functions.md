# Control Flow, Functions, and the Stack

*C's control flow is the ancestor of the syntax you already know — `if`, `while`, `for`, `switch`. Its functions look familiar too, but they hide a defining C fact: arguments are passed by value, always copied. Understanding pass-by-value, and the call stack that makes function calls work, is the bridge to the hardest and most important topic in C — pointers.*

We can compile a program and manipulate typed data. Now we structure it: branching, looping, and organizing code into functions. Most of this will feel familiar from other languages — C is where much of that syntax originated. But two things are distinctly C and set up everything ahead: functions copy their arguments, and every call lives on a stack. This post covers both.

## Control flow

C's control-flow constructs are the originals that Go, Java, and JavaScript inherited:

```c
if (x > 0) {
    puts("positive");
} else if (x == 0) {
    puts("zero");
} else {
    puts("negative");
}

for (int i = 0; i < n; i++) { /* ... */ }
while (condition) { /* ... */ }
do { /* runs at least once */ } while (condition);

switch (code) {
    case 200: puts("ok");    break;
    case 404: puts("gone");  break;
    default:  puts("other");
}
```

Two C-specific gotchas worth flagging. First, `switch` **falls through**: without a `break`, execution continues into the next case. This is occasionally useful (grouping cases) but a frequent bug — forget a `break` and you run code you didn't mean to. Second, C treats **any nonzero value as true** and zero as false; there was no `bool` until C99 (`<stdbool.h>`). This is why `if (x)` means "if x is nonzero," and why the classic typo `if (x = 5)` (assignment, not comparison) *compiles and is always true* — it assigns 5 to x, which is nonzero. Enable `-Wall` and the compiler warns you.

## Functions: declaration and definition

A C function has a return type, a name, typed parameters, and a body:

```c
int add(int a, int b) {   // definition
    return a + b;
}
```

Recall the declaration/definition split from post 1. Because C compiles top to bottom in one pass, a function must be *declared* before it's *called*. If `main` calls `add` before `add` appears in the file, you need a **function prototype** (a declaration) earlier — typically in a header:

```c
int add(int a, int b);    // prototype: declared, defined elsewhere/later
```

This is exactly the mechanism that lets C split a program across files: `.h` files hold prototypes so any `.c` can call functions defined in another `.c`, resolved at link time (post 1). `void` as a return type means "returns nothing"; `void` as the parameter list (`int main(void)`) means "takes no arguments" — and in C you should write `(void)`, not empty `()`, to *mean* no arguments explicitly.

## Pass-by-value: the crucial fact

Here is the single most important thing about C functions: **arguments are passed by value.** When you call a function, C *copies* each argument into the function's own parameters. The function operates on its copies; changes to them do not affect the caller's variables.

```c
void tryToModify(int x) {
    x = 99;              // modifies the LOCAL copy only
}

int main(void) {
    int n = 5;
    tryToModify(n);
    printf("%d\n", n);   // prints 5 — n is unchanged
    return 0;
}
```

`tryToModify` received a *copy* of `n`. Setting `x = 99` changed the copy, which vanishes when the function returns. This surprises newcomers who expect the caller's `n` to change. It doesn't, and it can't — not directly.

So how do C functions modify their caller's data (which they constantly need to do)? By passing the **address** of the variable — a pointer — so the function can reach back and modify the *original*. Pass-by-value is *why pointers are essential in C*: they're the mechanism for a function to affect something outside itself. That's the entire motivation for the next post. Everything about C's "why pointers?" starts here: because arguments are copied, you pass an address when you need to reach the original.

## Scope and lifetime

Where a variable is visible (scope) and how long it lives (lifetime) matter more in C than in garbage-collected languages, because C makes you manage them:

- **Local (automatic) variables** — declared inside a function or block. They're visible only within that block and live only until it exits. Crucially, they're stored on the *stack* (below) and are *not* initialized to zero by default — an uninitialized local holds garbage, and reading it is undefined behavior. Always initialize.
- **Global variables** — declared outside any function, visible across the file (or across files with `extern`), living for the whole program. Use sparingly; they're shared mutable state.
- **`static` locals** — a local variable marked `static` keeps its value *between calls* (its lifetime is the whole program, but its scope stays local). Useful for counters and caches.

The uninitialized-local trap is worth repeating because it's so common: `int x;` then reading `x` gives you whatever bits were on the stack — a real bug that may *appear* to work by luck. Make initialization a reflex.

## The call stack

Function calls in C are powered by the **call stack** — a region of memory that grows and shrinks as functions are called and return. Understanding it demystifies local variables, recursion, and a class of crashes.

When you call a function, C pushes a **stack frame** onto the stack: a block holding that call's parameters, its local variables, and the return address (where to resume in the caller). When the function returns, its frame is *popped* — instantly freeing all its locals. This is why local variables vanish on return, why they're fast (allocation is just moving a pointer), and why each recursive call gets its *own* copies of the locals (a fresh frame per call):

```c
long factorial(int n) {
    if (n <= 1) return 1;         // base case
    return n * factorial(n - 1);  // each call gets its own frame with its own n
}
```

Two consequences to carry forward. **Stack overflow**: because the stack is finite, too-deep recursion (or an accidental infinite recursion) exhausts it and crashes — the literal origin of the term. And a critical rule for the pointer posts ahead: **never return the address of a local variable.** Since its frame is popped on return, that address points to memory that's been reclaimed — a *dangling pointer* to a dead stack frame. Data that must outlive a function goes on the *heap* (post 6), not the stack. The stack is for the transient; the heap is for the lasting.

## Key takeaways

- C's control flow (`if`/`for`/`while`/`switch`) is the ancestor of modern syntax, with two gotchas: `switch` **falls through** without `break`, and C treats **any nonzero value as true** (so `if (x = 5)` compiles as an always-true assignment — use `-Wall`).
- Functions require **declaration before use** — a prototype (typically in a header) lets one `.c` call functions defined in another, resolved at link time; write `(void)` to explicitly mean "no parameters."
- **Arguments are passed by value** — C copies each argument, so a function modifying its parameter changes only its local copy, never the caller's variable; this is *why pointers exist*: to pass an address so a function can reach the original.
- **Locals aren't auto-initialized** (an uninitialized local holds garbage — undefined behavior to read), have block scope and stack lifetime, while `static` locals persist between calls — make initialization a reflex.
- The **call stack** pushes a frame (params, locals, return address) per call and pops it on return — explaining fast locals, per-call recursion state, **stack overflow** from too-deep recursion, and the rule to **never return the address of a local** (its frame is gone); lasting data belongs on the heap.

## Further reading

- [cppreference — C language functions](https://en.cppreference.com/w/c/language/functions)
- [cppreference — C language](https://en.cppreference.com/w/c/language)
