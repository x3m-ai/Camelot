#!/usr/bin/env python3
"""Compact Frida mobile conversion tests. No Frida source is executed."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

from convert_frida_mobile import build_packs, chunk_sources
from frida_classifier import classify
from frida_codeshare import page_projects, parse_project, project_links
from frida_dedup import deduplicate
from frida_github import discover_files, readme_snippets
from frida_sources import FridaSource, sha256


def source(source_id: str, code: str, title: str = "Fixture") -> FridaSource:
    return FridaSource(
        source_provider="fixture", source_id=source_id, title=title,
        description="Fixture source", source_code=code,
        source_url="https://example.invalid/source", source_hash=sha256(code),
        license="MIT", license_source="fixture", distribution_status="vendored",
        quality_tier="A",
    )


class FridaMobileTests(unittest.TestCase):
    def test_codeshare_project_and_pagination_extraction(self) -> None:
        browse = """
        <h2><a href="https://codeshare.frida.re/@alice/android-hook/">Android Hook</a></h2>
        <h3><i class="fa"></i> 12 | <i class="fa"></i> 3K</h3>
        <h2><a href="https://codeshare.frida.re/@bob/ios-hook/">iOS Hook</a></h2>
        <h3><i class="fa"></i> 4 | <i class="fa"></i> 900</h3>
        """
        self.assertEqual(project_links(browse), ["@alice/android-hook/", "@bob/ios-hook/"])
        self.assertEqual(page_projects(browse)["@alice/android-hook/"]["likes"], 12)
        code = "Java.perform(function(){ Java.use('android.app.Activity'); });"
        project = f'''projectName: "Android Hook", projectSlug: "android-hook", projectSource: {json.dumps(code)}, projectDesc: "Hook an app", projectUUID: "fixture" Fingerprint: {sha256(code)}'''
        parsed = parse_project("@alice/android-hook/", project, 2, {"likes": 12, "views": "3K"})
        self.assertEqual(parsed["source_id"], "codeshare:alice/android-hook")
        self.assertTrue(parsed["fingerprint_matches_source_hash"])
        self.assertEqual(parsed["discovery_page"], 2)

    def test_github_discovery_and_readme_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "scripts" / "direct.js").write_text("Java.perform(function(){ Java.use('A'); });", encoding="utf-8")
            (root / "ignored.js").write_text("send('ignored');", encoding="utf-8")
            (root / "README.md").write_text("# Standalone\n```js\nInterceptor.attach(Module.findExportByName(null, 'open'), { onEnter(args) { send(args[0]); } });\n```\n", encoding="utf-8")
            files, excluded = discover_files({"include": ["scripts/**/*.js"], "exclude": []}, root)
            self.assertEqual([path.name for path in files], ["direct.js"])
            self.assertTrue(any(item["source_path"] == "ignored.js" for item in excluded))
            snippets = readme_snippets(root)
            self.assertEqual(len(snippets), 1)
            self.assertEqual(snippets[0][0], "Standalone:js")

    def test_classification_dedup_derivative_and_pack_chunking(self) -> None:
        android_code = "Java.perform(function(){ var C=Java.use('okhttp3.Client'); C.run.implementation=function(){ return this.run(); }; });"
        ios_code = "if (ObjC.available) { Interceptor.attach(Module.findExportByName(null, 'SecTrustEvaluate'), {onEnter(args){send(args[0]);}}); }"
        flutter_code = "Interceptor.attach(Module.findExportByName('libflutter.so','SSL_set_custom_verify'), {onEnter(args){send(args[0]);}});"
        items = [
            classify(source("android", android_code, "Android OkHttp hook")),
            classify(source("ios", ios_code, "iOS trust hook")),
            classify(source("flutter", flutter_code, "Flutter TLS hook")),
            classify(source("exact", android_code, "Android duplicate")),
            classify(source("normalized", "// copied\n" + android_code + "\n", "Android normalized duplicate")),
        ]
        self.assertEqual(items[0].target_platform, "android")
        self.assertEqual(items[1].target_platform, "ios")
        self.assertIn("flutter", items[2].frameworks)
        canonical, report = deduplicate(items)
        self.assertEqual(len(canonical), 3)
        self.assertEqual(report["exact_duplicates"], 1)
        self.assertEqual(report["normalized_duplicates"], 1)
        packages = build_packs(canonical, max_count=1, max_bytes=500000)
        self.assertEqual(sum(len(package["scripts"]) for package, _ in packages), 3)
        self.assertTrue(all(package["assets"] == [] and package["chains"] == [] for package, _ in packages))
        self.assertTrue(all(script["executor"] == "frida" for package, _ in packages for script in package["scripts"]))
        self.assertTrue(all(script["executor_config"]["target"] == "#{mobile_app_id}" for package, _ in packages for script in package["scripts"]))


if __name__ == "__main__":
    unittest.main()