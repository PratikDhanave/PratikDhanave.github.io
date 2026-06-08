#!/usr/bin/env python3
"""
Build script for project showcase pages (Phase 2-3).
Mirrors build_blog.py structure: PROJECT_META dict → render functions → .write_text()

Architecture:
- /projects/ — project gallery (OSS + client grids)
- /projects/<slug>/ — individual project pages (OSS only)
- /projects/client-work/ — client portfolio overview
"""

import re
from pathlib import Path
from datetime import datetime
from build_blog import (
    SITE_ROOT,
    NAV_HTML,
    SITE_FOOTER,
    POST_CSS,
    find_related_posts,
    POST_META,
)

# Project metadata — mirrors POST_META structure
PROJECT_META = {
    "genie": {
        "slug": "genie",
        "kind": "oss",
        "name": "Genie",
        "tagline": "Multi-agent financial assistant on Microsoft MAF",
        "org": "Open Source · c2siorg",
        "status": "active",
        "featured": True,
        "summary": "Go-based multi-agent financial assistant with 15 role-specialized agents, JWT + RBAC, AES-256-GCM encryption, and full OpenTelemetry tracing.",
        "description_html": """<p>Genie is a comprehensive multi-agent financial advisory platform built on Microsoft's Agent Framework (MAF). The system orchestrates 15 role-specialized agents (supervisor, analyzer, forecaster, anomaly_detector, recommender, llm_auditor, and more) to deliver financial insights, risk analysis, and recommendations.</p>
<p>The platform implements enterprise-grade security (JWT + RBAC), transparent encryption (AES-256-GCM envelope), and production observability (full OpenTelemetry tracing). It serves as a reference implementation for multi-agent coordination patterns and agent specialization.</p>""",
        "language": "Go",
        "role": "Author / maintainer",
        "year": "2025–2026",
        "tags": ["Go", "MAF", "Postgres", "OpenTelemetry", "Multi-Agent AI", "Security"],
        "highlights": [
            "15 role-specialized agents with clear separation of concerns",
            "JWT + RBAC authentication, AES-256-GCM envelope encryption",
            "Full OpenTelemetry tracing and production observability",
            "Provider-agnostic design (Ollama, OpenAI, Azure Foundry)",
            "Tool governance with AGT policy enforcement",
        ],
        "metrics": [
            ["15", "specialized agents"],
            ["100%", "OTel-traced"],
            ["3", "deployment targets"],
        ],
        "links": [
            ["Source on GitHub", "https://github.com/c2siorg/genie"],
            ["Documentation", "https://github.com/c2siorg/genie#readme"],
        ],
        "blog_tags": ["MAF", "Multi-Agent AI", "Architecture", "Security", "Governance"],
        "blog_posts": ["/blog/posts/adk-to-maf-migration-why.html"],
        "credits": [
            {
                "name": "Microsoft Agent Framework Team",
                "context": "MAF patterns and SDK documentation",
                "url": "https://learn.microsoft.com/en-us/azure/ai-services/agents/",
            },
            {
                "name": "Ollama Community",
                "context": "Local LLM inference for development and deployment",
                "url": "https://ollama.com/",
            },
            {
                "name": "c2siorg Community",
                "context": "Collaborative open-source development and maintenance",
                "url": "https://github.com/c2siorg",
            },
        ],
    },
    "bodh": {
        "slug": "bodh",
        "kind": "oss",
        "name": "Bodh",
        "tagline": "Medical AI platform with physician panel orchestration",
        "org": "Open Source · Original",
        "status": "active",
        "featured": False,
        "summary": "Virtual physician panel on MAF, inspired by Microsoft's MAI-DxO. FHIR R4 + HL7 v2 aware with role-specialized diagnostic agents.",
        "description_html": """<p>Bodh is an open-source medical AI platform that orchestrates a virtual physician panel on Microsoft's MAF. The system is inspired by Microsoft's <a href="https://microsoft.ai/news/the-path-to-medical-superintelligence/">MAI-DxO</a> and SD-Bench, implementing role-specialized agents for intake, questioning, test planning, diagnostician analysis, and reasoning verification.</p>
<p>The platform is fully aware of healthcare standards (FHIR R4 for structured medical data, HL7 v2 for clinical messaging) and implements cost-aware diagnostic budget enforcement to optimize care delivery while managing expenses.</p>""",
        "language": "Go",
        "role": "Author / maintainer",
        "year": "2025–2026",
        "tags": ["Go", "MAF", "FHIR R4", "HL7 v2", "Medical AI", "Healthcare"],
        "highlights": [
            "Virtual physician panel with 6+ role-specialized diagnostic agents",
            "FHIR R4 and HL7 v2 standards compliance for healthcare interoperability",
            "Cost-aware diagnostic budget enforcement",
            "Inspired by Microsoft's MAI-DxO research",
            "Deployment-ready on Kubernetes with OpenTelemetry observability",
        ],
        "metrics": [
            ["6", "agent specializations"],
            ["FHIR R4", "compliant"],
            ["HL7 v2", "aware"],
        ],
        "links": [
            ["Source on GitHub", "https://github.com/PratikDhanave/bodh"],
        ],
        "blog_tags": ["MAF", "Medical AI", "Architecture", "Healthcare"],
        "blog_posts": [],
        "credits": [
            {
                "name": "Microsoft MAI-DxO Research",
                "context": "Multi-agent diagnostic orchestration patterns",
                "url": "https://microsoft.ai/news/the-path-to-medical-superintelligence/",
            },
            {
                "name": "HL7 FHIR",
                "context": "Healthcare data standards and interoperability",
                "url": "https://www.hl7.org/fhir/",
            },
            {
                "name": "HL7 v2 Messaging",
                "context": "Clinical messaging and legacy system integration",
                "url": "https://www.hl7.org/implement/standards/product_brief.cfm?product_id=186",
            },
        ],
    },
    "harbourbridge": {
        "slug": "harbourbridge",
        "kind": "oss",
        "name": "HarbourBridge",
        "tagline": "Google's Spanner Migration Tool — core contributor",
        "org": "Open Source · Google Cloud",
        "status": "maintained",
        "featured": False,
        "summary": "Core contributor to Google's open-source Spanner migration tool. Built backend APIs, CDC pipelines, and query optimization improving performance by 40–60%.",
        "description_html": """<p>HarbourBridge is Google's open-source tool for migrating legacy relational databases to Cloud Spanner. As a core contributor, I architected and built key components:</p>
<ul>
<li><strong>Intelligent Schema Assistant Backend:</strong> APIs that analyze source schemas and recommend optimal Spanner designs (primary keys, interleaving, indexes).</li>
<li><strong>CDC Pipelines:</strong> Change Data Capture from Datastream through Pub/Sub to Dataflow, enabling zero-downtime migrations.</li>
<li><strong>Query Optimization:</strong> Post-migration query rewriting and performance tuning, delivering 40–60% improvements through PK design, strategic indexing, and table interleaving.</li>
</ul>""",
        "language": "Go",
        "role": "Core contributor",
        "year": "2024–2025",
        "tags": ["Go", "Cloud Spanner", "Datastream", "CDC", "Google Cloud"],
        "highlights": [
            "40–60% post-migration query performance improvement",
            "Change Data Capture pipeline (Datastream → Pub/Sub → Dataflow)",
            "Intelligent Schema Assistant with interleaving recommendations",
            "PK design and indexing optimization strategies",
            "Thousands of successful production migrations",
        ],
        "metrics": [
            ["40–60%", "perf gain"],
            ["Zero-downtime", "CDC"],
            ["10K+", "migrations"],
        ],
        "links": [
            ["Source on GitHub", "https://github.com/GoogleCloudPlatform/spanner-migration-tool"],
            ["Google Cloud Docs", "https://cloud.google.com/spanner/docs/migration"],
        ],
        "blog_tags": ["Cloud Spanner", "Database Migration", "Performance"],
        "blog_posts": [],
        "credits": [
            {
                "name": "Google Cloud Platform",
                "context": "Spanner architecture and migration tooling",
                "url": "https://cloud.google.com/spanner",
            },
            {
                "name": "Cloud Datastream",
                "context": "Change Data Capture infrastructure",
                "url": "https://cloud.google.com/datastream/docs",
            },
            {
                "name": "Apache Beam / Dataflow",
                "context": "Data pipeline orchestration",
                "url": "https://beam.apache.org/",
            },
        ],
    },
    # Client work projects
    "tata-bigquery-finops": {
        "slug": "tata-bigquery-finops",
        "kind": "client",
        "name": "Tata Group — BigQuery FinOps",
        "tagline": "₹100 Cr+ savings, 57% cost reduction",
        "org": "Searce engagement · 2024–2025",
        "status": "completed",
        "featured": False,
        "summary": "Led BigQuery cost optimization for Tata Group — query refactoring, MERGE redesign, capacity transition. Delivered ₹100 Cr+ (~$12M) savings, 57% reduction.",
        "description_html": """<p>Led the comprehensive BigQuery cost optimization engagement for Tata Group, one of India's largest conglomerates. The initiative spanned query refactoring, MERGE operation redesign, and transition to capacity-based slot reservations.</p>
<p><strong>Delivered impact:</strong> ₹100 Cr+ (~$12M USD) in savings with a 57% reduction in data warehouse costs. The engagement was so successful that it was productized into Searce's recurring GCP managed service offering.</p>""",
        "role": "Lead consultant",
        "year": "2024–2025",
        "tags": ["BigQuery", "FinOps", "GCP", "Enterprise", "Cost Optimization"],
        "highlights": [
            "₹100 Cr+ (~$12M) total savings identified and delivered",
            "57% data warehouse cost reduction",
            "Query refactoring and optimization best practices",
            "Capacity-based slot reservation architecture",
            "Productized into recurring managed service offering",
        ],
        "metrics": [
            ["₹100 Cr+", "saved"],
            ["57%", "cost ↓"],
            ["10K+", "queries analyzed"],
        ],
        "links": [
            ["Tata Group", "https://www.tatasteel.com/"],
            ["Google BigQuery Docs", "https://cloud.google.com/bigquery/docs"],
            ["BigQuery Pricing", "https://cloud.google.com/bigquery/pricing"],
        ],
        "blog_tags": ["FinOps", "BigQuery", "GCP", "Cost Optimization"],
        "blog_posts": [],
        "credits": [
            {
                "name": "Google Cloud BigQuery",
                "context": "Cost optimization and capacity planning",
                "url": "https://cloud.google.com/bigquery",
            },
            {
                "name": "FinOps Foundation",
                "context": "Cloud cost optimization best practices",
                "url": "https://www.finops.org/",
            },
        ],
    },
    "globe-transaction-engine": {
        "slug": "globe-transaction-engine",
        "kind": "client",
        "name": "Globe — Telecom/FinTech Transaction Engine",
        "tagline": "30K+ TPS, PCI-aligned, DLQ resilience",
        "org": "Searce client work",
        "status": "completed",
        "featured": False,
        "summary": "30K+ TPS Kubernetes transaction platform for telecom/FinTech. Led 10 engineers, PCI-aligned, idempotent processing, DLQ resilience.",
        "description_html": """<p>Architected and led the engineering of a high-throughput transaction processing platform for Globe, the Philippines' leading telecom operator. The system handles <strong>30,000+ transactions per second</strong> for telecom and FinTech partner integrations.</p>
<p><strong>Key responsibilities:</strong> Team leadership (10 engineers), PCI-DSS compliance architecture, idempotent transaction semantics, sophisticated error-code orchestration with exponential backoff, and Dead Letter Queue (DLQ) resilience for failed transactions.</p>""",
        "role": "Tech lead / architect",
        "year": "Ongoing",
        "tags": ["Go", "Kubernetes", "Kafka", "Pub/Sub", "PCI", "High-throughput"],
        "highlights": [
            "30,000+ transactions per second sustained throughput",
            "PCI-DSS compliance for financial transactions",
            "Idempotent transaction processing",
            "Error-code orchestration with exponential backoff",
            "Dead Letter Queue architecture for failure resilience",
            "10-person international engineering team",
        ],
        "metrics": [
            ["30K+", "TPS"],
            ["100%", "uptime"],
            ["<100ms", "p99 latency"],
        ],
        "links": [
            ["Globe", "https://www.globe.com.ph/"],
            ["Kubernetes", "https://kubernetes.io/"],
        ],
        "blog_tags": ["Kubernetes", "High-Throughput", "Reliability"],
        "blog_posts": [],
        "credits": [
            {
                "name": "Kubernetes",
                "context": "Container orchestration and scaling",
                "url": "https://kubernetes.io/",
            },
            {
                "name": "Apache Kafka",
                "context": "Distributed event streaming",
                "url": "https://kafka.apache.org/",
            },
            {
                "name": "Google Pub/Sub",
                "context": "Message queuing and DLQ patterns",
                "url": "https://cloud.google.com/pubsub/docs",
            },
        ],
    },
    "brownlow-voting": {
        "slug": "brownlow-voting",
        "kind": "client",
        "name": "Brownlow — AFL Voting Platform",
        "tagline": "100K+ votes, 10K+ concurrent, zero-trust security",
        "org": "Searce client work",
        "status": "completed",
        "featured": False,
        "summary": "Zero-trust voting and analytics platform for AFL Brownlow Medal. 100K+ votes, 10K+ concurrent users, Cloud KMS + SCC security.",
        "description_html": """<p>Built a zero-trust voting and analytics platform for the AFL Brownlow Medal — one of Australian sports' most prestigious annual events.</p>
<p><strong>Scale and security:</strong> The platform handled <strong>100K+ votes</strong> with <strong>10K+ concurrent users</strong> during live broadcasts. Security was implemented at the highest level using Cloud KMS for encryption key management and Security Command Center for threat detection and compliance monitoring.</p>
<p><strong>Architecture:</strong> Cloud Run for auto-scaling, GraphQL API for flexible data queries, gRPC for internal services, and comprehensive audit logging for voting integrity.</p>""",
        "role": "Platform architect",
        "year": "2024",
        "tags": ["Go", "GraphQL", "gRPC", "Cloud Run", "Zero-Trust", "Security"],
        "highlights": [
            "100K+ secure votes processed",
            "10K+ concurrent users during live events",
            "Zero-trust security architecture",
            "Cloud KMS encryption for sensitive data",
            "Security Command Center monitoring",
            "Auto-scaling Cloud Run deployment",
        ],
        "metrics": [
            ["100K+", "votes"],
            ["10K+", "concurrent"],
            ["<50ms", "p99 latency"],
        ],
        "links": [
            ["AFL Brownlow", "https://www.afl.com.au/"],
            ["Cloud Run", "https://cloud.google.com/run"],
            ["Cloud KMS", "https://cloud.google.com/kms"],
        ],
        "blog_tags": ["Security", "Cloud Run", "Zero-Trust"],
        "blog_posts": [],
        "credits": [
            {
                "name": "Google Cloud Security",
                "context": "KMS encryption and SCC monitoring",
                "url": "https://cloud.google.com/security",
            },
            {
                "name": "Cloud Run",
                "context": "Serverless containerized deployment",
                "url": "https://cloud.google.com/run",
            },
        ],
    },
    "picnic-social": {
        "slug": "picnic-social",
        "kind": "client",
        "name": "Picnic — Social Network",
        "tagline": "1M+ users, 47% latency reduction, 80%+ test coverage",
        "org": "Searce client work",
        "status": "maintained",
        "featured": False,
        "summary": "1M+ user social platform backend. 47% latency reduction via protobuf contracts. Led international 4-person team, 80%+ test coverage.",
        "description_html": """<p>Built the backend infrastructure for Picnic, a social platform serving <strong>1M+ active users</strong>. The engineering effort focused on performance optimization and reliable service delivery at scale.</p>
<p><strong>Key achievements:</strong></p>
<ul>
<li>Reduced API response latency by <strong>47%</strong> through protobuf contract optimization and service consolidation.</li>
<li>Maintained <strong>80%+ automated test coverage</strong> across service-to-service communication.</li>
<li>Led a remote-first international team of 4 engineers across multiple time zones.</li>
<li>Cloud Spanner for global scale, Prometheus for observability, gRPC for internal APIs.</li>
</ul>""",
        "role": "Lead engineer / team lead",
        "year": "2023–2024",
        "tags": ["Go", "gRPC", "GraphQL", "Cloud Spanner", "Prometheus", "Performance"],
        "highlights": [
            "1M+ users served with sub-100ms p99 latency",
            "47% API latency reduction via optimization",
            "80%+ automated test coverage",
            "Cloud Spanner for global scale and consistency",
            "Remote-first international team of 4",
            "gRPC + GraphQL service architecture",
        ],
        "metrics": [
            ["1M+", "users"],
            ["47%", "latency ↓"],
            ["80%+", "test coverage"],
        ],
        "links": [
            ["Picnic (GitLab)", "https://gitlab.com/picnic-app"],
            ["Cloud Spanner", "https://cloud.google.com/spanner"],
            ["gRPC", "https://grpc.io/"],
        ],
        "blog_tags": ["Performance", "Cloud Spanner", "gRPC"],
        "blog_posts": [],
        "credits": [
            {
                "name": "Cloud Spanner",
                "context": "Globally distributed relational database",
                "url": "https://cloud.google.com/spanner",
            },
            {
                "name": "gRPC",
                "context": "High-performance inter-service communication",
                "url": "https://grpc.io/",
            },
            {
                "name": "Prometheus",
                "context": "Metrics collection and observability",
                "url": "https://prometheus.io/",
            },
        ],
    },
    "bancnet-open-banking": {
        "slug": "bancnet-open-banking",
        "kind": "client",
        "name": "Bancnet — Open Banking Portal",
        "tagline": "ADGM/DIFC/SAMA compliance, 37% latency reduction, RAG VectorDB",
        "org": "Searce client work",
        "status": "completed",
        "featured": False,
        "summary": "High-compliance Open Banking portal for UAE/Saudi Arabia. Consent management, data residency, RAG semantic search. 37% latency reduction.",
        "description_html": """<p>Architected and built a high-compliance Open Banking portal for the Middle East, serving UAE (ADGM/DIFC) and Saudi Arabia (SAMA) markets.</p>
<p><strong>Regulatory requirements:</strong> The platform implements consent management frameworks, enforces data residency requirements, and maintains audit trails for regulatory compliance.</p>
<p><strong>Technical innovation:</strong> Integrated RAG (Retrieval Augmented Generation) with AlloyDB AI as a Vector Database for semantic search over banking schemas and regulations, delivering <strong>37% latency reduction</strong> in schema discovery and query optimization.</p>""",
        "role": "Lead architect",
        "year": "2024",
        "tags": ["Python", "FastAPI", "RAG", "AlloyDB AI", "Open Banking", "Compliance"],
        "highlights": [
            "ADGM, DIFC, and SAMA regulatory compliance",
            "Consent management framework",
            "Data residency enforcement",
            "RAG-powered semantic search with AlloyDB AI",
            "37% latency reduction in schema discovery",
            "Full audit trail for regulatory reporting",
        ],
        "metrics": [
            ["37%", "latency ↓"],
            ["3", "markets"],
            ["SOMA", "compliant"],
        ],
        "links": [
            ["Bancnet", "https://www.bancnet.com.ph/"],
            ["AlloyDB AI", "https://cloud.google.com/alloydb"],
            ["Open Banking Standard", "https://www.openbanking.org.uk/"],
        ],
        "blog_tags": ["Open Banking", "Compliance", "RAG", "AlloyDB"],
        "blog_posts": [],
        "credits": [
            {
                "name": "AlloyDB AI",
                "context": "Vector database for RAG semantic search",
                "url": "https://cloud.google.com/alloydb",
            },
            {
                "name": "Open Banking Standard",
                "context": "API and regulatory framework",
                "url": "https://www.openbanking.org.uk/",
            },
        ],
    },
    "optimus-analyzer": {
        "slug": "optimus-analyzer",
        "kind": "client",
        "name": "Optimus — BigQuery Analyzer",
        "tagline": "Gemini-powered SQL analysis, 57% cost reduction",
        "org": "Searce client work",
        "status": "completed",
        "featured": False,
        "summary": "Gemini-powered BigQuery analyzer detecting SQL anti-patterns and recommending optimizations. Delivered 57% cost reduction (Tata engagement).",
        "description_html": """<p>Built Optimus, an AI-powered BigQuery analyzer that leverages Google's Gemini API to detect SQL anti-patterns and recommend query optimizations.</p>
<p><strong>Analysis scope:</strong> The system automatically detects:</p>
<ul>
<li>Full table scans instead of partition-pruned queries</li>
<li>Inefficient join orders and missing join predicates</li>
<li>Missing partition filters and clustering keys</li>
<li>Redundant aggregations and subquery nesting</li>
</ul>
<p><strong>Impact:</strong> Deployed at scale in the Tata BigQuery FinOps engagement, contributing to the <strong>57% cost reduction</strong> delivered across their data warehouse.</p>""",
        "role": "Lead engineer",
        "year": "2024–2025",
        "tags": ["Python", "Gemini API", "BigQuery", "NL2SQL", "FinOps"],
        "highlights": [
            "Gemini API integration for SQL analysis",
            "NL2SQL for natural language optimization",
            "Detects 10+ SQL anti-patterns",
            "Automated recommendations for optimization",
            "Deployed in Tata BigQuery optimization",
            "57% cost savings achieved",
        ],
        "metrics": [
            ["57%", "cost ↓"],
            ["10+", "anti-patterns"],
            ["100%", "automated"],
        ],
        "links": [
            ["Google Gemini API", "https://ai.google.dev/"],
            ["BigQuery", "https://cloud.google.com/bigquery"],
        ],
        "blog_tags": ["FinOps", "Gemini API", "NL2SQL"],
        "blog_posts": [],
        "credits": [
            {
                "name": "Google Gemini API",
                "context": "LLM-powered code and SQL analysis",
                "url": "https://ai.google.dev/",
            },
            {
                "name": "BigQuery",
                "context": "Data warehouse and query optimization",
                "url": "https://cloud.google.com/bigquery",
            },
        ],
    },
    "kinetic-india-voice": {
        "slug": "kinetic-india-voice",
        "kind": "client",
        "name": "Kinetic India — Voice Assistant for Bikes",
        "tagline": "Multi-language voice AI, ElevenLabs, Gemini dialog",
        "org": "Searce client work",
        "status": "completed",
        "featured": False,
        "summary": "Multi-language conversational voice assistant for two-wheeler riders. Vehicle diagnostics, service booking, ride telemetry. ElevenLabs voice synthesis + Gemini dialog.",
        "description_html": """<p>Built a conversational voice assistant for Kinetic India two-wheeler riders — enabling hands-free interaction with vehicle diagnostics, service booking, and ride telemetry.</p>
<p><strong>Capabilities:</strong></p>
<ul>
<li>Multi-language voice support (Hindi, English, regional languages)</li>
<li>Vehicle diagnostic queries and real-time telemetry</li>
<li>Service appointment booking integration</li>
<li>Ride safety and performance insights</li>
<li>ElevenLabs voice synthesis for natural speech</li>
<li>Gemini-powered dialog management for contextual understanding</li>
</ul>
<p><strong>Impact:</strong> Improved rider engagement and service accessibility for Kinetic's customer base.</p>""",
        "role": "Lead engineer",
        "year": "2024",
        "tags": ["Python", "Voice AI", "ElevenLabs", "Gemini", "Telecom", "IoT"],
        "highlights": [
            "Multi-language voice support",
            "Real-time vehicle telemetry integration",
            "ElevenLabs voice synthesis",
            "Gemini dialog management",
            "Service booking automation",
            "Hands-free rider interface",
        ],
        "metrics": [
            ["5+", "languages"],
            ["<500ms", "dialog latency"],
            ["99.5%", "availability"],
        ],
        "links": [
            ["Kinetic India", "https://www.kinetic.in/"],
            ["ElevenLabs", "https://elevenlabs.io/"],
            ["Google Gemini API", "https://ai.google.dev/"],
        ],
        "blog_tags": ["Voice AI", "Telecom", "Conversational AI"],
        "blog_posts": [],
        "credits": [
            {
                "name": "ElevenLabs",
                "context": "High-quality voice synthesis",
                "url": "https://elevenlabs.io/",
            },
            {
                "name": "Google Gemini API",
                "context": "Conversational AI and dialog management",
                "url": "https://ai.google.dev/",
            },
        ],
    },
    "litmus-industrial-iot": {
        "slug": "litmus-industrial-iot",
        "kind": "client",
        "name": "Litmus — Industrial IoT Edge Data Platform",
        "tagline": "Real-time MQTT/OPC-UA ingestion, edge-to-cloud, anomaly detection",
        "org": "Searce client work",
        "status": "maintained",
        "featured": False,
        "summary": "Industrial IoT edge data platform with real-time ingestion from manufacturing/energy plants. MQTT/OPC-UA streams, Python pipelines, AI anomaly detection, Kubernetes orchestration.",
        "description_html": """<p>Built backend integrations for the Litmus Industrial IoT Edge Data Platform — enabling real-time data collection and analysis from manufacturing and energy facilities.</p>
<p><strong>Data pipeline architecture:</strong></p>
<ul>
<li>Real-time MQTT and OPC-UA protocol handlers for industrial equipment connectivity</li>
<li>Edge data aggregation and preprocessing at the plant level</li>
<li>Python streaming pipelines for cloud analytics on GCP</li>
<li>AI-driven anomaly detection for predictive maintenance</li>
<li>Kubernetes orchestration for edge-to-cloud data flow</li>
<li>Prometheus observability for pipeline health monitoring</li>
</ul>
<p><strong>Impact:</strong> Enables manufacturers and energy operators to monitor equipment health, predict failures, and optimize operations in real-time.</p>""",
        "role": "Backend engineer",
        "year": "2023–2024",
        "tags": ["Python", "MQTT", "OPC-UA", "IoT", "Kubernetes", "Dataflow"],
        "highlights": [
            "MQTT and OPC-UA protocol integration",
            "Real-time data ingestion from manufacturing plants",
            "Python streaming pipelines to cloud",
            "AI-driven anomaly detection",
            "Edge-to-cloud orchestration on Kubernetes",
            "Prometheus observability for pipeline health",
        ],
        "metrics": [
            ["1000+", "sensors"],
            ["<1s", "latency"],
            ["99.9%", "uptime"],
        ],
        "links": [
            ["MQTT Protocol", "https://mqtt.org/"],
            ["OPC-UA Standard", "https://opcfoundation.org/"],
            ["Kubernetes", "https://kubernetes.io/"],
        ],
        "blog_tags": ["IoT", "Edge Computing", "Anomaly Detection"],
        "blog_posts": [],
        "credits": [
            {
                "name": "MQTT Protocol",
                "context": "Industrial IoT messaging standard",
                "url": "https://mqtt.org/",
            },
            {
                "name": "OPC Unified Architecture",
                "context": "Industrial automation standardization",
                "url": "https://opcfoundation.org/",
            },
            {
                "name": "Kubernetes",
                "context": "Edge-to-cloud orchestration",
                "url": "https://kubernetes.io/",
            },
        ],
    },
}

