#!/usr/bin/env python3
"""Focused unit tests for Stratus Red Team converter. No cloud techniques are detonated."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
CLOUD_DIR = TOOLS_DIR.parent / "cloud" / "stratus"
sys.path.insert(0, str(TOOLS_DIR))

from stratus_source import parse_technique, PLATFORM_META, TACTIC_RISK

# Fixture Go source for a representative technique
FIXTURE_MAIN_GO = '''package aws
import (
    "github.com/datadog/stratus-red-team/v2/pkg/stratus"
    "github.com/datadog/stratus-red-team/v2/pkg/stratus/mitreattack"
)
func init() {
    stratus.GetRegistry().RegisterAttackTechnique(&stratus.AttackTechnique{
        ID:           "aws.persistence.iam-backdoor-role",
        FriendlyName: "Backdoor an IAM Role",
        Description: `Establishes persistence by backdooring an existing IAM role.`,
        Detection: `Using CloudTrail's UpdateAssumeRolePolicy event`,
        Platform:           stratus.AWS,
        IsIdempotent:       true,
        MitreAttackTactics: []mitreattack.Tactic{mitreattack.Persistence},
    })
}
'''

FIXTURE_MAIN_GO_MULTI_TACTIC = '''package aws
import (
    "github.com/datadog/stratus-red-team/v2/pkg/stratus"
    "github.com/datadog/stratus-red-team/v2/pkg/stratus/mitreattack"
)
func init() {
    stratus.GetRegistry().RegisterAttackTechnique(&stratus.AttackTechnique{
        ID:           "aws.execution.ec2-user-data",
        FriendlyName: "Execute Commands on EC2 Instance via User Data",
        Description: `Runs commands on EC2 via user-data.`,
        Platform:           stratus.AWS,
        IsIdempotent:       false,
        MitreAttackTactics: []mitreattack.Tactic{mitreattack.Execution, mitreattack.Persistence},
        Revert: revert,
    })
}
func revert(params map[string]string, providers stratus.CloudProviders) error { return nil }
'''


class StratusConverterTests(unittest.TestCase):

    def _parse_from_fixture(self, content: str, plat: str, tactic: str) -> dict:
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            go_file = Path(tmpdir) / "main.go"
            go_file.write_text(content, encoding="utf-8")
            return parse_technique(go_file, plat, tactic)

    def test_basic_technique_parsed(self):
        t = self._parse_from_fixture(FIXTURE_MAIN_GO, "aws", "persistence")
        self.assertEqual(t["technique_id"], "aws.persistence.iam-backdoor-role")
        self.assertEqual(t["friendly_name"], "Backdoor an IAM Role")
        self.assertEqual(t["platform"], "aws")
        self.assertTrue(t["is_idempotent"])
        self.assertIn("Persistence", t["mitre_tactics"])
        self.assertEqual(t["script_id"], "stratus:aws.persistence.iam-backdoor-role")
        self.assertTrue(t["script_name"].startswith("STRATUS - AWS - "))

    def test_multi_tactic_preserved(self):
        t = self._parse_from_fixture(FIXTURE_MAIN_GO_MULTI_TACTIC, "aws", "execution")
        self.assertIn("Execution", t["mitre_tactics"])
        self.assertIn("Persistence", t["mitre_tactics"])

    def test_no_terraform_flag(self):
        t = self._parse_from_fixture(FIXTURE_MAIN_GO, "aws", "persistence")
        self.assertFalse(t["has_terraform"])  # no main.tf in tmpdir

    def test_risk_mapping(self):
        self.assertEqual(TACTIC_RISK["impact"], "disrupt")
        self.assertEqual(TACTIC_RISK["persistence"], "modify")
        self.assertEqual(TACTIC_RISK["discovery"], "interact")

    def test_platform_meta_all_present(self):
        for plat in ("aws", "azure", "entra-id", "gcp", "k8s", "eks"):
            self.assertIn(plat, PLATFORM_META)
            self.assertIn("target_environments", PLATFORM_META[plat])

    def test_stable_script_id(self):
        t1 = self._parse_from_fixture(FIXTURE_MAIN_GO, "aws", "persistence")
        t2 = self._parse_from_fixture(FIXTURE_MAIN_GO, "aws", "persistence")
        self.assertEqual(t1["script_id"], t2["script_id"])

    def test_generated_packages_exist(self):
        """Verify the generated package JSON files exist and have correct structure."""
        if not CLOUD_DIR.exists():
            self.skipTest("Cloud stratus output directory not found — run converter first")
        packages = list(CLOUD_DIR.rglob("*.json"))
        packages = [p for p in packages if p.name != "source-inventory.json"
                    and p.name != "conversion-report.json"
                    and p.name != "release-manifest.json"]
        self.assertGreater(len(packages), 0, "No package JSON files found")

        for pkg_path in packages:
            with self.subTest(pkg=pkg_path.name):
                data = json.loads(pkg_path.read_text(encoding="utf-8"))
                self.assertIn("scripts", data)
                self.assertIn("package_id", data)
                scripts = data["scripts"]
                self.assertGreater(len(scripts), 0)
                for s in scripts:
                    self.assertIn("id", s)
                    self.assertIn("name", s)
                    self.assertTrue(s["name"].startswith("STRATUS - "), f"Bad prefix: {s['name']}")
                    self.assertIn("command", s)
                    self.assertIn("cleanup_command", s)
                    self.assertIn("MORGANA_TEST_ID", s["command"])
                    self.assertIn("STRATUS_RED_TEAM_CORRELATION_ID", s["command"])
                    self.assertIn("stratus_linux_amd64", s.get("required_assets", []))
                    meta = s.get("source_metadata", {})
                    # No hardcoded static secrets (keys/certs) in commands
                    cmd = s["command"]
                    for secret_kw in ["AWS_SECRET_ACCESS_KEY=AKIA", "BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY"]:
                        self.assertNotIn(secret_kw, cmd, f"Hardcoded credential in command: {secret_kw}")

    def test_no_duplicate_script_ids(self):
        if not CLOUD_DIR.exists():
            self.skipTest("Cloud stratus output directory not found")
        all_ids = []
        for pkg_path in CLOUD_DIR.rglob("*.json"):
            if pkg_path.name in ("source-inventory.json", "conversion-report.json", "release-manifest.json"):
                continue
            data = json.loads(pkg_path.read_text(encoding="utf-8"))
            all_ids.extend(s["id"] for s in data.get("scripts", []))
        self.assertEqual(len(all_ids), len(set(all_ids)), "Duplicate script IDs found")

    def test_source_inventory_complete(self):
        inv_path = CLOUD_DIR / "source-inventory.json"
        if not inv_path.exists():
            self.skipTest("source-inventory.json not found")
        inv = json.loads(inv_path.read_text(encoding="utf-8"))
        self.assertGreater(len(inv), 0)
        for entry in inv:
            self.assertIn("technique_id", entry)
            self.assertIn("platform", entry)
            self.assertIn("mitre_tactics", entry)

    def test_catalog_has_stratus_entries(self):
        cat_path = TOOLS_DIR.parent.parent.parent / "morgana/excalibur/catalog.json"
        if not cat_path.exists():
            self.skipTest("catalog.json not found")
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        stratus_packs = [p for p in cat.get("packs", []) if "stratus" in p.get("package_id", "")]
        self.assertGreater(len(stratus_packs), 0, "No Stratus packs in catalog")


if __name__ == "__main__":
    unittest.main()
