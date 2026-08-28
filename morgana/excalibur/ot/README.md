# MITRE CALDERA for OT Packs

Morgana-native content converted from the six official MITRE CALDERA for OT plugins. Morgana consumes the content without requiring a CALDERA server at runtime. The packs use ATT&CK for ICS (`ics-attack`), preserve source technique and tactic metadata, and declare the `OT - ` script prefix.

> Some CALDERA for OT abilities can change device or process state. Use them only in an explicitly authorized lab, simulation, or approved production exercise.

Tag values are intentionally empty. No public or default OT target is supplied, and installing a pack never downloads an asset to an Agent or executes a command.

## Supported Protocols

| Protocol | Packs | Scripts |
|---|---:|---:|
| BACnet | 4 | 42 |
| DNP3 | 3 | 88 |
| Modbus | 3 | 36 |
| Profinet DCP | 2 | 21 |
| IEC 61850 MMS | 0 | 0 |
| GEMS | 3 | 36 |

Packs are split by protocol and ATT&CK for ICS tactic, for example `ot-modbus-discovery-v1`. One upstream platform/executor variant becomes one deterministic Morgana Script.

## Risk Model

Every Script has an operational risk level:

| Risk | Meaning |
|---|---|
| `observe` | Read-only discovery, metadata, or value queries |
| `interact` | Protocol requests not intended to alter process state |
| `modify` | May change configuration, parameters, coils, registers, or control values |
| `disrupt` | May stop, disable, inhibit, delete, or significantly affect operation |

Morgana displays risk badges in the Excalibur catalog and Scripts view. Direct Script, Chain, and Campaign execution containing `modify` or `disrupt` content requires explicit operator acknowledgement. Imported high-risk content is never executed automatically.

## Parameters And Assets

CALDERA facts are converted to scoped Morgana tags. Connection, read, process-write, and control parameters remain empty until an operator assigns values.

Protocol utilities are distributed as package assets rather than embedded in the database. Each asset records its controlled HTTPS URL, safe filename, platform, architecture, source repository and commit, license, size, and SHA256. On execution the Agent:

1. Downloads required assets into its per-Test work directory.
2. Enforces platform, architecture, filename, and size policy.
3. Verifies SHA256 before resolving `{{asset:<id>}}` placeholders.
4. Applies executable permission only when declared.
5. Removes the work directory after execution.

The legacy `download_url` and `{{payload}}` path remains supported for older content.

## Install In Morgana

1. Open **Scripts > Excalibur Packs**.
2. Select **Refresh catalog**.
3. Expand **MITRE CALDERA for OT** and review protocol and risk badges.
4. Import only the required packs.
5. Open an imported Script and assign all required tags for the authorized target.

Import stores Scripts, one-step Chains, tags, and asset metadata. Assets are delivered only after explicit execution.

## Safe Lab Validation

Use an isolated, authorized simulator or cyber range. The recommended first validation is the Modbus Discovery pack and an `observe` Script such as Read Device Information. Verify the simulator address and port, select a matching Agent platform, and confirm expected telemetry before considering higher-risk content.

Do not begin with write-coil, restart, shutdown, disable, denial-of-service, or network-configuration abilities. No test in this repository should be pointed at a live industrial device without written approval and an agreed rollback plan.

## Update Process

From `morgana/excalibur/tools`, run `update-caldera-ot-packs.ps1`. The updater recursively refreshes the umbrella repository and its six official submodules under `C:\ProgramData\Morgana\temp\caldera-ot`, records every source SHA, regenerates packs and inventories, and runs deterministic/static validation. Publication requires the explicit `-Publish` switch.

The converter reads and packages upstream content; it never runs source commands or assets. Review `conversion-report.json`, `source-inventory.json`, and `asset-inventory.json` before publication.

## Provenance And Licensing

Umbrella source commit: `1937fb1e32338747fdcc37a8edefa64672f26e99`.

Each protocol directory contains the LICENSE and NOTICE files found in its pinned plugin checkout. Asset entries preserve source repository, source commit, license, and SHA256. Licensing must be reviewed independently for every plugin and external payload source before redistribution.

## Known Limitations

IEC 61850 abilities require separately published binaries from `mitre/iec61850-payloads`. Those 64 variants are classified as `external_release` in the inventories and are intentionally not published until a release/version, repository, license, and SHA256 are pinned. Source-build-required or unresolved variants are likewise excluded rather than emitted as executable Scripts.

Only the six official MITRE plugins are included in this phase. Community plugins and simulator deployment are outside scope.
