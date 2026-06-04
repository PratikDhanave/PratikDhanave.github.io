---
title: "News Platform at Scale: Dainik Bhaskar's 5M+ Daily Readers"
description: "Production-grade technical deep-dive on NewsPlatformatScale:DainikBhaskar's5M+DailyReaders"
keywords: ["44-news-platform"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
---

# News Platform at Scale: Dainik Bhaskar's 5M+ Daily Readers

**Dainik Bhaskar is India's largest Hindi newspaper (5M+ daily readers).** When Bhaskar went digital, they needed a backend that could handle peak traffic (60K concurrent readers), deliver fresh content in < 500ms, and monetize through targeted advertising.

---

## The Architecture

```
Content Writers
    ↓
Article API (Go, gRPC)
    ↓
PostgreSQL (read replicas for scale)
    ↓
Redis Cache (60-second TTL)
    ↓
CDN (CloudFlare for global distribution)
    ↓
Mobile App / Web
```

---

## Multi-Edition API in Go

```go
type Article struct {
    ID        string    `json:"id"`
    Title     string    `json:"title"`
    Body      string    `json:"body"`
    Edition   string    `json:"edition"`   // Hindi/English/Regional
    CreatedAt time.Time `json:"created_at"`
}

func (a *ArticleService) GetArticle(ctx context.Context, id string) (*Article, error) {
    // 1. Check cache
    cached, err := redis.Get(ctx, fmt.Sprintf("article:%s", id))
    if err == nil {
        return unmarshalshal(cached)
    }
    
    // 2. Query database (read replica for scale)
    article, err := db.QueryRow(ctx, `
        SELECT id, title, body, edition FROM articles WHERE id = $1
    `, id).Scan(&a.ID, &a.Title, &a.Body, &a.Edition)
    
    if err != nil {
        return nil, err
    }
    
    // 3. Cache for 60 seconds
    redis.Set(ctx, fmt.Sprintf("article:%s", id), marshal(article), 60*time.Second)
    
    return article, nil
}
```

---

## Ad Revenue Analytics

```python
import bigquery

def analyze_ad_revenue():
    """Track ad impressions, clicks, and revenue."""
    
    query = """
    SELECT
        DATE(event_time) as date,
        edition,
        device_type,
        COUNT(*) as impressions,
        SUM(CASE WHEN clicked THEN 1 ELSE 0 END) as clicks,
        SUM(revenue) as total_revenue,
        SUM(revenue) / COUNT(*) as cpm
    FROM ad_events
    WHERE DATE(event_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY date, edition, device_type
    ORDER BY total_revenue DESC
    """
    
    results = bigquery.query(query)
    
    for row in results:
        print(f"""
        Date: {row['date']}
        Edition: {row['edition']}
        CPM: ${row['cpm']:.2f}
        Revenue: ${row['total_revenue']:.2f}
        """)
```

---

**Tags:** #ContentPlatform #Scaling #Caching #BigData #MultiLanguage

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** DB Corp (Dainik Bhaskar)
