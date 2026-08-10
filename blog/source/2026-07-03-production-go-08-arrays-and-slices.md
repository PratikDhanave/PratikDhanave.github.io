# Arrays and Slices

*Why an array is a value and a slice is a view — the three-word header, how `append` really grows, the aliasing trap that silently corrupts data, and the small habits (three-index slices, `copy`, pre-sizing) that keep it from biting you.*

---

Almost everyone reaching for Go already knows the *shape* of a slice: it grows, you `append` to it, you range over it. What separates code that merely works from code that behaves under load is understanding what a slice **is** — a small header pointing at a backing array it does not necessarily own. Get that wrong and you produce one of Go's nastier bug classes: two slices that look independent but share memory, where writing to one silently rewrites the other. This post builds the model from the bottom: fixed-size arrays first, then the slice header, then the growth and aliasing rules that follow directly from it.

---

## 1. Arrays are values, and values get copied

An array's length is part of its type. `[3]int` and `[4]int` are as different as `int` and `string` — you cannot assign one to the other, and a function that takes `[3]int` will not accept `[4]int`. The length is fixed at compile time and can never change.

The consequence that trips people is that **an array is a value**. Assigning it, or passing it to a function, copies every element.

```go
func zero(a [3]int) {
	a[0] = 0 // mutates the copy, not the caller's array
}

func main() {
	nums := [3]int{1, 2, 3}
	clone := nums // full copy of all three elements
	clone[0] = 99
	fmt.Println(nums[0], clone[0]) // 1 99

	zero(nums)
	fmt.Println(nums[0]) // still 1
}
```

This is occasionally what you want — a small, fixed-shape value like an RGBA pixel `[4]uint8` or a hash `[32]byte` that you *want* to pass by value cheaply and mutate locally without touching the original. But most day-to-day "list of things" work does not want copy-on-pass semantics, and that is exactly why slices exist.

**The gotcha:** because the length is part of the type, arrays don't compose with generic list-handling code. You almost never write array parameters directly. When you see `[N]T` in real code it's usually a deliberate fixed-width value (a key, a coordinate, a fixed lookup table) — not a collection you plan to grow. For everything else, reach for a slice.

---

## 2. The slice header: pointer, length, capacity

A slice is not an array. It is a small three-word struct — the *slice header* — that **describes a window into an array**:

- **pointer** — where the window starts in some backing array
- **length** — how many elements the window currently exposes (`len(s)`)
- **capacity** — how many elements exist from the pointer to the end of the backing array (`cap(s)`)

That is the whole model. Everything else — growth, aliasing, `copy`, three-index slicing — is a consequence of these three fields.

```go
s := make([]int, 3, 8) // len 3, cap 8
fmt.Println(len(s), cap(s)) // 3 8

s = s[:5]                   // extend the window within existing capacity
fmt.Println(len(s), cap(s)) // 5 8 — no allocation, same backing array
```

Because the header is small and fixed-size, **passing a slice to a function is cheap** — you copy three words, not the elements. But that copied header still points at the *same backing array*. So a function can mutate the elements the caller sees (writing through the shared pointer) even though it cannot change the caller's `len`/`cap` (those live in the caller's own copy of the header). That asymmetry is the source of most slice surprises, and the next sections are all downstream of it.

```go
func fill(s []int) {
	for i := range s {
		s[i] = i // visible to the caller — shared backing array
	}
	s = append(s, 999) // NOT visible to the caller — reassigns the local header
}
```

---

## 3. How `append` grows — mutate in place, or reallocate

`append` is where the length/capacity distinction earns its keep. The rule:

- If the slice has **spare capacity** (`len < cap`), `append` writes into the existing backing array in place and returns a header with a larger `len`. No allocation.
- If it is **full** (`len == cap`), `append` allocates a *new, larger* backing array, copies the existing elements over, writes the new one, and returns a header pointing at the new array. The old backing array is left behind.

```go
s := make([]int, 0, 4)
fmt.Printf("%p cap=%d\n", s, cap(s)) // some address, cap 4

s = append(s, 1, 2, 3, 4) // fills to len 4, still cap 4, same array
fmt.Printf("%p cap=%d\n", s, cap(s)) // same address, cap 4

s = append(s, 5) // full — reallocates
fmt.Printf("%p cap=%d\n", s, cap(s)) // NEW address, larger cap
```

