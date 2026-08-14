# Input Validation and Injection

*Part four of the API Security series: treat every byte crossing the boundary as hostile, validate against a schema you control, parameterize at the data sink, and never let a client-supplied URL become a pivot into your network.*

---

The first three posts in this series looked at *who* is calling your API and *what* they are allowed to touch — authentication, authorization, and the mass-assignment trap where a client sneaks `is_admin=true` into a body your handler blindly binds. This post is about the payload itself. Once a request is authenticated and authorized, its contents are still attacker-controlled. A valid session token does not make a JSON body trustworthy.

The failure mode is always the same shape: **data crosses a trust boundary, and somewhere downstream it is interpreted as code.** A string becomes part of a SQL statement. A field becomes a shell argument. A URL becomes an outbound request from inside your VPC. The interpreter — the database, the shell, the HTTP client — cannot tell your intent from the attacker's. That is the whole game, and it is why "sanitize the input" is the wrong mental model. You do not clean hostile data into safe data. You **validate it at the boundary** and **keep it as data at the sink** so it is never parsed as code in the first place.

---

## Validate at the boundary with a schema you own

The boundary is the moment untrusted bytes become a typed object in your program. That is where validation belongs — not scattered through business logic, not "we'll check it before the query." One place, before anything else runs, expressed as a schema.

Good input validation is **allow-list**, not deny-list. You describe exactly what a valid request looks like — types, ranges, lengths, formats, enumerated values — and reject everything else. You do not try to enumerate the bad inputs, because that list is infinite and you will always miss a case.

Concretely, for every field you decide:

- **Type** — is it a string, an integer, a boolean? A `quantity` that arrives as `"12; DROP..."` should fail before it is ever a number.
- **Range** — a `quantity` of `-5` or `2_000_000_000` is nonsense even though it is a valid integer.
- **Length** — an unbounded string is a denial-of-service vector and a buffer for injection payloads.
- **Format** — an email, a UUID, an ISO date. Match against a precise pattern, anchored start to end.
- **Enum** — a `status` field is one of a fixed, known set, never free text.

Pydantic makes this the natural default in Python. The model *is* the contract; parsing and validating are the same step.

```python
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, field_validator

class OrderStatus(str, Enum):
    pending = "pending"
    shipped = "shipped"
    cancelled = "cancelled"

class CreateOrder(BaseModel):
    # Unknown fields are rejected, not silently dropped.
    model_config = {"extra": "forbid"}

    customer_email: EmailStr
    sku: str = Field(min_length=3, max_length=32, pattern=r"^[A-Z0-9\-]+$")
    quantity: int = Field(ge=1, le=1000)
    status: OrderStatus = OrderStatus.pending

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        return v.upper()

# At the boundary: this either yields a fully-typed, in-range object or raises.
order = CreateOrder.model_validate(request_json)
```

The Go equivalent pairs a struct with a validation pass. The `binding`/`validate` tags declare the same allow-list constraints; the framework enforces them before your handler body runs.

```go
type CreateOrder struct {
	CustomerEmail string `json:"customer_email" validate:"required,email"`
	SKU           string `json:"sku"            validate:"required,min=3,max=32,alphanum|contains=-"`
	Quantity      int    `json:"quantity"       validate:"required,gte=1,lte=1000"`
	Status        string `json:"status"         validate:"omitempty,oneof=pending shipped cancelled"`
}

func decodeOrder(r *http.Request) (*CreateOrder, error) {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields() // reject unexpected keys — closes mass assignment

	var in CreateOrder
	if err := dec.Decode(&in); err != nil {
		return nil, fmt.Errorf("malformed body: %w", err)
	}
	if err := validate.Struct(&in); err != nil {
		return nil, fmt.Errorf("invalid order: %w", err)
	}
	return &in, nil
}
```

