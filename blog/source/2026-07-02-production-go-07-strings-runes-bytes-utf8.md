# Strings, Runes, Bytes, and UTF-8

*What a Go string actually is under the hood — an immutable read-only slice of bytes, not a sequence of characters — and how bytes, runes, and code points relate, so you stop shipping the classic multibyte bugs.*

---

Almost everyone who writes Go carries an unexamined assumption from other languages: that a string is a sequence of characters and that `s[0]` gives you the first character. In Go, both are wrong, and the gap between what you assume and what's true is where a whole family of production bugs lives — truncated user names, mangled emoji, `substring` calls that split a character down the middle, "uppercase" functions that quietly ignore half the world's alphabets.

The fix isn't a library. It's a precise mental model of four things — **bytes**, **runes**, **code points**, and **characters** — and the knowledge that Go conflates none of them by accident. Once the model clicks, the standard library (`strings`, `bytes`, `unicode`, `unicode/utf8`) stops feeling like a grab bag and starts feeling like a coherent toolkit. This guide builds that model from the byte up.

---

## 1. A string is an immutable slice of bytes

Start with the definition, because everything follows from it. A Go string is a read-only sequence of bytes. Not characters — bytes. The runtime represents it as a two-word header: a pointer to the backing array and a length. That's it.

```go
s := "héllo"
fmt.Println(len(s)) // 6, not 5 — the é is two bytes

for i := 0; i < len(s); i++ {
	fmt.Printf("%d ", s[i]) // prints byte values: 104 195 169 108 108 111
}
```

Two consequences fall out of "read-only slice of bytes" immediately. First, `len(s)` is the **byte count**, and for any non-ASCII text it will not equal what a human calls the length. Second, strings are immutable — you cannot assign to `s[i]`. The compiler rejects it:

```go
s := "hello"
s[0] = 'H' // compile error: cannot assign to s[0]
```

Immutability is a feature, not a limitation. It's why strings are safe to share across goroutines without copying, why they work as map keys, and why slicing a string is cheap — `s[1:4]` creates a new header pointing into the *same* backing array, no allocation, no copy.

**The gotcha:** because a slice of a string shares the backing array, holding a tiny substring of a huge string keeps the *entire* original alive in memory. `header := hugeString[:20]` pins all of `hugeString` until `header` is collected. When you slice a small piece out of a large string and expect to hold it long-term, force a copy with `strings.Clone(header)` (Go 1.18+) so the GC can free the original.

---

## 2. Source is UTF-8, and so is everything else

Go source files are defined to be UTF-8. That single decision cascades: a string literal in your source is stored as the UTF-8 encoding of the text you typed. When you write `"café"`, the bytes in the compiled binary are the UTF-8 bytes for those four characters — the `é` becomes the two-byte sequence `0xC3 0xA9`.

UTF-8 is a variable-width encoding. A code point takes one to four bytes:

- ASCII (U+0000–U+007F) → 1 byte, identical to plain ASCII
- Most Latin-with-accents, Greek, Cyrillic, Hebrew, Arabic → 2 bytes
- The rest of the Basic Multilingual Plane, including most CJK → 3 bytes
- Emoji, rare CJK, and everything above U+FFFF → 4 bytes

The elegance is backward compatibility: valid ASCII is valid UTF-8 with no change, so any ASCII-only string behaves exactly the way your intuition expects. The bugs only appear the moment real user data — a name, an address, a message — steps outside ASCII.

```go
s := "Go💙"
fmt.Println(len(s)) // 6: 'G'(1) + 'o'(1) + '💙'(4) — the heart is a 4-byte code point
```

Nothing in the string header tells you where one character ends and the next begins. That boundary information is encoded *in the bytes themselves*, per the UTF-8 rules, and decoding it is what the rune-aware tools do for you.

---

## 3. Runes are code points; characters are something else again

A **rune** is Go's name for a Unicode code point. It's an alias for `int32`, and a rune literal uses single quotes:

```go
var r rune = '💙'
fmt.Println(r)          // 128153 — the numeric code point
fmt.Printf("%U\n", r)   // U+1F499 — the standard notation
fmt.Printf("%c\n", r)   // 💙 — rendered
```

So we have a three-level hierarchy, and it pays to keep the terms straight:

- **Byte** — a `uint8`; the unit of storage. UTF-8 encodes code points into one or more bytes.
- **Rune / code point** — an `int32`; a single Unicode scalar value. `'A'`, `'é'`, `'💙'` are each one rune.
- **Character** — a human-perceived symbol (a *grapheme cluster*). This is **not** the same as a rune.

That last distinction trips up even experienced engineers. A "character" as a person sees it can be built from several code points. `é` might be one code point (U+00E9) or two (`e` + a combining accent, U+0065 U+0301). A flag emoji is two code points. A skin-toned emoji is a base plus a modifier. So even after you correctly count runes, you may still not have counted "characters" the way a user would. The standard library gives you bytes and runes for free; grapheme-cluster segmentation requires an external package (e.g. `golang.org/x/text/...`). For most backend work, runes are the right unit — just know the ceiling.

