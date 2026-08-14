# Authorization: BOLA, BFLA, and Object-Level Access

*Why the biggest class of API bugs is not about who you are but about what you are allowed to touch — and how to check ownership, function access, and property access on every single request.*

---

Post 2 in this series drew a hard line: **authentication is not authorization**. Authentication answers *who is calling* — it validates a token, a session, an API key. Authorization answers *what that caller may do* — read this order, delete that user, set this field. A caller can be perfectly authenticated and still have no business touching the record they just asked for.

That gap is where most real API breaches live. Look at the OWASP API Security Top 10 and the top of the list is not injection or misconfiguration — it is **authorization**. Three of the ten entries are pure access-control failures: object-level (API1), object-property-level (API3), and function-level (API5). They dominate because authorization is *per-request, per-object, per-field* — and every one of those checkpoints is a place a developer can forget.

This post walks the three failures in order, with Python and Go examples you can map onto your own stack, and one rule underneath all of them: **authorize every object and every function, server-side, deny-by-default.**

---

## The shape of the problem

A monolithic web app renders pages server-side, so authorization often rides along with the view: the page only shows *your* orders because the controller only queried *your* orders. APIs strip that away. The client asks for a specific resource by id — `GET /orders/8842` — and the server hands back whatever that id names. If nobody checks that order 8842 belongs to the caller, the API has just become a lookup service for other people's data.

The model that keeps this straight has two layers:

- **Coarse-grained**: *does this role reach this capability at all?* An anonymous user cannot reach the admin panel; a standard user cannot call the billing-refund endpoint. This is **function-level** authorization.
- **Fine-grained**: *may this specific caller act on this specific object or field?* You are a valid customer, but this is not your invoice. This is **object-level** and **object-property-level** authorization.

Skip either layer and you have a hole. The rest of this post is those two layers, in the order attackers probe them.

---

## 1. Broken Object Level Authorization (BOLA / IDOR) — OWASP API1

This is the number-one API risk, and it is embarrassingly simple. The API authenticates the caller, then trusts a client-supplied identifier to select the object — without ever checking the object belongs to that caller.

```http
GET /api/orders/8842 HTTP/1.1
Authorization: Bearer <valid token for user 17>
```

If the handler does `SELECT * FROM orders WHERE id = 8842` and returns the row, user 17 just read an order that might belong to user 42. Increment the id, script it, and you have walked the whole table. The same bug is often called **IDOR** — Insecure Direct Object Reference — and it applies to any identifier the client controls: numeric ids, UUIDs, filenames, slugs, even values buried in a JWT claim the client can tamper with before it is verified.

Why is it so common? Because the check is *invisible when it is missing*. The endpoint works. The tests pass. The happy path — a user reading their own order — behaves identically whether or not the ownership check exists. The bug only appears when someone asks for an id that is not theirs, and nobody wrote that test.

**The gotcha:** a valid token says *who*, not *what they can touch*. Authentication middleware that rejects bad tokens gives a false sense of safety — every request past it is authenticated, and none of it is authorized until you check the object.

### Prevent it: scope the query by the caller's identity

The fix is not to *add a check after fetching* — that is fragile and easy to forget. The durable fix is to make the caller's identity part of the query, so the data layer can never return an object the caller does not own.

```python
# Bad: trusts the client-supplied id, checks ownership nowhere.
def get_order(order_id: int, user):
    return db.query("SELECT * FROM orders WHERE id = %s", order_id)

# Good: the caller's id is part of the WHERE clause. A foreign id
# returns nothing, so there is no object to leak.
def get_order(order_id: int, user):
    row = db.query(
        "SELECT * FROM orders WHERE id = %s AND owner_id = %s",
        order_id, user.id,
    )
    if row is None:
        # 404, not 403 — do not confirm the object exists to a
        # caller who is not allowed to know it does.
        raise NotFound()
    return row
```

The same discipline in Go, where an explicit ownership guard reads clearly:

```go
func (s *Store) GetOrder(ctx context.Context, orderID int64, callerID int64) (*Order, error) {
    var o Order
    err := s.db.QueryRowContext(ctx,
        `SELECT id, owner_id, total FROM orders WHERE id = $1 AND owner_id = $2`,
        orderID, callerID,
    ).Scan(&o.ID, &o.OwnerID, &o.Total)
    if errors.Is(err, sql.ErrNoRows) {
        return nil, ErrNotFound // caller does not own it (or it does not exist)
    }
    return &o, err
}
```

For multi-tenant systems, the same idea widens to **tenancy**: every query carries the caller's `tenant_id`, and no query ever runs without it. The strongest version pushes this into a place it cannot be bypassed — a repository layer that refuses to build a query without a tenant scope, row-level security in the database, or a query builder that injects the tenant predicate automatically. When the scope lives in one enforced place, an individual endpoint author cannot forget it.

