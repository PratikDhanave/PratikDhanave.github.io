# Secrets Management: Keeping Credentials Out of Code and Under Control

*How to move from hardcoded passwords toward dynamic, short-lived, audited credentials — the hierarchy from bad to good, the role of a real secrets manager, and why a leaked secret is compromised the instant you push it.*

---

Every application needs to prove who it is: a database password, an API key, a cloud access key, a signing certificate. These credentials — **secrets** — are the single most valuable thing an attacker can steal, because a valid secret makes an intruder indistinguishable from a legitimate service. And they are the most commonly mishandled thing in a codebase. In [post 3 of this series](/blog/tags/devsecops/) we wired *secret scanning* into the pipeline so tools like **gitleaks** catch credentials before they land in git history. That is a safety net, not a strategy. Scanning tells you when you've already failed; secrets *management* is about designing so the failure can't happen — and so that when it inevitably does, the blast radius is small and the recovery is a rotation, not a rewrite.

This post walks the hierarchy from the worst way to handle a secret to the best, covers what a secrets manager actually gives you, and argues that the ideal secret is one that never persists at all.

---

## The problem: secrets leak from everywhere

A credential is only useful if the code can read it, which means it has to live *somewhere*. The failure mode is putting it somewhere durable and copyable. The usual suspects:

- **Hardcoded in source.** `password = "hunter2"` in a `.py` or `.go` file. It's now in every clone, every fork, and every commit forever.
- **A `.env` file committed to the repo.** People treat `.env` as local config and then `git add .` sweeps it in. Same outcome as hardcoding, one step removed.
- **Baked into container images.** An `ENV DB_PASSWORD=...` line in a Dockerfile, or a secret copied into an image layer. Anyone who can `docker pull` the image can `docker history` or unpack the layers and read it.
- **Printed to logs.** A well-meaning `log.Printf("config: %+v", cfg)` dumps the whole config struct — secrets included — into your log aggregator, where it's indexed, retained, and readable by anyone with dashboard access.
- **Sitting in CI configuration.** A plaintext token in a `.gitlab-ci.yml`, a Jenkinsfile, or a workflow file. CI config is source code and leaks like source code.

OWASP and NIST both frame this the same way: minimize where secrets exist, minimize how long they exist, and control and record every access. Everything below is an application of those three ideas — **least privilege, short-lived, audited** — plus the rotation and recovery that make them survivable.

**The gotcha:** environment variables feel safe because they're "not in the code," but a process-wide env var is broadly exposed. It's inherited by every child process you spawn, it's readable from `/proc/<pid>/environ` by anything running as the same user, it gets captured in crash dumps and core files, and a stray `log.Println(os.Environ())` or an error reporter that attaches the environment will ship it off-box. Env vars are fine for non-secret config and acceptable for low-sensitivity tokens injected by CI — but for your most sensitive credentials, prefer a value your process *fetches* on demand over one that lives in the process environment for the lifetime of the program.

---

## The hierarchy: from bad to good

Think of secret handling as a ladder. Each rung is strictly better than the one below it, and the goal is to climb as high as your infrastructure allows.

| Rung | Approach | Why it's better than the one below |
|---|---|---|
| 0 (worst) | Hardcoded in source | — |
| 1 | Env var from a committed `.env` | Nominally out of code, but still in the repo |
| 2 | Env var injected from a CI/platform secret store | Not in the repo; access is at least gated |
| 3 | Fetched at runtime from a **secrets manager** | Centralized storage, access policies, audit log |
| 4 | **Dynamic** secret with a short TTL | Generated on demand, auto-expires, per-consumer |
| 5 (best) | **No stored long-lived secret** — workload identity / OIDC | Nothing to leak; identity proven by the platform |

Rungs 0 and 1 are the ones secret scanning exists to stop. Rung 2 — a token stored in GitHub Actions secrets or your platform's secret store and injected as an env var at deploy time — is the *minimum* acceptable bar for a real system: the secret isn't in the repo, and access is controlled by the platform. But it's still a long-lived value sitting in a store, copied into an env var, and only rotated when someone remembers to. The interesting engineering happens from rung 3 up.

---

## Secrets managers: storage, policy, and audit

A **secrets manager** is a dedicated service whose whole job is to hold secrets safely and hand them out under control. The mainstream options are **HashiCorp Vault** and the cloud-native services — **AWS Secrets Manager**, **Google Cloud Secret Manager**, **Azure Key Vault** — often paired with a **KMS** (Key Management Service) that holds the encryption keys those services use. What you get over "a token in an env var":

- **Encrypted, centralized storage.** Secrets are encrypted at rest under a KMS-managed key. There's one place to store, version, and reason about them.
- **Fine-grained access policies.** You bind a policy to an identity: *this* service can read *this* path, nothing else. That's least privilege made concrete — a compromised service can only reach the handful of secrets it was granted, not the whole vault.
- **An audit log.** Every read, write, and denied attempt is recorded. When you're doing incident response, "who read this secret and when" is the difference between a scoped investigation and a company-wide panic.
- **A single rotation point.** Because consumers fetch from one place, you can change a secret centrally instead of hunting down every copy.

