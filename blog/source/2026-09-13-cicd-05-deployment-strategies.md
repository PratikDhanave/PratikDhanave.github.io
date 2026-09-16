# Deployment Strategies

*How you put new code into production is a design decision with real consequences for risk and downtime. Deploy it all at once and a bad release hits everyone; roll it out gradually and you can catch problems while they're small. Blue-green, canary, rolling, and feature flags are the core techniques — each trading complexity for safety in a different way. This post covers when and why to use each.*

Continuous Delivery/Deployment gets a proven artifact to the door of production; deployment strategy decides how it crosses the threshold. The naive approach — stop the old version, start the new one — causes downtime and exposes every user to any bug simultaneously. The strategies here reduce both risks, and picking the right one is core to safe delivery.

## The problem with big-bang deployment

The simplest deployment is **recreate**: shut down the old version, start the new one. It has two serious problems. There's **downtime** — a window where nothing is serving while the switch happens. And there's **blast radius** — the moment the new version is live, *every* user is on it, so any bug affects everyone at once, and your only recovery is another full redeploy of the old version.

Every strategy below exists to attack one or both of these: eliminate the downtime, shrink the blast radius, or both. The core insight running through all of them is that **a deployment doesn't have to be instantaneous and total** — you can run old and new side by side, and shift traffic deliberately.

## Blue-green: two environments, instant switch

**Blue-green deployment** runs two identical production environments — "blue" (current) and "green" (new). You deploy the new version to green while blue serves all traffic, verify green in a real production environment with no users on it, then **switch all traffic** from blue to green at once (usually by repointing a load balancer or router).

The wins:
- **No downtime** — the switch is instant; green is already warm and ready.
- **Instant rollback** — if green misbehaves, flip traffic straight back to blue, which is still running untouched. Rollback is a routing change, not a redeploy — seconds, not minutes.

The cost is running **two full production environments**, which doubles infrastructure for the deployment window (and requires your database/schema changes to be compatible with both versions during the switch — a real constraint). Blue-green is excellent when you want a clean, instant, reversible cutover and can afford the duplicate environment.

## Canary: expose a few, then ramp

**Canary deployment** (named for the canary in a coal mine) releases the new version to a *small subset* of users first — say 1% — while everyone else stays on the old version. You watch the canary's metrics (errors, latency, business signals); if it's healthy, you gradually increase its share (5%, 25%, 50%, 100%); if it degrades, you route that traffic back and the blast radius was tiny.

The wins:
- **Tiny blast radius** — a bad release affects 1% of users for a few minutes, not everyone.
- **Real-world validation** — the new version is tested on real production traffic and data, catching issues that staging never could, but with limited exposure.
- **Data-driven promotion** — you advance based on *observed metrics*, not hope.

The cost is complexity: you need traffic-splitting infrastructure, and — crucially — **good monitoring**, because a canary is only as useful as your ability to tell whether it's healthy. Canary is the strategy of choice for high-traffic services and for Continuous Deployment, where automated canary analysis (promote or roll back based on metrics, no human) is what makes unattended production releases safe.

## Rolling: replace instances gradually

**Rolling deployment** updates instances in batches: with, say, ten servers, you update two at a time — take two out of rotation, update them, return them, then the next two — until all run the new version. Old and new run simultaneously during the roll.

It's the default in most container orchestrators (Kubernetes rolling updates) because it needs no duplicate environment (unlike blue-green) and no traffic-splitting sophistication (unlike canary) — it just cycles instances. The trade-offs: rollback is *slower* than blue-green (you have to roll back instance by instance), and during the roll both versions serve traffic, so — like blue-green and canary — your changes must be *backward-compatible* across versions. Rolling is the sensible, low-overhead default when you don't need instant rollback or fine-grained canary control.

## Feature flags: decouple deploy from release

**Feature flags** (feature toggles) are a different axis entirely, and the most powerful idea here: they **separate *deploying* code from *releasing* a feature.** A flag is a runtime conditional — `if flag_enabled("new_checkout")` — that lets you ship code to production with a feature turned *off*, then enable it later without a deploy.

This unlocks capabilities the deployment strategies can't:
- **Deploy incomplete work safely** — merge and deploy a half-built feature behind an off flag (enabling the trunk-based development from post 2 — you integrate continuously without releasing unfinished features).
- **Release without deploying** — turn a feature on for users by flipping a flag, instantly, with no deployment.
- **Instant kill switch** — if a released feature misbehaves, turn its flag off in seconds — faster than any rollback.
- **Targeted and gradual release** — enable a feature for internal users, then 5% of customers, then everyone — a canary at the *feature* level, independent of deployment.

The cost is flag management: flags accumulate, and stale flags become technical debt and a source of bugs (untested combinations), so you must retire them once a feature is fully rolled out. Used with discipline, feature flags are the technique that makes Continuous Deployment and trunk-based development genuinely safe, because they let "the code is in production" and "users can see the feature" be two separate, independently-controlled events.

## Choosing a strategy

These aren't mutually exclusive — mature setups combine them (rolling deploys of artifacts, canary analysis on traffic, feature flags on top). A rough guide:
- **Rolling** — low-overhead default; you're fine with gradual rollout and don't need instant rollback.
- **Blue-green** — you want instant, clean, reversible cutovers and can afford duplicate environments.
- **Canary** — high-traffic or high-risk services where limiting blast radius and validating on real traffic matter most; essential for Continuous Deployment.
- **Feature flags** — layer on *everywhere*, to decouple deploy from release, ship dark, and get instant kill switches.

The unifying principle: never make a deployment an all-or-nothing bet on everyone at once. Run versions side by side, shift traffic deliberately, and keep a fast way back. Everything here is a variation on that theme.

## Key takeaways

- Big-bang "recreate" deployment causes **downtime** and maximum **blast radius** (every user hits any bug at once); every strategy attacks one or both by running old and new side by side and shifting traffic deliberately.
- **Blue-green**: two identical environments, instant traffic switch → no downtime + instant rollback (flip back to the untouched old env), at the cost of duplicate infrastructure and version-compatible data.
- **Canary**: release to a small user subset first, watch metrics, then ramp → tiny blast radius + real-traffic validation + data-driven promotion, at the cost of traffic-splitting and *good monitoring* (essential for automated Continuous Deployment).
- **Rolling**: update instances in batches (the orchestrator default) → no duplicate env, no traffic-splitting, but slower rollback and both versions run during the roll (needs backward compatibility).
- **Feature flags** decouple *deploying* code from *releasing* a feature — enabling ship-dark/incomplete work (trunk-based dev), release-without-deploy, instant kill switches, and feature-level gradual rollout — with the discipline cost of retiring stale flags. Combine strategies; never bet everything on everyone at once.

## Further reading

- [Martin Fowler — BlueGreenDeployment](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Martin Fowler — CanaryRelease](https://martinfowler.com/bliki/CanaryRelease.html)
- [Martin Fowler — Feature Toggles (Feature Flags)](https://martinfowler.com/bliki/FeatureToggle.html)
