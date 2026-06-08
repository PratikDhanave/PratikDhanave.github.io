#!/usr/bin/env python3
"""
build_blog.py — Convert markdown articles in blog/source/ into themed
HTML blog posts on PratikDhanave.github.io, plus regenerate the blog index.

This script is run from the site repo root. It expects the source markdown
files to live in blog/source/.

Design system aligned with the site's index.html:
  - Same CSS variables (light + dark mode)
  - System font stack
  - Sticky nav, max-width 980px, 24px gutter
  - Tag pill style
  - Code blocks with --code-bg background

The script:
  1. Reads each .md file in blog/source/ (skipping README.md and feed-posts.md)
  2. Extracts the title (H1) and subtitle (italic line under H1)
  3. Renders the markdown body to HTML via python-markdown
     with tables + fenced_code + sane_lists + toc extensions
  4. Wraps the HTML in the post template
  5. Writes to blog/posts/<slug>.html
  6. Builds blog/index.html listing all posts with title/excerpt/tags
  7. Leaves the root index.html for separate manual editing (Blog nav link)
"""

import math
import os
import re
import sys
import json as _json
import subprocess
import urllib.request
import urllib.error
from html import escape as _html_escape
from pathlib import Path
from datetime import datetime
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.sane_lists import SaneListExtension
from markdown.extensions.toc import TocExtension


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def calculate_read_time(html_content):
    """Estimate reading time from HTML content (avg 200 words/min)."""
    import re
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    # Count words
    words = len(text.split())
    # Estimate minutes (200 words per minute)
    minutes = max(1, round(words / 200))
    return minutes


def find_related_posts(current_slug, all_posts, current_tags, limit=3):
    """Find posts with tag overlap, excluding current post."""
    related = []
    for post in all_posts:
        if post["meta"]["slug"] == current_slug:
            continue
        # Calculate tag overlap
        overlap = len(set(post["meta"]["tags"]) & set(current_tags))
        if overlap > 0:
            related.append((overlap, post))

    # Sort by overlap (desc), then by date (desc), return top N
    related.sort(key=lambda x: (-x[0], -datetime.strptime(x[1]["meta"]["date"], "%Y-%m-%d").timestamp()))
    return [post for _, post in related[:limit]]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SITE_ROOT = Path(__file__).parent.resolve()
SRC_DIR = SITE_ROOT / "blog" / "source"
POSTS_DIR = SITE_ROOT / "blog" / "posts"
INDEX_PATH = SITE_ROOT / "blog" / "index.html"

