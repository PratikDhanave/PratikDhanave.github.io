---
title: "FHIR R4 + HL7 v2 in Production Medical AI: Building Bodh"
description: "Healthcare AI architecture guide: FHIR R4 and HL7 v2 interoperability, clinical data standards, medical AI compliance, and EHR integration patterns."
keywords: ["FHIR", "HL7", "healthcare AI", "medical AI", "clinical data", "EHR integration", "health information exchange", "medical standards"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
canonical: "https://pratikdhanave.github.io/articles/29-fhir-hl7-medical-ai/"
schema: {
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "FHIR R4 + HL7 v2 in Production Medical AI: Building Bodh",
  "description": "Healthcare AI system design with FHIR R4 and HL7 v2 interoperability standards",
  "author": {"@type": "Person", "name": "Pratik Dhanave", "url": "https://pratikdhanave.github.io"},
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
  "image": "https://pratikdhanave.github.io/og-default.png",
  "keywords": ["FHIR", "HL7", "healthcare AI", "medical standards"],
  "articleSection": "Healthcare & Medical AI"
}
---

# FHIR R4 + HL7 v2 in Production Medical AI: Building Bodh

*How to architect medical AI systems that interoperate with legacy health systems while maintaining modern safety constraints.*

## Why Healthcare Needs Two Standards

## Key FHIR R4 Resources

1. **Patient** - Demographic and personal information
2. **Observation** - Clinical measurements and test results
3. **Condition** - Diagnoses and clinical problems
4. **Medication** - Drug information and prescriptions
5. **CarePlan** - Care coordination and treatment plans

**FHIR R4 (Fast Healthcare Interoperability Resources)**
- Modern, REST-based, JSON/XML
- Used by newer EHRs (Epic, Cerner 2020+)

**HL7 v2**
- Legacy standard (1989–present)
- Flat, pipe-delimited messages
- Used by 90% of hospitals globally

You need to support BOTH because your healthcare customers use both.

## Bodh: Medical AI Panel Architecture

Bodh is an open-source medical AI panel on the Microsoft Agent Framework with:

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
