# License Notice — Stratus Red Team Integration

## Stratus Red Team

- **Source:** https://github.com/DataDog/stratus-red-team
- **Author:** Datadog, Inc. and contributors
- **License:** Apache License 2.0
- **Release integrated:** v2.36.0
- **Commit pinned:** `21c8fefa7cca862b38908090f85b403ed418400c`
- **Official documentation:** https://stratus-red-team.cloud/

This Morgana integration uses the official Stratus Red Team binary release unmodified.
The source is not bundled in this repository. The Morgana Excalibur package scripts invoke
the official pre-built Stratus binary, which is downloaded and verified by SHA256 checksum
on the Morgana Agent.

## Morgana wrapper

The Script command templates in this package (`STRATUS - *` scripts) are original X3M.AI
work (MIT license) that wrap the Stratus CLI for non-interactive Morgana execution with
correlation ID integration.

## Attribution

Stratus Red Team was created by Christophe Tafani-Dereeper at Datadog.
Full contributor list: https://github.com/DataDog/stratus-red-team/graphs/contributors

## Distribution note

The Stratus binary is distributed under the Apache-2.0 license by Datadog.
No Stratus source code is bundled in this Camelot repository.
The runtime binary is fetched from official GitHub release assets with verified checksums.