# Post metadata: (slug, title override, publish date, tags) keyed by source filename.
# The publish dates are intentionally staggered across the May 2026 sprint week
# so the blog index shows a sensible chronology — they are NOT manufactured to
# pre-date real events.
POST_META = {
    "00-hipaa-as-go-interfaces.md": {
        "slug": "hipaa-as-go-interfaces",
        "date": "2026-05-19",
        "tags": ["HIPAA", "Compliance", "Go", "Privacy Engineering"],
        "audience": "Compliance + engineering",
        "excerpt": "What HIPAA looks like when you express it as Go interfaces — governance policies, append-only audit at DB GRANTs, PHI redaction at the logger seam, and HITL as the §3060 CDS carve-out criterion 4.",
        "citations": [
            {
                "title": "HIPAA Technical Safeguards (45 CFR §164.312)",
                "url": "https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html",
                "context": "Access controls and audit mechanisms"
            },
            {
                "title": "21st Century Cures Act Clinical Decision Support (§3060)",
                "url": "https://www.congress.gov/bill/114th-congress/house-bill/34",
                "context": "Human-in-the-loop requirements for AI-assisted diagnosis"
            }
        ]
    },
    "01-bench-42-to-85.md": {
        "slug": "bench-42-to-85",
        "date": "2026-05-20",
        "tags": ["ML Engineering", "Benchmarks", "Go", "Evaluation"],
        "audience": "ML engineers, AI medicine",
        "excerpt": "How a single sprint of specialty-rule work — guided by a benchmark that wasn't afraid to print embarrassing numbers — turned a 'demo respiratory differential' into a five-condition rule-based diagnostic engine.",
    },
    "02-cures-act-as-code.md": {
        "slug": "cures-act-as-code",
        "date": "2026-05-21",
        "tags": ["Regulation", "Clinical Decision Support", "Cures Act", "Go"],
        "audience": "Policy + engineering",
        "excerpt": "The 21st Century Cures Act §3060 CDS carve-out criterion 4 expressed as a code-level queue, lossless on reject, with audit-recorded reviewer rationale. Build it once, satisfy GDPR Article 22 for free.",
    },
    "03-postgres-rls-hipaa.md": {
        "slug": "postgres-rls-hipaa",
        "date": "2026-05-22",
        "tags": ["PostgreSQL", "HIPAA", "Database Security", "Go"],
        "audience": "Backend engineering + security",
        "excerpt": "PostgreSQL row-level security as HIPAA defence in depth. Why fail-open application filtering isn't enough, and how 'append-only at DB GRANTs' carries more of the §164.312(b) burden than people realise.",
        "citations": [
            {
                "title": "PostgreSQL Row-Level Security (RLS) Documentation",
                "url": "https://www.postgresql.org/docs/current/ddl-rowsecurity.html",
                "context": "Filtering rows at the database layer"
            },
            {
                "title": "HIPAA § 164.312(a)(2)(i): Access Controls",
                "url": "https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html",
                "context": "Unique user identification and session management"
            },
            {
                "title": "PostgreSQL Grant & Permission System",
                "url": "https://www.postgresql.org/docs/current/sql-grant.html",
                "context": "Database-level access control enforcement"
            }
        ]
    },
    "04-fallback-is-the-contract.md": {
        "slug": "fallback-is-the-contract",
        "date": "2026-05-23",
        "tags": ["SRE", "Reliability", "LLM", "Production"],
        "audience": "SRE / reliability + ML infra",
        "excerpt": "Every LLM-backed agent in this platform has a deterministic rule-based fallback. The case always finalises. The fallback isn't a workaround — it's the contract.",
    },
    "05-mara-five-interfaces.md": {
        "slug": "mara-five-interfaces",
        "date": "2026-05-23",
        "tags": ["Software Architecture", "Multi-Agent", "MAF", "Go"],
        "audience": "Software architects",
        "excerpt": "Five interfaces hold the whole platform together. The 30-line orchestrator closure that makes the rest of the architecture testable, auditable, and safe to evolve.",
    },
    "06-audit-log-design.md": {
        "slug": "audit-log-design",
        "date": "2026-05-24",
        "tags": ["HIPAA", "Audit Log", "Privacy Engineering", "Compliance"],
        "audience": "Privacy + compliance + engineering",
        "excerpt": "Enough to reconstruct, never enough to leak. The audit event schema problem under §164.312(b), and how to solve it without conflating the audit sink with the PHI sink.",
    },
    "07-hl7v2-still-matters.md": {
        "slug": "hl7v2-still-matters",
        "date": "2026-05-25",
        "tags": ["HL7 v2", "FHIR", "Healthcare IT", "Integration"],
        "audience": "Healthcare IT integration",
        "excerpt": "Why HL7 v2 — a 50-year-old pipe-delimited protocol — still drives most US hospital ADT integrations in 2026, and what a clean Go parser looks like in ~300 lines.",
    },
    "08-aigp-reference-implementation.md": {
        "slug": "aigp-reference-implementation",
        "date": "2026-05-25",
        "tags": ["AI Governance", "AIGP", "IAPP", "Compliance"],
        "audience": "AIGP candidates + AI governance practitioners",
        "excerpt": "Studying for the IAPP AI Governance Professional credential? Here's an open-source Go codebase that demonstrates ~70% of the body of knowledge in working code.",
    },
    "09-gke-ai-infra-medical-multiagent.md": {
        "slug": "gke-ai-infra-medical-multiagent",
        "date": "2026-05-26",
        "tags": ["GKE", "GCP", "Multi-Agent", "Cloud Architecture"],
        "audience": "Cloud architects + medical AI engineers",
        "excerpt": "Google's GKE AI infrastructure docs list ~40 integrations. Here's a field map of which ones actually matter when the workload is a HIPAA-aware multi-agent medical AI, and where the gaps sit.",
    },
    "2026-06-01-adk-to-maf-migration-why.md": {
        "slug": "adk-to-maf-migration-why",
        "date": "2026-06-01",
        "tags": ["ADK", "MAF", "Architecture", "Multi-Agent AI"],
        "audience": "Software architects + platform engineers",
        "excerpt": "The philosophy, trade-offs, and what we learned converting 18+ agents in 3 months. Provider abstraction as the foundation for portable agents.",
        "featured": True,
        "series": "ADK to MAF Migration",
        "series_position": 1,
        "series_total": 8,
        "citations": [
            {
                "title": "Microsoft Agent Framework Documentation",
                "url": "https://learn.microsoft.com/en-us/azure/ai-services/agents/",
                "context": "Official MAF patterns and best practices"
            },
            {
                "title": "Google Agent Driven Kit (ADK) Reference",
                "url": "https://developers.google.com/assistant/sdk",
                "context": "ADK orchestration patterns and limitations"
            },
            {
                "title": "Provider Abstraction in Multi-Agent Systems",
                "url": "https://pratikdhanave.com/thank-you/",
                "context": "Design pattern for portable agent implementations"
            }
        ]
    },
    "2026-06-02-adk-to-maf-executor-pattern.md": {
        "slug": "adk-to-maf-executor-pattern",
        "date": "2026-06-02",
        "tags": ["ADK", "MAF", "Orchestration", "Design Pattern"],
        "audience": "Platform architects",
        "excerpt": "How to port ADK's orchestration callbacks to MAF builders without losing control. The executor pattern: you own the loop.",
        "series": "ADK to MAF Migration",
        "series_position": 2,
        "series_total": 8,
    },
    "2026-06-03-adk-to-maf-token-exchange.md": {
        "slug": "adk-to-maf-token-exchange",
        "date": "2026-06-03",
        "tags": ["ADK", "MAF", "State Management", "Token Budgeting"],
        "audience": "Backend + ML engineers",
        "excerpt": "Sessions to threads: porting multi-turn state from ADK to MAF. Token budgeting, long-term memory, and conversation audit trails.",
        "series": "ADK to MAF Migration",
        "series_position": 3,
        "series_total": 8,
    },
    "2026-06-04-adk-to-maf-tool-wrapping.md": {
        "slug": "adk-to-maf-tool-wrapping",
        "date": "2026-06-04",
        "tags": ["ADK", "MAF", "Tools", "Governance", "OPA"],
        "audience": "Governance + backend engineers",
        "excerpt": "From ADK functions to MAF governed tools. Adding policy enforcement, DLP, approval gates, and OPA integration.",
        "series": "ADK to MAF Migration",
        "series_position": 4,
        "series_total": 8,
    },
    "2026-06-05-adk-to-maf-provider-config.md": {
        "slug": "adk-to-maf-provider-config",
        "date": "2026-06-05",
        "tags": ["ADK", "MAF", "Provider Abstraction", "Config"],
        "audience": "DevOps + platform engineers",
        "excerpt": "Zero-code provider swaps: Ollama (dev), OpenAI (staging), Azure Foundry (prod). Same agents, different models.",
        "series": "ADK to MAF Migration",
        "series_position": 5,
        "series_total": 8,
    },
    "2026-06-06-adk-to-maf-callbacks.md": {
        "slug": "adk-to-maf-callbacks",
        "date": "2026-06-06",
        "tags": ["ADK", "MAF", "Middleware", "Observability", "OTel"],
        "audience": "SRE + observability engineers",
        "excerpt": "Callbacks to middleware: composable decorators for audit, retry, token enforcement, and OpenTelemetry integration.",
        "series": "ADK to MAF Migration",
        "series_position": 6,
        "series_total": 8,
    },
    "2026-06-07-adk-to-maf-deployment.md": {
        "slug": "adk-to-maf-deployment",
        "date": "2026-06-07",
        "tags": ["ADK", "MAF", "Deployment", "Cloud Run", "A2A"],
        "audience": "Cloud architects + SRE",
        "excerpt": "Cloud Run deployments, agent-to-agent communication, load balancing, and production observability.",
        "series": "ADK to MAF Migration",
        "series_position": 7,
        "series_total": 8,
    },
    "2026-06-08-adk-to-maf-lessons.md": {
        "slug": "adk-to-maf-lessons",
        "date": "2026-06-08",
        "tags": ["ADK", "MAF", "Case Study", "Lessons Learned"],
        "audience": "All engineers",
        "excerpt": "What worked, what was hard, and what we'd do differently. Real numbers: 18 agents, 90 days, 5 governance policies, 4 provider swaps.",
        "featured": True,
        "series": "ADK to MAF Migration",
        "series_position": 8,
        "series_total": 8,
    },
    "auto-000-12-google-cloud-agent-patterns-mapped.md": {
        "slug": "12-google-cloud-agent-patterns-mapped",
        "date": "2026-02-19",
        "tags": ['Agents', 'Architecture', 'Google Cloud'],
        "audience": "Engineering",
        "excerpt": "Google publishes a 12-pattern taxonomy for agent design. Most of them have direct corollaries in production code; one or two are best ignored. The mapping I\'ve used.",
    },
    "2026-05-17-57-percent-bigquery-cost-reduction-tata.md": {
        "slug": "57-percent-bigquery-cost-reduction-tata",
        "date": "2026-05-17",
        "tags": ['BigQuery', 'FinOps', 'Cloud Architecture', 'Solution Architecture', 'Data Warehouse'],
        "audience": "Engineering",
        "excerpt": "Architecture decisions that delivered 57% cost reduction on a Fortune 500 BigQuery data warehouse. The MERGE anti-pattern fix, partition strategy, capacity model, and the trust gap I'd handle differently next time.",
    },
    "auto-002-a2a-protocol-go-client.md": {
        "slug": "a2a-protocol-go-client",
        "date": "2026-02-20",
        "tags": ['A2A', 'Agents', 'Go', 'Protocols'],
        "audience": "Engineering",
        "excerpt": "Anthropic\'s A2A spec standardises how agents talk to other agents (not just tools). The Go client is small; the conceptual shift is what matters.",
    },
    "auto-003-agentic-architecture-on-mara.md": {
        "slug": "agentic-architecture-on-mara",
        "date": "2026-04-10",
        "tags": ['Architecture', 'MAF', 'Go', 'Multi-Agent AI'],
        "audience": "Engineering",
        "excerpt": "Microsoft\'s Multi-Agent Reference Architecture in Go. Protocol, registry, bus, governance, orchestration, observability, evaluation — and how the seven hold each other up.",
    },
    "auto-004-agentic-security-in-production.md": {
        "slug": "agentic-security-in-production",
        "date": "2026-04-20",
        "tags": ['Security', 'Operations', 'SRE', 'Multi-Agent AI'],
        "audience": "Engineering",
        "excerpt": "Twelve months of running multi-agent AI in a regulated context. SLIs that matter, the incident runbook, drift detection, continuous adversarial testing, secret rotation, compliance posture as code.",
    },
    "auto-005-ai-governance-from-credential-to-codebase.md": {
        "slug": "ai-governance-from-credential-to-codebase",
        "date": "2026-04-21",
        "tags": ['Governance', 'FREE-AI', 'Compliance', 'Multi-Agent AI'],
        "audience": "Engineering",
        "excerpt": "Board policy as a YAML file the risk team owns. Annexure VI as a database query. Every governance recommendation rendered as a file path in a Go repository.",
    },
    "auto-006-aigp-iapp-body-of-knowledge-reading-map.md": {
        "slug": "aigp-iapp-body-of-knowledge-reading-map",
        "date": "2026-02-01",
        "tags": ['AIGP', 'AI Governance', 'IAPP', 'Compliance'],
        "audience": "Engineering",
        "excerpt": "IAPP\'s AI Governance Professional certification covers a body of knowledge worth knowing whether you certify or not. The mapping from BOK to working Go code for the engineer who wants to understand AI governance practically.",
    },
    "auto-007-airshipit-opentelemetry-30pct-ops-reduction.md": {
        "slug": "airshipit-opentelemetry-30pct-ops-reduction",
        "date": "2026-05-07",
        "tags": ['OpenTelemetry', 'Kubernetes', 'Open Source', 'Observability'],
        "audience": "Engineering",
        "excerpt": "Notes from integrating OpenTelemetry into airshipit, an open-source bare-metal Kubernetes lifecycle project with contributions from Ericsson, AT&T, Microsoft, and others. The hard part wasn\'t OTel; it was making distributed traces useful across foreign code.",
    },
    "auto-008-annexure-vi-as-a-query.md": {
        "slug": "annexure-vi-as-a-query",
        "date": "2026-04-19",
        "tags": ['FREE-AI', 'Compliance', 'Incident Response'],
        "audience": "Engineering",
        "excerpt": "The RBI FREE-AI incident reporting form, expressed as a Go struct and a Postgres table. Every entry is an auto-generated artefact from the runtime — not a form an operator fills in retrospectively.",
    },
    "auto-042-audit-logs-are-the-api-of-record.md": {
        "slug": "audit-logs-are-the-api-of-record",
        "date": "2026-01-30",
        "tags": ['Audit', 'Architecture', 'Opinion'],
        "audience": "Engineering",
        "excerpt": "The audit log isn\'t a side effect of the system. It\'s the contract you owe to regulators, customers, and your future self. Treat it as a first-class API — schema, versioning, and SLOs included.",
    },
    "auto-043-aws-bedrock-vertex-ai-same-agent-stack.md": {
        "slug": "aws-bedrock-vertex-ai-same-agent-stack",
        "date": "2026-02-10",
        "tags": ['AWS', 'Bedrock', 'Vertex AI', 'Multi-Cloud', 'Go'],
        "audience": "Engineering",
        "excerpt": "An enterprise customer wants you on AWS; the next one wants you on GCP. The provider router pattern that keeps the agent code identical and swaps only the LLM endpoint.",
    },
    "auto-044-azure-service-operator-multi-vendor-collaboration.md": {
        "slug": "azure-service-operator-multi-vendor-collaboration",
        "date": "2026-05-06",
        "tags": ['Azure', 'Kubernetes', 'Open Source', 'Operators'],
        "audience": "Engineering",
        "excerpt": "The azure-service-operator project lets you declare Azure resources as Kubernetes objects. Notes from the multi-vendor collaboration shape: how decisions got made, what slowed us down, what shipped despite it.",
    },
    "auto-045-bcp-for-ai-forced-failure-drills.md": {
        "slug": "bcp-for-ai-forced-failure-drills",
        "date": "2026-04-16",
        "tags": ['BCP', 'Resilience', 'Multi-Agent AI', 'Testing'],
        "audience": "Engineering",
        "excerpt": "Fallback agents plus a CI step that replaces the primary agent with one that always errors. If the fallback doesn\'t produce a usable answer, the PR can\'t merge.",
    },
    "auto-046-bigquery-knowledge-graph-entity-resolution.md": {
        "slug": "bigquery-knowledge-graph-entity-resolution",
        "date": "2026-02-24",
        "tags": ['BigQuery', 'Knowledge Graph', 'Entity Resolution'],
        "audience": "Engineering",
        "excerpt": "BigQuery has had a built-in knowledge graph since 2024. For entity resolution across millions of rows — the \"is this John Smith the same as that John Smith\" problem — it\'s the cheapest tool I\'ve found.",
    },
    "auto-047-bigquery-slot-reservation-transition.md": {
        "slug": "bigquery-slot-reservation-transition",
        "date": "2026-05-15",
        "tags": ['BigQuery', 'FinOps', 'GCP', 'Reservations'],
        "audience": "Engineering",
        "excerpt": "Capacity-based slot reservation is the biggest single FinOps lever for predictable batch workloads, but the transition is harder than the math. Notes from sizing reservations across enterprise GCP customers.",
    },
    "auto-048-bigquery-storage-tiering-physical-logical-bytes.md": {
        "slug": "bigquery-storage-tiering-physical-logical-bytes",
        "date": "2026-05-14",
        "tags": ['BigQuery', 'FinOps', 'Storage', 'GCP'],
        "audience": "Engineering",
        "excerpt": "Storage was the second-biggest line item on the Tata BigQuery bill. Long-term storage, physical-vs-logical billing, and column-level retention together took a 6-figure monthly line down to a 5-figure one.",
    },
    "auto-049-bloom-terraform-regulated-bank-cloud.md": {
        "slug": "bloom-terraform-regulated-bank-cloud",
        "date": "2026-05-09",
        "tags": ['Terraform', 'Banking', 'SOC 2', 'ISO 27001', 'AWS'],
        "audience": "Engineering",
        "excerpt": "Notes from contributing to Bloom — SC Ventures / Standard Chartered\'s policy-driven secure cloud provisioning platform. Push-to-deploy self-service for bank engineering teams, with the audit controls baked in.",
    },
    "auto-050-boring-stack-choices-regulated-ai.md": {
        "slug": "boring-stack-choices-regulated-ai",
        "date": "2026-02-15",
        "tags": ['Architecture', 'Opinion', 'Go'],
        "audience": "Engineering",
        "excerpt": "Postgres over the latest vector DB. Go stdlib over the framework du jour. Single binary over Kubernetes operator. The choices that bore reviewers and delight on-call engineers.",
    },
    "auto-051-brownlow-cloud-kms-security-command-center.md": {
        "slug": "brownlow-cloud-kms-security-command-center",
        "date": "2026-02-02",
        "tags": ['Cloud KMS', 'Security Command Center', 'GCP', 'Voting'],
        "audience": "Engineering",
        "excerpt": "Vote integrity needed two things the platform team couldn\'t fake even by accident: signing keys we couldn\'t access, and continuous security monitoring we couldn\'t silence. KMS + SCC delivered both.",
    },
    "auto-052-brownlow-zero-trust-voting-cloud-run.md": {
        "slug": "brownlow-zero-trust-voting-cloud-run",
        "date": "2026-04-28",
        "tags": ['Cloud Run', 'Go', 'GraphQL', 'gRPC', 'KMS'],
        "audience": "Engineering",
        "excerpt": "100K+ votes, 10K+ concurrent users during a live AFL Brownlow Medal broadcast. The architecture: Go on Cloud Run, GraphQL + gRPC behind a CDN, vote integrity through Cloud KMS + Security Command Center. Notes on what makes a live-broadcast load shape unusual.",
    },
    "auto-053-cdc-minimal-downtime-spanner-migration.md": {
        "slug": "cdc-minimal-downtime-spanner-migration",
        "date": "2026-05-10",
        "tags": ['Spanner', 'Datastream', 'Pub/Sub', 'Dataflow', 'Migration'],
        "audience": "Engineering",
        "excerpt": "A bulk migration takes hours; the application can\'t be offline that long. CDC keeps the source and destination in sync while the bulk runs, and a quick cutover swaps traffic. The handoff between bulk and CDC is where most migrations go wrong.",
    },
    "auto-054-consolidated-security-deep-dive.md": {
        "slug": "consolidated-security-deep-dive",
        "date": "2026-04-22",
        "tags": ['Security', 'Architecture', 'FREE-AI'],
        "audience": "Engineering",
        "excerpt": "The long-form security narrative for a multi-agent financial assistant — authentication, authorisation, tenant isolation, dual-identity audit, envelope encryption, hash-chained logs, governance, red team, BCP.",
    },
    "auto-055-cost-aware-agent-dispatch.md": {
        "slug": "cost-aware-agent-dispatch",
        "date": "2026-02-17",
        "tags": ['Agents', 'Cost Optimisation', 'LLM Ops'],
        "audience": "Engineering",
        "excerpt": "Not every query needs the production agent. A cost-aware dispatcher decides whether to route to the cheap-and-fast agent or the expensive-and-thorough one. Same UX, dramatically lower bill.",
    },
    "auto-056-data-residency-uae-saudi-bancnet.md": {
        "slug": "data-residency-uae-saudi-bancnet",
        "date": "2026-02-08",
        "tags": ['Data Residency', 'UAE', 'Saudi Arabia', 'Open Banking'],
        "audience": "Engineering",
        "excerpt": "An open-banking platform serving UAE and Saudi customers had to honour three overlapping regulators: ADGM (Abu Dhabi), DIFC (Dubai), and SAMA (Saudi central bank). Notes on the architecture that satisfied all three.",
    },
    "auto-057-default-to-prototype-as-culture.md": {
        "slug": "default-to-prototype-as-culture",
        "date": "2026-02-14",
        "tags": ['Culture', 'Engineering', 'Tier Promotion'],
        "audience": "Engineering",
        "excerpt": "An agent that doesn\'t declare a tier defaults to Prototype, not Production. The flag is the code; the culture is what enforces \"new code is not production until someone says so.\"",
    },
    "auto-058-defence-in-depth-for-agentic-ai.md": {
        "slug": "defence-in-depth-for-agentic-ai",
        "date": "2026-04-23",
        "tags": ['Security', 'Architecture', 'Multi-Agent AI', 'FREE-AI'],
        "audience": "Engineering",
        "excerpt": "The mental model that says no two adjacent layers share a single point of failure for the same class of attack. From TLS to OTel, the eleven layers a customer request crosses before an answer comes back.",
    },
    "auto-059-deterministic-kyc-llm-just-talks.md": {
        "slug": "deterministic-kyc-llm-just-talks",
        "date": "2026-04-12",
        "tags": ['KYC', 'RBI', 'Multi-Agent AI', 'FinTech'],
        "audience": "Engineering",
        "excerpt": "PAN check-digit validation, Aadhaar offline KYC, DigiLocker, PEP/sanctions — all in Go code, not in a prompt. The LLM\'s job is to translate the verdict into something a human can read.",
    },
    "auto-060-egress-costs-cloud-arbitrage.md": {
        "slug": "egress-costs-cloud-arbitrage",
        "date": "2026-02-09",
        "tags": ['Multi-Cloud', 'Cost Optimisation', 'Networking'],
        "audience": "Engineering",
        "excerpt": "Cross-cloud data movement is billed by the GB. The bill is invisible until it isn\'t. A multi-region or multi-cloud architecture that doesn\'t model egress costs in design will discover them in production.",
    },
    "auto-061-embed-fs-as-deployment-unit.md": {
        "slug": "embed-fs-as-deployment-unit",
        "date": "2026-02-13",
        "tags": ['Go', 'embed.FS', 'Deployment'],
        "audience": "Engineering",
        "excerpt": "Go\'s embed.FS bundles files into the binary at compile time. The pattern collapses what would be a multi-artefact deploy into one binary. Three places it pays back daily.",
    },
    "auto-062-errgroup-parallel-agent-dispatch.md": {
        "slug": "errgroup-parallel-agent-dispatch",
        "date": "2026-01-27",
        "tags": ['Go', 'errgroup', 'Concurrency'],
        "audience": "Engineering",
        "excerpt": "Fan out to N agents; first error cancels the rest; collect successful results. errgroup is the right tool for this; the patterns are concise but worth getting exactly right.",
    },
    "auto-063-gke-for-stateful-ai-workloads.md": {
        "slug": "gke-for-stateful-ai-workloads",
        "date": "2026-02-07",
        "tags": ['GKE', 'Kubernetes', 'Multi-Agent AI', 'Production'],
        "audience": "Engineering",
        "excerpt": "Multi-agent stacks have state: vector indexes, chat histories, agent memory. GKE for AI workloads needs StatefulSets, PVCs, gateway controllers, and the patterns that work in 2026.",
    },
    "auto-064-globe-30k-tps-kubernetes-transaction-platform.md": {
        "slug": "globe-30k-tps-kubernetes-transaction-platform",
        "date": "2026-05-03",
        "tags": ['Kubernetes', 'Kafka', 'Go', 'Redis', 'Payments'],
        "audience": "Engineering",
        "excerpt": "The transaction engine had to absorb 30K+ TPS across partner integrations, never lose a transaction, and survive partial failures. The architecture: Go, Kafka, Pub/Sub, Redis, K8s, with idempotency at every layer.",
    },
    "auto-065-globe-error-code-orchestration.md": {
        "slug": "globe-error-code-orchestration",
        "date": "2026-05-01",
        "tags": ['Go', 'Distributed Systems', 'Architecture'],
        "audience": "Engineering",
        "excerpt": "Status-code-based dispatch made every worker grow a longer and longer switch. Normalising every partner-specific error into an enumerated set let the orchestration logic stop changing as new partners landed.",
    },
    "auto-066-globe-idempotency-three-layers.md": {
        "slug": "globe-idempotency-three-layers",
        "date": "2026-05-02",
        "tags": ['Idempotency', 'Distributed Systems', 'Payments', 'Go'],
        "audience": "Engineering",
        "excerpt": "A single layer of idempotency will eventually fail. Three independent layers gives you a margin. Here is the pattern that worked across ingest, worker, and emit boundaries.",
    },
    "auto-067-gocloud-unified-cloud-api-design.md": {
        "slug": "gocloud-unified-cloud-api-design",
        "date": "2026-04-25",
        "tags": ['Go', 'Multi-Cloud', 'Open Source', 'API Design'],
        "audience": "Engineering",
        "excerpt": "What it actually takes to build a unified cloud API library — and why \"write once, run anywhere\" still doesn\'t quite work, even for the patterns where it almost does.",
    },
    "auto-068-gomemlimit-soft-gc-pacing.md": {
        "slug": "gomemlimit-soft-gc-pacing",
        "date": "2026-02-12",
        "tags": ['Go', 'GOMEMLIMIT', 'Memory', 'Kubernetes'],
        "audience": "Engineering",
        "excerpt": "GOMEMLIMIT tells the Go runtime to keep memory below a soft cap by running GC harder when it\'s close. For containers with hard memory limits, this prevents OOM kills. The setting every Go service in K8s should have.",
    },
    "auto-069-google-cloud-next-2022-monolith-microservices-talk.md": {
        "slug": "google-cloud-next-2022-monolith-microservices-talk",
        "date": "2026-04-27",
        "tags": ['Speaking', 'Microservices', 'Google Cloud Next', 'Architecture'],
        "audience": "Engineering",
        "excerpt": "30 minutes on stage. The talk title looked tactical; the talk underneath was about why most microservices migrations fail and how to set up the one that doesn\'t.",
    },
    "auto-070-graphrag-when-graph-beats-vector.md": {
        "slug": "graphrag-when-graph-beats-vector",
        "date": "2026-02-25",
        "tags": ['GraphRAG', 'RAG', 'Knowledge Graph'],
        "audience": "Engineering",
        "excerpt": "Vector search treats every chunk as independent. GraphRAG models the relationships between entities, communities, and concepts. For corpus-spanning questions (\"what\'s the relationship between X and Y\"), graph wins.",
    },
    "auto-071-gsoc-mentor-2019-2026-lessons.md": {
        "slug": "gsoc-mentor-2019-2026-lessons",
        "date": "2026-04-26",
        "tags": ['GSoC', 'Open Source', 'Mentorship'],
        "audience": "Engineering",
        "excerpt": "Seven cycles. Ten-plus students. Most shipped, a few didn\'t, all of them taught me something about engineering culture. Notes on what works for mentors and what works for students.",
    },
    "auto-072-hs256-vs-rs256-pick-wrong-and-explain-why.md": {
        "slug": "hs256-vs-rs256-pick-wrong-and-explain-why",
        "date": "2026-03-06",
        "tags": ['Go', 'JWT', 'Security', 'Cryptography'],
        "audience": "Engineering",
        "excerpt": "Symmetric vs asymmetric JWT signing. The choice changes what fails when a key leaks, who can verify, and how rotation works.",
    },
    "auto-073-hyde-hypothetical-document-embeddings.md": {
        "slug": "hyde-hypothetical-document-embeddings",
        "date": "2026-02-23",
        "tags": ['RAG', 'HyDE', 'Retrieval'],
        "audience": "Engineering",
        "excerpt": "Embedding a question and embedding an answer often produce different vectors. HyDE generates a hypothetical answer to the question, embeds *that*, and retrieves on it. Retrieval quality goes up disproportionately.",
    },
    "auto-074-iter-seq-pull-iterator-go-123.md": {
        "slug": "iter-seq-pull-iterator-go-123",
        "date": "2026-01-28",
        "tags": ['Go', 'iter.Seq', 'Go 1.23'],
        "audience": "Engineering",
        "excerpt": "Range-over-function landed in Go 1.23. `iter.Seq` lets you write iterators that compose. The patterns that pay back; the ones that don\'t.",
    },
    "auto-075-jwt-150-lines-of-go.md": {
        "slug": "jwt-150-lines-of-go",
        "date": "2026-03-07",
        "tags": ['Go', 'JWT', 'Security', 'Stdlib'],
        "audience": "Engineering",
        "excerpt": "HS256 JWT issue + verify + audience check + expiry in pure stdlib. Why pulling a third-party JWT library is the wrong call for security-critical code.",
    },
    "auto-076-kyc-master-direction-vs-aadhaar-offline.md": {
        "slug": "kyc-master-direction-vs-aadhaar-offline",
        "date": "2026-02-04",
        "tags": ['KYC', 'RBI', 'Aadhaar', 'FinTech'],
        "audience": "Engineering",
        "excerpt": "Two KYC pathways an Indian fintech has to support. The Master Direction (Video KYC, etc.) and Aadhaar Offline KYC. Different speeds, different evidence requirements, different audit shapes.",
    },
    "auto-077-latency-aware-agent-dispatch-slo.md": {
        "slug": "latency-aware-agent-dispatch-slo",
        "date": "2026-02-16",
        "tags": ['Agents', 'SLO', 'Latency'],
        "audience": "Engineering",
        "excerpt": "Two agents can do the same job. One takes 200ms; the other takes 5 seconds. Pick by user-facing SLO, not by which agent is \"better.\" The dispatcher pattern.",
    },
    "auto-089-mapping-genie-to-gcp-pcse-blueprint.md": {
        "slug": "mapping-genie-to-gcp-pcse-blueprint",
        "date": "2026-04-24",
        "tags": ['Security', 'GCP', 'PCSE', 'Multi-Agent AI', 'Go'],
        "audience": "Engineering",
        "excerpt": "Every Professional Cloud Security Engineer exam bullet, mapped to a file path in an RBI FREE-AI aligned Go platform. Where the implementation matches, where the analog substitutes, and where the honest gaps are.",
    },
    "auto-090-merge-pattern-cost-ten-times-more.md": {
        "slug": "merge-pattern-cost-ten-times-more",
        "date": "2026-05-18",
        "tags": ['BigQuery', 'FinOps', 'SQL', 'Cost Optimisation'],
        "audience": "Engineering",
        "excerpt": "What looked like an idiomatic BigQuery MERGE was scanning the full target table on every batch. The fix was syntactic, not architectural — and it was the single biggest contributor to a 57% data-warehouse cost reduction across the Tata Group engagement.",
    },
    "auto-091-mtls-envoy-spire-svid.md": {
        "slug": "mtls-envoy-spire-svid",
        "date": "2026-02-27",
        "tags": ['mTLS', 'Envoy', 'SPIRE', 'Service Mesh'],
        "audience": "Engineering",
        "excerpt": "Pushing mTLS into a service mesh removes it from every individual service. Envoy + SPIRE is the canonical pattern; the implementation has fewer moving parts than the architecture diagrams suggest.",
    },
    "auto-092-multilingual-rag-bhashini-cross-lingual.md": {
        "slug": "multilingual-rag-bhashini-cross-lingual",
        "date": "2026-02-21",
        "tags": ['RAG', 'Multilingual', 'Bhashini', 'Indic Languages'],
        "audience": "Engineering",
        "excerpt": "An Indian banking deployment needs to handle Hindi, Marathi, Tamil, Bengali, and English in the same retrieval pipeline. Bhashini (the government\'s language stack) plus cross-lingual embeddings make it tractable.",
    },
    "auto-093-npci-rail-routing-with-hitl.md": {
        "slug": "npci-rail-routing-with-hitl",
        "date": "2026-04-14",
        "tags": ['Payments', 'NPCI', 'FinTech', 'HITL'],
        "audience": "Engineering",
        "excerpt": "UPI, IMPS, NEFT, RTGS — which rail to use depends on amount, urgency, window, success-rate history. A deterministic chooser with a HITL gate above ₹2 lakh.",
    },
    "auto-094-oauth-21-pkce-for-spa.md": {
        "slug": "oauth-21-pkce-for-spa",
        "date": "2026-03-05",
        "tags": ['Go', 'OAuth', 'PKCE', 'Security'],
        "audience": "Engineering",
        "excerpt": "PKCE is the load-bearing mitigation against authorization-code interception. The Go implementation is short; the parts every SPA gets wrong are documented here.",
    },
    "auto-095-oauth-device-flow-voice-kiosks.md": {
        "slug": "oauth-device-flow-voice-kiosks",
        "date": "2026-03-04",
        "tags": ['Go', 'OAuth', 'Device Flow', 'Voice AI'],
        "audience": "Engineering",
        "excerpt": "The flow where the device has no browser. User authenticates on their phone; the device polls until they\'re done. Implementation patterns in Go from the Genie reference.",
    },
    "auto-096-optimus-bigquery-anti-pattern-detector.md": {
        "slug": "optimus-bigquery-anti-pattern-detector",
        "date": "2026-05-16",
        "tags": ['BigQuery', 'Gemini', 'FinOps', 'Go', 'Python'],
        "audience": "Engineering",
        "excerpt": "We built a small Go + Python service that parses a project\'s INFORMATION_SCHEMA, asks Gemini to classify each top-spending query against a catalog of anti-patterns, and recommends a rewrite. It is not a magic box; it is a pipeline that cuts the human review time per query from 20 minutes to 90 seconds.",
    },
    "auto-097-otel-evaluation-multi-agent-workflows.md": {
        "slug": "otel-evaluation-multi-agent-workflows",
        "date": "2026-05-29",
        "tags": ['OpenTelemetry', 'Evaluation', 'Multi-Agent AI', 'Observability', 'Genie'],
        "audience": "Engineering",
        "excerpt": "How to instrument multi-agent systems with OpenTelemetry, propagate trace context across an in-memory bus, and build a layered evaluation pipeline — from real-time policy gates to async LLM-as-judge to SLO-based trust scoring. Everything I learned building Genie.",
    },
    "auto-098-p2p-lender-double-entry-ledger-invariants.md": {
        "slug": "p2p-lender-double-entry-ledger-invariants",
        "date": "2026-04-30",
        "tags": ['Go', 'PostgreSQL', 'FinTech', 'Lending', 'Accounting'],
        "audience": "Engineering",
        "excerpt": "5K+ loans per month. Three credit bureaus. Multiple payment gateways. The thing that has to be right is the ledger. Notes on what invariants the database enforces vs what the application enforces.",
    },
    "auto-099-p2p-lender-kyc-aml-credit-bureau-maker-checker.md": {
        "slug": "p2p-lender-kyc-aml-credit-bureau-maker-checker",
        "date": "2026-04-29",
        "tags": ['KYC', 'AML', 'Lending', 'Fraud', 'RBAC'],
        "audience": "Engineering",
        "excerpt": "Borrower onboarding is the most fraud-prone moment in a P2P platform. The shape that worked: deterministic KYC, parallel bureau pulls with fallback, real-time fraud signals, and a maker-checker approval for every disbursement.",
    },
    "auto-100-picnic-protobuf-consolidation-47pct-latency.md": {
        "slug": "picnic-protobuf-consolidation-47pct-latency",
        "date": "2026-05-05",
        "tags": ['Go', 'gRPC', 'GraphQL', 'Microservices', 'Performance'],
        "audience": "Engineering",
        "excerpt": "The Picnic social platform served 1M+ users across a graph of Go microservices behind a GraphQL gateway. The latency win came from a counter-intuitive move: fewer services, tighter contracts.",
    },
    "auto-101-picnic-test-coverage-prometheus.md": {
        "slug": "picnic-test-coverage-prometheus",
        "date": "2026-05-04",
        "tags": ['Testing', 'Prometheus', 'Observability', 'Go', 'SRE'],
        "audience": "Engineering",
        "excerpt": "Test coverage and observability are the boring infrastructure that makes the interesting changes safe. Notes on how the Picnic team built both, and the on-call experience they enabled.",
    },
    "auto-102-policy-as-code-without-shipping-code.md": {
        "slug": "policy-as-code-without-shipping-code",
        "date": "2026-04-13",
        "tags": ['Governance', 'Policy', 'FREE-AI', 'DSL'],
        "audience": "Engineering",
        "excerpt": "A tiny CEL-style DSL plus a board-approved YAML file. The risk team adds a governance rule by editing a config file; engineering ships the rule by restarting the service.",
    },
    "auto-103-production-agentic-on-kubernetes.md": {
        "slug": "production-agentic-on-kubernetes",
        "date": "2026-04-11",
        "tags": ['Kubernetes', 'Multi-Agent AI', 'Operations'],
        "audience": "Engineering",
        "excerpt": "Field notes from running multi-agent AI on K8s. The patterns the book recommends, the ones that survived contact with production, and the ones that broke in interesting ways.",
    },
    "auto-104-rbi-free-ai-implementation-notes.md": {
        "slug": "rbi-free-ai-implementation-notes",
        "date": "2026-04-18",
        "tags": ['RBI', 'FREE-AI', 'Compliance', 'FinTech'],
        "audience": "Engineering",
        "excerpt": "Every one of the 26 RBI FREE-AI recommendations, mapped to a specific file in a working multi-agent platform. What\'s ✅ done, what\'s 🟡 partial, what\'s ⚪ honest gap.",
    },
    "auto-105-recruiter-test-what-your-repo-says.md": {
        "slug": "recruiter-test-what-your-repo-says",
        "date": "2026-01-25",
        "tags": ['Career', 'GitHub', 'Open Source', 'Opinion'],
        "audience": "Engineering",
        "excerpt": "A recruiter spends 90 seconds on your GitHub before deciding to talk to you. What they\'re looking for; what makes them skip; what signals matter more than the README.",
    },
    "auto-106-rfc-8693-token-exchange-nurse-alice.md": {
        "slug": "rfc-8693-token-exchange-nurse-alice",
        "date": "2026-03-02",
        "tags": ['Go', 'OAuth', 'RFC 8693', 'Agents', 'Security'],
        "audience": "Engineering",
        "excerpt": "Dual-identity tokens for the agent → MCP server → upstream API chain. Subject stays the user; Actor identifies the agent acting on the user\'s behalf. Walked through with a worked clinical example.",
    },
    "auto-107-right-to-explanation.md": {
        "slug": "right-to-explanation",
        "date": "2026-05-26",
        "tags": ['GDPR', 'Privacy Engineering', 'AI Governance', 'Go'],
        "audience": "Engineering",
        "excerpt": "How a 200-line Go handler turns an audit log and an eval store into a regulator-friendly answer to 'why did the AI decide that?'",
    },
    "auto-108-saga-rollback-half-succeeded.md": {
        "slug": "saga-rollback-half-succeeded",
        "date": "2026-02-18",
        "tags": ['Saga', 'Distributed Systems', 'Workflow', 'Go'],
        "audience": "Engineering",
        "excerpt": "A saga is fine when every step succeeds. The interesting code is what runs when step 3 of 5 fails and you have to undo 1 and 2 in the right order. The patterns I use.",
    },
    "auto-109-saml-verifier-go-xml-signing.md": {
        "slug": "saml-verifier-go-xml-signing",
        "date": "2026-03-01",
        "tags": ['Go', 'SAML', 'Identity Federation', 'Banking'],
        "audience": "Engineering",
        "excerpt": "Many banks have a SAML IdP they want you to federate against. The verify path is the boring-but-load-bearing piece. Notes on the stdlib-mostly Go implementation.",
    },
    "auto-110-self-rag-crag-when-to-retrieve.md": {
        "slug": "self-rag-crag-when-to-retrieve",
        "date": "2026-02-22",
        "tags": ['RAG', 'Self-RAG', 'CRAG', 'Retrieval'],
        "audience": "Engineering",
        "excerpt": "Naive RAG retrieves on every query. Self-RAG decides whether to retrieve. CRAG decides whether the retrieved content is good enough or needs corrective retrieval. Two papers; both worth implementing.",
    },
    "auto-111-session-anomaly-detection-haversine.md": {
        "slug": "session-anomaly-detection-haversine",
        "date": "2026-02-26",
        "tags": ['Go', 'Security', 'Anomaly Detection', 'Fraud'],
        "audience": "Engineering",
        "excerpt": "Two signals do most of the work for detecting compromised sessions: impossible travel between consecutive logins, and credential-stuffing density across an IP range. The Go implementation.",
    },
    "auto-112-slog-migration-replace-five-libraries.md": {
        "slug": "slog-migration-replace-five-libraries",
        "date": "2026-02-11",
        "tags": ['Go', 'slog', 'Logging', 'Stdlib'],
        "audience": "Engineering",
        "excerpt": "Go 1.21 added structured logging to the stdlib (slog). For a codebase with three or four logging-library generations layered on top of each other, the migration is a productive afternoon.",
    },
    "auto-113-soc2-controls-as-terraform-modules.md": {
        "slug": "soc2-controls-as-terraform-modules",
        "date": "2026-05-08",
        "tags": ['SOC 2', 'Terraform', 'Compliance', 'DevOps'],
        "audience": "Engineering",
        "excerpt": "If you encode each SOC 2 control as a Terraform module, the audit becomes a check against module usage rather than a per-resource review. Notes from Bloom and adjacent projects.",
    },
    "auto-114-sovereign-ai-is-a-policy.md": {
        "slug": "sovereign-ai-is-a-policy",
        "date": "2026-04-15",
        "tags": ['Data Residency', 'Governance', 'FREE-AI'],
        "audience": "Engineering",
        "excerpt": "Classification → provider allowlist. A pii-classified message can only reach a provider whose region is in the allowlist for pii. Sovereignty as a runtime gate, not a checkbox.",
    },
    "auto-115-spanner-interleaving-when-to-use.md": {
        "slug": "spanner-interleaving-when-to-use",
        "date": "2026-05-11",
        "tags": ['Spanner', 'Database Design', 'Schema'],
        "audience": "Engineering",
        "excerpt": "Interleaving a child table into its parent co-locates the rows for fast joins. It also tightens coupling in ways that bite you on the next schema migration. A practitioner\'s decision matrix.",
    },
    "auto-116-spanner-migration-tool-contributor-reading-map.md": {
        "slug": "spanner-migration-tool-contributor-reading-map",
        "date": "2026-05-13",
        "tags": ['Spanner', 'Open Source', 'Go', 'Database Migration'],
        "audience": "Engineering",
        "excerpt": "Notes from contributing to Google\'s open-source Spanner Migration Tool (HarbourBridge). Where to start reading the codebase, where the load-bearing logic lives, and the parts that look simple but aren\'t.",
    },
    "auto-117-spanner-pk-design-write-hotspots.md": {
        "slug": "spanner-pk-design-write-hotspots",
        "date": "2026-05-12",
        "tags": ['Spanner', 'Database Design', 'Performance', 'Go'],
        "audience": "Engineering",
        "excerpt": "Spanner partitions by primary-key range. A monotonically-increasing PK like a timestamp or UUID-v1 funnels all writes to one server. The fix changes everything from your sequence strategy to your tenant model.",
    },
    "auto-118-spiffe-spire-workload-identity-basics.md": {
        "slug": "spiffe-spire-workload-identity-basics",
        "date": "2026-02-28",
        "tags": ['SPIFFE', 'SPIRE', 'Workload Identity', 'Zero-Trust'],
        "audience": "Engineering",
        "excerpt": "Services need identity too, not just users. SPIFFE issues SVIDs (verifiable identity documents) to workloads; SPIRE is the reference issuer. The shape and the first deploy.",
    },
    "auto-119-the-board-policy-is-a-yaml-file.md": {
        "slug": "the-board-policy-is-a-yaml-file",
        "date": "2026-01-31",
        "tags": ['AI Governance', 'Policy as Code', 'FREE-AI', 'Opinion'],
        "audience": "Engineering",
        "excerpt": "The bank\'s board approves an AI policy. The policy exists as a slide deck nobody reads. The risk team\'s actual operational policy is what\'s in the code. Closing that gap is the FREE-AI Rec 14 win.",
    },
    "auto-120-time-bound-elevation-pam-analog.md": {
        "slug": "time-bound-elevation-pam-analog",
        "date": "2026-05-26",
        "tags": ['Security', 'Go', 'Audit', 'PAM', 'RBAC'],
        "audience": "Engineering",
        "excerpt": "Request → N-eyes approve → window-of-time → automatic expiry, with every transition written to a hash-chained audit log. The package that closes Gap #1 from the PCSE map.",
    },
    "auto-121-twelve-go-idioms-i-changed-my-mind-about.md": {
        "slug": "twelve-go-idioms-i-changed-my-mind-about",
        "date": "2026-01-29",
        "tags": ['Go', 'Opinion', 'Patterns'],
        "audience": "Engineering",
        "excerpt": "Patterns I confidently recommended five years ago that I\'d argue against today. The list of \"things you used to do in Go that don\'t pay back anymore.\"",
    },
    "auto-122-twelve-months-of-genie-what-survived.md": {
        "slug": "twelve-months-of-genie-what-survived",
        "date": "2026-01-24",
        "tags": ['Genie', 'Multi-Agent AI', 'Retrospective', 'Go'],
        "audience": "Engineering",
        "excerpt": "An honest retrospective on the open-source Genie project after a year. The patterns that held up; the ones we rebuilt; the code we deleted because it solved problems we didn\'t actually have.",
    },
    "auto-123-twelve-months-of-writing-what-worked.md": {
        "slug": "twelve-months-of-writing-what-worked",
        "date": "2026-01-26",
        "tags": ['Writing', 'Career', 'Opinion'],
        "audience": "Engineering",
        "excerpt": "Reflections on a year of consistent technical writing. The post categories that compounded; the ones that didn\'t; what I\'d tell someone starting out.",
    },
    "auto-124-upi-integration-spec-quirks.md": {
        "slug": "upi-integration-spec-quirks",
        "date": "2026-02-05",
        "tags": ['UPI', 'NPCI', 'Payments', 'FinTech'],
        "audience": "Engineering",
        "excerpt": "UPI is the most popular payment rail in India. The spec is precise. The implementation guides are not. Notes on the integration details that ate weeks the first time.",
    },
    "auto-125-voice-ai-kinetic-multi-language-patterns.md": {
        "slug": "voice-ai-kinetic-multi-language-patterns",
        "date": "2026-02-03",
        "tags": ['Voice AI', 'ElevenLabs', 'Multi-Language', 'Bhashini'],
        "audience": "Engineering",
        "excerpt": "A rider asks the bike a question in Marathi, Hindi, or English. The voice stack has to do ASR, intent classification, dispatch to a service tool, generate a response, TTS — all under 3 seconds. Notes from the proof-of-concept.",
    },
    "auto-126-webauthn-passkeys-ed25519-go.md": {
        "slug": "webauthn-passkeys-ed25519-go",
        "date": "2026-03-03",
        "tags": ['Go', 'WebAuthn', 'Passkeys', 'Security', 'Stdlib'],
        "audience": "Engineering",
        "excerpt": "Passkeys are FIDO2; FIDO2 is the spec; Ed25519 is the signature algorithm. The full registration + assertion flow in 200 lines of stdlib Go.",
    },
    "auto-127-why-go-for-agentic-ai.md": {
        "slug": "why-go-for-agentic-ai",
        "date": "2026-04-17",
        "tags": ['Go', 'Multi-Agent AI', 'Architecture'],
        "audience": "Engineering",
        "excerpt": "Stdlib over libraries, single binary over framework, fail-closed defaults over forgiveness. The boring-on-purpose case for choosing Go to ship a multi-agent system into a regulated environment.",
    },
    "auto-128-workload-identity-federation-azure-gcp-migration.md": {
        "slug": "workload-identity-federation-azure-gcp-migration",
        "date": "2026-02-06",
        "tags": ['Azure', 'GCP', 'Workload Identity Federation', 'Migration'],
        "audience": "Engineering",
        "excerpt": "Moving a workload from Azure to GCP while it continues to authenticate against on-prem Azure AD (Entra ID). Federation lets the GCP workload assume a GCP service account based on its Azure identity.",
    },
    # --- June 2026: MAF series + security articles ---
    "june-zero-trust-for-ai-agents.html": {
        "slug": "zero-trust-for-ai-agents",
        "date": "2026-06-07",
        "tags": ['Zero Trust', 'AI Agents', 'Security', 'Enterprise AI'],
        "audience": "Engineering",
        "excerpt": "Agents can be manipulated into misusing permissions they legitimately hold — nothing 'unauthorized' ever hits your logs. A tiered Zero Trust framework for AI agents, with the test that reframes every control: impossible vs. tedious.",
    },
    "june-using-llms-to-secure-source-code.html": {
        "slug": "using-llms-to-secure-source-code",
        "date": "2026-06-07",
        "tags": ['AppSec', 'AI Agents', 'DevSecOps', 'Security'],
        "audience": "Engineering",
        "excerpt": "AI can now find vulnerabilities faster than the world can fix them. A six-step find-and-fix loop for using LLMs to secure source code — and why the verification bottleneck is the real problem.",
    },
    "june-maf-reference-architecture-overview.html": {
        "slug": "maf-reference-architecture-overview",
        "date": "2026-06-09",
        "tags": ['Multi-Agent', 'MAF', 'Architecture', 'Python'],
        "audience": "Engineering",
        "excerpt": "Microsoft published a 12-chapter reference architecture for multi-agent systems and a separate framework (MAF) to build them. Here is what the 102 Python files actually contain and how they map to the chapters.",
    },
    "june-maf-four-orchestration-patterns.html": {
        "slug": "maf-four-orchestration-patterns",
        "date": "2026-06-10",
        "tags": ['MAF', 'Workflows', 'Orchestration', 'Python'],
        "audience": "Engineering",
        "excerpt": "Sequential, Concurrent, Handoff, and Custom WorkflowBuilder. Four shapes the Microsoft Agent Framework ships out of the box, when to pick each, and the gotchas that cost me a day.",
    },
    "june-maf-five-patterns-group-chat-magentic.html": {
        "slug": "maf-five-patterns-group-chat-magentic",
        "date": "2026-06-11",
        "tags": ['MAF', 'Workflows', 'Orchestration', 'Magentic'],
        "audience": "Engineering",
        "excerpt": "The first ten posts treated MAF as having four orchestration patterns. The official docs say five. Here are the two I missed — Group Chat and Magentic — and why they matter.",
    },
    "june-maf-ollama-as-default.html": {
        "slug": "maf-ollama-as-default",
        "date": "2026-06-12",
        "tags": ['MAF', 'Ollama', 'Local AI', 'Developer Experience'],
        "audience": "Engineering",
        "excerpt": "PROVIDER=ollama, granite4.1:3b, zero API keys, no Azure account. How to make a multi-agent project that demonstrates enterprise patterns without requiring enterprise infrastructure.",
    },
    "june-maf-agent-registry-convention.html": {
        "slug": "maf-agent-registry-convention",
        "date": "2026-06-13",
        "tags": ['MAF', 'Architecture', 'Python', 'Registry'],
        "audience": "Engineering",
        "excerpt": "The Microsoft Agent Framework deliberately does not ship an agent registry. Here is why that is the right call, and what to build as a project-local convention when you need one.",
    },
    "june-maf-memory-done-right.html": {
        "slug": "maf-memory-done-right",
        "date": "2026-06-14",
        "tags": ['MAF', 'Memory', 'Python', 'Architecture'],
        "audience": "Engineering",
        "excerpt": "AgentSession is short-term memory. MemoryContextProvider + MemoryFileStore is long-term memory. Mem0 is long-term memory for serious workloads. The boundary that matters and how to implement each.",
    },
    "june-maf-a2a-workflow-is-broker.html": {
        "slug": "maf-a2a-workflow-is-broker",
        "date": "2026-06-15",
        "tags": ['MAF', 'A2A', 'Communication', 'Architecture'],
        "audience": "Engineering",
        "excerpt": "The reference architecture distinguishes request-based and message-driven agent communication. For in-process orchestration, the workflow IS the broker — and A2A is just the wire format.",
    },
    "june-maf-observability-traces-metrics.html": {
        "slug": "maf-observability-traces-metrics",
        "date": "2026-06-16",
        "tags": ['MAF', 'Observability', 'OpenTelemetry', 'Grafana'],
        "audience": "Engineering",
        "excerpt": "OpenTelemetry through MAF's configure_otel_providers, custom workflow spans, custom metrics for runs/duration/agent selection, Jaeger + Prometheus + Grafana wiring, and the set-once latch gotcha.",
    },
    "june-maf-multi-turn-evals-first-principles.html": {
        "slug": "maf-multi-turn-evals-first-principles",
        "date": "2026-06-17",
        "tags": ['MAF', 'Evaluation', 'LLM-as-Judge', 'Python'],
        "audience": "Engineering",
        "excerpt": "Single-turn evals check one decision. Multi-turn evals check the whole trajectory. A Python harness with three evaluators, an offline test suite, and the judge prompt that actually works.",
    },
    "june-maf-refactor-to-native-packages.html": {
        "slug": "maf-refactor-to-native-packages",
        "date": "2026-06-18",
        "tags": ['MAF', 'Refactor', 'Engineering'],
        "audience": "Engineering",
        "excerpt": "I built memory, communication, security, governance, and evals from scratch first. Then I deleted most of it and used the MAF-native packages. Here is the audit table and what survived.",
    },
    "june-maf-governance-with-agt.html": {
        "slug": "maf-governance-with-agt",
        "date": "2026-06-19",
        "tags": ['MAF', 'Governance', 'AGT', 'OWASP', 'Security'],
        "audience": "Engineering",
        "excerpt": "OWASP Agentic Top 10 coverage with YAML policy files, two API surfaces, and a metric bridge that shows policy denials in Grafana.",
    },
    "june-ai-driven-observability-trustworthy-agents.html": {
        "slug": "ai-driven-observability-trustworthy-agents",
        "date": "2026-06-20",
        "tags": ['Observability', 'Agentic AI', 'LLM-as-Judge', 'Responsible AI', 'AI Governance'],
        "audience": "Engineering",
        "excerpt": "Agents return a clean 200 OK and still be wrong, unsafe, or expensive. Why agentic AI needs a new observability layer — LLM-as-judge, safety metrics, and the four lifecycle stages.",
    },
}

