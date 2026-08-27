# Unsafe Rust

*There is a keyword in Rust that feels almost heretical given everything the language stands for: `unsafe`. It exists because Rust's safety guarantees, powerful as they are, are necessarily conservative — the compiler rejects some things that are actually fine, and some low-level operations (talking to hardware, calling C, building certain data structures) genuinely require capabilities the safe subset forbids. `unsafe` is the escape hatch, and understanding it — what it does, what it doesn't, and how to use it responsibly — completes the picture of how Rust achieves safety.*

This post covers **unsafe Rust** — the `unsafe` keyword and the capabilities it unlocks. It explains why unsafe exists, what its "superpowers" are (especially raw pointers), what unsafe does *not* turn off, and the crucial practice of building *safe abstractions* over unsafe code. Understanding unsafe completes the story of Rust's safety: safe Rust is built *on* a small amount of carefully-managed unsafe. Used well, it's a controlled tool, not a hole in the guarantees.

## Why unsafe exists

**Unsafe Rust** exists because the compiler's safety checks are *necessarily conservative*, and some operations genuinely need capabilities safe Rust forbids:

- **The safety checks are conservative.** Rust's borrow checker and safety rules are *conservative* — to *guarantee* safety, they *reject* some programs that are *actually* fine (the compiler can't prove them safe, so it rejects them). Sometimes *you* know something is safe that the compiler can't verify. Conservative checks reject some valid programs. The compiler errs toward rejecting.
- **Some low-level operations require it.** Certain operations are *inherently* beyond safe Rust's guarantees — interacting with *hardware*, calling *C code* (FFI — the next post), and building some *low-level data structures* (that require raw pointer manipulation). These *need* capabilities safe Rust doesn't allow. Low-level work needs unsafe. Hardware, FFI, low-level structures.
- **`unsafe` is the escape hatch.** The `unsafe` keyword lets you tell the compiler "*I* take responsibility for the safety here" — unlocking capabilities safe Rust forbids, in a clearly-marked block. It's an *escape hatch* for when you need more than safe Rust allows (and can ensure safety yourself). `unsafe` = "trust me, I've ensured safety." A marked escape hatch.
- **It's necessary but should be rare.** Unsafe is *necessary* (for the reasons above) but should be *rare* and *carefully contained* — most Rust is safe, with unsafe used sparingly where genuinely needed. Rust *is* a systems language *because* it has unsafe (for low-level work), but its *safety* comes from keeping unsafe minimal and contained. Unsafe: necessary, rare, contained. Sparingly and carefully.

Unsafe Rust exists because the safety checks are conservative (rejecting some valid programs) and some low-level operations (hardware, FFI, certain data structures) genuinely need capabilities safe Rust forbids — so `unsafe` is a carefully-marked escape hatch where *you* take responsibility for safety. It should be rare and contained. What it unlocks is a specific, limited set of powers.

## What unsafe unlocks (and what it doesn't)

The `unsafe` keyword unlocks *five* specific capabilities ("superpowers") — and, crucially, does *not* turn off Rust's other safety checks:

