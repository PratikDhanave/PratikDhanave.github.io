#!/usr/bin/env python3
"""
build_blog.py — Convert markdown articles in bodh-linkedin/ into themed
HTML blog posts on PratikDhanave.github.io, plus regenerate the blog index.

This script is run from the site repo root. It expects the source markdown
files to live in a sibling directory at ../bodh-linkedin/.

Design system aligned with the site's index.html:
  - Same CSS variables (light + dark mode)
  - System font stack
  - Sticky nav, max-width 980px, 24px gutter
  - Tag pill style
  - Code blocks with --code-bg background

The script:
  1. Reads each .md file in ../bodh-linkedin/ (skipping README.md and feed-posts.md)
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
# Configuration
# ---------------------------------------------------------------------------

SITE_ROOT = Path(__file__).parent.resolve()
SRC_DIR = SITE_ROOT.parent / "bodh-linkedin"
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
    "10-right-to-explanation.md": {
        "slug": "right-to-explanation",
        "date": "2026-05-26",
        "tags": ["GDPR", "Privacy Engineering", "AI Governance", "Go"],
        "audience": "AI governance + backend engineering",
        "excerpt": "How a 200-line Go handler turns an audit log and an eval store into a regulator-friendly answer to 'why did the AI decide that?' — without leaking a single byte of PHI. GDPR Article 22 as a Go HTTP endpoint.",
    },
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
      <li><a href="/#projects">Projects</a></li>
      <li><a href="/blog/" class="active">Blog</a></li>
      <li><a href="/#contact">Contact</a></li>
    </ul>
  </div>
</nav>"""


SITE_FOOTER = """<footer class="site-footer">
  <p>© {year} Pratik Dhanave · <a href="https://github.com/PratikDhanave">GitHub</a> · <a href="https://www.linkedin.com/in/pratikdhanave/">LinkedIn</a></p>
</footer>""".format(year=datetime.now().year)


def render_post_html(meta, title, subtitle, body_html):
    """Wrap rendered markdown body in the post template."""
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in meta["tags"])
    date_iso = meta["date"]
    date_human = datetime.strptime(date_iso, "%Y-%m-%d").strftime("%B %d, %Y")
    description = meta["excerpt"]
    canonical = f"https://pratikdhanave.github.io/blog/posts/{meta['slug']}.html"

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
<meta property="article:published_time" content="{date_iso}">
{''.join(f'<meta property="article:tag" content="{t}">' + chr(10) for t in meta['tags'])}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">

<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%231a73e8'/><text x='50' y='65' font-size='52' text-anchor='middle' fill='white' font-family='-apple-system,sans-serif' font-weight='700'>P</text></svg>">

<style>{POST_CSS}</style>
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
    </div>
    <div class="post-tags">{tags_html}</div>
  </header>

  {body_html}

  <div class="post-footer">
    <div class="footer-row">
      <span>Written by <strong>Pratik Dhanave</strong></span>
      <a href="/blog/">← All posts</a>
    </div>
    <p style="margin-top: 10px; font-size: 13px;">Find me on
      <a href="https://github.com/PratikDhanave">GitHub</a> ·
      <a href="https://www.linkedin.com/in/pratikdhanave/">LinkedIn</a></p>
  </div>
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
        posts_html.append(f"""    <article class="post-card">
      <div class="post-card-meta">
        <time datetime="{date_iso}">{date_human}</time>
        <span>·</span>
        <span>{p["meta"]["audience"]}</span>
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
<title>Blog — Pratik Dhanave</title>
<meta name="description" content="Long-form writing on multi-agent AI, medical AI governance, HIPAA-aware architecture, and cloud-native systems. By Pratik Dhanave.">
<meta name="author" content="Pratik Dhanave">

<meta property="og:title" content="Pratik Dhanave — Blog">
<meta property="og:description" content="Long-form writing on multi-agent AI, medical AI governance, and HIPAA-aware architecture.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://pratikdhanave.github.io/blog/">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Pratik Dhanave — Blog">

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
# Build
# ---------------------------------------------------------------------------

def main():
    if not SRC_DIR.exists():
        print(f"ERROR: source dir not found at {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    rendered = []
    for filename, meta in POST_META.items():
        md_path = SRC_DIR / filename
        if not md_path.exists():
            print(f"SKIP missing: {md_path}", file=sys.stderr)
            continue

        title, subtitle, body_md = parse_post(md_path)
        body_html = to_html(body_md)
        html = render_post_html(meta, title, subtitle, body_html)

        out_path = POSTS_DIR / f"{meta['slug']}.html"
        out_path.write_text(html)
        rendered.append({"meta": meta, "title": title, "subtitle": subtitle})
        print(f"  wrote {out_path.relative_to(SITE_ROOT)}")

    # Sort newest first by date.
    rendered.sort(key=lambda p: p["meta"]["date"], reverse=True)

    INDEX_PATH.write_text(render_index_html(rendered))
    print(f"  wrote {INDEX_PATH.relative_to(SITE_ROOT)}")
    print(f"\nBuilt {len(rendered)} posts.")


if __name__ == "__main__":
    main()
