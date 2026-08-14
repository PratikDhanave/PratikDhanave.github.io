# Security and Performance Review

*The two specialist lenses a reviewer switches on for a diff — thinking like an attacker to catch the injection and the missing authorization check, and thinking like production to catch the N+1 query — while knowing exactly where the human eye stops and a scanner, profiler, or load test has to take over.*

---

Most of a code review is design, correctness, tests, and clarity — the general-purpose pass covered earlier in this series. But two categories reward a *different kind of attention*, and a reviewer who does not deliberately switch into them will scroll right past the two most expensive bugs a diff can carry: a missing authorization check, and a query inside a loop.

Neither is about whether the code works. The injection-vulnerable handler works perfectly — for well-behaved input. The N+1 query works perfectly — on the twelve rows in your test database. Both pass review, both pass tests, and both surface later as an incident: one as a breach, the other as a 2 a.m. page when the table hits a million rows. The security and performance lenses exist to catch the class of bug that *looks fine and isn't*.

This post is about how to switch those lenses on, what to look for in an actual diff, and — just as important — where the human reviewer's usefulness ends and the tools take over. You cannot fully security-review or performance-review a change by eye. What you *can* do is flag the smells the tools miss and know when to demand a SAST run, a profiler trace, or a load test before approval.

This complements the site's dedicated [API Security series](/blog/posts/api-security-01-the-api-security-landscape.html), which goes deep on each vulnerability class. Here the focus is narrower: how to spot these things *in a pull request*, in the minutes you have.

---

## The security lens: assume the input is hostile

The whole security mindset compresses to one instruction: **assume every input is hostile, and follow the data.** When a diff introduces a new input — a query parameter, a request body field, an uploaded file, a header, a URL the user supplies — trace it forward. Where does it land? If it reaches a *sink* — a database query, a shell command, a file path, an HTTP call, a deserializer — without being validated or parameterized on the way, you have found something.

That is the entire technique: identify sources, identify sinks, and check every path between them. Here is the catalog of what to look for.

### Untrusted input reaching a sink (injection)

The classic. User input concatenated into a query string, a shell command, or an HTML template. The fix is almost always "parameterize" — let the driver separate code from data.

```diff
- rows, err := db.Query(
-     "SELECT * FROM invoices WHERE customer = '" + name + "'")
+ rows, err := db.Query(
+     "SELECT * FROM invoices WHERE customer = $1", name)
```

> **Review comment:** "`name` comes straight from the query string and is being concatenated into SQL — a value of `x' OR '1'='1` reads every customer's invoices. Use a parameterized query (`$1`) so the driver treats it as data, not code. Same pattern applies to the `os/exec` call on line 88 — build the argument list, don't shell out with a string."

The tell in a diff is string concatenation or interpolation reaching anything that executes: SQL, `exec`, `eval`, a template rendered as raw HTML, an LDAP filter, a file path joined from user input.

### A missing authorization check on a new endpoint or object

This one deserves top billing because it is the highest-value catch a human can make. When a diff adds an endpoint that loads or mutates an object by ID, ask the question a scanner cannot: *is this user allowed to touch this particular object?* Authentication ("who are you") is not authorization ("may you do this to that"). A logged-in user is still not allowed to read another user's invoice.

```diff
  func (h *InvoiceHandler) Get(w http.ResponseWriter, r *http.Request) {
      id := r.PathValue("id")
-     inv, err := h.store.FindInvoice(id)
+     inv, err := h.store.FindInvoice(id)
      if err != nil {
          http.Error(w, "not found", 404)
          return
      }
+     if inv.OwnerID != currentUser(r).ID {
+         http.Error(w, "not found", 404)  // 404, not 403 — don't confirm it exists
+         return
+     }
      writeJSON(w, inv)
  }
```

> **Review comment:** "This looks up the invoice by ID but never checks that it belongs to the caller — any authenticated user can read any invoice by guessing or enumerating IDs. This is Broken Object Level Authorization (BOLA). We need an ownership check after the lookup; returning 404 rather than 403 also avoids confirming the record exists to someone probing. The [authorization post in the API Security series](/blog/posts/api-security-03-authorization.html) covers the pattern."

**The gotcha:** the single highest-value security catch in a review is a missing authorization check on a new object or endpoint — and it is exactly the bug automated scanners are worst at. A SAST tool sees a database lookup and a response; it has no idea that *this* user shouldn't see *that* row, because the rule lives in your domain, not in the code's syntax. BOLA tops the API security risk lists precisely because it is invisible to machines and obvious to a human who asks "whose data is this?" Every time a diff adds an endpoint that takes an ID, that is the question.

