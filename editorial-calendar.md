# Editorial calendar — 400+ post ideas

> A year-plus catalog of post ideas grounded in real work: Genie,
> Bodh, the Tata Group BigQuery FinOps engagement (57% cost
> reduction), Bancnet (multi-jurisdiction Middle East open banking),
> Brownlow (AFL voting on Cloud Run), HarbourBridge (Spanner
> Migration Tool), Globe (30K+ TPS telecom/FinTech), Picnic (1M+
> users), the P2P lender, the Kinetic India voice assistant, the
> open-source Gocloud / CX work, and the GSoC / Google Cloud Next
> trajectory.
>
> Every idea ties to a specific project, file path, regulator
> framework, or production lesson — no generic "10 Go tips" filler.
> Pick any one and ask Claude to draft it; the source anchor tells
> Claude where to start.
>
> **17 series · ~400 posts · cadence options below.**

---

## How to use this calendar

- **Daily (5/week)** → 80 weeks ≈ 1.5 years of one-post-a-weekday.
- **Three a week** → 130 weeks ≈ 2.5 years.
- **Two a week** → 200 weeks ≈ ~4 years (this is the realistic ship-pace for long-form, code-anchored posts).
- **Burst-mode** → ship a whole series in a fortnight (already done with the 16-post May 2026 Genie wave).

Series are independent; you can interleave or run them in parallel.

---

## Series 1 — Genie deep dives (30 posts)

Every package, agent, and security primitive in `c2siorg/genie`. Each post cites a file path; readers can grep along.

1. Inside Genie's bus — the in-memory pub/sub that started life as 200 lines of Go
2. From Message to Verdict — the protocol package as the only stable contract
3. The Orchestrator hook surface — `OnPolicyDeny`, `OnAgentError`, and why we expose nothing else
4. `pkg/agent.Tier` — Sketch → Prototype → Beta → Production as a dispatch gate
5. `pkg/agent.RiskClass` — what "blast radius" actually means in code
6. `pkg/governance.RBACPolicy` — bus-layer authorisation that survives JSON round-trips
7. `pkg/governance.TenantPolicy` — the bus half of tenant isolation defence in depth
8. `pkg/storage/postgres` RLS migration — the DB half of the same defence
9. The `__admin__` sentinel — the one legitimate cross-tenant key, why it's invisible to the UI
10. `pkg/auth.Issuer` — why we kept HS256 stdlib instead of pulling a JWT library
11. `pkg/auth/tokenexchange` — RFC 8693 dual-identity tokens for agent → MCP → upstream chains
12. `pkg/auth/elevation` — time-bound privileged access (PCSE §1.4 analog)
13. `pkg/auth/webauthn` — passkeys in 200 lines of stdlib Go
14. `pkg/auth/oauth2` + `oauth_device` — when each flow is actually the right one
15. `pkg/policy/dsl` — the tiny CEL-style DSL the risk team owns
16. `pkg/safety` plugin chain — generator + critic in three lines of YAML
17. `pkg/sovereignty.ProviderRegistry` — classification → provider allowlist
18. `pkg/llm` wrappers — deadline + circuit + budget + router stacked at boot
19. `pkg/crypto` envelope encryption — per-document DEK, KMS-pluggable KEK
20. `pkg/compliance.AuditLog` — hash chain in 100 lines; verify in 30
21. `pkg/incidents` — Annexure VI as a Go struct
22. `pkg/observability` + `bq` warehouse sink — OTel today, BigQuery tomorrow
23. `agents/financial_supervisor` — the coordinator pattern in production
24. `agents/kyc_orchestrator` — deterministic core, LLM narration
25. `agents/payment_orchestrator` — NPCI rail chooser with HITL above ₹2L
26. `agents/cyber_guardian` — session anomaly detection with Haversine
27. `agents/fomc_research` — RBI MPC tracker
28. `agents/sme_loan_workflow` — multi-stage HITL with saga rollback
29. The Genie test pyramid — 100+ packages, security-envelope integration, agent-registry guardrails
30. Six months of Genie — what survived, what we rewrote, what we deleted

---

## Series 2 — Bodh deep dives (30 posts)

Medical AI on the Microsoft Agent Framework, FHIR R4, HL7 v2 — from the `PratikDhanave/bodh` repo.

