---
title: "PSD2 Open Banking with Multi-Agent Orchestration: Consent-Driven Payment Workflows"
description: "Production-grade technical deep-dive on PSD2OpenBankingwithMulti-AgentOrchestration:Consent-DrivenPaymentWorkflows"
keywords: ["32-psd2-agent-orchestration"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
---

# PSD2 Open Banking with Multi-Agent Orchestration: Consent-Driven Payment Workflows

**PSD2 (Payment Services Directive 2) just turned payment data into a utility.** Banks must expose customer data (accounts, transactions, payee lists) to third-party providers via standardized APIs. For the first time, a fintech startup can build a payment app that talks directly to a customer's bank — no middle-man, no walled garden.

But PSD2's genius is also its curse: it requires **real-time consent management**. A customer grants permission to access their account, specifies what a third party can see (transactions from the last 90 days, not lifetime), and can revoke it anytime. This isn't a one-time OAuth flow; it's a live negotiation between three parties (customer, bank, third-party app).

This is where **multi-agent orchestration shines.** Each stakeholder becomes an agent with explicit responsibilities and boundaries.

---

## The PSD2 Architecture Problem

### **Traditional Approach (Doesn't Work)**

```
Customer → ThirdPartyApp → BankAPI
           [monolithic]
```

A single service tries to:
- Manage the customer relationship (UI, preferences, notifications)
- Orchestrate payment flows (initiation, confirmation, routing)
- Handle bank integration (API contracts, error handling, retries)
- Audit compliance (prove consent was obtained, trace every API call)

**Problem:** When the bank rejects a payment, when consent expires mid-transaction, when the customer changes permissions — the monolith has no clean way to handle these branching paths. And from a compliance perspective, you can't prove which component made which decision.

### **PSD2-Compliant Architecture (Agent-Driven)**

```
Customer Agent ─┬─ Consent Manager ─┬─ Payment Orchestrator ─ Bank Agent
                │                   │
                ├─ Notification Agent
                └─ Audit Trail Agent
```

Each agent has a **narrow, auditable responsibility** and explicit consent boundaries.

---

## The Four Core Agents

### **Agent 1: Consent Manager**

**Responsibility:** Hold the customer's live permission state. No payment happens without explicit consent.

```python
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

class ConsentStatus(Enum):
    PENDING = "pending"        # Customer hasn't approved yet
    ACTIVE = "active"          # Consent is live
    REVOKED = "revoked"        # Customer revoked it
    EXPIRED = "expired"         # Consent timed out

@dataclass
class Consent:
    customer_id: str
    scope: str  # e.g., "read_accounts", "read_transactions_90d", "initiate_payment"
    status: ConsentStatus
    created_at: datetime
    expires_at: datetime
    bank_consent_reference: str  # Proof from bank that they saw this
    
    def is_valid_now(self) -> bool:
        """Is this consent still active RIGHT NOW?"""
        return (
            self.status == ConsentStatus.ACTIVE and
            datetime.now() < self.expires_at
        )

class ConsentManager:
    """Single source of truth for what a customer allows."""
    
    def request_consent(
        self,
        customer_id: str,
        scope: str,
        reason: str,
    ) -> str:
        """Ask customer for permission. Return consent request ID."""
        consent = Consent(
            customer_id=customer_id,
            scope=scope,
            status=ConsentStatus.PENDING,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=365),  # PSD2 default
            bank_consent_reference="",
        )
        store_consent(consent)
        # Trigger customer UI: "App XYZ wants permission to read your accounts"
        return consent.id

    def approve_consent(
        self,
        consent_id: str,
        bank_consent_reference: str,
    ):
        """Customer approved. Bank sent confirmation."""
        consent = load_consent(consent_id)
        consent.status = ConsentStatus.ACTIVE
        consent.bank_consent_reference = bank_consent_reference
        save_consent(consent)
        audit_log.record({
            "event": "consent_approved",
            "consent_id": consent_id,
            "bank_ref": bank_consent_reference,
            "timestamp": datetime.now(),
        })

    def verify_consent_before_action(
        self,
        customer_id: str,
        required_scope: str,
    ) -> bool:
        """Before ANY bank operation, verify the customer still consents."""
        consent = load_consent_by_customer_and_scope(customer_id, required_scope)
        if not consent or not consent.is_valid_now():
            audit_log.record({
                "event": "consent_check_failed",
                "customer_id": customer_id,
                "required_scope": required_scope,
                "reason": "no active consent",
            })
            return False
        return True

    def revoke_consent(self, customer_id: str, scope: str):
        """Customer changed their mind. Immediately effective."""
        consent = load_consent_by_customer_and_scope(customer_id, scope)
        consent.status = ConsentStatus.REVOKED
        save_consent(consent)
        # Notify Bank Agent: this customer revoked read_transactions access
        notify_bank_agent(customer_id, scope, "revoked")
        audit_log.record({
            "event": "consent_revoked",
            "customer_id": customer_id,
            "scope": scope,
            "timestamp": datetime.now(),
        })
```

**Why this works:** Consent is never implicit. Every operation checks: "Does this customer still allow this action *right now*?" If consent expired 5 minutes ago, the payment is rejected.

---

### **Agent 2: Payment Orchestrator**

**Responsibility:** Take a payment request from the customer, break it into steps, and route through the correct banks/intermediaries.

```python
from enum import Enum
from typing import Optional

class PaymentStep(Enum):
    VALIDATE = "validate"
    CHECK_CONSENT = "check_consent"
    INITIATE_WITH_BANK = "initiate_with_bank"
    GET_CUSTOMER_CONFIRMATION = "get_customer_confirmation"
    EXECUTE = "execute"
    CONFIRM = "confirm"

class PaymentOrchestrator:
    def __init__(self, consent_manager, notification_agent, audit_agent):
        self.consent = consent_manager
        self.notify = notification_agent
        self.audit = audit_agent

    def initiate_payment(
        self,
        customer_id: str,
        amount: float,
        recipient_iban: str,
        reason: str,
    ) -> dict:
        """Orchestrate a payment with full PSD2 compliance."""
        
        payment_id = generate_payment_id()
        
        # Step 1: Validate the request
        self.audit.log_step(payment_id, PaymentStep.VALIDATE, {
            "customer": customer_id,
            "amount": amount,
            "recipient": recipient_iban,
        })
        
        # Step 2: Verify consent (this is CRITICAL)
        if not self.consent.verify_consent_before_action(
            customer_id, 
            "initiate_payment"
        ):
            self.audit.log_step(
                payment_id, 
                PaymentStep.CHECK_CONSENT, 
                {"status": "FAILED", "reason": "no consent"}
            )
            return {
                "status": "rejected",
                "reason": "Customer has not granted permission to initiate payments",
                "payment_id": payment_id,
            }
        
        self.audit.log_step(payment_id, PaymentStep.CHECK_CONSENT, {"status": "OK"})
        
        # Step 3: Ask bank to initiate
        self.audit.log_step(payment_id, PaymentStep.INITIATE_WITH_BANK)
        bank_response = call_bank_api(
            endpoint="/payments",
            method="POST",
            body={
                "amount": amount,
                "debtor_iban": get_customer_account(customer_id),
                "creditor_iban": recipient_iban,
                "remittance_info": reason,
            }
        )
        
        if bank_response.status != "ACSP":  # Accepted and Settled or Pending
            self.audit.log_step(
                payment_id,
                PaymentStep.INITIATE_WITH_BANK,
                {"status": "FAILED", "bank_error": bank_response.error}
            )
            return {
                "status": "rejected",
                "reason": f"Bank rejected: {bank_response.error}",
                "payment_id": payment_id,
            }
        
        # Step 4: SCA (Strong Customer Authentication) — PSD2 requires this
        self.audit.log_step(payment_id, PaymentStep.GET_CUSTOMER_CONFIRMATION)
        self.notify.request_sca(
            customer_id,
            payment_id,
            amount,
            recipient_iban,
        )
        # Customer will approve via their bank's app or SMS
        # Webhook callback updates the payment status
        
        return {
            "status": "pending_customer_confirmation",
            "payment_id": payment_id,
            "next_step": "Wait for SCA completion",
        }
    
    def confirm_payment_after_sca(
        self,
        payment_id: str,
        sca_token: str,
    ) -> dict:
        """SCA confirmed by customer. Execute the payment."""
        payment = load_payment(payment_id)
        
        self.audit.log_step(payment_id, PaymentStep.EXECUTE, {
            "sca_token": sca_token
        })
        
        # Execute with SCA proof
        bank_response = call_bank_api(
            endpoint=f"/payments/{payment_id}/confirmation",
            method="POST",
            body={"sca_token": sca_token},
        )
        
        if bank_response.status == "ACCC":  # Accepted and Complete
            self.audit.log_step(payment_id, PaymentStep.CONFIRM, {"status": "SUCCESS"})
            return {
                "status": "executed",
                "payment_id": payment_id,
                "bank_reference": bank_response.transaction_id,
            }
        
        self.audit.log_step(payment_id, PaymentStep.CONFIRM, {"status": "FAILED"})
        return {
            "status": "failed",
            "payment_id": payment_id,
            "reason": bank_response.error,
        }
```

**Why this works:** Each step is logged and auditable. If a payment fails mid-way, you know *exactly* where and why.

---

### **Agent 3: Notification Agent**

**Responsibility:** Keep the customer informed of every decision that affects them.

```python
class NotificationAgent:
    def request_sca(
        self,
        customer_id: str,
        payment_id: str,
        amount: float,
        recipient_iban: str,
    ):
        """Send SCA challenge: 'Confirm: Pay €50 to DE89370400440532013000'"""
        message = f"""
        🔐 Confirm Payment
        Amount: €{amount}
        To: {mask_iban(recipient_iban)}
        
        Approve in your bank app or reply with code sent to your phone.
        """
        self.send_sms(customer_id, message)
        self.send_in_app_notification(customer_id, message)
        self.log_notification(payment_id, "sca_challenge_sent")

    def notify_consent_expiring(
        self,
        customer_id: str,
        scope: str,
        days_until_expiry: int,
    ):
        """Proactive: 'Your access to payments expires in 7 days. Renew?'"""
        message = f"Your permission to {scope} expires in {days_until_expiry} days."
        self.send_email(customer_id, message)
        self.log_notification(customer_id, "consent_expiry_warning")

    def notify_suspicious_activity(
        self,
        customer_id: str,
        payment_id: str,
        reason: str,
    ):
        """Fraud detection: 'Payment blocked: recipient is new'"""
        message = f"Payment {payment_id} was blocked: {reason}. Approve to continue."
        self.send_sms(customer_id, message)
        self.log_notification(payment_id, "suspicious_activity_alert")
```

---

### **Agent 4: Audit Trail Agent**

**Responsibility:** Prove to regulators that every payment followed PSD2 rules.

```python
class AuditTrailAgent:
    def log_step(
        self,
        payment_id: str,
        step: PaymentStep,
        details: dict,
    ):
        """Immutable record of every payment decision."""
        record = {
            "payment_id": payment_id,
            "step": step.value,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "hash": compute_hash(details),  # Tamper-proof
        }
        # Append to immutable log (e.g., Azure Append Blob)
        append_to_audit_log(record)

    def prove_compliance(self, payment_id: str) -> dict:
        """Generate a compliance report for regulators."""
        events = load_audit_trail(payment_id)
        return {
            "payment_id": payment_id,
            "consent_verified": self._check_step(events, PaymentStep.CHECK_CONSENT),
            "sca_completed": self._check_step(events, PaymentStep.GET_CUSTOMER_CONFIRMATION),
            "bank_confirmed": self._check_step(events, PaymentStep.CONFIRM),
            "timeline": [e["timestamp"] for e in events],
            "hash_chain_valid": self._verify_tamper_proof(events),
        }
```

---

## Azure Integration: PSD2-Ready Infrastructure

### **1. Azure Key Vault for Bank Credentials**

Each bank connection (connection string, API key) is stored securely:

```python
from azure.keyvault.secrets import SecretClient

vault = SecretClient(vault_url="https://bank-vault.vault.azure.net", ...)

# Each agent retrieves credentials on-demand
bank_api_key = vault.get_secret("deutsche-bank-api-key").value
```

### **2. Azure Service Bus for Payment Events**

Payment orchestrator publishes events; notification agent subscribes:

```python
from azure.servicebus import ServiceBusClient

bus = ServiceBusClient.from_connection_string(connection_string)
sender = bus.get_queue_sender("payment-events")

# Orchestrator publishes
sender.send_message({"payment_id": "...", "event": "sca_required"})

# Notification agent listens
receiver = bus.get_queue_receiver("payment-events")
for message in receiver:
    notify_customer(message.body)
```

### **3. Azure Cosmos DB for Audit Trail**

Append-only, globally distributed, compliance-ready:

```python
from azure.cosmos import CosmosClient

client = CosmosClient(endpoint, credential)
container = client.get_database_client("compliance").get_container_client("audit")

# Every step is immutable
container.create_item({
    "id": f"{payment_id}-{step_number}",
    "payment_id": payment_id,
    "step": "check_consent",
    "timestamp": datetime.now().isoformat(),
    "result": "approved",
    "_etag": "...",  # Cosmos versioning for tamper detection
})
```

---

## Production Checklist: Before You Go Live

- [ ] **Consent is checked before EVERY bank operation**
- [ ] **SCA (Strong Customer Authentication) is mandatory** for payments > €30 and account access
- [ ] **Audit trail is immutable** (hash-chain or append-only storage)
- [ ] **Notification agent keeps customer informed** at every step
- [ ] **Payment orchestrator has explicit steps**, not a monolithic function
- [ ] **Bank API errors are gracefully handled** (retry logic, fallback options)
- [ ] **Consent expiry is tracked** and proactively renewed
- [ ] **Customer can revoke consent instantly** (no batch jobs)
- [ ] **You can prove compliance to regulators** within 5 minutes

---

## My Takeaway

PSD2 feels like added regulatory burden, but it's actually a **clarity gift.** By splitting payment handling into agents with narrow, auditable responsibilities, you build systems that:

1. **Customers trust** — They can see what permission they gave, when it expires, and revoke it instantly
2. **Banks respect** — Clear audit trails prove you're not siphoning data
3. **Regulators can verify** — Every decision is logged with timestamps and consent proofs

The agent-driven architecture isn't a workaround for PSD2 — it's the natural way to build compliant, transparent, multi-party systems.

---

## Further Reading

- **PSD2 Official** — [Payment Services Directive 2](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32015L2366)
- **EBA Guidelines** — [Strong Customer Authentication (SCA)](https://www.eba.europa.eu/regulation-and-policy/payment-services-and-electronic-money/regulatory-technical-standards-on-sca-and-cmi)
- **Open Banking Standards** — [OASIS OpenAPI for PSD2](https://www.openapis.org/)
- **Microsoft Compliance** — [PSD2 on Azure](https://docs.microsoft.com/en-us/azure/compliance/regulatory/psd2)

---

**Tags:** #PSD2 #OpenBanking #FinTech #AgenticAI #Compliance #PaymentOrchestration #MAF #Azure #Python

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** Multi-agent payment orchestration systems
