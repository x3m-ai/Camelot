# Stratus Red Team — Cloud Adversary Emulation

**Provider:** Stratus Red Team (Datadog)  
**Source:** [DataDog/stratus-red-team](https://github.com/DataDog/stratus-red-team)  
**Release:** v2.36.0 | **Commit:** `21c8fef`  
**License:** Apache-2.0  
**Documentation:** https://stratus-red-team.cloud/  
**Category:** Cloud / Stratus Red Team  
**Scripts:** 93 | **Packages:** 30 | **Chains:** 0  

---

## What is Stratus Red Team?

Stratus Red Team is effectively **Atomic Red Team for cloud environments**.

It provides granular, self-contained cloud adversary-emulation techniques mapped to MITRE ATT&CK, targeting:
- **AWS** (44 techniques)
- **Azure** (15 techniques)
- **GCP** (19 techniques)
- **Entra ID** (7 techniques)
- **Kubernetes** (6 techniques)
- **Amazon EKS** (2 techniques)

Each technique performs a real cloud API operation using the official cloud SDK/CLI.
Stratus handles prerequisite infrastructure (Terraform warmup) and cleanup automatically.

---

## Packages by platform

| Platform | Packages | Scripts |
|---|---|---|
| [AWS](aws/) | 10 | 44 |
| [Azure](azure/) | 6 | 15 |
| [GCP](gcp/) | 7 | 19 |
| [Entra ID](entra-id/) | 1 | 7 |
| [Kubernetes](k8s/) | 3 | 6 |
| [Amazon EKS](eks/) | 2 | 2 |

---

## Lifecycle

Each Morgana Script maps to one Stratus lifecycle:

```
detonate → warmup prerequisites (Terraform where needed) → execute cloud API calls
cleanup  → revert technique side effects → destroy prerequisites
```

The same `MORGANA_TEST_ID` is used as the Stratus correlation ID for both detonate and cleanup.

---

## Authentication prerequisites

| Platform | Requirement |
|---|---|
| AWS | AWS credentials (env vars, profile, or IAM instance profile) |
| Azure | `az login` or Managed Identity |
| Entra ID | `az login` with Entra ID permissions |
| GCP | Application Default Credentials (`gcloud auth application-default login`) |
| Kubernetes | kubectl kubeconfig current context |
| EKS | AWS credentials + `aws eks update-kubeconfig` |

**Never run against production cloud accounts.** Use dedicated sandbox accounts with appropriate IAM/RBAC restrictions.

---

## Important

- Some techniques create real cloud resources (VMs, IAM roles, S3 buckets) that **incur cost**.
- Always run cleanup after detonation.
- Warmup can take 1–5 minutes for Terraform-based infrastructure.
- Some techniques require specific IAM permissions — review package prerequisites before installation.

See [LICENSE-NOTICE.md](LICENSE-NOTICE.md) for attribution.
