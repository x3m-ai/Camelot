# Assessment to Validation Packages

> **Audience:** Merlino analysts, detection engineers and Purple Team leads.
> **Status:** describes the current Assessment → Threat Profile → Catalogue →
> Validation Package flow. Use synthetic or approved data in examples.

## What the assessment produces

The Merlino assessment workbook records organisation context, scenarios,
signals and answers. Its runbooks produce:

- a validated assessment result with per-scenario relevance and confidence;
- a Threat Profile with stable Threat Profile IDs and ATT&CK release provenance;
- a Catalogue of structured validation scope, linked back to the assessment;
- a traceability record (`Assessment_ID`, scenario, mapping version, ATT&CK
  version) for every exported row.

The mapping is marked **`DRAFT_REVIEW_REQUIRED`**. Generated mappings and
candidate packages are drafts: a human must review them before they become an
approved scope.

### NO is not UNKNOWN

- **NO** is evidence that a behaviour is not applicable or not present. It can
  lower relevance while confidence in that conclusion remains high.
- **UNKNOWN** / **Not sure** means the evidence is missing. It lowers confidence;
  it must not be treated as a negative finding or silently removed from the
  scope.

Relevance and confidence are separate. A high-relevance scenario with many
UNKNOWN answers remains relevant but has lower confidence. A confident NO can
remove relevance for that scenario.

## From assessment to packages

1. **Validate the assessment.** Resolve missing required answers; UNKNOWN is a
   valid answer where the workbook allows it, but it is not a blank.
2. **Generate the Threat Profile.** Review the reconstructed profile, Threat
   Profile IDs and ATT&CK version.
3. **Generate the Catalogue.** Review the structured rows and their lineage.
   The Catalogue is the operational starting point, not the final package list.
4. **Generate candidate Validation Packages.** The default builder is a
   candidate generator. One Catalogue row or one Technique does not equal one
   final package. Review, merge, split or defer candidates so each package has
   one coherent validation objective. Generated and merged packages remain
   `DRAFT` with `requires_review` until confirmed.
5. **Check with Morgana.** This is a read-only capability resolution. It creates
   0 packages, Chains, Campaigns, Plans, Tests or runs. It returns the eligible
   Technique/Family/Variant counts used to refine the estimate.
6. **Sync Selected with Morgana.** This is an idempotent package upsert with
   stable external IDs and revisions. It creates Validation Package objects
   only: 0 Tests, 0 Chains, 0 Campaigns, 0 Plans, 0 runs.
7. **Prepare the Execution Plan in Morgana.** Morgana selects eligible
   Families/Variants, applies the chosen strategy and saves a Plan. Saving a
   plan does not execute it.
8. **Execute deliberately and measure assurance.** An operator runs the Plan
   against an authorized Agent. Each Variant produces a Test; Detection Fabric
   and Assurance record what was observed.

## Reuse of Universal Import

Validation Packages reuse the existing Universal Import path for catalogue and
package data. Do not create a second importer or a parallel package format. The
import must preserve assessment lineage and the ATT&CK release; it must not
fabricate missing techniques or silently drop UNKNOWN answers.

## AI is optional and not authoritative

AI-assisted refinement can suggest grouping, naming or rationale. It cannot:

- change an explicit NO into evidence;
- invent a Technique, Variant or execution result;
- approve a package or plan;
- replace the capability check or the human review gate.

Every generated suggestion must be reviewed and must keep its provenance.

## Related guides

- [Morgana Test Intelligence and Validation Packages](../morgana/test-intelligence.md)
- [Merlino manual](../../merlino/README.md)
- [Morgana manual](../../morgana/README.md)
- [Plans and pricing](https://x3m.ai/licensing/)