1. Bodh — what MAI-DxO + SD-Bench taught us about diagnostic agents
2. The five-role panel — intake, questioner, test_planner, cost_guardian, diagnostician, reasoning_verifier
3. Cost-aware diagnostic budgets — the `cost_guardian` agent
4. FHIR R4 in Go — resource parsing without the big libraries
5. HL7 v2 segments that still matter in 2026
6. The intake agent — taking a chief complaint without leading the witness
7. The questioner — bounded ReAct in a clinical loop
8. test_planner — ranking labs by Bayesian information gain per dollar
9. The diagnostician — pulling structured differentials out of free text
10. reasoning_verifier — the critic pattern, applied to medical claims
11. Why deterministic ranking beats LLM scoring for triage
12. PHI redaction — `pkg/governance/pii.go` for US clinical data
13. The audit log row for a clinical decision — what survives forensic review
14. Postgres RLS for clinical records — patient_id as the tenant
15. Information blocking and the Cures Act — what your code has to do
16. Right of access vs minimum necessary — encoding both in the schema
17. De-identification for research — Safe Harbor vs Expert Determination in Go
18. Break-glass access — a clinical PAM pattern in `auth/elevation` shape
19. Drug-drug interaction checks — when LLMs are the wrong tool
20. A diagnostic critic test corpus — 200 cases that don't change
21. Latency budgets in clinical AI — when 30s is too slow
22. Fallback to a deterministic differential — Bodh's BCP story
23. SD-Bench numbers — moving 42.9% → 85.7% by changing two files
24. Confidence calibration — Brier score on a diagnostic panel
25. Hallucination as a clinical safety event — the incident shape we settled on
26. A medical AI bill of materials — what's in the model card
27. Multi-language clinical AI — Bhashini hooks for Indian-language intake
28. EHR integration shapes — Epic vs Cerner vs Athena, what each expects
29. The HITL gate — when does the panel hand back to a human
30. Twelve clinical cases Bodh got wrong, and what we changed

---

## Series 3 — RBI FREE-AI in code (30 posts)

Every one of the 26 recommendations, anchored to a file path in Genie. A few get two posts because they're load-bearing.

1. Reading the FREE-AI report as a Go engineer
2. Rec 2 — AI Innovation Sandbox: what a real sandbox stack looks like
3. Rec 4 — Indigenous models: Ollama-first deployment patterns
4. Rec 5 — Capacity building: the GSoC pipeline for AI-native engineering
5. Rec 6 — Adaptive policies: a CEL-style DSL the risk team can author
6. Rec 8 — Graded liability in `pkg/incidents/grading.go`
7. Rec 14 — Board-approved policy YAML: the file the risk team owns
8. Rec 14 (continued) — what a Sutra is and how it shows up in policy evaluation
9. Rec 15 — Data lifecycle: envelope encryption + RLS + retention
10. Rec 15 (continued) — Postgres RLS as the DB half of tenant isolation
11. Rec 16 — Autonomous system controls: deadline + circuit + budget
12. Rec 17 — Product approval: the four-tier promotion model
13. Rec 18 — Consumer protection: the SSE ai_disclosure event
14. Rec 19 — Cybersecurity, the application-layer perimeter
15. Rec 19 (continued) — `cyber_guardian` and impossible-travel scoring
16. Rec 20 — Red teaming in CI: `cmd/red-team/` against the live policy
17. Rec 21 — BCP for AI: fallback agents and forced-failure drills
18. Rec 22 — Annexure VI as a structured incident record
19. Rec 22 (continued) — Dual-identity tokens for after-the-fact attribution
20. Rec 23 — AI inventory: the `/v1/ai-inventory` endpoint and what it surfaces
21. Rec 24 — AI audit framework: hash chain + the verifier walk
22. Rec 25 — Disclosures: per-output Disclaimer field, public `/v1/disclosures`
23. Rec 26 — Toolkit reuse: `pkg/policy/dsl` for the risk team
24. Reading Annexure V — board policy template line by line
25. Reading Annexure VI — incident form fields mapped to Go struct fields
26. The FREE-AI 7 Sutras as runtime principles, not slogans
27. KYC under FREE-AI vs under the RBI Master Direction
28. Bancassurance + FREE-AI — what the IRDAI overlay adds
29. NPCI rails under FREE-AI — UPI 2.0, IMPS, NEFT, RTGS routing
30. Twelve months of FREE-AI implementation — what changed, what didn't

---

## Series 4 — GCP PCSE field guide (30 posts)

