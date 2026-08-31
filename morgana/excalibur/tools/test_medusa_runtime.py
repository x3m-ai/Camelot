#!/usr/bin/env python3
"""Compact MEDUSA compiler/runtime unit tests. No device execution."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from medusa_module_parser import parse_module, enumerate_modules
from medusa_compiler import compile_module, js_syntax_valid, substitute_options

MEDUSA_SOURCE = Path(
    os.environ.get("MEDUSA_SOURCE", r"C:\ProgramData\Morgana\temp\medusa-source")
)


class MedusaCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (MEDUSA_SOURCE / "modules").is_dir():
            raise unittest.SkipTest(f"MEDUSA source not found: {MEDUSA_SOURCE}")
        cls.core = MEDUSA_SOURCE / "libraries" / "js"
        cls.modules, _ = enumerate_modules(MEDUSA_SOURCE)

    def test_android_compilation_wraps_in_java_perform(self) -> None:
        module = parse_module(MEDUSA_SOURCE / "modules" / "helpers" / "location_spoof.med", "android")
        js, wired = compile_module(module, self.core)
        self.assertIn("Java.perform(function()", js)
        self.assertIn("setTimeout(displayAppInfo,500)", js)
        self.assertEqual(set(wired), {"latitude", "longitude"})
        self.assertTrue(js_syntax_valid(js)[0], js_syntax_valid(js)[1])

    def test_options_substitution_preserves_type_semantics(self) -> None:
        module = parse_module(MEDUSA_SOURCE / "modules" / "helpers" / "android_net_uri.med", "android")
        js, wired = compile_module(module, self.core)
        # boolean options are bare placeholders (unquoted); strings stay quoted
        self.assertIn("#{show_common}", js)
        self.assertNotIn("'#{show_common}'", js)
        self.assertEqual(set(wired), {"show_common", "show_all_query_params"})

        loc = parse_module(MEDUSA_SOURCE / "modules" / "helpers" / "location_spoof.med", "android")
        js2, wired2 = compile_module(loc, self.core)
        self.assertIn("'#{latitude}'", js2)
        self.assertEqual(set(wired2), {"latitude", "longitude"})

    def test_ios_compilation_uses_objc_wrapper(self) -> None:
        module = parse_module(MEDUSA_SOURCE / "modules" / "ios" / "ssl_pinning" / "ssl_unpinning_ios_13.imed", "ios")
        js, _ = compile_module(module, self.core)
        # iOS wrapper uses the try{} block, NOT the Android Java.perform preamble
        self.assertNotIn("setTimeout(displayAppInfo,500)", js)
        self.assertTrue(js_syntax_valid(js)[0], js_syntax_valid(js)[1])

    def test_jni_module_gets_env_prolog(self) -> None:
        jni = next((m for m in self.modules if m["platform"] == "android" and m["category"] == "JNICalls"), None)
        if jni is None:
            self.skipTest("no JNICalls module found")
        module = parse_module(MEDUSA_SOURCE / jni["source_path"], "android")
        js, _ = compile_module(module, self.core)
        self.assertIn("JNIEnv base address", js)

    def test_empty_scratchpad_returns_none(self) -> None:
        module = parse_module(MEDUSA_SOURCE / "modules" / "scratchpad.med", "android")
        self.assertIsNone(compile_module(module, self.core))

    def test_full_corpus_compiles_except_known_upstream_defect(self) -> None:
        compiled = 0
        manual = []
        syntax_fail = []
        for m in self.modules:
            r = compile_module(m, self.core)
            if r is None:
                manual.append(m["source_path"])
                continue
            js, _ = r
            ok, msg = js_syntax_valid(js)
            if ok:
                compiled += 1
            else:
                syntax_fail.append((m["source_path"], msg))
        self.assertEqual(compiled, 133)
        self.assertEqual(manual, ["modules/scratchpad.med", "modules/system_server/system_scratchpad.med", "modules/scratchpad.imed"])
        # exactly one genuine upstream brace defect in the iOS corpus
        self.assertEqual([p for p, _ in syntax_fail], ["modules/ios/helpers/dump_ios_url_scheme.imed"])


if __name__ == "__main__":
    unittest.main()
