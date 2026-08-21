# Alerting

*An alert that fires when nothing is actually wrong trains people to ignore alerts — and an ignored alert is worse than no alert, because it creates false confidence while the real incident scrolls past unnoticed. Good alerting is ruthlessly selective: page a human only for things that are both urgent and real, alert on what users feel, and treat every noisy alert as a bug to fix.*

Telemetry and SLOs tell you how the system is doing; **alerting** is how you find out *without staring at dashboards*. But alerting is where observability most often goes wrong — not from too few alerts, but from too many. This post covers the principles of alerting that works: alert on symptoms not causes, tie alerts to SLOs, fight alert fatigue, and design for the humans who get paged. Done right, alerting catches real problems early; done wrong, it burns out your team and hides the incidents that matter.

## The cardinal sin: alert fatigue

The defining failure of alerting is **alert fatigue** — so many alerts, so many of them false or unactionable, that people stop trusting and reading them. This is worse than having no alerting, because:

- **Real alerts get lost** in the noise — the one page that matters is buried among fifty that don't, and gets missed or dismissed.
- **People burn out** — being paged constantly, especially for non-problems and at night, is a leading cause of on-call misery and attrition.
- **Trust collapses** — once alerts are "usually nothing," they're ignored on principle, so the whole alerting system stops functioning even when it fires correctly.

Every principle that follows serves one goal: **every alert should be real, urgent, and actionable**, so that when something pages you, you *know* it matters and act. The bar for paging a human is high, and keeping it high is the whole game. Treat a false or noisy alert as a *bug* — something to fix or delete, not tolerate — because each one erodes the system's value.

## Alert on symptoms, not causes

The most important principle: **alert on symptoms (what the user experiences), not causes (internal conditions).** Page when *users are affected* — requests failing, latency high, the SLO burning — not on every internal metric that *might* indicate a problem.

```text
Cause-based (avoid paging on these):     Symptom-based (page on these):
  CPU is at 90%                            error rate exceeds SLO
  a disk is filling                        p99 latency exceeds SLO
  one server restarted                     users can't complete checkout
  memory usage is high                     the service is down
```

Why symptoms over causes:

- **Causes don't always mean impact.** High CPU might be fine (it's *supposed* to be busy); a restarted server might have failed over cleanly with no user impact. Paging on causes generates alerts for non-problems — the fatigue engine.
- **Symptoms are what actually matter.** If users are unaffected, it can usually wait for business hours, no matter what the internal cause is. If users *are* affected, page — regardless of whether you've identified the cause yet.
- **There are far fewer symptoms than causes.** Many different internal problems manifest as the same handful of user-facing symptoms (errors, slowness), so alerting on symptoms is both more meaningful and less noisy than trying to alert on every possible cause.

Causes still belong in your telemetry — they're how you *diagnose* an alert once it fires (the dashboards, the traces, the logs). But the *page* should be triggered by user-facing symptoms. Diagnose with causes; alert on symptoms.

## Tie alerts to SLOs and error budgets

The SLOs from the last post give you the sharpest symptom-based alerts. Instead of arbitrary thresholds ("alert if latency > 500ms" — why 500?), alert on **SLO burn**: page when you're consuming your error budget fast enough to threaten the SLO.

- **Error-budget burn-rate alerting** — alert when the rate of failures/slowness is burning the error budget quickly enough to breach the SLO if it continues. A fast burn (budget being consumed in hours) pages urgently; a slow burn (budget trending down over days) is a gentler notification.
- **This aligns alerts with what you promised.** You alert precisely when the thing you committed to (the SLO) is genuinely at risk — which is, by construction, when users are being affected enough to matter. No arbitrary thresholds, no alerting on blips that don't threaten the objective.

Burn-rate alerting is the mature form of symptom-based alerting: it's tied to a user-centric SLO, it distinguishes urgent (fast burn → page now) from non-urgent (slow burn → look into it), and it inherently filters out the small fluctuations that don't endanger the budget. If you take one concrete alerting practice from this series, it's alert on SLO burn rate.

## Designing alerts for humans

Alerts are consumed by tired humans, often at 3 a.m., so design for them:

- **Severity tiers.** Not everything deserves a page. Distinguish **page-now** (urgent, user-impacting, wake someone) from **ticket/notify** (needs attention but can wait for business hours). Reserve paging for the genuinely urgent; route the rest to non-paging channels. Paging for non-urgent things is a top fatigue source.
- **Every alert must be actionable.** If there's nothing the recipient can *do* about it, it shouldn't page. An alert with no action is noise; either make it actionable, downgrade it, or delete it.
- **Include context and a runbook.** A good alert says *what's wrong, how bad, and what to check/do first* — ideally linking a runbook. An alert that just says "error rate high" with no next step wastes precious incident time.
- **Make alerts easy to tune and delete.** Regularly review which alerts fire, which are ignored, and which are noise — and prune. Alert rules are code; maintain them, and delete the ones that don't earn their place.

## The on-call reality

Alerting exists to drive **on-call** response, and humane on-call is part of alerting design:

- **Sustainable load.** If on-call is constantly paged, that's a signal the *alerting* (or the system's reliability) needs fixing, not that people should suffer. Excessive paging is a bug in the alerts or the system.
- **Blameless follow-up.** After an incident, a blameless postmortem asks what the system (and the alerting) should do better — did the right alert fire at the right time? was it actionable? — turning incidents into improvements rather than blame.
- **Alerts feed a loop.** Good alerting isn't set-and-forget: incidents reveal missing or noisy alerts, and you continuously tune toward "every page is real and actionable."

Alerting is where observability becomes *response*, and its quality is measured not by how many alerts you have but by how *trustworthy* each one is. Alert on user-facing symptoms and SLO burn, keep the paging bar high, make every alert actionable with context, and protect the humans on the other end. The final post pulls the whole series together into instrumenting a real system and building the practice.

## Key takeaways

- Alert fatigue — too many false or unactionable alerts — is alerting's defining failure and is worse than no alerting: real alerts get lost, people burn out, and trust collapses; so the goal is that every alert is real, urgent, and actionable, and every noisy alert is a bug to fix or delete.
- Alert on symptoms (what users experience: errors, latency, SLO burn), not causes (CPU, disk, a restart) — causes don't always mean user impact and generate noise, while symptoms are fewer, more meaningful, and worth waking someone for; use causes to diagnose, not to page.
- Tie alerts to SLO error-budget burn rate rather than arbitrary thresholds: page on fast burn (SLO imminently at risk), notify on slow burn — aligning alerts with what you promised and filtering out blips that don't threaten the objective.
- Design alerts for tired humans: severity tiers (page-now vs. ticket), every alert actionable, include context and a runbook, and regularly prune noisy alerts (alert rules are code to maintain).
- Alerting drives on-call, so keep the load sustainable (excessive paging is a bug in the alerts/system), do blameless postmortems, and continuously tune toward "every page is real and actionable."

## Further reading

- [SLIs, SLOs, and error budgets (previous post)](/blog/posts/observ-06-slos-and-error-budgets.html)
- [Google SRE Book — alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Distributed Systems: failure and resilience](/blog/posts/distsys-08-failure-and-resilience.html)