Every Professional Cloud Security Engineer bullet, with an application-layer Genie analog or honest gap.

1. PCSE blueprint as a code reading list
2. §1.1 Cloud Identity — when Genie is the IdP, when it isn't
3. §1.1 Workforce Identity Federation — what it gives you that JWT doesn't
4. §1.2 Service accounts vs SPIFFE workload identity in Genie
5. §1.2 Short-lived credentials — JWT TTL + RFC 8693 cache
6. §1.2 Service account impersonation == RFC 8693 token exchange
7. §1.3 SAML vs OAuth — when banks insist on SAML
8. §1.3 Passkeys (WebAuthn) as 2-step verification
9. §1.4 IAM deny policies → `CompositePolicy` deny-on-first
10. §1.4 Privileged Access Manager → `pkg/auth/elevation` (the PAM analog)
11. §1.4 Separation of duties — N-eyes approvals in code
12. §1.5 Resource hierarchy — flat tenancy today, org_id roadmap
13. §2.1 Layer-7 inspection — prompt injection + PII + classification policies
14. §2.1 Rate limiting at the application layer — `mid.RateLimit`
15. §2.2 VPC Service Controls analog — `sovereignty.ProviderRegistry`
16. §3.1 PII detection and redaction in Go — the Aadhaar / PAN regex set
17. §3.1 Pseudonymisation — `affected_id` in `pkg/incidents`
18. §3.1 Secret Manager — KEK resolver as the interface
19. §3.2 CMEK vs EKM — what the `KMSClient` interface gives you
20. §3.2 KEK rotation in production — per-row `kek_id` and the lazy rewrap job
21. §3.2 Object lifecycle policies — `retention.go` and the 6h purge job
22. §3.3 Securing AI workloads — the eleven-layer envelope
23. §4.1 Drift detection at the application layer — security envelope tests
24. §4.1 Binary Authorization analog — tier promotion as image signing
25. §4.2 Logging strategy — OTel spans + Annexure VI + hash chain
26. §4.2 Secure log access — admin-only audit reader
27. §4.2 Log export to BigQuery — `pkg/observability/bq` async dispatcher
28. §4.2 Security Command Center analog — admin dashboard + AI inventory
29. §5.1 Shared responsibility — what Genie owns and what it explicitly doesn't
30. §5.1 Compliance mapping — the FREE-AI ↔ PCSE cross-walk

---

## Series 5 — Compliance trilogy: HIPAA / Cures Act / AIGP (25 posts)

For the medical-AI side (Bodh + clinical readers).

1. HIPAA as Go interfaces — what changed in 2026 enforcement
2. Right of access in 30 days — a worked implementation
3. The HIPAA audit log — what to log, what never to
4. PHI under §164.312(b) — the audit trail you'd want a regulator to see
5. Minimum necessary — encoding it as RLS plus column-level deny
6. Break-glass access — the clinical analog of `pkg/auth/elevation`
7. De-identification: Safe Harbor vs Expert Determination
8. Business Associate Agreements in a multi-model stack
9. Subcontractor risk — the model-card chain
10. The 21st Century Cures Act §170.401 — information blocking in code
11. USCDI v3 — what fields your API must expose
12. SMART on FHIR launch context in Go
13. AIGP body of knowledge — a reading map for engineers
14. Privacy by design — what it actually means in a Go service
15. Data Protection Impact Assessments — the docs you generate from code
16. GDPR right to erasure — Postgres + audit chain reconciliation
17. India's DPDP Act — what FREE-AI assumes about it
18. Brazil's LGPD — comparison to GDPR for an exporter
19. Saudi Arabia's PDPL — practical clauses for an open-banking deployment
20. UAE ADGM DPR + DIFC DP Law — Bancnet's regional split
21. PIPEDA in Canada — for medical AI exports
22. APPI in Japan — short-lived cross-border deployment shape
23. ISO/IEC 42001 — AI management system in 30 minutes
24. ISO/IEC 23894 — AI risk management mapped to FREE-AI
25. NIST AI RMF 1.0 — what to lift, what to localise

---

## Series 6 — Identity, auth, and zero-trust in Go (25 posts)

OAuth, OIDC, JWT, passkeys, mTLS, SPIFFE — the auth stack you actually need.