---

## 4. Indexing gives a byte; ranging decodes runes

This is the single most important operational fact in the whole topic. **Indexing a string returns a byte. Ranging over a string returns runes.** They are different operations with different types.

```go
s := "héllo"

b := s[1]              // b is a byte (uint8) = 195, the FIRST byte of é — garbage on its own
fmt.Printf("%T\n", b)  // uint8

for i, r := range s {
	fmt.Printf("index=%d rune=%c (%d)\n", i, r, r)
}
// index=0 rune=h
// index=1 rune=é   <- the range loop decoded both bytes of é
// index=3 rune=l   <- note the index JUMPED from 1 to 3
// index=4 rune=l
// index=5 rune=o
```

Study the indices in that loop. The `i` is a **byte offset into the string**, not a rune counter — it jumps from 1 to 3 because `é` occupied bytes 1 and 2. This is exactly right and exactly the thing people misread: `for i, r := range s` decodes one UTF-8 sequence per iteration, hands you the decoded rune in `r`, and reports where that rune *started* in `i`.

**The gotcha:** `s[i]` is a byte, so `string(s[i])` does not "get the character at position i" — it converts a single byte to a string, and for any multibyte character that byte is only a fragment. `string("héllo"[1])` yields `"Ã"` (the replacement of one stray byte), not `"é"`. If you find yourself writing `string(s[i])` to pull out a character, that's the tell you should be ranging, or converting to `[]rune` first.

---

## 5. Converting to []byte and []rune — and what it costs

Go gives you two conversions, and their cost profiles differ sharply.

```go
s := "héllo"

bs := []byte(s)   // copies the bytes; len(bs) == len(s) == 6
rs := []rune(s)   // DECODES the UTF-8 and allocates an int32 per code point; len(rs) == 5
back := string(rs) // re-encodes to UTF-8
```

`[]byte(s)` is a straight copy of the storage — same length as the string, one allocation. It's what you reach for when handing data to an API that mutates bytes or that speaks in `[]byte` (most of `io`, `bytes`, `encoding/*`). Note that Go optimizes several common patterns to avoid the copy — `for range []byte(s)` decodes without allocating, and `string(b)` used directly as a map-lookup key (`m[string(b)]`) skips the allocation — but semantically assume a copy.

`[]rune(s)` is heavier: it walks the whole string, decodes every UTF-8 sequence, and allocates a fresh `int32` slice — four bytes per code point regardless of the original encoding. You do this when you genuinely need **random access by character position** or need to reverse, count, or index text in a way that must respect character boundaries.

```go
// Correctly reversing a string of runes (ASCII-only naive byte reversal would corrupt UTF-8)
func reverse(s string) string {
	rs := []rune(s)
	for i, j := 0, len(rs)-1; i < j; i, j = i+1, j-1 {
		rs[i], rs[j] = rs[j], rs[i]
	}
	return string(rs)
}
```

**The gotcha:** don't reach for `[]rune` reflexively. If all you need is to *count* runes, `utf8.RuneCountInString(s)` does it without allocating the whole slice. If all you need is to *iterate*, `for range` decodes without allocating anything. The `[]rune` conversion earns its allocation only when you need indexed, mutable, character-level access — reversing, or grabbing "the 5th character." For streaming or large inputs, prefer the allocation-free paths.

---

## 6. Counting: len(s) is bytes, RuneCountInString is characters-ish

Because `len` counts bytes, any "how long is this string to a human" question needs `utf8`:

```go
import "unicode/utf8"

s := "café"
fmt.Println(len(s))                    // 5 (é is 2 bytes)
fmt.Println(utf8.RuneCountInString(s)) // 4 (code points)
```

Use `len(s)` when you care about storage, buffer sizes, or byte offsets. Use `utf8.RuneCountInString(s)` when you care about "how many code points" — validating a max-length field the way a user perceives it, for instance. And remember from section 3 that even the rune count isn't the grapheme count; a length limit expressed in "characters" against emoji or combining marks needs grapheme segmentation to match user expectations exactly.

`utf8` also gives you the low-level decode primitives when you want to walk bytes manually: `utf8.DecodeRuneInString` returns the first rune and its byte width, `utf8.ValidString` checks whether a byte sequence is well-formed UTF-8 (worth doing at trust boundaries before you assume the encoding), and `utf8.RuneLen(r)` tells you how many bytes a rune will occupy when encoded.

---

## 7. The package toolkit: strings, bytes, unicode, utf8

Four packages cover the vast majority of text work, and knowing which is which saves a lot of searching.

| Package | Operates on | Use it for |
|---|---|---|
| `strings` | `string` | Split, Join, Contains, Replace, ToUpper, TrimSpace, Fields, and `strings.Builder` |
| `bytes` | `[]byte` | The exact same API as `strings`, but for byte slices — avoids a `string` copy in hot paths |
| `unicode` | `rune` | Per-rune classification: `IsLetter`, `IsDigit`, `IsSpace`, `ToUpper`, `ToLower` |
| `unicode/utf8` | bytes ↔ runes | Encode/decode, count, and validate UTF-8 |

