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

import os
import re
import sys
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
        "tags": ["Software Architecture", "Multi-Agent", "MARA", "Go"],
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
        "tags": ["ADK", "MARA", "Architecture", "Multi-Agent AI"],
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
                "url": "https://pratikdhanave.github.io/thank-you/",
                "context": "Design pattern for portable agent implementations"
            }
        ]
    },
    "2026-06-02-adk-to-maf-executor-pattern.md": {
        "slug": "adk-to-maf-executor-pattern",
        "date": "2026-06-02",
        "tags": ["ADK", "MARA", "Orchestration", "Design Pattern"],
        "audience": "Platform architects",
        "excerpt": "How to port ADK's orchestration callbacks to MAF builders without losing control. The executor pattern: you own the loop.",
        "series": "ADK to MAF Migration",
        "series_position": 2,
        "series_total": 8,
    },
    "2026-06-03-adk-to-maf-token-exchange.md": {
        "slug": "adk-to-maf-token-exchange",
        "date": "2026-06-03",
        "tags": ["ADK", "MARA", "State Management", "Token Budgeting"],
        "audience": "Backend + ML engineers",
        "excerpt": "Sessions to threads: porting multi-turn state from ADK to MAF. Token budgeting, long-term memory, and conversation audit trails.",
        "series": "ADK to MAF Migration",
        "series_position": 3,
        "series_total": 8,
    },
    "2026-06-04-adk-to-maf-tool-wrapping.md": {
        "slug": "adk-to-maf-tool-wrapping",
        "date": "2026-06-04",
        "tags": ["ADK", "MARA", "Tools", "Governance", "OPA"],
        "audience": "Governance + backend engineers",
        "excerpt": "From ADK functions to MAF governed tools. Adding policy enforcement, DLP, approval gates, and OPA integration.",
        "series": "ADK to MAF Migration",
        "series_position": 4,
        "series_total": 8,
    },
    "2026-06-05-adk-to-maf-provider-config.md": {
        "slug": "adk-to-maf-provider-config",
        "date": "2026-06-05",
        "tags": ["ADK", "MARA", "Provider Abstraction", "Config"],
        "audience": "DevOps + platform engineers",
        "excerpt": "Zero-code provider swaps: Ollama (dev), OpenAI (staging), Azure Foundry (prod). Same agents, different models.",
        "series": "ADK to MAF Migration",
        "series_position": 5,
        "series_total": 8,
    },
    "2026-06-06-adk-to-maf-callbacks.md": {
        "slug": "adk-to-maf-callbacks",
        "date": "2026-06-06",
        "tags": ["ADK", "MARA", "Middleware", "Observability", "OTel"],
        "audience": "SRE + observability engineers",
        "excerpt": "Callbacks to middleware: composable decorators for audit, retry, token enforcement, and OpenTelemetry integration.",
        "series": "ADK to MAF Migration",
        "series_position": 6,
        "series_total": 8,
    },
    "2026-06-07-adk-to-maf-deployment.md": {
        "slug": "adk-to-maf-deployment",
        "date": "2026-06-07",
        "tags": ["ADK", "MARA", "Deployment", "Cloud Run", "A2A"],
        "audience": "Cloud architects + SRE",
        "excerpt": "Cloud Run deployments, agent-to-agent communication, load balancing, and production observability.",
        "series": "ADK to MAF Migration",
        "series_position": 7,
        "series_total": 8,
    },
    "2026-06-08-adk-to-maf-lessons.md": {
        "slug": "adk-to-maf-lessons",
        "date": "2026-06-08",
        "tags": ["ADK", "MARA", "Case Study", "Lessons Learned"],
        "audience": "All engineers",
        "excerpt": "What worked, what was hard, and what we'd do differently. Real numbers: 18 agents, 90 days, 5 governance policies, 4 provider swaps.",
        "featured": True,
        "series": "ADK to MAF Migration",
        "series_position": 8,
        "series_total": 8,
    },
}

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
    "02-cures-act-as-code": 3,              # Duplicate handling
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
  --text-muted: #888;
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
# Templates
# ---------------------------------------------------------------------------

