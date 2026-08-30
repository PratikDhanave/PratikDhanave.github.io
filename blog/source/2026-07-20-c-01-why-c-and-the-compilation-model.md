# Why C, and How It Compiles

*C is fifty years old and still runs the world — operating systems, databases, language runtimes, embedded devices, and the standard libraries under almost everything else. Learning C is learning how computers actually work: memory, pointers, and the thin layer between your code and the machine. This series builds C from the ground up, and it starts with what C is and what really happens when you compile it.*

If you've written Go, Python, Rust, or TypeScript, you've stood on top of abstractions that C built. C is the language those runtimes are often written in, and it's the one that forces you to understand memory directly because it hands you almost nothing for free. That's exactly why it's worth learning: C teaches the machine. This series is a from-scratch C curriculum for programmers who want that foundation. This first post covers why C endures and what the compilation model — the thing that trips up newcomers most — actually does.

## Why C still matters

C occupies a unique place: it's a **high-level language that sits very close to the hardware.** It gives you structured code — functions, types, control flow — while exposing memory addresses, manual allocation, and a nearly one-to-one correspondence with what the CPU does. That combination is why, decades on, C remains foundational:

- **It runs the infrastructure.** Operating system kernels (Linux, much of Windows and macOS internals), databases, network stacks, language interpreters (CPython), and embedded firmware are largely written in C. When you need control and speed, C is still the answer.
- **It's the lingua franca of interop.** C's calling convention and ABI are the common tongue systems use to talk to each other. That's why nearly every language has a "foreign function interface" to C — it's the universal glue.
- **It teaches the machine.** Because C doesn't hide memory, learning it forces you to understand pointers, the stack and heap, and how data is laid out in bytes. That knowledge makes you a better programmer in *every* language, because you finally understand what the abstractions above are managing for you.

The flip side, which this series takes seriously, is that C gives you very little safety. There's no garbage collector, no bounds checking, no memory safety net. The power to touch memory directly is also the power to corrupt it. C demands discipline, and much of this series is about the discipline.

## Your first C program

Here is C in its entirety, minimal form:

```c
#include <stdio.h>

int main(void) {
    printf("Hello, C\n");
    return 0;
}
```

Every piece matters. `#include <stdio.h>` pulls in the standard I/O declarations so the compiler knows what `printf` is. `int main(void)` is the entry point — execution begins here, and it returns an `int` *status code* to the operating system (`0` means success). `printf` writes to standard output; `\n` is a newline. `return 0;` hands that success code back to the shell. There's no runtime, no interpreter — this compiles to a native executable that the OS runs directly.

## The compilation model: four stages

The single most important thing to understand early is that C is **compiled ahead of time into machine code**, in a pipeline of distinct stages. Confusion about C — especially about headers, declarations, and "undefined reference" errors — usually comes from not knowing these stages. When you run `gcc hello.c -o hello`, four things happen in order:

1. **Preprocessing.** The preprocessor handles the lines starting with `#`. `#include <stdio.h>` is *literally replaced* with the contents of that header file; `#define` macros are expanded. The output is a single expanded source file, pure C with all directives resolved. (This is textual substitution — the preprocessor doesn't understand C, it just manipulates text, which is why it's both powerful and dangerous, as post 8 explores.)
2. **Compilation.** The compiler translates that expanded C into **assembly** — the human-readable form of the CPU's instructions — for your target architecture. This is where type checking and optimization happen.
3. **Assembly.** The assembler turns that assembly into an **object file** (`.o`): machine code, but not yet a complete program. It has your compiled functions but unresolved references to functions defined elsewhere (like `printf`).
4. **Linking.** The linker combines your object file(s) with the libraries they need (the C standard library, where `printf` actually lives) and resolves all those references, producing the final **executable**.

Understanding this pipeline explains the errors you'll hit. A "implicit declaration" warning is the *compiler* not finding a declaration (you forgot an `#include`). An "undefined reference" error is the *linker* not finding a definition (the function was declared but its implementation wasn't linked in). Same-sounding problems, different stages, different fixes.

## Headers, declarations, and definitions

That pipeline is why C separates **declarations** from **definitions**, a distinction that puzzles newcomers. A *declaration* tells the compiler a name's type and signature ("a function `printf` exists that takes a format string and returns an int") without providing its body. A *definition* provides the actual implementation.

Header files (`.h`) contain declarations; source files (`.c`) contain definitions. When you `#include <stdio.h>`, you're getting *declarations* so the compiler can type-check your calls; the actual *definition* of `printf` is in the standard library, linked in at stage 4. This declare-here, define-elsewhere split is how C compiles large programs file by file (each `.c` compiled independently to a `.o`, then all linked) — the subject we return to in post 8 on multi-file projects.

## The toolchain

In practice you'll use a compiler driver — **`gcc`** or **`clang`** — that runs all four stages for you:

```bash
gcc -Wall -Wextra -std=c17 hello.c -o hello   # compile with warnings on
./hello                                         # run it
```

Two habits to adopt from day one. **Always compile with warnings enabled** (`-Wall -Wextra`): C's compiler will, by default, let you do dangerous things silently, and warnings catch a huge fraction of bugs before they run. **Specify a standard** (`-std=c17` or `c11`) so you know which version of C you're writing. Later you'll add a debugger (`gdb`/`lldb`) and a memory checker (`valgrind`, post 6) — because in C, the tools that catch your mistakes are as important as the language itself.

The mental model to carry forward: C is a thin, compiled layer over the machine, built in four stages (preprocess, compile, assemble, link), where you manage memory yourself and the compiler assumes you know what you're doing. The rest of the series builds on the machine C exposes — starting, next, with how it represents data as bits.

## Key takeaways

- C is a **high-level language that sits very close to the hardware** — structured code with direct access to memory and a near one-to-one map to the CPU — which is why it still runs OS kernels, databases, runtimes, and embedded systems, and is the universal interop language.
- C's power comes with **no safety net** (no garbage collector, no bounds checking) — the ability to touch memory directly is also the ability to corrupt it, so C demands discipline.
- C **compiles ahead of time in four stages**: preprocessing (textual `#include`/`#define` expansion), compilation (C→assembly, type-checking), assembly (→object files), and linking (combine objects + libraries → executable).
- Knowing the stages explains the errors: an **"implicit declaration"** is the compiler missing a *declaration* (forgotten `#include`); an **"undefined reference"** is the linker missing a *definition* (unlinked implementation).
- C separates **declarations** (headers `.h`, type/signature only) from **definitions** (source `.c`, the implementation) — the split that lets C compile large programs file by file — and you should always compile with **`-Wall -Wextra` and a `-std=`** from day one.

## Further reading

- [cppreference — C language](https://en.cppreference.com/w/c/language)
- [cppreference — C language functions](https://en.cppreference.com/w/c/language/functions)