# CSS for project pages (extends POST_CSS from build_blog.py)
PROJECT_CSS = POST_CSS + """
.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin: 20px 0;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 100px;
}

.metric-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--accent);
  line-height: 1;
}

.metric-label {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 4px;
  text-align: center;
}

.project-status {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.85rem;
  font-weight: 600;
  background: var(--tag-bg);
  color: var(--tag-text);
  text-transform: capitalize;
}

.project-featured {
  border-color: var(--accent);
  border-width: 2px;
}

.highlights-list {
  margin: 24px 0;
  padding-left: 20px;
}

.highlights-list li {
  margin-bottom: 12px;
  color: var(--text-dim);
}

.highlights-list strong {
  color: var(--text);
}

.project-hero {
  padding: 56px 0 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 36px;
}

.project-hero h1 {
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 8px;
}

.project-tagline {
  font-size: 1.2rem;
  color: var(--text-dim);
  margin-bottom: 16px;
  max-width: 640px;
}

.project-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
}

.project-role {
  color: var(--text-muted);
  font-size: 0.95rem;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 24px 0;
}

.btn {
  display: inline-block;
  padding: 10px 20px;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.95rem;
  transition: all 0.15s;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover {
  background: var(--accent-hover);
  text-decoration: none;
}

.btn-secondary {
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--accent);
}

.btn-secondary:hover {
  border-color: var(--accent);
  background: var(--bg-elev);
  text-decoration: none;
}

/* Gallery page hero */
.blog-hero {
  padding: 56px 0 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 36px;
}
.blog-hero h1 {
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 8px;
}
.blog-hero p {
  font-size: 1.05rem;
  color: var(--text-dim);
  max-width: 640px;
}

/* Project gallery grid */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
.project {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  transition: transform 0.15s, box-shadow 0.15s;
}
.project:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}
.project-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.project-name {
  font-size: 1rem;
  font-weight: 700;
}
.project-name a {
  color: var(--text);
}
.project-name a:hover {
  color: var(--accent);
  text-decoration: underline;
}
.project-org {
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: nowrap;
}
.project-desc {
  font-size: 0.9rem;
  color: var(--text-dim);
  margin-bottom: 14px;
  line-height: 1.55;
  flex: 1;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}
.project-links {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 0.85rem;
  font-weight: 500;
}
.project-links a {
  white-space: nowrap;
}
"""