NAV_HTML = """<nav>
  <div class="nav-container">
    <a href="/" class="nav-brand">Pratik Dhanave</a>
    <ul class="nav-links">
      <li><a href="/#about">About</a></li>
      <li><a href="/projects/">Projects</a></li>
      <li><a href="/speaking/">Speaking</a></li>
      <li><a href="/blog/" class="active">Blog</a></li>
      <li><a href="/resources/">Resources</a></li>
      <li><a href="/#contact">Contact</a></li>
    </ul>
  </div>
</nav>"""


SITE_FOOTER = """<footer class="site-footer">
  <p>© {year} Pratik Dhanave · <a href="https://github.com/PratikDhanave">GitHub</a> · <a href="https://www.linkedin.com/in/pratikdhanave/">LinkedIn</a> · <a href="/thank-you/">Acknowledgments</a></p>
</footer>""".format(year=datetime.now().year)


def render_post_html(meta, title, subtitle, body_html, all_posts=None):
    """Wrap rendered markdown body in the post template."""
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in meta["tags"])
    date_iso = meta["date"]
    date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%B %d, %Y")
    description = meta["excerpt"]
    canonical = f"https://pratikdhanave.github.io/blog/posts/{meta['slug']}.html"

    # Calculate read time
    read_time = calculate_read_time(body_html)
    read_time_text = f"{read_time} min read"

    # Render series breadcrumbs if present
    series_html = ""
    if "series" in meta and meta.get("series"):
        series_name = meta["series"]
        position = meta.get("series_position", 0)
        total = meta.get("series_total", 0)
        series_html = f"""  <div class="series-breadcrumb">
    <span class="series-label">Part {position} of {total}</span>
    <span class="series-title">{series_name}</span>
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
      <div class="citation-title"><a href="{citation['url']}" target="_blank">{citation['title']}</a></div>
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
<title>{title} — Pratik Dhanave</title>
<meta name="description" content="{description}">
<meta name="author" content="Pratik Dhanave">

<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://pratikdhanave.github.io/og-default.png">
<meta property="article:published_time" content="{date_iso}">
{''.join(f'<meta property="article:tag" content="{t}">' + chr(10) for t in meta['tags'])}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://pratikdhanave.github.io/og-default.png">

<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<style>{POST_CSS}</style>

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "{title}",
  "description": "{description}",
  "datePublished": "{date_iso}",
  "author": {{
    "@type": "Person",
    "name": "Pratik Dhanave"
  }},
  "keywords": "{', '.join(meta['tags'])}",
  "url": "{canonical}"
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
      <a href="https://github.com/PratikDhanave">GitHub</a> ·
      <a href="https://www.linkedin.com/in/pratikdhanave/">LinkedIn</a> ·
      <a href="/thank-you/">Acknowledgments</a></p>
  </div>
{citations_html}
</article>
</main>

{SITE_FOOTER}

</body>
</html>
"""


