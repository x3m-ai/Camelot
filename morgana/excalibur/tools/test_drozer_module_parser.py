#!/usr/bin/env python3
"""Drozer parser tests. No module source is executed."""
from __future__ import annotations

import os
import sys
import unittest
from collections import Counter
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from drozer_module_parser import (  # noqa: E402
    DROZER_COMMIT,
    DROZER_MODULES_COMMIT,
    enumerate_core_modules,
    enumerate_external_modules,
    get_source_commit,
)

DROZER_SOURCE = Path(os.environ.get("DROZER_SOURCE", r"C:\ProgramData\Morgana\temp\drozer-source"))
DROZER_MODULES = Path(os.environ.get("DROZER_MODULES_SOURCE", r"C:\ProgramData\Morgana\temp\drozer-modules-source"))


class DrozerModuleParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (DROZER_SOURCE / "src" / "drozer" / "modules").is_dir():
            raise unittest.SkipTest(f"drozer source not found: {DROZER_SOURCE}")
        cls.core, cls.core_err = enumerate_core_modules(DROZER_SOURCE)
        cls.ext, cls.ext_err = enumerate_external_modules(DROZER_MODULES)

    def test_pinned_source_and_complete_parse(self) -> None:
        self.assertEqual(get_source_commit(DROZER_SOURCE), DROZER_COMMIT)
        self.assertEqual(self.core_err, [])
        self.assertGreaterEqual(len(self.core), 85)
        self.assertEqual(
            Counter(r.get("status") for r in self.core),
            {"EXECUTABLE": 65, "FRAMEWORK_INTERNAL": 20, "MANUAL": 3},
        )

    def test_external_modules_complete(self) -> None:
        self.assertEqual(get_source_commit(DROZER_MODULES), DROZER_MODULES_COMMIT)
        self.assertEqual(self.ext_err, [])
        self.assertEqual(Counter(r.get("status") for r in self.ext), {"EXECUTABLE": 14})

    def test_ids_paths_and_metadata_stable(self) -> None:
        executable = [r for r in self.core + self.ext if r.get("status") == "EXECUTABLE"]
        self.assertTrue(all(r.get("fqmn") for r in executable))
        self.assertTrue(all(r.get("source_path") and not Path(r["source_path"]).is_absolute() for r in executable))
        self.assertEqual(len({r["script_id"] for r in executable}), len(executable))
        self.assertTrue(all(r.get("source_sha256") for r in executable))
        self.assertTrue(all(r.get("license") for r in executable))
        self.assertTrue(all(r.get("author") for r in executable))

    def test_fqmn_matches_namespace_convention(self) -> None:
        info = [r for r in self.core if r.get("fqmn") == "app.package.info"]
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["namespace"], "app.package")
        self.assertEqual(info[0]["class_name"], "Info")
        self.assertEqual(info[0]["license"], "BSD (3 clause)")

    def test_arguments_preserve_flags_types_defaults(self) -> None:
        info = [r for r in self.core if r.get("fqmn") == "app.package.info"][0]
        opts = {o["name"]: o for o in info["options"]}
        self.assertIn("package", opts)
        self.assertEqual(opts["package"]["flag"], "--package")
        self.assertIn("show-intent-filters", opts)
        self.assertEqual(opts["show-intent-filters"]["action"], "store_true")
        # positional arg in attacksurface
        asurface = [r for r in self.core if r.get("fqmn") == "app.package.attacksurface"][0]
        positional = [o for o in asurface["options"] if o.get("positional")]
        self.assertTrue(positional)
        self.assertIsNone(positional[0]["flag"])

    def test_payload_modules_are_manual(self) -> None:
        manual = [r for r in self.core if r.get("status") == "MANUAL"]
        self.assertTrue(all(r.get("module_type") == "payload" for r in manual))


if __name__ == "__main__":
    unittest.main()
