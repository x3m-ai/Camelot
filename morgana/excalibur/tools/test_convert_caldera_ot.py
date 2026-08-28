#!/usr/bin/env python3
"""Fixture-only tests for the CALDERA for OT converter. Nothing is executed."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parent / "convert_caldera_ot.py"
SPEC = importlib.util.spec_from_file_location("convert_caldera_ot", MODULE_PATH)
assert SPEC and SPEC.loader
converter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = converter
SPEC.loader.exec_module(converter)


class CalderaOtConverterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for protocol in converter.PLUGINS:
            (self.root / protocol / "data" / "abilities").mkdir(parents=True)
            (self.root / protocol / "payloads").mkdir()
            (self.root / protocol / "LICENSE").write_text("Fixture license\n", encoding="utf-8")
            (self.root / protocol / "NOTICE.md").write_text("Fixture notice\n", encoding="utf-8")
        self.overrides = self.root / "overrides.json"
        self.overrides.write_text(
            json.dumps(
                {
                    "abilities": {},
                    "rules": [
                        {"tcode": "T0888", "name_contains": "Read Device Information", "risk": "observe"},
                        {"tcode": "T0836", "name_contains": "Write Single Coil", "risk": "modify"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.commits = {"caldera-ot": "a" * 40, **{key: chr(98 + index) * 40 for index, key in enumerate(converter.PLUGINS)}}
        self.dates = {key: "2026-08-28" for key in self.commits}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def arguments(self, protocol: str | None = "modbus") -> argparse.Namespace:
        return argparse.Namespace(
            caldera_ot_dir=str(self.root),
            out_dir=str(self.root / "output"),
            risk_overrides=str(self.overrides),
            protocol=protocol,
            tactic=None,
            platform=None,
            dry_run=False,
            no_update_catalog=True,
        )

    def write_modbus_fixtures(self) -> None:
        payloads = self.root / "modbus" / "payloads"
        (payloads / "modbus_cli").write_bytes(b"reviewed-linux-fixture")
        (payloads / "modbus_cli.exe").write_bytes(b"reviewed-windows-fixture")
        abilities = self.root / "modbus" / "data" / "abilities"
        read_ability = [{
            "id": "fixture-read",
            "name": "Modbus - Read Device Information",
            "description": "Fixture read",
            "tactic": "discovery",
            "technique_id": "T0888",
            "technique_name": "Remote System Information Discovery",
            "executors": [{
                "platform": "linux",
                "name": "sh",
                "command": "./modbus_cli #{modbus.server.ip} --port #{modbus.server.port} read_device_info",
                "payloads": ["modbus_cli"],
            }],
        }]
        write_ability = [{
            "id": "fixture-write",
            "name": "Modbus - Write Single Coil",
            "description": "Fixture process write",
            "tactic": "impair-process-control",
            "technique": {"attack_id": "T0836", "name": "Modify Parameter"},
            "platforms": {
                "windows": {
                    "psh, cmd": {
                        "command": "./modbus_cli.exe #{modbus.server.ip} write_single_coil #{modbus.coil.address} #{modbus.coil.value}",
                        "payloads": ["modbus_cli.exe"],
                    }
                }
            },
            "additional_info": {
                "facts": {
                    "modbus.coil.value": {"description": "Required process coil state"}
                }
            },
        }]
        (abilities / "executors.yml").write_text(
            converter.yaml.safe_dump(read_ability, sort_keys=False), encoding="utf-8"
        )
        (abilities / "platforms.yml").write_text(
            converter.yaml.safe_dump(write_ability, sort_keys=False), encoding="utf-8"
        )

    def convert(self, arguments: argparse.Namespace):
        with mock.patch.object(converter, "source_identity", return_value=(self.commits, self.dates)):
            return converter.convert(arguments)

    def test_both_schemas_assets_facts_risk_and_determinism(self) -> None:
        self.write_modbus_fixtures()
        first = self.convert(self.arguments())
        second = self.convert(self.arguments())
        self.assertEqual(
            json.dumps(first[:4], sort_keys=True),
            json.dumps(second[:4], sort_keys=True),
        )
        packs, report, source_inventory, asset_inventory, assets = first
        self.assertEqual(len(packs), 2)
        self.assertEqual(report["summary"]["generated_scripts"], 3)
        self.assertEqual(report["statistics"]["by_risk"], {"modify": 2, "observe": 1})
        self.assertEqual(report["statistics"]["by_platform"], {"linux": 1, "windows": 2})
        self.assertEqual(len(assets), 2)
        self.assertEqual(source_inventory["source_commits"]["caldera-ot"], "a" * 40)
        self.assertEqual(asset_inventory["protocols"]["modbus"]["status_counts"], {"resolved": 3})

        scripts = [script for pack in packs for script in pack["scripts"]]
        read_script = next(script for script in scripts if script["tcode"] == "T0888")
        write_scripts = [script for script in scripts if script["tcode"] == "T0836"]
        self.assertEqual(read_script["operational_risk"], "observe")
        self.assertTrue(all(script["operational_risk"] == "modify" for script in write_scripts))
        self.assertIn("{{asset:modbus_modbus_cli_linux_amd64}}", read_script["command"])
        self.assertIn("#{ot_modbus_discovery_0888_server_ip}", read_script["command"])
        self.assertEqual(read_script["tag_params"]["ot_modbus_discovery_0888_server_ip"]["default"], "")
        coil = write_scripts[0]["tag_params"]["ot_modbus_impair_process_control_0836_coil_value"]
        self.assertEqual(coil["parameter_class"], "process_write")
        self.assertTrue(all(len(chain["script_refs"]) == 1 for pack in packs for chain in pack["chains"]))
        self.assertFalse(report["errors"])

    def test_missing_iec61850_external_release_assets_are_inventoried_and_skipped(self) -> None:
        ability = self.root / "iec61850" / "data" / "abilities" / "collection.yml"
        ability.write_text(
            textwrap.dedent(
                """
                - id: fixture-iec
                  name: IEC 61850 - Get Data Sets
                  tactic: collection
                  technique_id: T0802
                  technique_name: Automated Collection
                  executors:
                  - platform: windows
                    name: psh
                    command: .\\iec61850_actions.exe get data_sets #{iec61850.server.ip}
                    payloads: [iec61850_actions.exe]
                """
            ).strip() + "\n",
            encoding="utf-8",
        )
        packs, report, _, inventory, _ = self.convert(self.arguments("iec61850"))
        self.assertEqual(packs, [])
        self.assertEqual(report["summary"]["skipped_variants"], 1)
        self.assertEqual(inventory["protocols"]["iec61850"]["status_counts"], {"external_release": 1})
        self.assertFalse(report["errors"])

    def test_malformed_yaml_is_a_hard_error(self) -> None:
        path = self.root / "modbus" / "data" / "abilities" / "bad.yml"
        path.write_text("- id: [unterminated\n", encoding="utf-8")
        packs, report, _, _, _ = self.convert(self.arguments())
        self.assertEqual(packs, [])
        self.assertEqual(report["summary"]["hard_errors"], 1)

    def test_catalog_update_preserves_existing_entries(self) -> None:
        self.write_modbus_fixtures()
        packs, _, _, _, _ = self.convert(self.arguments())
        existing = [{"package_id": f"existing-{index}"} for index in range(26)]
        updated = converter.updated_catalog(
            {"catalog_version": "1.3.0", "updated": "2026-08-27", "packs": existing},
            packs,
            "2026-08-20",
        )
        self.assertEqual(updated["catalog_version"], "1.4.0")
        self.assertEqual(updated["updated"], "2026-08-27")
        self.assertEqual(updated["packs"][:26], existing)
        self.assertIn("ot/modbus", {category["id"] for category in updated["categories"]})
        self.assertIn("mitre-caldera-ot", {provider["id"] for provider in updated["providers"]})


if __name__ == "__main__":
    unittest.main()