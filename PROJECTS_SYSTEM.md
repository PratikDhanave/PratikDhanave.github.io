# Project Showcase System - Phase 2-3

## Overview

The website now features a comprehensive project portfolio with individual project pages, gallery view, and deep integration with the blog system. Projects are organized into two categories: Open Source and Client Work.

## Architecture

### Directory Structure

```
projects/
  index.html                 # Gallery: OSS + client grids
  genie/index.html          # Genie project detail page
  bodh/index.html           # Bodh project detail page
  harbourbridge/index.html  # HarbourBridge project detail page
build_projects.py           # Build script (mirrors build_blog.py)
PROJECTS_SYSTEM.md          # This documentation
```

All pages use pretty URLs via directory + `index.html` convention (same as `/blog/topic/*` and `/thank-you/`).

### Data Model - `PROJECT_META`

Mirror of `POST_META` from `build_blog.py`. Two record shapes with `kind` discrimination:

```python
PROJECT_META = {
  "slug": {
    "slug": "slug",
    "kind": "oss" | "client",
    "name": "Display Name",
    "tagline": "Short description",
    "org": "Organization",
    "status": "active" | "maintained" | "archived",
    "featured": True | False,
    "summary": "1-2 line gallery card text",
    "description_html": "<p>Longer body...</p>",
    "language": "Go" | "Python",
    "role": "Author" | "Contributor" | "Lead",
    "year": "2025–2026",
    "tags": ["Tag1", "Tag2", ...],
    "highlights": ["Achievement 1", "Achievement 2", ...],
    "metrics": [["value", "label"], ...],
    "links": [["Label", "https://url"], ...],
    "blog_tags": ["MAF", "Security", ...],  # for related posts
    "blog_posts": ["/blog/posts/slug.html", ...],  # explicit pins
    "credits": [
      {"name": "Project", "context": "...", "url": "..."},
      ...
    ],
  }
}
```

### Projects in the System

**Open Source (3):**
1. **Genie** - Multi-agent financial assistant on MAF
   - Status: active, featured
   - GitHub: c2siorg/genie

2. **Bodh** - Medical AI platform on MAF
   - Status: active
   - GitHub: PratikDhanave/bodh

3. **HarbourBridge** - Google Spanner Migration Tool (core contributor)
   - Status: maintained
   - GitHub: GoogleCloudPlatform/spanner-migration-tool

**Client Work (6):**
- Tata Group BigQuery FinOps (₹100 Cr+ savings, 57% reduction)
- Globe Telecom Transaction Engine (30K+ TPS)
- Brownlow AFL Voting Platform (100K+ votes)
- Picnic Social Network (1M+ users, 47% latency reduction)
- Bancnet Open Banking Portal (ADGM/DIFC/SAMA compliant, 37% latency ↓)
- Optimus BigQuery Analyzer (Gemini-powered, 57% cost reduction)

## Build System

### `build_projects.py`

Mirrors `build_blog.py` structure:
- Imports shared utilities: `SITE_ROOT`, `NAV_HTML`, `SITE_FOOTER`, `POST_CSS`, `find_related_posts`
- Extends `POST_CSS` with project-specific classes (`.metric-row`, `.project-status`, `.action-buttons`, `.btn`)
- Functions:
  - `render_project_gallery_html(all_projects)` → `/projects/index.html`
  - `render_project_detail_html(slug, all_posts)` → `/projects/<slug>/index.html`
  - `_wrap_page_html(title, body)` → complete HTML with nav/footer
  - `main()` → orchestrate full generation

### Invocation

```bash
python3 build_projects.py
```

Generates:
- Gallery index with OSS + client grids
- Individual detail pages for all 3 OSS projects
- ~4 HTML files, ~50KB total

### Integration with Blog Build

The blog build script was updated to:
- Change nav from `/#projects` → `/projects/`
- Regenerate all blog posts and tag pages with corrected nav

Command:
```bash
python3 build_blog.py
```

## Design & Styling

### Gallery Page (`/projects/`)

- `main` container at `980px` (homepage width)
- Two sections: "Featured Open Source" + "Delivered Impact at Scale"
- Card grid using `.projects-grid` (same CSS as homepage)
- Reuses `.project`, `.tag`, `.tag-row` classes from homepage
- Bottom: "View all projects →" buttons on both sections

### Detail Pages (`/projects/<slug>/`)

- `main` container at `760px` (article reading width)
- Hero section: project name, tagline, status badge, metrics row, action buttons
- Full description HTML (`.description_html`)
- "Key Highlights" bulleted list
- "Built with" tags
- "Related Writing" section (auto-linked by `blog_tags` + explicit `blog_posts`)
- "Acknowledgments" section (reuses `.post-citations` styling from blog)
- Footer with back-link to gallery

### CSS Extensions

New classes (extends `POST_CSS`):

- `.metric-row` / `.metric` — stat chips display (value + label)
- `.project-status` — status badge (active/maintained/archived)
- `.project-featured` — accent border variant
- `.project-hero` — page header styling
- `.highlights-list` — bulleted achievements
- `.action-buttons` — button row layout
- `.btn` / `.btn-primary` / `.btn-secondary` — call-to-action styling

