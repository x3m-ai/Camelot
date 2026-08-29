# License Notice — Elastic Cortado Integration

## Elastic Cortado

- **Source:** https://github.com/elastic/cortado
- **Author:** Elasticsearch B.V. and contributors
- **License:** Elastic License 2.0
- **Release integrated:** dev-release-0.1.0+f1dd8bc1
- **Commit pinned:** `f1dd8bc1883a399c4990f2f4a63d7a3d26cdd89e`

The Elastic Cortado source code, Python wheel, and all RTA files are subject to the
**Elastic License 2.0**. Please review the full license before use:
https://www.elastic.co/licensing/elastic-license

This Morgana integration uses the official Elastic Cortado wheel unmodified.
The RTA source code is not modified; the Morgana runner (`morgana_cortado_runner.py`)
wraps the official Cortado runtime for non-interactive execution.

## Morgana Cortado Runner

`morgana_cortado_runner.py` is an original X3M.AI work (MIT license) that wraps
the Cortado CodeRTA execution path for Morgana Agent orchestration.

## Sample content warning

Some Elastic Cortado RTAs (HashRta type) reference external binary samples that
may be malicious. These samples are NOT included in this repository and are NOT
automatically acquired by Morgana. Use only in isolated, authorized test environments.

## Distribution note

The Cortado wheel (`cortado-0.1.0+f1dd8bc1-py3-none-any.whl`) is distributed by
Elastic as an official release asset from the public GitHub repository. It is
fetched and verified by SHA256 checksum by the Morgana Asset system.
No Cortado source code is bundled directly in this Camelot repository.
