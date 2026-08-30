# Dynamic Memory Management

*Stack memory is automatic but rigid — sized at compile time and gone when a function returns. For data whose size you only know at runtime, or that must outlive the function that created it, C gives you the heap and four functions to manage it: `malloc`, `calloc`, `realloc`, and `free`. With that power comes C's heaviest responsibility: every allocation you make, you must free — exactly once, and never use again.*

Post 3 introduced the stack; post 5 built arrays whose size was fixed at compile time. But real programs need memory whose size is decided at runtime (a buffer for a file of unknown length, an array that grows) and memory that survives past the function that created it. That's the **heap**, and managing it manually is the defining responsibility — and the defining hazard — of C. This post covers how, and the bug classes you must avoid.

## Stack vs. heap

C programs use two regions of memory, and choosing correctly is fundamental:

- **The stack** (post 3) — automatic, fast, and scoped. Local variables live here; allocation is just moving the stack pointer; everything is freed automatically when the function returns. But it's *rigid*: sizes must be known at compile time, and data can't outlive its function (returning a pointer to a local is the dangling-pointer bug from post 3).
- **The heap** — a large pool of memory you allocate from *explicitly* at runtime and must free *explicitly*. It's flexible (any size, decided at runtime; lives until you free it) but manual (you own every byte's lifecycle) and slower (allocation involves bookkeeping).

The rule of thumb: use the stack for small, fixed-size, function-local data (the default — it's free and automatic), and the heap when you need runtime-determined size or data that outlives its creating function. The heap is where dynamic data structures (post 7) live, because their size grows and shrinks as the program runs.

## The four functions

Heap memory is managed through `<stdlib.h>`:

```c
#include <stdlib.h>

int *arr = malloc(n * sizeof(int));   // allocate space for n ints (uninitialized)
if (arr == NULL) { /* allocation failed — handle it */ }

int *zeroed = calloc(n, sizeof(int)); // allocate AND zero-initialize n ints

arr = realloc(arr, 2 * n * sizeof(int)); // resize the block (grow/shrink)

free(arr);      // return the memory to the heap when done
arr = NULL;     // defensive: avoid a dangling pointer
```

- **`malloc(size)`** — allocates `size` bytes and returns a pointer to them (or `NULL` on failure). The memory is **uninitialized** — it contains garbage until you write to it.
- **`calloc(count, size)`** — allocates `count * size` bytes *and zeroes them*. Use it when you want zero-initialized memory (and it safely handles the multiplication overflow that `malloc(count * size)` risks).
- **`realloc(ptr, newsize)`** — resizes an existing block, preserving its contents; it may move the block (returning a new address), so always assign its result back (and to a *temporary* first — see the leak trap below).
- **`free(ptr)`** — returns a block to the heap. After this, the pointer is *dangling* and must not be used.

Two habits from the start: **always check `malloc`/`realloc` for `NULL`** (allocation can fail, especially for large requests), and **`sizeof` the type** in the size calculation so it stays correct across platforms.

## Ownership: the mental model that saves you

C has no garbage collector, so *someone* must free every allocation — and C won't tell you who. The discipline that makes this tractable is **ownership**: for every heap allocation, decide which piece of code is responsible for freeing it, and make that responsibility clear.

Ownership questions run through all C API design: When a function returns a `malloc`'d pointer, does the *caller* now own it (and must free it)? When you store a pointer in a struct, who frees it — and when? Answer these deliberately, document them, and the manual memory management becomes manageable. Most memory bugs are really *ownership* confusion — two places both free it, or neither does. Think in terms of "who owns this and when does its life end," and match every `malloc` with exactly one `free` on every path.

## The four deadly bugs

Manual memory management creates four notorious bug classes. Recognizing them is half of avoiding them:

- **Memory leak** — you allocate but never `free`. The memory is lost for the program's lifetime; in a long-running server, leaks accumulate until it exhausts memory and dies. Leaks are *silent* — the program works, then slowly starves. The realloc trap is a common cause: `p = realloc(p, n)` leaks the original block if realloc *fails* and returns `NULL` (you've overwritten the only pointer to it), so realloc into a *temporary* and check it first.
- **Dangling pointer / use-after-free** — using a pointer *after* its memory was freed. The block may have been reused for something else, so you read or corrupt unrelated data — a bug that's intermittent and can be a security vulnerability. Defense: set pointers to `NULL` after freeing, so a mistaken use crashes loudly instead of corrupting silently.
- **Double free** — calling `free` twice on the same pointer, which corrupts the heap's internal bookkeeping and often crashes later, far from the cause. Setting the pointer to `NULL` after freeing helps here too (`free(NULL)` is safe and does nothing).
- **Buffer overflow on the heap** — the same out-of-bounds writes from post 5, now in heap memory: allocate 8 bytes, write 16, and you corrupt adjacent heap blocks. Stay within the size you allocated.

