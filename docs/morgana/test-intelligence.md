# Test Intelligence and Validation Packages

> **Audience:** Morgana operators, Merlino analysts and Purple Team leads.
> **Scope:** the current package-based flow. Legacy Test sync is described in
> the appendix and is not the default path.

## Canonical model

```text
Threat Profile        WHY      which threats and techniques matter
Catalogue             SCOPE    structured validation scope derived from the profile
Validation Package    WHAT     one coherent validation objective
Execution Plan        HOW      exact Families / Variants / Strategy
Test                  RESULT   one real Variant execution
Assurance             LEARNING detection / prevention / coverage evidence
```

Hard distinctions:

```text
Technique != Script          Family != Chain
Validation Package != Chain  Execution Plan != Chain
Package != Campaign          Catalogue row != final Validation Package
```

## Current operator flow

1. **Capability check (read-only).** Merlino resolves package Technique scope to
   Family/Variant/eligibility counts. It creates 0 Validation Packages, 0 Chains,
   0 Campaigns, 0 Plans, 0 Tests and 0 runs.
2. **Package sync.** Merlino sends selected Validation Packages with stable
   external IDs and revisions. Morgana creates or updates **Validation Package
   objects only**: 0 Tests, 0 Chains, 0 Campaigns, 0 Plans, 0 runs.
3. **Plan preparation.** In Morgana, open the package in Technique Intelligence,
   review the eligible Families/Variants, choose an Execution Strategy and save
   an Execution Plan. Saving a plan does not execute it.
4. **Deliberate execution.** An operator launches the Plan against an authorized
   Agent. Each selected Variant produces a Test. No package sync or plan save
   starts a Test implicitly.
5. **Evidence and assurance.** Tests produce output and, when configured,
   Detection Fabric correlation and Assurance. Package status and roll-ups are
   read back by Merlino.

## Execution strategies

| Strategy | Plan content |
|---|---|
| Representative Calibration | A representative Variant per Family |
| Smart Sample | A bounded, risk-aware selection |
| All Variants | Every eligible Variant |
| Custom Selection | Operator-selected Variants |

Community includes manual execution, Test Intelligence, custom selection and
representative calibration. Smart Sample, All Variants, bulk parameter packs,
Detection Fabric and Automation Center are Professional capabilities.

## Legacy sync appendix

The old Merlino Test sync endpoint can create Chain definitions from installed
Scripts. It is a legacy compatibility path for existing tests. It is **not** the
package workflow described above and must not be presented as the current
onboarding path. Use the current package endpoints and the Validation Packages
page; use the legacy path only for an existing integration that already depends
on it.

## Related guides

- [Validation Packages in Merlino](../merlino/validation-packages.md)
- [Morgana manual](../../morgana/README.md)
- [Plans and pricing](https://x3m.ai/licensing/)
- [Merlino manual](../../merlino/README.md)