**The gotcha:** validation must be allow-list, not deny-list. A deny-list — "reject anything containing `'` or `--` or `<script>`" — is a game of whack-a-mole you cannot win, because encodings, Unicode homoglyphs, and payload variants outnumber your filters. An allow-list flips the burden: you enumerate the finite set of *good* shapes and reject the infinite rest by default. The `sku` pattern above accepts `A-Z0-9-` and nothing else; you never have to imagine what a malicious SKU looks like.

---

## Reject unknown fields — one line, two bugs closed

Notice `extra="forbid"` in Pydantic and `DisallowUnknownFields()` in Go. This single choice does two jobs.

First, it closes the mass-assignment door from post three. If a client sends `{"quantity": 2, "is_admin": true, "internal_price": 0}`, a lenient decoder binds what it recognizes and ignores the rest — and "the rest" is exactly where privilege-escalation fields hide. Rejecting unknown fields means the request fails loudly instead of quietly binding something you never intended to expose.

Second, it catches honest client bugs. A frontend that sends `quantiy` (typo) or `customerEmail` (wrong case) gets a clear 400 at integration time, not a mysterious "why is quantity always the default" ticket three weeks later. Strictness is a feature: it turns silent data loss into a loud, early error.

**The gotcha:** rejecting unknown fields closes mass assignment *and* catches typos — the same strictness that stops an attacker from smuggling `is_admin` stops a teammate from silently dropping `customer_email`. Lenient parsing hides both. Turn strictness on at the schema and you never have to remember to check for either.

---

## Injection: keep data as data at the sink

Validation at the boundary reduces the attack surface, but it is not the last line of defense. The real fix for injection lives at the **sink** — the exact place where your data meets an interpreter. The rule there is universal across interpreter types: **never build the command by concatenating strings; pass the data through a channel the interpreter treats as data, not code.**

### SQL injection

The classic. String-building a query mixes your instructions and the attacker's data into one text blob the database then parses as a whole:

```python
# NEVER do this — the value becomes part of the SQL grammar.
cur.execute(f"SELECT * FROM orders WHERE sku = '{sku}'")
# sku = "x' OR '1'='1"  ->  returns every row
# sku = "x'; DROP TABLE orders; --"  ->  ruins your afternoon
```

Parameterized queries (prepared statements) send the query text and the parameter values over *separate* channels. The database compiles the statement first, then binds the values as pure data — a value can never change the statement's structure, no matter what characters it contains.

```python
# Correct — the driver sends SQL and values separately.
cur.execute("SELECT * FROM orders WHERE sku = %s", (sku,))
```

```go
// Correct in Go — placeholders, never fmt.Sprintf into the query.
row := db.QueryRow(
	"SELECT id, quantity FROM orders WHERE sku = $1 AND customer_email = $2",
	order.SKU, order.CustomerEmail,
)
```

Escaping and quoting by hand is not an acceptable substitute. Character-set edge cases and encoding tricks defeat manual escaping; parameterization defeats the entire class because the value is never parsed as SQL to begin with.

**The gotcha:** an ORM is not automatic immunity. Query builders and model methods parameterize for you — right up until someone reaches for the raw escape hatch (`Model.objects.raw(...)`, `session.execute(text(...))`, `db.Raw(...)`, `.extra()`) and interpolates a string into it. The moment you `f"...{user_input}..."` inside a raw query, you have reintroduced the exact vulnerability the ORM was protecting you from. Raw queries are fine — raw queries with **placeholders** — but string-concatenated raw queries are SQL injection with extra steps.

### NoSQL injection

Document stores are not immune; they just have a different grammar. When a request body is passed straight into a query object, an attacker can substitute an operator for a value:

```python
# Attacker sends {"username": {"$ne": null}, "password": {"$ne": null}}
db.users.find_one({"username": body["username"], "password": body["password"]})
# The $ne operators match the first user — an auth bypass.
```

The defense is the same principle at a different sink: validate that each field is the scalar type you expect (a string, not a dict) at the boundary, and never let request-derived data introduce query operators. Your Pydantic model declaring `username: str` rejects the `{"$ne": null}` object outright.

### Command injection

If your API ever shells out — generating a thumbnail, calling a CLI tool — the danger is passing user data through a shell that re-parses it.

