# Scaling Teams and Communication

*Adding people to a growing company feels like it should straightforwardly add capacity — but it doesn't, and understanding why is one of the most important lessons in operations. Every person you add creates new communication links with everyone else, and those links grow far faster than the headcount. This is why big teams feel slower than small ones, why "adding people to a late project makes it later," and why scaling an organization is mostly a battle against communication overhead. Managing that overhead is the core challenge of scaling.*

**Scaling teams** is harder than it looks because *communication overhead* grows *faster* than headcount — the central challenge of growing an organization. This post covers why communication cost grows super-linearly, the resulting drag on large teams, why keeping teams small matters, and how organizations manage the overhead (through structure and autonomy). It builds on org design (from the previous post) and explains the coordination cost that makes scaling so hard. Managing communication overhead is the crux of scaling.

## Why communication overhead grows faster than headcount

The fundamental challenge of scaling teams: **communication links grow faster than the number of people** — so coordination cost grows *super-linearly* with size:

- **Links grow quadratically, not linearly.** Adding people doesn't just add *people* — it adds *communication links* between people, and the number of possible links grows *quadratically* (roughly, with n people there are about n²/2 possible pairs). So doubling the team *more than doubles* the potential communication paths. Communication complexity grows *faster* than headcount — super-linearly. Links explode faster than people. n people, ~n² links.
- **Coordination cost grows super-linearly.** Because communication links grow super-linearly, the *cost of coordinating* the team grows *faster than the team size* — a team twice as large has *more than twice* the coordination overhead. This is why scaling isn't linear: capacity added per person *decreases* as the team grows (more of each person's effort goes to coordination). Coordination overhead grows faster than the team. More people, disproportionately more overhead.
- **Adding people can slow things down.** The consequence (famously "Brooks's law" for software): *adding people to a late project can make it later* — because the *added communication/coordination overhead* can exceed the added capacity, *slowing* rather than speeding the work. Beyond some point, adding people yields *diminishing (or negative)* returns due to overhead. More people isn't always more output. Sometimes it's less.

The core scaling challenge is that communication links grow *quadratically* (n²) while headcount grows linearly (n) — so coordination overhead grows *super-linearly*, meaning each added person contributes less (more goes to coordination) and adding people can even slow things down. This communication-overhead reality drives everything about scaling teams — starting with why big teams feel slow.

## Why big teams drag

The super-linear communication overhead explains why *large teams feel slower and less effective* than small ones — a common, frustrating experience:

- **Big teams have huge coordination overhead.** In a *large* team, the communication/coordination overhead (from the n² links) is *enormous* — much of everyone's effort goes to coordinating (meetings, updates, alignment) rather than *doing*. Big teams spend a large fraction of energy just *coordinating themselves*. Big teams drown in coordination. Much effort spent staying aligned.
- **Small teams move fast; big teams move slow.** *Small* teams have *few* communication links (low overhead), so they coordinate easily and move *fast* (most effort goes to work). *Large* teams have *many* links (high overhead), coordinate with difficulty, and move *slow* (much effort goes to coordination). This is why small teams often *outperform* large ones per person — less overhead. Small = fast, big = slow (per person). Overhead is the difference.
- **This is a fundamental, not fixable-by-effort, drag.** The large-team drag isn't a *failure of effort or people* — it's a *structural* consequence of communication overhead (the n² math). You can't just "try harder" to eliminate it; you must *manage* it *structurally* (below). Understanding it's structural (not a people problem) is key to addressing it right. It's structural, not a people failing. Math, not motivation.

Large teams drag because super-linear communication overhead means much of a big team's effort goes to coordinating itself (not doing) — so small teams move fast (low overhead) and big teams move slow (high overhead) per person, a *structural* consequence of the n² math (not a fixable-by-effort failing). Managing this structurally starts with keeping teams small.

## Keeping teams small

The most important lever against communication overhead is **keeping teams small** — because small teams have manageable overhead:

- **Small teams keep overhead manageable.** Since overhead grows super-linearly with size, *small* teams have *low, manageable* overhead — they coordinate easily and move fast. Keeping teams small is the most direct way to *avoid* the crushing overhead of large teams. Small teams are the antidote to overhead. Keep the team small to keep it fast.
- **The "two-pizza team" idea.** A well-known heuristic (popularized by Amazon): keep teams *small enough to be fed by two pizzas* (roughly under ~8-10 people) — small enough that communication overhead stays manageable and the team moves fast. The specific number matters less than the principle: *small teams* (not large ones) are the effective unit. Small teams (two-pizza) as the unit. Small enough to coordinate easily.
- **Scale by adding teams, not growing teams.** The key structural move: to *scale the organization*, add *more small teams* rather than *growing teams larger* — keeping each team small (low internal overhead) and coordinating *between* teams (the harder problem, below). You scale by *multiplying small teams*, not by inflating team size. Scale via more teams, not bigger teams. Many small teams, not few big ones.
- **Small teams are the effective unit.** The principle: the *small team* (not the individual, not the large group) is the effective *unit of work* — small enough to coordinate easily, large enough to accomplish meaningful work. Organizations scale as *collections of small teams*. The small team is the building block. Build the org from small teams. The unit that works.

