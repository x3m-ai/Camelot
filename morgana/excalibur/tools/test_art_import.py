#!/usr/bin/env python3
"""
Test import of ART (Red Canary Atomic Red Team) Excalibur packs against a running Morgana server.

Usage:
    python test_art_import.py [--pack art-lateral-v1]   # import one pack
    python test_art_import.py --all                      # import all art-*.json packs
    python test_art_import.py --list                     # list available ART packs without importing
"""

import argparse
import json
import glob
import ssl
import sys
import urllib.request
import urllib.error
from pathlib import Path

ART_DIR = Path(__file__).parent.parent / "art"

# SSL context that accepts self-signed Morgana cert
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# Read from Morgana master.key (same as test_import.py convention)
MORGANA_URL = "https://localhost:8888/api/v2/scripts/import-package"
API_KEY_FILE = r"C:\ProgramData\Morgana\data\master.key"


def get_api_key() -> str:
    try:
        return Path(API_KEY_FILE).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        print(f"[ERROR] master.key not found at {API_KEY_FILE}")
        print("  Set MORGANA_API_KEY env var or start Morgana at least once.")
        sys.exit(1)


def import_pack(json_path: Path, api_key: str) -> bool:
    print(f"\n--- {json_path.name} ---")
    payload = json_path.read_bytes()

    req = urllib.request.Request(MORGANA_URL, data=payload, method="POST")
    req.add_header("KEY", api_key)
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, context=CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            imported = result.get("imported", 0)
            removed = result.get("removed", 0)
            chains = result.get("chains_imported", 0)
            errors = result.get("errors", [])
            print(f"[OK] imported={imported}  removed={removed}  chains={chains}")
            if errors:
                print(f"  Errors ({len(errors)}): {errors[:3]}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {json_path.name}")
        try:
            body = json.loads(e.read().decode("utf-8"))
            print(f"  Detail: {body.get('detail', '?')}")
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"[ERROR] {json_path.name}: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Test import ART packs into Morgana")
    parser.add_argument("--pack", help="Import only this pack (e.g. art-lateral-v1)")
    parser.add_argument("--all", action="store_true", help="Import all art-*.json packs")
    parser.add_argument("--list", action="store_true", help="List available packs without importing")
    parser.add_argument("--url", default=MORGANA_URL, help="Morgana import-package URL")
    args = parser.parse_args()

    packs = sorted(ART_DIR.glob("art-*.json"))
    if not packs:
        print(f"[ERROR] No art-*.json files found in {ART_DIR}")
        print("  Run convert_atomics.py first.")
        sys.exit(1)

    if args.list:
        for p in packs:
            d = json.loads(p.read_text(encoding="utf-8"))
            s = len(d.get("scripts", []))
            c = len(d.get("chains", []))
            print(f"  {p.name:<40} scripts={s:>4}  chains={c:>4}  ({round(p.stat().st_size/1024)}KB)")
        return

    if args.pack:
        target = ART_DIR / f"{args.pack}.json"
        if not target.exists():
            target = ART_DIR / args.pack
        if not target.exists():
            print(f"[ERROR] Pack not found: {args.pack}")
            sys.exit(1)
        packs = [target]
    elif not args.all:
        # default: import only small packs (<200 scripts) for smoke test
        packs = [p for p in packs if json.loads(p.read_text(encoding="utf-8")).get("scripts") and
                 len(json.loads(p.read_text(encoding="utf-8"))["scripts"]) <= 30]
        if not packs:
            packs = sorted(ART_DIR.glob("art-*.json"))[:1]
        print(f"[INFO] Smoke test mode: importing {len(packs)} small pack(s). Use --all for all packs.")

    api_key = get_api_key()
    ok = fail = 0

    for p in packs:
        if import_pack(p, api_key):
            ok += 1
        else:
            fail += 1

    print(f"\n--- Import complete: {ok} OK, {fail} failed ---")


if __name__ == "__main__":
    main()
