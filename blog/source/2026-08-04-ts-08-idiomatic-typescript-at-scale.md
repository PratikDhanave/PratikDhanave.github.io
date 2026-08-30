# Idiomatic TypeScript at Scale

*Knowing the type system isn't the same as using it well. Idiomatic TypeScript is a set of judgments: lean on inference, avoid `any`, model impossible states out of existence, and know when a type earns its complexity. On a large, long-lived codebase these habits are the difference between types that catch bugs and types that are decorative noise. This closing post turns the mechanics of the series into a working discipline.*

We've built up the whole type system — structural typing, unions, generics, utility types, async, tooling. This final post is about *taste*: how to wield it on real codebases so the types pay for themselves. These are the practices that distinguish TypeScript that prevents production incidents from TypeScript that merely adds ceremony.

## Let inference work; annotate boundaries

The first habit is knowing where types belong. **Annotate the boundaries — function parameters, public API signatures, exported types — and let inference handle the internals.** The compiler already knows that `const total = price * quantity` is a number; restating it adds noise without safety. But a public function's signature is a *contract* others depend on, so make it explicit and stable.

```typescript
// noisy — inference already knows these
const name: string = "Ada";
const items: number[] = [1, 2, 3];

// valuable — the contract is explicit
export function createUser(input: CreateUserInput): Promise<User> { ... }
```

Over-annotating locals makes code harder to read and refactor (every type change means editing two places); under-annotating public functions removes the documentation and safety types exist for. The rule of thumb: if the compiler can obviously infer it and it's local, leave it; if it's a boundary others call across, spell it out.

## Avoid `any`; reach for `unknown`

The most important discipline is treating **`any` as a code smell.** Every `any` is a hole where type checking stops and runtime bugs return — and worse, `any` is *contagious*: it spreads through everything it touches, silently disabling checks far from where you wrote it. A single `any` in a hot path can quietly un-type an entire call chain.

The alternatives, in order of preference:

- **Proper types** — usually you *can* express the real type; do so.
- **`unknown`** for genuinely-untyped input (parsed JSON, `catch` errors, third-party boundaries) — it forces you to narrow before use (post 3), keeping safety instead of discarding it.
- **`any` only as a last resort**, localized and commented, ideally during migration. If you must, contain it — never let it leak into a public signature.

Turn on lint rules (`no-explicit-any`, `no-unsafe-*`) so `any` is a deliberate, visible choice rather than an accident. The `any`-vs-`unknown` reflex is the single clearest marker of TypeScript maturity: mature code narrows `unknown`; immature code sprinkles `any` and wonders why the types didn't catch anything.

## Make impossible states impossible

The highest-leverage idea in typed design: **use the type system so illegal states can't be represented.** If your types allow a combination that should never occur, someone will eventually create it and cause a bug. Model the data so the bad combination doesn't type-check.

The classic example is a loading state modeled as loose booleans:

```typescript
// ✗ allows nonsense: loading && error && data all set, or none
interface State { loading: boolean; data?: Data; error?: string; }
```

This permits `{ loading: true, data: someData, error: "oops" }` — an incoherent state your UI must defensively guard against everywhere. Replace it with a discriminated union (post 3) that permits *only* the valid shapes:

```typescript
// ✓ only the four real states are representable
type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: Data }
  | { status: "error"; error: string };
```

Now `data` exists *only* in the success state, `error` *only* in the error state, and impossible combinations simply won't compile. You've moved a class of bug from "handle defensively at runtime" to "cannot occur." This is type-driven design, and it's where TypeScript delivers its deepest value — not in annotating what exists, but in *making the wrong thing unrepresentable.*

## Prefer precision, within reason

A few smaller judgments compound:

- **Literal unions over loose primitives.** `type Status = "active" | "inactive"` beats `string` — it documents the options and rejects typos. (There's a live debate over `enum` vs. union-of-literals; unions are simpler, erase cleanly, and are increasingly preferred, but consistency matters more than the choice.)
- **`readonly` where things shouldn't change.** Marking properties and arrays `readonly` prevents accidental mutation and communicates intent — cheap safety.
- **Narrow return types.** Returning `User | null` and forcing callers to handle the null is safer than returning `User` and lying.

Each is a small nudge toward types that carry real information rather than rubber-stamping `string` and `object` everywhere.

## Know when types cost more than they're worth

Maturity also means restraint. TypeScript's type system is Turing-complete-adjacent — you *can* build breathtakingly clever conditional-and-mapped-type contraptions. Usually you shouldn't. If a type needs a paragraph of explanation, or an error message it produces is three screens long, the cleverness has become a liability: the next engineer (or you, in six months) can't maintain it.

The judgment: reach for advanced types (post 5) when they *eliminate real duplication or real bugs*, and stop when they're complexity for its own sake. A slightly-less-precise type that everyone understands often beats a perfectly-precise one nobody can modify. Types serve the code and the team; when a type stops paying its way in caught bugs and starts costing in comprehension, simplify it. This is the same restraint good engineers apply to abstraction anywhere.

## Migrating and living with it

For existing JavaScript, adopt TypeScript *incrementally*: allow JS and TS side by side, convert file by file, start with loose settings and ratchet toward `strict` (post 7) as you go. Use `unknown` and honest types at the boundaries first, tighten internals over time, and let each converted module catch its own bugs. The goal is steady progress to `strict`, not a big-bang rewrite.

Pulling the series together: TypeScript is a compile-time structural type checker that erases to JavaScript, and using it *well* is a discipline — infer locally and annotate boundaries, refuse `any` in favor of `unknown` and real types, model your domain so illegal states can't exist, prefer precision where it carries information, and simplify types that cost more than they catch. Do this on a large codebase and the type system stops being ceremony and becomes what it promised at the start of the series: a machine that catches whole categories of bugs before your users ever see them.

## Key takeaways

- **Annotate boundaries, infer internals** — put explicit types on parameters, public signatures, and exported types (they're contracts), and let the compiler infer obvious locals; over-annotating adds noise, under-annotating public APIs removes safety.
- **Treat `any` as a code smell** — it's a contagious hole that silently disables checking; prefer real types, then **`unknown`** (which forces narrowing) for untyped input, and contain `any` to last-resort, commented, migration-only uses (enforce with lint rules).
- **Make impossible states impossible** — model data with discriminated unions so illegal combinations (e.g. `loading && error && data`) simply don't type-check, moving bugs from runtime defense to compile-time impossibility. This is type-driven design's deepest payoff.
- **Prefer precision that carries information** — literal unions over bare `string`, `readonly` where things shouldn't mutate, honest `T | null` return types — small nudges toward types that mean something.
- **Know when types cost more than they're worth** — reach for advanced types when they eliminate real duplication or bugs, but simplify clever contraptions that hurt comprehension; a maintainable type beats a perfectly-precise unmaintainable one.
- **Migrate incrementally** toward `strict` (JS and TS side by side, file by file, boundaries first) — the destination is `strict`-on, type-driven code where the compiler catches whole bug categories before users do.

## Further reading

- [TypeScript Handbook — Narrowing (discriminated unions)](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
- [TSConfig Reference — strict](https://www.typescriptlang.org/tsconfig/)