# Project metadata (slug → name). Posts with "project" in their meta
# use this to render a back-link breadcrumb.
PROJECT_META = {}

# Post popularity ranking (1-10 scale, 10 = most popular)
# Used to generate "popular posts" section on homepage
POST_POPULARITY = {
    "adk-to-maf-migration-why": 10,         # Featured, core content, most recent
    "adk-to-maf-lessons": 9,                # Featured case study
    "hipaa-as-go-interfaces": 8,            # Compliance critical content
    "postgres-rls-hipaa": 7,                # Database security fundamentals
    "bench-42-to-85": 7,                    # Performance improvements
    "mara-five-interfaces": 6,              # Architecture pattern
    "audit-log-design": 6,                  # Governance + compliance
    "cures-act-as-code": 5,                 # Regulatory requirements
    "fallback-is-the-contract": 5,          # Reliability patterns
    "hl7v2-still-matters": 4,               # Legacy integration
    "gke-ai-infra-medical-multiagent": 4,   # Cloud infrastructure
    "aigp-reference-implementation": 3,     # Certification prep
}

# ---------------------------------------------------------------------------
# Theme — CSS aligned with the site's index.html design tokens
# ---------------------------------------------------------------------------

POST_CSS = """
:root {
  --bg: #ffffff;
  --bg-elev: #f7f8fa;
  --bg-card: #ffffff;
  --text: #1a1a1a;
  --text-dim: #444;
  --text-muted: #6b6b6b;
  --border: #e5e7eb;
  --accent: #1a73e8;
  --accent-hover: #1557b0;
  --tag-bg: #eef3fb;
  --tag-text: #1557b0;
  --code-bg: #f3f4f6;
  --code-border: #e1e4e8;
  --shadow: 0 1px 3px rgba(0,0,0,0.05), 0 4px 12px rgba(0,0,0,0.04);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117;
    --bg-elev: #161b22;
    --bg-card: #161b22;
    --text: #e6edf3;
    --text-dim: #c4ccd5;
    --text-muted: #7d8590;
    --border: #30363d;
    --accent: #58a6ff;
    --accent-hover: #79b8ff;
    --tag-bg: #1e2d4a;
    --tag-text: #79b8ff;
    --code-bg: #1e242c;
    --code-border: #2d333b;
    --shadow: 0 1px 3px rgba(0,0,0,0.3), 0 4px 12px rgba(0,0,0,0.2);
  }
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.65;
  color: var(--text);
  background: var(--bg);
  -webkit-font-smoothing: antialiased;
  font-size: 16px;
}
a { color: var(--accent); text-decoration: none; transition: color 0.15s; }
a:hover { color: var(--accent-hover); text-decoration: underline; }

nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255,255,255,0.85);
  backdrop-filter: saturate(180%) blur(10px);
  -webkit-backdrop-filter: saturate(180%) blur(10px);
  border-bottom: 1px solid var(--border);
}
@media (prefers-color-scheme: dark) {
  nav { background: rgba(13,17,23,0.85); }
}
.nav-container {
  max-width: 980px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}
.nav-brand {
  font-weight: 700;
  font-size: 16px;
  color: var(--text);
  letter-spacing: -0.01em;
}
.nav-brand:hover { text-decoration: none; color: var(--text); }
.nav-links {
  display: flex;
  gap: 22px;
  list-style: none;
  font-size: 14px;
  font-weight: 500;
}
.nav-links a { color: var(--text-dim); }
.nav-links a:hover { color: var(--accent); text-decoration: none; }
.nav-links a.active { color: var(--accent); }
@media (max-width: 640px) {
  .nav-container { padding: 12px 18px; }
  .nav-links { gap: 14px; }
  .nav-links li:nth-child(n+4) { display: none; }
}

main {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 24px;
}

article header {
  padding: 64px 0 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 40px;
}
article h1 {
  font-size: clamp(1.7rem, 4vw, 2.4rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 14px;
}
.post-subtitle {
  font-size: 1.05rem;
  color: var(--text-dim);
  font-style: italic;
  margin-bottom: 20px;
}
.post-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 14px;
}
.post-meta time { font-weight: 500; }
.post-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag {
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--tag-bg);
  color: var(--tag-text);
}

article h2 {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  margin-top: 48px;
  margin-bottom: 16px;
  color: var(--text);
}
article h3 {
  font-size: 1.18rem;
  font-weight: 700;
  margin-top: 32px;
  margin-bottom: 10px;
  color: var(--text);
}
article h4 {
  font-size: 1rem;
  font-weight: 700;
  margin-top: 24px;
  margin-bottom: 8px;
  color: var(--text);
}

article p {
  margin: 0 0 18px;
  color: var(--text-dim);
}
article strong { color: var(--text); font-weight: 600; }
article em { font-style: italic; }
article ul, article ol {
  margin: 0 0 20px;
  padding-left: 24px;
  color: var(--text-dim);
}
article li { margin-bottom: 6px; }
article blockquote {
  border-left: 3px solid var(--accent);
  background: var(--bg-elev);
  padding: 12px 18px;
  margin: 0 0 20px;
  color: var(--text-dim);
  font-style: italic;
  border-radius: 0 6px 6px 0;
}
article blockquote p:last-child { margin-bottom: 0; }
article hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 36px 0;
}

article code {
  font-family: "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.88em;
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 4px;
  padding: 1px 6px;
  color: var(--text);
}
article pre {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  padding: 16px 18px;
  overflow-x: auto;
  margin: 0 0 20px;
  line-height: 1.55;
  font-size: 13.5px;
}
article pre code {
  background: none;
  border: none;
  padding: 0;
  font-size: inherit;
  color: var(--text);
}

article table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 22px;
  font-size: 0.93rem;
}
article th, article td {
  text-align: left;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
article th {
  background: var(--bg-elev);
  font-weight: 700;
  color: var(--text);
}
article td { color: var(--text-dim); }
article tr:hover td { background: var(--bg-elev); }

article img { max-width: 100%; height: auto; border-radius: 8px; }

.post-footer {
  padding: 36px 0;
  border-top: 1px solid var(--border);
  margin-top: 48px;
  color: var(--text-muted);
  font-size: 14px;
}
.post-footer a { color: var(--accent); }
.post-footer .footer-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

footer.site-footer {
  text-align: center;
  padding: 32px 24px;
  color: var(--text-muted);
  font-size: 13px;
  border-top: 1px solid var(--border);
  margin-top: 48px;
}
footer.site-footer a { color: var(--text-muted); }

.post-citations {
  margin: 56px 0 0;
  padding: 28px 0;
  border-top: 2px solid var(--accent);
  border-bottom: 1px solid var(--border);
}
.post-citations h3 {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--text);
}
.citation-item {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}
.citation-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.citation-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.citation-title a { color: var(--accent); }
.citation-title a:hover { color: var(--accent-hover); }
.citation-context {
  font-size: 0.9rem;
  color: var(--text-muted);
  font-style: italic;
}

.series-breadcrumb {
  background: var(--bg-elev);
  border-left: 3px solid var(--accent);
  padding: 12px 16px;
  margin: 0 0 20px;
  border-radius: 0 4px 4px 0;
  font-size: 0.9rem;
}
.series-label {
  font-weight: 600;
  color: var(--accent);
  display: block;
  margin-bottom: 4px;
}
.series-title {
  color: var(--text-dim);
  font-size: 0.95rem;
}
.series-nav {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  flex-wrap: wrap;
}
.series-nav a {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--accent);
}
.series-nav a:hover { color: var(--accent-hover); }
.series-prev { text-align: left; }
.series-next { text-align: right; margin-left: auto; }

.project-breadcrumb {
  background: var(--bg-elev);
  border-left: 3px solid var(--accent);
  padding: 12px 16px;
  margin: 0 0 20px;
  border-radius: 0 4px 4px 0;
  font-size: 0.9rem;
}
.project-breadcrumb a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
}
.project-breadcrumb a:hover {
  text-decoration: underline;
}

.related-posts {
  margin: 40px 0;
  padding: 20px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.related-posts h3 {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--text);
}
.related-posts ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.related-posts li {
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.related-posts li:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.related-posts a {
  color: var(--accent);
  flex: 1;
}
.related-posts a:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}
.related-date {
  font-size: 0.85rem;
  color: var(--text-muted);
  white-space: nowrap;
}

::selection { background: var(--accent); color: white; }
"""