### Secrets committed, and sensitive data in logs

Two of the cheapest catches, and both permanent once they land. A hard-coded API key, a database password, a private key, a token in a config file — even if deleted in a later commit, it lives in git history forever and must be rotated, not just removed. And the quieter cousin: sensitive data written to logs.

```diff
- log.Printf("auth attempt: user=%s password=%s token=%s", u, pw, tok)
+ log.Printf("auth attempt: user=%s result=%s", u, result)
```

> **Review comment:** "This logs the raw password and token at info level — they'll land in log aggregation, get indexed, and sit there readable by anyone with log access. Drop the secret fields; log the outcome, not the credentials. Also flagging the `apiKey = \"sk-live-...\"` on line 12 — that needs to move to config/secret storage and the exposed key rotated, since it's now in git history."

The diff tells: a string that looks like a key (`sk-`, `AKIA`, a long base64 blob, `-----BEGIN`), and any log line that formats a password, token, full card number, or personal data.

### Unsafe deserialization, SSRF, and missing rate limits

Three more that hide in ordinary-looking additions:

- **Unsafe deserialization.** A diff that deserializes untrusted bytes with a format that can instantiate arbitrary types (Python `pickle`, Java native serialization, YAML loaders that build objects) is a remote-code-execution risk. Ask why the data isn't JSON with an explicit schema.
- **SSRF via a user-supplied URL.** When the server fetches a URL the user provided — a webhook, an "import from URL," an avatar fetcher — an attacker can point it at `http://169.254.169.254/` (cloud metadata) or internal services. The fix is an allowlist of hosts and blocking internal address ranges, not a blocklist of bad strings.
- **Missing rate limits on expensive or auth endpoints.** A new login endpoint with no throttle is a credential-stuffing target; a new report-generation or search endpoint with no limit is a denial-of-service lever. Flag the *absence* of a limit on anything expensive or authentication-related.

```diff
  func FetchPreview(userURL string) (*http.Response, error) {
-     return http.Get(userURL)   // SSRF: userURL may be an internal address
+     if err := validatePublicURL(userURL); err != nil {  // allowlist scheme+host, block private ranges
+         return nil, err
+     }
+     return safeClient.Get(userURL)
  }
```

> **Review comment:** "`userURL` is user-controlled and we fetch it server-side — that's SSRF. Someone can point it at the cloud metadata endpoint or an internal service the firewall trusts. We need to validate the scheme and host against an allowlist and reject private/link-local ranges *before* the request, and ideally use a client that doesn't follow redirects into those ranges."

### A new dependency is new attack surface

When a diff adds a package to `go.mod`, `package.json`, or `pyproject.toml`, that is not a free line. You are importing someone else's code, and its transitive dependencies, into your trust boundary and your build.

> **Review comment:** "This adds `left-pad-ultra` for one string-padding call — do we need the dependency, or is this ten lines of our own? If we do keep it: is it maintained (last release, open CVEs, download count), and does it pull in a large transitive tree? A one-line helper isn't worth a new supply-chain surface."

**The gotcha:** a new dependency is new attack surface, not just a convenience — every package you add can execute code at install time, ship a future compromised version, or drag in a tree of transitive packages you never chose. Review *why* it is needed and whether it is maintained, the same way you would review code written in-house, because at runtime that is exactly what it is. Trivial functionality is cheaper to own than to import. This ties directly into supply-chain security: the dependency you wave through today is the one in the incident report tomorrow.

### Security smells checklist

A quick scan list for the security lens:

- [ ] User input concatenated into SQL, a shell command, a template, or a path (injection).
- [ ] A new endpoint or object lookup with no ownership/authorization check (BOLA).
- [ ] Hard-coded secrets, keys, or tokens anywhere in the diff.
- [ ] Passwords, tokens, or personal data written to logs or error messages.
- [ ] Deserializing untrusted input with an unsafe format.
- [ ] A server-side fetch of a user-supplied URL (SSRF).
- [ ] A new expensive or authentication endpoint with no rate limit.
- [ ] A new dependency — justified, maintained, and reasonably scoped?
- [ ] Authentication confused for authorization ("logged in" treated as "allowed").

---

## The performance lens: think like production, not like your laptop

The performance mindset is a shift of scale: read the diff as if the data were a thousand times bigger and a hundred requests were hitting it at once. Almost every performance bug that survives review does so because it was tested against a tiny dataset where the problem is genuinely invisible.

### The N+1 query — the classic diff smell

If you learn to spot one performance problem in a diff, make it this one. A loop that runs a query per iteration turns one logical operation into one query plus N more — hence "N+1."