def render_index_html(posts):
    """Build the blog landing page listing all posts (newest first)."""
    posts_html = []
    for p in posts:
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p["meta"]["tags"])
        date_iso = p["meta"]["date"]
        date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%b %d, %Y")
        is_featured = p["meta"].get("featured", False)
        featured_badge = '<span class="featured-badge">Featured</span>' if is_featured else ''

        posts_html.append(f"""    <article class="post-card{'  post-card-featured' if is_featured else ''}">
      <div class="post-card-meta">
        <time datetime="{date_iso}">{date_human}</time>
        <span>·</span>
        <span>{p["meta"]["audience"]}</span>
        {featured_badge}
      </div>
      <h2 class="post-card-title"><a href="posts/{p['meta']['slug']}.html">{p['title']}</a></h2>
      <p class="post-card-subtitle">{p['subtitle']}</p>
      <p class="post-card-excerpt">{p['meta']['excerpt']}</p>
      <div class="post-tags">{tags_html}</div>
    </article>""")

    index_css = POST_CSS + """

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
.post-card-featured {
  border-color: var(--accent);
  background: var(--bg-elev);
}
.post-card-featured:hover {
  border-color: var(--accent-hover);
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
.featured-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  background: var(--accent);
  color: white;
  border-radius: 4px;
  margin-left: auto;
  letter-spacing: 0.5px;
}
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog — Pratik Dhanave</title>
<meta name="description" content="Long-form writing on multi-agent AI, medical AI governance, HIPAA-aware architecture, and cloud-native systems. By Pratik Dhanave.">
<meta name="author" content="Pratik Dhanave">

<meta property="og:title" content="Pratik Dhanave — Blog">
<meta property="og:description" content="Long-form writing on multi-agent AI, medical AI governance, and HIPAA-aware architecture.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://pratikdhanave.github.io/blog/">
<meta property="og:image" content="https://pratikdhanave.github.io/og-default.png">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — Blog">
<meta name="twitter:image" content="https://pratikdhanave.github.io/og-default.png">

<link rel="canonical" href="https://pratikdhanave.github.io/blog/">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<style>{index_css}</style>
</head>
<body>

{NAV_HTML}

<main class="blog-index">

<section class="blog-hero">
  <h1>Blog</h1>
  <p>Long-form writing on multi-agent AI, medical AI governance, HIPAA-aware architecture, and cloud-native systems. Most posts grow out of work on <a href="https://github.com/PratikDhanave/bodh">Bodh</a> — an open-source Go implementation of Microsoft's MARA pattern tuned for medical sequential diagnosis.</p>
</section>

<section class="post-list">
{chr(10).join(posts_html)}
</section>

</main>

{SITE_FOOTER}

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

def render_tag_page(tag, posts_with_tag, all_tags):
    """Generate a page for a single tag listing all posts with that tag."""
    posts_html = []
    for p in posts_with_tag:
        tags_html = "".join(f'<span class="tag">{t}</span>' for t in p["meta"]["tags"])
        date_iso = p["meta"]["date"]
        date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%b %d, %Y")
        posts_html.append(f"""    <article class="post-card">
      <div class="post-card-meta">
        <time datetime="{date_iso}">{date_human}</time>
        <span>·</span>
        <span>{p["meta"]["audience"]}</span>
      </div>
      <h2 class="post-card-title"><a href="/blog/posts/{p['meta']['slug']}.html">{p['title']}</a></h2>
      <p class="post-card-subtitle">{p['subtitle']}</p>
      <p class="post-card-excerpt">{p['meta']['excerpt']}</p>
      <div class="post-tags">{tags_html}</div>
    </article>""")

    tag_cloud_html = "".join(f'<a href="/blog/tags/{t.lower().replace(" ", "-")}/"><span class="tag-cloud-item">{t}</span></a>' for t in sorted(all_tags))

    tag_page_css = POST_CSS + """

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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{tag} — Blog — Pratik Dhanave</title>
<meta name="description" content="Posts tagged with {tag}. By Pratik Dhanave.">
<meta name="author" content="Pratik Dhanave">

<meta property="og:title" content="Pratik Dhanave — {tag}">
<meta property="og:description" content="Posts tagged with {tag}.">
<meta property="og:type" content="website">
<meta property="og:image" content="https://pratikdhanave.github.io/og-default.png">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — {tag}">
<meta name="twitter:image" content="https://pratikdhanave.github.io/og-default.png">

