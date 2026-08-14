# Infrastructure as Code Security and Policy as Code

*Why your Terraform is a security control point, how misconfiguration scanners catch public buckets and open ingress before apply, and how to encode org guardrails as executable policy with OPA/Rego, Conftest, and Sentinel instead of a wiki page nobody reads.*

---

When infrastructure was provisioned by hand — a console click here, an SSH session there — a mistake was usually a *one-off*. Someone forgot to tick "encrypt this volume," and one volume shipped unencrypted. Infrastructure as Code changed the blast radius. Now the mistake lives in a file, that file gets reviewed once, merged, and then **reused across every environment and every team that imports the module**. A single wrong default doesn't produce one incident; it produces N identical incidents, deployed faster and more reliably than any human could manage.

That is the uncomfortable truth about IaC: the same properties that make it good engineering — repeatability, version control, reuse — make it a *force multiplier for misconfiguration*. A public S3 bucket, a security group open to `0.0.0.0/0`, an IAM role with `*` permissions — these are no longer accidents you find in an audit. They are code, and code scales. Which means IaC is also the best place in your whole stack to *catch* those problems: earlier, cheaper, and before anything real exists to exploit. This post is about treating your infrastructure definitions as a security control point, and enforcing the rules automatically rather than hoping reviewers remember them.

---

## Why IaC is a security control point

The design principle here is **shift left**: move security checks as close to the developer's keyboard as you can, because the cost of fixing a problem grows the further right it travels. Catching a public bucket in a pull request costs a review comment. Catching it in production costs an incident, a disclosure timeline, and a postmortem.

IaC makes this shift possible because the desired state of your infrastructure is now a static, machine-readable artifact *before* it exists. A Terraform plan, a CloudFormation template, a Kubernetes manifest — these can be read, parsed, and judged against rules without touching a cloud account. Compare that to runtime security, where you can only detect the open port after it's already open and reachable. IaC lets you ask "is this configuration safe?" at the point where the answer still costs nothing to act on.

The categories of misconfiguration are remarkably consistent across organizations, and they map directly onto well-documented baselines like the CIS Benchmarks and NIST SP 800-53. The usual suspects:

- **Public storage** — object storage (S3, GCS, Azure Blob) with public-read ACLs or policies, or block-public-access disabled.
- **Overly permissive network ingress** — security groups or firewall rules allowing `0.0.0.0/0` on administrative ports (SSH 22, RDP 3389) or databases.
- **Unencrypted data at rest** — volumes, buckets, databases, and snapshots created without encryption, or without a customer-managed key where policy requires one.
- **Over-broad IAM** — roles and policies granting `*` actions on `*` resources, wildcard principals, or `iam:PassRole` without constraints.
- **Missing logging and audit trails** — resources created without access logging, flow logs, or a CloudTrail/audit sink, so an incident later has no forensic record.

None of these are exotic. That's the point — they're common precisely because the insecure option is often the *default*, and IaC faithfully reproduces defaults.

**The gotcha:** a single insecure module is deployed everywhere it's reused. If your `terraform-aws-s3-bucket` module ships with public access allowed and forty teams import it, you don't have one finding — you have forty, and they'll keep multiplying every time someone runs `terraform apply`. Fix the vulnerability at the *module source*, then track down every consumer; scanning only the leaf configurations means you patch symptoms while the root keeps spreading.

---

## Scanning IaC for misconfiguration in CI

The first line of defense is a static analysis scanner that reads your infrastructure definitions and flags known-bad patterns. Several mature open-source tools do this, and it's worth knowing what each is:

- **Checkov** (by Bridgecrew/Prisma Cloud) — a Python-based scanner with a large library of built-in policies covering Terraform, CloudFormation, Kubernetes, Helm, ARM, and more. Findings are keyed by stable check IDs (e.g. `CKV_AWS_18`), which makes suppression and tracking sane.
- **tfsec** — originally a dedicated Terraform static analyzer with fast, Terraform-aware checks. Its checks and engine have been folded into **Trivy**, so new work generally targets Trivy directly.
- **Trivy** (by Aqua Security) — a broad scanner that covers container images, filesystems, and IaC/misconfiguration in one tool, which is convenient when you want a single binary across your pipeline.