```diff
  orders, _ := db.Query("SELECT id, customer_id FROM orders WHERE status='open'")
  for _, o := range orders {
-     // one query per order — N+1
-     cust, _ := db.Query(
-         "SELECT name FROM customers WHERE id = $1", o.CustomerID)
-     results = append(results, render(o, cust))
+     ids = append(ids, o.CustomerID)
  }
+ // one query for all customers, then join in memory
+ custByID, _ := loadCustomers(db, ids)  // SELECT ... WHERE id = ANY($1)
+ for _, o := range orders {
+     results = append(results, render(o, custByID[o.CustomerID]))
+ }
```

> **Review comment:** "This runs one customer query per order — with 500 open orders that's 501 round trips, and it scales linearly with order volume. It won't show up in the test with three orders, but it will melt in production. Can we collect the customer IDs and fetch them in a single `WHERE id = ANY(...)`, then look them up from a map in the loop? If an ORM is doing the loading, this is where eager-loading / a `JOIN` belongs."

**The gotcha:** an N+1 query is completely invisible in a small test dataset and melts production the moment the table grows — the test with ten rows does eleven fast queries and passes green, while the same code does ten thousand and one against the real table. You cannot catch this by watching it run in CI; you catch it by recognizing the *shape* in the diff — a loop with a query (or an ORM lazy-load, or a network call) inside it. Train your eye on the pattern, because the profiler only finds it after it has already shipped.

### Unbounded queries and missing pagination

A query with no `LIMIT` and no pagination is a landmine planted on a schedule: fine today, an out-of-memory crash the day the result set grows past what one response can hold.

```diff
- rows, _ := db.Query("SELECT * FROM events WHERE user_id = $1", uid)
+ rows, _ := db.Query(
+     "SELECT * FROM events WHERE user_id = $1 ORDER BY id LIMIT $2 OFFSET $3",
+     uid, pageSize, offset)
```

> **Review comment:** "This loads every event for a user into memory with no bound. For an active user that's unbounded growth — a slow response now and an OOM later. Can we paginate (limit + cursor/offset) and have the endpoint return a page? Also selecting `*` when we render three columns pulls more than we need over the wire."

### Work in a loop that should be hoisted, and missing indexes

Two more that read straight off the diff:

- **Loop-invariant work.** A compiled regex, a config lookup, a connection, or a constant computation *inside* a loop that never changes across iterations belongs above the loop. Hoist it once instead of paying for it N times.
- **Missing indexes for a new query pattern.** When a diff introduces a query that filters or joins on a column, ask whether that column is indexed. A new `WHERE tenant_id = ?` against an unindexed column is a full table scan on every call — invisible until the table is large.

```diff
- for _, line := range lines {
-     re := regexp.MustCompile(`^\d{4}-\d{2}-\d{2}`)  // recompiled every iteration
-     if re.MatchString(line) { ... }
- }
+ re := regexp.MustCompile(`^\d{4}-\d{2}-\d{2}`)      // compile once
+ for _, line := range lines {
+     if re.MatchString(line) { ... }
+ }
```

> **Review comment:** "The regex is compiled on every iteration — hoist it above the loop and compile once. Separately, the new `WHERE tenant_id = $1 AND created_at > $2` query: is there an index covering `(tenant_id, created_at)`? Without one this is a sequential scan that gets slower as the table grows — worth an accompanying migration."

### Hot-path allocations, blocking calls, caching, and O(n²)

Rounding out the performance lens:

- **Allocations and O(n²) in hot paths.** A nested loop over the same collection (accidental quadratic), or an allocation inside a tight loop, matters when the path is hot. A membership check that scans a slice inside a loop over another slice is O(n²) — a set/map turns it into O(n).
- **Blocking calls on the request path.** A synchronous HTTP call, a large file read, or a lock held across I/O sitting in the middle of request handling ties up a worker and caps throughput. Ask whether it can move off the hot path or run concurrently.
- **Missing caching for repeated identical work.** If the same expensive computation or lookup runs on every request with the same inputs, a cache may be warranted — but measure first.

### The discipline: don't optimize prematurely, but don't ship the obvious incident

There is a real tension here, and getting it right is the skill. "Premature optimization is the root of all evil" is *correct* about micro-performance — do not rewrite a clean function into an unreadable one to save nanoseconds nobody will notice, and do not demand hand-tuned code where a readable version runs fine. Guessed performance is usually wrong; the honest answer to "is this fast enough?" is often "measure it."