1. JWT in 150 lines of Go — the case against pulling a library
2. HS256 vs RS256 — pick the wrong one and explain why
3. OAuth 2.1 + PKCE for a single-page app
4. OAuth Device Flow for voice assistants and kiosks
5. WebAuthn passkeys with `crypto/ed25519`
6. Email-link sign-in done right
7. Magic-link drift — when these flows break
8. RFC 8693 token exchange explained with one nurse and three services
9. Nested actor chains — N-hop attribution in audit logs
10. SAML 2.0 verifier in Go — XML signing without losing your mind
11. Workforce Identity Federation against Okta / Azure AD
12. Service account impersonation — the right metaphor in 2026
13. SPIFFE/SPIRE basics — workload identity at deploy time
14. mTLS at the proxy — Envoy + SPIRE-issued SVIDs
15. Zero-trust without buying a vendor product
16. OAuth 2.0 + Open Banking PSD2 — the European overlay
17. UPI authentication — what the spec demands
18. Risk-based step-up auth — the IDV + behaviour combo
19. Session anomaly detection — Haversine + credential stuffing density
20. Cookie vs token storage — what survives an XSS
21. JWT pitfalls — `none` algorithm, RSA confusion, audience leakage
22. Rotating JWT signing keys — zero-downtime in 5 lines
23. Webhook signing — HMAC-SHA256 with a replay window
24. CSRF in 2026 — what SameSite still doesn't catch
25. The audit log row for an auth event — what survives a compromise probe

---

## Series 7 — Postgres for production AI (25 posts)

From RLS to pgvector to AlloyDB AI to the Spanner Migration Tool experience.

1. Postgres Row-Level Security — defence in depth for tenant isolation
2. `SET LOCAL` vs `SET` — why the wrong choice leaks across requests
3. `set_config(name, value, true)` — parameterising the GUC safely
4. FORCE ROW LEVEL SECURITY — the line a regulator will ask about
5. The `__admin__` sentinel — when cross-tenant reads are legitimate
6. pgvector in production — index types, distance metrics, recall
7. Hybrid search in Postgres — BM25 alongside vector
8. AlloyDB AI — what it gives you over vanilla pgvector
9. AlloyDB AI for RAG at Bancnet — 37% latency reduction story
10. Reciprocal Rank Fusion in pgvector queries
11. Connection pools and RLS — pitfall + fix
12. JSONB for agent state — when it pays, when it doesn't
13. Partial indexes for tenant-heavy tables
14. Time-bucketed partitioning for audit logs
15. Logical replication for tenant migrations
16. CDC with pglogical — what changed since 2023
17. Spanner vs Postgres for multi-region writes
18. Migrating to Spanner — the HarbourBridge schema redesign playbook
19. Spanner write hotspots — PK design that doesn't kill throughput 40-60%
20. Spanner interleaved tables — when and when not
21. Backups and PITR at the application layer
22. Postgres + KMS — encrypting columns the agents can't read
23. Postgres extensions in production — what we ban and why
24. Query plan drift on a vector index — how to spot it
25. Twelve outages caused by Postgres tuning we shouldn't have done

---

## Series 8 — LLM Ops in Go (25 posts)

The wrappers that make LLM calls survive contact with production.

1. The deadline wrapper — context cancellation that actually fires
2. Circuit breakers for LLM providers — when to trip and how to recover
3. Per-principal token budget — the wrapper that protects payroll
4. Cost in micros — the unit every LLM provider should expose
5. Latency buckets — `genie.llm.latency_ms` histograms that matter
6. Multi-provider routing — Vertex, Bedrock, Anthropic, Ollama
7. Failover order — when "use the cheaper one first" is wrong
8. Prompt cache TTL — when to invalidate
9. Model swap drift — what changes when you upgrade the model
10. LLM-as-Judge for eval — `agents/llm_auditor` patterns
11. Output schema enforcement — JSON schema as a contract
12. Streaming + SSE — the bytes-not-tokens question
13. WebSocket vs SSE for agent output
14. Function calling vs tool use vs MCP — three names for the same idea
15. MCP server in Go — a worked example
16. MCP client — the policy you wrap around every tool call
17. Bedrock Agents vs ADK vs the Microsoft Agent Framework — when to pick which
18. Vertex AI Agent Engine — what it gives you that you'd otherwise build
19. Fine-tuning OSS models on AWS Bedrock
20. Ollama on-prem — production patterns
21. Multi-tenant LLM cost attribution
22. Per-request safety scoring — Model Armor / Lakera / Bedrock Guardrails
23. Output watermarking — what's actually possible in 2026
24. Detecting prompt injection in tool arguments
25. The LLM call's audit row — what a regulator will ask for

