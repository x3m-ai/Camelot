#!/usr/bin/env python3
"""Focused tests for FuzzySully converter — no fuzz profiles are executed."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
from convert_fuzzysully import (
    build_combinations, build_packages, _sha256_file, _sha256_text, OPCUA_TAG_CATEGORIES
)

MAPPING_PATH = TOOLS_DIR / "fuzzysully_mapping_overrides.json"


class FuzzySullyConverterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
        # Build a fake contract matching the known upstream
        self.contract = {
            "modes": ["server", "gds", "reverse"],
            "functions_by_mode": {
                "server": self.mapping["server_functions"],
                "gds": self.mapping["gds_functions"],
                "reverse": self.mapping["reverse_functions"],
            },
            "server_function_count": len(self.mapping["server_functions"]),
            "gds_function_count": len(self.mapping["gds_functions"]),
            "reverse_function_count": len(self.mapping["reverse_functions"]),
            "total_functions": (
                len(self.mapping["server_functions"]) +
                len(self.mapping["gds_functions"]) +
                len(self.mapping["reverse_functions"])
            ),
            "drift_warnings": [],
        }

    def test_all_valid_profiles_generated(self) -> None:
        valid, skipped = build_combinations(self.contract, self.mapping)
        # server/None = 20
        # server/Basic256Sha256-Sign = 17 (3 excluded)
        # server/Basic256Sha256-SignEncrypt = 17
        # gds/Sign = 9
        # gds/SignEncrypt = 9
        # reverse/None = 1
        self.assertEqual(len([p for p in valid if p["mode"] == "server" and p["policy"] == "None"]), 20)
        self.assertEqual(len([p for p in valid if p["mode"] == "server" and p["policy"] == "Basic256Sha256" and not p["encrypt"]]), 17)
        self.assertEqual(len([p for p in valid if p["mode"] == "server" and p["policy"] == "Basic256Sha256" and p["encrypt"]]), 17)
        self.assertEqual(len([p for p in valid if p["mode"] == "gds"]), 18)
        self.assertEqual(len([p for p in valid if p["mode"] == "reverse"]), 1)
        # 6 skipped (3 functions × 2 encrypt variants for Basic256Sha256)
        self.assertEqual(len(skipped), 6)
        # Total
        self.assertEqual(len(valid), 73)

    def test_excluded_functions_not_in_basic256_profiles(self) -> None:
        valid, _ = build_combinations(self.contract, self.mapping)
        basic_profiles = [p for p in valid if p["mode"] == "server" and p["policy"] == "Basic256Sha256"]
        excluded = set(self.mapping["server_basic_excluded_functions"])
        for p in basic_profiles:
            self.assertNotIn(p["function"], excluded,
                             f"Excluded function {p['function']!r} found in Basic256Sha256 profile")

    def test_gds_has_no_none_policy(self) -> None:
        valid, _ = build_combinations(self.contract, self.mapping)
        gds_none = [p for p in valid if p["mode"] == "gds" and p["policy"] == "None"]
        self.assertEqual(len(gds_none), 0, "GDS profiles with None policy should not exist")

    def test_reverse_has_only_none_policy(self) -> None:
        valid, _ = build_combinations(self.contract, self.mapping)
        reverse_profiles = [p for p in valid if p["mode"] == "reverse"]
        for p in reverse_profiles:
            self.assertEqual(p["policy"], "None", f"Reverse profile should be None-only: {p['script_id']}")

    def test_stable_script_ids(self) -> None:
        valid1, _ = build_combinations(self.contract, self.mapping)
        valid2, _ = build_combinations(self.contract, self.mapping)
        ids1 = {p["script_id"] for p in valid1}
        ids2 = {p["script_id"] for p in valid2}
        self.assertEqual(ids1, ids2, "Script IDs must be stable across runs")

    def test_all_script_ids_unique(self) -> None:
        valid, _ = build_combinations(self.contract, self.mapping)
        ids = [p["script_id"] for p in valid]
        self.assertEqual(len(ids), len(set(ids)), "All script IDs must be unique")

    def test_fuzzysully_name_prefix_on_all_scripts(self) -> None:
        valid, _ = build_combinations(self.contract, self.mapping)
        for p in valid:
            self.assertTrue(p["name"].startswith("FUZZYSULLY"), f"Bad prefix: {p['name']}")

    def test_packages_have_correct_structure(self) -> None:
        valid, skipped = build_combinations(self.contract, self.mapping)
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            runner_path = Path(f.name)
            runner_path.write_bytes(b"# fixture runner")
        try:
            packages = build_packages(
                valid, skipped, self.mapping,
                "50a0631178331d2cc39b6ed554b9b68050580f92",
                runner_path,
                hashlib.sha256(runner_path.read_bytes()).hexdigest(),
                runner_path.stat().st_size,
            )
        finally:
            runner_path.unlink(missing_ok=True)

        self.assertEqual(len(packages), 4)
        for pkg, key in packages:
            self.assertIn("scripts", pkg)
            self.assertIn("assets", pkg)
            self.assertIn("tag_categories", pkg)
            for s in pkg["scripts"]:
                self.assertIn("id", s)
                self.assertIn("name", s)
                self.assertIn("command", s)
                self.assertIn("source_metadata", s)
                # MORGANA_RESULT_METADATA= is emitted by runner to stdout; bash command invokes runner
                self.assertIn('python3 "$runner"', s["command"])
                self.assertIn("opcua_target_host", s["command"])
                meta = s["source_metadata"]
                self.assertEqual(meta["protocol"], "opcua")
                self.assertEqual(meta["mitre_domain"], "ics-attack")
                self.assertFalse(meta["source_modified"])
            # No sensitive data in scripts
            pkg_str = json.dumps(pkg)
            self.assertNotIn("BEGIN PRIVATE KEY", pkg_str)
            self.assertNotIn("BEGIN CERTIFICATE", pkg_str)

    def test_runner_invoked_in_all_commands(self) -> None:
        """MORGANA_RESULT_METADATA= is emitted by the Python runner; bash command must invoke the runner."""
        valid, skipped = build_combinations(self.contract, self.mapping)
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            runner_path = Path(f.name)
            runner_path.write_bytes(b"# fixture runner")
        try:
            packages = build_packages(
                valid, skipped, self.mapping,
                "50a0631178331d2cc39b6ed554b9b68050580f92",
                runner_path,
                hashlib.sha256(runner_path.read_bytes()).hexdigest(),
                runner_path.stat().st_size,
            )
        finally:
            runner_path.unlink(missing_ok=True)
        for pkg, _ in packages:
            for s in pkg["scripts"]:
                cmd = s["command"]
                self.assertTrue(
                    'python3 "$runner"' in cmd or 'python3' in cmd,
                    f"Missing python3 runner invocation in {s['id']}"
                )

    def test_cert_required_tags_for_basic256sha256(self) -> None:
        valid, skipped = build_combinations(self.contract, self.mapping)
        for p in valid:
            if p["policy"] == "Basic256Sha256":
                # Script required_tags should mention cert paths (handled in _required_tags_for_profile)
                # verified via script building
                from convert_fuzzysully import _required_tags_for_profile
                tags = _required_tags_for_profile(p)
                self.assertIn("opcua_client_cert_path", tags, f"{p['script_id']} missing cert tag")
                self.assertIn("opcua_private_key_path", tags, f"{p['script_id']} missing key tag")

    def test_no_cert_required_for_none_policy(self) -> None:
        valid, _ = build_combinations(self.contract, self.mapping)
        from convert_fuzzysully import _required_tags_for_profile
        for p in valid:
            if p["policy"] == "None":
                tags = _required_tags_for_profile(p)
                self.assertNotIn("opcua_client_cert_path", tags,
                                 f"None-policy script {p['script_id']} should not require cert")

    def test_risk_values_valid(self) -> None:
        valid, _ = build_combinations(self.contract, self.mapping)
        valid_risks = {"observe", "interact", "modify", "disrupt"}
        for p in valid:
            self.assertIn(p["risk"], valid_risks, f"Invalid risk {p['risk']!r} for {p['script_id']}")


if __name__ == "__main__":
    unittest.main()
