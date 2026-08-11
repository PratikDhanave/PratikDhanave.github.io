# Tokens and Tokenization

*The unit a language model actually reads is neither a word nor a character — it is a token, and once you see the world the way the model does, half of its strange behavior stops being strange.*

---

Ask a large language model to count the letters in "strawberry" and it may well tell you there are two. Ask it to reverse a string and it fumbles. Bill it for a paragraph of English and it costs a fraction of the same paragraph in Hindi or Japanese. None of these are bugs — they are all the same fact wearing different clothes. A model does not read text the way you do. Before a single layer of the network runs, your text is chopped into **tokens**, and everything downstream — pricing, context limits, spelling, arithmetic — is a consequence of where those cuts fall.

This post is about that first, invisible step. We will build the intuition for what a token is, how the byte-pair encoding that produces them actually works, and why it explains behavior you have already seen. Then we will count tokens in Go — both the exact way, against a real OpenAI encoding, and a rough way you can carry anywhere.

---

## A token is a subword unit

The first instinct is that a model reads words. It does not. The second instinct is that it reads characters. It does not do that either. A token sits in between: it is a chunk of text, usually a few characters long, drawn from a fixed **vocabulary** the model was trained with. A vocabulary might hold 50,000 or 100,000 or 200,000 distinct tokens.

Common words often become a single token. Rare words get split into several. A word like `tokenization` might arrive as `token` + `ization`; a name the model has never seen, like `Dhanave`, might fracture into three or four pieces. Punctuation, spaces, and even the *leading space* of a word are part of the token — ` cat` (with a space) and `cat` (without) are usually two different tokens.

Here is the mental model to hold onto: **the model never sees your letters.** It sees a sequence of integer IDs, one per token. When it generates, it emits one token ID at a time and the IDs are mapped back to text. The letters are on your side of the fence, not the model's.

```text
Text:    "Tokenization is subword."
Tokens:  ["Token", "ization", " is", " sub", "word", "."]
IDs:     [3404, 2065, 374, 1207, 1178, 13]
```

(The exact split and IDs depend on which encoding you use — the ones above are illustrative, not a promise about any specific model.)

**The gotcha:** "one token ≈ one word" is a rule of thumb, not a law. For ordinary English prose it lands near ~0.75 words per token, but the moment you feed a model code, JSON, non-Latin script, or a wall of rare proper nouns, the ratio swings hard. Treat any word-based estimate as an approximation and count real tokens when money or limits are on the line.

---

## How byte-pair encoding builds a vocabulary

The dominant way to produce that vocabulary is **byte-pair encoding** (BPE). The name sounds intimidating; the idea is almost embarrassingly simple, and you can hold the whole algorithm in your head.

Start with the smallest possible units — individual bytes (or characters). At this point your "vocabulary" is just the raw alphabet, and every word is spelled out one symbol at a time. Then you repeat one move:

1. Scan a large training corpus and count every **adjacent pair** of symbols.
2. Find the pair that occurs most often.
3. Merge that pair into a single new symbol and add it to the vocabulary.
4. Go back to step 1.

Each merge makes the most common pairing in your data into its own token. Do this thousands of times and frequent sequences — `th`, then `the`, then ` the` — get promoted into single tokens, while rare sequences stay fragmented. The vocabulary you ship is just the starting alphabet plus the ordered list of merges you learned.

Walk it through by hand. Suppose your corpus is the words `low`, `lower`, `lowest`, repeated many times. Starting from characters, the pair `l o` is everywhere, so it merges into `lo`. Now `lo w` is everywhere, so it merges into `low`. Suddenly the common stem `low` is one token, and the endings `er` and `est` — themselves frequent across the whole language — become their own tokens too. The model ends up with reusable pieces: a stem plus a suffix, assembled on demand.

```text
Round 0:  l o w   l o w e r   l o w e s t
merge lo: lo w    lo w e r    lo w e s t
merge low:low     low e r     low e s t
merge er: low     low er      low e s t
...
Vocabulary grows: [l,o,w,e,r,s,t, lo, low, er, ...]
```

The elegance is that BPE learns *where words tend to break* purely from frequency, with no dictionary and no grammar. Because it can always fall back to individual bytes, it can encode literally any input — a brand-new word, an emoji, a snippet of a language it barely saw — without ever hitting an "unknown token." Worst case, it spells the thing out one byte at a time, which is exactly why obscure inputs cost more tokens.

**The gotcha:** the merge list is *ordered and fixed at training time*. Tokenization is deterministic but greedy — it applies learned merges in order, it does not search for the shortest possible split. Two visually similar strings can tokenize very differently, and you cannot reason about token counts from the letters alone. You have to run the actual encoder.

