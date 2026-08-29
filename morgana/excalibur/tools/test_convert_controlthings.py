#!/usr/bin/env python3
"""Focused unit tests for ControlThings Suite converter. No devices are contacted."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CT_DIR = TOOLS_DIR.parent / "ot" / "controlthings"
PKG_DIR = CT_DIR / "packages"

sys.path.insert(0, str(TOOLS_DIR))
from convert_controlthings import build_all_scripts, build_packages, _MODBUS_OPS, _SERIAL_OPS, _MANUAL_TOOLS


class ControlThingsConverterTests(unittest.TestCase):

    def setUp(self):
        self.scripts = build_all_scripts()
        self.packages = build_packages(self.scripts)

    def test_script_count(self):
        self.assertEqual(len(self.scripts), 33, f"Expected 33 scripts, got {len(self.scripts)}")

    def test_package_count(self):
        self.assertEqual(len(self.packages), 5)

    def test_all_script_ids_unique(self):
        ids = [s["id"] for s in self.scripts]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate script IDs")

    def test_all_names_start_controlthings(self):
        for s in self.scripts:
            self.assertTrue(s["name"].startswith("CONTROLTHINGS - "), f"Bad prefix: {s['name']}")

    def test_risk_values_valid(self):
        valid = {"observe", "interact", "modify", "disrupt"}
        for s in self.scripts:
            self.assertIn(s["operational_risk"], valid)

    def test_modbus_read_are_interact(self):
        modbus_reads = [s for s in self.scripts if "ctmodbus" in s["id"] and "write" not in s["id"]]
        for s in modbus_reads:
            self.assertEqual(s["operational_risk"], "interact", f"Read should be interact: {s['id']}")

    def test_modbus_write_are_modify(self):
        modbus_writes = [s for s in self.scripts if "ctmodbus" in s["id"] and "write" in s["id"]]
        self.assertGreater(len(modbus_writes), 0, "No write scripts found")
        for s in modbus_writes:
            self.assertEqual(s["operational_risk"], "modify", f"Write should be modify: {s['id']}")

    def test_manual_tools_use_manual_executor(self):
        manual = [s for s in self.scripts if any(m in s["id"] for m in ("ctspi", "cti2c", "ctvelocio"))]
        for s in manual:
            self.assertEqual(s["executor"], "manual", f"Should be manual: {s['id']}")

    def test_no_hardcoded_ips(self):
        for s in self.scripts:
            cmd = s.get("command", "")
            self.assertNotIn("192.168.", cmd, f"Hardcoded IP in {s['id']}")
            self.assertNotIn("10.0.0.", cmd, f"Hardcoded IP in {s['id']}")

    def test_no_installer_downloads(self):
        for s in self.scripts:
            cmd = s.get("command", "")
            self.assertNotIn("pip install", cmd, f"pip install in {s['id']}")
            self.assertNotIn("wget http", cmd, f"wget in {s['id']}")

    def test_source_metadata_present(self):
        for s in self.scripts:
            meta = s.get("source_metadata", {})
            self.assertEqual(meta.get("provider"), "controlthings")
            self.assertFalse(meta.get("source_modified"))
            self.assertIn(meta.get("component"), ("ctmodbus","ctserial","ctspi","cti2c","ctvelocio"))

    def test_packages_have_correct_fields(self):
        if not PKG_DIR.exists():
            self.skipTest("Package dir not found")
        for p in PKG_DIR.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertTrue(data["package_id"].startswith("controlthings-"))
            self.assertEqual(data["provider"], "controlthings")
            self.assertGreater(len(data.get("scripts", [])), 0)

    def test_catalog_has_controlthings(self):
        cat_path = TOOLS_DIR.parent.parent.parent / "morgana/excalibur/catalog.json"
        if not cat_path.exists():
            self.skipTest("catalog.json not found")
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        ct_packs = [p for p in cat.get("packs", []) if "controlthings" in p.get("package_id", "")]
        self.assertEqual(len(ct_packs), 5)


if __name__ == "__main__":
    unittest.main()
