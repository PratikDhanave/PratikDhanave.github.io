# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Site Overview

- **URL:** https://pratikdhanave.com
- **Type:** Custom Python-based static site generator (not Jekyll, Hugo, or any off-the-shelf SSG)
- **Hosting:** GitHub Pages from `master` branch
- **CI/CD:** `.github/workflows/publish-blog.yml` auto-runs `build_blog.py` when `blog/source/*.md` changes

---

## Build Commands

```bash
# Regenerate all blog posts, tag pages, archive pages, RSS feed
python3 build_blog.py

# Regenerate sitemaps (run after build_blog.py to pick up new tag pages)
python3 build_sitemap.py

# Regenerate project pages
python3 build_projects.py

# Preview locally
python3 -m http.server 8765
```

No install step needed beyond `pip install markdown` (Python 3.9+, standard library otherwise).

---

## Architecture

The site has two distinct content tiers:

### 1. Static pages (manually edited HTML)
`index.html`, `about/`, `resume/`, `projects/`, `speaking/`, `resources/`, `articles/`, `certifications/`, `404.html` — edit these files directly. They are never touched by the build scripts.

### 2. Generated content (driven by `build_blog.py`)
All output in `blog/posts/`, `blog/tags/`, `blog/archive/`, `blog/feed.xml`, and `blog/popular-posts.json` is fully regenerated on each run. **Never hand-edit files in these directories** — changes will be overwritten.

---

## How the Blog Build Works

`build_blog.py` is the single source of truth for all blog content. Key structures:

- **`POST_META` dict** — keyed by source filename (e.g. `"2026-06-01-my-post.md"`), contains `slug`, `date`, `tags`, `audience`, `excerpt`, `citations`. Adding a new post requires a new entry here.
- **`POST_POPULARITY` dict** — maps slug → rank, used to build `blog/popular-posts.json`.
- Markdown source files live in `blog/source/` following the naming convention `YYYY-MM-DD-slug.md`.
- 108 legacy posts exist only as HTML (no markdown source); their metadata is still in `POST_META` with an empty or missing source file — the script handles this gracefully.
- HTML templates are f-strings inside the script (`POST_CSS`, `NAV_HTML`, `SITE_FOOTER`, `render_post_html()`, `render_tag_page()`, `render_index_html()`, `render_rss_feed()`). To change layout or design, edit these functions — there is no separate template file.

### Adding a new blog post

1. Create `blog/source/YYYY-MM-DD-slug.md` with an H1 title, optional italic subtitle on line 2, then body.
2. Add an entry to `POST_META` in `build_blog.py`.
3. Run `python3 build_blog.py && python3 build_sitemap.py`.
4. Commit everything including the generated HTML.

---

## SEO & Structured Data

Every generated blog post includes a `BlogPosting` JSON-LD schema. Tag pages with 5+ posts get a `CollectionPage` schema; those with <3 posts get `<meta name="robots" content="noindex">`. Static pages embed `Person`, `BreadcrumbList`, or `SoftwareApplication` schemas — these must be maintained manually.

**Pending placeholders** (require Google account setup):
- GA4 Measurement ID: search for `G-XXXXXXXXXX` — appears in `build_blog.py` template and 9 static HTML files
- Google Search Console: search for `YOUR_VERIFICATION_CODE` — appears in `index.html`

---

## `build_projects.py` — Dependency Note

This script imports `SITE_ROOT`, `NAV_HTML`, `SITE_FOOTER`, `POST_CSS`, and `POST_META` directly from `build_blog.py`. Changes to those symbols in `build_blog.py` affect project page rendering.

---

## Sitemap Strategy

`build_sitemap.py` generates three sub-sitemaps + an index:
- `sitemap-pages.xml` — 9 static pages
- `sitemap-blog.xml` — all 117 blog post URLs
- `sitemap-tags.xml` — only tag pages with ≥3 posts (avoids thin-content indexing)

`lastmod` dates come from `git log` per file; falls back to today with a stderr warning if a file has no git history.