# ---------------------------------------------------------------------------
# Shared CSS components (used across index, tag, archive pages)
# ---------------------------------------------------------------------------

BLOG_LAYOUT_CSS = """
main.blog-index {
  max-width: 880px;
  padding-top: 32px;
  padding-bottom: 32px;
}

.blog-hero {
  padding: 56px 0 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 36px;
}
.blog-hero h1 {
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 14px;
}
.blog-hero p {
  font-size: 1.05rem;
  color: var(--text-dim);
  max-width: 640px;
}
"""

CARD_CSS = """
.post-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.post-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px 28px;
  transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s;
}
.post-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
  border-color: var(--accent);
}
.post-card-meta {
  display: flex;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 8px;
  align-items: center;
}
.post-card-title {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.25;
  margin: 0 0 8px;
}
.post-card-title a { color: var(--text); }
.post-card-title a:hover { color: var(--accent); text-decoration: none; }
.post-card-subtitle {
  font-size: 0.97rem;
  font-style: italic;
  color: var(--text-dim);
  margin-bottom: 8px;
}
.post-card-excerpt {
  font-size: 0.95rem;
  color: var(--text-dim);
  margin-bottom: 14px;
}
"""

TAG_CLOUD_CSS = """
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 24px 0 32px;
}
.tag-cloud-item {
  display: inline-block;
  padding: 8px 14px;
  background: var(--bg-elev);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.15s;
}
.tag-cloud-item:hover {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
  text-decoration: none;
}
"""