---

## Series 9 — RAG, GraphRAG, and retrieval (30 posts)

Everything from "vector + BM25 + RRF" to BigQuery Knowledge Graph.

1. Retrieval is the bottleneck — why and what to do about it
2. Hybrid search — vector + BM25 + RRF as the new baseline
3. Reranking — bi-encoder vs cross-encoder, latency vs precision
4. HyDE — generating hypothetical answers to improve retrieval
5. Self-RAG — when to retrieve, when to skip
6. CRAG (corrective RAG) — fixing wrong retrieval at runtime
7. GraphRAG basics — entities, communities, summaries
8. BigQuery Knowledge Graph — when SQL beats vector
9. Citations as a first-class contract
10. Chunking strategies — fixed, semantic, recursive, agentic
11. Embedding model choice — closed vs open, when each wins
12. Embedding rotation — the silent break
13. Dense vs sparse — when SPLADE beats dense vectors
14. Negative sampling for retrieval training
15. Query expansion — synonyms, acronyms, multi-language
16. Multilingual RAG for India — Bhashini + cross-lingual retrieval
17. Time-aware retrieval — when "recent" matters
18. Multimodal RAG — image + text + table extraction
19. Tabular RAG — PDFs with tables, the format that breaks everything
20. Long-context vs RAG — when context windows make retrieval optional
21. RAG evaluation — Ragas, ARES, custom
22. Retrieval fairness — bias in what gets surfaced
23. RAG over your own org — Slack + Confluence + Jira + Notion
24. Personalised RAG — per-user vector spaces
25. Streaming RAG — incremental citations
26. RAG cost analysis — token economics by stage
27. Vector DB choice — pgvector vs Pinecone vs Vertex Vector Search
28. RAG against AlloyDB AI — the Bancnet stack
29. RAG cache invalidation — the hard part
30. Twelve RAG failures, ranked

---

## Series 10 — Multi-agent patterns and orchestration (30 posts)

Every pattern from the Google Cloud catalog, the ADK, MCP, A2A, the Microsoft Agent Framework.

1. The 12 Google Cloud agent design patterns mapped to Genie's agents
2. Single-agent vs multi-agent — pick the lower one first
3. Sequential — the easy pattern that scales to about a dozen steps
4. Parallel — when fan-out actually saves time
5. Loop with explicit termination — the pattern that bounds Reflexion
6. Generator + Critic — the formal review-and-critique pair
7. Iterative refinement — bounded loops with quality thresholds
8. Coordinator — the supervisor pattern in `agents/financial_supervisor`
9. Hierarchical task decomposition — `agents/sme_loan_workflow`
10. Swarm — why we don't ship it in regulated finance
11. ReAct in production — the wrapper that actually catches loops
12. Reflexion — a budget-bound reflection loop
13. Tree of Thoughts in Go — when it pays
14. Step-Back prompting — generate a higher-level question first
15. Chain-of-Verification — the critic pattern, structured
16. HITL gates — saga + checkpoint + approval channel
17. Agent-to-Agent (A2A) — the spec and the Go client
18. MCP servers vs tool calling — when each makes sense
19. Skill manifests — progressive disclosure for supervisors
20. Agent registry as the routing fabric
21. Dispatching by capability vs by id
22. Fallback wiring — the orchestrator hook + the BCP drill
23. Cross-agent observability — distributed traces that survive bus hops
24. The bus as the only audit point
25. Workflow saga — the rollback pattern in `pkg/workflow`
26. DAG vs saga vs state machine — pick by failure semantics
27. Cost-aware agent dispatch
28. Latency-aware agent dispatch
29. Tier promotion as the production gate
30. Twelve months of multi-agent in production — what survived

---

## Series 11 — BigQuery FinOps and data platform (25 posts)

The Tata Group engagement — 57% data warehouse cost reduction.

