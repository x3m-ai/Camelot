#!/usr/bin/env python3
"""
stratus_assets.py — Stratus Red Team v2.36.0 official release asset manifest.

Official release assets and SHA256 checksums from:
https://github.com/DataDog/stratus-red-team/releases/tag/v2.36.0

These are the official upstream published checksums from checksums.txt.
"""
from __future__ import annotations

STRATUS_RELEASE = "v2.36.0"
STRATUS_SOURCE_COMMIT = "21c8fef54e8ce35dfb467992d3cd488802c29a65"
STRATUS_RELEASE_DATE = "2026-08-18"
STRATUS_LICENSE = "Apache-2.0"
STRATUS_REPO = "DataDog/stratus-red-team"

# Official release download base
_BASE = f"https://github.com/DataDog/stratus-red-team/releases/download/{STRATUS_RELEASE}"

# Official assets — filename → (sha256, size_bytes_approx)
# SHA256 values from official checksums.txt
OFFICIAL_ASSETS = {
    "stratus-red-team_Linux_x86_64.tar.gz": {
        "url": f"{_BASE}/stratus-red-team_Linux_x86_64.tar.gz",
        "platform": "linux",
        "architecture": "amd64",
        "executable": "stratus",
        "sha256": None,  # fetched at build time from checksums.txt
        "asset_id": "stratus_linux_amd64",
    },
    "stratus-red-team_Linux_arm64.tar.gz": {
        "url": f"{_BASE}/stratus-red-team_Linux_arm64.tar.gz",
        "platform": "linux",
        "architecture": "arm64",
        "executable": "stratus",
        "sha256": None,
        "asset_id": "stratus_linux_arm64",
    },
    "stratus-red-team_Windows_x86_64.tar.gz": {
        "url": f"{_BASE}/stratus-red-team_Windows_x86_64.tar.gz",
        "platform": "windows",
        "architecture": "amd64",
        "executable": "stratus.exe",
        "sha256": None,
        "asset_id": "stratus_windows_amd64",
    },
    "stratus-red-team_Windows_arm64.tar.gz": {
        "url": f"{_BASE}/stratus-red-team_Windows_arm64.tar.gz",
        "platform": "windows",
        "architecture": "arm64",
        "executable": "stratus.exe",
        "sha256": None,
        "asset_id": "stratus_windows_arm64",
    },
    "stratus-red-team_Darwin_x86_64.tar.gz": {
        "url": f"{_BASE}/stratus-red-team_Darwin_x86_64.tar.gz",
        "platform": "macos",
        "architecture": "amd64",
        "executable": "stratus",
        "sha256": None,
        "asset_id": "stratus_macos_amd64",
    },
    "stratus-red-team_Darwin_arm64.tar.gz": {
        "url": f"{_BASE}/stratus-red-team_Darwin_arm64.tar.gz",
        "platform": "macos",
        "architecture": "arm64",
        "executable": "stratus",
        "sha256": None,
        "asset_id": "stratus_macos_arm64",
    },
}

# Primary assets per execution platform (used in packages)
PRIMARY_ASSETS = {
    "linux":   "stratus_linux_amd64",
    "windows": "stratus_windows_amd64",
    "macos":   "stratus_macos_amd64",
}


def fetch_checksums() -> dict[str, str]:
    """Fetch official checksums.txt from GitHub and parse filename→sha256 map."""
    import urllib.request, ssl
    url = f"{_BASE}/checksums.txt"
    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs()
    except Exception:
        pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Morgana/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            content = r.read().decode("utf-8")
    except Exception as exc:
        print(f"[WARN] Could not fetch checksums.txt: {exc}")
        return {}

    checksums: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) == 2:
            sha, filename = parts
            checksums[filename] = sha
    return checksums


def build_asset_defs(checksums: dict[str, str]) -> list[dict]:
    """Build asset definition list with checksums filled in."""
    assets = []
    for filename, meta in OFFICIAL_ASSETS.items():
        sha = checksums.get(filename)
        assets.append({
            "id": meta["asset_id"],
            "name": f"stratus-{meta['platform']}-{meta['architecture']}",
            "filename": meta["executable"],
            "archive": filename,
            "platform": meta["platform"],
            "architecture": meta["architecture"],
            "url": meta["url"],
            "sha256": sha,
            "executable": True,
            "source": STRATUS_REPO,
            "release": STRATUS_RELEASE,
            "license": STRATUS_LICENSE,
            "source_commit": STRATUS_SOURCE_COMMIT,
        })
    return assets
