# Strings, Bytes, and Unicode

*Why Python draws a hard line between text and raw bytes, how the encode/decode boundary works, and the string-handling habits that keep that line from cutting you.*

---

Text feels like the simplest thing a program handles — until you paste a name with an accent, read a file someone saved on Windows, or emit JSON that a downstream service rejects as malformed. At that moment you discover that "a string" is really two different things wearing the same word: a sequence of human-readable characters, and a sequence of raw bytes on a wire or a disk. Python 3 refuses to let you confuse the two, and that refusal — annoying at first — is the single feature that turns text bugs from silent corruption into loud, fixable errors.

This post is about the model underneath `str` and `bytes`: what each one actually holds, where the boundary between them sits, and the everyday habits (`encode`, `decode`, f-strings, `join`, raw strings) that follow from getting the model right.

---

## Two types, two jobs

Python has two distinct sequence types for text-ish data, and they are not interchangeable.

`str` is an **immutable sequence of Unicode code points**. A code point is an abstract number the Unicode standard assigns to a character — `U+0041` for `A`, `U+00E9` for `é`, `U+1F600` for a grinning face. A `str` knows nothing about disks or networks; it is pure text, held in memory as code points.

`bytes` is an **immutable sequence of integers, each 0–255**. A `bytes` object is what actually travels over a socket or lands in a file. It carries no notion of "character" — only octets.

```python
text = "café"          # str: 4 code points
raw = text.encode("utf-8")   # bytes: 5 octets, because é needs 2

print(len(text))   # 4
print(len(raw))    # 5
print(raw)         # b'caf\xc3\xa9'
print(type(text), type(raw))   # <class 'str'> <class 'bytes'>
```

Both are immutable — every method that "changes" a string returns a new one. And both are sequences, so indexing, slicing, and iteration work on each. But indexing a `bytes` gives you back an `int`, not a one-character `bytes`:

```python
raw[0]        # 99  (the integer for 'c')
raw[0:1]      # b'c'  (slicing keeps the type)
"café"[0]     # 'c'  (str indexing gives a str)
```

**The gotcha:** iterating `bytes` yields integers, iterating `str` yields one-character strings. Code that assumes `for ch in data:` gives you characters will silently do arithmetic-shaped things if `data` is bytes. Know which type you hold before you loop.

---

## The encode/decode boundary

Converting between the two directions has fixed names, and they only go one way each:

- **`str.encode(encoding)` → `bytes`.** Text out to octets. "Encode to bytes for the outside world."
- **`bytes.decode(encoding)` → `str`.** Octets in, back to text. "Decode incoming bytes to text."

The mnemonic that sticks: a *coder* turns readable text into a coded byte form; a *decoder* recovers the readable text. `str` is the readable side, `bytes` is the coded side.

```python
message = "π ≈ 3.14159"
wire = message.encode("utf-8")     # str -> bytes, ready to send
print(wire)                        # b'\xcf\x80 \xe2\x89\x88 3.14159'

restored = wire.decode("utf-8")    # bytes -> str, ready to display
print(restored)                    # π ≈ 3.14159
print(restored == message)         # True
```

An **encoding** is the rule that maps code points to byte patterns and back. UTF-8, UTF-16, Latin-1, and ASCII are all different rules; the same text produces different bytes under each, and bytes encoded with one rule are gibberish (or an error) if decoded with another. That is the whole source of "mojibake" — the `Ã©` you sometimes see where an `é` belonged.

This leads to the rule worth memorizing:

> **Decode bytes as early as possible; encode text as late as possible.**

The moment bytes enter your program — off a socket, out of a file, from a subprocess — decode them to `str` and work in text for the entire middle of the program. Encode back to `bytes` only at the last possible instant, right before the data leaves. This keeps your core logic in one clean type and confines every encoding decision to two thin edges. It is sometimes called the "Unicode sandwich": bytes on the outside, text in the filling.

---

## UTF-8 is the sane default

Of all the encodings, **UTF-8** is the one to reach for unless something forces your hand. It is backward-compatible with ASCII (the first 128 code points encode to a single identical byte), it can represent every Unicode code point, and it has become the de facto standard for the web, JSON, and most modern file formats. When you have a choice, choose UTF-8.

The trap is that Python does not *always* default to UTF-8 for you. `str.encode()` and `bytes.decode()` do default to UTF-8 — but `open()` historically defaulted to the platform's locale encoding, which might be UTF-8 on Linux and macOS but `cp1252` on a Windows box. Code that works on your laptop then mangles text in production.

```python
# Fragile: encoding depends on the machine's locale.
with open("names.txt") as f:
    data = f.read()

# Robust: the encoding is explicit and identical everywhere.
with open("names.txt", encoding="utf-8") as f:
    data = f.read()
```

