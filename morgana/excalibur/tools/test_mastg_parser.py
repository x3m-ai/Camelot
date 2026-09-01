#!/usr/bin/env python3
"""Unit tests for mastg_parser.py — front matter, tests, demos, playground."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from mastg_parser import (
    body_after_fm,
    parse_front_matter,
    playground_inventory,
    playground_meta,
)

MASTG_SOURCE = Path(r"C:\ProgramData\Morgana\temp\mastg")
PLAYGROUND_SOURCE = Path(r"C:\ProgramData\Morgana\temp\MASTG-Hacking-Playground")


class TestFrontMatter(unittest.TestCase):
    def test_inline_list(self):
        fm = parse_front_matter("---\nprofiles: [L1, L2]\nid: MASTG-TEST-0001\n---\nBody")
        self.assertEqual(fm["profiles"], ["L1", "L2"])
        self.assertEqual(fm["id"], "MASTG-TEST-0001")

    def test_block_list(self):
        fm = parse_front_matter("---\nmasvs_v2_id:\n- MASVS-CODE-4\n- MASVS-CODE-5\n---\n")
        self.assertEqual(fm["masvs_v2_id"], ["MASVS-CODE-4", "MASVS-CODE-5"])

    def test_scalar_and_comment(self):
        fm = parse_front_matter("---\nplatform: android # comment\nstatus: deprecated\n---\n")
        self.assertEqual(fm["platform"], "android")
        self.assertEqual(fm["status"], "deprecated")

    def test_body_after_fm(self):
        text = "---\nplatform: android\n---\n## Overview\nHello"
        self.assertEqual(body_after_fm(text), "## Overview\nHello")


@unittest.skipUnless(MASTG_SOURCE.is_dir(), "MASTG source not present")
class TestMastgSource(unittest.TestCase):
    def test_test_front_matter(self):
        from mastg_parser import mastg_tests
        tests = mastg_tests(MASTG_SOURCE)
        self.assertEqual(len(tests), 292)
        ids = {t["canonical_id"] for t in tests}
        self.assertIn("MASTG-TEST-0002", ids)     # deprecated v1
        self.assertIn("MASTG-TEST-0326", ids)     # current v2
        # deprecated test preserves covered_by
        dep = next(t for t in tests if t["canonical_id"] == "MASTG-TEST-0002")
        self.assertEqual(dep["status"], "deprecated")
        self.assertIn("MASTG-TEST-0338", dep["covered_by"])
        self.assertIn("MASVS-CODE-4", dep["masvs_v2_id"])
        # current v2 test preserves id + weakness + type
        cur = next(t for t in tests if t["canonical_id"] == "MASTG-TEST-0326")
        self.assertEqual(cur["weakness"], "MASWE-0021")
        self.assertIn("static", cur["type"])
        # platform: network tests normalized to android/ios directory platform
        net = next(t for t in tests if t["canonical_id"] == "MASTG-TEST-0236")
        self.assertEqual(net["platform"], "android")

    def test_demo_discovery(self):
        from mastg_parser import mastg_demos
        demos = mastg_demos(MASTG_SOURCE)
        self.assertEqual(len(demos), 157)
        ids = {d["canonical_id"] for d in demos}
        self.assertIn("MASTG-DEMO-0089", ids)
        d = next(x for x in demos if x["canonical_id"] == "MASTG-DEMO-0089")
        self.assertEqual(d["linked_test"], "MASTG-TEST-0326")
        self.assertEqual(d["platform"], "android")

    def test_reference_discovery(self):
        from mastg_parser import mastg_references
        self.assertEqual(len(mastg_references(MASTG_SOURCE, "knowledge")), 141)
        self.assertEqual(len(mastg_references(MASTG_SOURCE, "techniques")), 168)
        self.assertEqual(len(mastg_references(MASTG_SOURCE, "tools")), 136)
        self.assertEqual(len(mastg_references(MASTG_SOURCE, "apps")), 30)
        self.assertEqual(len(mastg_references(MASTG_SOURCE, "best-practices")), 75)


@unittest.skipUnless(PLAYGROUND_SOURCE.is_dir(), "Playground source not present")
class TestPlaygroundSource(unittest.TestCase):
    def test_inventory(self):
        inv = playground_inventory(PLAYGROUND_SOURCE)
        apps = [p for p in inv if p["type"] == "HACKING_PLAYGROUND_APP"]
        backends = [p for p in inv if p["type"] == "HACKING_PLAYGROUND_BACKEND"]
        self.assertEqual(len(apps), 3)
        self.assertEqual(len(backends), 1)
        platforms = {a["platform"] for a in apps}
        self.assertEqual(platforms, {"android", "ios"})
        kotlin = next(a for a in apps if "Kotlin" in a["name"])
        self.assertEqual(kotlin["package_id"], "owasp.mastgkotlin")
        self.assertEqual(kotlin["backend_dependency"], "rails-api-original")
        for a in apps:
            self.assertEqual(a["license"], "GPL-3.0")

    def test_meta(self):
        meta = playground_meta(PLAYGROUND_SOURCE)
        self.assertEqual(meta["license"], "GPL-3.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
