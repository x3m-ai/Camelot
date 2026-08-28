#!/usr/bin/env python3
"""Compact fixture tests for LOTL converters. No source command is executed."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from convert_lotl import NormalizedProcedure, ProviderStats, build_packs, deduplicate

TOOLS_DIR = Path(__file__).resolve().parent
CONVERTER = TOOLS_DIR / "convert_lotl.py"


class LotlConverterTests(unittest.TestCase):
    def create_sources(self, root: Path) -> tuple[Path, Path]:
        lolbas = root / "lolbas"
        gtfo = root / "gtfobins"
        (lolbas / "yml" / "OSBinaries").mkdir(parents=True, exist_ok=True)
        (gtfo / "_gtfobins").mkdir(parents=True, exist_ok=True)
        (gtfo / "_data").mkdir(parents=True, exist_ok=True)
        (lolbas / "yml" / "OSBinaries" / "Fixture.yml").write_text(textwrap.dedent("""
            Name: Fixture.exe
            Description: Fixture Windows binary
            Commands:
              - Command: Fixture.exe /download {REMOTEURL:.exe} {PATH:.exe}
                Description: Download a file
                Usecase: Download fixture
                Category: Download
                Privileges: User
                MitreID: T1105
                OperatingSystem: Windows 11
              - Command: Fixture.exe /run {CMD}
                Description: Execute a command
                Usecase: Execute fixture command
                Category: Execute
                Privileges: Administrator
                MitreID: T1059
                OperatingSystem: Windows 11
            Detection:
              - Sigma: https://example.invalid/fixture.yml
            Full_Path:
              - Path: C:\\Windows\\System32\\Fixture.exe
        """).strip() + "\n", encoding="utf-8")
        (gtfo / "_data" / "functions.yml").write_text(textwrap.dedent("""
            command:
              label: Command
              description: Run a command.
              mitre: [T1059]
            file-read:
              label: File read
              description: Read a local file.
              mitre: [T1005, T1059]
            inherit:
              label: Inherit
              description: Inherit behavior.
        """).strip() + "\n", encoding="utf-8")
        (gtfo / "_data" / "contexts.yml").write_text(textwrap.dedent("""
            unprivileged:
              label: Unprivileged
              description: Any user.
            sudo:
              label: Sudo
              description: Preconfigured sudo.
            suid:
              label: SUID
              description: Preconfigured SUID.
        """).strip() + "\n", encoding="utf-8")
        (gtfo / "_gtfobins" / "cat").write_text(textwrap.dedent("""
            functions:
              file-read:
                - code: cat /path/to/input-file
                  contexts:
                    unprivileged:
                    sudo:
        """).strip() + "\n", encoding="utf-8")
        (gtfo / "_gtfobins" / "pager").write_text(textwrap.dedent("""
            functions:
              inherit:
                - code: pager help
                  contexts:
                    sudo:
                  from: cat
              command:
                - code: pager -c COMMAND
                  contexts:
                    unprivileged:
                    suid:
        """).strip() + "\n", encoding="utf-8")
        (gtfo / "_gtfobins" / "wrapper").write_text(textwrap.dedent("""
            functions:
              inherit:
                - code: wrapper help
                  contexts:
                    sudo:
                  from: pager
        """).strip() + "\n", encoding="utf-8")
        return lolbas, gtfo

    def run_converter(self, root: Path, output: Path) -> subprocess.CompletedProcess[str]:
        lolbas, gtfo = self.create_sources(root)
        return subprocess.run([
            sys.executable, str(CONVERTER), "--lolbas-dir", str(lolbas),
            "--gtfobins-dir", str(gtfo), "--out-dir", str(output),
            "--no-update-catalog", "--max-per-pack", "50",
        ], capture_output=True, text=True, check=False)

    def test_full_fixture_conversion_and_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            completed = self.run_converter(root, output)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads((output / "conversion-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["lolbas"]["raw_variants"], 2)
            self.assertEqual(report["lolbas"]["published"], 2)
            self.assertTrue(report["lolbas"]["reconciled"])
            self.assertEqual(report["gtfobins"]["raw_variants"], 6)
            self.assertEqual(report["gtfobins"]["published"], 6)
            self.assertEqual(report["gtfobins"]["metrics"]["inheritance_entries"], 2)
            self.assertTrue(report["gtfobins"]["reconciled"])

            lolbas_scripts = [
                script for path in (output / "lolbas").glob("*.json")
                for script in json.loads(path.read_text(encoding="utf-8"))["scripts"]
            ]
            gtfo_scripts = [
                script for path in (output / "gtfobins").glob("*.json")
                for script in json.loads(path.read_text(encoding="utf-8"))["scripts"]
            ]
            self.assertEqual(len(lolbas_scripts), 2)
            self.assertTrue(all(script["name"].startswith("LOLBAS - ") for script in lolbas_scripts))
            self.assertTrue(any("#{lotl_lolbas_remote_url}" in script["command"] for script in lolbas_scripts))
            self.assertTrue(any(script["source_metadata"]["privileges"] == "Administrator" for script in lolbas_scripts))
            self.assertEqual(len(gtfo_scripts), 6)
            self.assertTrue(any(script["source_metadata"]["inherited_from"] == "cat" for script in gtfo_scripts))
            self.assertTrue(any(script["source_metadata"]["inheritance_path"] == ["wrapper", "pager", "cat"] for script in gtfo_scripts))
            self.assertTrue(any(script["source_metadata"]["source_tcodes"] == ["T1005", "T1059"] for script in gtfo_scripts))
            self.assertEqual({script["platform"] for script in gtfo_scripts}, {"linux"})

    def test_conversion_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            first = self.run_converter(root, output)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            initial = {
                str(path.relative_to(output)): path.read_bytes()
                for path in output.rglob("*") if path.is_file()
            }
            second = self.run_converter(root, output)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            repeated = {
                str(path.relative_to(output)): path.read_bytes()
                for path in output.rglob("*") if path.is_file()
            }
            self.assertEqual(initial, repeated)

    def test_common_deduplication_and_stable_chunking(self) -> None:
        procedures = []
        for index in range(52):
            procedures.append(NormalizedProcedure(
                provider="lolbas",
                source_id=f"fixture:{index}",
                source_name=f"Binary{index if index < 51 else 0}",
                name=f"LOLBAS - T1059 - Fixture {index}",
                platform="windows",
                executor="cmd",
                command=f"fixture-{index if index < 51 else 0}",
                primary_tcode="T1059",
                source_tcodes=["T1059"],
                category="Execute",
                context="all",
                risk="interact",
                readiness="ready",
                description="Fixture",
                source_metadata={"source_file": f"fixture/{index}"},
            ))
        stats = ProviderStats(raw_variants=len(procedures))
        unique = deduplicate(procedures, stats)
        self.assertEqual(len(unique), 51)
        self.assertEqual(stats.duplicates, 1)
        self.assertTrue(stats.reconciles())
        packs = build_packs(
            unique, "lolbas", "fixture-sha", "https://example.invalid/lolbas", "GPL-3.0", 50,
        )
        self.assertEqual([len(package["scripts"]) for package, _ in packs], [50, 1])
        self.assertEqual(
            [package["package_id"] for package, _ in packs],
            ["lolbas-execute-01-v1", "lolbas-execute-02-v1"],
        )


if __name__ == "__main__":
    unittest.main()