```python
import subprocess

# DANGEROUS: shell=True re-parses the whole string.
# filename = "photo.jpg; rm -rf /"  ->  the shell runs both commands.
subprocess.run(f"convert {filename} out.png", shell=True)

# SAFE: argument vector, no shell. Data stays in one argv slot.
subprocess.run(["convert", filename, "out.png"], shell=False, check=True)
```

```go
// SAFE in Go: exec.Command takes argv directly — no shell parsing.
// Never build a string and hand it to `sh -c`.
cmd := exec.Command("convert", filename, "out.png")
```

Pass an argument vector, never a shell string. When each argument occupies its own slot in `argv`, shell metacharacters (`;`, `|`, `$()`, backticks) are inert — they are just bytes in a filename, not directives.

---

## SSRF: when "fetch this URL" becomes a pivot

Server-Side Request Forgery (OWASP API7:2023) is the injection class people forget, because the "interpreter" is your own HTTP client. Any endpoint that accepts a URL from the client and fetches it — webhook registration, "import from URL," an avatar-by-link feature, a link preview generator — can be steered at targets the client could never reach directly.

```http
POST /api/v1/import HTTP/1.1
Content-Type: application/json

{ "source_url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/" }
```

That address is the cloud instance metadata endpoint. Your server, sitting inside the network with an instance role, cheerfully fetches it and hands back credentials. The same trick reaches internal admin panels (`http://10.0.0.5:8080/admin`), other services on `localhost`, and databases bound to private interfaces — all invisible from the public internet but wide open to a request originating from *your* server.

Validating "is this a well-formed URL" is not enough; `http://169.254.169.254/` is perfectly well-formed. You need an **allow-list of destinations** plus an explicit block of internal and link-local ranges — and you must enforce it against the IP you actually connect to, not the hostname the attacker typed.

```python
import ipaddress, socket
from urllib.parse import urlparse
import httpx

ALLOWED_HOSTS = {"api.trusted-partner.com", "cdn.example.com"}

def _is_public_ip(host: str) -> bool:
    # Resolve first, then judge the resolved address — DNS can point anywhere.
    for info in socket.getaddrinfo(host, None):
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            return False
    return True

def safe_fetch(raw_url: str) -> httpx.Response:
    url = urlparse(raw_url)
    if url.scheme not in ("https", "http"):
        raise ValueError("only http(s) is allowed")
    if url.hostname not in ALLOWED_HOSTS:      # allow-list of destinations
        raise ValueError(f"host not permitted: {url.hostname}")
    if not _is_public_ip(url.hostname):        # block internal/link-local
        raise ValueError("host resolves to a non-public address")
    # Do NOT follow redirects — a 302 to 169.254.169.254 defeats every check above.
    return httpx.get(raw_url, follow_redirects=False, timeout=5.0)
```

```go
// Go: a Dial hook is the robust place to enforce the block, because it sees
// the concrete IP for the initial request AND every redirect hop.
func safeDialContext(ctx context.Context, network, addr string) (net.Conn, error) {
	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		return nil, err
	}
	ips, err := net.DefaultResolver.LookupIPAddr(ctx, host)
	if err != nil {
		return nil, err
	}
	for _, ip := range ips {
		if ip.IP.IsPrivate() || ip.IP.IsLoopback() ||
			ip.IP.IsLinkLocalUnicast() || ip.IP.IsUnspecified() {
			return nil, fmt.Errorf("blocked non-public address: %s", ip.IP)
		}
	}
	return (&net.Dialer{Timeout: 5 * time.Second}).DialContext(ctx, network, net.JoinHostPort(host, port))
}
```

**The gotcha:** SSRF turns a helpful "fetch this URL for me" into a pivot to your internal network and cloud metadata endpoint — and the two mistakes that make it exploitable are checking the *hostname* instead of the *resolved IP*, and **following redirects**. An attacker registers a domain that resolves to `169.254.169.254`, or simply serves a `302 Location: http://10.0.0.5/` — and any check you ran on the original URL is bypassed on the hop your validator never saw. Allow-list the destination hosts, block private and link-local ranges against the resolved address, and disable redirect-following (or re-run the block on every hop, as the Go dialer does).