<link rel="canonical" href="https://pratikdhanave.github.io/blog/tags/{tag.lower().replace(' ', '-')}/">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<style>{tag_page_css}</style>
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
        canonical = f"https://pratikdhanave.github.io/blog/archive/{year}/{month:02d}/"
    else:
        title = str(year)
        canonical = f"https://pratikdhanave.github.io/blog/archive/{year}/"

    posts_html = []
    if posts_with_date:
        for p in posts_with_date:
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in p["meta"]["tags"])
            date_iso = p["meta"]["date"]
            date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%b %d, %Y")
            posts_html.append(f"""    <article class="post-card">
      <div class="post-card-meta">
        <time datetime="{date_iso}">{date_human}</time>
        <span>·</span>
        <span>{p["meta"]["audience"]}</span>
      </div>
      <h2 class="post-card-title"><a href="/blog/posts/{p['meta']['slug']}.html">{p['title']}</a></h2>
      <p class="post-card-subtitle">{p['subtitle']}</p>
      <p class="post-card-excerpt">{p['meta']['excerpt']}</p>
      <div class="post-tags">{tags_html}</div>
    </article>""")

    # Year/month nav
    year_nav = "".join(f'<a href="/blog/archive/{y}/" class="tag-cloud-item">{y}</a>' for y in sorted(all_years, reverse=True))

    archive_css = POST_CSS + """

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
<meta property="og:image" content="https://pratikdhanave.github.io/og-default.png">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — {title}">
<meta name="twitter:image" content="https://pratikdhanave.github.io/og-default.png">

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
        if not md_path.exists():
            print(f"SKIP missing: {md_path}", file=sys.stderr)
            continue

        title, subtitle, body_md = parse_post(md_path)
        body_html = to_html(body_md)
        rendered.append({"meta": meta, "title": title, "subtitle": subtitle})
        posts_data[meta["slug"]] = {"body_html": body_html, "title": title, "subtitle": subtitle}

    # Sort newest first by date (for index).
    rendered.sort(key=lambda p: p["meta"]["date"], reverse=True)

    # Second pass: render posts with access to all posts for related content
    for post in rendered:
        meta = post["meta"]
        title = post["title"]
        subtitle = post["subtitle"]
        body_html = posts_data[meta["slug"]]["body_html"]
        html = render_post_html(meta, title, subtitle, body_html, all_posts=rendered)

        out_path = POSTS_DIR / f"{meta['slug']}.html"
        out_path.write_text(html)
        print(f"  wrote {out_path.relative_to(SITE_ROOT)}")

    # Generate main blog index
    INDEX_PATH.write_text(render_index_html(rendered))
    print(f"  wrote {INDEX_PATH.relative_to(SITE_ROOT)}")

    # Generate popular posts JSON feed
    popular_posts_json = render_popular_posts_json(rendered, limit=3)
    popular_posts_path = SITE_ROOT / "blog" / "popular-posts.json"
    popular_posts_path.write_text(popular_posts_json)
    print(f"  wrote {popular_posts_path.relative_to(SITE_ROOT)}")

    # Generate tag pages
    all_tags = set()
    tag_posts = {}
    for p in rendered:
        for tag in p["meta"]["tags"]:
            all_tags.add(tag)
            tag_key = tag.lower().replace(" ", "-")
            if tag_key not in tag_posts:
                tag_posts[tag_key] = []
            tag_posts[tag_key].append(p)

    tags_dir = SITE_ROOT / "blog" / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)

    for tag_key, posts_with_tag in tag_posts.items():
        tag_dir = tags_dir / tag_key
        tag_dir.mkdir(parents=True, exist_ok=True)
        tag_file = tag_dir / "index.html"
        tag_name = posts_with_tag[0]["meta"]["tags"][[t.lower().replace(" ", "-") for t in posts_with_tag[0]["meta"]["tags"]].index(tag_key)]
        tag_file.write_text(render_tag_page(tag_name, posts_with_tag, all_tags))
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
        for month in sorted(archive_by_date[year].keys()):
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

    print(f"\nBuilt {len(rendered)} posts + {len(tag_posts)} tag pages + {len(archive_by_date)} year archives.")


if __name__ == "__main__":
    main()
