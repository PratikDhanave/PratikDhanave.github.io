# Utility and Mapped Types

*TypeScript's type system is itself a small programming language — you can compute new types from existing ones. The built-in utility types (`Partial`, `Pick`, `Omit`, `Record`) are the everyday face of this; underneath, `keyof`, mapped types, conditional types, and template literal types are the primitives that make them possible. Learning to derive types instead of hand-writing them is what separates fluent TypeScript from annotation-copying.*

Generics gave us type parameters. This post shows what you can *do* with them: transform one type into another at the type level. This is where TypeScript stops being "Java for JavaScript" and becomes something more expressive — a language for describing how types relate and change. We'll start with the utilities you'll use daily and then open them up to see the machinery inside.

## The everyday utility types

TypeScript ships **utility types** that transform object types. These four cover most needs:

```typescript
interface User { id: number; name: string; email: string; }

Partial<User>          // { id?: number; name?: string; email?: string }  — all optional
Required<User>         // all properties required (removes ?)
Pick<User, "id" | "name">    // { id: number; name: string }  — subset
Omit<User, "email">          // { id: number; name: string }  — all but some
Record<string, User>         // { [key: string]: User }  — a dictionary type
Readonly<User>         // all properties readonly
```

These solve real, constant problems. `Partial<User>` types an update payload where any subset of fields may be present. `Omit<User, "id">` types the input to a "create user" function (no id yet). `Record<Role, Permissions>` types a lookup table. The key insight: **you define `User` once and derive every related shape from it.** When `User` gains a field, all the derived types update automatically — no drift between your create-input, update-input, and the entity. Hand-maintaining parallel interfaces is exactly the rot these prevent.

## `keyof` and indexed access

Two operators underlie the utilities. **`keyof`** produces a union of an object type's keys:

```typescript
type UserKeys = keyof User;   // "id" | "name" | "email"
```

**Indexed access** looks up the type of a property (or several):

```typescript
type NameType = User["name"];          // string
type Vals = User["id" | "name"];       // number | string
```

Together these let you talk about "the keys of a type" and "the type at a key" — the raw material for transforming types. You saw `keyof` already in the generic `getProp<T, K extends keyof T>` from the last post; here it becomes a building block for computing whole new types.

## Mapped types: transforming every property

A **mapped type** iterates over the keys of a type and produces a new property for each — a `for` loop at the type level:

```typescript
type MyPartial<T> = { [K in keyof T]?: T[K] };
type MyReadonly<T> = { readonly [K in keyof T]: T[K] };
```

Read `{ [K in keyof T]?: T[K] }` as: "for each key `K` in `T`, make a property of type `T[K]`, optional." That *is* how `Partial<T>` is implemented — the built-in utilities are mostly thin mapped types over `keyof`. Once you can read this syntax, the "magic" utilities become ordinary code you could have written, and you can build your own:

```typescript
type Nullable<T> = { [K in keyof T]: T[K] | null };  // every field can be null
type Stringify<T> = { [K in keyof T]: string };      // every field becomes string
```

Mapped types can also *add or remove* modifiers (`-?` removes optionality, `-readonly` removes readonly) and even *remap keys*. They turn "I need a variant of this type where every property is X" from copy-paste into a one-line derivation.

## Conditional types: types that branch

**Conditional types** choose between two types based on a test, using a ternary at the type level:

```typescript
type IsString<T> = T extends string ? "yes" : "no";
type A = IsString<"hi">;   // "yes"
type B = IsString<42>;     // "no"
```

`T extends U ? X : Y` means "if `T` is assignable to `U`, the type is `X`, else `Y`." This enables types that adapt to their input. Combined with the `infer` keyword, conditional types can *extract* a type from within another — this is how utilities like `ReturnType<F>` (the return type of a function type) and `Awaited<T>` (the type a promise resolves to) work:

```typescript
type ReturnOf<F> = F extends (...args: any[]) => infer R ? R : never;
type R = ReturnOf<() => User>;   // User
```

`infer R` says "capture whatever the return type is, and call it `R`." Conditional types plus `infer` are the deep end of type-level programming — you rarely write them yourself, but understanding them demystifies the standard library and lets you read advanced type code.

## Template literal types

Types can even manipulate strings. **Template literal types** build string literal types from other types, mirroring JavaScript's template strings:

```typescript
type Method = "get" | "post";
type Route = "/users" | "/orders";
type Endpoint = `${Uppercase<Method>} ${Route}`;
// "GET /users" | "GET /orders" | "POST /users" | "POST /orders"
```

Because unions distribute, this generates every combination as a precise literal type. Template literal types power things like typed event names (`` `on${Capitalize<Event>}` ``) and typed object-path strings — expressing string patterns the type system can *check*, not just describe.

## The point: derive, don't duplicate

Step back and the theme is clear: **TypeScript lets you compute types from other types**, so a single source-of-truth type can generate all its variants. Define `User`; derive the create-input with `Omit`, the update-input with `Partial`, the read-only view with `Readonly`, the keys with `keyof`, a lookup table with `Record`. When the source changes, everything derived changes with it — no parallel definitions drifting apart.

This is a genuine mindset shift. In many languages types are static declarations you write out. In TypeScript they're *computed relationships*: `Partial`, mapped types, conditional types, and template literals are a small functional language operating on types. You don't need to write advanced conditional types often, but *reading* them — and reaching for the utility types constantly — is what fluent TypeScript looks like. The practical rule: whenever you're about to hand-write a type that's "like this other type but with a change," there's almost certainly a derivation for it. Derive instead of duplicate, and your types stay correct as your code evolves.

## Key takeaways

- **Utility types** (`Partial`, `Required`, `Pick`, `Omit`, `Record`, `Readonly`) transform object types so you define an entity *once* and derive every related shape (create-input, update-input, lookup table) — which then update automatically when the entity changes.
- **`keyof`** yields a union of a type's keys and **indexed access** (`T["name"]`) yields the type at a key — the raw material for computing new types.
- **Mapped types** (`{ [K in keyof T]: ... }`) are a type-level loop over keys, producing a new property per key; the built-in utilities are mostly thin mapped types, and you can write your own (`Nullable<T>`, `Stringify<T>`) and add/remove `?`/`readonly` modifiers.
- **Conditional types** (`T extends U ? X : Y`) branch on a type test, and with **`infer`** can *extract* types from within others (how `ReturnType`, `Awaited` work) — the deep end you rarely write but should be able to read.
- **Template literal types** build checked string-literal patterns from other types (`` `${Uppercase<Method>} ${Route}` ``), powering typed event names and path strings.
- The mindset shift: **derive types, don't duplicate them** — TypeScript's type system is a small language for computing types, so a single source-of-truth type generates all its variants and stays consistent as code evolves.

## Further reading

- [TypeScript Handbook — Utility Types](https://www.typescriptlang.org/docs/handbook/utility-types.html)
- [TypeScript Handbook — Mapped Types](https://www.typescriptlang.org/docs/handbook/2/mapped-types.html)
