# The Memory Hierarchy of an Agent

*Cognitive science spent a century mapping human memory into distinct systems — working, episodic, semantic, procedural — and agent engineering has been rediscovering the same partition from the opposite direction, because the same pressures produce the same shapes. The hierarchy isn't biomimicry for its own sake: each memory type answers a different question, is stored differently, retrieved differently, and fails differently. Confusing them is the root of most memory-system design mistakes.*

Post [1](/blog/posts/agmem-01-why-agents-forget.html) framed memory as the system around a stateless model. This post gives the series its organizing frame: the four memory types, what each is *for* in an agent, and why collapsing them into one undifferentiated store — the most common design error — fails. Every mechanism in posts 3–7 slots into this map.

## Working memory: the context window

**Working memory** holds what the current task needs right now: the instructions, the conversation so far, the tool results just returned, the plan in progress. For an agent this *is* the context window, plus the scratch structures the harness maintains around it. Its defining properties: small, fast, expensive, and constantly overwritten. The engineering discipline here is curation — what earns a place in the window — which is [context engineering](/blog/series/context-engineering/)'s territory. The relevant design insight for this series: working memory is the *destination* of every other memory type. Episodic, semantic, and procedural memory only matter at the moment their contents are selected back into the window. A memory that can't be retrieved into working memory at the right moment functionally doesn't exist.

## Episodic memory: what happened

**Episodic memory** stores experiences: this conversation happened, these steps were taken, this attempt failed with that error, the user reacted this way. It is time-stamped, context-rich, and specific — the agent's autobiography. Agents need it to continue yesterday's session, to answer "what did we decide last week?", and — critically for post 7 — as the raw material learning is extracted from.

Its natural storage is append-only logs of events and transcripts, typically made searchable by embedding (post 4's mechanism). Its failure modes are characteristic: **volume** (every session generates episodes; without selection the store becomes a landfill) and **staleness by design** (episodes record what was true *then* — retrieving a six-month-old episode as if it described the present is a category error). Episodic memory should be read like history, not like fact.

## Semantic memory: what is true

**Semantic memory** stores facts divorced from the episodes that taught them: the user prefers Go, the staging database is read-only, the client's fiscal year ends in March, deploys happen Fridays. Where episodic memory says "on March 3rd the user said X," semantic memory says "X." The compression is the point — facts are smaller, faster to retrieve, and directly usable without re-reading the episode that produced them.

Semantic memory is *derived*: something must read episodes and extract durable facts from them — the consolidation process post 6 builds. That derivation step is where judgment lives: what's a durable fact versus a passing remark, what confidence to attach, and — hardest — when a new episode should *revise* an existing fact rather than coexist with it. The failure mode is contradiction: "user prefers tabs" and "user prefers spaces" both retrieved into the same window, which is worse than knowing neither. Semantic memory needs an update discipline, not just an insert path, and its natural forms are structured — key-value preferences, entity records, the knowledge graphs of post 5.

## Procedural memory: how to do things

**Procedural memory** stores skills: how to run the deploy, how this team's PR etiquette works, which approach to the flaky API actually succeeds. In humans it's riding the bicycle; in agents it takes concrete textual forms — system-prompt rules ("always run the linter before committing"), reusable playbooks and skill files, learned tool-use patterns, even few-shot examples of successful past solutions. It differs from semantic memory in kind: semantic memory informs *what the agent says*; procedural memory shapes *what the agent does and how*. It's also the type with the highest leverage and the highest risk — a learned procedure applies to every future task, so a wrong one does compounding damage. Post 7 is devoted to how procedures get learned safely.

## Why the distinctions pay rent

The hierarchy earns its keep in concrete design decisions. **Storage**: episodes want append-only logs; facts want updatable records; procedures want versioned, reviewable documents — one undifferentiated vector store serves all three badly. **Retrieval**: episodes are searched ("find the session where…"), facts are looked up ("what's the user's timezone?"), procedures are loaded by task type ("doing a deploy — load the deploy playbook") — three different access patterns with three different precision requirements. **Lifecycle**: episodes age into history and can be summarized or expired; facts must be revised in place when the world changes; procedures should change rarely and deliberately, like code. And **failure analysis**: "the agent forgot" means a retrieval miss in one type, but "the agent remembered wrong" is usually a *type confusion* — an old episode treated as current fact, or a one-off instruction promoted to standing procedure. Naming which memory misbehaved is usually most of the debugging.

The takeaway: agent memory decomposes into four types with different jobs — **working** (the context window, destination of all the others), **episodic** (what happened: time-stamped history, read as history), **semantic** (what is true: compressed, derived facts needing an update discipline), and **procedural** (how to act: high-leverage, code-like, changed deliberately). They differ in storage, retrieval pattern, and lifecycle, and the commonest design error — one undifferentiated store — fails precisely because it erases those differences. The rest of the series builds each mechanism against this map.

## Key takeaways

- **Working memory** = the context window; every other memory type only matters at the moment it's retrieved back into it.
- **Episodic** = the agent's autobiography: specific, time-stamped, append-only; fails by volume and by being read as current fact — history, not truth.
- **Semantic** = facts extracted from episodes: compressed, directly usable; needs *revision* (not just insertion) or it accumulates contradictions.
- **Procedural** = skills and playbooks shaping behavior: highest leverage, highest risk, should evolve like code — versioned and reviewed.
- The types differ in **storage, retrieval pattern, and lifecycle**; one undifferentiated vector store erases those differences, and most "agent remembered wrong" bugs are type confusions (episode-as-fact, remark-as-procedure).

## Further reading

- [Episodic memory — memory of experienced events](https://en.wikipedia.org/wiki/Episodic_memory)
- [Semantic memory — memory of facts and meanings](https://en.wikipedia.org/wiki/Semantic_memory)