1. BigQuery cost levers — slot reservation, on-demand, capacity transitions
2. The MERGE pattern that costs ten times more than INSERT-then-UPDATE
3. Anti-patterns Optimus detects — full scans, missing partition filters, inefficient joins
4. The 57% number — how we got there at Tata Group
5. Slot-based vs on-demand — when each wins
6. Storage tiering — physical vs logical bytes
7. Materialized views — when they pay, when they don't
8. Authorised views and column-level security
9. BigQuery ML for fast baselines
10. Vector Search in BigQuery
11. BigQuery Knowledge Graph for entity resolution
12. Streaming inserts vs Storage Write API
13. Reservation autoscaling — what no one says
14. Edition transitions — Standard vs Enterprise vs Enterprise Plus
15. Cost attribution by labels — multi-tenant accounting
16. Lineage with Dataplex
17. Detecting cardinality drift in BI queries
18. Saving 30% on dashboards — pre-aggregation patterns
19. BigQuery + Looker — the cache layer most teams miss
20. INFORMATION_SCHEMA queries that pay for themselves
21. The query optimizer — when to override its choices
22. Time-travel + snapshots — backup without copies
23. Data clean rooms — joining across orgs without leaking
24. Productising a FinOps engagement — the Searce playbook
25. Twelve cost spikes and what triggered them

---

## Series 12 — Cloud-native production reliability (25 posts)

From Picnic (1M+ users), Globe (30K TPS), Brownlow (10K concurrent on Cloud Run).

1. Cloud Run for live-broadcast traffic — Brownlow's autoscale story
2. The two-knob load test — concurrency × requests per instance
3. GKE for stateful AI workloads — the patterns we ship
4. Idempotency keys done right
5. Dead-letter queues — when to retry, when to drop
6. Exponential backoff with jitter — `golang.org/x/time/rate` patterns
7. Circuit breakers in Go — gobreaker vs handroll
8. Saga rollback when half the steps succeeded
9. State-based duplicate prevention in payment ledgers
10. Outbox pattern for Kafka producers
11. Kafka exactly-once — the config you actually need
12. Pub/Sub ordering keys — when ordering costs throughput
13. Redis as a session store at 30K TPS
14. PgBouncer — transaction vs session mode, why it matters
15. SLO design — what we promised in the Picnic 47% latency win
16. Error budget burn rate — alerts that wake you for the right reasons
17. Cardinality control on Prometheus
18. OTel collector pipelines — what to drop at the edge
19. Tempo + Grafana — distributed tracing on a budget
20. Chaos engineering for agents — the BCP drill harness
21. Game days — what we ran at Searce
22. Postmortem template — the parts most teams skip
23. Runbook structure — section headers that actually get used
24. Capacity planning for live events — Brownlow lessons
25. Twelve production incidents, walked through

---

## Series 13 — Multi-cloud, migration, infra (20 posts)

AWS, Azure, GCP — Spanner Migration Tool, Bloom (SOC 2 + ISO 27001), Bancnet (UAE/Saudi).

1. The unified-cloud-API question — what Gocloud got right
2. When to multi-cloud, when to actively avoid it
3. Spanner Migration Tool — the contributor's reading map
4. CDC for minimal-downtime migration — Datastream + Pub/Sub + Dataflow
5. Schema redesign for distributed DBs — PK and interleaving
6. Bloom — Terraform-driven secure cloud provisioning for banks
7. SOC 2 controls as Terraform modules
8. ISO 27001 — what code can prove, what it can't
9. Cross-cloud identity — federation patterns that work
10. Workload Identity Federation Azure → GCP for a real migration
11. Cross-cloud secrets — Vault as the abstraction
12. AWS Bedrock + Vertex AI in the same agent stack
13. Choosing between SageMaker and Vertex AI for fine-tuning
14. Networking for cross-cloud — VPN vs private interconnect
15. Egress costs — the gotcha that kills cloud-arbitrage plans
16. Data residency in the Gulf — UAE ADGM, DIFC, Saudi SAMA
17. Bancnet's split — what runs where and why
18. India's RBI data localisation — what it really requires
19. The CISO's question every migration project gets
20. Migration retrospectives — the three things we'd do differently

---

## Series 14 — Domain vertical deep dives (35 posts)

Specific vertical patterns from the projects in your portfolio.

**Finance (12)**

1. KYC under RBI Master Direction — PAN check-digit + Aadhaar offline + DigiLocker
2. AML / sanctions screening — the lists, the cadence, the audit
3. The double-entry ledger in Go — invariants that protect you
4. Maker-checker RBAC — encoding the four-eyes rule
5. Real-time fraud detection in a P2P lender
6. UPI integration — the spec quirks no one mentions
7. IMPS routing and reversal flows
8. NEFT batch settlement — when it's the right rail
9. RTGS for ≥ ₹2 lakh — the HITL gate
10. Credit bureau integration — three bureaus, three formats
11. Payment gateway reconciliation — the silent bugs
12. CRR / SLR awareness in an AI-aware treasury

