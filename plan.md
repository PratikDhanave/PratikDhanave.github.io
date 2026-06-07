# SEO Master Plan for pratikdhanave.github.io

**Date:** June 6, 2026
**Status:** Awaiting Approval
**Approach:** Deep audit-driven, prioritized by real impact

---

## Executive Summary

After a thorough audit of the site (403 HTML files, build scripts, sitemaps, schemas, robots.txt, and social meta), the biggest finding is this: **the foundation is strong but there are several critical bugs undermining it.** The og:image file referenced by every page doesn't exist. 130+ blog posts are invisible to sitemaps. 233 tag pages risk a thin-content penalty. There's no analytics to measure anything. The plan below fixes the critical bugs first, then builds on the strong foundation.

---

## Part 1: Audit Findings (What's Actually Wrong)

### CRITICAL (Actively Hurting SEO Right Now)

| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| C1 | **og-default.png does not exist** | Every page references `https://pratikdhanave.github.io/og-default.png` in OG/Twitter meta tags. The file is not in the repo. | Social shares on LinkedIn, Twitter, Slack show no preview image. Severely reduces click-through from social. |
| C2 | **130+ blog posts missing from sitemap** | `sitemap.xml` lists ~21 blog posts. `find` shows 403 index.html files across blog/. Hundreds of posts rely solely on internal links for discovery. | Google may never crawl deep posts. Sitemap is the primary discovery mechanism for large sites. |
| C3 | **No analytics or Search Console** | Zero `gtag`, `ga`, or `google-site-verification` found in any HTML file. | Cannot measure traffic, rankings, crawl errors, or Core Web Vitals in the field. Flying blind. |
| C4 | **233 tag pages, many with 1-2 posts** | Tags like "aadhaar", "accounting", "aml" have minimal content. No schema, no unique meta descriptions (template-generated). | Google's helpful content system penalizes thin, auto-generated pages. Wastes crawl budget. |

### HIGH (Significant Missed Opportunities)

| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| H1 | **BlogPosting schema missing `dateModified`** | Schema only has `datePublished`. `build_blog.py` never sets `dateModified`. | Google can't tell when content was refreshed. Freshness is a ranking factor. |
| H2 | **BlogPosting schema missing `publisher`** | No `publisher` field with Organization type, name, logo. | Google requires publisher for full rich result eligibility. |
| H3 | **External links have no `rel` attributes** | Links to LinkedIn, GitHub, citations all lack `rel="noopener noreferrer"`. `build_blog.py` line 1675 uses `target="_blank"` without rel. | Referrer leakage + security issue. Minor SEO signal but affects trust. |
| H4 | **No `<meta name="robots">` on blog/tag pages** | Blog posts and tag pages have no robots directive. Homepage does. | Ambiguous crawl signal. Best practice is explicit `index, follow`. |
| H5 | **About page is a meta-refresh redirect** | `/about/index.html` uses `<meta http-equiv="refresh" content="0; url=/#about">` with `noindex`. | Meta-refresh is the weakest redirect type. Wastes a valuable E-E-A-T page. Google Cloud Next speakers deserve a real about page. |
| H6 | **No RSS/Atom feed** | Only `feed.json` (JSON Feed 1.1). No XML RSS/Atom. | Many aggregators, podcast apps, and Google News prefer RSS/Atom. Limits syndication reach. |
| H7 | **robots.txt blocks AhrefsBot & SemrushBot** | Lines 23-30 block these crawlers. | You can't see your own backlink profile in Ahrefs/Semrush free tools. Consider unblocking. |
| H8 | **robots.txt sets Crawl-delay for Googlebot** | `Crawl-delay: 1` for Googlebot. | Google officially ignores Crawl-delay. It does nothing but signals you don't want fast crawling — counterproductive for a static site that handles any load. |

### MEDIUM (Polish & Optimization)

| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| M1 | Tag pages have no schema.org markup | Zero structured data on 233 tag pages. | Missed opportunity for CollectionPage rich results. |
| M2 | No custom 404 page | No `404.html` in repo root. GitHub shows default. | Lost users on broken links. No recovery path. |
| M3 | All pages share one OG image | Even once fixed, every page will use the same generic image. | No visual differentiation in social feeds. Reduces social CTR. |
| M4 | Sitemap `lastmod` dates are all static | Every URL shows `2026-06-04` regardless of actual modification. | Google may ignore `lastmod` if it detects static dates, defeating the purpose. |
| M5 | No `inLanguage` in BlogPosting schema | Missing from all post schemas. | Minor signal but helps Google understand content language definitively. |

---

## Part 2: Implementation Plan

### Phase 0: Fix Critical Bugs (Do Before Anything Else)

**Why this is Phase 0:** These are bugs, not optimizations. They actively undermine all the SEO work already done.

#### 0.1 Create og-default.png
- Generate a branded 1200x630px Open Graph image
- Design: Site name, tagline ("Multi-Agent AI Engineer"), clean professional layout
- Place in repo root as `og-default.png`
- **Verify:** After deploy, test with https://cards-dev.twitter.com/validator and https://developers.facebook.com/tools/debug/

#### 0.2 Generate comprehensive sitemap with ALL blog posts
- Write a script (or extend `build_blog.py`) that:
  - Scans all `blog/YYYY/MM/DD/*/index.html` files
  - Extracts dates from the URL path
  - Generates sitemap entries with proper `lastmod` from git history
  - Assigns priority: 2026 posts = 0.8, 2025 = 0.7, 2024 = 0.6
- Create `sitemap-index.xml` referencing:
  - `sitemap-pages.xml` (main pages, ~15 URLs)
  - `sitemap-blog.xml` (all blog posts, ~150+ URLs)
  - `sitemap-articles.xml` (existing articles sitemap, ~19 URLs)
  - `sitemap-tags.xml` (only tags with 3+ posts, see 0.4)
- Update `robots.txt` to reference only `sitemap-index.xml`
- **Files:** New `build_sitemap.py`, updated `robots.txt`

#### 0.3 Add Google Analytics 4 + Search Console verification
- Add GA4 snippet to the HTML template in `build_blog.py` (all blog posts get it)
- Add GA4 to manually-maintained pages (homepage, resume, projects, articles, etc.)
- Add `<meta name="google-site-verification" content="...">` to homepage
- **Note:** The actual GA4 property ID and verification code require your Google account. I'll add placeholder tags you fill in.
- **Files:** `build_blog.py` (template `<head>`), `index.html`, all main page HTMLs

#### 0.4 Thin tag page strategy
- **Audit:** Programmatically count posts per tag
- **Action:** Tags with fewer than 3 posts get `<meta name="robots" content="noindex, follow">`
  - Still crawlable (follow) so link equity flows
  - But not indexed, so Google doesn't see them as thin content
- Tags with 3+ posts remain indexable
- **Estimated split:** ~80 tags indexed, ~153 tags noindexed
- **Files:** `build_blog.py` (tag page template)

---

### Phase 1: Schema & Metadata Hardening

#### 1.1 Fix BlogPosting schema in build_blog.py
Add to every blog post's JSON-LD:
```json
{
  "dateModified": "<git last-commit date or publish date>",
  "inLanguage": "en",
  "publisher": {
    "@type": "Person",
    "name": "Pratik Dhanave",
    "url": "https://pratikdhanave.github.io"
  }
}
```
- **Files:** `build_blog.py` (schema generation section)

#### 1.2 Add meta robots to all generated pages
- Blog posts: `<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">`
- Tag pages (3+ posts): Same as above
- Tag pages (<3 posts): `<meta name="robots" content="noindex, follow">`
- **Files:** `build_blog.py` (post template + tag template)

#### 1.3 Add `rel="noopener noreferrer"` to external links
- Modify `build_blog.py` to post-process generated HTML:
  - Any `<a>` with `href` starting with `http` and `target="_blank"` gets `rel="noopener noreferrer"`
  - Citation links get the same treatment
- Also fix existing external links in manually-maintained pages
- **Files:** `build_blog.py`, `index.html`, article pages

#### 1.4 Add CollectionPage schema to qualifying tag pages
- Only tags with 5+ posts get CollectionPage schema
- Include: name, description, numberOfItems, hasPart (list of article headlines)
- **Files:** `build_blog.py` (tag template)

