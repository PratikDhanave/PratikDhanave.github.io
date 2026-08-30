# Structs, Unions, and Data Structures

*Structs let you bundle related data into a single named type — the closest C gets to an object. Combined with pointers and heap allocation, they're how you build every data structure C is famous for: linked lists, trees, hash tables. This post covers structs, their cousins unions and enums, the memory-layout details that bite (padding), and puts it all together to build a linked list from scratch.*

We have pointers and the heap. Now we combine them into aggregate types and the classic data structures they enable. Structs are the organizing tool that turns loose variables into modeled entities, and — pointed at each other and allocated on the heap — into the dynamic structures that grow at runtime. This post is where the whole series so far comes together in working code.

## Structs: grouping related data

A **struct** is a user-defined type that groups several values (its *members*) under one name:

```c
struct Point {
    int x;
    int y;
};

struct Point p = {3, 4};
printf("%d, %d\n", p.x, p.y);   // access members with .
```

A struct lays its members out in memory *together, in order*, so `struct Point` is a small block holding an `x` then a `y`. You access members with the dot operator (`p.x`). Structs are C's way of modeling entities — a `Point`, a `User`, a `Connection` — bundling the data that belongs together instead of passing around loose parallel variables.

When you have a *pointer* to a struct (which is constant in C, since structs are often heap-allocated or passed by address to avoid copying), you use the **arrow operator** `->` to access members through the pointer:

```c
struct Point *pp = &p;
printf("%d\n", pp->x);     // pp->x is shorthand for (*pp).x
```

`pp->x` means "dereference `pp`, then take member `x`" — the everyday way to work with struct pointers. This matters because passing large structs by value copies all their bytes; passing a pointer (`struct Point *`) is cheap and lets the function modify the original (post 4's pass-by-value logic, applied to structs).

## typedef: cleaner names

Writing `struct Point` everywhere is verbose. **`typedef`** creates an alias so you can use just `Point`:

```c
typedef struct {
    int x;
    int y;
} Point;

Point p = {1, 2};      // no "struct" keyword needed
```

This is idiomatic C — most codebases `typedef` their structs so the type reads as a single name. (For self-referential structs, like list nodes below, you give the struct a tag *and* typedef it, so it can refer to itself.)

## Memory layout and padding

A detail that surprises people: **a struct's size is often larger than the sum of its members**, because the compiler inserts **padding** to align members on their natural boundaries (many CPUs access a 4-byte `int` faster when it sits at a 4-byte-aligned address):

```c
struct Example {
    char  c;     // 1 byte
    int   n;     // 4 bytes — needs 4-byte alignment
    char  d;     // 1 byte
};
// sizeof might be 12, not 6: padding after c (to align n) and after d (to
// make the whole struct's size a multiple of its largest member's alignment)
```

The takeaway is practical: `sizeof(struct Example)` may exceed the raw member sizes, and *member order affects struct size* — grouping members by size (largest first, or same-size together) can reduce padding. This matters for memory-tight code, for structs you allocate by the million, and for anything mapping to a binary format or hardware layout (where you may need to control padding explicitly). For everyday code, just know that padding exists and don't assume a struct is the sum of its parts.

## Unions and enums

Two related aggregate types round out the toolkit:

- **`union`** — like a struct, but all members *share the same memory*; it holds *one* of its members at a time, and its size is that of its largest member. Unions are for memory-efficient "one of these" data, typically paired with a tag field saying which member is currently valid (a "tagged union"):

```c
enum Kind { INT_VAL, FLOAT_VAL };
struct Value {
    enum Kind kind;         // which member is active
    union { int i; float f; } data;   // i and f overlap in memory
};
```

- **`enum`** — a set of named integer constants, for readable, finite sets of options:

```c
enum Color { RED, GREEN, BLUE };   // RED=0, GREEN=1, BLUE=2 by default
enum Color c = GREEN;
```

Enums make code self-documenting (`GREEN` instead of `1`) and pair naturally with `switch`. The tagged-union pattern above (`enum` discriminant + `union` payload) is C's version of the discriminated unions from typed languages — a memory-efficient way to hold one of several kinds of value, with the enum telling you which.

## Building a linked list

Now the payoff: structs that *point to other structs*, allocated on the heap, form dynamic data structures. Here's a singly linked list — the "hello world" of C data structures — using everything from the series:

```c
#include <stdlib.h>

typedef struct Node {
    int value;
    struct Node *next;    // pointer to the next node (self-referential)
} Node;

// Prepend a value; returns the new head.
Node *prepend(Node *head, int value) {
    Node *n = malloc(sizeof(Node));   // heap-allocate a node
    if (n == NULL) return head;       // allocation can fail
    n->value = value;
    n->next  = head;                  // point at the old head
    return n;                         // the new node is the new head
}

// Free every node — ownership: the list owns its nodes.
void freeList(Node *head) {
    while (head != NULL) {
        Node *next = head->next;      // save next BEFORE freeing
        free(head);
        head = next;
    }
}
```

Every concept converges here. The struct is **self-referential** — `struct Node` contains a `Node *next`, a pointer to its own type — which is how nodes chain together (a struct can't *contain* itself, but it can *point to* itself). Each node is **heap-allocated** (`malloc`) because the list grows at runtime, and we **check for `NULL`**. We traverse by following `next` pointers until `NULL` (the end marker). And `freeList` embodies **ownership** (post 6): the list owns its nodes, so it frees each one — carefully saving `next` *before* freeing the current node, because reading `head->next` after `free(head)` would be use-after-free.

This single example is C in miniature: structs to model the node, pointers to link them, the heap for runtime growth, `NULL` to mark the end, and disciplined freeing to avoid leaks and use-after-free. Trees, hash tables, and graphs are the same idea elaborated — structs pointing to structs, allocated and freed by hand.

## Why this is where C pays off

Structs plus pointers plus the heap are the combination that makes C capable of real programs. Structs model your domain; pointers link instances together; the heap lets those structures grow and shrink at runtime; and the ownership discipline from post 6 keeps it all leak-free. The data structures you use in every language — lists, trees, maps — are, underneath, exactly this: nodes of memory pointing at each other. Building them by hand in C is what makes you understand what those higher-level collections are actually doing, and it's the foundation for the systems C is used to build. The final post steps back to the preprocessor, multi-file programs, undefined behavior, and the idioms that keep all of this safe.

## Key takeaways

- A **struct** groups related members into one named type laid out together in memory; access members with `.` on a value and **`->`** on a pointer (`pp->x` = `(*pp).x`) — and pass large structs by pointer to avoid copying and to modify the original.
- **`typedef`** aliases a struct to a single name (idiomatic C), and self-referential structs (list nodes) use a tag plus typedef so they can point to their own type.
- A struct's size can **exceed the sum of its members** due to **padding** for alignment, so member order affects size — relevant for memory-tight code and binary/hardware layouts.
- **`union`** overlaps all members in shared memory (holds one at a time, sized to the largest) — paired with an **`enum`** tag it forms a tagged union (C's discriminated union); enums give readable, finite named constants.
- A **linked list** unites the series: a **self-referential struct** (`Node *next`), **heap-allocated** nodes that grow at runtime, `NULL` as the end marker, and **ownership-based freeing** (save `next` before `free` to avoid use-after-free) — the template for all pointer-based data structures.

## Further reading

- [cppreference — Struct declarations](https://en.cppreference.com/w/c/language/struct)
- [cppreference — C language](https://en.cppreference.com/w/c/language)