**The gotcha:** BOLA is invisible in tests that only use one user's own data. A test suite where "Alice reads Alice's order" passes tells you nothing. You must test **cross-tenant access explicitly** — authenticate as Alice, request Bob's object id, and assert you get a 404. That negative test is the only thing that catches the bug.

A last note on ids: switching numeric ids to UUIDs raises the effort of guessing but does not fix BOLA. A UUID that leaks in a URL, a referrer header, a shared link, or a prior response is still a direct object reference. Unguessable is not the same as authorized.

---

## 2. Broken Function Level Authorization (BFLA) — OWASP API5

Where BOLA is about *objects*, BFLA is about *operations*. It happens when a caller reaches a function — an endpoint, an HTTP method, an administrative action — that their role should never expose.

The classic shapes:

- A standard user calls `DELETE /api/users/42` and it works, because the handler checks authentication but not role.
- An endpoint under `/api/admin/...` has no server-side role gate; it was "hidden" because the UI never renders a link to it.
- `GET /api/orders/8842` is protected but the `PUT`/`DELETE` on the same path is not — the read was guarded and the mutating methods were forgotten.

```http
POST /api/admin/users/42/promote HTTP/1.1
Authorization: Bearer <valid token for an ordinary user>
```

If that returns `200 OK`, the endpoint is trusting the *existence* of a token rather than the *role* inside it. Attackers find these by enumerating methods and guessing admin routes — HTTP verbs and predictable path segments (`/admin`, `/internal`, `/v1/users/{id}/roles`) are a small search space.

**The gotcha:** hiding an admin button does not protect the admin *endpoint*. The browser is fully under the caller's control; a route that is not linked in the UI is one `curl` away. Function authorization has to be enforced on the server, on every method of every route — never in the client.

### Prevent it: deny-by-default, checked server-side

The safe posture is **deny-by-default**: an endpoint is inaccessible unless a rule explicitly grants the caller's role. That inverts the risk. With allow-by-default, forgetting a check exposes an endpoint; with deny-by-default, forgetting a check *closes* it — a much safer failure mode.

```python
# A deny-by-default decorator: no matching role, no entry.
def require_role(*allowed):
    def decorator(handler):
        @functools.wraps(handler)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed:
                raise Forbidden()  # 403 by default
            return handler(request, *args, **kwargs)
        return wrapper
    return decorator

@require_role("admin")
def delete_user(request, user_id: int):
    ...
```

In Go, the same gate as middleware wrapping the admin routes:

```go
func RequireRole(allowed ...string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            role := CallerFromContext(r.Context()).Role
            if !slices.Contains(allowed, role) {
                http.Error(w, "forbidden", http.StatusForbidden)
                return
            }
            next.ServeHTTP(w, r)
        })
    }
}

// admin.Handle("/users/", RequireRole("admin")(usersHandler))
```

Two things make this robust. First, the default is *no access* — a new route added under the admin group inherits the gate unless someone deliberately opens it. Second, the check reads the role from a **server-trusted source** — the verified token or session — never from a request body, header, or query parameter the client can set.

---

## 3. Broken Object Property Level Authorization — OWASP API3

The third failure is finer still. The caller may legitimately reach the endpoint *and* own the object — but the request or response operates on *properties* they should not control or see. OWASP folds two old categories into this one: **mass assignment** (writing properties you shouldn't) and **excessive data exposure** (reading properties you shouldn't).

### Mass assignment — the input side

Frameworks that auto-bind a JSON body to a model are a convenience trap. If the endpoint does `user.update(**request.json)`, then whatever the client sends gets written — including fields the client was never meant to control.

```http
PATCH /api/users/17 HTTP/1.1
Authorization: Bearer <valid token for user 17>
Content-Type: application/json

{ "displayName": "Pratik", "role": "admin", "isVerified": true, "balance": 999999 }
```

The user meant to change their display name. If the handler binds the whole body, they also just made themselves an admin, marked their account verified, and set their balance. The endpoint is theirs, the object is theirs — but `role`, `isVerified`, and `balance` are not fields they may write.

**The gotcha:** mass assignment binds *whatever the client sends*. Never bind a raw request body to your persistence model. The safe pattern is an **allow-listed input DTO**: a small object that names exactly the fields this endpoint accepts, and nothing else. Extra fields are dropped, not written.

```python
# Explicit allow-list. Only these fields can ever be written here,
# no matter what the client sends.
@dataclass
class UpdateProfileInput:
    display_name: str
    bio: str | None = None

def update_profile(request, user):
    data = UpdateProfileInput(
        display_name=request.json["displayName"],
        bio=request.json.get("bio"),
    )
    user.display_name = data.display_name
    user.bio = data.bio
    # role, isVerified, balance are simply never assignable here.
    db.save(user)
```

