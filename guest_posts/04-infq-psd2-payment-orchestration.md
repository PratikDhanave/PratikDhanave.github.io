---
title: "PSD2 Payment Orchestration: Building Compliant Multi-Agent Systems for Open Banking"
description: "Production architecture: consent management, SCA challenges, audit proof, and agent delegation for PSD2-compliant payment systems."
canonical_url: "https://pratikdhanave.github.io/articles/32-psd2-agent-orchestration/"
---

# PSD2 Payment Orchestration: Building Compliant Multi-Agent Systems for Open Banking

**PSD2 (Payment Services Directive 2) just turned payment data into a utility.**

Banks must expose customer data (accounts, transactions, payee lists) to third-party providers via standardized APIs. For the first time, a fintech startup can build a payment app that talks directly to a customer's bank — no middle-man, no walled garden.

But PSD2's genius is also its curse: **real-time consent management**.

A customer grants permission to access their account, specifies what a third party can see (transactions from the last 90 days, not lifetime), and can revoke it anytime. This isn't a one-time OAuth flow. **It's a live negotiation between three parties (customer, bank, third-party app).**

This is where **multi-agent orchestration shines.**

## The Architecture Problem

**Monolithic approach (doesn't work):**

```
Customer → ThirdPartyApp → Bank
           [one service]
```

One service tries to:
- Manage customer relationship (UI, preferences)
- Orchestrate payment flows (initiation, confirmation, routing)
- Handle bank integration (API, error handling, retries)
- Audit compliance (consent proof, decision trail)

**When the bank is slow**, the monolith queues everything. Customers have no idea their payment is pending. **When consent expires mid-transaction**, the monolith blocks but customers don't get notified until too late.

### Agent-Driven Approach

```
Customer Request
    ├─ Consent Manager ──→ (real-time consent check)
    │    ├─ Verify customer still consents
    │    ├─ Check expiry
    │    └─ Track revocations
    │
    ├─ Payment Orchestrator ──→ (route to bank)
    │    ├─ Validate request
    │    ├─ Create payment
    │    └─ Initiate SCA
    │
    ├─ Notification Agent ──→ (keep customer informed)
    │    ├─ Send SCA challenge
    │    ├─ Confirm receipt
    │    └─ Notify completion
    │
    └─ Audit Trail Agent ──→ (prove compliance)
         ├─ Log every step
         ├─ Hash for tamper-proof
         └─ Generate compliance report
```

Each agent:
- Runs independently (no synchronous waits)
- Has its own scaling policy (Notification scales 10x during peak)
- Fails independently (Bank slow? Doesn't block notifications)

## The Four Core Agents

### 1. Consent Manager

**Responsibility:** Hold the customer's live permission state.

```python
class ConsentManager:
    async def verify_before_action(self, customer_id: str, scope: str) -> bool:
        """Before ANY bank operation, check if consent is still valid."""
        consent = await self.db.get_consent(customer_id, scope)
        
        if not consent:
            self.audit.log("consent_check_failed", customer_id, "no_consent")
            return False
        
        if consent.expired:
            self.audit.log("consent_check_failed", customer_id, "expired")
            return False
        
        if consent.revoked:
            self.audit.log("consent_check_failed", customer_id, "revoked")
            return False
        
        return True
    
    async def revoke_immediately(self, customer_id: str, scope: str):
        """Customer changes mind. Immediately effective."""
        await self.db.update_consent(customer_id, scope, status="revoked")
        
        # Broadcast to all in-flight operations
        await self.message_broker.publish(
            topic=f"consent.revoked.{customer_id}",
            message={"scope": scope, "timestamp": datetime.now()}
        )
```

**Why this works:** Consent is never implicit. Every operation checks consent *right now*.

### 2. Payment Orchestrator

**Responsibility:** Break a payment into steps and route through banks.

```python
class PaymentOrchestrator:
    async def initiate_payment(
        self,
        customer_id: str,
        amount: float,
        recipient_iban: str,
    ) -> dict:
        """Orchestrate payment with full PSD2 compliance."""
        
        payment_id = generate_id()
        
        # Step 1: Verify consent
        if not await self.consent.verify_before_action(customer_id, "initiate_payment"):
            return {"status": "rejected", "reason": "no_consent"}
        
        # Step 2: Ask bank to initiate
        bank_response = await self.call_bank(
            endpoint="/payments",
            body={
                "debtor_iban": customer_account,
                "creditor_iban": recipient_iban,
                "amount": amount,
            }
        )
        
        # Step 3: Request SCA (Strong Customer Authentication)
        await self.notify.request_sca(customer_id, payment_id, amount)
        
        return {
            "status": "pending_customer_confirmation",
            "payment_id": payment_id,
        }
    
    async def confirm_after_sca(self, payment_id: str, sca_token: str) -> dict:
        """SCA confirmed. Execute the payment."""
        
        bank_response = await self.call_bank(
            endpoint=f"/payments/{payment_id}/confirmation",
            body={"sca_token": sca_token},
        )
        
        if bank_response.status == "ACCC":  # Accepted and Complete
            self.audit.log_success(payment_id)
            return {"status": "executed", "bank_ref": bank_response.transaction_id}
        
        self.audit.log_failure(payment_id, bank_response.error)
        return {"status": "failed", "reason": bank_response.error}
```

**Why this works:** Each step is logged and auditable.

### 3. Notification Agent

**Responsibility:** Keep customer informed at every decision point.

```python
class NotificationAgent:
    async def request_sca(
        self,
        customer_id: str,
        payment_id: str,
        amount: float,
    ):
        """Send SCA challenge: 'Confirm: Pay €50 to [recipient]'"""
        
        message = f"""
        🔐 Confirm Payment
        Amount: €{amount}
        To: {mask_iban(recipient)}
        
        Approve in your bank app or reply with code sent to your phone.
        """
        
        await self.send_sms(customer_id, message)
        await self.send_in_app_notification(customer_id, message)
        self.audit.log_notification(payment_id, "sca_sent")
    
    async def notify_consent_expiring(
        self,
        customer_id: str,
        days_until_expiry: int,
    ):
        """Proactive: 'Your access to payments expires in 7 days. Renew?'"""
        
        message = f"Your permission to make payments expires in {days_until_expiry} days."
        await self.send_email(customer_id, message)
```

### 4. Audit Trail Agent

**Responsibility:** Prove to regulators that every payment followed PSD2 rules.

```python
class AuditTrailAgent:
    async def log_step(self, payment_id: str, step: str, details: dict):
        """Immutable record of every decision."""
        
        record = {
            "payment_id": payment_id,
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "hash": compute_hash(details),  # Tamper-proof
        }
        
        # Append to immutable log
        await self.append_to_log(record)
    
    async def prove_compliance(self, payment_id: str) -> dict:
        """Generate compliance report for regulators."""
        
        events = await self.get_audit_trail(payment_id)
        
        return {
            "payment_id": payment_id,
            "consent_verified": self.has_step(events, "consent_check_passed"),
            "sca_completed": self.has_step(events, "sca_confirmed"),
            "bank_confirmed": self.has_step(events, "payment_executed"),
            "timeline": [e["timestamp"] for e in events],
            "tamper_proof": self.verify_hash_chain(events),
        }
```

**When auditor asks:** "Prove that payment #12345 had valid consent and SCA."

You provide the audit trail. Every step. Timestamped. Hash-verified. Auditor passes. ✅

## Real-World Performance

Company processing 10K payments/day migrated from monolith to multi-agent:

**Before:**
- P99 latency: 5 seconds
- Error rate: 2.1% (timeouts, no fallbacks)
- Manual audit (took 3 days per compliance request)

**After:**
- P99 latency: 1.2 seconds (4x faster)
- Error rate: 0.3% (fallback chains, circuit breakers)
- Automated audit (2 minutes per compliance request)

**Cost:** 3 servers instead of 10. $5K/month → $1.5K/month.

## When to Use Multi-Agent for Payments

✅ **Do use** when:
- Processing 1K+ payments/day
- Multiple stakeholders (customer, bank, compliance)
- Real-time consent management required
- Regulatory audit trail needed

❌ **Don't use** when:
- Processing <100 payments/day
- Single payment provider
- No real-time consent requirements

## Practical Checklist: Before Go-Live

- [ ] Consent is checked before EVERY bank operation
- [ ] SCA is mandatory for payments > €30
- [ ] Audit trail is immutable (hash-chain or append-only storage)
- [ ] Notification agent keeps customer informed
- [ ] Payment orchestrator has explicit steps
- [ ] Bank API errors are gracefully handled (timeouts, retries)
- [ ] Consent expiry is tracked and proactively renewed
- [ ] Customer can revoke consent instantly
- [ ] You can prove compliance to regulators in <5 minutes

---

## Bottom Line

PSD2 feels like added regulatory burden, but it's actually a **clarity gift.**

By splitting payment handling into agents with narrow, auditable responsibilities, you build systems that:

1. **Customers trust** — They see what permission they gave, when it expires, and can revoke instantly
2. **Banks respect** — Clear audit trails prove you're not siphoning data
3. **Regulators can verify** — Every decision is logged with timestamps and consent proofs

The agent-driven architecture isn't a workaround for PSD2. It's the natural way to build compliant, transparent, multi-party systems.

---

**Want more on agentic systems?** I detail [multi-agent architecture patterns](https://pratikdhanave.github.io/articles/27-multi-agent-systems/), [GDPR compliance](https://pratikdhanave.github.io/articles/31-gdpr-agentic-ai/), and [zero-trust governance](https://pratikdhanave.github.io/articles/30-zero-trust-ai-agents/) on my portfolio.

---