**The gotcha:** always pass `encoding=` to `open()` — do not rely on the platform default. The same discipline applies to `subprocess`, `requests`, database drivers, and any API that hands you text: find out what encoding it assumes and make it explicit. An implicit encoding is a bug waiting for a different computer.

---

## UnicodeDecodeError, and how to avoid it

When you decode bytes with the wrong rule — or the bytes are genuinely malformed — Python raises `UnicodeDecodeError` rather than quietly producing wrong text. This is a feature: a loud failure at the boundary beats corrupted data three layers deep.

```python
raw = "café".encode("utf-8")   # b'caf\xc3\xa9'

raw.decode("ascii")
# UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position 3:
#   ordinal not in range(128)
```

The byte `0xc3` is part of a valid UTF-8 sequence, but ASCII only knows 0–127, so the decode aborts. The fix is almost always "decode with the encoding the bytes were actually written in." When you genuinely cannot guarantee clean input, the `errors=` parameter lets you choose a fallback instead of crashing:

```python
messy = b"caf\xe9"   # 'é' as Latin-1, not valid UTF-8

messy.decode("utf-8", errors="strict")    # default: raises UnicodeDecodeError
messy.decode("utf-8", errors="replace")   # 'caf�'  (U+FFFD replacement char)
messy.decode("utf-8", errors="ignore")    # 'caf'  (bad bytes dropped)
messy.decode("latin-1")                   # 'café'  (the correct rule here)
```

**The gotcha:** `errors="ignore"` and `errors="replace"` silence the error by *destroying data* — they should be a deliberate, last-resort choice for display-only text, never a reflex to make a traceback go away. If you find yourself reaching for them constantly, you have the wrong encoding, not bad luck.

---

## Formatting text: f-strings first

Once your data is `str`, you assemble output. Modern Python has three formatting styles, and f-strings (PEP 498, Python 3.6+) are the default choice: they are readable, fast, and put the expression right where it appears.

```python
name, ratio = "Ada", 0.8137

f"{name} scored {ratio:.1%}"     # 'Ada scored 81.4%'
```

Everything after the colon is the **format spec mini-language**, a compact grammar for alignment, width, precision, and type. A few you will use constantly:

```python
value = 1234567.891

f"{value:,.2f}"      # '1,234,567.89'   thousands separator, 2 decimals
f"{value:>15.2f}"    # '     1234567.89' right-align in width 15
f"{value:+.2e}"      # '+1.23e+06'      forced sign, scientific
f"{42:08b}"          # '00101010'       binary, zero-padded to width 8
f"{0xFF:#x}"         # '0xff'           hex with 0x prefix
```

There is also the `=` debug form, which prints the expression text alongside its value — a genuinely great logging shortcut:

```python
x, y = 3, 4
f"{x=}, {y=}, {x*y=}"    # 'x=3, y=4, x*y=12'
```

So when do the older styles still appear? `str.format()` shows up when the template is separated from the data — a template loaded from a config file or reused across call sites, where there is no f-string to interpolate at definition time. And `%`-formatting survives in two places: legacy code, and the standard `logging` module, where `logging.info("user %s failed %d times", user, n)` defers the string-building until the framework decides the message will actually be emitted.

**The gotcha:** an f-string is evaluated immediately, so `logging.info(f"...")` builds the whole string even when the log level would discard it. For hot logging paths, prefer the `%`-style `logging.info("... %s", value)` and let the logger decide whether to format at all.

---

## String methods and the join rule

`str` carries a rich toolbox, all returning new strings. The workhorses:

```python
"  hello world  ".strip()          # 'hello world'
"a,b,c".split(",")                 # ['a', 'b', 'c']
"-".join(["2026", "06", "29"])     # '2026-06-29'
"Report".replace("o", "0")         # 'Rep0rt'
"HELLO".lower()                    # 'hello'
"file.TXT".endswith(".txt")        # False  (case-sensitive)
"  data".startswith(" ")           # True
```

`split()` and `join()` are inverses and belong together: split tears a string into a list on a delimiter; join stitches a list back with a separator. Note that `join` is a method *on the separator*, which reads backwards the first few times: `", ".join(parts)`, not `parts.join(", ")`.

That backwards-looking `join` is also the right way to build a string from many pieces. Because `str` is immutable, `+=` in a loop creates a brand-new string on every iteration, copying all the accumulated characters each time — quadratic work as the string grows. Collect into a list and join once:

```python
# Avoid: each += allocates and copies the whole string so far.
out = ""
for row in rows:
    out += format_row(row)

# Prefer: one allocation at the end.
pieces = [format_row(row) for row in rows]
out = "".join(pieces)
```

**The gotcha:** `"".join(list_of_strings)` beats `+=` in a loop not as a micro-optimization but as a complexity fix — it turns O(n²) into O(n) for large inputs. Every element of the list must already be a `str`; `join` will raise `TypeError` if a number or `bytes` sneaks in, so wrap non-strings in `str()` first.