PAGINATION_CSS = """
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-top: 40px;
  flex-wrap: wrap;
  font-variant-numeric: tabular-nums;
}
.pagination a, .pagination span {
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-dim);
  background: var(--bg-card);
  text-decoration: none;
  transition: all 0.15s;
  min-width: 40px;
  text-align: center;
}
.pagination a:hover { border-color: var(--accent); color: var(--accent); text-decoration: none; }
.pagination .current { background: var(--accent); color: white; border-color: var(--accent); font-weight: 600; }
.pagination .disabled { color: var(--text-muted); background: var(--bg-elev); cursor: not-allowed; }
.pagination .ellipsis { border: none; background: transparent; color: var(--text-muted); padding: 8px 4px; }
"""


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

NAV_HTML = """<nav>
  <div class="nav-container">
    <a href="/" class="nav-brand">Pratik Dhanave</a>
    <ul class="nav-links">
      <li><a href="/about/">About</a></li>
      <li><a href="/projects/">Projects</a></li>
      <li><a href="/open-source/">Open Source</a></li>
      <li><a href="/google-cloud-next/">GCN Speaker</a></li>
      <li><a href="/mentoring/">Mentoring</a></li>
      <li><a href="/gsoc/">GSoC</a></li>
      <li><a href="/resume/">Resume</a></li>
      <li><a href="/certifications/">Certifications</a></li>
      <li><a href="/gallery/">Gallery</a></li>
      <li><a href="/featured/">Featured</a></li>
      <li><a href="/blog/" class="active">Blog</a></li>
      <li><a href="/#contact">Contact</a></li>
    </ul>
  </div>
</nav>"""