- **The five unsafe superpowers.** `unsafe` lets you: (1) *dereference raw pointers* (below), (2) *call unsafe functions/methods* (including FFI — next post), (3) *access/modify mutable static variables*, (4) *implement unsafe traits*, and (5) *access fields of unions*. These are the *only* things `unsafe` unlocks — a *specific, limited* set. Five specific extra capabilities. Not unlimited power.
- **Unsafe does NOT turn off the borrow checker.** Crucially, `unsafe` does *not* disable the *rest* of Rust's safety — the *borrow checker still runs*, ownership still applies, and all other checks remain *inside* an `unsafe` block. `unsafe` *only* unlocks the five superpowers; everything else stays safe. `unsafe` ≠ "anything goes." Most checks still apply. It's not a free-for-all.
- **It's a small, marked scope.** `unsafe` is used in a *block* (`unsafe { ... }`) or on a *function* — a *marked, contained* scope where the extra capabilities are available. This *marking* is valuable: unsafe code is *visible* (you can find and scrutinize the `unsafe` blocks), unlike languages where everything is "unsafe." Unsafe is marked and localized. Findable and scrutinizable.
- **The marking enables auditing.** Because unsafe is *explicitly marked*, you can *audit* it — safety review focuses on the (small) `unsafe` blocks (where safety isn't compiler-guaranteed), trusting the (large) safe rest. This *containment and visibility* is central to Rust's approach: minimize and mark unsafe, so it's auditable. Marked unsafe is auditable. Concentrate scrutiny where it's needed.

`unsafe` unlocks exactly five capabilities (dereference raw pointers, call unsafe functions, access mutable statics, implement unsafe traits, access union fields) and does *not* turn off the borrow checker or other safety — it's a small, marked, contained scope, and the marking makes unsafe *auditable* (concentrating scrutiny). The most common superpower is raw pointers.

## Raw pointers

**Raw pointers** (`*const T` and `*mut T`) are the most common unsafe capability — pointers *without* Rust's safety guarantees, needed for low-level work:

```rust
fn main() {
    let mut num = 5;

    // Creating raw pointers is safe; dereferencing them requires `unsafe`.
    let r1 = &num as *const i32; // immutable raw pointer
    let r2 = &mut num as *mut i32; // mutable raw pointer

    unsafe {
        println!("r1 is: {}", *r1); // dereferencing requires unsafe
        *r2 = 10;
        println!("r2 is: {}", *r2);
    }
}
```

- **Raw pointers lack the guarantees of references.** *Raw pointers* (`*const T`, `*mut T`) are like references but *without* Rust's guarantees: they *can* be null, dangling, or unaligned, they *ignore* the borrowing rules (you can have multiple mutable raw pointers), and they aren't automatically cleaned up. They're *unchecked* pointers. Pointers without safety guarantees. Like C pointers.
- **Creating them is safe; dereferencing is unsafe.** You can *create* raw pointers in *safe* code (just making a pointer isn't dangerous) — but *dereferencing* them (accessing what they point to) requires `unsafe` (because the pointer might be invalid — that's where the danger is). Create in safe, dereference in unsafe. The danger is dereferencing.
- **Why raw pointers: low-level work.** Raw pointers are needed for *interfacing with C* (FFI — next post), *building low-level data structures* (some structures need pointer manipulation the borrow checker forbids), and *performance-critical* code. They're the tool for when Rust's safe references aren't enough. Raw pointers for low-level needs. Beyond safe references.
- **Use them carefully (the safety is on you).** With raw pointers, *you* are responsible for safety (valid, non-null, properly aligned, no data races) — the compiler *doesn't* check. Misusing them causes *undefined behavior* (the exact thing Rust normally prevents). So raw pointers demand *care*. Raw pointers put safety on you. Undefined behavior if misused.

Raw pointers (`*const T`, `*mut T`) are the most common unsafe capability — pointers without Rust's guarantees (can be null/dangling, ignore borrowing rules) — safe to *create* but requiring `unsafe` to *dereference* (where the danger is), used for FFI, low-level data structures, and performance, with safety being *your* responsibility. The key discipline is wrapping unsafe in safe abstractions.

## Safe abstractions over unsafe

The crucial practice: **wrap unsafe code in a safe abstraction** — a safe API whose *implementation* uses unsafe but whose *interface* is safe and correct:

- **Wrap unsafe in a safe API.** The idiomatic pattern: use `unsafe` *internally* (in the implementation) but expose a *safe* API — the unsafe is *contained inside*, and callers use a *safe* interface (that the author has ensured is actually safe). Contain unsafe behind a safe interface. Unsafe inside, safe outside.
- **The standard library does this everywhere.** Much of the standard library is *safe abstractions over unsafe* — `Vec`, `Rc`, `Mutex`, etc. use `unsafe` internally (raw pointers, etc.) but expose *safe* APIs. You use safe `Vec` daily; its *implementation* uses unsafe, *contained* and *verified* by its authors. Safe std built on contained unsafe. You use it safely without knowing.
- **Why this works.** This works because the *unsafe is contained and verified*: the author ensures the *unsafe implementation* upholds safety (so the *safe API* really is safe), and callers get safety *without* writing unsafe. Contained, verified unsafe → safe abstractions → safe usage. This is *how* Rust's safety scales: a small, audited unsafe core under a large safe surface. Contained unsafe enables safe abstractions. The core pattern.
- **Minimize and encapsulate unsafe.** The discipline: *minimize* unsafe (use it only where necessary), *encapsulate* it (in safe abstractions), and *carefully verify* the unsafe parts (ensuring the safe API is truly safe). Minimal, encapsulated, verified unsafe is how you use it responsibly. Minimize, encapsulate, verify. Responsible unsafe.

Unsafe Rust — the escape hatch unlocking five specific capabilities (chiefly raw pointers) where safe Rust's conservative checks or low-level needs require it — does *not* turn off the borrow checker, is marked and auditable, and is used responsibly by *wrapping it in safe abstractions* (a small verified unsafe core under a large safe surface, as the standard library does). This completes how Rust achieves safety: safe Rust built on minimal, contained unsafe. Next: FFI, a major use of unsafe. 

## Key takeaways

- Unsafe Rust exists because the safety checks are *conservative* (rejecting some programs that are actually fine) and some operations genuinely need more than safe Rust allows (interacting with hardware, calling C via FFI, building certain low-level data structures) — so `unsafe` is a marked escape hatch where *you* take responsibility for safety; it should be rare and contained.
- `unsafe` unlocks exactly five capabilities (dereference raw pointers, call unsafe functions/methods, access/modify mutable statics, implement unsafe traits, access union fields) and does *NOT* turn off the rest of Rust's safety — the borrow checker and ownership still apply inside `unsafe` blocks — so it's not "anything goes," and its marking makes unsafe code findable and auditable.
- Raw pointers (`*const T`, `*mut T`) are the most common unsafe capability — pointers without Rust's guarantees (can be null/dangling/unaligned, ignore the borrowing rules) — that are *safe to create* but require `unsafe` to *dereference* (where the danger is), used for FFI, low-level data structures, and performance, with safety being your responsibility (misuse causes undefined behavior).
- The crucial responsible-use practice is wrapping unsafe in a *safe abstraction*: use `unsafe` internally but expose a safe, verified API — as the standard library does throughout (`Vec`, `Rc`, `Mutex` use unsafe internally but present safe interfaces you use daily without knowing).
- This is how Rust's safety scales: a small, audited unsafe core under a large safe surface — so the discipline is to *minimize* unsafe (only where necessary), *encapsulate* it (in safe abstractions), and *carefully verify* the unsafe parts so the safe API is truly safe.

## Further reading

- [The Rust Book — Unsafe Rust](https://doc.rust-lang.org/book/ch20-01-unsafe-rust.html)
- [Advanced types (previous post)](/blog/posts/rust-26-advanced-types.html)
- [Rust: Ownership — the safety unsafe carefully steps around (Module 1)](/blog/posts/rust-04-ownership.html)
