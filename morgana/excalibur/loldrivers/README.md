# LOLDrivers Windows Driver Security Packs

Metadata-only Morgana procedures derived from the complete LOLDrivers structured corpus. No known vulnerable or malicious driver binary is downloaded, packaged, loaded, or exploited.

## Corpus

- Source commit: `c8652a34e287988f1c826ca671909342317eaf95`
- YAML objects: 663
- Sample associations: 2215
- Unique sample identities: 2111
- Published procedures: 18766
- Packages: 58
- Validation: PASS

## Procedure Families

- `blocklist_validation`: 2111
- `cve_exposure`: 155
- `driver_service_inventory`: 1739
- `event_code_integrity`: 2111
- `event_defender`: 2111
- `event_service_control_manager`: 2111
- `event_sysmon_driver_load`: 2111
- `filename_presence`: 1739
- `hash_presence`: 2027
- `loaded_driver_inventory`: 1739
- `signer_publisher_hunt`: 810
- `source_command_simulation`: 2

Search roots and event lookback values are operator-configurable Morgana Tags. Benign telemetry simulations require an operator-supplied valid test-signed driver and never use LOLDrivers sample binaries.

Run `morgana/excalibur/tools/update-loldrivers-packs.ps1` for deterministic source updates, full static validation, and optional representative imports.