SITE_FOOTER = """<footer class="site-footer">
  <p>© {year} Pratik Dhanave · <a href="https://github.com/PratikDhanave" target="_blank" rel="noopener noreferrer">GitHub</a> · <a href="https://www.linkedin.com/in/pratikdhanave/" target="_blank" rel="noopener noreferrer">LinkedIn</a> · <a href="tel:+917276469649">+91 7276469649</a> · <a href="/thank-you/">Acknowledgments</a></p>
</footer>""".format(year=datetime.now().year)


def render_post_html(meta, title, subtitle, body_html, all_posts=None):
    """Wrap rendered markdown body in the post template."""
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in meta["tags"])
    date_iso = meta["date"]
    date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%B %d, %Y")
    description = meta["excerpt"]
    canonical = f"https://pratikdhanave.com/blog/posts/{meta['slug']}.html"

    # Escape for safe embedding in HTML attributes and JSON-LD
    title_html = _html_escape(title, quote=True)
    desc_html = _html_escape(description, quote=True)
    title_json = _json.dumps(title)[1:-1]   # strip outer quotes
    desc_json = _json.dumps(description)[1:-1]

    # Calculate read time
    read_time = calculate_read_time(body_html)
    read_time_text = f"{read_time} min read"

    # Render series breadcrumbs with prev/next navigation if present
    series_html = ""
    if "series" in meta and meta.get("series"):
        series_name = meta["series"]
        position = meta.get("series_position", 0)
        total = meta.get("series_total", 0)

        # Find prev/next posts in the same series
        series_nav = ""
        if all_posts:
            series_posts = sorted(
                [p for p in all_posts if p["meta"].get("series") == series_name],
                key=lambda p: p["meta"].get("series_position", 0)
            )
            nav_items = []
            for sp in series_posts:
                sp_pos = sp["meta"].get("series_position", 0)
                if sp_pos == position - 1:
                    nav_items.insert(0, f'<a href="/blog/posts/{sp["meta"]["slug"]}.html" class="series-prev">&larr; Part {sp_pos}: {sp["title"]}</a>')
                elif sp_pos == position + 1:
                    nav_items.append(f'<a href="/blog/posts/{sp["meta"]["slug"]}.html" class="series-next">Part {sp_pos}: {sp["title"]} &rarr;</a>')
            if nav_items:
                series_nav = f'<div class="series-nav">{chr(10).join(nav_items)}</div>'

        series_html = f"""  <div class="series-breadcrumb">
    <span class="series-label">Part {position} of {total}</span>
    <span class="series-title">{series_name}</span>
    {series_nav}
  </div>"""

    # Render project back-link if present
    project_html = ""
    if "project" in meta and meta.get("project"):
        project_slug = meta["project"]
        project_name = PROJECT_META.get(project_slug, {}).get("name", project_slug)
        project_url = f"/projects/{project_slug}/"
        project_html = f"""  <div class="project-breadcrumb">
    <span>Part of <a href="{project_url}"><strong>{project_name}</strong></a> →</span>
  </div>"""

    # Render related posts if available
    related_html = ""
    if all_posts and len(all_posts) > 1:
        related_posts = find_related_posts(meta["slug"], all_posts, meta["tags"], limit=3)
        if related_posts:
            related_items = []
            for post in related_posts:
                post_date = datetime.strptime(post["meta"]["date"], "%Y-%m-%d").strftime("%b %d")
                related_items.append(f"""    <li>
      <a href="/blog/posts/{post['meta']['slug']}.html">{post['title']}</a>
      <span class="related-date">{post_date}</span>
    </li>""")
            related_html = f"""
  <aside class="related-posts">
    <h3>Related Reading</h3>
    <ul>
{chr(10).join(related_items)}
    </ul>
  </aside>"""

    # Render citations section if present
    citations_html = ""
    if "citations" in meta and meta["citations"]:
        citations_items = []
        for citation in meta["citations"]:
            citations_items.append(f"""    <div class="citation-item">
      <div class="citation-title"><a href="{citation['url']}" target="_blank" rel="noopener noreferrer">{citation['title']}</a></div>
      <div class="citation-context">{citation['context']}</div>
    </div>""")
        citations_html = f"""
  <section class="post-citations">
    <h3>Sources & References</h3>
{chr(10).join(citations_items)}
  </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_html} — Pratik Dhanave</title>
<meta name="description" content="{desc_html}">
<meta name="author" content="Pratik Dhanave">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">

<meta property="og:title" content="{title_html}">
<meta property="og:description" content="{desc_html}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://pratikdhanave.com/og-default.png">
<meta property="article:published_time" content="{date_iso}T00:00:00+00:00">
{''.join(f'<meta property="article:tag" content="{_html_escape(t, quote=True)}">' + chr(10) for t in meta['tags'])}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title_html}">
<meta name="twitter:description" content="{desc_html}">
<meta name="twitter:image" content="https://pratikdhanave.com/og-default.png">

<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="Pratik Dhanave — Blog" href="https://pratikdhanave.com/blog/feed.xml">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-3BZ8MDPHE1"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-3BZ8MDPHE1');</script>

<style>{POST_CSS}</style>

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "{title_json}",
  "description": "{desc_json}",
  "datePublished": "{date_iso}",
  "dateModified": "{date_iso}",
  "inLanguage": "en",
  "author": {{
    "@type": "Person",
    "name": "Pratik Dhanave",
    "url": "https://pratikdhanave.com"
  }},
  "publisher": {{
    "@type": "Person",
    "name": "Pratik Dhanave",
    "url": "https://pratikdhanave.com"
  }},
  "keywords": "{', '.join(meta['tags'])}",
  "url": "{canonical}",
  "mainEntityOfPage": {{
    "@type": "WebPage",
    "@id": "{canonical}"
  }}
}}
</script>
</head>
<body>

{NAV_HTML}

<main>
<article>
  <header>
    <h1>{title}</h1>
    <p class="post-subtitle">{subtitle}</p>
    <div class="post-meta">
      <time datetime="{date_iso}">{date_human}</time>
      <span>·</span>
      <span>{meta['audience']}</span>
      <span>·</span>
      <span>{read_time_text}</span>
    </div>
    <div class="post-tags">{tags_html}</div>
  </header>

{series_html}

{project_html}

  {body_html}

{related_html}

  <div class="post-footer">
    <div class="footer-row">
      <span>Written by <strong>Pratik Dhanave</strong></span>
      <a href="/blog/">← All posts</a>
    </div>
    <p style="margin-top: 10px; font-size: 13px;">Find me on
      <a href="https://github.com/PratikDhanave" target="_blank" rel="noopener noreferrer">GitHub</a> ·
      <a href="https://www.linkedin.com/in/pratikdhanave/" target="_blank" rel="noopener noreferrer">LinkedIn</a> ·
      <a href="/thank-you/">Acknowledgments</a></p>
  </div>
{citations_html}
</article>
</main>

{SITE_FOOTER}

</body>
</html>
"""


def _render_post_card(p, link_prefix="/blog/posts/"):
    """Render a single post card HTML block."""
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in p["meta"]["tags"])
    date_iso = p["meta"]["date"]
    date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%b %d, %Y")
    read_time = p.get("read_time", 0)
    read_time_html = f'<span>·</span><span>{read_time} min read</span>' if read_time > 0 else ''
    return f"""    <article class="post-card">
      <div class="post-card-meta">
        <time datetime="{date_iso}">{date_human}</time>
        <span>·</span>
        <span>{p["meta"]["audience"]}</span>
        {read_time_html}
      </div>
      <h2 class="post-card-title"><a href="{link_prefix}{p['meta']['slug']}.html">{p['title']}</a></h2>
      <p class="post-card-subtitle">{p['subtitle']}</p>
      <p class="post-card-excerpt">{p['meta']['excerpt']}</p>
      <div class="post-tags">{tags_html}</div>
    </article>"""


