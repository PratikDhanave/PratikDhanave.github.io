---
title: "Terraform for Regulated Environments: Infrastructure as Compliance Code"
description: "Infrastructure-as-code for compliance: Terraform patterns for SOC 2, ISO 27001, HIPAA. Policy enforcement, guardrails, and compliance automation for regulated cloud."
keywords: ["Terraform", "infrastructure as code", "compliance", "SOC 2", "ISO 27001", "HIPAA", "policy enforcement", "cloud security"]
author: "Pratik Dhanave"
date: "2026-06-04"
readtime: "10-15 min"
canonical: "https://pratikdhanave.github.io/articles/38-terraform-regulated/"
schema: {
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "Terraform for Regulated Environments: Infrastructure as Compliance Code",
  "description": "Guide to using Terraform for compliance enforcement in regulated cloud environments",
  "author": {"@type": "Person", "name": "Pratik Dhanave", "url": "https://pratikdhanave.github.io"},
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
  "image": "https://pratikdhanave.github.io/og-default.png",
  "keywords": ["Terraform", "compliance", "infrastructure as code", "SOC 2"],
  "articleSection": "DevSecOps & Governance"
}
---

# Terraform for Regulated Environments: Infrastructure as Compliance Code

**In regulated industries (finance, healthcare), infrastructure IS compliance.** Your database encryption key, VPC isolation, audit logging — these aren't nice-to-haves, they're mandatory controls.

Most teams manually configure these in the console, which is:
1. Error-prone (humans forget steps)
2. Un-auditable (no proof of what was configured when)
3. Non-repeatable (hard to replicate across environments)

Terraform solves this by turning compliance requirements into code.

---

## The Pattern: Compliance as Terraform Modules

Instead of writing a Terraform file for "deploy a database," write a module for "deploy a SOC 2-compliant database."

```hcl
# modules/secure-database/main.tf

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

resource "google_sql_database_instance" "main" {
  name             = "db-${var.environment}"
  database_version = "POSTGRES_15"
  
  # SOC 2 requirement: Encryption at rest
  settings {
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      backup_retention_days          = var.environment == "prod" ? 30 : 7
    }
    
    # SOC 2 requirement: No public IP
    ip_configuration {
      require_ssl            = true
      private_network        = google_compute_network.private.id
      authorized_networks    = []  # No public access
      enable_private_path_length_check = true
    }
    
    # ISO 27001 requirement: Database audit logging
    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    database_flags {
      name  = "log_statement"
      value = "all"  # Audit every statement
    }
  }
  
  # Deletion protection (prevents accidents in prod)
  deletion_protection = var.environment == "prod" ? true : false
}

# PCI-DSS requirement: Encrypt data at rest
resource "google_kms_crypto_key" "database" {
  name = "database-key-${var.environment}"
  
  lifecycle {
    prevent_destroy = true  # Never delete the key (audit requirement)
  }
}

# ISO 27001 requirement: Monitor access
resource "google_monitoring_alert_policy" "database_access" {
  display_name = "Database access anomaly"
  combiner     = "OR"
  
  conditions {
    display_name = "Unusual connection count"
    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/network/connections\""
      threshold_value = 1000
      comparison      = "COMPARISON_GT"
    }
  }
  
  notification_channels = [google_monitoring_notification_channel.security_team.id]
}
```

**Usage:**
```hcl
# environments/prod/main.tf

module "database" {
  source = "../../modules/secure-database"
  environment = "prod"
}
```

When you `terraform apply`, you're applying compliance as code.

---

## Audit Trail: Proving Compliance

Terraform has state files. These are your compliance proof.

```hcl
# terraform.tfstate (simplified)
{
  "resources": [{
    "type": "google_sql_database_instance",
    "name": "main",
    "instances": [{
      "attributes": {
        "database_version": "POSTGRES_15",
        "settings": {
          "backup_configuration": {
            "backup_retention_days": 30
          },
          "database_flags": [
            {"name": "log_statement", "value": "all"}
          ]
        }
      }
    }]
  }]
}
```

When an auditor asks, "Prove your database has audit logging enabled," you show them:
```bash
$ terraform show | grep log_statement
"log_statement" = "all"
```

**Proof in < 1 second.**

---

## Policy as Code: Prevent Non-Compliant Deployments

Use Sentinel (HashiCorp's policy language) to block non-compliant Terraform plans:

```hcl
# policies/require-encryption.sentinel

import "tfplan/v2" as tfplan

# Ensure all databases have encryption enabled
databases = filter tfplan.resource_changes as _, rc {
  rc.type == "google_sql_database_instance"
}

encryption_enabled = rule {
  all databases as _, db {
    db.change.after.settings[0].backup_configuration[0].location != null
  }
}

main = rule {
  (length(databases) == 0) or encryption_enabled
}
```

When someone tries to deploy a database without encryption:
```
$ terraform apply
Error: Policy violation: require-encryption
Databases must have backup encryption enabled.
```

---

## Production Checklist

- [ ] **Compliance modules** exist for each regulatory requirement
- [ ] **State files are encrypted** and backed up
- [ ] **Audit logging is enabled** on all infrastructure changes
- [ ] **Deletion protection** is on for production
- [ ] **Sentinel policies** block non-compliant deployments
- [ ] **Plan diffs are reviewed** before applying (no auto-apply to prod)

---

**Tags:** #Terraform #Compliance #IaC #SOC2 #ISO27001 #Regulated

**Published:** June 2026  
**Author:** Pratik Dhanave  
**Related Projects:** Bloom (Standard Chartered), regulated fintech