These tools are complementary to policy-as-code, not a replacement — they ship *opinionated, maintained rule sets* derived from public benchmarks so you don't have to author every rule yourself. Run them in CI on every pull request that touches infrastructure, and fail the build on findings above a severity threshold you choose.

Here's the shape of what a scanner catches. This Terraform is the kind of thing that looks fine at a glance and is quietly dangerous:

```hcl
# INSECURE — do not ship this
resource "aws_s3_bucket" "reports" {
  bucket = "acme-quarterly-reports"
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_security_group" "db" {
  name = "db-sg"
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # database open to the entire internet
  }
}
```

A scanner flags the disabled public-access block and the wide-open ingress immediately. The remediated version closes both, adds encryption, and turns on logging:

```hcl
# SECURE
resource "aws_s3_bucket" "reports" {
  bucket = "acme-quarterly-reports"
  tags   = { owner = "data-platform", environment = "prod" }
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_logging" "reports" {
  bucket        = aws_s3_bucket.reports.id
  target_bucket = aws_s3_bucket.audit_logs.id
  target_prefix = "reports/"
}

resource "aws_security_group" "db" {
  name = "db-sg"
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id] # only the app tier
  }
}
```

The secure version isn't cleverer — it just doesn't take the dangerous default. That's most of IaC security: refusing the easy wrong thing, consistently, everywhere.

**The gotcha:** scanners read the *code*, and code isn't always the whole truth. A finding can be a genuine false positive (a bucket that's public on purpose because it serves a static website) or a suppression someone added six months ago and forgot. Use the tool's inline suppression syntax with a required justification, review suppressions in code review like any other change, and periodically audit what's been silenced — an ignored finding is a decision, and decisions decay.

---

## Drift: when reality diverges from the code

Scanning proves your *code* is safe. It says nothing about whether the running infrastructure still matches that code. **Drift** is what happens when someone changes infrastructure out-of-band — a hotfix in the console at 2 a.m., a support engineer widening a security group to debug, a resource created manually and never captured. The code says one thing; the cloud says another.

Drift is corrosive to IaC security specifically because your whole safety argument rests on "the code is the source of truth." Once reality diverges, your green CI runs are checking a fiction. The public-access block your Terraform enforces means nothing if someone toggled it off directly in the console and Terraform hasn't reconciled.

Terraform detects drift through its plan mechanism: `terraform plan` refreshes state against the real provider and shows you the delta between declared and actual. A scheduled plan (often called a *detect-drift* job) that runs on a cadence and alerts when the plan is non-empty turns drift from an invisible slow leak into a monitored signal. Some teams run this hourly on production workspaces; the exact cadence matters less than having one at all.

**The gotcha:** scanning your code while allowing manual console changes gives you *false confidence*. You've secured the artifact and left the door to bypass it wide open — every out-of-band change silently reintroduces the risk your pipeline was built to prevent. Drift detection is only half the fix; the other half is *forbidding* out-of-band changes, which is an IAM and process problem covered below.

---

## Policy as Code: turning org rules into executable checks

Off-the-shelf scanners enforce *industry* baselines. But every organization also has its own rules: "every resource must carry an `owner` tag," "production databases must use customer-managed KMS keys," "no security group may allow ingress from another account's VPC." These live, in most companies, in a wiki page or a Confluence doc — which is to say they live nowhere, because a rule that isn't executable is a suggestion.

**Policy as Code** is the practice of writing those rules as programs that run in your pipeline and return pass/fail. The two dominant approaches:

- **Open Policy Agent (OPA)** with its policy language **Rego**, typically invoked over IaC via **Conftest**, which runs Rego policies against structured config files (Terraform plan JSON, Kubernetes YAML, Dockerfiles). OPA is a CNCF-graduated, general-purpose policy engine — the same Rego you write for Terraform can later gate Kubernetes admission (more on that below).
- **HashiCorp Sentinel**, a policy-as-code framework embedded in Terraform Cloud/Enterprise that evaluates policies against a plan before apply, with enforcement levels (advisory, soft-mandatory, hard-mandatory).

