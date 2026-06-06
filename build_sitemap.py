#!/usr/bin/env python3
"""
build_sitemap.py — Generate comprehensive split sitemaps for pratikdhanave.github.io.

Scans all HTML files, extracts dates from paths/content, and generates:
  - sitemap-pages.xml   (main pages)
  - sitemap-blog.xml    (all blog posts)
  - sitemap-articles.xml (articles)
  - sitemap-tags.xml    (tag pages with 3+ posts)
  - sitemap-index.xml   (index pointing to all sub-sitemaps)

Run from the site repo root after build_blog.py.
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

SITE_ROOT = Path(__file__).parent.resolve()
SITE_URL = "https://pratikdhanave.github.io"


def git_last_modified(file_path):
    """Get last commit date for a file from git history."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%aI", "-1", "--", str(file_path)],
            capture_output=True, text=True, cwd=SITE_ROOT
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:10]  # YYYY-MM-DD
    except Exception:
        pass
    return datetime.now().strftime("%Y-%m-%d")


def make_sitemap(urls, filename):
    """Write a sitemap XML file."""
    entries = []
    for url, lastmod, changefreq, priority in urls:
        entries.append(f"""  <url>
    <loc>{escape(url)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(entries)}
</urlset>
"""
    out_path = SITE_ROOT / filename
    out_path.write_text(xml)
    print(f"  wrote {filename} ({len(urls)} URLs)")
    return out_path


def make_sitemap_index(sitemaps):
    """Write a sitemap index XML file."""
    entries = []
    now = datetime.now().strftime("%Y-%m-%d")
    for sitemap_url in sitemaps:
        entries.append(f"""  <sitemap>
    <loc>{escape(sitemap_url)}</loc>
    <lastmod>{now}</lastmod>
  </sitemap>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(entries)}
</sitemapindex>
"""
    out_path = SITE_ROOT / "sitemap-index.xml"
    out_path.write_text(xml)
    print(f"  wrote sitemap-index.xml ({len(sitemaps)} sitemaps)")


def collect_main_pages():
    """Collect main static pages."""
    pages = [
        ("/", "index.html", "daily", "1.0"),
        ("/blog/", "blog/index.html", "daily", "0.9"),
        ("/articles/", "articles/index.html", "weekly", "0.9"),
        ("/projects/", "projects/index.html", "weekly", "0.8"),
        ("/resume/", "resume/index.html", "monthly", "0.7"),
        ("/about/", "about/index.html", "monthly", "0.7"),
        ("/speaking/", "speaking/index.html", "monthly", "0.7"),
        ("/resources/", "resources/index.html", "monthly", "0.6"),
        ("/certifications/", "certifications/index.html", "monthly", "0.5"),
    ]
    urls = []
    for path, file_rel, changefreq, priority in pages:
        file_path = SITE_ROOT / file_rel
        if file_path.exists():
            lastmod = git_last_modified(file_path)
            urls.append((f"{SITE_URL}{path}", lastmod, changefreq, priority))
    return urls


def collect_blog_posts():
    """Collect all blog posts from blog/posts/ directory."""
    posts_dir = SITE_ROOT / "blog" / "posts"
    urls = []
    if not posts_dir.exists():
        return urls

    for html_file in sorted(posts_dir.glob("*.html")):
        slug = html_file.stem
        url = f"{SITE_URL}/blog/posts/{slug}.html"
        lastmod = git_last_modified(html_file)

        # Assign priority based on year from lastmod
        year = int(lastmod[:4]) if lastmod else 2024
        if year >= 2026:
            priority = "0.8"
        elif year >= 2025:
            priority = "0.7"
        else:
            priority = "0.6"

        urls.append((url, lastmod, "monthly", priority))

    # Also collect date-based blog URLs (blog/YYYY/MM/DD/slug/)
    for index_html in sorted(SITE_ROOT.glob("blog/20??/??/??/*/index.html")):
        rel = index_html.relative_to(SITE_ROOT)
        url = f"{SITE_URL}/{rel.parent}/"
        lastmod = git_last_modified(index_html)
        year = int(lastmod[:4]) if lastmod else 2024
        priority = "0.8" if year >= 2026 else "0.7" if year >= 2025 else "0.6"
        urls.append((url, lastmod, "monthly", priority))

    return urls


def collect_articles():
    """Collect article pages."""
    articles_dir = SITE_ROOT / "articles"
    urls = []
    if not articles_dir.exists():
        return urls

    # Main articles index
    index_file = articles_dir / "index.html"
    if index_file.exists():
        # Already in main pages, skip
        pass

    # Individual article pages (look for subdirectories with index.html)
    for article_dir in sorted(articles_dir.iterdir()):
        if article_dir.is_dir():
            index_html = article_dir / "index.html"
            if index_html.exists():
                rel = article_dir.relative_to(SITE_ROOT)
                url = f"{SITE_URL}/{rel}/"
                lastmod = git_last_modified(index_html)
                urls.append((url, lastmod, "monthly", "0.8"))

    return urls


def collect_tag_pages(min_posts=3):
    """Collect tag pages that have enough posts to be indexed."""
    tags_dir = SITE_ROOT / "blog" / "tags"
    urls = []
    if not tags_dir.exists():
        return urls

    for tag_dir in sorted(tags_dir.iterdir()):
        if not tag_dir.is_dir():
            continue
        index_html = tag_dir / "index.html"
        if not index_html.exists():
            continue

        # Count post-cards in the tag page to determine if it qualifies
        content = index_html.read_text(errors="ignore")
        post_count = content.count('class="post-card"')

        if post_count >= min_posts:
            rel = tag_dir.relative_to(SITE_ROOT)
            url = f"{SITE_URL}/{rel}/"
            lastmod = git_last_modified(index_html)
            urls.append((url, lastmod, "weekly", "0.5"))

    return urls


def main():
    print("Building sitemaps...")

    # Collect URLs
    pages = collect_main_pages()
    blog_posts = collect_blog_posts()
    articles = collect_articles()
    tags = collect_tag_pages(min_posts=3)

    # Write individual sitemaps
    sitemaps = []

    if pages:
        make_sitemap(pages, "sitemap-pages.xml")
        sitemaps.append(f"{SITE_URL}/sitemap-pages.xml")

    if blog_posts:
        make_sitemap(blog_posts, "sitemap-blog.xml")
        sitemaps.append(f"{SITE_URL}/sitemap-blog.xml")

    if articles:
        make_sitemap(articles, "sitemap-articles.xml")
        sitemaps.append(f"{SITE_URL}/sitemap-articles.xml")

    if tags:
        make_sitemap(tags, "sitemap-tags.xml")
        sitemaps.append(f"{SITE_URL}/sitemap-tags.xml")

    # Write sitemap index
    if sitemaps:
        make_sitemap_index(sitemaps)

    print(f"\nTotal: {len(pages)} pages + {len(blog_posts)} blog posts + {len(articles)} articles + {len(tags)} tag pages")


if __name__ == "__main__":
    main()
