<!-- Markdown version for AI agents and readers. Canonical: https://pratikdhanave.com/blog/posts/zdm-05-cutover-and-rollback.html -->

# Cutover and Rollback — Crossing Carefully, and Keeping the Bridge

*Everything before this moment was preparation with an exit. Cutover is the moment traffic actually moves — reads, then writes, then trust — and its engineering question is blunt: how do you cross so that the first sign of trouble costs a flag-flip instead of an incident? The answer is incremental exposure, pre-staged rollback, and a disciplined patience about demolishing the bridge you just crossed.*

Posts [2](/blog/posts/zdm-02-expand-contract.html)–[4](/blog/posts/zdm-04-dual-writes-and-shadow-reads.html) built the new copy and proved it agrees; this post moves production onto it — the migrate phase's final steps, executed with [feature-flag discipline](/blog/series/ci-cd-pipelines-from-first-principles/) and post 4's agreement rate as the admission ticket.

## Reads first, and by percentage

Read cutover goes first because it's the reversible half: serving reads from the new copy changes no data, so rollback is purely a routing decision. The mechanics: a **flag, not a deploy** — the read path selects old/new per request, controllable at runtime, because rollback-by-deploy measures in minutes while rollback-by-flag measures in seconds; **ramped exposure** — internal traffic, then 1%, 10%, 50%, 100%, each stage holding long enough to see real load shapes (including the daily peak — a cutover validated only at 3 a.m. traffic has been validated against nothing); **cohort-sticky routing** where consistency within a session matters — percentage by *user/tenant*, not by request, so one actor doesn't straddle copies mid-session; and **watch the comparative metrics** — error rate, latency, and (the migration-specific one) the shadow-read mismatch rate from post 4, which during ramp becomes your live canary: mismatches rising with exposure means the cold copy has problems the hot sample missed. Any degradation: flip back, diagnose, re-ramp. Boring is the goal.

## Writes second, and the asymmetry that changes everything

Write cutover — new copy becomes the written truth, old copy becomes the follower (reverse dual-write) or stops — carries the asymmetry that deserves respect: **once writes land only in the new copy, "flip back" is no longer free**, because the old copy is now the stale one. The disciplines that manage it: **keep reverse dual-writes running** (new → old) through the entire rollback window, so the old copy stays current and rollback remains a flag-flip — this is "keeping the bridge"; **cut writes by cohort** where the system allows (tenant-by-tenant write migration bounds any disaster to a cohort you can repair); and **sequence the risky day deliberately** — write cutover on a quiet morning with the team watching, not Friday 6 p.m., because while rollback is cheap, *diagnosis* still wants humans awake.

## Rollback as a built thing, and the demolition date

The rollback plan that works is the one that was **built, tested, and pre-staged** — not the paragraph in the runbook. Concretely: the flags exist in both directions and have been *exercised* (flip to new, flip back, in staging and in the early ramp — a rollback path never tested is a hypothesis); the data story under rollback is explicit (with reverse dual-writes: none needed; without: a documented re-sync procedure with a measured duration); and the **rollback window is declared** — the period during which the old path is kept warm and return is cheap. The window ends deliberately: after N days at 100% with agreement sustained (post 4's number, still running), the team crosses the real point of no return — stop reverse writes, decommission the old path, schedule the contract phase (post 2). Two traps on the way out: **the forever-bridge** (reverse dual-writes left running for months "just in case" — cost, complexity, and a false comfort that rots as the paths drift) and **the premature demolition** (dropping the old column in the same week as the write flip — the incidents this causes are the entire reason contract is a separate, dated, boring phase). The bridge exists to be kept exactly as long as declared, then demolished on schedule.

The takeaway: cutover is incremental exposure with a pre-staged exit — **reads first** (flag-controlled, percentage-ramped through real peaks, cohort-sticky, canaried by the live mismatch rate), **writes second** with the asymmetry respected (reverse dual-writes keep the old copy current, cohort-scoped flips bound the blast radius, quiet-morning scheduling keeps humans available), and **rollback as a built, tested artifact** with a declared window — after which the bridge is demolished on schedule, neither kept forever nor dropped in the flush of victory. Migrations end the way they were run: deliberately.

## Key takeaways

- **Reads cut first** because they're free to reverse: runtime flags (seconds, not deploy-minutes), ramped 1→100% through daily peaks, sticky per tenant/user, with post 4's mismatch rate as the live canary.
- **Writes carry the asymmetry**: after the flip the old copy stales — so run **reverse dual-writes** through the rollback window to keep return a flag-flip, cut by cohort where possible, schedule for watched quiet hours.
- **Rollback is built, not written**: both-direction flags actually exercised, the under-rollback data story explicit, the window *declared* in advance.
- Exit deliberately: sustained agreement at 100% ends the window → stop reverse writes → decommission → dated contract phase. Avoid both the **forever-bridge** and **premature demolition**.

## Further reading

- [Feature toggle — the runtime switch cutover rides on](https://en.wikipedia.org/wiki/Feature_toggle)
- [Rollback (data management) — returning to a prior state as an engineered operation](https://en.wikipedia.org/wiki/Rollback_(data_management))

---

Author: Pratik Dhanave (https://pratikdhanave.com) | Published: 2026-11-02
Canonical: https://pratikdhanave.com/blog/posts/zdm-05-cutover-and-rollback.html
Attribution: please link the canonical URL when citing or quoting this post.
