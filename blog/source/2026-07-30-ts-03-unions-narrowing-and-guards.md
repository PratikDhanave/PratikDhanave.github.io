# Unions, Narrowing, and Type Guards

*Union types are TypeScript's way of saying "this could be one of several things," and they're everywhere in real JavaScript — a value that's a string or a number, a result that's data or an error. The companion skill is narrowing: convincing the compiler, through ordinary runtime checks, which member of the union you actually have. Master unions, narrowing, and exhaustiveness and you can model the messy reality of JavaScript data precisely and safely.*

The previous post introduced literal types and promised they'd shine with unions. Here they do. Unions model the fundamental JavaScript reality that a value can be one of several shapes, and *narrowing* is how you safely work with such a value. This is where TypeScript's type system starts to feel genuinely powerful — and where it maps onto how JavaScript is actually written.

## Union types

A **union** type, written with `|`, means "one of these types":

```typescript
type Id = string | number;
function format(id: Id): string {
  return id.toString();   // ok — both string and number have toString
}
```

`id` might be a string or a number. Crucially, TypeScript only lets you access members that exist on *all* members of the union. `id.toUpperCase()` would be an error, because `number` has no `toUpperCase`. The union is honest: until you prove which type you have, you can only use what they share. This safety is the whole point — it forces you to handle the possibility that `id` is either kind.

Unions model countless real patterns: a config value that's `string | undefined`, a function that returns `User | null`, an event that's `ClickEvent | KeyEvent`. Combined with literal types, they express finite sets precisely (`"light" | "dark"`, `1 | 2 | 3`).

## Narrowing: proving which type you have

To use members specific to one union arm, you **narrow** — write a runtime check that TypeScript understands, after which it treats the value as the narrower type *within that branch*. TypeScript recognizes ordinary JavaScript checks as narrowing operations (this is called control-flow analysis):

```typescript
function pad(value: string | number): string {
  if (typeof value === "number") {
    return " ".repeat(value);   // here `value` is number
  }
  return value.trim();          // here `value` is string
}
```

The magic is that these are *normal JavaScript checks* — the same code you'd write anyway — and TypeScript reads them to refine the type per branch. The common narrowing tools:

- **`typeof`** — for primitives: `typeof x === "string"`.
- **`instanceof`** — for classes: `x instanceof Date`.
- **`in`** — for object properties: `"radius" in shape`.
- **Truthiness** — `if (value)` narrows away `null`/`undefined`/`""`/`0`.
- **Equality** — comparing against a literal narrows to that literal.

You don't learn a special "narrowing syntax"; you write the checks you'd write in plain JavaScript, and the compiler follows along, tracking the type down each branch.

## Discriminated unions: the killer pattern

The most powerful application is the **discriminated (tagged) union**: a union of object types that share a common literal-typed field — the *discriminant* — which identifies which member you have. This is the idiomatic way to model "one of several kinds of thing" in TypeScript:

```typescript
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "square"; side: number }
  | { kind: "rect"; width: number; height: number };

function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return Math.PI * s.radius ** 2;  // s is the circle member
    case "square": return s.side ** 2;
    case "rect":   return s.width * s.height;
  }
}
```

Switching on the `kind` field narrows `s` to exactly the right member in each `case`, so `s.radius` is available in the circle branch and nowhere else. This pattern models results, states, events, AST nodes — any "sum type" — with full type safety. It's the TypeScript equivalent of Rust's enums or a tagged union, and it's the single most valuable modeling tool the language offers.

## Exhaustiveness with `never`

Discriminated unions pair with the `never` type (post 2) to give **exhaustiveness checking** — a compile-time guarantee that you've handled every case. Add a `default` that assigns the value to `never`:

```typescript
function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return Math.PI * s.radius ** 2;
    case "square": return s.side ** 2;
    case "rect":   return s.width * s.height;
    default:
      const _exhaustive: never = s;   // ✗ compile error if a case is unhandled
      return _exhaustive;
  }
}
```

Here's why it works: if you've handled every member, then in `default` the type of `s` is narrowed to `never` (nothing left), and assigning `never` to `_exhaustive` is fine. But if you later *add* a fourth shape and forget a `case`, `s` in `default` is that new member — not `never` — and the assignment fails to compile. The compiler *forces* you to handle the new case. This turns "did I update every switch?" from a manual, error-prone audit into a guarantee. It's one of the most practically valuable patterns in TypeScript, and it's why discriminated unions plus `never` are worth internalizing together.

## Custom type guards

Sometimes narrowing needs logic the built-in operators can't express. You write a **type guard**: a function whose return type is a *type predicate* (`x is T`), which tells the compiler "if this returns true, `x` is a `T`":

```typescript
interface User { name: string; email: string; }

function isUser(value: unknown): value is User {
  return typeof value === "object" && value !== null
    && "name" in value && "email" in value;
}

const data: unknown = JSON.parse(input);
if (isUser(data)) {
  console.log(data.email);   // data is narrowed to User here
}
```

Type guards are the bridge from `unknown` to a real type — exactly the safe-boundary pattern from post 2. Parse untyped input into `unknown`, then a type guard both *checks* it at runtime and *narrows* it for the compiler, so you validate and type in one step. This is how you safely bring outside data (API responses, JSON) into your typed world without reaching for `any`.

## Why this is the heart of TypeScript

Unions and narrowing are where TypeScript's design philosophy is clearest: it types *the JavaScript you'd already write*. You model reality with unions ("this is one of these"), then the ordinary runtime checks you'd write anyway (`typeof`, `switch`, property checks) double as type refinements. Discriminated unions give you safe sum types, `never` gives you exhaustiveness, and custom guards bridge untyped input. Together they let you describe messy, real-world JavaScript data with precision and prove — at compile time — that you've handled every case.

## Key takeaways

- A **union type** (`A | B`) means "one of these," and TypeScript only lets you access members common to *all* arms until you prove which one you have — honest safety that forces you to handle every possibility.
- **Narrowing** refines a union within a branch using *ordinary JavaScript checks* the compiler understands — `typeof`, `instanceof`, `in`, truthiness, equality — so you write the code you'd write anyway and get per-branch types.
- **Discriminated (tagged) unions** — a union of objects sharing a literal-typed discriminant (`kind`) — are the idiomatic way to model sum types (results, states, events); switching on the discriminant narrows to the exact member.
- Pair discriminated unions with **`never` for exhaustiveness checking**: a `default` that assigns to `never` fails to compile if you add a case and forget to handle it — turning "did I update every switch?" into a compiler guarantee.
- **Custom type guards** (functions returning `x is T`) bridge `unknown` to real types — validating untyped input (parsed JSON, API data) at runtime *and* narrowing it for the compiler in one step, without resorting to `any`.

## Further reading

- [TypeScript Handbook — Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
- [TypeScript Handbook — Everyday Types (unions)](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html)