In Go, decoding into a purpose-built struct does the same job — the request can only ever populate the fields the struct declares:

```go
type UpdateProfileInput struct {
    DisplayName string `json:"displayName"`
    Bio         string `json:"bio"`
}

func updateProfile(w http.ResponseWriter, r *http.Request) {
    var in UpdateProfileInput
    if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
        http.Error(w, "bad request", http.StatusBadRequest)
        return
    }
    // Map only these fields onto the model. Role/Balance are unreachable.
    user.DisplayName = in.DisplayName
    user.Bio = in.Bio
}
```

Privileged fields like `role` should only ever be settable through a separate, function-authorized endpoint (`POST /api/admin/users/{id}/role`, gated by `require_role("admin")`) — never as a side effect of a profile update.

### Excessive data exposure — the output side

The mirror image: returning the whole object and trusting the client to only display the safe parts. `return jsonify(user.__dict__)` on a user record happily ships `password_hash`, `mfa_secret`, internal flags, and another user's PII if the object was fetched without scoping. "The mobile app only shows the name" is not a control — the raw JSON is right there in the response.

The fix is symmetric with the input side: an **allow-listed output DTO** that names exactly the fields this caller may see.

```python
def public_user_view(user):
    # Explicit output shape. New model fields are NOT exposed by
    # default — you must add them here on purpose.
    return {
        "id": user.id,
        "displayName": user.display_name,
        "bio": user.bio,
    }
```

Serializing through an explicit view means adding a sensitive column to the model does not silently leak it — the field stays invisible until someone deliberately adds it to the DTO. That is deny-by-default applied to output.

---

## RBAC, ABAC, and where the rules should live

Two models cover most authorization needs:

| | RBAC (role-based) | ABAC (attribute-based) |
|---|---|---|
| Decides on | The caller's role | Attributes of caller, resource, action, context |
| Example rule | "admins may delete users" | "a manager may approve expenses under $5k in their own region" |
| Strength | Simple, auditable, easy to reason about | Expresses ownership, tenancy, limits, time-of-day |
| Watch out for | Role explosion as edge cases pile up | Policies become hard to test and audit |

In practice most systems are a blend: RBAC handles the coarse function-level gate ("is this caller an admin?"), while ABAC-style checks handle the fine object-level rule ("is this the caller's own order, in the caller's tenant?"). BFLA is usually an RBAC failure; BOLA is usually a missing attribute check.

The deeper question is *where* authorization logic lives. Scattering `if user.role == "admin"` across dozens of handlers guarantees that one handler eventually forgets. **Centralizing** the decision — a policy function, a middleware layer, a dedicated policy engine, or database row-level security — gives you one place to read, test, and audit the rules. Centralization also makes deny-by-default enforceable: the shared gate says no unless a policy says yes, so a new endpoint is safe until someone opens it on purpose.

Centralize the *decision*; you still have to place the *checkpoint*. Object-level checks must run at the point of data access (or be baked into the scoped query), because only there do you have the object and the caller together. A central policy engine that is never called on the order-fetch path protects nothing.

---

## Key takeaways

- **Authentication is not authorization.** A verified token establishes *who*; every object and every function still needs a separate check for *what they may do*. This is the whole reason authorization dominates the OWASP API Top 10.
- **BOLA (API1) is the top risk and the easiest to miss.** Scope every query by the caller's identity or tenant so a foreign id returns nothing. Do not trust client-supplied ids, and test cross-tenant access explicitly — the happy path hides the bug.
- **BFLA (API5) means missing function gates.** Enforce role checks server-side on every method of every route, deny-by-default. Hiding a button in the UI protects nothing.
- **API3 is about properties.** Use allow-listed input DTOs so the client cannot mass-assign `role` or `balance`, and allow-listed output DTOs so you never leak fields by returning the raw model.
- **Centralize the policy, place the checkpoint.** RBAC for coarse function access, attribute checks for fine object access; one auditable place to decide, enforced at the point where you actually hold the object.

Authorize every object. Authorize every function. Server-side. Deny-by-default. Everything in this post is a variation on those four words.

---

## Further reading

- [OWASP API1:2023 — Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)
- [OWASP API3:2023 — Broken Object Property Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa3-broken-object-property-level-authorization/)
- [OWASP API5:2023 — Broken Function Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization/)
- [OWASP Cheat Sheet — Mass Assignment](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)
- [OWASP Cheat Sheet — Insecure Direct Object Reference Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)
- [OWASP Cheat Sheet — Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