The `strings`/`bytes` symmetry is deliberate: if you already have a `[]byte` (say, from an `io.Reader`), reach for `bytes.Contains` rather than converting to a string first — the conversion is a copy you don't need. And `unicode` is the package that actually knows about the Unicode tables, so per-character logic ("is this a letter, in any language?") belongs there, not in hand-rolled ASCII range checks like `c >= 'a' && c <= 'z'`.

**The gotcha:** `strings.ToUpper` and `unicode.ToUpper` are Unicode-aware and handle accented Latin, Greek, and Cyrillic correctly — but they use *default* case mapping, which is locale-independent. The famous trap is Turkish: the uppercase of `i` is a dotted `İ` in Turkish locale, but `strings.ToUpper` gives the default `I`. If your product is locale-sensitive, `golang.org/x/text/cases` with a language tag is the correct tool, not the standard library. For locale-neutral work (identifiers, protocol tokens), the standard `ToUpper`/`ToLower` are exactly right.

---

## 8. strings.Builder: concatenation without the quadratic blowup

Because strings are immutable, `s += piece` in a loop allocates a brand-new string every iteration and copies everything so far — classic O(n²) behavior that looks innocent in review and melts under load.

```go
// Bad: allocates and copies on every iteration
var s string
for _, p := range parts {
	s += p
}

// Good: one growing buffer, amortized O(n)
var b strings.Builder
for _, p := range parts {
	b.WriteString(p)
}
s := b.String()
```

`strings.Builder` writes into an internal `[]byte` that grows geometrically, then hands you the finished string with `b.String()` — and crucially, `String()` does **not** copy the buffer (it uses an unsafe conversion internally), so the final result is free. If you know the approximate final size, `b.Grow(n)` pre-sizes the buffer and eliminates the intermediate growth allocations entirely. (This forward-references the broader allocation story — the same "don't reallocate in a loop" instinct applies to slices and maps, which a later post covers in depth.)

**The gotcha:** never copy a `strings.Builder` after you've written to it — the type embeds a check that panics if a copied Builder is used, because copying would share the same backing array in a way that breaks the no-copy `String()` guarantee. Pass a `*strings.Builder` if you need to hand it to a function, never a `strings.Builder` by value.

---

## 9. Where these bugs actually bite

Three real patterns account for most string bugs in production Go:

- **Slicing multibyte strings by byte offset.** `s[:maxLen]` to truncate a user field looks fine in tests full of ASCII and corrupts the last character the moment a two-byte accent straddles the boundary — you get an invalid UTF-8 sequence and a `�` in the UI. Truncate on rune boundaries: convert to `[]rune`, slice, convert back, or walk with `utf8.DecodeRuneInString` until you hit the byte budget.
- **`string(intValue)` when you meant a number.** `string(65)` is `"A"`, not `"65"` — it's interpreted as a code point. This is such a common mistake that `go vet` flags it; use `strconv.Itoa` or `fmt.Sprint` to stringify a number.
- **ASCII-only case and classification.** Hand-rolled `c >= 'a' && c <= 'z'` checks silently exclude every non-English letter. Use `unicode.IsLetter`, `unicode.ToUpper`, and friends so your validation and normalization work for the whole user base, not just the ASCII subset.

The common thread: bugs hide in test suites written entirely in English ASCII and surface the first time a real name, address, or emoji arrives. Test with genuinely multibyte input — accented Latin, CJK, and at least one 4-byte emoji — and these defects show up before your users find them.

---

## Key takeaways

- **A string is an immutable, read-only slice of bytes.** `len(s)` is bytes; slicing shares the backing array (and can pin a large original — `strings.Clone` to break the link).
- **Source is UTF-8**, so string literals store variable-width encoded bytes: 1–4 per code point.
- **Byte ≠ rune ≠ character.** A byte is storage, a rune is a code point (`int32`), and a user-perceived character can span several runes.
- **`s[i]` is a byte; `for i, r := range s` decodes runes** and reports byte offsets. `string(s[i])` on multibyte text gives you a fragment, not a character.
- **`[]byte(s)` copies bytes cheaply; `[]rune(s)` decodes and allocates per code point** — use the allocation-free paths (`for range`, `utf8.RuneCountInString`) unless you truly need indexed character access.
- **Know the toolkit:** `strings`/`bytes` (same API, different type), `unicode` (per-rune classification), `unicode/utf8` (encode/decode/count/validate).
- **`strings.Builder` turns O(n²) concatenation into amortized O(n)** — never copy it after writing.

Get the byte-vs-rune model right and most "unicode bugs" simply stop happening, because you're no longer treating storage as if it were meaning.

---

## Further reading

- [Strings, bytes, runes and characters in Go](https://go.dev/blog/strings) — the canonical Go blog piece on exactly this model, and the source to reach for when a teammate needs convincing.
