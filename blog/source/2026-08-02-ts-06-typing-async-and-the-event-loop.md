# Typing Async Code and the Event Loop

*Almost everything interesting in JavaScript is asynchronous — network calls, file reads, timers — and TypeScript types all of it through one generic: `Promise<T>`. But typing async code well means understanding the runtime it describes: the single-threaded event loop that makes non-blocking concurrency work. Types and runtime together are what let you write async code that's both correct and comprehensible.*

We've built up the type system; now we point it at the defining feature of JavaScript execution: asynchrony. This post covers how TypeScript types promises and `async`/`await`, and — just as important — the event-loop model those types sit on top of. You can't type async code confidently without a mental model of how it actually runs.

## The event loop, briefly

JavaScript is **single-threaded**: one call stack, one thing executing at a time. Yet it handles thousands of concurrent connections without blocking. The trick is the **event loop**. When you start an async operation (a network request, a timer), JavaScript doesn't wait — it hands the operation off (to the browser or Node runtime) and keeps running. When the operation completes, its callback is placed on a queue, and the event loop runs that callback once the call stack is empty.

The consequences shape everything:

- **Non-blocking, not parallel.** Async code doesn't run *simultaneously* on multiple threads; it *interleaves* on one thread. While a network request is in flight, other code runs; when the response arrives, its handler is scheduled. Concurrency without parallelism.
- **Your code runs to completion before any callback.** A queued callback never interrupts running synchronous code — it waits until the stack clears. This is why a long synchronous loop *freezes* everything, including UI, until it finishes.
- **Order is subtle.** Microtasks (promise callbacks) run before macrotasks (timers), so `Promise.resolve().then(...)` fires before a `setTimeout(..., 0)`. You rarely depend on this, but it explains surprising orderings.

This model — single thread, non-blocking handoff, callbacks scheduled on completion — is what promises and `async`/`await` are ergonomic wrappers around. The types describe it; the event loop runs it.

## `Promise<T>`: the type of a future value

A **`Promise<T>`** represents a value of type `T` that will exist *later* — the type-level encoding of "this async operation will eventually produce a `T` (or fail)." It's just a generic (post 4), and it's how TypeScript types every async result:

```typescript
function fetchUser(id: number): Promise<User> {
  return fetch(`/api/users/${id}`).then(res => res.json());
}
```

The signature says: call this and you get back not a `User` but a *promise of* a `User`. The `<T>` flows through: a `Promise<User>` resolves to a `User`, a `Promise<string>` to a `string`. This makes async return types honest — the caller can *see* in the type that the value is deferred and must be awaited, which is exactly the information you need.

## `async`/`await`: promises, readably

`async`/`await` is syntactic sugar over promises that lets asynchronous code *read* like synchronous code, and TypeScript types it seamlessly:

```typescript
async function loadProfile(id: number): Promise<Profile> {
  const user = await fetchUser(id);      // user: User (awaited out of Promise<User>)
  const posts = await fetchPosts(id);    // posts: Post[]
  return { user, posts };
}
```

Two typing facts to internalize:

- **`async` functions always return a `Promise`.** Even though `loadProfile` `return`s a `Profile`, its type is `Promise<Profile>` — the `async` keyword wraps the return value in a promise automatically. You never return a bare value from an async function; the runtime and the types both promise-wrap it.
- **`await` unwraps the promise's type.** `await fetchUser(id)` has type `User`, not `Promise<User>` — `await` strips one layer of promise. This is why awaited code reads like ordinary synchronous code: the types line up as if the values were immediate, even though under the hood the event loop is scheduling continuations.

Crucially, `await` doesn't block the thread — it *yields* to the event loop, letting other work run until the promise resolves, then resumes. The synchronous *appearance* hides asynchronous *execution*. That's the whole point, and the types support the illusion perfectly.

## Concurrency: awaiting in parallel

A common performance bug is awaiting sequentially when you could await concurrently. `loadProfile` above fetches the user, *then* the posts — two round-trips back to back. If they're independent, run them together:

```typescript
const [user, posts] = await Promise.all([fetchUser(id), fetchPosts(id)]);
// user: User, posts: Post[]  — both in flight at once, ~half the latency
```

`Promise.all` takes an array of promises and returns a promise of an array of their resolved values — and TypeScript types the result tuple precisely, so `user` and `posts` keep their exact types. This is the event-loop model paying off: the two requests interleave on the single thread, both in flight, and you wait once for the slower. Related combinators — `Promise.allSettled` (wait for all, successes and failures), `Promise.race` (first to settle) — are typed just as precisely. Knowing when to `Promise.all` versus sequential `await` is one of the highest-leverage async skills, and the types make it safe.

## Typing errors in async code

Async errors are where the type system reaches its honest limit. A rejected promise (or a `throw` inside `async`) surfaces at the `await`, caught with `try/catch`:

```typescript
try {
  const user = await fetchUser(id);
} catch (err) {
  // err is `unknown` (or `any`) — TypeScript can't know what was thrown
}
```

Here's the catch (literally): **the caught error is typed `unknown`**, because JavaScript lets you `throw` *anything* — an `Error`, a string, an object — so the compiler can't assume it's an `Error`. This is correct and important: you must *narrow* the error (post 3) before using it — `if (err instanceof Error) { err.message }` — rather than blindly accessing `.message`. It's the same boundary-safety lesson as parsing untyped input: `Promise<T>` types the *success* value precisely, but the *failure* path is untyped by necessity, so handle it with narrowing. (This is also why the `Result<T>` pattern from post 4 appeals to some teams — it moves errors into the typed return value instead of the untyped throw channel.)

## Why runtime and types go together

The lesson of this post is that typing async code well requires *both* halves. The types — `Promise<T>`, `async` returning a promise, `await` unwrapping it, `Promise.all` preserving tuples — give you precise, honest signatures for deferred values. The event-loop model — single-threaded, non-blocking, callbacks scheduled on completion — explains what those types *mean* at runtime: why `await` doesn't block, why `Promise.all` speeds things up, why a synchronous loop freezes the app. Hold both and async TypeScript stops being a source of mysterious bugs and becomes what it's designed to be: asynchronous execution that reads like synchronous code, with the type system tracking exactly which values are deferred.

## Key takeaways

- JavaScript is **single-threaded with an event loop**: async operations are handed off and their callbacks scheduled on completion, giving **non-blocking concurrency without parallelism** — interleaving on one thread, so a long synchronous loop freezes everything.
- **`Promise<T>`** is a generic for "a `T` that will exist later," making async return types honest — the caller sees the value is deferred and must be awaited.
- **`async` functions always return a `Promise`** (the return value is auto-wrapped), and **`await` unwraps one promise layer** (`await fetchUser()` is `User`, not `Promise<User>`) while *yielding* to the event loop rather than blocking — which is why awaited code reads synchronously.
- Run independent async work **concurrently with `Promise.all`** (both in flight, wait once for the slower), which TypeScript types as a precise tuple — knowing when to parallelize vs. sequential-await is a high-leverage skill.
- **Caught async errors are typed `unknown`** because JS can `throw` anything — you must *narrow* (e.g. `err instanceof Error`) before use; `Promise<T>` types the success value but the failure path is untyped by necessity.
- Typing async well requires **both the types and the event-loop model** — the types say which values are deferred; the runtime model explains why `await` doesn't block and `Promise.all` speeds things up.

## Further reading

- [MDN — The event loop](https://developer.mozilla.org/en-US/docs/Web/JavaScript/EventLoop)
- [TypeScript Handbook — Everyday Types](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html)
