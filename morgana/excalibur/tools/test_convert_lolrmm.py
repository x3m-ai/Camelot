#!/usr/bin/env python3
"""Focused unit tests for LOLRMM converter. No RMM products are installed or executed."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
LOT_DIR = TOOLS_DIR.parent / "lotl" / "lolrmm"
PKG_DIR = LOT_DIR / "packages"

sys.path.insert(0, str(TOOLS_DIR))
from lolrmm_source import normalize_tool, LOLRMM_COMMIT

WINDOWS_FIXTURE = """
Name: TestRMM
Category: RMM
Description: A test RMM tool with rich artifacts.
Author: tester
Created: 2024-01-01
LastModified: 2024-06-01
Details:
  Website: https://testrmm.example.com
  PEMetadata:
    Filename: testrmm.exe
    OriginalFileName: TestRMM.exe
    Description: TestRMM Agent
  Privileges: SYSTEM
  Free: "Yes"
  Verification: ""
  SupportedOS:
    - Windows
  Capabilities:
    - Remote monitoring and management
    - File transfer
  Vulnerabilities: []
  InstallationPaths:
    - C:\\Program Files\\TestRMM\\testrmm.exe
Artifacts:
  Disk:
    - File: C:\\ProgramData\\TestRMM\\config.ini
      Description: Configuration file
      OS: Windows
  EventLog:
    - EventID: 7045
      ProviderName: Service Control Manager
      LogFile: System
      ServiceName: TestRMM
      Description: Service installation
  Registry:
    - Regkey: HKLM\\SOFTWARE\\TestRMM
      Description: Installation registry key
  Network:
    - Description: Known remote domains
      Domains:
        - "*.testrmm.example.com"
      Ports:
        - 443
Detections:
  - Sigma: https://github.com/magicsword-io/LOLRMM/blob/main/detections/sigma/testrmm_sigma.yml
    Description: Detects TestRMM network activity
References:
  - https://testrmm.example.com/docs
Acknowledgement: []
CodeSigning:
  search_names:
    - testrmm.exe
  signer_names:
    - TestRMM Corp
  certificates: []
"""

MINIMAL_FIXTURE = """
Name: MinimalRMM
Category: RAT
Description: Minimal remote access tool.
Details:
  Website: ""
  SupportedOS: []
  Capabilities: []
  InstallationPaths: []
Artifacts:
  Disk: []
  EventLog: []
  Registry: []
  Network: []
"""


class LolrmmConverterTests(unittest.TestCase):

    def _parse(self, content: str, name: str = "test.yaml") -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / name
            f.write_text(content, encoding="utf-8")
            return normalize_tool(f, LOLRMM_COMMIT)

    def test_rich_windows_tool_parsed(self):
        t = self._parse(WINDOWS_FIXTURE, "testrmm.yaml")
        self.assertEqual(t["name"], "TestRMM")
        self.assertEqual(t["category"], "RMM")
        self.assertIn("windows", t["platforms"])
        self.assertTrue(t["probe_capable"])
        self.assertTrue(t["has_registry"])
        self.assertTrue(t["has_evtlog"])
        self.assertTrue(t["has_files"] or t["has_filenames"])
        self.assertTrue(t["has_domains"])
        self.assertEqual(len(t["detections"]), 1)
        self.assertEqual(t["tool_id"], "lolrmm:testrmm")

    def test_minimal_tool_is_manual(self):
        t = self._parse(MINIMAL_FIXTURE, "minimalrmm.yaml")
        self.assertEqual(t["name"], "MinimalRMM")
        self.assertFalse(t["probe_capable"])
        self.assertEqual(t["platforms"], [])

    def test_pe_metadata_extracted(self):
        t = self._parse(WINDOWS_FIXTURE, "testrmm.yaml")
        self.assertGreater(len(t["pe_metadata"]), 0)
        self.assertEqual(t["pe_metadata"][0]["filename"], "testrmm.exe")

    def test_code_signing_preserved(self):
        t = self._parse(WINDOWS_FIXTURE, "testrmm.yaml")
        self.assertGreater(len(t["code_signing"]), 0)
        self.assertIn("testrmm.exe", t["code_signing"][0]["search_names"])

    def test_stable_slug_id(self):
        t1 = self._parse(WINDOWS_FIXTURE, "testrmm.yaml")
        t2 = self._parse(WINDOWS_FIXTURE, "testrmm.yaml")
        self.assertEqual(t1["tool_id"], t2["tool_id"])
        self.assertTrue(t1["tool_id"].startswith("lolrmm:"))

    def test_generated_packages_exist(self):
        if not PKG_DIR.exists():
            self.skipTest("Package directory not found — run converter first")
        packages = list(PKG_DIR.glob("*.json"))
        self.assertGreater(len(packages), 0)
        total = 0
        for p in packages:
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertTrue(data["package_id"].startswith("lolrmm-"))
            scripts = data.get("scripts", [])
            total += len(scripts)
            for s in scripts:
                self.assertTrue(s["name"].startswith("LOLRMM - "), f"Bad name: {s['name']}")
                self.assertEqual(s["operational_risk"], "observe", f"Risk not observe: {s['id']}")
                self.assertIn(s["executor"], ("bash", "manual"))
                meta = s.get("source_metadata", {})
                self.assertEqual(meta.get("provider"), "lolrmm")
                self.assertFalse(meta.get("source_modified"))
                # No active downloads of RMM installers in command
                cmd = s.get("command", "")
                for bad in ["Invoke-WebRequest", "wget http", "curl -O http", "pip install"]:
                    self.assertNotIn(bad, cmd, f"Possible download in {s['id']}")
        print(f"\n  Total LOLRMM scripts: {total}")
        self.assertEqual(total, 320)

    def test_no_duplicate_ids(self):
        if not PKG_DIR.exists():
            self.skipTest("Package dir not found")
        ids = []
        for p in PKG_DIR.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            ids.extend(s["id"] for s in data.get("scripts", []))
        self.assertEqual(len(ids), len(set(ids)), "Duplicate script IDs")

    def test_source_inventory_complete(self):
        inv_path = LOT_DIR / "source-inventory.json"
        if not inv_path.exists():
            self.skipTest("source-inventory.json not found")
        inv = json.loads(inv_path.read_text(encoding="utf-8"))
        self.assertEqual(len(inv), 320)

    def test_catalog_has_lolrmm_entries(self):
        cat_path = TOOLS_DIR.parent.parent.parent / "morgana/excalibur/catalog.json"
        if not cat_path.exists():
            self.skipTest("catalog.json not found")
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        lolrmm_packs = [p for p in cat.get("packs", []) if "lolrmm" in p.get("package_id","")]
        self.assertGreater(len(lolrmm_packs), 0)


if __name__ == "__main__":
    unittest.main()