Here's a Rego policy that denies any S3 bucket whose public-access block isn't fully locked down. Conftest evaluates this against the JSON output of `terraform show -json plan.out`:

```rego
package main

# Deny any public-access-block resource that leaves a gate open.
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_public_access_block"
    after := resource.change.after

    # any of the four guards being false means the bucket can be made public
    guards := ["block_public_acls", "block_public_policy",
               "ignore_public_acls", "restrict_public_buckets"]
    guard := guards[_]
    after[guard] == false

    msg := sprintf(
        "S3 bucket '%s' has '%s' disabled — public access is possible; all four guards must be true",
        [resource.address, guard],
    )
}
```

And a companion rule enforcing the org's tagging standard, because "who owns this?" is a security question the day something goes wrong:

```rego
# Every taggable resource must declare an owner.
deny contains msg if {
    resource := input.resource_changes[_]
    tags := object.get(resource.change.after, "tags", {})
    not tags.owner
    msg := sprintf("Resource '%s' is missing the required 'owner' tag", [resource.address])
}
```

The value here is that the rule *is* the documentation. There's no gap between "what the policy says" and "what the pipeline enforces," because they're the same artifact, versioned alongside the code it governs.

**The gotcha:** policy-as-code in the pipeline only guards what *goes through* the pipeline. If a human can `terraform apply` from a laptop, or click in the console, they apply around your policies entirely — the guardrail exists but nobody's obliged to walk through the gate. Pipeline enforcement must be paired with admission-time enforcement (evaluating the same policies at the cluster or cloud-control-plane boundary) and with IAM that makes the pipeline the *only* path to change. Enforcing in one place and leaving the others open is enforcing nowhere.

---

## Guardrails vs. gates: prevent, don't just report

There's an important distinction in how policy runs. A **gate** is a check that reports a verdict — it can pass or fail a build, but it's fundamentally *detective*. A **guardrail** is *preventive*: it stops the bad infrastructure from ever being created, ideally before `apply` runs. The strongest posture combines both, and the design goal is to push enforcement as early and as unavoidable as possible.

In practice this is a spectrum:

| Where enforcement happens | Type | What it catches | Bypass risk |
|---|---|---|---|
| Pre-commit hook / local scan | Advisory | Obvious issues, fast feedback | High — trivially skipped |
| CI pull-request check | Gate | Everything scannable, blocks merge | Medium — needs branch protection |
| Pre-apply policy (Sentinel / Conftest on plan) | Guardrail | Policy violations before provisioning | Low — if apply only runs in the pipeline |
| Admission control (OPA/Gatekeeper, cloud policy) | Guardrail | Anything reaching the control plane, incl. out-of-band | Lowest — enforced at the boundary |

The lesson is that no single layer is sufficient. Pre-commit hooks give fast feedback but are trivially skipped. CI gates are solid but only bind if branch protection requires them and applies run in the pipeline. Pre-apply guardrails stop bad plans, but only for plans that go through the pipeline. Admission control at the control plane catches what everything upstream missed — including manual changes. **Defense in depth means the same rule enforced at multiple layers**, so a bypass at one is caught at the next.

---

## Least privilege for the IaC pipeline itself

Here's a blind spot that shows up constantly. Teams spend weeks hardening the infrastructure their pipeline *produces*, and give the pipeline itself a god-mode credential — an IAM role that can create, modify, and delete essentially anything, sitting in a CI system reachable by anyone who can open a pull request.

Think about what that credential is. Your CI runner is now the single most powerful identity in your cloud account, and it executes code from every branch. A compromised dependency in your build, a malicious pull request that runs during plan, a leaked CI token — any of these inherits the ability to create *anything*. The pipeline that enforces least privilege everywhere else is often the one place it isn't applied.

The remediation follows standard least-privilege principles from NIST and the CIS Benchmarks, applied to the automation identity:

- **Scope the role to what the code actually manages.** If a pipeline only manages networking, it doesn't need IAM-write or the ability to create databases. Grant the specific actions on the specific resource scopes, not `*`.
- **Separate plan from apply.** `plan` needs only read/describe permissions; `apply` needs write. Running plan under a read-only identity means the vast majority of pipeline executions — every PR — never hold write credentials at all.
- **Use short-lived, federated credentials** (OIDC from the CI provider to the cloud) rather than long-lived static keys stored as secrets. A credential that expires in an hour and is minted per-run is far less useful to an attacker than a key that lives in a settings page.
- **Constrain by environment.** The role that can touch production should be assumable only from the protected pipeline on the protected branch, not from a feature branch or a developer's machine.

