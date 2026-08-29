#!/usr/bin/env python3
"""Focused unit tests for Elastic Cortado converter. No RTAs are executed."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
DETECTION_DIR = TOOLS_DIR.parent / "detection" / "cortado"
PKG_DIR = DETECTION_DIR / "packages"

sys.path.insert(0, str(TOOLS_DIR))
from cortado_ast import parse_rta_file, CORTADO_WHEEL_SHA256, CORTADO_COMMIT
from cortado_risk import get_tactics, get_primary_tactic, get_risk

# Fixtures
CODE_RTA_SOURCE = '''
# Copyright Elasticsearch B.V.
# Name: Test Code RTA
# Description: Creates a test network connection.
from . import OSType, RuleMetadata, register_code_rta
@register_code_rta(
    id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    name="test_code_rta",
    platforms=[OSType.WINDOWS, OSType.LINUX],
    endpoint_rules=[RuleMetadata(id="11111111-2222-3333-4444-555555555555", name="Test Endpoint Rule")],
    siem_rules=[RuleMetadata(id="66666666-7777-8888-9999-aaaaaaaaaaaa", name="Test SIEM Rule")],
    techniques=["T1059", "T1059.001"],
)
def main():
    """Execute test RTA."""
    pass
'''

HASH_RTA_SOURCE = '''
from . import OSType, RuleMetadata, register_hash_rta
register_hash_rta(
    id="bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    name="test_hash_rta",
    platforms=[OSType.WINDOWS],
    endpoint_rules=[RuleMetadata(id="77777777-8888-9999-aaaa-bbbbbbbbbbbb", name="Hash Rule")],
    techniques=["T1562"],
    sample_hash="deadbeef1234567890abcdef1234567890abcdef1234567890abcdef12345678",
)
'''

ANCILLARY_SOURCE = '''
from . import OSType, RuleMetadata, register_code_rta
SHIM_FILE = "test.sdb"
@register_code_rta(
    id="cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa",
    name="test_ancillary_rta",
    platforms=[OSType.WINDOWS],
    endpoint_rules=[],
    siem_rules=[],
    techniques=["T1546"],
    ancillary_files=[SHIM_FILE],
)
def main():
    pass
'''


class CortadoConverterTests(unittest.TestCase):

    def _parse(self, source: str, name: str = "test.py") -> list[dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir) / name
            f.write_text(source, encoding="utf-8")
            return parse_rta_file(f)

    def test_code_rta_parsed(self):
        rtas = self._parse(CODE_RTA_SOURCE, "test_code_rta.py")
        self.assertEqual(len(rtas), 1)
        r = rtas[0]
        self.assertEqual(r["rta_type"], "code")
        self.assertEqual(r["id"], "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        self.assertEqual(r["name"], "test_code_rta")
        self.assertIn("windows", r["platforms"])
        self.assertIn("linux", r["platforms"])
        self.assertEqual(len(r["endpoint_rules"]), 1)
        self.assertEqual(r["endpoint_rules"][0]["name"], "Test Endpoint Rule")
        self.assertEqual(len(r["siem_rules"]), 1)
        self.assertIn("T1059", r["techniques"])
        self.assertEqual(r["description"], "Creates a test network connection.")

    def test_hash_rta_parsed(self):
        rtas = self._parse(HASH_RTA_SOURCE, "test_hash_rta.py")
        self.assertEqual(len(rtas), 1)
        r = rtas[0]
        self.assertEqual(r["rta_type"], "hash")
        self.assertEqual(r["id"], "bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
        self.assertEqual(r["name"], "test_hash_rta")
        self.assertEqual(r["sample_hash"], "deadbeef1234567890abcdef1234567890abcdef1234567890abcdef12345678")
        self.assertIn("windows", r["platforms"])

    def test_ancillary_files_extracted(self):
        rtas = self._parse(ANCILLARY_SOURCE, "test_ancillary.py")
        self.assertEqual(len(rtas), 1)
        self.assertGreater(len(rtas[0]["ancillary_files"]), 0)

    def test_risk_mapping(self):
        self.assertEqual(get_risk("impact"), "disrupt")
        self.assertEqual(get_risk("defense-evasion"), "modify")
        self.assertEqual(get_risk("discovery"), "interact")
        self.assertEqual(get_risk("execution"), "modify")

    def test_tactic_from_techniques(self):
        self.assertIn("execution", get_tactics(["T1059"]))
        self.assertIn("defense-evasion", get_tactics(["T1562.001"]))

    def test_primary_tactic(self):
        self.assertEqual(get_primary_tactic(["T1059"]), "execution")
        self.assertEqual(get_primary_tactic([]), "unmapped")

    def test_generated_packages_exist(self):
        if not PKG_DIR.exists():
            self.skipTest("Package directory not found — run converter first")
        packages = list(PKG_DIR.glob("*.json"))
        self.assertGreater(len(packages), 0)
        code_total, hash_total = 0, 0
        for pkg_path in packages:
            data = json.loads(pkg_path.read_text(encoding="utf-8"))
            scripts = data.get("scripts", [])
            self.assertIn("package_id", data)
            self.assertTrue(data["package_id"].startswith("cortado-"))
            for s in scripts:
                self.assertTrue(s["name"].startswith("CORTADO - "), f"Bad prefix: {s['name']}")
                rtype = s.get("source_metadata", {}).get("rta_type", "")
                if rtype == "code":
                    code_total += 1
                    self.assertEqual(s["executor"], "bash")
                    self.assertIn("elastic_cortado_wheel", s.get("required_assets", []))
                    self.assertNotIn("BEGIN PRIVATE KEY", s.get("command", ""))
                elif rtype == "hash":
                    hash_total += 1
                    self.assertEqual(s["executor"], "manual")
                    self.assertIn("sample_hash", s.get("source_metadata", {}))
        print(f"\n  CodeRTA scripts: {code_total}, HashRTA scripts: {hash_total}")
        self.assertGreater(code_total, 0)
        self.assertGreater(hash_total, 0)

    def test_no_duplicate_script_ids(self):
        if not PKG_DIR.exists():
            self.skipTest("Package directory not found")
        all_ids = []
        for p in PKG_DIR.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            all_ids.extend(s["id"] for s in data.get("scripts", []))
        self.assertEqual(len(all_ids), len(set(all_ids)), "Duplicate script IDs")

    def test_sample_backed_package_exists(self):
        if not PKG_DIR.exists():
            self.skipTest("Package directory not found")
        sample_pkg = PKG_DIR / "cortado-sample-backed-v1.json"
        self.assertTrue(sample_pkg.exists(), "Sample-backed package missing")
        data = json.loads(sample_pkg.read_text(encoding="utf-8"))
        scripts = data.get("scripts", [])
        for s in scripts:
            self.assertEqual(s["executor"], "manual")
            self.assertIsNotNone(s["source_metadata"].get("sample_hash"))

    def test_wheel_metadata(self):
        bm_path = DETECTION_DIR / "build-manifest.json"
        if not bm_path.exists():
            self.skipTest("build-manifest.json not found")
        bm = json.loads(bm_path.read_text(encoding="utf-8"))
        self.assertEqual(bm["wheel_sha256"], CORTADO_WHEEL_SHA256)
        self.assertEqual(bm["source_commit"], CORTADO_COMMIT)
        self.assertFalse(bm["manual_cortado_install_required"])
        self.assertFalse(bm["poetry_required_on_agent"])
        self.assertFalse(bm["source_modified"])

    def test_catalog_has_cortado_entries(self):
        cat_path = TOOLS_DIR.parent.parent.parent / "morgana/excalibur/catalog.json"
        if not cat_path.exists():
            self.skipTest("catalog.json not found")
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        cortado_packs = [p for p in cat.get("packs", []) if "cortado" in p.get("package_id", "")]
        self.assertGreater(len(cortado_packs), 0)


if __name__ == "__main__":
    unittest.main()