**The gotcha:** "optimize later" is the right call for micro-performance and exactly the wrong call for an unbounded query or a missing index — those are not optimizations, they are latent incidents you are choosing to ship. The distinction is *algorithmic and structural* versus *constant-factor*. An N+1 query, a missing `LIMIT`, an unindexed hot query, an accidental O(n²) — these change how the code scales, and "later" means "during the outage." Constant-factor tuning genuinely can wait for a profiler. Catch the scaling bugs now; defer the micro-tuning until something proves it matters.

### Performance smells checklist

- [ ] A query, network call, or lazy-load inside a loop (N+1).
- [ ] A query with no `LIMIT` / no pagination on data that grows.
- [ ] Loop-invariant work (compiled regex, config lookup, connection) not hoisted.
- [ ] A new filter/join column with no supporting index.
- [ ] Nested loops over the same data (accidental O(n²)) on a hot path.
- [ ] Allocations inside a tight loop.
- [ ] A blocking I/O call or a lock held across I/O on the request path.
- [ ] `SELECT *` where a few columns are used.
- [ ] Repeated identical expensive work that a cache could serve — if measurement supports it.

---

## Know where your eyes stop

The most important thing to internalize about both lenses is their limit. **You cannot fully security-review or performance-review a change by reading it.** A human reviewer catches the *smells* — the pattern, the missing check, the loop-with-a-query — and that is high-value work no tool does well. But depth belongs to instruments built for it.

For security, the diff-level catch is the start; behind it sits SAST (static analysis over the whole codebase), DAST (probing the running app), dependency scanners, and secret scanners in CI. Some classes — a taint path across many files, a vulnerable transitive dependency, a runtime injection — are things a scanner finds and an eyeball won't. A reviewer's job is to catch the human-obvious BOLA the scanner misses, *and* to insist the scanners run for everything else.

For performance, the diff-level catch is the N+1 and the unbounded query; the depth is a profiler on a representative dataset and a load test at expected concurrency. If a change touches a hot path and you cannot tell whether it is fast enough, the right review outcome is not "approve and hope" or "reject on a guess" — it is "please attach a benchmark or a profile before we merge." Ask for the measurement; don't invent it.

| Lens | What the human reviewer catches by eye | What you defer to tools |
|---|---|---|
| Security | Missing authz/BOLA, obvious injection, committed secrets, secrets in logs, unjustified dependency | SAST/DAST, dependency & secret scanners, penetration testing |
| Performance | N+1, unbounded query, missing index, loop-invariant work, obvious O(n²) | Profiler on real data, load/stress test, APM traces |

---

## Key takeaways

- **Assume the input is hostile and follow the data.** Trace every new input to its sink; if it reaches a query, command, path, or fetch without validation or parameterization, you have found the bug.
- **The highest-value security catch is a missing authorization check.** A scanner cannot know whose data a row is; a human asking "may *this* user touch *that* object?" catches the BOLA that tops every API risk list.
- **The N+1 query is the performance smell to train your eye on.** A loop with a query inside is invisible on ten test rows and an incident on ten million — spot the shape in the diff, because the profiler only finds it after it ships.
- **Distinguish latent incidents from micro-optimization.** "Optimize later" is right for constant-factor tuning and wrong for unbounded queries and missing indexes — those change how the code scales, so fix them before merge.
- **A new dependency is new attack surface.** Review why it's needed and whether it's maintained, exactly as you'd review in-house code, because at runtime it is.
- **Know where your eyes stop.** Flag the smells; defer the depth to SAST/DAST, profilers, and load tests. Approving on a guess — in either lens — is how the smell becomes the outage.

---

## Further reading

- [OWASP Code Review Guide](https://owasp.org/www-project-code-review-guide/) — the open, community-maintained reference on reviewing code for security, including how to trace untrusted input to sinks.
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) — concise, practical cheat sheets on injection prevention, deserialization, SSRF, logging, and dependency management, each written as a checklist you can apply during review.
- [OWASP API Security Top 10](https://owasp.org/API-Security/editions/2023/en/0x11-t10/) — the risk list that puts Broken Object Level Authorization (BOLA) at the top, with the reasoning for why authorization bugs dominate API breaches.
- [Martin Fowler on the N+1 query problem (from *Patterns of Enterprise Application Architecture*)](https://martinfowler.com/bliki/AliasingBug.html) and the broader lazy-load discussion in his patterns catalog — a primary treatment of why per-row loading in a loop is the recurring database performance trap.
- The site's own [API Security series](/blog/posts/api-security-01-the-api-security-landscape.html) — deeper, per-vulnerability coverage of the classes this post teaches you to spot in a diff, including [authorization and BOLA](/blog/posts/api-security-03-authorization.html) and [input validation and injection](/blog/posts/api-security-04-input-validation-and-injection.html).