**The gotcha:** the IaC pipeline's credentials are often the most over-privileged identity in the whole account precisely because "it needs to create infrastructure" is treated as a blank check. It isn't — it needs to create *specific* infrastructure. An attacker who lands code execution in your pipeline doesn't need to find a privilege escalation if the pipeline already has every privilege there is.

---

## Immutable infrastructure and reviewed plans

The final pillar is process, and it's what makes everything above hold together. Two disciplines:

**Reviewed plans.** The `terraform plan` output is a security artifact — it's the precise, reviewable statement of what's about to change. Requiring that a plan be reviewed and approved before `apply` (as a mandatory step, not a courtesy) means a human and your policy engine both see the diff before it touches reality. This is where policy-as-code and human review reinforce each other: the machine catches the rules it knows, the human catches the intent it can't encode.

**Immutable infrastructure and no manual changes.** The strongest defense against drift is to make out-of-band change *impossible* rather than merely discouraged. Immutable infrastructure — where you replace resources rather than mutating them in place, and where the pipeline is the only identity with write access — closes the console-change loophole structurally. If nobody *can* click in the console (because interactive human roles are read-only in production), there's nothing to drift toward. Combined with drift detection as a backstop, out-of-band change stops being a routine risk and becomes an alarm.

The through-line of this whole post: security controls that depend on people remembering things fail quietly and at scale. Controls encoded as code — scanned, gated, and enforced by the pipeline — fail loudly, in a pull request, before anything real is at stake.

---

## Key takeaways

- **IaC is a security control point, for better and worse.** Reuse makes one misconfiguration into N incidents — and also makes one fix protect N deployments. Fix vulnerabilities at the module source, not just the leaf.
- **Scan every infrastructure change in CI.** Checkov, tfsec, and Trivy ship maintained rule sets derived from CIS/NIST baselines; catch public storage, open ingress, missing encryption, over-broad IAM, and absent logging before apply.
- **Drift breaks your source-of-truth assumption.** Detect it with scheduled plans, and — more importantly — prevent it by forbidding manual changes.
- **Policy as Code puts org rules where they're enforced, not where they're forgotten.** Rego with Conftest, or Sentinel in Terraform Cloud, makes "no public buckets, must be encrypted, must have an owner" executable.
- **Prefer preventive guardrails over detective gates, at multiple layers.** Enforce in the pipeline *and* at admission, because pipeline-only policy is bypassed the moment someone applies around it.
- **Scope the pipeline's own credentials.** The identity that provisions everything is your highest-value target — separate plan from apply, use short-lived federated credentials, and constrain by environment.
- **Require reviewed plans and immutable infra.** Make out-of-band change structurally impossible, and let the plan diff be the security review.

---

## Further reading

- [Checkov documentation](https://www.checkov.io/) — checks, suppression syntax, and supported frameworks.
- [Trivy misconfiguration scanning](https://trivy.dev/latest/docs/scanner/misconfiguration/) — IaC/misconfig scanning, which now incorporates the tfsec engine.
- [tfsec (Aqua Security)](https://github.com/aquasecurity/tfsec) — the original Terraform scanner and its migration into Trivy.
- [Open Policy Agent](https://www.openpolicyagent.org/) and the [Rego policy language reference](https://www.openpolicyagent.org/docs/latest/policy-language/).
- [Conftest](https://www.conftest.dev/) — running Rego policies against structured configuration files.
- [HashiCorp Sentinel](https://developer.hashicorp.com/sentinel) — policy as code for Terraform Cloud/Enterprise, including enforcement levels.
- [Terraform recommended practices and security](https://developer.hashicorp.com/terraform/language/state/sensitive-data) — handling sensitive data and state safely.
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks) — the configuration baselines most IaC scanners encode.
- [NIST SP 800-53](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) — the control catalog behind least-privilege and audit-logging requirements.