The growth is **amortized**: for small slices the runtime roughly doubles the capacity, which makes a sequence of `n` appends cost O(n) total rather than O(n²). For large slices Go switches to a smaller growth factor (closer to ~1.25×) so a huge slice doesn't jump from, say, 512 MB to 1 GB on a single append. The exact thresholds and factors are runtime implementation details and have changed across Go versions — don't hard-code assumptions about them. What is stable and worth internalizing is the *shape*: appends are cheap on average, but any individual `append` may reallocate and copy, and after it does, **your slice points at different memory than it did a line earlier**.

**The gotcha:** this is why the canonical form is always `s = append(s, x)` — you must capture the returned header, because it may point at a brand-new array. Ignoring the return value (`append(s, x)` with no assignment) is a bug: if a reallocation happened, your `s` still points at the old array and you've lost the appended element. `go vet` flags this, but the habit should be automatic.

---

## 4. The aliasing trap: subslices share the backing array

Slicing an existing slice — `s[low:high]` — does **not** copy anything. It produces a new header pointing into the *same* backing array. The subslice and its parent now alias overlapping memory. Writes through one are visible through the other, and this is where correct-looking code goes wrong.

The dangerous case is `append` onto a subslice that still has spare capacity. Because `s[low:high]` inherits capacity all the way to the end of the parent's backing array, an `append` onto the subslice can land **inside the parent's live region** and silently overwrite it:

```go
parent := []int{1, 2, 3, 4, 5}
head := parent[0:2] // len 2, but cap 5 — reaches the end of parent
fmt.Println(len(head), cap(head)) // 2 5

head = append(head, 99) // spare capacity exists, so this writes IN PLACE
fmt.Println(head)       // [1 2 99]
fmt.Println(parent)     // [1 2 99 4 5]  ← parent[2] was clobbered!
```

Nobody wrote to `parent[2]` directly, yet it changed. The `append` onto `head` had room in the shared backing array and used it. This is the bug behind a whole family of "why did my other variable change?" reports — a function returns a subslice of some buffer, the caller appends to it, and the append reaches back into memory the buffer still considers live.

Worse, the behavior is *conditional on capacity*, so it's non-deterministic across inputs: if the subslice happens to be at full capacity, `append` reallocates and the parent is untouched; if it has spare room, the parent is corrupted. Code that passes every small test can fail once the data gets large enough (or small enough) to flip which branch runs.

---

## 5. Fixing aliasing: three-index slices and `copy`

There are two clean fixes, and which you want depends on whether you need a *view* or a *separate buffer*.

**Three-index slicing** — `s[low:high:max]` — sets the capacity explicitly: the resulting slice has `cap == max - low`. Cap it to the length and any future `append` is *forced* to reallocate rather than reach into the parent:

```go
parent := []int{1, 2, 3, 4, 5}
head := parent[0:2:2] // len 2, cap 2 — the third index caps capacity
fmt.Println(len(head), cap(head)) // 2 2

head = append(head, 99) // no spare capacity, so append REALLOCATES
fmt.Println(head)       // [1 2 99]
fmt.Println(parent)     // [1 2 3 4 5] ← untouched
```

This is the idiomatic guard when you hand a subslice to code that might append to it — especially a library returning a slice of an internal buffer. Capping capacity makes accidental aliasing impossible: the next `append` is guaranteed to get its own array.

**`copy`** — when you want a genuinely independent slice from the start, allocate one and copy the elements over. `copy(dst, src)` copies `min(len(dst), len(src))` elements and returns that count; it never grows `dst`.

```go
src := []int{1, 2, 3, 4, 5}
dst := make([]int, len(src)) // must be pre-sized — copy won't extend it
n := copy(dst, src)
fmt.Println(n, dst) // 5 [1 2 3 4 5] — fully independent backing array
```

A frequent mistake is `copy(dst, src)` where `dst` was made with `make([]int, 0, len(src))` — length zero, so `copy` copies **zero** elements and returns 0. `copy` is bounded by `len(dst)`, not `cap(dst)`. Size the destination by length.

