# Collections: Vec, String, and HashMap

*Module 1's arrays and tuples were fixed-size and stack-bound. Real programs need growable, heap-backed collections — and Rust's three workhorses, Vec, String, and HashMap, are where ownership and borrowing stop being abstract rules and become the everyday texture of writing Rust. This opens Module 2: the data structures and abstractions you actually build with.*

Module 1 built Rust's foundations — ownership, borrowing, lifetimes, enums, error handling. Module 2 covers what you build *with* them, starting with the **collections** you'll use constantly: **`Vec<T>`** (a growable list), **`String`** (growable, owned text), and **`HashMap<K, V>`** (key-value lookup). These are heap-backed and dynamically sized, unlike Module 1's fixed arrays and tuples, and working with them is where ownership becomes concrete daily practice. This post covers all three and the ownership patterns they teach.

## Vec: the growable list

**`Vec<T>`** is Rust's growable, heap-allocated list of values of a single type `T` — the collection you reach for most:

```rust
let mut nums: Vec<i32> = Vec::new();
nums.push(1);
nums.push(2);
nums.push(3);

let letters = vec!['a', 'b', 'c'];   // the vec! macro for literals

for n in &nums {                     // iterate by reference (borrow)
    println!("{}", n);
}
println!("first: {}", nums[0]);      // index access
```

A `Vec` owns its elements (they live on the heap), grows as you `push`, and is dropped — freeing its elements — when it goes out of scope (ownership rules from Module 1, applied to a collection). Two Rust-specific things to note:

- **Access safety.** Indexing (`nums[0]`) panics if out of bounds; the safe alternative `nums.get(0)` returns an `Option<&T>` (from the error-handling post) — `Some(&value)` or `None` — so you handle the missing case rather than crash. Rust gives you both: fast-but-panicking indexing, and safe optional access.
- **Borrowing applies.** Iterating with `&nums` borrows the vec immutably; you can't push to a vec while holding an immutable reference into it (the borrowing rule from Module 1) — which prevents the classic "modify a collection while iterating it" bug at compile time. This is where the borrow checker's rules pay off in everyday code.

## String: growable, owned text

Module 1 mentioned `&str` (a string slice) in passing. **`String`** is the growable, heap-allocated, *owned* counterpart — and the `String` vs `&str` distinction is one Rust newcomers must get straight:

- **`String`** — an *owned*, growable, mutable string (like a `Vec<u8>` of UTF-8 text). You own it; it's dropped when it goes out of scope.
- **`&str`** — a *borrowed* string slice: a view into string data someone else owns (a `String`, or a string literal baked into the binary). It doesn't own the text.

```rust
let mut s = String::new();
s.push_str("hello");
s.push(' ');
s.push_str("world");             // s is now "hello world"

let literal: &str = "baked in";  // a &str borrowing static data
let owned: String = literal.to_string();   // convert &str -> owned String
let view: &str = &s;             // borrow a String as a &str
```

The pattern to internalize: **take `&str` as function parameters, return/store `String` when you need ownership.** A function that just reads text should accept `&str` (it can then take both a `String` (via a reference) and a literal — maximum flexibility, no ownership taken); a function that produces or stores text returns/keeps a `String`. This `&str`-for-borrowing, `String`-for-owning split is the string-level expression of the ownership/borrowing model, and getting it right makes string code both efficient and ergonomic. (Also note: Rust strings are UTF-8, so you don't index by byte position casually — you iterate `.chars()` or `.bytes()` — because a `char` may be multiple bytes, the Unicode point from Module 1.)

## HashMap: key-value lookup

**`HashMap<K, V>`** stores key-value pairs with fast lookup by key — Rust's dictionary/map:

```rust
use std::collections::HashMap;

let mut scores: HashMap<String, i32> = HashMap::new();
scores.insert(String::from("alice"), 10);
scores.insert(String::from("bob"), 7);

// safe lookup returns Option<&V>:
match scores.get("alice") {
    Some(score) => println!("alice: {}", score),
    None => println!("no score"),
}

// the entry API: insert-or-update in one idiomatic move
*scores.entry(String::from("alice")).or_insert(0) += 5;   // alice -> 15
```

Two HashMap idioms worth learning:

- **`get` returns `Option<&V>`** — lookup might miss, so (like `Vec::get`) it returns an `Option` you handle, never a null or a crash. Absence is in the type, consistent with Module 1's error handling.
- **The `entry` API** — `entry(key).or_insert(default)` is the idiomatic "get the value for this key, inserting a default if absent" — perfect for counting/accumulating (the counting-words example is the classic use). It returns a mutable reference you can modify in place, avoiding an awkward check-then-insert dance.

Note that `HashMap` needs its keys to be hashable and comparable (they implement the relevant traits — the subject of the traits post), and inserting a `String` key *moves* it into the map (ownership, again). The collection follows the same ownership rules as everything else.

## Collections make ownership concrete

The deeper point of this post: collections are where Module 1's rules become *daily practice*, because collections own their contents and you constantly borrow into them:

- **Ownership of contents** — a `Vec`/`String`/`HashMap` owns its elements/characters/entries, which are freed when the collection drops. Moving a value into a collection moves ownership; the collection is now responsible for it.
- **Borrowing into collections** — you iterate and access by reference (`&vec`, `.get()` returning `Option<&T>`), and the borrow checker prevents mutating a collection while you hold references into it — killing iterator-invalidation and aliasing bugs at compile time.
- **Optional access** — `.get()` returning `Option` (rather than panicking or returning null) makes "the element might not be there" explicit and handled, the Module 1 error-handling philosophy applied to lookups.

So collections aren't just data structures — they're where you *feel* ownership and borrowing working, every day. If Module 1 taught the rules in the abstract, `Vec`/`String`/`HashMap` are where they click into muscle memory. (Rust's standard library has more collections — `VecDeque`, `BTreeMap`, `HashSet`, and others — but these three cover the vast majority of needs and teach the patterns the rest follow.) The next post covers writing code that works over *many* types — generics.

## Key takeaways

- `Vec<T>` is Rust's growable, heap-allocated list: `push` to grow, index (`v[0]`, panics out of bounds) or `.get()` (returns `Option<&T>`, safe), and iterate by reference — with the borrow checker preventing modify-while-iterating bugs at compile time.
- `String` is owned, growable, mutable UTF-8 text; `&str` is a borrowed view into text someone else owns — take `&str` as parameters (accepts both `String` and literals, borrows without taking ownership) and return/store `String` when you need ownership.
- `HashMap<K, V>` is key-value lookup: `get` returns `Option<&V>` (absence in the type, no null/crash), and the `entry(key).or_insert(default)` API is the idiomatic insert-or-update, ideal for counting/accumulating.
- Collections own their contents (freed when the collection drops; inserting moves ownership in) and you borrow into them (references, optional access) — so the borrow checker's rules prevent aliasing/iterator-invalidation bugs in everyday collection code.
- These three (plus `HashSet`, `VecDeque`, `BTreeMap` for special cases) cover most needs and are where Module 1's ownership, borrowing, and Option-based safety become concrete daily practice.

## Further reading

- [Error handling: Result, Option, and no exceptions (Module 1)](/blog/posts/rust-08-error-handling.html)
- [The Rust Book — common collections](https://doc.rust-lang.org/book/ch08-00-common-collections.html)
- [Ownership: Rust's big idea (Module 1)](/blog/posts/rust-04-ownership.html)
