# The Structural Type System

*TypeScript's type system has two properties that shape everything you do with it: it judges compatibility by structure rather than by name, and it infers types so you rarely have to spell them out. Add the small vocabulary of primitives, literal types, and the special types `any`, `unknown`, and `never`, and you have the foundation the rest of the language builds on.*

The previous post introduced structural typing in passing. This post makes it precise and adds the rest of the base vocabulary: inference, the ways to name object shapes, and the three special types that trip up newcomers. Get these and the more advanced features (unions, generics, mapped types) become straightforward extensions.

## Structural, not nominal

In a *nominal* type system (Java, C#), two types are compatible only if one explicitly declares it's the other — the *name* is the identity. TypeScript is **structural**: two types are compatible if their *shapes* match, regardless of names.

```typescript
interface Named { name: string; }
class Dog { constructor(public name: string) {} }

function greet(n: Named) { console.log(n.name); }
greet(new Dog("Rex"));            // ✓ Dog has a `name: string`, so it fits Named
greet({ name: "Ada", age: 3 });   // ✓ object literal with the right shape fits too
```

Nothing declared that `Dog` "is a" `Named`. It's accepted because it *has the structure* of one. This is TypeScript matching JavaScript's own duck-typed spirit — code that works if the object has the right properties — but checking it at compile time. The practical upshot: you type against *shapes* you need, not class hierarchies, which keeps code flexible and decoupled.

## Type inference: let the compiler do the work

You rarely annotate everything, because TypeScript **infers** types from how values are used:

```typescript
let count = 0;          // inferred: number
const name = "Ada";     // inferred: "Ada" (a literal type — see below)
const nums = [1, 2, 3]; // inferred: number[]
function double(n: number) { return n * 2; } // return type inferred: number
```

The guideline: **annotate boundaries, infer internals.** Put explicit types on function parameters and public API signatures (the contracts others depend on), and let inference handle local variables and return types where the intent is obvious. Over-annotating local variables adds noise the compiler already knows; under-annotating public functions removes the documentation and safety types are for. Good TypeScript reads mostly like clean JavaScript, with types concentrated at the edges.

## Naming object shapes: interface vs. type alias

Two ways name object shapes, and they're mostly interchangeable:

```typescript
interface User { id: number; name: string; }
type UserT = { id: number; name: string };
```

- **`interface`** is designed for object shapes and supports *declaration merging* (two `interface User {}` blocks combine) and `extends`. It's the conventional choice for public object/class contracts.
- **`type`** (a type alias) names *any* type, not just objects — unions, tuples, primitives, function types, and the computed types from later posts. It can't be merged, which is often a feature (no surprise reopening).

A reasonable rule: use `interface` for object shapes you might extend or that model public contracts; use `type` for unions, tuples, function signatures, and anything computed. The difference matters less than consistency.

## Primitives and literal types

TypeScript has the JavaScript primitives — `string`, `number`, `boolean`, `null`, `undefined`, `bigint`, `symbol` — plus arrays (`number[]` or `Array<number>`), tuples (`[string, number]`), and object types.

More interesting are **literal types**: a type can be a *specific value*, not just a category. `"GET"` is a type inhabited only by the string `"GET"`. On their own they're a curiosity; combined with unions (next post) they become powerful:

```typescript
type Method = "GET" | "POST" | "PUT" | "DELETE";
function request(url: string, method: Method) { /* ... */ }
request("/x", "GET");   // ✓
request("/x", "PATCH"); // ✗ not one of the allowed literals
```

Literal types let you express "one of these exact values" precisely — safer and more self-documenting than a bare `string`, and the basis for discriminated unions later. This is worth noticing because `const` declarations infer literal types while `let` widens to the general type — a subtlety that matters when you build unions.

## The three special types: `any`, `unknown`, `never`

Three types have no direct JavaScript analog and are the source of much confusion and misuse:

- **`any`** turns type checking *off* for a value. It's assignable to and from everything; the compiler stops complaining and stops helping. `any` is the escape hatch — occasionally necessary during migration, but every `any` is a hole in your type safety through which runtime bugs return. Treat it as a code smell (post 8).
- **`unknown`** is the *safe* counterpart to `any`: it can hold anything, but you can't *use* it until you narrow it to a specific type (via a check). It says "I don't know what this is yet, and the compiler will force me to find out before I touch it." Use `unknown` for genuinely-untyped input (parsed JSON, `catch` clause errors) and narrow before use — you keep safety instead of discarding it.
- **`never`** is the type with *no values* — it represents something that cannot happen. A function that always throws or loops forever returns `never`; a variable narrowed until no cases remain is `never`. It seems abstract but is deeply useful: it's how you get *exhaustiveness checking* (post 3), where the compiler proves you've handled every case because the leftover is `never`.

The `any`-vs-`unknown` distinction is a litmus test of TypeScript maturity: reaching for `any` discards the type system for that value; reaching for `unknown` keeps it and forces a check. Prefer `unknown` almost always.

## Why this foundation matters

Structural typing makes TypeScript flexible and JavaScript-native — you type against shapes, not hierarchies. Inference keeps it low-friction — you annotate edges and let the compiler fill in the rest. Literal types add precision — "exactly these values." And `any`/`unknown`/`never` give you the escape hatch, the safe-unknown, and the impossible-type that later features (narrowing, exhaustiveness, generics) build on. Everything more advanced in this series is a way of composing these basics into precise descriptions of your program's shapes.

## Key takeaways

- TypeScript is **structural**: type compatibility is based on a value's *shape* (its properties), not its declared name — "duck typing checked at compile time," which keeps code flexible and decoupled from class hierarchies.
- **Type inference** means you rarely annotate everything — the guideline is *annotate boundaries (parameters, public signatures), infer internals (locals, return types)* so code reads like clean JS with types at the edges.
- Name object shapes with **`interface`** (object-focused, supports declaration merging and `extends`) or **`type`** aliases (name *any* type — unions, tuples, functions, computed types); prefer `interface` for extendable object contracts, `type` for everything else.
- **Literal types** (`"GET"`, `42`) type a *specific value*; combined with unions they express "one of exactly these values," safer and more self-documenting than bare primitives.
- The three special types: **`any`** turns checking off (an escape hatch and code smell), **`unknown`** is the *safe* anything that must be narrowed before use, and **`never`** is the valueless "can't happen" type that powers exhaustiveness checking — prefer `unknown` over `any` almost always.

## Further reading

- [TypeScript Handbook — Type Compatibility (structural typing)](https://www.typescriptlang.org/docs/handbook/type-compatibility.html)
- [TypeScript Handbook — Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html)