---

## XML, deserialization, and the output sink

Two more sinks round out the picture.

**XML and deserialization.** Parsing formats that can carry references or type instructions is dangerous by default. An XML parser with external-entity resolution enabled reads attacker-defined entities that pull in local files or make outbound requests — XXE, itself an SSRF vector. Deserializers that reconstruct arbitrary object types from a byte stream (native pickle, unsafe YAML loaders, Java/`.NET` binary formats) can be coerced into constructing objects that execute code as a side effect of being built. The defenses: disable external entity and DTD processing on any XML parser, and never deserialize untrusted input with a format that reconstructs arbitrary types. For data interchange, prefer plain JSON parsed into your validated schema — JSON carries values, not object graphs or code.

```python
# Safe YAML: values only, no arbitrary object construction.
import yaml
data = yaml.safe_load(untrusted_text)   # NOT yaml.load / Loader=FullLoader on untrusted input
```

**Output encoding — XSS at the sink.** APIs mostly return JSON to code, but the moment your output reaches an HTML context — a server-rendered page, a dashboard that interpolates an API field into the DOM, an email template — unescaped data becomes cross-site scripting. Input validation does not fix this; the correct fix is **context-aware output encoding at the sink where the value is rendered**. A `display_name` of `<img src=x onerror=alert(1)>` is a perfectly valid string to *store*; it is only dangerous when written into HTML without encoding. Encode for the specific context (HTML body, attribute, JS, URL) at render time. And always send `Content-Type: application/json` with a correct charset so a browser never sniffs a JSON response as HTML and executes a payload in it.

---

## Where each defense lives

| Threat | Defense | Where it lives |
|---|---|---|
| Malformed / out-of-range input | Schema validation (type, range, length, format, enum) | Request boundary |
| Mass assignment, client typos | Reject unknown fields (`extra="forbid"` / `DisallowUnknownFields`) | Request boundary |
| SQL / NoSQL injection | Parameterized queries; scalar-typed fields; no raw string-concat | Data sink |
| Command injection | Argument vector, no shell (`shell=False` / `exec.Command`) | OS sink |
| SSRF (API7) | Host allow-list, block private/link-local by resolved IP, no redirects | HTTP client sink |
| XXE / unsafe deserialization | Disable DTDs/entities; safe loaders; JSON over object formats | Parser |
| XSS | Context-aware output encoding; correct `Content-Type` | Output sink |

---

## Key takeaways

- **Validate at the boundary, allow-list not deny-list.** Describe the finite set of valid inputs — type, range, length, format, enum — and reject the infinite rest. A block-list of bad patterns always misses a case.
- **Reject unknown fields.** One schema setting closes mass assignment and catches client typos at the same time. Lenient parsing hides both.
- **Parameterize at the sink.** Prepared statements keep values as data so they are never parsed as SQL. ORMs help, but a string-concatenated `raw()` query throws that protection away.
- **Every interpreter is a sink.** The SQL rule generalizes: argument vectors for the shell, scalar-typed fields for NoSQL, safe loaders for deserializers. Never let data be re-parsed as code.
- **Treat URLs and redirects as attacker-controlled.** SSRF turns "fetch this for me" into a network pivot. Allow-list destinations, block private and link-local ranges against the *resolved* IP, and never follow redirects to them.
- **Encode at the output sink.** When API data reaches a browser, context-aware encoding — not input filtering — is what stops XSS.

---

## Further reading

- [OWASP API Security Top 10 — API7:2023 Server Side Request Forgery](https://owasp.org/API-Security/editions/2023/en/0xa7-server-side-request-forgery/)
- [OWASP Cheat Sheet — Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)
- [OWASP Cheat Sheet — SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP Cheat Sheet — Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP Cheat Sheet — Server Side Request Forgery Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
