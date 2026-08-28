#!/usr/bin/env python3
"""Fixture-only tests for the CTID converter. No procedure or asset is executed."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

MODULE_PATH = Path(__file__).resolve().parent / "convert_ctid_emu.py"
SPEC = importlib.util.spec_from_file_location("convert_ctid_emu", MODULE_PATH)
assert SPEC and SPEC.loader
converter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = converter
SPEC.loader.exec_module(converter)


class CtidConverterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "library"
        self.yaml_dir = self.library / "fixture_actor" / "Emulation_Plan" / "yaml"
        self.yaml_dir.mkdir(parents=True)
        (self.library / "fixture_actor" / "Emulation_Plan" / "Scenario_1").mkdir()
        (self.library / "micro_emulation_plans" / "src" / "ad_enum").mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def write_plan(self):
        plan = [
            {"emulation_plan_details": {
                "id": "fixture-plan",
                "adversary_name": "Fixture Actor",
                "adversary_description": "A fixture threat actor used only for converter tests.",
                "attack_version": "15",
                "format_version": "1.0",
            }},
            {
                "id": "ready-procedure",
                "name": "Enumerate Host",
                "description": "Collect host information.",
                "tactic": "discovery",
                "technique": {"attack_id": "T1082", "name": "System Information Discovery"},
                "cti_source": "https://example.invalid/intelligence",
                "procedure_group": "procedure_discovery",
                "procedure_step": "1.A",
                "platforms": {"windows": {"cmd": {"command": "hostname #{target.host} & echo #{operator.password}"}}},
                "input_arguments": {
                    "target.host": {"description": "Authorized target host", "type": "string", "default": "prod-host"},
                    "operator.password": {"description": "Fixture credential", "type": "string", "default": "never-preserve"},
                },
            },
            {
                "id": "payload-procedure",
                "name": "Payload Step",
                "description": "Requires an unapproved payload.",
                "tactic": "execution",
                "technique": {"attack_id": "T1059.001", "name": "PowerShell"},
                "procedure_group": "procedure_execution",
                "procedure_step": "2.A",
                "platforms": {"windows": {"psh,pwsh": {"command": ".\\tool.exe", "payloads": ["tool.exe"]}}},
            },
        ]
        path = self.yaml_dir / "fixture.yaml"
        path.write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
        return path

    def test_full_plan_preserves_order_and_simulates_unavailable_payloads(self):
        path = self.write_plan()
        package, report, inventory = converter.convert_full_plan(
            path, self.library, "source-sha", "emu-sha"
        )

        self.assertEqual(package["package_id"], "ctid-fixture-actor-v1")
        self.assertEqual(package["attack_version"], "15")
        self.assertEqual(report["automated"], 2)
        self.assertEqual(report["source_commands"], 1)
        self.assertEqual(report["simulated"], 1)
        self.assertEqual(report["manual"], 0)
        self.assertEqual([row["procedure_step"] for row in inventory], ["1.A", "2.A"])
        self.assertEqual(
            [node["script_ref"] for node in package["chains"][0]["flow"]["nodes"]],
            [script["name"] for script in package["scripts"]],
        )
        self.assertEqual(package["scripts"][0]["executor"], "cmd")
        self.assertIn("#{ctid_fixture_actor_target_host}", package["scripts"][0]["command"])
        self.assertEqual(package["scripts"][1]["executor"], "powershell")
        self.assertNotIn("tool.exe", package["scripts"][1]["command"])
        self.assertIn("CTID simulation T1059.001", package["scripts"][1]["command"])
        self.assertTrue(package["scripts"][1]["cleanup_command"])
        self.assertEqual(package["scripts"][1]["source_metadata"]["conversion_status"], "simulated")
        tags = package["tag_categories"][0]["tags"]
        self.assertEqual(next(tag for tag in tags if tag["key"].endswith("target_host"))["default"], "")
        self.assertEqual(next(tag for tag in tags if tag["key"].endswith("operator_password"))["default"], "")
        self.assertTrue(next(tag for tag in tags if tag["key"].endswith("operator_password"))["sensitive"])

    def test_micro_plan_simulates_behavior_until_asset_review(self):
        package, report, _ = converter.convert_ad_enum(
            self.library, "source-sha", "emu-sha"
        )
        self.assertEqual(package["plan_type"], "micro-emulation")
        self.assertEqual(package["scripts"][0]["executor"], "powershell")
        self.assertIn("CTID simulation", package["scripts"][0]["command"])
        self.assertTrue(package["scripts"][0]["cleanup_command"])
        self.assertEqual(package["scripts"][0]["source_metadata"]["conversion_status"], "simulated")
        self.assertEqual(report["automated"], 1)
        self.assertEqual(report["manual"], 0)
        self.assertIn("SHA256", " ".join(package["safety_notes"]))

    def test_reviewed_override_creates_source_ordered_phase_chain(self):
        path = self.write_plan()
        overrides = self.root / "overrides.json"
        overrides.write_text(json.dumps({
            "fixture-actor": {
                "reason": "Fixture source document defines this phase.",
                "source_document": "fixture_actor/Emulation_Plan/Scenario_1/README.md",
                "phase_chains": [{
                    "id": "phase-1",
                    "name": "Phase 1",
                    "description": "Fixture phase.",
                    "objective": "Validate fixture phase ordering.",
                    "step_prefixes": ["1."],
                }],
            }
        }), encoding="utf-8")
        with mock.patch.object(converter, "OVERRIDES_FILE", overrides):
            package, report, _ = converter.convert_full_plan(
                path, self.library, "source-sha", "emu-sha"
            )
        self.assertEqual(len(package["chains"]), 2)
        self.assertEqual(report["phase_chains"], 1)
        self.assertEqual(
            [node["source_step"] for node in package["chains"][1]["flow"]["nodes"]],
            ["1.A"],
        )
        self.assertIn("Fixture source document", package["chains"][1]["source_metadata"]["override_reason"])

    def test_human_only_full_plan_converts_documented_steps_to_simulations(self):
        plan_dir = self.library / "manual_actor"
        (plan_dir / "Emulation_Plan").mkdir(parents=True)
        (plan_dir / "README.md").write_text(
            "# Manual Actor\n\nA documented threat-informed scenario.\n",
            encoding="utf-8",
        )
        (plan_dir / "Emulation_Plan" / "Scenario.md").write_text(
            "## Step 0 - macOS Setup\nPrepare the macOS lab.\n\n"
            "## Step 1 - Linux Discovery\nExercise T1082 on the Linux host.\n",
            encoding="utf-8",
        )
        package, report, inventory = converter.convert_manual_full_plan(
            plan_dir, self.library, "source-sha", "emu-sha"
        )
        self.assertEqual(len(package["scripts"]), 2)
        self.assertEqual(len(package["chains"][0]["flow"]["nodes"]), 2)
        self.assertEqual(report["automated"], 2)
        self.assertEqual(report["simulated"], 2)
        self.assertEqual(report["manual"], 0)
        self.assertEqual([item["source_order"] for item in inventory], [1, 2])
        self.assertEqual(package["scripts"][0]["executor"], "bash")
        self.assertEqual(package["scripts"][0]["platform"], "macos")
        self.assertEqual(package["scripts"][1]["tcode"], "T1082")
        self.assertEqual(package["scripts"][1]["executor"], "bash")
        self.assertEqual(package["scripts"][1]["platform"], "linux")
        self.assertIn("CTID simulation T1082", package["scripts"][1]["command"])
        self.assertTrue(package["scripts"][1]["cleanup_command"])
        metadata = package["scripts"][1]["source_metadata"]
        self.assertEqual(metadata["conversion_status"], "simulated")
        self.assertEqual(metadata["simulation_family"], "discovery")
        self.assertIn("source-sha", metadata["source_documentation"])

    def test_catalog_metadata_and_conversion_are_deterministic(self):
        path = self.write_plan()
        first = converter.convert_full_plan(path, self.library, "source-sha", "emu-sha")[0]
        second = converter.convert_full_plan(path, self.library, "source-sha", "emu-sha")[0]
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )
        micro = converter.convert_ad_enum(self.library, "source-sha", "emu-sha")[0]
        catalog = converter.update_catalog(
            {"catalog_version": "1.5.0", "providers": [], "categories": [], "packs": []},
            [
                converter.catalog_entry(first, "full/fixture/fixture.json"),
                converter.catalog_entry(micro, "micro/ad_enum/ad_enum.json"),
            ],
        )
        self.assertEqual(catalog["catalog_version"], "1.6.0")
        self.assertEqual({item["id"] for item in catalog["categories"]}, {
            "ctid/full-emulation", "ctid/micro-emulation"
        })
        self.assertEqual(catalog["providers"][0]["id"], "mitre-ctid")


if __name__ == "__main__":
    unittest.main()
