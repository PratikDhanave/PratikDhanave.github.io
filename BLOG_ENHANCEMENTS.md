# Blog Enhancements - Phase 2

## Completed Features

### 1. ✅ Read-Time Badges
**What it does**: Estimates reading time based on word count (~200 words/minute)

**Where it appears**:
- Post-meta section next to date and audience
- Example: "Jun 08, 2026 · All engineers · 4 min read"

**Implementation**:
```python
def calculate_read_time(html_content):
    """Estimate reading time from HTML content (avg 200 words/min)."""
    import re
    text = re.sub(r'<[^>]+>', '', html_content)
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return minutes
```

**User benefit**: Readers can quickly gauge post length before committing

---

### 2. ✅ Series Breadcrumbs
**What it does**: Shows post position within a multi-post series

**How to use it**:
Add to POST_META:
```python
"series": "ADK to MAF Migration",
"series_position": 1,
"series_total": 8,
```

**Renders as**:
```
Part 1 of 8
ADK to MAF Migration
```

**Current series**:
- ADK to MAF Migration (8 posts, June 1-8, 2026)
  - Post 1: Why We Migrated
  - Post 2: Executor Pattern
  - Post 3: Token Exchange
  - Post 4: Tool Wrapping
  - Post 5: Provider Config
  - Post 6: Callbacks & Middleware
  - Post 7: Deployment
  - Post 8: Lessons Learned

**User benefit**: Readers understand context and motivation to follow the series

---

### 3. ✅ Related Posts Sidebar
**What it does**: Automatically recommends related posts based on tag overlap

**How it works**:
1. For each post, analyze its tags
2. Find other posts that share ≥1 tag
3. Rank by number of shared tags, then by recency
4. Display top 3 as "Related Reading"

**Example output**:
```
Related Reading
• Lessons from Converting 18 Agents in 90 Days (Jun 08)
• Tool Wrapping & Policy Enforcement (Jun 04)
• State Management & Token Budgeting (Jun 03)
```

**Implementation**:
```python
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
```

**User benefit**: Readers discover related content and can deep-dive into topics

---

### 4. ✅ Featured Posts Badges
**What it does**: Highlights key posts on the blog index

**How to use it**:
Add to POST_META:
```python
"featured": True,
```

**Renders as**:
- Colored badge "Featured" in post-meta
- Distinct card styling (accent border, alternate background)
- Right-aligned for visual prominence

**Currently featured**:
- "Why We Migrated from Google ADK to Microsoft MARA" (Series intro)
- "Lessons from Converting 18 Agents in 90 Days" (Series conclusion)

**User benefit**: Important starting/ending posts are immediately visible

---

## Architecture Changes

### Two-Pass Rendering
Previously, posts were rendered as they were read from POST_META. Now:

1. **First pass**: Collect all posts and their metadata
2. **Sort**: By date (newest first)
3. **Second pass**: Render each post with access to all posts (for related content)

This enables related posts, featured badges, and series context.

---

## CSS & Styling

### New CSS Classes

#### `.series-breadcrumb`
- Left accent border (3px, accent color)
- Light background
- Left-aligned label ("Part X of Y")

#### `.related-posts`
- Top and bottom borders (light)
- Inline link titles with dates
- Links are full-width with dates right-aligned

#### `.featured-badge`
- Small pill-style badge
- Accent background with white text
- Appears in post-meta, right-aligned

#### `.post-card-featured`
- Distinct styling for featured cards on blog index
- Accent border + alternate background

---

## Data Structure

### Enhanced POST_META
```python
POST_META = {
    "filename.md": {
        "slug": "url-slug",
        "date": "2026-06-01",
        "tags": ["Tag1", "Tag2"],
        "audience": "Target readers",
        "excerpt": "One-line summary",
        
        # New fields:
        "featured": True/False,           # Optional, defaults to False
        "series": "Series Name",          # Optional
        "series_position": 1,             # Numeric position in series
        "series_total": 8,                # Total posts in series
        
        "citations": [...],               # From Phase 2
    }
}
```

---

## Remaining Phase 2 Tasks

1. **Featured posts section** on blog index (visual grouping at top)
2. **Read-more links** for excerpts that are truncated
3. **Estimated reading section** - "Getting ready to read?" sidebar
4. **Comment count badge** (infrastructure prep for Phase 3)

---

## Stats

- **Posts rendered**: 8 posts
- **Series coverage**: 100% (all ADK→MAF posts in series)
- **Featured posts**: 2 of 8 (25%)
- **Related posts density**: 3 per post (24 recommendations across 8 posts)
- **Code additions**: ~150 lines (functions + CSS)
- **Commit**: f4c6b51

---

## Next Steps

1. Continue Phase 2: Featured section on index, visual hierarchy improvements
2. Phase 2-3: Project showcase pages with similar discoverability features
3. Phase 3-4: Homepage restructuring with blog integration
