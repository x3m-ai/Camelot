# License Notice — LOLRMM Integration

## LOLRMM

- **Source:** https://github.com/magicsword-io/LOLRMM
- **Author:** MagicSword contributors
- **License:** Apache License 2.0
- **Commit pinned:** `fa859607fb05af91878ac8d44a59655f44d286fe`
- **Project website:** https://lolrmm.io/

All LOLRMM YAML source data, tool descriptions, artifact metadata, detection rules,
and Sigma rules are subject to the Apache License 2.0 from the upstream repository.

## Morgana integration

The Morgana LOLRMM probe scripts and converter code are original X3M.AI work (MIT).
No LOLRMM YAML source files are modified; the integration reads them as-is.

## Important

LOLRMM catalogs legitimate Remote Monitoring and Management (RMM) and Remote Access
Tool (RAT) software that may be abused by threat actors. This integration does NOT
install, operate, or download any of the cataloged tools. It generates read-only
artifact-presence probes and intelligence profiles only.
