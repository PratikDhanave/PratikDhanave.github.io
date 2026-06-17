# Tool Wrapping: From ADK Functions to MAF Governed Tools

*How to port tools, add policy enforcement, and integrate OPA.*

---

## The Basics: @tool Decorator

**ADK**:
```python
def fetch_account_balance(account_id: str) -> float:
    """Get the account balance for an account."""
    return db.query(f"SELECT balance FROM accounts WHERE id = {account_id}")

agent = Agent(..., tools=[fetch_account_balance])
```

**MAF**:
```python
from agent_framework import tool

@tool
def fetch_account_balance(account_id: str) -> float:
    """Get the account balance for an account."""
    return db.query(f"SELECT balance FROM accounts WHERE id = {account_id}")

agent = Agent(..., tools=[fetch_account_balance])
```

The signature and docstring become the schema. That's it.

## Adding Policy: Governed Tools

In regulated environments, you need:
- **DLP** (prevent sensitive data leakage)
- **Audit** (log every tool call)
- **Approval** (human-in-the-loop for risky operations)

MAF's `governed.*` wrappers give you this:

```python
from multi_agent.tools import governed_write, governed_delete, governed_query

@tool
@governed_query(schema="users", audit=True)  # Log read; no approval needed
def fetch_user(user_id: str) -> dict:
    """Get user details."""
    return db.users[user_id]

@tool
@governed_write(schema="users", audit=True, approval=True)  # Log + require approval
def update_user(user_id: str, data: dict) -> None:
    """Update user details."""
    db.users[user_id].update(data)

@tool
@governed_delete(schema="users", audit=True, approval=True)  # Log + require approval
def delete_user(user_id: str) -> None:
    """Delete a user account."""
    db.users[user_id].delete()

agent = Agent(..., tools=[fetch_user, update_user, delete_user])
```

Every tool call is logged. Approval-gated tools queue for human review.

## Pattern 1: Wrapping External APIs

You have an external payment API. ADK would call it directly. MAF wraps it:

**ADK**:
```python
def charge_card(user_id: str, amount: float) -> dict:
    """Charge a card."""
    return payment_api.charge(user_id, amount)

agent = Agent(..., tools=[charge_card])
```

No control. No audit. No approval.

**MAF**:
```python
@tool
@governed_write(schema="payments", audit=True, approval=True, amount_limit=10000)
async def charge_card(user_id: str, amount: float) -> dict:
    """Charge a card for a payment."""
    # The governance layer checks:
    # - User is authorized to make payments
    # - Amount < limit
    # - Call is logged
    # - If > manual approval threshold, queue for human
    return await payment_api.charge(user_id, amount)

agent = Agent(..., tools=[charge_card])
```

**Result**: Auto-approval for small charges. Manual approval for large ones. Full audit trail.

## Pattern 2: OPA (Open Policy Agent) Integration

For complex policies (e.g., "user can only access their own data unless they have a manager role"), use OPA:

```python
from multi_agent.tools import opa_governed_tool

# Define the policy in Rego
POLICY = """
allow {
    input.user_role == "admin"
} {
    input.user_id == input.requested_user_id
    input.user_role == "user"
}
"""

@tool
@opa_governed_tool(policy=POLICY, input_builder=lambda user_id, requested_user_id, **kw: {
    "user_id": user_id,
    "requested_user_id": requested_user_id,
    "user_role": get_user_role(user_id)
})
def fetch_user_profile(user_id: str, requested_user_id: str) -> dict:
    """Fetch another user's profile."""
    return db.users[requested_user_id]

# Call it
result = await fetch_user_profile("alice", "bob")
# OPA checks: alice's role, can she see bob? If yes, return profile. If no, raise exception.
```

OPA becomes your policy engine. The tool becomes your enforcement point.

## Pattern 3: Multi-Step Tools

A tool might need to:
1. Check permissions
2. Log the request
3. Call the API
4. Process the response
5. Log the result

**ADK** would mix all this into the function. **MAF** lets you layer it:

```python
async def call_payment_api(user_id: str, amount: float) -> dict:
    """Raw API call."""
    return await payment_api.charge(user_id, amount)

# Layer 1: Governance (approval gate)
governed = governed_write(
    schema="payments",
    audit=True,
    approval=True,
    amount_limit=10000
)(call_payment_api)

# Layer 2: Observability (tracing)
from multi_agent.observability import traced_tool
traced = traced_tool(governed)

# Layer 3: Retry + resilience
from tenacity import retry, stop_after_attempt
resilient = retry(stop=stop_after_attempt(3))(traced)

# Use it
agent = Agent(..., tools=[resilient])
```

Each layer is composable. You can test governance independently from tracing.

## The Conversion Checklist

**For every ADK tool:**

- [ ] Extract function signature + docstring
- [ ] Apply `@tool` decorator
- [ ] Identify the operation: read? write? delete?
- [ ] Apply governance: `@governed_query`, `@governed_write`, `@governed_delete`
- [ ] If complex policy: switch to `@opa_governed_tool`
- [ ] If external API: wrap the call; add retry logic
- [ ] If sensitive: add audit logging
- [ ] Test the tool independently; test with governance separately

## Real Example: Genie's Tools

We ported three tools from ADK:

### 1. Portfolio Query (read-only)
```python
@tool
@governed_query(schema="portfolios", audit=True)
def get_portfolio(portfolio_id: str) -> dict:
    """Get the portfolio details and current holdings."""
    return db.portfolios[portfolio_id].to_dict()
```

No approval needed. Just audit.

### 2. Trade Execution (write + approval)
```python
@tool
@governed_write(schema="trades", audit=True, approval=True)
async def execute_trade(portfolio_id: str, symbol: str, quantity: int, price: float) -> dict:
    """Execute a trade. Requires manual approval for size > 100 shares."""
    cost = quantity * price
    if cost > 50000:  # Manual approval gate
        # Raise exception; governance layer handles approval flow
        pass
    return await broker_api.execute_trade(portfolio_id, symbol, quantity, price)
```

Automatic for small trades. Manual approval for large ones.

### 3. Alert Configuration (write + policy)
```python
ALERT_POLICY = """
allow {
    input.user_role == "advisor"
    input.alert_type == "daily"
} {
    input.user_role == "client"
    input.alert_type in ["critical", "weekly"]
}
"""

@tool
@opa_governed_tool(policy=ALERT_POLICY)
def set_alert(user_id: str, alert_type: str, threshold: float) -> None:
    """Set a price alert."""
    db.alerts[user_id].append({"type": alert_type, "threshold": threshold})
```

Advisors can set any alert. Clients can only set critical/weekly. OPA enforces it.

---

Next: [Provider Abstraction and .env Configuration](/blog/posts/adk-to-maf-provider-config.html)
