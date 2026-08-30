# Modules, Config, and Tooling

*Types are only half of TypeScript; the other half is the machinery that compiles, configures, and connects your code to the vast JavaScript ecosystem. ES modules organize code, `tsconfig.json` controls how strictly the compiler checks it, and declaration files let typed and untyped code interoperate. Understanding this layer is what turns a working `.ts` file into a real, maintainable project.*

We've covered the type system thoroughly. This post is about everything *around* it: how code is organized into modules, how you configure the compiler (and why `strict` is the setting that matters most), and how TypeScript integrates with plain JavaScript libraries through declaration files. This is the practical infrastructure of a TypeScript project.

## Modules: organizing code

Modern TypeScript uses **ES modules** — the standard `import`/`export` syntax — to split code into files with explicit dependencies:

```typescript
// user.ts
export interface User { id: number; name: string; }
export function greet(u: User) { return `Hi, ${u.name}`; }

// app.ts
import { User, greet } from "./user";
```

Each file is a module with its own scope; nothing is global unless exported and imported. TypeScript understands modules natively and type-checks *across* them — import a function and the compiler knows its signature, so a wrong-type argument three files away is caught. Prefer **named exports** (as above) over default exports in most cases: they're refactor-friendly (rename propagates), autocomplete-friendly, and avoid the ambiguity of default-export naming. Modules are how a TypeScript codebase stays navigable and how the compiler builds its cross-file understanding.

## `tsconfig.json`: the control panel

Every TypeScript project has a **`tsconfig.json`** that tells the compiler what to compile and how. The options that matter most:

- **`target`** — which JavaScript version to emit (`ES2022`, etc.). TypeScript can *downlevel* modern syntax to older JS for broader compatibility.
- **`module`** — the module system for the output (`ESNext`, `CommonJS`, `NodeNext`), depending on where the code runs.
- **`lib`** — which built-in type definitions to include (DOM APIs for browsers, etc.).
- **`outDir` / `rootDir`** — where source is and where compiled output goes.
- **`strict`** — the single most important flag (its own section below).

A minimal, sane config:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "strict": true,
    "outDir": "dist",
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
```

The config *is* your project's contract with the compiler; getting it right (especially `strict`) determines how much safety you actually get. Many teams extend a shared base config for consistency.

## `strict` mode: turn it on

If you take one thing from this post: **enable `strict: true`.** It's an umbrella that turns on a family of checks, and without it TypeScript is a shadow of itself. The most consequential members:

- **`strictNullChecks`** — the big one. Without it, `null` and `undefined` are assignable to *every* type, so `user.name` compiles even when `user` might be null — and crashes at runtime. *With* it, `null`/`undefined` are their own types you must handle explicitly (`User | null`), and the compiler forces you to check before access. This single flag eliminates the "cannot read property of undefined" class of bug — JavaScript's most common runtime error — at compile time. Turning it on is the difference between TypeScript catching null bugs and merely decorating them.
- **`noImplicitAny`** — errors when the compiler would silently infer `any` (e.g. an un-annotated parameter). It forces you to *choose* your types rather than accidentally opting out of checking. Silent `any` is how type safety erodes; this flag stops it.
- Plus `strictFunctionTypes`, `strictBindCallApply`, and others that tighten checking.

Starting a *new* project without `strict` is choosing a weaker language for no reason. For an *existing* untyped codebase, you enable it incrementally (file by file, or flag by flag) as part of migration — but `strict` is the destination. Everything about TypeScript's value proposition assumes it's on.

## Declaration files: bridging to JavaScript

The JavaScript ecosystem is enormous and mostly written in plain JS. **Declaration files** (`.d.ts`) are how TypeScript understands that untyped code: they contain *only* type information — signatures, no implementation — describing the shape of a JavaScript library so your typed code can call it safely.

```typescript
// math.d.ts — types for a plain-JS math.js
export declare function add(a: number, b: number): number;
```

Two ways these show up:

- **Bundled types.** Many modern libraries ship their own `.d.ts` files, so `import`ing them just works with full type safety.
- **DefinitelyTyped** (`@types/*`). For libraries that don't bundle types, the community maintains declarations in a massive repository, installed as `@types/lodash`, `@types/node`, and so on. Install the `@types` package and the untyped library becomes typed.

Declaration files are also what your *own* library emits (`tsc` can generate `.d.ts` from your source) so *consumers* of your package get types. They're the interface layer that lets the typed and untyped halves of the ecosystem interoperate — without them, TypeScript would be an island.

## The build pipeline in practice

Because TypeScript compiles to JavaScript and erases types (post 1), a real project has a build step, and how you run it varies:

- **`tsc`** compiles and type-checks together — the baseline.
- **Bundlers** (esbuild, Vite, Webpack) often *transpile* TypeScript to JavaScript very fast by *stripping types without checking them* — great for speed, but it means the bundler isn't your safety net. So teams commonly run **`tsc --noEmit`** separately (in CI and editors) purely to *type-check*, while the bundler produces the actual output. Type-checking and emitting become two jobs.
- **Editors** run the TypeScript language service continuously, giving you the red squiggles and autocomplete in real time — the fastest feedback loop of all.

The practical setup for most projects: a fast bundler for builds, `tsc --noEmit` in CI to enforce type correctness, and `strict` on so that check has teeth. Understanding that *transpiling* (strip types) and *type-checking* (verify types) are separable explains why "it built fine but has type errors" is possible — and why you should gate merges on an actual type-check, not just a successful bundle.

## Key takeaways

- **ES modules** (`import`/`export`, prefer named exports) organize code into scoped files, and TypeScript type-checks *across* them so cross-file mistakes are caught.
- **`tsconfig.json`** is the compiler control panel — `target`, `module`, `lib`, `outDir` — and it's your project's contract with the compiler; getting it right determines how much safety you get.
- **Enable `strict: true`** — especially **`strictNullChecks`** (makes `null`/`undefined` explicit types you must handle, eliminating "cannot read property of undefined" at compile time) and **`noImplicitAny`** (stops silent opt-outs of checking). Without `strict`, TypeScript is drastically weaker.
- **Declaration files (`.d.ts`)** carry types-only descriptions of JavaScript code — bundled with modern libraries or provided by community **DefinitelyTyped `@types/*` packages** — and are how typed and untyped code interoperate (and how your own library ships types).
- **Transpiling (strip types) and type-checking (verify types) are separable**: fast bundlers often strip without checking, so run **`tsc --noEmit` in CI** to enforce correctness and gate merges on a real type-check, not just a successful build.

## Further reading

- [TSConfig Reference](https://www.typescriptlang.org/tsconfig/)
- [TypeScript Handbook — Introduction to Declaration Files](https://www.typescriptlang.org/docs/handbook/declaration-files/introduction.html)