The code side is deliberately boring: your app authenticates to the manager (itself using a platform identity — more on that below), asks for a secret by name, and gets it back. The critical design choice is **fail closed** — if the secret can't be fetched, the app must refuse to start rather than silently fall back to a default, an empty string, or a stale cached value.

```go
package config

import (
	"context"
	"fmt"
	"time"
)

// SecretsClient is whatever your manager's SDK provides — Vault, AWS Secrets
// Manager, GCP Secret Manager, Azure Key Vault all expose a "fetch by name" call.
type SecretsClient interface {
	GetSecret(ctx context.Context, name string) (string, error)
}

// MustLoadSecret fetches a secret at startup and HARD-FAILS if it can't.
// No default, no empty string, no "log a warning and continue" — a missing
// credential is a fatal misconfiguration, not a recoverable condition.
func MustLoadSecret(ctx context.Context, sm SecretsClient, name string) string {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	val, err := sm.GetSecret(ctx, name)
	if err != nil {
		// Fail closed. Do NOT log `val` or the underlying secret material.
		panic(fmt.Sprintf("fatal: could not load required secret %q: %v", name, err))
	}
	if val == "" {
		panic(fmt.Sprintf("fatal: secret %q resolved to an empty value", name))
	}
	return val
}
```

**The gotcha:** notice the code never logs the secret's *value*, only its *name*, and even the error path prints only the manager's error — not the material. A surprising number of leaks come from the code that handles secrets correctly right up until an error handler dumps the payload into a log line to "help debugging." Log the name, the path, the timestamp, the caller — never the secret.

---

## Dynamic secrets and short TTLs: the real prize

Storing a static password in a manager is good hygiene, but the password is still static — the same value works for months, so a single leak is durably dangerous. The step-change is **dynamic secrets**: instead of storing a credential, the manager *generates one on demand* and *revokes it automatically* after a short time-to-live.

Vault's database secrets engine is the canonical example. Your app doesn't hold a database password at all; it asks Vault, Vault connects to the database as an admin, creates a brand-new user with a random password and a 15-minute lease, and returns those credentials. When the lease expires, Vault drops the user. The credential that leaks at 2:00 is useless by 2:15, and because each consumer gets its own generated credential, the audit trail ties every database session back to a specific request.

The principle generalizes: short-lived beats long-lived every time, because the value of a stolen secret is proportional to how long it stays valid. A 15-minute credential is a rounding error of risk compared to a key that's been valid since 2023.

**The gotcha:** short TTLs only work if consumers *re-read*. An app that fetches a 15-minute credential once at startup and caches it in a package-level variable will be running on an expired lease within the hour — and will either break or, worse, cling to a credential the manager thinks it revoked. If you use short TTLs, you must renew the lease or re-fetch before expiry. This is the same trap as rotation, which is the next section.

---

## Rotation: only helps if consumers re-read

**Rotation** is replacing a secret with a new value on a schedule so that an undetected leak has a bounded lifetime. Cloud secrets managers automate this — AWS Secrets Manager, for instance, can run a rotation function that generates a new database password, updates the database, and updates the stored secret, all without a human. Automated rotation should be the default for every static secret you can't yet replace with a dynamic one.

But rotation is only half a mechanism. Changing the value in the manager does nothing if your application read the old value once and holds it forever.

**The gotcha:** rotation is useless if the app caches the old value indefinitely. A service that loads a secret at boot into a global and never looks again will keep authenticating with the pre-rotation credential until it happens to restart — which means either the rotation "succeeds" while every consumer silently keeps using the stale secret, or the old credential gets invalidated and every consumer breaks at once. Design for rotation up front: re-read on a cache TTL shorter than the rotation interval, subscribe to a rotation event/notification, or lean on short-lived dynamic secrets so re-reading is already part of the loop. Rotation and short TTLs are the same discipline viewed from two angles — both demand that consumers treat a secret as something to fetch again, not something to keep.

---

## Workload identity and OIDC: the best secret is no secret

The top of the ladder removes the stored secret entirely. Instead of your CI job or service *holding* a cloud key, the platform *vouches for its identity* and the cloud hands back a short-lived token. This is **workload identity federation**, and it's built on **OIDC** (OpenID Connect): the platform issues a signed, short-lived identity token describing the workload, and the cloud — configured to trust that issuer — exchanges it for temporary credentials scoped to a specific role.

The most common concrete case is **GitHub Actions OIDC → a cloud role**. Historically you'd store a long-lived AWS access key as a repository secret; every workflow that needs AWS reads it, and if it ever leaks, an attacker has standing access until someone rotates it. With OIDC, the workflow requests a signed token from GitHub's OIDC provider, presents it to AWS STS, and receives temporary credentials good for the length of the job. There is **no long-lived cloud key stored anywhere** — nothing in the repo, nothing in GitHub secrets, nothing to leak.