---

## Why tokenization explains real behavior

Once you accept that the model reads token IDs and not characters, a pile of otherwise-mysterious behavior becomes obvious.

**Pricing is per token.** Providers bill input and output in tokens, not words or characters. This is why a request in a token-dense language costs more for the "same" content, and why trimming a verbose system prompt saves real money.

**Context limits are counted in tokens.** When a model advertises a 128,000-token context window, that budget is spent in tokens. A document that looks short by character count can be surprisingly expensive if it is full of rare words, code, or non-Latin script, and it can overflow a window sooner than you expect.

**Spelling, reversing, and counting characters are hard.** Ask the model how many `r`s are in "strawberry" and it struggles because it never saw the letters — it saw something like ` straw` + `berry`, two opaque IDs. Counting characters inside a token means reasoning about a symbol whose internal spelling was thrown away at the door. Reversing a string is the same problem: the model would have to unpack each token into characters it does not have direct access to.

**Arithmetic is shaky for the same reason.** Numbers tokenize in awkward, inconsistent chunks — `1234` might be one token while `12345` splits as `123` + `45`. The model is not manipulating digits in place values; it is pattern-matching over token sequences, which is why long multiplication drifts. (This is exactly the kind of task you hand to a tool or a code interpreter instead of trusting the raw model.)

**Whitespace, casing, and language shift the count.** ` The`, `The`, and `THE` can be three different tokens. Extra spaces and newlines are tokens too. And because BPE merges were learned mostly on English-heavy corpora, English packs more characters per token than most other languages — so the identical meaning, translated, can cost noticeably more tokens.

| Behavior you observe | Root cause in tokenization |
|---|---|
| "Same" text costs more in another language | Fewer learned merges → more tokens per character |
| Model miscounts letters in a word | It sees token IDs, not the characters inside them |
| Reversing a string goes wrong | Characters are hidden behind opaque tokens |
| Long arithmetic drifts | Digits split into inconsistent token chunks |
| A short-looking doc blows the context window | Rare words / code fragment into many tokens |

---

## Counting tokens exactly in Go

Estimates are fine for a gut check, but when you are enforcing a context budget or reconciling a bill you want the real number. For OpenAI's encodings there is a well-maintained Go port of the reference tokenizer: [`github.com/pkoukk/tiktoken-go`](https://github.com/pkoukk/tiktoken-go). It ships the actual merge tables, so its counts match the encodings the models use.

The pattern is: load an encoding by name, encode your text into token IDs, and take the length.

```go
package main

import (
	"fmt"
	"log"

	"github.com/pkoukk/tiktoken-go"
)

func main() {
	// cl100k_base is the encoding used by several OpenAI chat models.
	// Load it once and reuse the encoder — it is safe to keep around.
	enc, err := tiktoken.GetEncoding("cl100k_base")
	if err != nil {
		log.Fatalf("load encoding: %v", err)
	}

	text := "Tokenization is subword, not words or characters."

	// Encode returns the token IDs. The extra arguments are the sets of
	// allowed/disallowed special tokens; nil means "use the defaults".
	// (If a version of the library uses a different signature, check its API.)
	ids := enc.Encode(text, nil, nil)

	fmt.Printf("text:   %q\n", text)
	fmt.Printf("tokens: %d\n", len(ids))
	fmt.Printf("ids:    %v\n", ids)
}
```

`GetEncoding` takes the encoding name directly (`"cl100k_base"` here). Some versions also expose a model-oriented helper that maps a model name to its encoding for you — if you would rather name the model than the encoding, check the library's API for that variant. Either way, the shape is the same: get an encoder, call `Encode`, measure the slice.

**The gotcha:** an encoding is not a model. `cl100k_base` is one specific tokenizer; a different model family may use a different encoding (and therefore a different count) for the exact same string. Pick the encoding that matches the model you are actually calling, and do not assume a token count transfers across providers or model generations. When in doubt, count against the encoding the model documents.

---

## A rough approximation with no dependencies

Sometimes you cannot pull in the encoding tables — you are in a hot path, a size-constrained binary, or you just want a fast pre-flight guess before making the real call. A crude heuristic is genuinely useful here, as long as you *treat it as a lower-confidence estimate* and pad your budget.

The simplest rule that holds up for English prose: roughly **four characters per token**. Slightly better is to count words and punctuation and nudge upward, since punctuation and spaces carry their own tokens.