def render_index_html(posts, tag_counts=None, popular_posts=None):
    """Build the blog landing page with curated sections."""
    if tag_counts is None:
        tag_counts = {}
    if popular_posts is None:
        popular_posts = []

    total_posts = len(posts)

    # --- Featured posts ---
    featured = [p for p in posts if p["meta"].get("featured", False)]
    featured_slugs = {p["meta"]["slug"] for p in featured}

    featured_html = ""
    if featured:
        cards = []
        for p in featured:
            cards.append(_render_post_card(p))
        featured_html = f"""
<section class="blog-section">
  <h2 class="section-heading">Featured</h2>
  <div class="featured-grid">
{chr(10).join(cards)}
  </div>
</section>"""

    # --- Popular posts ---
    popular_slugs = set()
    popular_html = ""
    if popular_posts:
        # Exclude featured from popular to avoid duplication
        pop_filtered = [p for p in popular_posts if p["meta"]["slug"] not in featured_slugs][:6]
        popular_slugs = {p["meta"]["slug"] for p in pop_filtered}
        if pop_filtered:
            cards = []
            for p in pop_filtered:
                cards.append(_render_post_card(p))
            popular_html = f"""
<section class="blog-section">
  <h2 class="section-heading">Popular</h2>
  <div class="popular-grid">
{chr(10).join(cards)}
  </div>
</section>"""

    # --- Tag cloud (tags with 3+ posts, sorted by count) ---
    tag_cloud_html = ""
    if tag_counts:
        qualified = [(t, c) for t, c in tag_counts.items() if c >= 3]
        qualified.sort(key=lambda x: (-x[1], x[0]))
        if qualified:
            tag_items = "".join(
                f'<a href="/blog/tags/{t.lower().replace(" ", "-")}/"><span class="tag-cloud-item">{t} <span class="tag-count">({c})</span></span></a>'
                for t, c in qualified
            )
            tag_cloud_html = f"""
<section class="blog-section">
  <h2 class="section-heading">Browse by Topic</h2>
  <div class="tag-cloud">
    {tag_items}
  </div>
</section>"""

    # --- Recent posts (12, excluding featured & popular) ---
    shown_slugs = featured_slugs | popular_slugs
    recent = [p for p in posts if p["meta"]["slug"] not in shown_slugs][:12]
    recent_cards = [_render_post_card(p) for p in recent]

    recent_html = f"""
<section class="blog-section">
  <h2 class="section-heading">Recent</h2>
  <div class="post-list">
{chr(10).join(recent_cards)}
  </div>
  <div class="view-all-cta">
    <a href="/blog/archive/">View all {total_posts} posts &rarr;</a>
  </div>
</section>"""

    index_css = POST_CSS + BLOG_LAYOUT_CSS + CARD_CSS + TAG_CLOUD_CSS + """
.blog-section { margin-bottom: 48px; }
.section-heading {
  font-size: 1.1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.featured-grid, .popular-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 18px;
}
@media (max-width: 640px) { .featured-grid, .popular-grid { grid-template-columns: 1fr; } }
.popular-grid .post-card { border-left: 3px solid var(--accent); }
.tag-count { font-size: 11px; color: var(--text-muted); }
.view-all-cta { text-align: center; margin-top: 28px; }
.view-all-cta a {
  display: inline-block;
  padding: 12px 28px;
  background: var(--bg-elev);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.15s;
}
.view-all-cta a:hover {
  border-color: var(--accent);
  color: var(--accent);
  text-decoration: none;
}

/* Search */
.search-box { position: relative; margin-bottom: 32px; }
.search-box input {
  width: 100%; padding: 14px 18px; font-size: 1rem;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; color: var(--text); outline: none;
  font-family: inherit;
}
.search-box input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(26,115,232,0.15); }
.search-results {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 50;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; margin-top: 4px; max-height: 400px; overflow-y: auto;
  box-shadow: var(--shadow);
}
.search-result-item { padding: 14px 18px; border-bottom: 1px solid var(--border); display: block; color: var(--text); }
.search-result-item:last-child { border-bottom: none; }
.search-result-item:hover { background: var(--bg-elev); text-decoration: none; }
.search-result-title { font-weight: 600; color: var(--text); }
.search-result-meta { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog — Pratik Dhanave</title>
<meta name="description" content="Long-form writing on multi-agent AI, medical AI governance, HIPAA-aware architecture, and cloud-native systems. By Pratik Dhanave.">
<meta name="author" content="Pratik Dhanave">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">

<meta property="og:title" content="Pratik Dhanave — Blog">
<meta property="og:description" content="Long-form writing on multi-agent AI, medical AI governance, and HIPAA-aware architecture.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://pratikdhanave.com/blog/">
<meta property="og:image" content="https://pratikdhanave.com/og-default.png">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — Blog">
<meta name="twitter:description" content="Technical articles on multi-agent AI, cloud architecture, security, and production systems. {total_posts} posts and counting.">
<meta name="twitter:image" content="https://pratikdhanave.com/og-default.png">

<link rel="canonical" href="https://pratikdhanave.com/blog/">
<link rel="alternate" type="application/rss+xml" title="Pratik Dhanave — Blog" href="https://pratikdhanave.com/blog/feed.xml">

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{"@type": "ListItem", "position": 1, "name": "Home", "item": "https://pratikdhanave.com"}},
    {{"@type": "ListItem", "position": 2, "name": "Blog", "item": "https://pratikdhanave.com/blog/"}}
  ]
}}
</script>

<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-3BZ8MDPHE1"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-3BZ8MDPHE1');</script>

<style>{index_css}</style>
</head>
<body>

{NAV_HTML}

<main class="blog-index">

<section class="blog-hero">
  <h1>Blog</h1>
  <p>Long-form writing on multi-agent AI, medical AI governance, HIPAA-aware architecture, and cloud-native systems. Most posts grow out of work on <a href="https://github.com/PratikDhanave/bodh">Bodh</a> &mdash; an open-source Go implementation of Microsoft's MAF pattern tuned for medical sequential diagnosis.</p>
</section>

<div class="search-box">
  <input type="search" id="blog-search" placeholder="Search {total_posts} posts..." autocomplete="off">
  <div id="search-results" class="search-results" hidden></div>
</div>

{featured_html}

{popular_html}

{tag_cloud_html}

{recent_html}

</main>

{SITE_FOOTER}

<script>
(function(){{
  var input=document.getElementById('blog-search');
  var box=document.getElementById('search-results');
  var idx=null;
  function mk(tag,cls){{var e=document.createElement(tag);if(cls)e.className=cls;return e}}
  input.addEventListener('focus',function(){{
    if(!idx){{fetch('/blog/search-index.json').then(function(r){{return r.json()}}).then(function(d){{idx=d}}).catch(function(){{}})}}
  }});
  input.addEventListener('input',function(){{
    var q=this.value.toLowerCase().trim();
    if(!q||!idx){{box.hidden=true;return}}
    var m=idx.filter(function(p){{
      return p.t.toLowerCase().indexOf(q)!==-1||p.e.toLowerCase().indexOf(q)!==-1||p.g.some(function(g){{return g.toLowerCase().indexOf(q)!==-1}})
    }}).slice(0,8);
    box.textContent='';
    if(m.length===0){{var d=mk('div','search-result-item');var s=mk('span','search-result-title');s.textContent='No results found.';d.appendChild(s);box.appendChild(d)}}
    else{{m.forEach(function(p){{
      var a=mk('a','search-result-item');a.href=p.u;
      var t=mk('span','search-result-title');t.textContent=p.t;a.appendChild(t);
      var meta=mk('div','search-result-meta');meta.textContent=p.d+(p.r?' \u00b7 '+p.r+' min read':'')+' \u00b7 '+p.g.join(', ');
      a.appendChild(meta);box.appendChild(a)
    }})}}
    box.hidden=false
  }});
  document.addEventListener('click',function(e){{if(!input.contains(e.target)&&!box.contains(e.target))box.hidden=true}})
}})();
</script>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def parse_post(md_path):
    """Read a markdown file and split title / subtitle / body."""
    text = md_path.read_text()

    # Strip the leading H1 from the body so it's not rendered twice.
    h1_match = re.match(r"^#\s+(.+?)\n", text)
    if not h1_match:
        raise ValueError(f"{md_path.name}: no H1 found")
    title = h1_match.group(1).strip()
    body = text[h1_match.end():]

    # The subtitle is the next non-blank line if it's an italic line ("*...*").
    subtitle = ""
    sub_match = re.match(r"\s*\*([^*\n]+?)\*\s*\n", body)
    if sub_match:
        subtitle = sub_match.group(1).strip()
        body = body[sub_match.end():]

    # Skip a leading horizontal rule (most posts start with "---\n" after subtitle).
    body = re.sub(r"^\s*---\s*\n", "", body, count=1)

    return title, subtitle, body


def to_html(md_body):
    """Render markdown to HTML."""
    return markdown.markdown(
        md_body,
        extensions=[
            FencedCodeExtension(),
            TableExtension(),
            SaneListExtension(),
            TocExtension(toc_depth="2-3", marker=""),
            "smarty",
        ],
        output_format="html5",
    )


# ---------------------------------------------------------------------------
# Tag & Archive Generation
# ---------------------------------------------------------------------------

def render_tag_page(tag, posts_with_tag, all_tags, post_count=None):
    """Generate a page for a single tag listing all posts with that tag."""
    if post_count is None:
        post_count = len(posts_with_tag)

    # Phase 0.4: noindex thin tags (<3 posts), index qualifying tags
    if post_count < 3:
        robots_meta = '<meta name="robots" content="noindex, follow">'
    else:
        robots_meta = '<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">'

    # Phase 1.4: CollectionPage schema for tags with 5+ posts
    collection_schema = ""
    if post_count >= 5:
        schema_items = ", ".join(
            f'{{"@type": "BlogPosting", "headline": "{_json.dumps(p["title"])[1:-1]}", "url": "https://pratikdhanave.com/blog/posts/{p["meta"]["slug"]}.html"}}'
            for p in posts_with_tag
        )
        tag_json = _json.dumps(tag)[1:-1]
        collection_schema = f"""
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "{tag_json}",
  "description": "Posts tagged with {tag_json}. By Pratik Dhanave.",
  "url": "https://pratikdhanave.com/blog/tags/{tag.lower().replace(' ', '-')}/",
  "numberOfItems": {post_count},
  "hasPart": [{schema_items}]
}}
</script>"""

    posts_html = []
    for p in posts_with_tag:
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p["meta"]["tags"])
        date_iso = p["meta"]["date"]
        date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%b %d, %Y")
        read_time = p.get("read_time", 0)
        read_time_html = f'<span>·</span><span>{read_time} min read</span>' if read_time > 0 else ''
        posts_html.append(f"""    <article class="post-card">
      <div class="post-card-meta">
        <time datetime="{date_iso}">{date_human}</time>
        <span>·</span>
        <span>{p["meta"]["audience"]}</span>
        {read_time_html}
      </div>
      <h2 class="post-card-title"><a href="/blog/posts/{p['meta']['slug']}.html">{p['title']}</a></h2>
      <p class="post-card-subtitle">{p['subtitle']}</p>
      <p class="post-card-excerpt">{p['meta']['excerpt']}</p>
      <div class="post-tags">{tags_html}</div>
    </article>""")

    tag_cloud_html = "".join(f'<a href="/blog/tags/{t.lower().replace(" ", "-")}/"><span class="tag-cloud-item">{t}</span></a>' for t in sorted(all_tags))

    tag_page_css = POST_CSS + TAG_CLOUD_CSS + BLOG_LAYOUT_CSS + CARD_CSS

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{tag} — Blog — Pratik Dhanave</title>
<meta name="description" content="Posts tagged with {tag}. By Pratik Dhanave.">
<meta name="author" content="Pratik Dhanave">
{robots_meta}

<meta property="og:title" content="Pratik Dhanave — {tag}">
<meta property="og:description" content="Posts tagged with {tag}.">
<meta property="og:type" content="website">
<meta property="og:image" content="https://pratikdhanave.com/og-default.png">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — {tag}">
<meta name="twitter:image" content="https://pratikdhanave.com/og-default.png">

<link rel="canonical" href="https://pratikdhanave.com/blog/tags/{tag.lower().replace(' ', '-')}/">
<link rel="alternate" type="application/rss+xml" title="Pratik Dhanave — Blog" href="https://pratikdhanave.com/blog/feed.xml">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-3BZ8MDPHE1"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-3BZ8MDPHE1');</script>

<style>{tag_page_css}</style>
{collection_schema}
</head>
<body>

{NAV_HTML}

<main class="blog-index">

<section class="blog-hero">
  <h1>#{tag}</h1>
  <p>Posts about {tag.lower()}. <a href="/blog/">← All posts</a></p>
</section>

<section class="tag-cloud">
  {tag_cloud_html}
</section>

<section class="post-list">
{chr(10).join(posts_html)}
</section>

</main>

{SITE_FOOTER}

</body>
</html>
"""