**Insurance & bancassurance (6)**

13. Auto insurance claim adjudication — deterministic core, LLM narration
14. Health pre-auth — IRDAI + claim portal patterns
15. Motor IDV calculation in Go
16. PED disclosures — what the model sees and doesn't
17. Insurance fraud rings — graph analytics over claims
18. The claim_adjudicator agent's decision tree

**Open banking & FinTech (6)**

19. UAE ADGM open banking — Bancnet patterns
20. Saudi SAMA open banking — what differs from EU PSD2
21. Account aggregator framework (India) — the FIU/FIP role split
22. Consent management — the missing UX in most implementations
23. SCA (Strong Customer Authentication) flows
24. PCI-DSS for a 30K TPS pipeline (Globe's lessons)

**Voice & conversational (4)**

25. Voice AI for two-wheelers (Kinetic India) — multi-language patterns
26. ElevenLabs in production — latency, voice cloning ethics, cost
27. Conversational interrupt handling — the bit that breaks demos
28. Voice-to-tool dispatch — when "book service" actually books

**Medical (4)**

29. FHIR R4 patterns we actually use in Bodh
30. HL7 v2 segments mapped to FHIR resources
31. ICD-10 vs SNOMED CT — picking the coding for your use case
32. Drug-drug interaction APIs — RxNav vs FDB

**Civic / Sports (3)**

33. Brownlow — zero-trust voting under 10K concurrent users
34. Audit logging for vote integrity
35. Live-broadcast load patterns — the autoscale story

---

## Series 15 — Open source, mentorship, career (15 posts)

The narrative side — GSoC, Google Cloud Next, mentoring 40+ engineers.

1. Speaking at Google Cloud Next — the monolith-to-microservices talk
2. Slides as a contract — what to cut from a 30-minute Cloud Next slot
3. GSoC contributor → mentor in two years
4. Mentoring 10+ GSoC students — what works
5. The intern's first PR — code review patterns
6. Mentoring 40+ engineers across four internship cohorts
7. The Spanner Migration Tool — being a core contributor in OSS
8. Maintainer hygiene — what saves your evenings
9. Productising a client engagement — the Tata FinOps → Searce service playbook
10. Setting architecture standards for 15+ enterprise clients
11. Building a remote-first team of 4 — Picnic lessons
12. P1 incidents — being the technical SPOC
13. The interview I prepare for — Senior / Staff / Cloud Architect
14. Open source as portfolio — what recruiters actually read
15. AI dev tools (Cursor, Claude Code, Copilot) — what changes in a senior workflow

---

## Series 16 — Go language and runtime, the deep cuts (25 posts)

For the Go audience that wants language-level depth.

1. `embed.FS` as a deployment unit — config, prompts, UI assets
2. `GOMEMLIMIT` and the soft GC pacing change
3. `context.Context` patterns that survive deadline cascades
4. The race detector in CI — what every senior Go engineer ships
5. `pprof` under an admin-only JWT gate
6. `sync.Pool` for short-lived buffers — when it actually pays
7. `slog` migration — replacing five logging libraries with stdlib
8. Generics for repository code — when they finally pay
9. `errors.Join` and structured error chains
10. `iter.Seq` — the pull iterator pattern in Go 1.23+
11. `for range over int` — small ergonomic win that changes test setup
12. Workspace mode for multi-module repos
13. Build tags for cloud-target variants
14. CGO budget — when to break the stdlib-only rule
15. Goroutine leaks — `goleak` in test setup
16. `errgroup` patterns for parallel agent dispatch
17. Channel patterns I regret
18. The buffered-channel sizing question
19. `sync.Map` vs mutex+map — when each wins
20. JSON encoding in hot paths — `json.RawMessage`, `bytes.Buffer` reuse
21. Reflection — when to reach for it, when to refactor
22. Comparable types in 1.20+ — design for hashable keys
23. `testing/synctest` for time-based tests
24. Benchmarks that don't lie — `b.ReportAllocs()`, `b.Loop()`
25. Twelve Go idioms I changed my mind about

---

## Series 17 — Standalone / commentary pieces (15 posts)

The opinion side. Lower frequency, higher stakes per piece.

1. The case for boring stack choices in regulated AI
2. Why Go for production agentic AI (and when it's the wrong call)
3. Default-to-Prototype as a culture, not just a flag
4. The board policy is not a slide — it's a YAML file
5. Audit logs as the API of record
6. "Defence in depth" without the fluff
7. Single-page CV vs blog — pick one to update first
8. The Searce playbook — productising bespoke work
9. India's AI moment — what an RBI rule actually changes
10. Sovereign AI is policy, not a slide
11. The recruiter test — what your repo says before the interview
12. Speaking at conferences vs publishing — pick a cycle
13. Open-source maintenance as career insurance
14. The cost of a bad SLO
15. Twelve months of writing — what worked, what didn't, what I'd cut

---

## Quick-pick lists

### Top 10 to write next (highest leverage for a Senior / Staff search)

1. The FREE-AI 26 recommendations as Genie file paths — series 3, post 1
2. PCSE blueprint as a code reading list — series 4, post 1
3. RFC 8693 token exchange explained with one nurse and three services — series 6, post 8
4. The 57% number — how we got there at Tata Group — series 11, post 4
5. Postgres Row-Level Security — defence in depth for tenant isolation — series 7, post 1
6. The board policy is not a slide — it's a YAML file — series 17, post 4
7. The eleven-layer envelope — defence in depth for agentic AI — already published
8. The 12 Google Cloud agent design patterns mapped to Genie's agents — series 10, post 1
9. Speaking at Google Cloud Next — the monolith-to-microservices talk — series 15, post 1
10. The recruiter test — what your repo says before the interview — series 17, post 11

### Top 10 evergreen reposts (for LinkedIn cadence)

Pick the punchiest 80-word excerpt from each of:
- Defence in depth — eleven-layer envelope
- Why Go for production agentic AI
- Annexure VI as a query
- The Sovereign AI is a policy piece
- The 57% BigQuery cost reduction story (after publishing)
- The PAM analog in Go
- The PCSE mapping
- The deterministic-KYC-LLM-just-talks piece
- The board-policy-as-YAML piece
- The N-eyes elevation pattern

### Three-month sample cadence (3 posts/week)

Weeks 1-2 — Series 4 (PCSE) posts 1-6
Weeks 3-4 — Series 3 (FREE-AI) posts 1-6
Weeks 5-6 — Series 11 (BigQuery FinOps) posts 1-6 (the highest-conversion topic given the Tata Group 57% cost reduction case)
Weeks 7-8 — Series 6 (Auth in Go) posts 1-6
Weeks 9-10 — Series 9 (RAG) posts 1-6
Weeks 11-12 — Series 10 (multi-agent patterns) posts 1-6

That's 36 posts in 12 weeks — leaving 330+ in the bank.

---

## Production notes

- **Source repo for code anchors.** Every Series 1-12 post should grep into `c2siorg/genie` or `PratikDhanave/bodh` and cite the file path; readers can verify.
- **Length target.** 800-1,800 words for technical deep dives; 400-800 for opinion / commentary; 2,500+ for the canonical references (already shipped: `ai-governance-security.md`, `gcp-pcse-mapping.md`).
- **Header style.** Always lead with the contract ("here's what's true after you read this") and end with "how to verify."
- **Code blocks.** Always include 5-30 lines of real Go from the linked file path — copy-paste, never invent.
- **Disclosure.** When a post draws on a paid client engagement (Tata Group, Bancnet, Brownlow, Globe, Picnic), describe the *pattern* without revealing customer data; the engagement is mentioned where it's already in your CV.
- **Image strategy.** None to start; the existing design is text-first and works without images. Add a `cover` field later if you want OG previews.
- **Cross-link discipline.** Every post should link forward to one related post in the same series and backward to one anchor in the docs (the canonical security reference, the FREE-AI map, the PCSE map).

---

## What to skip

Don't write:
- "10 Go tips for beginners" — out of voice
- "What is RAG?" — already a thousand of these, none anchor to working code
- "ChatGPT vs Claude vs Gemini" — opinion drift, no Genie connection
- Vendor-promotional pieces — your repo IS the demo
- Conference recap posts — link to the talk recording instead

---

*Last updated 2026-05-26 · 17 series · 400+ post ideas · ground-truth in code at `github.com/c2siorg/genie`, `github.com/PratikDhanave/bodh`.*
