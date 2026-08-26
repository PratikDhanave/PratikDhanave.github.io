# Org Design and Conway's Law

*Here is one of the most profound and underappreciated ideas in all of software engineering, and it comes from operations, not code: the structure of your software will end up mirroring the structure of your organization. This is Conway's law, and its implication is startling — if you want to change your architecture, you may need to change your org chart first. Organizational design isn't just an HR concern; for technical organizations, it's an architectural decision. How you organize people shapes what you build.*

**Organizational design** is the deliberate *design* of how an organization is structured — and its most important insight for technical organizations is **Conway's law**: systems mirror the communication structure of the organizations that build them. This post covers org design as deliberate choice, Conway's law and its profound implications, team boundaries, and the "inverse Conway maneuver." It builds on org structure (the previous post) and reveals why org design is, for technical companies, an architectural decision.

## Org design as deliberate choice

**Organizational design** is *deliberately designing* the organization's structure (rather than letting it grow haphazardly) — treating structure as a *choice* with consequences:

- **Structure should be designed, not accidental.** As organizations grow, their structure can either be *deliberately designed* (chosen to serve the company's needs) or *accrete accidentally* (growing haphazardly, reflecting history and politics rather than what works). Org design is the discipline of *deliberately* designing structure — choosing it purposefully. Design the org; don't let it just happen. Deliberate, not accidental.
- **Design for what the organization needs to do.** Good org design starts from *what the organization needs to accomplish* (its strategy, products, how work must flow) and designs structure to *enable* that — grouping and connecting people to support the needed work and coordination. Structure should *serve* the organization's goals and work. Design structure to fit the mission. Form follows function.
- **It's an ongoing concern as you scale.** Org design isn't one-time — as a company *grows and changes*, its structure must be *redesigned* (what worked at one size fails at another — the scaling theme). Org design is an ongoing concern, revisited as the organization evolves. Redesign the org as it grows. Evolving structure for an evolving company.

Org design is the deliberate design of organizational structure — choosing it purposefully (not letting it accrete accidentally) to serve what the organization needs to do, revisited as the company scales. Treating structure as a deliberate, consequential choice is the essence of org design. And the deepest reason it's consequential — for technical organizations — is Conway's law.

## Conway's law

**Conway's law** is a profound observation: *organizations design systems that mirror their own communication structure* — the software you build ends up shaped like your org:

- **Systems mirror the org's communication structure.** Conway's law states that the *structure of a system* (software architecture) tends to *mirror* the *communication structure of the organization* that builds it. Teams build software shaped like the teams — the system's components and their interfaces reflect the teams and their communication. Software mirrors the org. Architecture reflects organization.
- **Why it happens.** It happens because *teams build the parts they own*, and the *interfaces between components* reflect the *communication between teams*. Components built by one team are cohesive; boundaries between components fall where team boundaries (and communication gaps) are. The software's shape *emerges from* how the org is structured and communicates. Team boundaries become software boundaries. The org's shape imprints on the code.
- **It's remarkably robust.** Conway's law is *remarkably consistent* — observed across many systems and organizations. It's not a rule someone imposes; it's an *emergent tendency* (software naturally comes to mirror the org). This robustness makes it a powerful lens for understanding why systems are shaped as they are (often: look at the org). A robust, emergent phenomenon. It just happens, reliably.

Conway's law — systems mirror the communication structure of the organizations that build them (because teams build the parts they own, and component interfaces reflect team communication) — is a robust, emergent tendency. It reveals a deep link between org structure and software architecture, with profound implications.

## The implications of Conway's law

Conway's law has *profound implications* — chief among them, that for technical organizations, org design *is* architectural design:

- **Org design determines architecture.** The startling implication: *how you organize your teams shapes your software architecture* (via Conway's law). So org design *isn't just an HR/management concern* — for technical organizations, it's an *architectural* decision. Your team structure will *become* your architecture. Org design is architectural design. How you organize shapes what you build.
- **To change architecture, consider the org.** A powerful consequence: if you want a particular architecture, you may need the *matching org structure* — and if your org fights your desired architecture (Conway's law pulling the other way), the architecture will struggle. To change architecture, you may need to change the org. Architecture and org are linked; you can't freely change one against the other. Align org and architecture. Change the org to change the architecture.
- **The inverse Conway maneuver.** Teams *use* Conway's law deliberately — the *inverse Conway maneuver*: *design the organization to produce the architecture you want* (structure teams to match your desired system structure, so Conway's law works *for* you). Rather than fighting Conway's law, you *harness* it — shaping the org to shape the architecture. Harness Conway's law deliberately. Design the org to get the architecture.
- **Misaligned org and architecture cause pain.** When org structure and desired architecture are *misaligned* (Conway's law pulling against your intended design), you get *friction* (architecture fights the org, coordination is hard, the system drifts toward mirroring the org anyway). Aligning them (org matching architecture) is much smoother. Misalignment between org and architecture causes friction. Fight Conway's law and you'll lose.

Conway's law's implications are profound: org design determines architecture (for technical organizations, org design *is* architectural design), so changing architecture may require changing the org, and teams can *harness* this (the inverse Conway maneuver — design the org to produce the desired architecture) rather than fight it (misalignment causes friction). This makes team boundaries architecturally significant.

## Team boundaries and org design in practice

Because of Conway's law, *team boundaries* are architecturally significant — and designing them well is central to org design for technical organizations:

- **Team boundaries become system boundaries.** Since Conway's law makes team boundaries into *system boundaries* (component/service boundaries), *how you draw team boundaries* shapes *how your system is decomposed*. Drawing team boundaries *is*, in effect, drawing architectural boundaries. Team boundaries = architectural boundaries. Where teams split, the system splits.
- **Design teams around the desired decomposition.** Org design for technical orgs means designing *teams* to match the *desired system decomposition* — teams that own cohesive, loosely-coupled parts (matching how you want the system decomposed). Well-designed teams (aligned with good architectural boundaries) produce well-decomposed systems; poorly-designed teams produce poorly-decomposed ones. Design teams to match desired architecture. Teams shaped like the system you want.
- **Minimize cross-team dependencies.** A key principle: *minimize dependencies between teams* (as you'd minimize coupling between components) — because cross-team dependencies mean cross-team coordination (slow, friction). Teams that own their parts *autonomously* (few dependencies) move fast (like loosely-coupled components). Autonomous, loosely-coupled teams (the team-topologies idea) are the goal. Minimize cross-team dependencies. Loosely-coupled teams, like loosely-coupled code.
- **This connects to the whole blog's architecture themes.** Conway's law links org design to the *architecture* themes across this blog (modularity, loose coupling, bounded contexts) — good org design and good architecture *mirror* each other (both about cohesive, loosely-coupled parts). For technical leaders, org design and architecture are two sides of one coin. Org design and architecture are intertwined. Organize like you'd architect.

Org design and Conway's law reveal that, for technical organizations, how you organize people *shapes what you build* — org design is architectural design. Team boundaries become system boundaries, so design teams around your desired system decomposition (cohesive, autonomous, loosely-coupled — minimizing cross-team dependencies), harnessing Conway's law rather than fighting it. This is one of the most important insights linking operations to engineering. Next: scaling teams and communication.

## Key takeaways

- Organizational design is the deliberate design of organizational structure — choosing it purposefully (not letting it accrete accidentally from history and politics) to serve what the organization needs to accomplish, revisited as the company scales (what works at one size fails at another).
- Conway's law is a profound, robust, emergent observation: organizations design systems that *mirror their own communication structure* — the software's architecture ends up shaped like the org (because teams build the parts they own, and component interfaces reflect team communication), so team boundaries become system boundaries.
- The startling implication: how you organize teams *shapes your software architecture*, so org design isn't just an HR concern — for technical organizations, it's an *architectural* decision, and to change your architecture you may need to change your org (you can't freely change one against the other).
- Teams can *harness* Conway's law deliberately — the "inverse Conway maneuver": design the organization to produce the architecture you want (structure teams to match your desired system structure) — rather than fight it, since misaligned org and architecture cause friction (the system drifts toward mirroring the org anyway).
- Because team boundaries become architectural boundaries, org design for technical orgs means designing teams around the desired system decomposition — cohesive, autonomous, loosely-coupled teams that minimize cross-team dependencies (the team-topologies idea) — linking org design to the blog's architecture themes (good org design and good architecture mirror each other).

## Further reading

- [Conway's law (Wikipedia)](https://en.wikipedia.org/wiki/Conway%27s_law)
- [Organizational architecture (Wikipedia)](https://en.wikipedia.org/wiki/Organizational_architecture)
- [Organizational structure (previous post)](/blog/posts/ops-03-organizational-structure.html)