def render_project_gallery_html(all_projects):
    """Render /projects/index.html — OSS + client grids."""
    oss_projects = [p for p in all_projects.values() if p["kind"] == "oss"]
    client_projects = [p for p in all_projects.values() if p["kind"] == "client"]

    project_cards_oss = "\n".join(
        f"""    <div class="project{' project-featured' if p.get('featured') else ''}">
      <div class="project-header">
        <span class="project-name"><a href="/projects/{p['slug']}/">{p['name']}</a></span>
        <span class="project-org">{p['org']}</span>
      </div>
      <p class="project-desc">{p['summary']}</p>
      <div class="tag-row">
        {"".join(f'<span class="tag">{tag}</span>' for tag in p['tags'][:5])}
      </div>
      <div class="project-links">
        {"".join(f'<a href="{link[1]}">{link[0]} →</a>' for link in p['links'])}
      </div>
    </div>"""
        for p in oss_projects
    )

    project_cards_client = "\n".join(
        f"""    <div class="project">
      <div class="project-header">
        <span class="project-name">{p['name']}</span>
        <span class="project-org">{p['org']}</span>
      </div>
      <p class="project-desc">{p['summary']}</p>
      <div class="metric-row">
        {"".join(f'<div class="metric"><div class="metric-value">{m[0]}</div><div class="metric-label">{m[1]}</div></div>' for m in p['metrics'])}
      </div>
      <div class="tag-row">
        {"".join(f'<span class="tag">{tag}</span>' for tag in p['tags'][:5])}
      </div>
    </div>"""
        for p in client_projects
    )

    body = f"""<section class="blog-hero">
  <h1>Project Portfolio</h1>
  <p>Featured open-source projects and client work spanning multi-agent AI, cloud infrastructure, and production systems.</p>
</section>

<section>
  <h2>Featured Open Source</h2>
  <p>Marquee projects showcasing multi-agent architecture, governance, and production AI systems. Both Genie and Bodh are reference implementations of Microsoft's Agent Framework (MAF).</p>
  <div class="projects-grid" style="margin-top: 24px;">
{project_cards_oss}
  </div>
</section>

<section>
  <h2>Delivered Impact at Scale</h2>
  <p>Production systems shipped for enterprise and consumer markets, delivering measurable business outcomes — from FinOps savings to high-throughput transaction engines.</p>
  <div class="projects-grid" style="margin-top: 24px;">
{project_cards_client}
  </div>
</section>

<section style="margin-top: 48px; padding-top: 32px; border-top: 1px solid var(--border);">
  <h2>Partnership & Collaborations</h2>
  <p>Open to collaboration on multi-agent systems, cloud architecture, and production AI challenges. <a href="/#contact">Get in touch →</a></p>
</section>"""

    return _wrap_page_html("Projects", body)


