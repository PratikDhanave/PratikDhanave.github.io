# SEO Audit & Fixes — Context for Continuation

## Project Overview

- **Site:** https://pratikdhanave.github.io
- **Type:** Custom static site (NOT Jekyll/Hugo) with Python build pipeline
- **Build scripts:** `build_blog.py` (generates 147 blog posts + 232 tag pages), `build_sitemap.py` (generates split sitemaps)
- **Hosting:** GitHub Pages (master branch)
- **Repo:** PratikDhanave/PratikDhanave.github.io

## What Was Done (Complete SEO Overhaul)

### Phase 0 — Critical Fixes
- Created `og-default.png` (1200x630 branded Open Graph image)
- Created `build_sitemap.py` for split sitemap generation
- Added GA4 placeholders to all templates and static pages (STILL PLACEHOLDER — see pending below)
- Added noindex logic for thin tag pages (<3 posts)

### Phase 1 — Schema & Metadata
- Fixed BlogPosting JSON-LD: added dateModified, publisher, inLanguage, mainEntityOfPage
- Added JSON/HTML escaping for titles and descriptions in JSON-LD and meta attributes
- Added `hasCredential` (was incorrectly `credential`) across index.html, about/index.html, resume/index.html
- Fixed `award` property (was invalid `@type: "Award"`, now plain strings)
- Added CollectionPage schema to tag pages with 5+ posts
- Added meta robots to all pages
- Added rel="noopener noreferrer" to external links
- Fixed `article:published_time` to full ISO 8601 format

### Phase 2 — Robots & Crawl
- Rewrote robots.txt (unblocked crawlers, removed invalid Disallow for 404.html)
- Removed legacy sitemap.xml (invalid, stale)
- Removed orphaned articles/sitemap.xml (all 19 URLs were 404s)
- Fixed duplicate sitemap URLs (284 → 147 unique)

### Phase 3 — Content & E-E-A-T
- Created real About page (replaced meta-refresh redirect)
- Created custom 404.html
- Added RSS feed generation
- Fixed GDPR FAQ legal error ("data processor" → "data controller")
- Fixed 6 truncated excerpts in POST_META
- Fixed RSS `&mdash;` double-encoding
- Fixed SOMA → SAMA typo on projects page
- Fixed GCN 2022 talk description on resources page
- Fixed placeholder YouTube/Slides URLs on speaking page
- Added missing og:image/twitter:image on articles page
- Added missing og:url/twitter:description on resume page
- Removed stale worksFor from resume schema
- Fixed double active nav on projects page
- Fixed nav brand href="#" → "/" on index.html

### Phase 4 — Build System
- Added `PROJECT_META = {}` (was undefined, latent NameError)
- Added `import json` and `html.escape` for safe template rendering
- Added `html.unescape()` for HTML-only post title extraction
- Added stderr warning in `git_last_modified()` fallback
- Added GA4 to 404.html

## PENDING — What Needs to Be Done Next

### 1. GA4 Measurement ID (CRITICAL)

**Current state:** All pages have `G-XXXXXXXXXX` placeholder.

**Steps to get the ID:**
1. Go to https://analytics.google.com
2. Sign in with Google account
3. Admin (gear icon) → Create → Property
4. Property name: "Pratik Dhanave Blog", set timezone/currency
5. Next → select business info → Create
6. Data collection → Web
7. Website URL: `https://pratikdhanave.github.io`, Stream name: "Main Site"
8. Create stream → copy the Measurement ID (format: `G-ABC123XYZ`)

**Files to update (replace `G-XXXXXXXXXX` with real ID):**

Static pages (manual edit):
- `index.html` (lines 15-16)
- `about/index.html`
- `resume/index.html`
- `projects/index.html`
- `speaking/index.html`
- `resources/index.html`
- `articles/index.html`
- `404.html`
- `certifications/index.html`

Build template (auto-propagates to all blog posts):
- `build_blog.py` — search for `G-XXXXXXXXXX` (appears 4 times: 2 in render_post_html, 2 in render_tag_page)

After editing build_blog.py, run:
```bash
python3 build_blog.py
python3 build_sitemap.py
```

**Quick replace command:**
```bash
# Replace in all HTML files and build_blog.py
grep -rl "G-XXXXXXXXXX" . --include="*.html" --include="*.py" | xargs sed -i '' 's/G-XXXXXXXXXX/G-YOUR_REAL_ID/g'
# Then rebuild
python3 build_blog.py && python3 build_sitemap.py
```

### 2. Google Search Console Verification (CRITICAL)

**Current state:** `index.html` has `YOUR_VERIFICATION_CODE` placeholder.

**Steps to get the code:**
1. Go to https://search.google.com/search-console
2. Add property → URL prefix → enter `https://pratikdhanave.github.io`
3. Choose HTML tag verification method
4. Copy the `content` value from the meta tag they provide

**File to update:**
- `index.html` — line 12: replace `YOUR_VERIFICATION_CODE` with actual code

**After deploying, go back to Search Console and click Verify.**

Then submit the sitemap:
1. In Search Console sidebar → Sitemaps
2. Enter: `sitemap-index.xml`
3. Click Submit

### 3. Content Decisions Still Pending (LOW PRIORITY)

These are not bugs but content inconsistencies the audit flagged:
- **Post count:** `index.html` says "All 127 posts" but also "29+ Published Articles" — pick one accurate number
- **Mentee count:** "40+ students" vs "10+ students" across pages — standardize
- **articles/index.html:** All article links point to `.md` files (will 404 in browser) — needs build step or route change
- **speaking/index.html:** "Cloud Architecture Magazine" links to own blog post — either get real external link or change label
- **speaking/index.html:** "Coming Soon" podcast placeholder — remove if no real podcast

## Build Commands

```bash
# Rebuild all blog posts (147 posts + 232 tag pages)
python3 build_blog.py

# Rebuild sitemaps (run AFTER build_blog.py)
python3 build_sitemap.py

# Commit and push
git add -A && git commit -m "message" && git push origin master
```

## Key File Locations

| File | Purpose |
|------|---------|
| `build_blog.py` | Main build script — generates all blog HTML from markdown |
| `build_sitemap.py` | Generates split sitemaps from HTML files |
| `blog/source/*.md` | Markdown source for blog posts |
| `blog/posts/*.html` | Generated blog post HTML |
| `blog/feed.xml` | Generated RSS feed |
| `sitemap-index.xml` | Sitemap index (points to 3 sub-sitemaps) |
| `robots.txt` | Crawler directives |
| `og-default.png` | Default Open Graph image (1200x630) |
| `index.html` | Homepage (manually edited) |
| `about/index.html` | About page |
| `resume/index.html` | Resume page |
| `projects/index.html` | Projects page |
| `speaking/index.html` | Speaking page |
| `resources/index.html` | Resources page |
| `articles/index.html` | Articles listing page |
| `404.html` | Custom 404 page |