Notice how many defenses reduce to one habit: **`free(p); p = NULL;`** — it neutralizes use-after-free (crashes instead of corrupts) and double-free (`free(NULL)` is a no-op) in one move.

## Tools: let the machine catch what you can't

Because these bugs are silent and intermittent, C programmers rely on tools to find them — this is not optional for serious C. A memory checker like **Valgrind** (or the compiler's **AddressSanitizer**, `-fsanitize=address`) runs your program and reports leaks, use-after-free, double-frees, and out-of-bounds accesses with the exact location:

```bash
valgrind --leak-check=full ./myprogram
gcc -fsanitize=address -g program.c -o program   # ASan alternative
```

Run your C programs under these routinely, especially before trusting them. They catch the memory errors that testing alone misses — the ones that "work on my machine" and crash in production. In C, the memory-checking tools are as much a part of the workflow as the compiler.

## The bargain, made explicit

Dynamic memory is C's control-and-responsibility bargain at its sharpest. You get precise, manual control over exactly when memory is allocated and freed — no GC pauses, no hidden overhead, memory usage you fully determine. In exchange, you own the entire lifecycle, and the four bug classes await any lapse. The way through is discipline made routine: think in ownership, match every `malloc` with one `free` on every path, adopt `free(p); p = NULL;` as a reflex, check every allocation for `NULL`, and run a memory checker. Do these consistently and manual memory management stops being terrifying and becomes just another engineering practice — the one that, more than any other, is what "knowing C" means. Next, we put the heap to work building data structures that grow at runtime.

## Key takeaways

- Use the **stack** for small, fixed-size, function-local data (automatic and free) and the **heap** for runtime-sized data or data that must outlive its creating function (flexible but manually managed).
- The heap is managed with four `<stdlib.h>` functions: **`malloc`** (allocate, uninitialized), **`calloc`** (allocate + zero, overflow-safe), **`realloc`** (resize, may move — assign to a temporary), and **`free`** (release) — always check `malloc`/`realloc` for `NULL` and `sizeof` the type.
- Think in **ownership**: for every allocation decide which code frees it and when; most memory bugs are ownership confusion (double-free or never-free), so match every `malloc` with exactly one `free` on every path.
- The four deadly bugs are **memory leaks** (never freed — silent starvation), **use-after-free/dangling pointers** (using freed memory — intermittent corruption/security holes), **double free** (heap corruption), and **heap buffer overflows** — and the reflex **`free(p); p = NULL;`** defuses use-after-free and double-free at once.
- These bugs are silent and intermittent, so **run a memory checker** (Valgrind or AddressSanitizer) routinely — in C the memory tools are as essential to the workflow as the compiler itself.

## Further reading

- [cppreference — Dynamic memory management](https://en.cppreference.com/w/c/memory)
- [cppreference — C language behavior (undefined behavior)](https://en.cppreference.com/w/c/language/behavior)