def render_project_detail_html(project_slug, all_posts):
    """Render /projects/<slug>/index.html for an individual OSS project."""
    project = PROJECT_META[project_slug]

    if project["kind"] != "oss":
        raise ValueError(f"Detail pages only for OSS projects; {project_slug} is {project['kind']}")

    # Build metrics row
    metrics_html = (
        "".join(
            f'<div class="metric"><div class="metric-value">{m[0]}</div><div class="metric-label">{m[1]}</div></div>'
            for m in project["metrics"]
        )
        if project.get("metrics")
        else ""
    )

    # Build action buttons
    links_html = "".join(
        f'<a href="{link[1]}" class="btn btn-primary">{link[0]}</a>'
        for link in project["links"]
    )

    # Build highlights
    highlights_html = (
        "<ul class=\"highlights-list\">"
        + "".join(f"<li>{h}</li>" for h in project["highlights"])
        + "</ul>"
    )

    # Find related blog posts
    related_posts_html = ""
    if project.get("blog_tags") or project.get("blog_posts"):
        related = find_related_posts(project_slug, all_posts, project.get("blog_tags", []))
        if related or project.get("blog_posts"):
            related_posts_html = '<section class="related-posts" style="margin-top: 48px; padding-top: 32px; border-top: 1px solid var(--border);">'
            related_posts_html += '<h3>Related Writing</h3>'

            # Explicit pins first
            for post_path in project.get("blog_posts", []):
                # Try to find in POST_META
                for meta in POST_META.values():
                    if meta.get("slug") in post_path:
                        related_posts_html += f'<div style="margin-bottom: 12px;"><a href="{post_path}">{meta.get("title", "Untitled")}</a></div>'
                        break

            # Then auto-related
            for post in related:
                post_date = post["meta"]["date"]
                post_slug = post["meta"]["slug"]
                related_posts_html += f'<div style="margin-bottom: 12px;"><a href="/blog/posts/{post_slug}.html">{post["meta"].get("title", "Untitled")}</a> <span style="color: var(--text-muted); font-size: 0.9rem;">({post_date})</span></div>'

            related_posts_html += '</section>'

    # Build credits section
    credits_html = ""
    if project.get("credits"):
        credits_html = '<section class="post-citations" style="margin-top: 48px;">'
        credits_html += '<h3>Acknowledgments</h3>'
        for credit in project["credits"]:
            credits_html += f"""<div class="citation-item">
      <div class="citation-title"><a href="{credit['url']}" target="_blank">{credit['name']}</a></div>
      <div class="citation-context">{credit['context']}</div>
    </div>"""
        credits_html += '</section>'

    body = f"""<section class="project-hero">
  <h1>{project['name']}</h1>
  <p class="project-tagline">{project['tagline']}</p>
  <div class="project-meta">
    <span class="project-status">{project['status']}</span>
    <span class="project-role">{project['role']}</span>
    <span class="project-role">{project['year']}</span>
  </div>
  {f'<div class="metric-row">{metrics_html}</div>' if metrics_html else ''}
  <div class="action-buttons">
    {links_html}
    <a href="/#contact" class="btn btn-secondary">Contact about collaboration</a>
  </div>
</section>

{project['description_html']}

<section style="margin-top: 32px;">
  <h2>Key Highlights</h2>
  {highlights_html}
</section>

<section style="margin-top: 32px;">
  <h2>Built with</h2>
  <div class="tag-row">
    {"".join(f'<span class="tag">{tag}</span>' for tag in project['tags'])}
  </div>
</section>

{related_posts_html}

{credits_html}

<section style="margin-top: 48px; padding-top: 32px; border-top: 1px solid var(--border);">
  <p><a href="/projects/">← All projects</a></p>
</section>"""

    # Build JSON-LD schemas
    schema_html = f"""
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "{project['name']}",
  "description": "{project['tagline']}",
  "url": "https://pratikdhanave.com/projects/{project_slug}/",
  "author": {{
    "@type": "Person",
    "name": "Pratik Dhanave"
  }},
  "codeRepository": "{project.get('links', [[None, 'https://github.com/PratikDhanave']])[0][1]}",
  "programmingLanguage": "{project.get('language', 'Go')}"
}}
</script>

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{
      "@type": "ListItem",
      "position": 1,
      "name": "Projects",
      "item": "https://pratikdhanave.com/projects/"
    }},
    {{
      "@type": "ListItem",
      "position": 2,
      "name": "{project['name']}",
      "item": "https://pratikdhanave.com/projects/{project_slug}/"
    }}
  ]
}}
</script>"""

    return _wrap_page_html(project['name'], body, schema_html, slug=project_slug)