All use existing CSS variables for light/dark mode.

### Responsive Design

- Reuses homepage grid collapse via `repeat(auto-fit, minmax(420px,1fr))`
- Same breakpoints: 820px, 640px, 480px
- Metrics and buttons flex-wrap at smaller widths
- Nav matches blog nav behavior (links hide progressively on mobile)

## Blog Integration

### Linking Projects ↔ Posts

Three mechanisms:

1. **Auto-related by `blog_tags`**
   - `find_related_posts()` imported from `build_blog.py`
   - Projects set `blog_tags` list (e.g., Genie → ["MAF", "Multi-Agent AI", "Security"])
   - Matching blog posts render as "Related Writing" section
   - Reuses `.related-posts` styling from blog

2. **Topic page links**
   - If project sets `topic: "bodh"` (optional), renders "Read all X posts on this project →" button to `/blog/topic/bodh/`
   - Currently: Genie → MAF tag page, Bodh → bodh topic page, HarbourBridge → spanner tag page

3. **Explicit pinned posts**
   - `blog_posts` list for the 1–3 canonical posts per project
   - Rendered first in "Related Writing", before auto-related

### Reverse Integration (Optional, Phase 3)

Future enhancement: mark blog posts with `project: "genie"` in `POST_META` to render "Part of the Genie project →" breadcrumb. Low-priority; mirrors existing `series` pattern.

## Credits & Acknowledgments

### Per-Project Credits

Each project includes a `credits` list:
```python
"credits": [
  {
    "name": "Microsoft Agent Framework Team",
    "context": "MAF patterns and SDK",
    "url": "https://learn.microsoft.com/.../agents/",
  },
  ...
]
```

Renders as "Acknowledgments" section reusing `.post-citations` / `.citation-item` styles from blog.

### Global Acknowledgments Page

All project detail pages footer-link to `/thank-you/`, keeping the central credits page the single source of truth.

Future enhancement: add "Featured Projects" section to `thank-you.html` linking back to each project page (closes the loop).

## Navigation Consistency

Updated across all pages:

**Homepage nav** (`/index.html`):
- Simplified to 5 items: About / Projects / Experience / Blog / Contact
- Projects link → `/projects/`

**Blog nav** (generated by `build_blog.py`):
- 4 items: About / Projects / Blog / Contact
- Projects link → `/projects/` (fixed from `/#projects`)
- All tag pages, archives, and posts regenerated with corrected nav

**Project pages nav** (generated by `build_projects.py`):
- 4 items: About / Projects / Blog / Contact
- Projects link active (`.active` class)

**Acknowledgments page nav** (`/thank-you.html`):
- 4 items: About / Projects / Blog / Contact

## Stats

- **Pages generated**: 4 (gallery + 3 OSS detail pages)
- **Projects featured**: 3 OSS + 6 client work
- **Metrics per project**: 2–3 stat chips
- **Blog integration**: all projects have `blog_tags` for related-posts linking
- **Credits per project**: 3–5 acknowledgment entries
- **Code**: ~400 lines (build_projects.py + CSS extensions)
- **Total files**: 4 HTML files generated, ~50KB

## Maintenance

### Adding a New OSS Project

1. Add entry to `PROJECT_META` in `build_projects.py`:
   ```python
   "slug": {
     "kind": "oss",
     "name": "...",
     "tagline": "...",
     ...
   }
   ```

2. Run `python3 build_projects.py` → generates `/projects/slug/index.html`

3. Update homepage nav link if needed

### Adding a New Client Project

1. Add entry to `PROJECT_META` with `kind: "client"`:
   ```python
   "slug": {
     "kind": "client",
     "name": "...",
     "metrics": [...],
     ...
   }
   ```

2. Run `python3 build_projects.py` → updates `/projects/index.html` gallery

3. No detail page needed (client work is NDA-bounded; deep-links go to `/projects/client-work/` or relevant blog posts)

### Updating Blog-to-Project Links

If a new blog post relates to a project:
1. Add post slug to `blog_posts` list in `PROJECT_META`
2. Or add project's `blog_tags` to post's `tags` in `POST_META`
3. Re-run both scripts: `python3 build_blog.py && python3 build_projects.py`

## Files Modified

- `build_blog.py` — Updated nav from `/#projects` → `/projects/`
- `index.html` — Updated nav, added "View all projects" buttons to project grids
- Created `build_projects.py` — New build script
- Created `/projects/` directory with 4 generated HTML files

## Next Steps (Phase 3-4)

1. **Homepage restructuring** — Reorganize hero, add credibility signals section
2. **Resource page** — `/resources.html` with recommended reading, tools, standards
3. **Project back-links** — Add "Part of [project]" breadcrumb to related blog posts
4. **Client case studies** — Expand client work summaries with anonymized metrics
5. **SEO & structured data** — Add schema.org markup for projects (CreativeWork or SoftwareSourceCode types)

---

## Document History

- Created: May 31, 2026 (Phase 2-3 completion)
- Mirrors: CREDITS_SYSTEM.md, BLOG_ENHANCEMENTS.md

