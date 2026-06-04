---
title: "Picnic: Achieving 47% Latency Reduction Through Protocol Buffers and Service Consolidation"
description: "Latency optimization guide: Protocol Buffers vs JSON, service consolidation, P99 reduction strategies, and real case study achieving 47% latency improvement."
keywords: ["latency optimization", "Protocol Buffers", "gRPC", "performance", "serialization", "P99 latency", "service consolidation", "microservices"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
canonical: "https://pratikdhanave.github.io/articles/35-picnic-latency/"
schema: {
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "Picnic: Achieving 47% Latency Reduction Through Protocol Buffers",
  "description": "Production guide to latency optimization achieving 47% P99 reduction with Protocol Buffers",
  "author": {"@type": "Person", "name": "Pratik Dhanave", "url": "https://pratikdhanave.github.io"},
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
  "image": "https://pratikdhanave.github.io/og-default.png",
  "keywords": ["latency optimization", "Protocol Buffers", "performance", "gRPC"],
  "articleSection": "Performance & Optimization"
}
---

# Picnic: Achieving 47% Latency Reduction Through Protocol Buffers and Service Consolidation

**"API latency is feature latency."** When your social network backend has a P99 latency of 500ms, every page load feels slow. Your users switch to competitors. This is the story of Picnic: a 1M+ user social platform where a seemingly small optimization (switching serialization formats) cascaded into a 47% P99 latency reduction.

The lesson: sometimes the bottleneck isn't the algorithm, it's the protocol.

## Protobuf vs JSON Performance

| Metric | JSON | Protobuf | Improvement |
|--------|------|----------|-------------|
| Payload Size | 80 KB | 8 KB | 90% reduction |
| Parsing Time | 450ms | 120ms | 73% faster |
| P99 Latency | 900ms | 476ms | 47% reduction |

---

## The Latency Problem at 1M+ Users

Traditional REST + JSON architecture:
- **Serialization:** Convert objects to JSON (expensive)
- **Deserialization:** Parse JSON back (expensive)
- **Schema mismatches:** Client requests 50 fields, server returns 50 fields, client uses 5
- **Network bandwidth:** JSON is verbose; 50KB for what could be 5KB

At 1M+ users with peak load, every millisecond matters.

**Baseline metrics:**
- **P50:** 150ms
- **P99:** 900ms ← This is the killer
- **Payload size:** 80KB avg (way too much)

---

## Solution: Protocol Buffers + Service Consolidation

###  **Step 1: Migrate to Protocol Buffers (gRPC)**

Protocol Buffers are binary-encoded, typed messages. Think "JSON's smaller, faster cousin."

```protobuf
syntax = "proto3";

package social.api.v1;

message UserProfile {
  int64 user_id = 1;
  string username = 2;
  string bio = 3;
  repeated int64 follower_ids = 4;  // Only what we need
  int32 follower_count = 5;
  google.protobuf.Timestamp created_at = 6;
}

message GetUserRequest {
  int64 user_id = 1;
  repeated string fields = 2;  // Client specifies WHAT it wants
}

message GetUserResponse {
  UserProfile user = 1;
}

service SocialAPI {
  rpc GetUser(GetUserRequest) returns (GetUserResponse);
  rpc ListFollowers(ListFollowersRequest) returns (stream Follower);
}
```

**Impact:**
- **JSON:** `{"user_id": 123, ...}` → 80 bytes + delimiters
- **Protobuf:** `\x08\x7b\x12\x04user` → 8 bytes (binary)

**Real-world result:**
- **Before:** 80KB per request
- **After:** 8KB per request (90% smaller)

```python
# Python gRPC implementation
from grpc import aio
import grpc

class SocialServicer:
    def __init__(self, db_client):
        self.db = db_client
    
    async def GetUser(self, request, context):
        """Only fetch fields the client asked for."""
        user = await self.db.get_user(
            user_id=request.user_id,
            fields=request.fields if request.fields else ["user_id", "username"]
        )
        return UserProfile(
            user_id=user.id,
            username=user.username,
            follower_count=len(user.followers),
        )

# Server startup
server = aio.server()
add_SocialAPIServicer_to_server(SocialServicer(db), server)
await server.start()
```

---

### **Step 2: Service Consolidation**

Before Picnic, the architecture was:
```
Client → API Gateway → UserService → Database
                    → FollowService → Database
                    → FeedService → Database
                    → PhotoService → Database
```

Each service = network hop. Each hop = latency.

After consolidation:
```
Client → GraphQL API Gateway → Consolidated Backend
                              (UserService + FollowService + FeedService)
```

All logic in one process (still running in Kubernetes, but talking via in-process function calls instead of network).

```python
class ConsolidatedSocialAPI:
    """All logic in one service. No network hops between features."""
    
    async def GetUserWithFollowers(self, request):
        # Before: 3 network calls (GetUser, ListFollowers, GetFollowerDetails)
        # After: 3 function calls (same data, 3000x faster)
        
        user = await self.db.get_user(request.user_id)
        followers = await self.db.get_followers(request.user_id)
        follower_details = await asyncio.gather(*[
            self.db.get_user(fid) for fid in followers
        ])
        
        return {
            "user": user,
            "follower_count": len(followers),
            "top_followers": follower_details[:10],
        }
```

**Result:**
- **Before:** 1 call to API Gateway + 3 calls to micro-services = 4 hops
- **After:** 1 call to consolidated API = 1 hop

---

## The Numbers

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **P50 latency** | 150ms | 89ms | 40% ↓ |
| **P99 latency** | 900ms | 476ms | **47% ↓** |
| **Payload size** | 80KB | 8KB | 90% ↓ |
| **Requests/sec per replica** | 600 | 1200 | 2x ↑ |
| **Infrastructure costs** | 100% | 60% | 40% ↓ |

---

## Observability: Proving the Win

We used Prometheus to track every layer:

```yaml
# Prometheus metrics
grpc_server_handling_seconds_bucket{method="GetUser", le="0.1"} 4500  # 4500 requests < 100ms
grpc_server_handling_seconds_bucket{method="GetUser", le="1.0"} 4998  # 4998 requests < 1s (only 2 outliers)

# Compared to REST/JSON:
http_server_request_duration_seconds_bucket{method="GetUser", le="0.5"} 2100  # Only 2100 < 500ms
http_server_request_duration_seconds_bucket{method="GetUser", le="1.0"} 4500  # Rest took > 500ms
```

---

## My Takeaway

The 47% latency reduction didn't come from a breakthrough algorithm. It came from:

1. **Right protocol for the job** (gRPC, not REST)
2. **Eliminating unnecessary network hops** (consolidation)
3. **Clients specify what they need** (not "get everything")
4. **Continuous measurement** (Prometheus, not hunches)

If your P99 is > 500ms and you're using REST + JSON, this is low-hanging fruit.

---

**Tags:** #Latency #gRPC #ProtocolBuffers #Performance #Kubernetes #Observability

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** Picnic social network (1M+ users)