```go
package main

import (
	"fmt"
	"strings"
	"unicode"
)

// estimateTokensByChars: the classic "~4 characters per token" rule.
// Fast, dependency-free, and only a ballpark — bias it high for safety.
func estimateTokensByChars(text string) int {
	n := len([]rune(text))
	est := n / 4
	if est < 1 && n > 0 {
		est = 1
	}
	return est
}

// estimateTokensByWords: count word-ish runs plus standalone punctuation.
// Tends to track English a little better than raw character division.
func estimateTokensByWords(text string) int {
	words := strings.Fields(text) // splits on any whitespace
	punct := 0
	for _, r := range text {
		if unicode.IsPunct(r) {
			punct++
		}
	}
	// Each word is ~1.3 tokens on average for English; add punctuation.
	return int(float64(len(words))*1.3) + punct
}

func main() {
	text := "Tokenization is subword, not words or characters."
	fmt.Printf("char-based estimate: %d\n", estimateTokensByChars(text))
	fmt.Printf("word-based estimate: %d\n", estimateTokensByWords(text))
}
```

Neither number is exact, and both drift badly on code or non-English text — but for "will this prompt roughly fit?" they earn their keep. The discipline is to know which one you are holding: an estimate for a quick check, the real encoder for anything that touches money or a hard limit.

**The gotcha:** the ~4-chars rule is calibrated on English. On code, dense punctuation, or non-Latin scripts it can under-count by a wide margin — precisely the inputs that fragment into many tokens. If your estimate feeds a safety margin, round *up* and leave headroom; never let a heuristic be the thing standing between you and a context-window overflow.

---

## From tokens to a bill

Because pricing is per token, a cost estimate is just arithmetic once you have counts. Providers quote a price per million tokens, usually with different rates for input (prompt) and output (completion). Keep the rates in one place and the calculation stays honest.

```go
package main

import "fmt"

// Prices are per 1,000,000 tokens, in your currency of choice.
// These are placeholders — read the current numbers from the provider's
// pricing page; do not trust hard-coded rates to stay correct.
type Pricing struct {
	InputPerMillion  float64
	OutputPerMillion float64
}

func estimateCost(inputTokens, outputTokens int, p Pricing) float64 {
	in := float64(inputTokens) / 1_000_000 * p.InputPerMillion
	out := float64(outputTokens) / 1_000_000 * p.OutputPerMillion
	return in + out
}

func main() {
	// Suppose you counted these with tiktoken-go.
	inputTokens, outputTokens := 1_200, 800

	// Fill in with the real, current published rates.
	price := Pricing{InputPerMillion: 3.00, OutputPerMillion: 15.00}

	cost := estimateCost(inputTokens, outputTokens, price)
	fmt.Printf("input:  %d tokens\n", inputTokens)
	fmt.Printf("output: %d tokens\n", outputTokens)
	fmt.Printf("est. cost: $%.5f\n", cost)
}
```

The numbers in that example are stand-ins so the code runs — the point is the *shape*. Output tokens are usually priced higher than input tokens, so a chatty completion can dominate the bill even when the prompt is long. Count both separately.

**The gotcha:** never hard-code prices as if they are permanent. Rates change, and they differ per model. Put them in config, refresh them from the provider's published pricing, and treat the number your calculator prints as an estimate — the authoritative charge is whatever the provider's usage metering reports back after the call.

---

## Key takeaways

- **A token is a subword unit**, not a word and not a character. The model reads integer IDs from a fixed vocabulary; your letters never cross the fence.
- **BPE builds the vocabulary by merging the most frequent adjacent pairs**, starting from bytes. Frequent sequences become single tokens; rare ones stay fragmented, which is why obscure input costs more.
- **Tokenization explains the weird behavior.** Per-token pricing, token-counted context limits, bad spelling/reversing/char-counting, shaky arithmetic, and language-dependent cost are all downstream of where the cuts fall.
- **Count exactly with `tiktoken-go`** against the encoding your model uses (`GetEncoding("cl100k_base")` → `Encode` → `len`). An encoding is not a model — match them.
- **Estimate cheaply with ~4 chars/token or a word+punctuation heuristic**, but bias high and never let a guess guard a hard limit or a bill.

Tokenization is the layer everyone skips and then trips over. Spend an afternoon watching real text turn into real token IDs and the model's quirks stop looking like magic — they look like the direct, predictable consequence of reading the world in subword chunks.

---

## Further reading

- [OpenAI — Understanding tokens / the tokenizer tool](https://platform.openai.com/tokenizer) — paste text and watch it split into tokens interactively.
- [openai/tiktoken](https://github.com/openai/tiktoken) — the reference BPE tokenizer that the encodings above come from.
- [pkoukk/tiktoken-go](https://github.com/pkoukk/tiktoken-go) — the Go port used in this post for exact counts against OpenAI encodings.