```yaml
# GitHub Actions: assume a cloud role via OIDC — no stored cloud key.
# The `id-token: write` permission is what lets the job request a signed
# OIDC token from GitHub; the cloud role is configured to trust GitHub's
# OIDC issuer and this specific repo/branch as the subject.
permissions:
  id-token: write   # allows the job to mint the OIDC token
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      # The cloud login action exchanges GitHub's OIDC token for
      # short-lived credentials scoped to the role's policy. No secret
      # key material is stored in the repo or in Actions secrets.
      - name: Configure cloud credentials via OIDC
        uses: <cloud-provider-login-action>   # e.g. aws-actions/configure-aws-credentials
        with:
          role-to-assume: <arn-of-the-least-privileged-deploy-role>
          # ...provider-specific inputs; the exact keys live in the action's docs
```

The same pattern secures running services: Kubernetes workloads use their service-account token to assume a cloud IAM role (IRSA on EKS, Workload Identity on GKE, Workload Identity Federation on Azure), so pods reach cloud APIs with no stored keys. The mental model is: **prove identity, borrow a short-lived token, discard it** — rather than **hold a permanent key and hope it never leaks**.

**The gotcha:** the best secret is no stored secret. Every long-lived credential you delete is one you never have to rotate, scan for, or explain in an incident. Before you reach for a secrets manager to *store* a cloud key, ask whether workload identity/OIDC lets you avoid storing it at all — the answer is increasingly yes for CI, cloud services, and cross-cloud access.

---

## GitOps: encrypt secrets at rest in the repo

There's a tension in the GitOps model, where the desired state of a cluster — including its secrets — lives in git. You want the manifests in version control, but you can't put a plaintext Kubernetes `Secret` in a repo. Two well-established patterns resolve it by keeping only *encrypted* secrets in git:

- **SOPS** (Secrets OPerationS) encrypts the *values* in a YAML/JSON file while leaving the keys readable, so a diff still shows what changed structurally. It encrypts against a KMS key, age key, or PGP key, and only something holding the decryption key — a cluster operator, a controller — can read the values.
- **Sealed Secrets** (a Kubernetes controller) lets you encrypt a Secret into a `SealedSecret` custom resource that's safe to commit; the in-cluster controller is the only thing that can decrypt it back into a real Secret.

Either way the encryption key lives outside the repo (typically in a cloud KMS), and only the decryption endpoint can recover the plaintext — so the git repository holds ciphertext that's useless on its own. A common production shape is the **External Secrets Operator**, which does the opposite direction: it pulls secrets from an external manager (Vault, a cloud Secrets Manager) into the cluster at runtime, so git holds only a *reference* to the secret, never the value at all.

---

## Incident response: a leaked secret is a compromised secret

When a secret leaks — a key in a public push, a token in a screenshot, a password in a support ticket — there is exactly one correct first move: **rotate it**. Generate a new value, deploy it, invalidate the old one. The leaked credential must be made worthless as fast as possible.

**The gotcha:** deleting the commit does not un-leak the secret. This is the most expensive mistake in the whole topic. The instant you `git push` a secret to a public repo, assume it is compromised — automated bots continuously scrape public pushes and public gists, and a leaked key is often used within *seconds to minutes*, long before you notice. Rewriting history with `git filter-repo`, force-pushing, or deleting the repo removes the *evidence*, not the *exposure*: anyone (or any bot) who pulled in that window still has the value, and it may already be cached in forks, CI logs, and mirror caches. History rewriting is a cleanup step you do *after* rotating, never instead of it. The order is always: **rotate first, then clean up, then figure out how it got there** so scanning and policy can stop the next one.

---

## Key takeaways

- **Secrets leak from everywhere** — source, `.env` files, images, logs, CI config. Secret scanning (post 3) catches failures; management prevents them.
- **Climb the ladder.** Hardcoded → `.env` in repo → CI-injected env var → secrets manager → dynamic/short-lived → no stored secret at all. Aim as high as your platform allows.
- **A secrets manager buys you policy and audit,** not just storage. Bind least-privilege policies to identities and treat the audit log as an incident-response asset. Fail closed when a secret can't be fetched.
- **Short-lived beats long-lived.** Dynamic secrets and tight TTLs shrink the value of any leak to near zero — but only if consumers re-read instead of caching forever.
- **Rotation is half a mechanism** until consumers re-read the rotated value. Design re-fetching in from the start.
- **The best secret is no stored secret.** Workload identity and OIDC (e.g. GitHub Actions OIDC → a cloud role) give CI and services short-lived tokens with nothing durable to leak.
- **A leaked secret is compromised the moment it's pushed.** Rotate first; deleting the commit removes evidence, not exposure.

---

## Further reading

- [HashiCorp Vault documentation](https://developer.hashicorp.com/vault/docs) — secrets engines, dynamic secrets, leases, and policies.
- [AWS Secrets Manager documentation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) and [AWS KMS documentation](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html).
- [Google Cloud Secret Manager documentation](https://cloud.google.com/secret-manager/docs) and [Azure Key Vault documentation](https://learn.microsoft.com/en-us/azure/key-vault/general/overview).
- [GitHub Actions: OpenID Connect (OIDC) hardening](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect).
- [SOPS (Secrets OPerationS)](https://github.com/getsops/sops) and the [External Secrets Operator](https://external-secrets.io/).
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html).
- [NIST SP 800-57: Recommendation for Key Management](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final).
