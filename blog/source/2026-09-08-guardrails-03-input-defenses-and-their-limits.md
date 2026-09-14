# Input Defenses and Their Limits

*The first instinct when facing prompt injection is to inspect the input and block the bad stuff. It's a reasonable layer — but a treacherous one, because it creates a feeling of safety far larger than the protection it provides. This post covers the input-side defenses that are genuinely worth having, and draws a hard line around what they can and cannot do.*

Having established that injection can't be prevented at the model level and must be contained by architecture, we start the defense stack at the layer people reach for first: the input. Input defenses are the shallowest layer — necessary, cheap, and real, but never sufficient. The goal here is to use them for what they're good at while refusing to trust them for what they can't do.

## What input defenses can do

Input-side controls inspect or transform what reaches the model. The ones worth implementing:

**Length and rate limits.** Cap input size and request frequency. This won't stop a clever one-line injection, but it blunts many-shot jailbreaks (which need long contexts), token-flooding, and automated attack campaigns. It's cheap and has other benefits (cost control, DoS resistance), so it's an easy yes.

**Structural validation.** If your application expects input in a specific shape — a support ticket, a product SKU, a date range — validate that shape *before* it reaches the model. A field that should contain an order number has no business containing three paragraphs of instructions. The tighter the expected structure, the more this buys you. It does nothing for genuinely free-text applications (a chatbot), but for constrained inputs it's one of the most effective controls you have, precisely because it narrows the channel.

**Known-pattern detection.** Scanning for signatures of common attacks — "ignore previous instructions," "you are now DAN," base64 blobs, suspiciously long runs of instructions inside data — catches the lazy majority of attempts and gives you telemetry (you learn you're being probed). Treat it as a *signal and a speed bump*, not a wall.

**Classifier-based screening.** A dedicated model (or a cheap LLM call) trained to score "does this input look like an injection/jailbreak attempt?" is more robust than regex because it generalizes beyond exact strings. This is the strongest input defense, and post 7 covers it in depth. But — critically — it's still a probabilistic classifier that attackers can evade.

## Why input filtering cannot be the answer

Here is the wall every input defense hits, and internalizing it is the point of this post: **you cannot filter your way to safety against natural language.**

The reasons compound:

- **Infinite paraphrase.** "Disregard your prior instructions" can be written ten thousand ways — in French, in pig latin, as an acrostic, implied through a story, spelled with unicode look-alikes, split across tokens, framed as a hypothetical. A blocklist is a finite defense against an infinite attack space. You will always be one paraphrase behind.
- **The dual-use problem.** The same phrases that appear in attacks appear in legitimate use. "Ignore the previous suggestion and try again" is a normal thing a user says. Aggressive filtering generates false positives that break the product; lax filtering lets attacks through. There's no threshold that's both safe and usable.
- **Indirect injection bypasses input filtering entirely.** This is the decisive point. The most dangerous attacks (post 2) don't come through the user's input at all — they arrive inside a retrieved document, a web page, an email. Your input filter never sees them. You could build a perfect user-input filter and still be fully exploitable through the content your model reads. Filtering the user protects against the *least* dangerous attack class.
- **Attackers adapt.** Any published filter is a public target. Attackers test against it until they find what passes. A static filter degrades the moment it's deployed.

None of this means input filtering is worthless. It means it's a **speed bump, not a gate.** It reduces attack volume, catches unsophisticated attempts, and generates useful signal — real value. It just cannot be the thing your security depends on.

## Normalization: a double-edged tool

One input transformation deserves special mention because it cuts both ways. **Normalizing input** — decoding encodings, stripping invisible unicode, collapsing homoglyphs to ASCII — can strip the obfuscation attackers use to hide instructions (invisible text, base64, look-alike characters). That's genuinely useful, especially against the hidden-text tricks common in indirect injection.

But normalization can also *reveal* an attack that was previously inert, or *mangle* legitimate content (a document that legitimately contains base64, a message in another script). And an over-eager normalizer becomes its own attack surface. Use normalization deliberately — especially stripping zero-width and invisible characters from retrieved content, which is almost always the right move — but don't assume it closes the obfuscation hole; it narrows it.

## Where input defenses fit

The honest role of input defenses in the overall strategy: they are the **cheap outer layer that reduces noise so your expensive inner defenses do less work.** They filter the obvious, rate-limit the floods, validate the structured, and surface telemetry — making the attacker's job harder and your monitoring richer.

What they must *not* do is carry the weight of your security. The moment your threat model reads "we're safe because we filter malicious inputs," you have a critical vulnerability, because indirect injection walks right past that filter and paraphrase defeats it anyway. Input defenses buy you a quieter front door; they do nothing about the windows.

That's why the next posts move inward and downward — to prompt hardening (which helps a little more), and then to the architecture and privilege controls that actually hold, because they don't depend on recognizing the attack at all. The strongest defenses are the ones that keep you safe *even when the malicious input gets through* — which, eventually, it will.

## Key takeaways

- Input defenses — length/rate limits, **structural validation**, known-pattern detection, and classifier screening — are a real, cheap layer worth having, best at catching unsophisticated attacks and generating telemetry.
- **Structural validation is the strongest input control** for *constrained* inputs (validate the expected shape before the model sees it); it does nothing for free-text apps.
- Input filtering **cannot be your security** because natural language is infinitely paraphrasable, attack phrases are dual-use (false-positive vs. miss tradeoff has no safe threshold), and attackers adapt to any published filter.
- **Indirect injection bypasses input filtering entirely** — the most dangerous attacks arrive in retrieved content the filter never sees, so filtering user input protects against only the least dangerous attack class.
- **Normalization** (decoding, stripping invisible/homoglyph characters — especially from retrieved content) helps against obfuscation but cuts both ways; treat input defenses as a **speed bump that quiets the front door, not a gate** — the real defenses (next posts) keep you safe even when malicious input gets through.

## Further reading

- [OWASP — LLM01: Prompt Injection (prevention and mitigation)](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [Simon Willison — Prompt injection: what's the worst that can happen?](https://simonwillison.net/2023/Apr/14/worst-that-can-happen/)