---

### Phase 2: Robots.txt & Crawl Optimization

#### 2.1 Remove Crawl-delay for Googlebot
- Google ignores `Crawl-delay`. Removing it is cleaner.
- Keep `Crawl-delay: 2` for generic bots (this is fine).

#### 2.2 Consider unblocking AhrefsBot and SemrushBot
- **Trade-off:** Blocking them prevents competitors from analyzing your site, but also prevents YOU from using their free tools to see your backlink profile
- **Recommendation:** Unblock them. The backlink visibility benefit outweighs the risk for a personal portfolio site. Competitors aren't your concern here.

#### 2.3 Clean up robots.txt
```
User-agent: *
Allow: /
Disallow: /search/
Disallow: /404.html

User-agent: Googlebot
Allow: /

Sitemap: https://pratikdhanave.github.io/sitemap-index.xml
```
- Remove: `Request-rate` (non-standard), `/thank-you/` (doesn't seem to exist), misplaced `Crawl-delay` at the end (applies to no user-agent block)

---

### Phase 3: Content & E-E-A-T

#### 3.1 Create a real About page (`/about/index.html`)
- Replace the meta-refresh redirect with a full page
- Content:
  - Professional bio (3-4 paragraphs)
  - Google Cloud Next 2022 speaker credential (with conference link)
  - Tata Group FinOps engagement summary
  - Open-source contributions (HarbourBridge, etc.)
  - Certifications list
  - Links to GitHub, LinkedIn, Twitter
- Schema: Person with `sameAs`, `alumniOf`, `worksFor`, `award`
- This is the single most important E-E-A-T signal for Google

#### 3.2 Create a custom 404 page (`/404.html`)
- GitHub Pages automatically serves `/404.html` for missing URLs
- Include: Apology message, search/navigation links, popular articles, homepage link
- Add BreadcrumbList schema
- Keep the same site nav and styling

#### 3.3 Add RSS/Atom feed
- Generate `blog/feed.xml` alongside existing `feed.json`
- Include: Last 20 posts with full content, proper `<pubDate>`, `<guid>`
- Add `<link rel="alternate" type="application/rss+xml">` to all page `<head>` sections
- Helps with: Google News discovery, feed reader syndication, podcast app indexing
- **Files:** `build_blog.py` (new feed generation function), all templates (link tag)

#### 3.4 Add FAQ schema to top 5 articles
- Select articles with the highest search potential:
  1. Multi-agent AI architecture patterns
  2. BigQuery cost optimization / FinOps
  3. GDPR for agentic AI
  4. Cloud Spanner migration patterns
  5. Agent security / governance
- Add 3-5 FAQs per article as `FAQPage` schema
- **Files:** Individual article HTML files

---

### Phase 4: Build System Improvements

#### 4.1 Automate sitemap generation in build pipeline
- Create `build_sitemap.py` that:
  - Walks all HTML directories
  - Extracts dates from file paths or HTML meta
  - Pulls `lastmod` from `git log --format=%aI -1 -- <file>`
  - Generates split sitemaps + sitemap index
- Run after `build_blog.py` and `build_projects.py`

#### 4.2 Add related posts to blog post footer
- `build_blog.py` already has `find_related_posts()` (lines 55-68) but verify it's being called
- Ensure every post renders 3 related posts with title + date + link
- This increases internal linking and reduces bounce rate

#### 4.3 Per-post OG images (optional enhancement)
- Generate unique OG images per blog post using a template:
  - Post title overlaid on a branded background
  - Can use Python Pillow or a simple HTML-to-image approach
- Store in `blog/og/` directory
- Update `build_blog.py` to reference per-post images
- **Trade-off:** Adds 150+ image files to repo (~50-100KB each = 10-15MB). Worth it for social CTR.

---

### Phase 5: Off-Page Execution (Manual Steps)

These require your action outside the codebase:

#### 5.1 Google Search Console Setup
1. Go to https://search.google.com/search-console
2. Add property: `https://pratikdhanave.github.io`
3. Verify via HTML meta tag (added in Phase 0.3)
4. Submit `sitemap-index.xml`
5. Use "URL Inspection" to request indexing for top 10 pages:
   - Homepage, Resume, Articles hub, Blog hub, Projects hub
   - Top 5 blog posts by content quality
6. Monitor "Coverage" for crawl errors within 48 hours

#### 5.2 Bing Webmaster Tools
1. Go to https://www.bing.com/webmasters
2. Import from Google Search Console (easiest)
3. Submit sitemap
4. Bing powers DuckDuckGo and Yahoo results

#### 5.3 Social Profile Cross-linking
- GitHub bio: Add site URL + "Multi-Agent AI Engineer" title
- LinkedIn: Add site URL to Contact Info + Featured section
- Twitter/X bio: Add site URL
- All must use consistent name/title matching the Person schema

#### 5.4 Backlink Execution (already planned)
- Execute the existing strategy in `articles/BACKLINK_STRATEGY.md`
- Priority: DEV.to and Hashnode first (auto-accept, highest ROI)
- Track published URLs in a spreadsheet

---

## Part 3: Implementation Sequence

```
Week 1 (Critical Fixes):
  Day 1:  Phase 0.1 - Create og-default.png
  Day 1:  Phase 0.3 - Add GA4 + verification placeholders
  Day 1:  Phase 2   - Fix robots.txt
  Day 2:  Phase 0.2 - Build sitemap generator, generate full sitemap
  Day 2:  Phase 0.4 - Audit tag pages, add noindex to thin ones
  Day 3:  Phase 1.1 - Fix BlogPosting schema (dateModified, publisher)
  Day 3:  Phase 1.2 - Add meta robots to all templates
  Day 3:  Phase 1.3 - Fix external link rel attributes
  Day 4:  Phase 3.2 - Create custom 404 page
  Day 5:  Your action: Set up GA4 property, Search Console (5.1), Bing (5.2)

Week 2 (Content & Structure):
  Day 6:  Phase 3.1 - Create real About page
  Day 7:  Phase 3.3 - Add RSS/Atom feed
  Day 8:  Phase 1.4 - Add CollectionPage schema to tag pages
  Day 9:  Phase 4.2 - Verify related posts rendering
  Day 10: Phase 3.4 - Add FAQ schema to top 5 articles

Week 3+ (Ongoing):
  Phase 4.3 - Per-post OG images (if approved)
  Phase 5.3 - Social profile updates (your action)
  Phase 5.4 - Backlink execution (your action)
  Monitor Search Console data and adjust
```

---

## Part 4: Files Modified / Created

### Modified (Build Scripts - Highest Leverage)
| File | Changes |
|------|---------|
| `build_blog.py` | Add meta robots, fix BlogPosting schema, add rel attributes to external links, add RSS generation, GA4 snippet, verification meta tag |
| `robots.txt` | Remove Crawl-delay for Googlebot, unblock Ahrefs/Semrush, point to sitemap-index.xml, clean up |
| `index.html` | Add GA4, verification meta, RSS link tag |
| `resume/index.html` | Add GA4, meta robots, RSS link tag |
| `projects/index.html` | Add GA4, meta robots, RSS link tag |
| `articles/index.html` | Add GA4, meta robots, RSS link tag |
| `speaking/index.html` | Add GA4, meta robots, RSS link tag |
| `resources/index.html` | Add GA4, meta robots, RSS link tag |
| `blog/index.html` | Add GA4, meta robots, RSS link tag |

### Created (New Files)
| File | Purpose |
|------|---------|
| `og-default.png` | Branded Open Graph image (1200x630px) |
| `build_sitemap.py` | Automated sitemap generator |
| `sitemap-index.xml` | Sitemap index pointing to split sitemaps |
| `sitemap-pages.xml` | Main pages sitemap |
| `sitemap-blog.xml` | All blog posts sitemap |
| `sitemap-tags.xml` | Tag pages sitemap (3+ posts only) |
| `about/index.html` | Real About page (replaces redirect) |
| `404.html` | Custom 404 error page |
| `blog/feed.xml` | RSS/Atom feed |

### Regenerated (via build scripts)
| Scope | Count |
|-------|-------|
| Blog post HTML files | ~150+ (schema + meta fixes) |
| Tag page HTML files | ~233 (noindex on thin, schema on qualifying) |

---

## Part 5: Success Metrics

| Metric | Baseline (Now) | Target (3 Months) | How to Measure |
|--------|----------------|-------------------|----------------|
| Indexed pages | Unknown (likely <50) | 200+ | Google Search Console > Coverage |
| Daily impressions | Unknown (likely 0-5) | 100+ | Search Console > Performance |
| CTR from search | Unknown | 3-5% | Search Console > Performance |
| Keywords in top 50 | Unknown | 50+ | Search Console > Performance |
| Social card rendering | Broken (no image) | Working on all platforms | Twitter Card Validator |
| Core Web Vitals | Good (lab) | Good (field) | Search Console > CWV |
| Referring domains | Unknown | 10+ | Ahrefs free / Search Console > Links |
| RSS subscribers | 0 | Any | Feed analytics |

---

## Part 6: What This Plan Does NOT Do

- **No paid ads** (Google Ads, LinkedIn Ads)
- **No video SEO** (YouTube)
- **No local SEO** (Google Business Profile — not applicable)
- **No international SEO** (single language site)
- **No content rewriting** (existing content quality is strong)
- **No JavaScript framework migration** (static HTML is ideal for SEO)

---

## Part 7: Custom Domain Migration (pratikdhanave.com)

**Status:** Code changes DONE. Domain not yet purchased.

All URLs in the codebase have been migrated from `pratikdhanave.github.io` → `pratikdhanave.com`. The CNAME file has been removed until the domain is purchased to prevent redirect to an unresolvable domain.

### When Ready to Activate

#### Step 1: Buy the Domain
- **Registrar:** Namecheap (recommended for ease of use + 24/7 human support)
- **Domain:** `pratikdhanave.com` (confirmed available as of June 7, 2026)
- **Cost:** ~$10-12/year
- Enable auto-renew and free WHOIS privacy

#### Step 2: Configure DNS at Namecheap
Set these DNS records (Advanced DNS → Add New Record):

| Type | Host | Value |
|------|------|-------|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | pratikdhanave.github.io |

#### Step 3: Add CNAME File to Repo
```bash
echo "pratikdhanave.com" > CNAME
git add CNAME
git commit -m "Add CNAME for pratikdhanave.com custom domain"
git push
```

#### Step 4: Enable in GitHub
- Go to: github.com/PratikDhanave/PratikDhanave.github.io → Settings → Pages
- Custom domain: enter `pratikdhanave.com`
- Check "Enforce HTTPS"
- Wait ~10 minutes for SSL certificate provisioning

#### Step 5: Set Up Email (Free)
- In Namecheap dashboard → Email Forwarding (or use Cloudflare Email Routing if DNS is moved)
- Create: `pratik@pratikdhanave.com` → forwards to your Gmail
- Set up Gmail "Send As" to reply from the custom address

#### Step 6: Update Google Search Console
- Add `pratikdhanave.com` as a new property in Search Console
- Submit `sitemap-index.xml`
- Request indexing for top pages
- The old `pratikdhanave.github.io` property will show redirect data

### What's Already Done (code changes committed)
- [x] All canonical URLs updated to pratikdhanave.com
- [x] All Open Graph URLs updated
- [x] All Twitter Card URLs updated
- [x] All JSON-LD schema URLs updated
- [x] All RSS feed URLs updated
- [x] All sitemap URLs updated
- [x] robots.txt updated
- [x] build_blog.py SITE_ROOT updated (affects 200+ generated pages)
- [x] build_sitemap.py updated
- [x] build_projects.py updated
- [x] 245 legacy blog HTML files updated
- [x] blog/feed.json updated
- [x] CLAUDE.md updated

### Optional: Also Buy pratikdhanave.ai
- Available as of June 7, 2026
- Cost: ~$70-80/year
- Set up as redirect to pratikdhanave.com
- Reinforces AI positioning in conversations

---

## Key Architectural Decision

**All template changes go through `build_blog.py`**, not individual HTML files. The build script generates ~383 HTML files (150+ posts, 233 tag pages). Editing the template once propagates to all. The manually-maintained pages (homepage, resume, projects, articles, speaking, resources) are edited directly since they're hand-crafted HTML.
