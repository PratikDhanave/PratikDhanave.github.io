# FHIR R4 + HL7 v2 in Production Medical AI: Building Bodh

*How to architect medical AI systems that interoperate with legacy health systems while maintaining modern safety constraints.*

## Why Healthcare Needs Two Standards

**FHIR R4 (Fast Healthcare Interoperability Resources)**
- Modern, REST-based, JSON/XML
- Used by newer EHRs (Epic, Cerner 2020+)

**HL7 v2**
- Legacy standard (1989–present)
- Flat, pipe-delimited messages
- Used by 90% of hospitals globally

You need to support BOTH because your healthcare customers use both.

## Bodh: Medical AI Panel Architecture

Bodh is an open-source medical AI panel on Microsoft's MARA with:

- **7 role-specialized agents**: intake, supervisor, questioner, test_planner, cost_guardian, diagnostician, reasoning_verifier
- **FHIR R4 schemas** for EHR interoperability
- **HL7 v2 message parsing** for legacy system integration
- **Cost-aware diagnostic budgets** that agents enforce
- **SD-Bench evaluation metrics** for multi-turn diagnostic reasoning

## Cost-Aware Diagnostic Budgets

In healthcare, every test costs money. The cost_guardian agent enforces a budget:

```
Patient presents with cough
├─ Budget: $500
├─ Intake: fever, cough, shortness of breath
├─ Tests: Chest X-ray ($200), CBC ($50), Culture ($100)
├─ Cost guardian: "Budget allows all three. Proceed."
└─ Result: Pneumonia (confirmed by imaging + labs)
```

## HIPAA Compliance & Data Privacy

1. **Encryption in transit**: TLS 1.3
2. **Encryption at rest**: AES-256-GCM
3. **Audit logging**: Every data access logged
4. **Consent management**: Track which agents can access what
5. **Data residency**: Keep patient data in-country per regulations

---

**Bodh is open source: [github.com/c2siorg/bodh](https://github.com/c2siorg/bodh)**