def render_archive_page(year, month=None, posts_with_date=None, all_years=None):
    """Generate archive pages (by year or month)."""
    if month:
        title = f"{datetime(year, month, 1).strftime('%B %Y')}"
        canonical = f"https://pratikdhanave.com/blog/archive/{year}/{month:02d}/"
    else:
        title = str(year)
        canonical = f"https://pratikdhanave.com/blog/archive/{year}/"

    posts_html = []
    if posts_with_date:
        current_month_label = None
        for p in posts_with_date:
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in p["meta"]["tags"])
            date_iso = p["meta"]["date"]
            date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%b %d, %Y")
            read_time = p.get("read_time", 0)
            read_time_html = f'<span>·</span><span>{read_time} min read</span>' if read_time > 0 else ''

            # Add month heading for year pages (Change 8)
            if not month:
                post_month = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%B")
                if post_month != current_month_label:
                    current_month_label = post_month
                    posts_html.append(f'    <h3 class="month-heading">{post_month}</h3>')

            posts_html.append(f"""    <article class="post-card">
      <div class="post-card-meta">
        <time datetime="{date_iso}">{date_human}</time>
        <span>·</span>
        <span>{p["meta"]["audience"]}</span>
        {read_time_html}
      </div>
      <h2 class="post-card-title"><a href="/blog/posts/{p['meta']['slug']}.html">{p['title']}</a></h2>
      <p class="post-card-subtitle">{p['subtitle']}</p>
      <p class="post-card-excerpt">{p['meta']['excerpt']}</p>
      <div class="post-tags">{tags_html}</div>
    </article>""")

    # Year/month nav
    year_nav = "".join(f'<a href="/blog/archive/{y}/" class="tag-cloud-item">{y}</a>' for y in sorted(all_years, reverse=True))

    archive_css = POST_CSS + TAG_CLOUD_CSS + BLOG_LAYOUT_CSS + CARD_CSS + """
.month-heading {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-muted);
  margin: 28px 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.month-heading:first-child { margin-top: 0; }
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Archive — Pratik Dhanave</title>
<meta name="description" content="Blog posts from {title}. By Pratik Dhanave.">
<meta name="author" content="Pratik Dhanave">

<meta property="og:title" content="Pratik Dhanave — {title}">
<meta property="og:description" content="Blog posts from {title}.">
<meta property="og:type" content="website">
<meta property="og:image" content="https://pratikdhanave.com/og-default.png">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — {title}">
<meta name="twitter:image" content="https://pratikdhanave.com/og-default.png">

<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<style>{archive_css}</style>
</head>
<body>

{NAV_HTML}

<main class="blog-index">

<section class="blog-hero">
  <h1>{title}</h1>
  <p>Blog posts from {title}. <a href="/blog/">← All posts</a></p>
</section>

<section class="tag-cloud">
  <strong style="display: block; width: 100%; margin-bottom: 10px;">Years:</strong>
  {year_nav}
</section>

<section class="post-list">
{chr(10).join(posts_html) if posts_html else '<p style="color: var(--text-muted);">No posts found.</p>'}
</section>

</main>

{SITE_FOOTER}

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Paginated Archive
# ---------------------------------------------------------------------------

def _archive_page_url(n):
    """Return canonical URL path for archive page n (page 1 = /blog/archive/)."""
    return "/blog/archive/" if n == 1 else f"/blog/archive/page/{n}/"


def render_paginated_archive(page_posts, page_num, total_pages, total_posts):
    """Generate a paginated archive page."""

    cards = [_render_post_card(p, link_prefix="/blog/posts/") for p in page_posts]

    # Pagination nav
    pages = []
    if page_num > 1:
        pages.append(f'<a href="{_archive_page_url(page_num - 1)}">&larr; Newer</a>')
    else:
        pages.append('<span class="disabled">&larr; Newer</span>')

    for i in range(1, total_pages + 1):
        if i == page_num:
            pages.append(f'<span class="current">{i}</span>')
        elif abs(i - page_num) <= 2 or i == 1 or i == total_pages:
            pages.append(f'<a href="{_archive_page_url(i)}">{i}</a>')
        elif abs(i - page_num) == 3:
            pages.append('<span class="ellipsis">&hellip;</span>')

    if page_num < total_pages:
        pages.append(f'<a href="{_archive_page_url(page_num + 1)}">Older &rarr;</a>')
    else:
        pages.append('<span class="disabled">Older &rarr;</span>')

    pagination_html = f'<nav class="pagination" aria-label="Pagination">{" ".join(pages)}</nav>'

    # SEO: noindex page 2+ to avoid duplicate content
    robots = '<meta name="robots" content="noindex, follow">' if page_num > 1 else '<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">'

    # Canonical and prev/next links for SEO
    canonical = f"https://pratikdhanave.com{_archive_page_url(page_num)}"
    link_tags = ""
    if page_num > 1:
        link_tags += f'\n<link rel="prev" href="https://pratikdhanave.com{_archive_page_url(page_num - 1)}">'
    if page_num < total_pages:
        link_tags += f'\n<link rel="next" href="https://pratikdhanave.com{_archive_page_url(page_num + 1)}">'

    page_css = POST_CSS + BLOG_LAYOUT_CSS + CARD_CSS + PAGINATION_CSS

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archive{f' — Page {page_num}' if page_num > 1 else ''} — Pratik Dhanave</title>
<meta name="description" content="All blog posts by Pratik Dhanave. Page {page_num} of {total_pages} ({total_posts} posts).">
<meta name="author" content="Pratik Dhanave">
{robots}
{link_tags}

<meta property="og:title" content="Archive — Pratik Dhanave">
<meta property="og:type" content="website">
<meta property="og:image" content="https://pratikdhanave.com/og-default.png">

<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-3BZ8MDPHE1"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-3BZ8MDPHE1');</script>

<style>{page_css}</style>
</head>
<body>

{NAV_HTML}

<main class="blog-index">

<section class="blog-hero">
  <h1>Archive</h1>
  <p>{total_posts} posts &middot; Page {page_num} of {total_pages}. <a href="/blog/">← Blog</a></p>
</section>

<section class="post-list">
{chr(10).join(cards)}
</section>

{pagination_html}

</main>

{SITE_FOOTER}

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Popular Posts & Feeds
# ---------------------------------------------------------------------------

def get_popular_posts(all_posts, limit=3):
    """Extract top popular posts ranked by POST_POPULARITY score."""
    posts_with_score = []
    for post in all_posts:
        slug = post["meta"]["slug"]
        score = POST_POPULARITY.get(slug, 0)
        if score > 0:
            posts_with_score.append({
                "slug": slug,
                "score": score,
                "post": post
            })

    # Sort by score descending, return top N
    posts_with_score.sort(key=lambda x: -x["score"])
    return [item["post"] for item in posts_with_score[:limit]]


def render_popular_posts_json(all_posts, limit=3):
    """Generate JSON feed of popular posts for homepage consumption."""
    import json
    popular = get_popular_posts(all_posts, limit)

    items = []
    for post in popular:
        items.append({
            "slug": post["meta"]["slug"],
            "title": post["title"],
            "subtitle": post["subtitle"],
            "excerpt": post["meta"].get("excerpt", ""),
            "date": post["meta"]["date"],
            "audience": post["meta"].get("audience", ""),
            "tags": post["meta"].get("tags", []),
            "url": f"/blog/posts/{post['meta']['slug']}.html"
        })

    return json.dumps({"popular_posts": items}, indent=2)


def render_search_index(all_posts):
    """Generate lightweight JSON search index for client-side search."""
    import json
    index = []
    for p in all_posts:
        index.append({
            "t": p["title"],
            "e": p["meta"].get("excerpt", ""),
            "u": f"/blog/posts/{p['meta']['slug']}.html",
            "d": p["meta"]["date"],
            "g": p["meta"].get("tags", []),
            "r": p.get("read_time", 0),
        })
    return json.dumps(index, separators=(',', ':'))


def render_rss_feed(posts, limit=20):
    """Generate RSS 2.0 XML feed of recent blog posts."""
    from xml.sax.saxutils import escape
    items = []
    for p in posts[:limit]:
        pub_date = datetime.strptime(p["meta"]["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")
        url = f"https://pratikdhanave.com/blog/posts/{p['meta']['slug']}.html"
        categories = "".join(f"      <category>{escape(t)}</category>\n" for t in p["meta"]["tags"])
        items.append(f"""    <item>
      <title>{escape(p['title'])}</title>
      <link>{url}</link>
      <guid isPermaLink="true">{url}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{escape(p['meta'].get('excerpt', ''))}</description>
{categories}    </item>""")

    build_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Pratik Dhanave — Blog</title>
    <link>https://pratikdhanave.com/blog/</link>
    <description>Long-form writing on multi-agent AI, medical AI governance, HIPAA-aware architecture, and cloud-native systems.</description>
    <language>en</language>
    <lastBuildDate>{build_date}</lastBuildDate>
    <atom:link href="https://pratikdhanave.com/blog/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def main():
    if not SRC_DIR.exists():
        print(f"ERROR: source dir not found at {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    # First pass: collect all posts
    rendered = []
    posts_data = {}  # Keep body_html for each post
    for filename, meta in POST_META.items():
        md_path = SRC_DIR / filename
        if md_path.exists():
            title, subtitle, body_md = parse_post(md_path)
            body_html = to_html(body_md)
            read_time = calculate_read_time(body_html)
            rendered.append({"meta": meta, "title": title, "subtitle": subtitle, "read_time": read_time})
            posts_data[meta["slug"]] = {"body_html": body_html, "title": title, "subtitle": subtitle}
        else:
            # HTML-only post (already in blog/posts/, no source .md)
            html_path = POSTS_DIR / f"{meta['slug']}.html"
            if html_path.exists():
                from html import unescape as _html_unescape
                raw = html_path.read_text(errors="ignore")
                m = re.search(r"<title>([^<]+)</title>", raw, re.I)
                post_title = _html_unescape(m.group(1)).replace(" — Pratik Dhanave", "").strip() if m else meta["slug"]
                read_time = calculate_read_time(raw)
                rendered.append({"meta": meta, "title": post_title, "subtitle": "", "read_time": read_time})
            else:
                print(f"SKIP missing: {md_path} and {html_path}", file=sys.stderr)

    # Sort newest first by date (for index).
    rendered.sort(key=lambda p: p["meta"]["date"], reverse=True)

    # Second pass: render posts with access to all posts for related content
    for post in rendered:
        meta = post["meta"]
        if meta["slug"] not in posts_data:
            continue  # HTML-only post, already in blog/posts/
        title = post["title"]
        subtitle = post["subtitle"]
        body_html = posts_data[meta["slug"]]["body_html"]
        html = render_post_html(meta, title, subtitle, body_html, all_posts=rendered)

        out_path = POSTS_DIR / f"{meta['slug']}.html"
        out_path.write_text(html)
        print(f"  wrote {out_path.relative_to(SITE_ROOT)}")

    # Compute tag counts for tag cloud
    tag_counts = {}
    tag_posts = {}
    all_tags = set()
    for p in rendered:
        for tag in p["meta"]["tags"]:
            all_tags.add(tag)
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            tag_key = tag.lower().replace(" ", "-")
            if tag_key not in tag_posts:
                tag_posts[tag_key] = []
            tag_posts[tag_key].append(p)

    # Get popular posts for index
    popular = get_popular_posts(rendered, limit=6)

    # Generate main blog index
    INDEX_PATH.write_text(render_index_html(rendered, tag_counts, popular))
    print(f"  wrote {INDEX_PATH.relative_to(SITE_ROOT)}")

    # Generate search index JSON
    search_index = render_search_index(rendered)
    search_path = SITE_ROOT / "blog" / "search-index.json"
    search_path.write_text(search_index)
    print(f"  wrote {search_path.relative_to(SITE_ROOT)}")

    # Generate popular posts JSON feed
    popular_posts_json = render_popular_posts_json(rendered, limit=3)
    popular_posts_path = SITE_ROOT / "blog" / "popular-posts.json"
    popular_posts_path.write_text(popular_posts_json)
    print(f"  wrote {popular_posts_path.relative_to(SITE_ROOT)}")

    # Generate RSS feed
    rss_xml = render_rss_feed(rendered, limit=50)
    rss_path = SITE_ROOT / "blog" / "feed.xml"
    rss_path.write_text(rss_xml)
    print(f"  wrote {rss_path.relative_to(SITE_ROOT)}")

    tags_dir = SITE_ROOT / "blog" / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)

    for tag_key, posts_with_tag in tag_posts.items():
        tag_dir = tags_dir / tag_key
        tag_dir.mkdir(parents=True, exist_ok=True)
        tag_file = tag_dir / "index.html"
        tag_name = posts_with_tag[0]["meta"]["tags"][[t.lower().replace(" ", "-") for t in posts_with_tag[0]["meta"]["tags"]].index(tag_key)]
        tag_file.write_text(render_tag_page(tag_name, posts_with_tag, all_tags, post_count=len(posts_with_tag)))
        print(f"  wrote {tag_file.relative_to(SITE_ROOT)}")

    # Generate archive pages
    archive_by_date = {}
    all_years = set()
    for p in rendered:
        date_obj = datetime.strptime(p["meta"]["date"], "%Y-%m-%d")
        year = date_obj.year
        month = date_obj.month
        all_years.add(year)

        if year not in archive_by_date:
            archive_by_date[year] = {}
        if month not in archive_by_date[year]:
            archive_by_date[year][month] = []
        archive_by_date[year][month].append(p)

    archive_dir = SITE_ROOT / "blog" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Archive year pages
    for year in sorted(archive_by_date.keys(), reverse=True):
        year_dir = archive_dir / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        year_file = year_dir / "index.html"

        posts_in_year = []
        for month in sorted(archive_by_date[year].keys(), reverse=True):
            posts_in_year.extend(archive_by_date[year][month])

        year_file.write_text(render_archive_page(year, None, posts_in_year, all_years))
        print(f"  wrote {year_file.relative_to(SITE_ROOT)}")

        # Archive month pages
        for month in sorted(archive_by_date[year].keys()):
            month_dir = year_dir / f"{month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)
            month_file = month_dir / "index.html"
            month_file.write_text(render_archive_page(year, month, archive_by_date[year][month], all_years))
            print(f"  wrote {month_file.relative_to(SITE_ROOT)}")

    # Generate paginated archive
    posts_per_page = 12
    total_pages = math.ceil(len(rendered) / posts_per_page)
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * posts_per_page
        page_posts = rendered[start:start + posts_per_page]
        page_html = render_paginated_archive(page_posts, page_num, total_pages, len(rendered))

        if page_num == 1:
            # Page 1 lives at /blog/archive/ (canonical entry point)
            (archive_dir / "index.html").write_text(page_html)
            print(f"  wrote {(archive_dir / 'index.html').relative_to(SITE_ROOT)}")
        else:
            # Pages 2+ live at /blog/archive/page/N/
            page_dir = archive_dir / "page" / str(page_num)
            page_dir.mkdir(parents=True, exist_ok=True)
            (page_dir / "index.html").write_text(page_html)
            print(f"  wrote {(page_dir / 'index.html').relative_to(SITE_ROOT)}")

    print(f"\nBuilt {len(rendered)} posts + {len(tag_posts)} tag pages + {len(archive_by_date)} year archives + {total_pages} archive pages.")


INDEXNOW_KEY  = "b6b1ed31366b46ad8a801ad9bc6e5613"
INDEXNOW_HOST = "https://pratikdhanave.com"
INDEXNOW_API  = "https://api.indexnow.org/indexnow"


def indexnow_ping(new_urls: list[str]) -> None:
    """POST newly published URLs to IndexNow (Bing + Yandex + more).

    Only fires when there are URLs to submit.  Skips silently if the
    network is unavailable (e.g. offline CI runs) — never breaks the build.
    """
    if not new_urls:
        return

    payload = _json.dumps({
        "host":        "pratikdhanave.com",
        "key":         INDEXNOW_KEY,
        "keyLocation": f"{INDEXNOW_HOST}/{INDEXNOW_KEY}.txt",
        "urlList":     new_urls,
    }).encode("utf-8")

    req = urllib.request.Request(
        INDEXNOW_API,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception as exc:
        print(f"  [IndexNow] skipped — {exc}", file=sys.stderr)
        return

    if status in (200, 202):
        print(f"  [IndexNow] ✅ pinged {len(new_urls)} URL(s) → HTTP {status}")
    else:
        print(f"  [IndexNow] ⚠️  unexpected HTTP {status}", file=sys.stderr)


def _new_post_urls() -> list[str]:
    """Return site URLs for blog posts added/modified since the last git commit.

    Compares git index (staged + working tree changes) against HEAD so that
    URLs are collected right after the build writes the HTML but before the
    user commits — matching real-world CI usage where build → commit happens
    in the same pipeline step.

    Falls back to an empty list if git is unavailable.
    """
    try:
        # Files changed vs HEAD (staged or unstaged)
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(SITE_ROOT),
        )
        changed = result.stdout.splitlines()
    except Exception:
        return []

    urls = []
    for path in changed:
        # Only blog post HTML files: blog/posts/<slug>.html
        if path.startswith("blog/posts/") and path.endswith(".html"):
            slug = path[len("blog/posts/"):-len(".html")]
            urls.append(f"{INDEXNOW_HOST}/blog/posts/{slug}.html")
    return urls


if __name__ == "__main__":
    main()
    new_urls = _new_post_urls()
    if new_urls:
        print(f"\nPinging IndexNow for {len(new_urls)} new/updated post(s)...")
        indexnow_ping(new_urls)
