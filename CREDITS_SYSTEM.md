# Credits & References System

## Overview

The website now has a comprehensive, multi-layered credits system to acknowledge the people, projects, and knowledge that made this work possible.

## Architecture

### 1. **Dedicated Acknowledgments Page** (`/thank-you.html`)

A comprehensive recognition page with five sections:

#### 👥 People & Mentors
- Microsoft Agent Framework Team
- Go Community
- Python Data Science Community
- OpenTelemetry Project

#### 📚 Open Source Projects
- **Core Libraries**: Ollama, OPA/Conftest, PostgreSQL, Kubernetes
- **Observability**: Jaeger, Prometheus
- **Development Tools**: Docker, GitHub

#### 📖 Data Sources & References
- **Standards**: FHIR, HL7 v2, HIPAA, 21st Century Cures Act §3060
- **Research**: OWASP AI Security Guide, IAPP AIGP

#### 🌍 Communities & Organizations
- Cloud Native Computing Foundation (CNCF)
- Healthcare IT Community
- Microsoft Learn
- Google Cloud Architecture Center

### 2. **Per-Post Citations**

Each blog post can include structured citations:

```python
"citations": [
    {
        "title": "Reference Title",
        "url": "https://example.com",
        "context": "How this was used in the post"
    }
]
```

#### Rendered As
- **"Sources & References"** section before post footer
- Linked titles with italicized context
- Clear visual distinction with accent border

#### Current Examples
- `adk-to-maf-migration-why.html`: MAF docs, ADK reference, provider abstraction
- `hipaa-as-go-interfaces.md`: HIPAA regulations, Cures Act §3060
- `postgres-rls-hipaa.md`: PostgreSQL docs, HIPAA §164.312, grant system

### 3. **Footer Links**

All pages link to `/thank-you/`:
- Homepage footer
- Blog index footer  
- Individual blog post footers
- Tag page footers
- Archive page footers

## Implementation

### File: `build_blog.py`

**POST_META Structure**:
```python
POST_META = {
    "filename.md": {
        "slug": "url-slug",
        "date": "2026-06-01",
        "tags": ["Tag1", "Tag2"],
        "audience": "Target readers",
        "excerpt": "One-line summary",
        "citations": [...]  # Optional, new field
    }
}
```

**Template Rendering**:
```python
def render_post_html(meta, title, subtitle, body_html):
    # Build citations HTML from meta["citations"]
    # Insert before post-footer, after article body
```

**CSS Classes**:
- `.post-citations` - Container with accent border
- `.citation-item` - Individual citation
- `.citation-title` - Linked title
- `.citation-context` - Italicized context

## Expansion Roadmap

### Phase 2-3 (Project Pages)
Each project showcase will include:
- **Technologies Used**: Linked to OSS projects
- **References**: Key papers, tutorials, documentation
- **Team Thanks**: Collaborators and contributors

### Phase 3-4 (Homepage & Resources)
New `/resources.html` page:
- **Recommended Reading**: Books, papers, courses
- **Tools & Standards**: Curated list of governance/compliance tools
- **Community Links**: CNCF, HL7, OWASP, IAPP

### Post-Launch
- **Reader Contributions**: "Know a better source?" feedback system
- **Citation Stats**: Track which resources are most referenced
- **Microdata**: Schema.org markup for citations (scholarly articles)

## Design Principles

1. **Specificity**: Every credit includes *why* it mattered
2. **Discoverability**: Links are prominent and functional
3. **Accessibility**: Works in light and dark modes, keyboard navigable
4. **Consistency**: Same styling across blog posts, archives, and pages
5. **Liveness**: Easy to add citations to new posts via POST_META

## Examples

### Blog Post Citation (Rendered)
```html
<section class="post-citations">
  <h3>Sources & References</h3>
  <div class="citation-item">
    <div class="citation-title">
      <a href="..." target="_blank">Microsoft Agent Framework Docs</a>
    </div>
    <div class="citation-context">Official MAF patterns and best practices</div>
  </div>
</section>
```

### Page Footer
```html
<footer class="site-footer">
  <p>© 2026 Pratik Dhanave · 
    <a href="https://github.com/PratikDhanave">GitHub</a> · 
    <a href="https://www.linkedin.com/in/pratikdhanave/">LinkedIn</a> · 
    <a href="/thank-you/">Acknowledgments</a></p>
</footer>
```

## Maintenance

When adding a new blog post with citations:

1. Add `"citations": [...]` to POST_META entry
2. Run `python3 build_blog.py`
3. Citations section auto-renders
4. No additional HTML editing needed

## Stats

- **Acknowledgments Page**: 30+ entities across 5 categories
- **Blog Post Citations**: 3 posts, expanding to all 8 ADK→MAF posts
- **Linked Resources**: 20+ external links to official docs, standards, communities
- **Coverage**: Healthcare standards (HIPAA, FHIR, HL7v2), governance (OPA, IAPP), cloud (GCP, Azure, CNCF)