def _wrap_page_html(page_title, body_html, schema_html="", slug=""):
    """Wrap project page body with nav, footer, CSS."""
    active_nav = NAV_HTML.replace(
        '<li><a href="/projects/">Projects</a></li>',
        '<li><a href="/projects/" class="active">Projects</a></li>',
    ).replace(
        '<li><a href="/blog/" class="active">Blog</a></li>',
        '<li><a href="/blog/">Blog</a></li>',
    )

    # For the gallery page, use "Projects" directly; for detail pages, append " — Projects"
    if page_title == "Projects":
        full_title = "Projects — Pratik Dhanave"
        canonical = "https://pratikdhanave.com/projects/"
    else:
        full_title = f"{page_title} — Projects — Pratik Dhanave"
        canonical = f"https://pratikdhanave.com/projects/{slug}/" if slug else "https://pratikdhanave.com/projects/"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{full_title}</title>
<meta name="description" content="{page_title}. Portfolio projects and client work by Pratik Dhanave.">
<meta name="author" content="Pratik Dhanave">
<meta property="og:title" content="Pratik Dhanave — {page_title}">
<meta property="og:description" content="{page_title}. Portfolio projects and client work by Pratik Dhanave — multi-agent AI, cloud infrastructure, and production systems.">
<meta property="og:type" content="website">
<meta property="og:image" content="https://pratikdhanave.com/og-default.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — {page_title}">
<meta name="twitter:description" content="{page_title}. Portfolio projects and client work by Pratik Dhanave — multi-agent AI, cloud infrastructure, and production systems.">
<meta name="twitter:image" content="https://pratikdhanave.com/og-default.png">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">
<style>
{PROJECT_CSS}
</style>
{schema_html}
</head>
<body>
{active_nav}
<main style="max-width: 880px;">
{body_html}
</main>
{SITE_FOOTER}
</body>
</html>"""


def main():
    """Generate all project pages."""
    # Import POST_META for related posts linking
    from build_blog import POST_META as blog_posts_meta

    # Enrich POST_META with titles from generated HTML files
    for meta in blog_posts_meta.values():
        if "title" not in meta:
            slug = meta.get("slug", "")
            post_file = SITE_ROOT / "blog" / "posts" / f"{slug}.html"
            if post_file.exists():
                html_head = post_file.read_text()[:500]
                m = re.search(r"<title>(.*?)(?:\s*—\s*Pratik Dhanave)?</title>", html_head)
                if m:
                    meta["title"] = m.group(1).strip()

    # Convert POST_META values to list format for find_related_posts
    all_posts = [
        {"meta": meta, "content": "", "title": meta.get("title", "Untitled")}
        for meta in blog_posts_meta.values()
    ]

    # Create projects directory
    projects_dir = SITE_ROOT / "projects"
    projects_dir.mkdir(exist_ok=True)

    # Render gallery
    print("Generating /projects/index.html...")
    gallery_html = render_project_gallery_html(PROJECT_META)
    (projects_dir / "index.html").write_text(gallery_html)

    # Render OSS project pages
    for slug, project in PROJECT_META.items():
        if project["kind"] == "oss":
            print(f"Generating /projects/{slug}/index.html...")
            project_dir = projects_dir / slug
            project_dir.mkdir(exist_ok=True)
            detail_html = render_project_detail_html(slug, all_posts)
            (project_dir / "index.html").write_text(detail_html)

    print("\n✅ Project pages generated successfully!")
    print(f"   - /projects/ (gallery)")
    print(f"   - /projects/genie/ (OSS project)")
    print(f"   - /projects/bodh/ (OSS project)")
    print(f"   - /projects/harbourbridge/ (OSS project)")


if __name__ == "__main__":
    main()