**The gotcha:** returning `s[i:j]` of a buffer you keep reusing is the classic footgun — the caller now holds a window into memory you're about to overwrite, and if they append into its spare capacity they'll corrupt your buffer (or you'll corrupt their data next cycle). Either return `s[i:j:j]` to cap it, or return a `copy` if the caller needs to outlive your buffer. There is no runtime warning for this — it's on you to know which side owns the memory.

---

## 6. `nil` vs. empty, and pre-sizing with `make`

A `nil` slice and an empty-but-non-nil slice are *almost* interchangeable, and knowing where they differ prevents a small class of bugs.

A `nil` slice has no backing array: pointer nil, `len` 0, `cap` 0. An empty slice (`[]int{}` or `make([]int, 0)`) has `len` 0 but may hold a (possibly zero-length) backing array and is **not** `nil`. The good news is that the read-side operations treat them identically:

```go
var a []int          // nil
b := []int{}         // empty, non-nil

fmt.Println(a == nil, b == nil) // true false
fmt.Println(len(a), len(b))     // 0 0

a = append(a, 1) // appending to nil is perfectly fine
b = append(b, 1) // same result
```

`len`, `range`, and `append` all work on a `nil` slice — so **prefer `nil` as your zero-value empty slice** and don't reach for `[]int{}` reflexively. The distinction matters in exactly two places: an explicit `== nil` check, and serialization — `encoding/json` marshals a `nil` slice as `null` but an empty slice as `[]`. If your API contract says "always emit an array," initialize with `[]T{}`.

**Pre-sizing** is the performance lever that falls out of the growth model. If you know (even approximately) how many elements you'll add, tell `make` up front so `append` never has to reallocate and copy:

```go
// Bad: starts at cap 0, reallocates and copies repeatedly as it grows.
out := []Result{}
for _, r := range rows {
	out = append(out, transform(r))
}

// Good: one allocation, zero reallocations.
out := make([]Result, 0, len(rows))
for _, r := range rows {
	out = append(out, transform(r))
}
```

Note the `0` length with `len(rows)` capacity — you want an *empty* slice with room reserved, then `append` into the reserved space. A common slip is `make([]Result, len(rows))` (length, not capacity), which pre-fills the slice with zero values and then `append` adds *after* them, giving you a slice twice the size with garbage in front.

**The gotcha:** pre-sizing is not just fewer allocations — it also determines whether the slice can escape to the heap. A tight `append` loop on a growing slice creates repeated allocation churn the garbage collector must clean up; reserving capacity once collapses that to a single allocation. The interaction between slice growth, stack-vs-heap placement, and escape analysis is a topic in its own right — covered in the post on escape analysis and allocation — but the practical rule is simple: **if you know the size, pass it to `make`.**

---

## Quick reference

| Operation | Copies data? | Shares backing array? | Notes |
|---|---|---|---|
| `b := a` where `a` is `[N]T` | Yes, all elements | No | Arrays are values |
| `b := a` where `a` is `[]T` | No | Yes | Copies the 3-word header only |
| `s[low:high]` | No | Yes | Inherits cap to end of parent — aliasing risk |
| `s[low:high:max]` | No | Yes, but capped | `append` forced to reallocate past `max` |
| `append` with `len < cap` | No | Yes | In-place write, no allocation |
| `append` with `len == cap` | Yes | No (new array) | Reallocates and copies |
| `copy(dst, src)` | Yes | No | Bounded by `len(dst)`, not cap |

---

## Key takeaways

- **Arrays are values; slices are views.** Assigning or passing an array copies every element; assigning or passing a slice copies a three-word header that still points at shared memory.
- **The header is everything.** Pointer, length, capacity — growth, aliasing, `copy`, and three-index slicing all follow directly from those three fields.
- **`append` may reallocate.** Below capacity it mutates in place; at capacity it allocates a new array and copies. Always write `s = append(s, x)` to capture the possibly-new header.
- **Subslices alias their parent.** `s[low:high]` shares the backing array *and* inherits capacity to the end, so an `append` onto the subslice can clobber the parent — non-deterministically, depending on spare capacity.
- **Cap capacity to break aliasing.** Use `s[low:high:high]` when handing out a subslice, or `copy` into a fresh, length-sized slice when the caller needs independent memory.
- **Prefer `nil` for the empty slice**, watch the `null`-vs-`[]` JSON difference, and **pre-size with `make([]T, 0, n)`** whenever you know the count.

The single mental model to carry away: a slice is a *description of a window*, not the data itself. Two windows can look at the same glass. Every slice bug is a moment where you forgot that.

---

## Further reading

- [Go Slices: usage and internals](https://go.dev/blog/slices-intro) — the canonical walk-through of the slice header, `append`, and `copy`.
- [Arrays, slices (and strings): the mechanics of 'append'](https://go.dev/blog/slices) — a deeper dive into how `append` grows a backing array and why the return value matters.
