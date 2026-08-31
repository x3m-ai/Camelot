#!/usr/bin/env python3
"""Compact MEDUSA parser tests. No module source is executed."""

from __future__ import annotations

import os
import sys
import unittest
from collections import Counter
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from medusa_module_parser import (
    MEDUSA_COMMIT,
    enumerate_modules,
    enumerate_snippets,
    get_source_commit,
    parse_module,
)

MEDUSA_SOURCE = Path(
    os.environ.get("MEDUSA_SOURCE", r"C:\ProgramData\Morgana\temp\medusa-source")
)


class MedusaModuleParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (MEDUSA_SOURCE / "modules").is_dir():
            raise unittest.SkipTest(f"MEDUSA source not found: {MEDUSA_SOURCE}")
        cls.modules, cls.errors = enumerate_modules(MEDUSA_SOURCE)
        cls.snippets = enumerate_snippets(MEDUSA_SOURCE)

    def test_pinned_source_and_complete_parse(self) -> None:
        self.assertEqual(get_source_commit(MEDUSA_SOURCE), MEDUSA_COMMIT)
        self.assertEqual(self.errors, [])
        self.assertEqual(len(self.modules), 137)
        self.assertEqual(len(self.snippets), 14)
        self.assertEqual(
            Counter(module["platform"] for module in self.modules),
            {"android": 125, "ios": 12},
        )

    def test_paths_categories_and_ids_are_stable(self) -> None:
        records = self.modules + self.snippets
        self.assertTrue(all(record["source_path"] for record in records))
        self.assertTrue(all(not Path(record["source_path"]).is_absolute() for record in records))
        self.assertEqual(len({record["script_id"] for record in records}), len(records))
        self.assertTrue(all(module["parse_mode"] == "standard" for module in self.modules))

        ios_module = parse_module(
            MEDUSA_SOURCE / "modules" / "ios" / "ssl_pinning" / "ssl_unpinning_ios_13.imed",
            "ios",
        )
        self.assertEqual(ios_module["category"], "ssl_pinning")
        self.assertEqual(ios_module["source_path"], "modules/ios/ssl_pinning/ssl_unpinning_ios_13.imed")

    def test_options_preserve_names_types_help_and_defaults(self) -> None:
        modules_with_options = [module for module in self.modules if module["has_options"]]
        self.assertEqual(len(modules_with_options), 5)
        self.assertTrue(all(option["name"] for module in modules_with_options for option in module["options"]))
        self.assertTrue(all(option["type"] for module in modules_with_options for option in module["options"]))
        self.assertTrue(all("help" in option and "value" in option for module in modules_with_options for option in module["options"]))


if __name__ == "__main__":
    unittest.main()