---

## str and bytes do not mix

Python 3 will not let you combine the two types implicitly. This is the change that caused so much Python 2-to-3 migration pain — and, in hindsight, the best thing about it.

```python
"total: " + b"42"
# TypeError: can only concatenate str (not "bytes") to str

"café" == b"caf\xc3\xa9"
# False  (never equal across types; not even compared byte-for-byte)
```

In Python 2, `str` *was* bytes, and the language happily mixed text and octets until an unexpected non-ASCII character detonated deep in production. Python 3 makes the two types disjoint: you cannot concatenate them, compare them as equal, or use one where the other is expected. The `TypeError` fires at the exact line where you crossed the streams, not three modules downstream. What looks like strictness is really early failure — encoding bugs surface where you can still see their cause.

**The gotcha:** if you need them together, convert explicitly — `"total: " + b"42".decode("ascii")` — and let the conversion mark exactly where text becomes bytes or the reverse.

---

## len() counts code points, not what you see

`len()` on a `str` returns the number of **code points**, which is not always the number of characters a human perceives — a "grapheme cluster." Most of the time these agree; with emoji, flags, and combining marks they diverge.

```python
len("café")            # 4   (c, a, f, é as one code point)
len("café")      # 5   ('e' + a combining acute accent = 5 code points)
len("👍")              # 1   (this emoji is one code point)
len("👨‍👩‍👧")          # 5   (family emoji: 3 people + 2 zero-width joiners)
len("🇮🇳")             # 2   (flag = two regional-indicator code points)
```

Two strings can even *look* identical on screen while having different lengths and comparing unequal, because the same visible character can be a single precomposed code point (`é`, `U+00E9`) or a base letter plus a combining mark (`e` + `U+0301`). When you need them to compare as equal, normalize with `unicodedata.normalize("NFC", s)` first.

**The gotcha:** `len(s)` is not "how many characters a user sees," and `s[0]` is not reliably "the first visible character." For truncating display text, validating input by "character count," or reversing a string, code-point indexing can split a grapheme and produce broken output. For real grapheme-aware work, reach for a dedicated library; do not assume one code point equals one character.

---

## Raw strings for regex and paths

A normal string literal processes backslash escapes: `\n` becomes a newline, `\t` a tab. That is exactly wrong when the backslashes are meant literally — as in regular expressions and Windows paths. A **raw string**, prefixed with `r`, turns escape processing off.

```python
"a\tb"       # 'a<TAB>b'  — \t interpreted as a tab
r"a\tb"      # 'a\\tb'    — a backslash, then t, literally

import re
re.findall(r"\d+", "order 42, qty 7")   # ['42', '7']
```

Regex has its own backslash grammar (`\d`, `\w`, `\b`), and a raw string hands those backslashes to the regex engine untouched instead of Python trying to interpret them first. Without the `r`, you would write `"\\d+"` and fight two layers of escaping. The same logic makes raw strings convenient for Windows paths like `r"C:\Users\data"` — though for filesystem work `pathlib.Path` is the better tool.

**The gotcha:** a raw string cannot *end* in an odd number of backslashes — `r"C:\path\"` is a syntax error, because the trailing backslash escapes the closing quote even in raw mode. And `r` changes only how the literal is *parsed*; the resulting `str` is an ordinary string with no memory of having been raw.

---

## Key takeaways

- **`str` is code points; `bytes` is octets.** Text lives in `str` in memory; `bytes` is what crosses disks and wires. They are different types on purpose.
- **`encode()` goes str→bytes, `decode()` goes bytes→str.** Decode at the moment data enters, encode at the moment it leaves — the Unicode sandwich.
- **Default to UTF-8 and make it explicit.** Especially pass `encoding="utf-8"` to `open()`; never trust the platform locale.
- **`UnicodeDecodeError` is a loud, useful failure.** Fix it with the right encoding, not by silencing it with `errors="ignore"`.
- **Prefer f-strings and their format spec.** Fall back to `.format()` for reusable templates and `%`-style for the `logging` module's deferred formatting.
- **Build strings with `"".join(list)`, not `+=` in a loop** — it is O(n) instead of O(n²).
- **`len()` counts code points, not perceived characters.** Emoji and combining marks break the "one character" assumption; normalize before comparing.
- **Use raw strings (`r"..."`) for regex and literal backslashes** — just never end one on a lone backslash.

Python's hard line between text and bytes is the feature that makes text handling boring in the best way: encoding decisions live at two thin edges, and everything in between is clean Unicode text.

## Further reading

- [Unicode HOWTO](https://docs.python.org/3/howto/unicode.html) — the official, thorough guide to how Python handles text, encodings, and the `str`/`bytes` boundary.