Keeping teams small (the "two-pizza team" — under ~8-10 people) keeps communication overhead manageable so teams move fast, and you scale by *adding more small teams* rather than growing teams larger — the small team being the effective unit. But this shifts the challenge to coordinating *between* teams.

## Managing overhead between teams

Scaling as many small teams shifts the problem to *between-team* coordination — and managing *that* overhead (through autonomy and structure) is the crux of scaling:

- **The overhead moves to between teams.** Keeping teams small solves *within-team* overhead but creates *between-team* overhead (many teams that must coordinate). The scaling challenge becomes *coordinating between teams* — which, if not managed, recreates the n² problem at the team level (every team coordinating with every other). Between-team coordination is the new challenge. Overhead reappears between teams.
- **Team autonomy reduces coordination need.** The key: make teams *autonomous* — each owning a cohesive area with *minimal dependencies* on others (the loosely-coupled teams from the Conway's law post) — so they *need less* cross-team coordination. Autonomous teams (few dependencies) minimize between-team overhead (they mostly work independently). *Reducing the need* for coordination (via autonomy) beats trying to coordinate more. Autonomous teams need less coordination. Independence beats coordination.
- **Structure and clear interfaces manage the rest.** For the coordination that *is* needed, *structure* (org design — grouping related teams, clear ownership) and *clear interfaces* (well-defined boundaries between teams, like APIs between components — Conway's law) manage the overhead — making between-team coordination clear and limited rather than chaotic. Clear team boundaries/interfaces reduce coordination friction. Clear interfaces, less friction. Well-defined boundaries between teams.
- **This is org design's core scaling job.** Managing communication overhead — small autonomous teams with clear boundaries and minimal dependencies — is the *core job of org design at scale* (from the previous posts). Good org design *minimizes* coordination overhead (autonomous, loosely-coupled teams); bad org design *maximizes* it (tangled dependencies). Scaling well *is* managing communication overhead through good org design. Org design manages scaling overhead. Design for minimal coordination.

Scaling teams is fundamentally about managing *communication overhead* (which grows super-linearly with size): keep teams small (manageable within-team overhead), scale by adding more small teams, and manage between-team overhead through *autonomy* (minimize dependencies so teams need less coordination) and *clear interfaces/structure* — which is org design's core scaling job. Managing communication overhead is the crux of scaling an organization. Next: decision-making — how organizations decide.

## Key takeaways

- The core scaling challenge is that communication links grow *quadratically* (with n people, ~n²/2 possible pairs) while headcount grows linearly — so coordination overhead grows *super-linearly*, meaning each added person contributes less (more effort goes to coordination) and adding people can even slow things down ("adding people to a late project makes it later").
- This explains why big teams drag: large teams have enormous coordination overhead (much effort spent coordinating rather than doing), so small teams move fast (low overhead) and big teams move slow (high overhead) per person — a *structural* consequence of the n² math, not a fixable-by-effort failing.
- The most important lever is keeping teams small (the "two-pizza team" — roughly under ~8-10 people) so communication overhead stays manageable and the team moves fast — and you scale by adding *more small teams* rather than growing teams larger (the small team is the effective unit of work).
- Keeping teams small shifts the challenge to *between-team* coordination (many teams must coordinate, risking recreating the n² problem at the team level) — managed chiefly through team *autonomy* (each team owns a cohesive area with minimal dependencies, so it needs less cross-team coordination — reducing the *need* to coordinate beats coordinating more).
- Managing communication overhead — small, autonomous, loosely-coupled teams with clear boundaries/interfaces and minimal dependencies — is org design's core scaling job (good design minimizes coordination overhead; bad design maximizes it), so scaling an organization well *is* managing communication overhead through good org design.

## Further reading

- [Span of control (Wikipedia)](https://en.wikipedia.org/wiki/Span_of_control)
- [Team (Wikipedia)](https://en.wikipedia.org/wiki/Team)
- [Org design and Conway's law (previous post)](/blog/posts/ops-04-org-design-and-conways-law.html)
