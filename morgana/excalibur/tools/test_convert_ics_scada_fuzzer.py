#!/usr/bin/env python3
"""Focused tests for ICS-SCADA-Fuzzer conversion; no fuzz profile is executed."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
from convert_ics_scada_fuzzer import build_packages, inspect_source, protocol_seed


SOURCE_FIXTURE = r'''
#define MAX_THREADS 64
#define MODBUS_PORT 502
#define DNP3_PORT 20000
#define S7_PORT 102
#define IEC104_PORT 2404
void recalc_modbus_len() {}
void recalc_dnp3_crc() {}
int main(int argc, char **argv) {
 while (getopt(argc, argv, "t:P:p:i:m:s:T:Sd:l:c:R:r:v?h") != -1) {}
 if(!strcasecmp(optarg,"modbus")) {}
 if(!strcasecmp(optarg,"dnp3")) {}
 if(!strcasecmp(optarg,"s7")) {}
 if(!strcasecmp(optarg,"iec104")) {}
 if(!strcasecmp(optarg,"opcua")) {}
 if(!strcasecmp(optarg,"random")) {}
 if(!strcasecmp(optarg,"bitflip")) {}
 if(!strcasecmp(optarg,"overflow")) {}
 if(!strcasecmp(optarg,"dictionary")) {}
 if(!strcasecmp(optarg,"format")) {}
 if(!strcasecmp(optarg,"type")) {}
 if(!strcasecmp(optarg,"time")) {}
 if(!strcasecmp(optarg,"sequence")) {}
 case 'S': stateful=1; break;
 case 'R': pcap_out=optarg; break;
 case 'r': pcap_init_replay(optarg); break;
 printf("Packets: %d | Anomalies: %d | Crashes: %d | Timeouts: %d");
}
'''


class IcsScadaFuzzerConverterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = json.loads((TOOLS_DIR / "ics_scada_fuzzer_mapping.json").read_text(encoding="utf-8"))

    def test_source_contract_and_complete_profile_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "ics_fuzzer.c"
            source.write_text(SOURCE_FIXTURE, encoding="utf-8")
            binary = root / "ics-fuzzer"
            binary.write_bytes(b"fixture-binary")
            contract = inspect_source(source, self.mapping)
            packages, inventory = build_packages(
                self.mapping, "fixture-sha", binary,
                hashlib.sha256(binary.read_bytes()).hexdigest(), binary.stat().st_size,
            )
        self.assertEqual(contract["max_threads"], 64)
        self.assertEqual(len(packages), 5)
        self.assertEqual(len(inventory), 120)
        self.assertTrue(all(len(package["scripts"]) == 24 for package, _ in packages))
        identities = {script["id"] for package, _ in packages for script in package["scripts"]}
        self.assertEqual(len(identities), 120)
        replay = next(script for package, _ in packages for script in package["scripts"] if script["source_metadata"]["mode"] == "replay")
        self.assertEqual(len(replay["required_assets"]), 2)
        self.assertIn("MORGANA_RESULT_METADATA=", replay["command"])
        self.assertIn("${args[@]}", replay["command"])
        self.assertIn("#{ot_fuzz_timeout}", replay["executor_config"]["timeout_seconds"])

    def test_protocol_seeds_are_deterministic_and_distinct(self) -> None:
        first = {protocol: protocol_seed(protocol) for protocol in self.mapping["protocols"]}
        second = {protocol: protocol_seed(protocol) for protocol in reversed(self.mapping["protocols"])}
        self.assertEqual(first, second)
        self.assertEqual(len({hashlib.sha256(value).hexdigest() for value in first.values()}), 5)
        self.assertTrue(all(value[:4] == bytes.fromhex("d4c3b2a1") for value in first.values()))


if __name__ == "__main__":
    unittest.main()