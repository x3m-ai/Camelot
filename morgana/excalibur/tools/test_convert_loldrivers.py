#!/usr/bin/env python3
"""Focused LOLDrivers converter tests. No driver or generated command is executed."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CONVERTER = TOOLS_DIR / "convert_loldrivers.py"
sys.path.insert(0, str(TOOLS_DIR))
from convert_loldrivers import Procedure, build_packs


class LolDriversConverterTests(unittest.TestCase):
    def write_sources(self, root: Path) -> Path:
        source = root / "source"
        (source / "yaml").mkdir(parents=True, exist_ok=True)
        common_sample = textwrap.dedent("""
            Filename: fixture.sys
            MD5: 11111111111111111111111111111111
            SHA1: 1111111111111111111111111111111111111111
            SHA256: 1111111111111111111111111111111111111111111111111111111111111111
            Signature: ACME Signing
            Publisher: ACME Security
            Company: ACME Security
            Product: Fixture Driver
            ProductVersion: 1.0
            FileVersion: 1.0.0
            MachineType: AMD64
            OriginalFilename: fixture.sys
        """).strip()
        (source / "yaml" / "vulnerable.yaml").write_text(textwrap.dedent(f"""
            Id: vulnerable-object
            Tags: [fixture.sys]
            Author: Fixture
            Created: '2026-01-01'
            MitreID: T1068
            CVE: [CVE-2026-12345, CVE-2026-67890]
            Category: vulnerable driver
            Verified: 'TRUE'
            Commands:
              Command: sc.exe create fixture binPath=C:\\Temp\\fixture.sys type=kernel
              Description: Source load example
              Usecase: Elevate privileges
              Privileges: kernel
              OperatingSystem: Windows 11
            Resources: [https://example.invalid/vulnerable]
            Detection:
              - type: Sigma
                value: https://example.invalid/sigma
            KnownVulnerableSamples:
              - {common_sample.replace(chr(10), chr(10) + '                ')}
        """).strip() + "\n", encoding="utf-8")
        (source / "yaml" / "malicious.yaml").write_text(textwrap.dedent(f"""
            Id: malicious-object
            Tags: [fixture.sys, second.sys]
            Author: Fixture
            Created: '2026-01-02'
            MitreID: T1014, T1068
            Category: malicious
            Verified: 'FALSE'
            Commands:
              Command: sc.exe create second binPath=C:\\Temp\\second.sys type=kernel
              Description: Source malicious example
              Usecase: Rootkit behavior
              Privileges: kernel
              OperatingSystem: Windows 10
            Resources: []
            Detection: []
            KnownVulnerableSamples:
              - {common_sample.replace(chr(10), chr(10) + '                ')}
              - Filename: second.sys
                SHA1: 2222222222222222222222222222222222222222
                Signature: ACME Signing
                Publisher: ACME Security
                Company: ACME Security
                Product: Second Driver
                FileVersion: 2.0
                MachineType: x86
        """).strip() + "\n", encoding="utf-8")
        return source

    def test_complete_fixture_expansion_and_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write_sources(root)
            output = root / "output"
            completed = subprocess.run([
                sys.executable, str(CONVERTER), "--source-dir", str(source),
                "--out-dir", str(output), "--no-update-catalog", "--max-per-pack", "50",
            ], capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads((output / "conversion-report.json").read_text(encoding="utf-8"))
            inventory = json.loads((output / "source-inventory.json").read_text(encoding="utf-8"))
            self.assertEqual(report["yaml_objects"], 2)
            self.assertEqual(report["sample_associations"], 3)
            self.assertEqual(report["unique_samples"], 2)
            self.assertEqual(report["duplicate_sample_associations"], 1)
            self.assertEqual(report["procedure_counts"]["source_command_simulation"], 2)
            self.assertEqual(report["procedure_counts"]["cve_exposure"], 1)
            self.assertTrue(report["sample_inventory_reconciled"])
            self.assertTrue(report["procedure_reconciled"])
            self.assertEqual(len(inventory), 3)
            self.assertTrue(all(row["source_command"] for row in inventory))

            packages = [json.loads(path.read_text(encoding="utf-8")) for path in output.glob("*/*.json")]
            scripts = [script for package in packages for script in package["scripts"]]
            self.assertEqual(len(scripts), report["published"])
            self.assertTrue(all(package["assets"] == [] and package["chains"] == [] for package in packages))
            self.assertTrue(all(script["name"].startswith("LOLDRIVERS - ") for script in scripts))
            self.assertTrue(any(script["source_metadata"].get("cves") == ["CVE-2026-12345", "CVE-2026-67890"] for script in scripts))
            simulation = next(script for script in scripts if script["source_metadata"]["procedure_family"] == "source_command_simulation")
            self.assertIn("#{loldrivers_benign_driver_path}", simulation["command"])
            self.assertNotIn("C:\\Temp\\fixture.sys", simulation["command"])

    def test_chunking_is_stable(self) -> None:
        procedures = [
            Procedure(
                source_id=f"sample:{index}", family="hash_presence", category="vulnerable",
                name=f"LOLDRIVERS - T1068 - Hash Presence - {index}", command=f"Write-Output {index}",
                tcode="T1068", source_tcodes=["T1068"], risk="observe", readiness="ready",
                required_tags=[], description="Fixture", source_metadata={"sample_identity": f"sample:{index}", "cves": []},
            )
            for index in range(51)
        ]
        first = build_packs(procedures, "fixture-sha", 50)
        second = build_packs(list(reversed(procedures)), "fixture-sha", 50)
        self.assertEqual([package["package_id"] for package, _ in first], ["loldrivers-vulnerable-hash-presence-01-v1", "loldrivers-vulnerable-hash-presence-02-v1"])
        self.assertEqual(
            [[script["id"] for script in package["scripts"]] for package, _ in first],
            [[script["id"] for script in package["scripts"]] for package, _ in second],
        )


if __name__ == "__main__":
    unittest.main()