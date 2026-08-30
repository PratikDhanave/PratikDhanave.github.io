# Why Put Types on JavaScript

*JavaScript runs everywhere and forgives everything — including your mistakes, right up until they reach production. TypeScript adds a static type layer on top of JavaScript that catches those mistakes at compile time, while compiling away to plain JavaScript that runs unchanged. Understanding what TypeScript actually is — a structural type checker that erases at build time — is the foundation for everything else.*

If you've written Go, Python, or Rust and then touched a large JavaScript codebase, the absence of types feels like driving without headlights. TypeScript is the industry's answer: a superset of JavaScript that adds static types. This series builds it from the ground up for engineers who already program and want to understand TypeScript's type system deeply rather than cargo-culting annotations. This first post is about what TypeScript *is* and why it's worth the ceremony.

## The problem TypeScript solves

JavaScript is dynamically typed: a variable can hold anything, and type errors surface only when a line actually runs. `user.nmae` (typo) isn't an error — it's `undefined`, which flows silently downstream until something explodes far from the cause. `"3" + 4` is `"34"`; `[] + {}` is a string. The language does its best to keep running, which means bugs hide instead of failing fast.

For a small script this is fine. For a large, long-lived codebase with many contributors, it's a slow-motion disaster: refactoring is terrifying (did I break a caller three files away?), APIs are undocumented (what shape is this object?), and whole categories of bugs — typos, wrong argument order, null access, shape mismatches — reach production. TypeScript exists to move that entire class of failure from *runtime* to *compile time*, where it's cheap to fix.

## What TypeScript is

TypeScript is **JavaScript plus a static type layer**. Three properties define it:

- **It's a superset.** Every valid JavaScript program is a valid TypeScript program. You adopt it incrementally — rename `.js` to `.ts`, add types where they help, leave the rest. There's no rewrite.
- **It's checked at compile time.** A separate program, the TypeScript compiler (`tsc`), reads your annotated code and reports type errors *before* it runs. This is static analysis: it reasons about your program's types without executing it.
- **It erases to JavaScript.** This is the part newcomers miss. TypeScript's types exist *only at compile time*. `tsc` checks them and then **strips them out entirely**, emitting plain JavaScript. The types are not present at runtime — there's no runtime type checking, no performance cost, no `.ts` on the server. TypeScript is a *developer-time* tool that produces ordinary JS.

That last point has deep consequences we'll return to: because types are erased, they can't be inspected at runtime, and any runtime validation (of API responses, user input) still needs actual runtime code. Types check your *code*; they don't guard your *data* at the boundary.

## Compilation and erasure in practice

Concretely, you write:

```typescript
function greet(name: string): string {
  return `Hello, ${name}`;
}
greet("Ada");
greet(42); // ✗ compile error: Argument of type 'number' is not assignable to 'string'
```

`tsc` flags the `greet(42)` line at build time. Then it emits this JavaScript, with the types gone:

```javascript
function greet(name) {
  return `Hello, ${name}`;
}
greet("Ada");
```

The annotations `: string` vanished. What ran the check (the compiler) is separate from what runs in production (the emitted JS). You get the safety during development and pay nothing at runtime. This separation — check-then-erase — is the essence of how TypeScript works.

## Structural typing: a first taste

TypeScript's type system is **structural**, not nominal — a distinction that surprises people from Java or C#. What matters is the *shape* of a value, not the name of its type. If an object has the right properties, it fits, regardless of what class or interface it was declared as:

```typescript
interface Point { x: number; y: number; }
function dist(p: Point): number { return Math.hypot(p.x, p.y); }

const location = { x: 3, y: 4, label: "home" };
dist(location); // ✓ fine — location has x and y; the extra label is ignored
```

`location` was never declared as a `Point`, but it *has the shape of one*, so it's accepted. This "duck typing, checked at compile time" is a defining feature of TypeScript and the subject of the next post. It's what makes TypeScript feel flexible and JavaScript-native rather than rigid.

## What you get, and the honest caveats

The payoff of the type layer is large and compounding:

- **Errors caught early** — typos, wrong types, missing properties, null access, all flagged before running.
- **Fearless refactoring** — change a function's signature and the compiler lists every caller that now breaks. Large-scale change becomes tractable.
- **Documentation that can't rot** — the types *are* the API contract, always in sync with the code because the compiler enforces them.
- **Editor superpowers** — precise autocomplete, inline errors, and safe automated refactors, because the tooling knows the types.

The honest caveats keep you from over-trusting it: types are **erased**, so they don't validate data crossing your program's boundary (API responses, JSON, user input) — that still needs runtime checks. The escape hatch `any` turns checking *off* for a value and, used carelessly, quietly defeats the whole system (post 8). And types add friction — annotations, config, a build step — that pays off on large, long-lived codebases far more than on a throwaway script.

The mental model to carry through the series: **TypeScript is a compile-time structural type checker that erases to plain JavaScript.** Every feature ahead — inference, unions, generics, utility types, module config — is a way of describing your program's shapes precisely enough that the compiler can catch mistakes before your users do.

## Key takeaways

- JavaScript's dynamic typing hides type errors until runtime; **TypeScript moves that entire class of bug (typos, wrong types, null access, shape mismatches) to compile time**, where it's cheap to fix.
- TypeScript is **JavaScript plus a static type layer**: a *superset* (all JS is valid TS, adopt incrementally), *checked at compile time* by `tsc`, and **erased to plain JavaScript** — types exist only at development time with zero runtime cost or presence.
- Because types are **erased**, they check your *code* but don't validate *data* at the boundary — API responses and user input still need real runtime validation.
- TypeScript's type system is **structural**: compatibility is based on a value's *shape* (its properties), not the declared type name — "duck typing checked at compile time."
- The payoff is early error detection, fearless refactoring, always-current documentation, and powerful editor tooling; the caveats are boundary validation, the `any` escape hatch, and friction that suits large codebases more than throwaway scripts.

## Further reading

- [TypeScript Handbook — The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html)
- [TypeScript Handbook — Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html)
