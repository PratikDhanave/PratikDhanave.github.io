# Web and CDN Caching

*Every time a web page loads instantly on a repeat visit, or a video streams smoothly from halfway around the world, caching is the reason. The web is layered with caches — in your browser, at CDN edge servers near you, in front of origin servers — all applying the same caching principle to make the internet fast. And remarkably, much of it is coordinated by a few HTTP headers that let servers tell caches exactly what to store and for how long. Understanding web and CDN caching is understanding how the internet stays fast at global scale.*

**Web caching** and **CDNs** (Content Delivery Networks) apply caching across the internet to make the web fast. This post covers HTTP caching (how caches are controlled by headers), the browser cache, CDNs (caching content near users at the edge), and how these layers work together. It's caching applied to the web — the same principles (from earlier posts) at internet scale, coordinated by HTTP. This is caching most engineers interact with constantly.

## HTTP caching and cache headers

The web has built-in caching coordinated by **HTTP headers** — the servers tell caches *what* to store and *for how long*, making web caching standardized and controllable:

- **HTTP defines how responses are cached.** The HTTP protocol has *built-in caching* — responses can be *cached* by browsers and intermediary caches, controlled by *HTTP headers* the server sends. These headers tell caches whether a response is cacheable, for how long, and how to validate it. So web caching is *standardized* into HTTP, coordinated by headers rather than ad-hoc. The server controls caching via headers. This is elegant: the protocol itself carries the caching rules.
- **Cache-Control: the key header.** The `Cache-Control` header is the primary way servers control caching — specifying whether a response is cacheable (`public`/`private`/`no-store`), for how long (`max-age` — essentially a TTL, from the eviction post), and revalidation behavior. It's how the server dictates the caching policy for each response. `Cache-Control: max-age=3600` says "cache this for an hour." Cache-Control is the main lever for HTTP caching.
- **Validation: ETags and conditional requests.** Beyond expiry, HTTP supports *validation* — an *ETag* (a version identifier for a resource) lets a cache *check* with the server whether its cached copy is still current (a conditional request: "give me this only if it changed since this ETag"). If unchanged, the server responds "not modified" (no re-sending the data — saving bandwidth); if changed, it sends the new version. Validation lets caches *reuse* data while *checking freshness* cheaply — a middle ground between blind caching and refetching. ETags/conditional requests handle "is my cached copy still good?" efficiently.

HTTP caching is built into the protocol, coordinated by headers — `Cache-Control` (cacheable? how long? — a TTL) and validation via ETags/conditional requests (cheaply check if a cached copy is still current) — letting servers control exactly how responses are cached. This standardized, header-driven caching is what makes web caching work across the internet's many caches. The nearest cache to the user is the browser.

## The browser cache

The **browser cache** — caching in the user's own browser — is the closest, first layer of web caching:

- **The browser caches resources locally.** Your browser *caches* web resources (images, CSS, JavaScript, pages) *locally on your device*, per the HTTP headers. On revisiting a page or reusing a resource, the browser serves it from its *local cache* instead of re-downloading — making repeat visits *much faster* (no network fetch for cached resources). The browser cache is why revisited pages load faster. It's the first, closest cache.
- **It's controlled by HTTP headers.** The browser caches according to the server's `Cache-Control` (and validation) headers — the server tells the browser what to cache and for how long, and the browser obeys. So developers control browser caching via the headers their server sends. This is why setting cache headers correctly matters — they directly control browser (and CDN) caching behavior. Headers drive the browser cache.
- **It's the fastest cache layer.** The browser cache is the *closest* to the user (on their device) — so browser-cache hits are the *fastest* (no network at all, served locally). It's the first layer of web caching, catching repeat requests before they even hit the network. Maximizing appropriate browser caching (via good headers on cacheable static resources) is a key web-performance technique. Closest cache = fastest hits.

The browser cache — local caching in the user's browser, controlled by HTTP headers — is the closest and fastest web cache layer, serving repeat requests locally without any network fetch (why revisited pages load fast). It's the first layer; beyond it, CDNs cache content globally near users.

## CDNs: caching at the edge

A **CDN** (Content Delivery Network) caches content on *servers distributed around the world* ("the edge"), close to users — a powerful application of caching at global scale:

- **Cache content near users, geographically.** A CDN is a *network of servers distributed globally* (edge locations) that *cache* content (especially static assets — images, video, CSS, JS, and increasingly dynamic content) *close to users*. When a user requests content, it's served from a *nearby* CDN edge server instead of the far-away *origin* server — reducing latency (the data travels a shorter distance) and offloading the origin. CDNs cache content geographically near users. Proximity is the point.
- **Why CDNs matter: latency and scale.** Network latency depends heavily on *distance* (physics — data takes time to travel), so serving from a *nearby* edge (vs a distant origin) is *much faster* for the user. And CDNs *absorb load* (edge servers serve cached content, offloading the origin — handling huge traffic and protecting the origin). CDNs make the web *fast globally* and *scalable* — a nearby cache for everyone, worldwide. They're essential infrastructure for fast, scalable web content, especially static assets and media. Global proximity + load offloading.
- **CDNs are caching at internet scale.** A CDN is fundamentally *caching* — the same principle (keep reused data in a faster/closer place) applied at *global, internet scale*: cache content at edges close to users so most requests are served fast and locally (relative to the user), only occasionally fetching from the origin (a CDN "miss" goes to the origin, like any cache miss). CDNs are the caching principle applied geographically across the internet. Same idea, planetary scale.

CDNs cache content on globally-distributed edge servers close to users — serving from a nearby edge instead of the distant origin, reducing latency (distance-driven) and offloading the origin — making the web fast globally and scalable. A CDN is the caching principle applied at internet scale, geographically. Browser, CDN, and origin caches form layers.

## Layers of web caching

Web caching works as *multiple layers* — browser, CDN, and origin-side caches — that together make the web fast, a nice illustration of caching's universality:

- **The web caching layers.** A web request may hit several cache layers in sequence: the *browser cache* (closest, on-device — checked first), then a *CDN edge cache* (nearby, geographic — checked if the browser misses), then *origin-side caches* (caches in front of or within the origin server — e.g. a reverse proxy cache, or an application/distributed cache like Redis — checked if the CDN misses), and finally the *origin* itself (the source — hit only if all caches miss). Each layer catches requests the previous one missed. Requests fall through the layers until a hit.

```text
   Web request flow through cache layers:
     Browser cache → CDN edge cache → origin-side cache → Origin (source)
     (on device)     (nearby edge)    (reverse proxy/     (only if all
                                       app cache/Redis)     caches miss)
   each layer serves what it has; misses fall through to the next
```

- **Layers compound the benefit.** Each layer *catches* some requests (serving them fast, closer), so fewer requests reach the slower/farther layers, and few reach the origin. The layers *compound* — most requests are served by the browser or CDN (fast, near the user), sparing the origin. This layered caching is why the web is fast and origins can handle huge scale: the caches absorb the vast majority of load. Layered caching is enormously effective. Each layer offloads the next.
- **The same principle, many layers.** These web caching layers are the *same caching principle* (from post one) applied at multiple points — browser (local), CDN (edge), origin-side (server) — each a cache in the hierarchy from user to source. It's a vivid example of caching's *universality and layering* (the memory-hierarchy idea, generalized to the web): caches all the way from the user's device to the origin. Understanding this layering demystifies web performance. Caching, layered, is how the web stays fast.

Web and CDN caching apply the caching principle across the internet — HTTP headers coordinate it, the browser cache serves repeat requests locally (fastest), CDNs cache content on global edge servers near users (fast, scalable), and browser/CDN/origin caches layer to absorb most requests and spare the origin. It's caching at internet scale, layered — the same universal principle from the user's device to the source. Next, the final post: caching pitfalls and practice.

## Key takeaways

- HTTP has built-in caching coordinated by headers: `Cache-Control` sets whether a response is cacheable and for how long (`max-age` — a TTL), and validation via ETags/conditional requests lets caches cheaply check if a cached copy is still current (getting "not modified" without re-sending data) — so servers control exactly how responses are cached across the web's many caches.
- The browser cache (local caching in the user's browser, controlled by HTTP headers) is the closest and fastest web cache layer — serving repeat requests locally with no network fetch (why revisited pages load fast) — so setting cache headers correctly on cacheable resources is a key web-performance technique.
- A CDN (Content Delivery Network) caches content on globally-distributed edge servers close to users — serving from a nearby edge instead of the distant origin, cutting latency (which is distance-driven) and offloading the origin — making the web fast globally and scalable; a CDN is the caching principle applied at internet scale, geographically.
- Web caching works as layers — browser cache → CDN edge → origin-side caches (reverse proxy, app/Redis cache) → origin — where each layer catches requests the previous missed, so most requests are served fast and near the user, sparing the origin; the layers compound to make the web fast and origins scalable.
- Web/CDN caching is a vivid example of caching's universality and layering (the memory-hierarchy idea generalized to the web) — the same caching principle applied at every point from the user's device to the source — which is how the web stays fast at global scale.

## Further reading

- [Content delivery network (Wikipedia)](https://en.wikipedia.org/wiki/Content_delivery_network)
- [Web cache (Wikipedia)](https://en.wikipedia.org/wiki/Web_cache)
- [Distributed caching (previous post)](/blog/posts/cache-06-distributed-caching.html)
